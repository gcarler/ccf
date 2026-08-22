"""Pruebas del Gateway Unificado FastMCP 2.0 (/api/mcp/*)."""

from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.models_agents import ToolExecutionLog
from tests.conftest import TestingSessionLocal, auth_headers, seed_admin, seed_user_with_role


@pytest.fixture
def gateway_setup(db_session, client, monkeypatch):
    import backend.core.database as core_db
    import backend.mcp_crm as m_crm
    import backend.mcp_cms as m_cms
    import backend.mcp_academy as m_acad
    import backend.mcp_agenda as m_ag
    import backend.mcp_evangelism as m_ev
    import backend.mcp_governance as m_gov
    import backend.api.mcp_gateway as m_gw

    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)
    for m in (m_crm, m_cms, m_acad, m_ag, m_ev, m_gov, m_gw):
        if hasattr(m, "SessionLocal"):
            monkeypatch.setattr(m, "SessionLocal", TestingSessionLocal)

    # Admin has all permissions including mcp:execute
    admin_user, admin_persona, admin_sede = seed_admin(db_session, email="mcp-gw-admin@test.com")
    admin_hdrs = auth_headers(client, email="mcp-gw-admin@test.com", password="testpass123")

    # Regular member user without mcp:execute
    member_user, member_persona, member_sede = seed_user_with_role(
        db_session, role_name="miembro", email="mcp-gw-member@test.com", permisos={}
    )
    member_hdrs = auth_headers(client, email="mcp-gw-member@test.com", password="testpass123")

    # Member user with explicit mcp:execute and crm:read permission grant
    exec_user, exec_persona, exec_sede = seed_user_with_role(
        db_session,
        role_name="miembro",
        email="mcp-gw-executor@test.com",
        permisos={"mcp:execute": "allow", "crm:read": "allow", "cms:read": "allow"},
    )
    exec_hdrs = auth_headers(client, email="mcp-gw-executor@test.com", password="testpass123")

    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key="ccf",
        name="Sitio CCF",
        is_active=True,
        sede_id=admin_sede.id,
    )
    db_session.add(site)
    db_session.commit()

    return {
        "admin": admin_user,
        "admin_headers": admin_hdrs,
        "member": member_user,
        "member_headers": member_hdrs,
        "executor": exec_user,
        "executor_headers": exec_hdrs,
        "sede": admin_sede,
        "client": client,
        "db": db_session,
    }


class TestFastMcpGateway:
    def test_list_servers(self, gateway_setup):
        client = gateway_setup["client"]
        res = client.get("/api/mcp/servers")
        assert res.status_code == 200
        data = res.json()
        assert "servers" in data
        assert {"crm", "cms", "academy", "agenda", "evangelism", "governance"} <= set(data["servers"])

    def test_list_all_tools_requires_mcp_execute(self, gateway_setup):
        client = gateway_setup["client"]
        # Member without mcp:execute -> 403
        res_forbidden = client.get("/api/mcp/tools", headers=gateway_setup["member_headers"])
        assert res_forbidden.status_code == 403
        assert "mcp:execute" in res_forbidden.json()["detail"]

        # Admin with mcp:execute -> 200
        res_ok = client.get("/api/mcp/tools", headers=gateway_setup["admin_headers"])
        assert res_ok.status_code == 200
        tools = res_ok.json()["tools"]
        assert len(tools) > 10
        tool_names = {t["name"] for t in tools}
        assert "list_crm_events" in tool_names
        assert "list_cms_posts" in tool_names
        assert "get_active_policies" in tool_names

    def test_list_server_tools(self, gateway_setup):
        client = gateway_setup["client"]
        res = client.get("/api/mcp/crm/tools/list", headers=gateway_setup["admin_headers"])
        assert res.status_code == 200
        data = res.json()
        assert data["server"] == "crm"
        tools = {t["name"] for t in data["tools"]}
        assert "search_crm_people" in tools
        assert "list_crm_events" in tools

    def test_call_server_tool_with_zero_trust_and_telemetry(self, gateway_setup):
        client = gateway_setup["client"]
        db = gateway_setup["db"]
        req_id = f"test-req-{uuid.uuid4().hex[:8]}"

        res = client.post(
            "/api/mcp/crm/tools/call",
            headers={
                **gateway_setup["admin_headers"],
                "X-Request-ID": req_id,
                "X-Sede-ID": str(gateway_setup["sede"].id),
            },
            json={
                "name": "list_crm_events",
                "arguments": {"limit": 5},
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["server"] == "crm"
        assert data["tool"] == "list_crm_events"
        assert "items" in data["result"]
        assert "latency_ms" in data

        # Verify telemetry log recorded in database
        log_entry = (
            db.query(ToolExecutionLog)
            .filter(ToolExecutionLog.request_id == req_id)
            .first()
        )
        assert log_entry is not None
        assert log_entry.tool_name == "list_crm_events"
        assert log_entry.status == "success"
        assert log_entry.execution_time_ms >= 0

    def test_call_tool_rejected_when_lacking_mcp_execute(self, gateway_setup):
        client = gateway_setup["client"]
        res = client.post(
            "/api/mcp/crm/tools/call",
            headers=gateway_setup["member_headers"],
            json={"name": "list_crm_events", "arguments": {}},
        )
        assert res.status_code == 403
        assert "mcp:execute" in res.json()["detail"]

    def test_call_universal_tools_endpoint(self, gateway_setup):
        client = gateway_setup["client"]
        req_id = f"universal-{uuid.uuid4().hex[:8]}"
        res = client.post(
            "/api/mcp/tools/call",
            headers={
                **gateway_setup["admin_headers"],
                "X-Request-ID": req_id,
            },
            json={
                "name": "list_cms_posts",
                "arguments": {"limit": 5},
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["server"] == "cms"
        assert data["tool"] == "list_cms_posts"

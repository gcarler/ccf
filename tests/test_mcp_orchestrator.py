"""Pruebas de integración de AgentOrchestrator con FastMCP 2.0 y telemetría."""

from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.agents.orchestrator import AgentOrchestrator
from backend.models_agents import ToolExecutionLog
from tests.conftest import TestingSessionLocal, seed_admin, seed_user_with_role


@pytest.fixture
def orchestrator_fixture(db_session, monkeypatch):
    import backend.core.database as core_db
    import backend.agents.orchestrator as orch_mod
    import backend.mcp_crm as m_crm
    import backend.mcp_cms as m_cms
    import backend.mcp_academy as m_acad
    import backend.mcp_agenda as m_ag
    import backend.mcp_evangelism as m_ev
    import backend.mcp_governance as m_gov

    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(orch_mod, "SessionLocal", TestingSessionLocal)
    for m in (m_crm, m_cms, m_acad, m_ag, m_ev, m_gov):
        if hasattr(m, "SessionLocal"):
            monkeypatch.setattr(m, "SessionLocal", TestingSessionLocal)

    admin, persona, sede = seed_admin(db_session, email="orch-admin@test.com")
    member, m_persona, m_sede = seed_user_with_role(
        db_session, role_name="miembro", email="orch-member@test.com", permisos={}
    )
    return {
        "admin": admin,
        "persona": persona,
        "sede": sede,
        "member": member,
        "db": db_session,
    }


class TestAgentOrchestratorFastMCP:
    def test_discover_fastmcp_tools(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-key-for-testing")
        orch = AgentOrchestrator(api_key="sk-mock-key-for-testing")
        tools = orch.get_mcp_tools()
        assert len(tools) > 10
        names = {t["function"]["name"] for t in tools}
        assert "list_crm_events" in names
        assert "list_cms_posts" in names
        assert "get_active_policies" in names
        assert "list_academy_courses" in names
        assert "ensure_mass_event" in names or "list_mass_events" in names

    def test_get_unified_tools_combines_mcp_and_registry(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-key-for-testing")
        orch = AgentOrchestrator(api_key="sk-mock-key-for-testing")
        unified = orch.get_tools()
        names = {t["function"]["name"] for t in unified}
        # FastMCP tools
        assert "list_crm_events" in names
        assert "list_cms_posts" in names
        # Registry tools
        assert "crm_search_persona" in names or "analytics_get_radar" in names

    def test_execute_tool_with_telemetry_logging(self, monkeypatch, orchestrator_fixture):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-key-for-testing")
        orch = AgentOrchestrator(api_key="sk-mock-key-for-testing")
        db = orchestrator_fixture["db"]
        admin = orchestrator_fixture["admin"]
        sede = orchestrator_fixture["sede"]
        req_id = f"orch-test-{uuid.uuid4().hex[:8]}"

        # Execute FastMCP tool
        result = orch.execute_tool(
            tool_name="list_crm_events",
            arguments={"limit": 5},
            user=admin,
            sede_id=sede.id,
            request_id=req_id,
        )
        assert isinstance(result, dict)
        assert "items" in result

        # Verify telemetry entry in DB
        log_entry = (
            db.query(ToolExecutionLog)
            .filter(ToolExecutionLog.request_id == req_id)
            .first()
        )
        assert log_entry is not None
        assert log_entry.tool_name == "list_crm_events"
        assert log_entry.status == "success"
        assert log_entry.sede_id == sede.id

    def test_execute_tool_rejects_unauthorized_user(self, monkeypatch, orchestrator_fixture):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-key-for-testing")
        orch = AgentOrchestrator(api_key="sk-mock-key-for-testing")
        member = orchestrator_fixture["member"]

        result = orch.execute_tool(
            tool_name="list_crm_events",
            arguments={"limit": 5},
            user=member,
        )
        assert "error" in result
        assert result.get("status") == 403 or "mcp:execute" in result.get("error", "")

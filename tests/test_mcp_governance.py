"""Pruebas del MCP de Gobernanza Institucional CCF."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from backend import models
from tests.conftest import TestingSessionLocal, seed_admin


@pytest.fixture
def governance_scope(db_session):
    admin, persona, sede = seed_admin(db_session, email="mcp-gov-admin@test.com")
    policy = models.GovernancePolicy(
        id=uuid.uuid4(),
        code=f"POL-{uuid.uuid4().hex[:4].upper()}",
        title="Política de Membresía y Ética",
        category="OPERACIONAL",
        version=1,
        status="PUBLICADA",
        content="Contenido de política de prueba",
        sede_id=sede.id,
        created_by_id=persona.id,
    )
    resolution = models.GovernanceResolution(
        id=uuid.uuid4(),
        number=f"RES-{uuid.uuid4().hex[:4].upper()}",
        title="Resolución de Ordenación Pastoral",
        summary="Aprobación de ordenación",
        content="Detalle de resolución eclesial",
        session_date=datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc),
        status="FIRMADA",
        sede_id=sede.id,
        created_by_id=persona.id,
    )
    committee = models.GovernanceCommittee(
        id=uuid.uuid4(),
        name="Comité de Doctrina y Disciplina",
        description="Comité de doctrina",
        committee_type="PASTORAL",
        sede_id=sede.id,
        is_active=True,
    )
    db_session.add_all([policy, resolution, committee])
    db_session.commit()
    return {
        "admin_id": admin.id,
        "persona": persona,
        "sede": sede,
        "policy": policy,
        "resolution": resolution,
        "committee": committee,
    }


def _authenticate(subject):
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="gov-test-token",
                client_id="test-client",
                subject=str(subject),
                scopes=["profile:manage", "system:config"],
            )
        )
    )


class TestMcpGovernanceContract:
    def test_registers_governance_tools(self):
        from backend.mcp_governance import governance_mcp

        tools = asyncio.run(governance_mcp.list_tools())
        names = {tool.name for tool in tools}
        assert {
            "get_active_policies",
            "get_official_resolutions",
            "list_pastoral_committees",
            "get_governance_summary",
        } <= names

    def test_query_active_policies_with_db_session(self, monkeypatch, governance_scope):
        import backend.mcp_governance as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(governance_scope["admin_id"])
        try:
            policies = module.get_active_policies(limit=10)
            assert isinstance(policies, list)
            assert len(policies) >= 1
            assert any(p["id"] == str(governance_scope["policy"].id) for p in policies)
        finally:
            auth_context_var.reset(token)

    def test_query_official_resolutions_with_db_session(self, monkeypatch, governance_scope):
        import backend.mcp_governance as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(governance_scope["admin_id"])
        try:
            resolutions = module.get_official_resolutions(limit=10)
            assert isinstance(resolutions, list)
            assert len(resolutions) >= 1
            assert any(r["id"] == str(governance_scope["resolution"].id) for r in resolutions)
        finally:
            auth_context_var.reset(token)

    def test_list_pastoral_committees_with_db_session(self, monkeypatch, governance_scope):
        import backend.mcp_governance as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(governance_scope["admin_id"])
        try:
            committees = module.list_pastoral_committees()
            assert isinstance(committees, list)
            assert len(committees) >= 1
            assert any(c["id"] == str(governance_scope["committee"].id) for c in committees)
        finally:
            auth_context_var.reset(token)

    def test_get_governance_summary_with_db_session(self, monkeypatch, governance_scope):
        import backend.mcp_governance as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(governance_scope["admin_id"])
        try:
            summary = module.get_governance_summary()
            assert isinstance(summary, dict)
            assert "total_policies" in summary or "active_policies" in summary or "policies" in summary or "total_resolutions" in summary or "total_committees" in summary
        finally:
            auth_context_var.reset(token)

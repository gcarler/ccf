"""Pruebas del MCP privado de CRM."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from backend import models
from tests.conftest import TestingSessionLocal, seed_admin


@pytest.fixture
def crm_scope(db_session):
    admin, person, sede = seed_admin(db_session, email="mcp-crm-admin@test.com")
    person.pastoral_notes = "Nota pastoral privada"
    person.medical_notes = "Dato médico privado"

    other_sede = models.Sede(
        id=uuid.uuid4(),
        nombre="Otra sede CRM MCP",
        ciudad="Cali",
        es_activa=True,
    )
    other_person = models.Persona(
        id=uuid.uuid4(),
        first_name="Persona",
        last_name="Externa",
        sede_id=other_sede.id,
        church_role="Miembro",
    )
    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Evento CRM MCP",
        description="Evento operativo",
        event_date=datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
        status="SCHEDULED",
        event_type="ONCE",
    )
    other_event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Evento de otra sede",
        event_date=datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc),
        sede_id=other_sede.id,
        status="SCHEDULED",
        event_type="ONCE",
    )
    db_session.add_all([other_sede, other_person, event, other_event])
    db_session.commit()
    return {
        "admin_id": admin.id,
        "person": person,
        "other_person": other_person,
        "event": event,
        "other_event": other_event,
    }


def _authenticate(subject):
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="crm-test-token",
                client_id="test-client",
                subject=str(subject),
                scopes=["crm:read", "crm:edit", "crm:manage"],
            )
        )
    )


class TestMcpCrmContract:
    def test_registers_crm_tools(self):
        from backend.mcp_crm import crm_mcp

        tools = asyncio.run(crm_mcp.list_tools())
        names = {tool.name for tool in tools}
        assert {
            "search_crm_people",
            "create_crm_person",
            "list_crm_cases",
            "add_crm_case_interaction",
            "add_crm_case_task",
            "list_crm_pipelines",
            "create_crm_automation_flow",
            "list_crm_events",
            "create_crm_event",
            "get_crm_event_attendance",
            "register_crm_event_attendance",
        } <= names

    def test_event_lifecycle_is_available_through_crm_mcp(self, monkeypatch, crm_scope):
        import backend.mcp_crm as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(crm_scope["admin_id"])
        try:
            created = module.create_crm_event(
                name="Nuevo evento MCP",
                event_type="ONCE",
                event_date="2026-09-01T10:00:00Z",
                location="Auditorio",
            )
            updated = module.update_crm_event(
                event_id=uuid.UUID(created["event_id"]),
                changes={"name": "Nuevo evento MCP actualizado"},
            )
            archived = module.archive_crm_event(uuid.UUID(created["event_id"]))
        finally:
            auth_context_var.reset(token)

        assert created["name"] == "Nuevo evento MCP"
        assert updated["name"] == "Nuevo evento MCP actualizado"
        assert archived == {"status": "archived", "event_id": created["event_id"]}

    def test_people_and_events_are_scoped_to_the_user_sede(self, monkeypatch, crm_scope):
        import backend.mcp_crm as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(crm_scope["admin_id"])
        try:
            people = module.search_crm_people(query=None, limit=100)
            events = module.list_crm_events(limit=100)
        finally:
            auth_context_var.reset(token)

        people_ids = {item["persona_id"] for item in people["items"]}
        event_ids = {item["event_id"] for item in events["items"]}
        assert str(crm_scope["person"].id) in people_ids
        assert str(crm_scope["other_person"].id) not in people_ids
        assert event_ids == {str(crm_scope["event"].id)}

    def test_person_response_excludes_sensitive_fields(self, monkeypatch, crm_scope):
        import backend.mcp_crm as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(crm_scope["admin_id"])
        try:
            result = module.get_crm_person(crm_scope["person"].id)
        finally:
            auth_context_var.reset(token)

        assert result["persona_id"] == str(crm_scope["person"].id)
        assert "pastoral_notes" not in result
        assert "medical_notes" not in result

    def test_event_attendance_rejects_cross_sede_people(self, monkeypatch, crm_scope):
        import backend.mcp_crm as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(crm_scope["admin_id"])
        try:
            result = module.register_crm_event_attendance(
                event_id=crm_scope["event"].id,
                session_date=date(2026, 8, 20),
                persona_ids=[crm_scope["other_person"].id],
            )
        finally:
            auth_context_var.reset(token)

        assert result["status"] == "rejected"
        assert str(crm_scope["other_person"].id) in result["invalid_persona_ids"]
        assert result["recorded"] == 0

    def test_event_attendance_is_idempotent_and_readable(self, monkeypatch, crm_scope):
        import backend.mcp_crm as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(crm_scope["admin_id"])
        try:
            first = module.register_crm_event_attendance(
                event_id=crm_scope["event"].id,
                session_date=date(2026, 8, 20),
                persona_ids=[crm_scope["person"].id],
            )
            second = module.register_crm_event_attendance(
                event_id=crm_scope["event"].id,
                session_date=date(2026, 8, 20),
                persona_ids=[crm_scope["person"].id],
            )
            report = module.get_crm_event_attendance(
                event_id=crm_scope["event"].id,
                session_date=date(2026, 8, 20),
            )
        finally:
            auth_context_var.reset(token)

        assert first["status"] == "success"
        assert second["status"] == "success"
        assert report["counts"]["present"] == 1
        assert report["present"][0]["persona_id"] == str(crm_scope["person"].id)

    def test_empty_attendance_requires_explicit_confirmation(self, monkeypatch, crm_scope):
        import backend.mcp_crm as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(crm_scope["admin_id"])
        try:
            with pytest.raises(ValueError, match="allow_empty"):
                module.register_crm_event_attendance(
                    event_id=crm_scope["event"].id,
                    session_date=date(2026, 8, 20),
                    persona_ids=[],
                )
        finally:
            auth_context_var.reset(token)

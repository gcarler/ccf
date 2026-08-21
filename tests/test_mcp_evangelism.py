"""Pruebas del MCP privado de evangelismo y su frontera multi-sede."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from backend import models
from tests.conftest import TestingSessionLocal, seed_admin


@pytest.fixture
def mass_event(db_session):
    _admin, _persona, sede = seed_admin(db_session, email="mcp-admin@test.com")
    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Conferencia MCP",
        event_date=datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
        status="SCHEDULED",
        settings_json={
            "evangelism_strategy_id": str(uuid.uuid4()),
            "strategy_typology": "evento_masivo",
        },
    )
    person = models.Persona(
        id=uuid.uuid4(),
        first_name="Persona",
        last_name="MCP",
        sede_id=sede.id,
        church_role="Miembro",
    )
    other_sede = models.Sede(
        id=uuid.uuid4(),
        nombre="Otra sede MCP",
        ciudad="Cali",
        es_activa=True,
    )
    other_person = models.Persona(
        id=uuid.uuid4(),
        first_name="Otra",
        last_name="Sede",
        sede_id=other_sede.id,
        church_role="Miembro",
    )
    db_session.add_all([event, person, other_sede, other_person])
    db_session.commit()
    return {"event": event, "person": person, "other_person": other_person, "admin_id": _admin.id}


def _authenticate(subject):
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="test-token",
                client_id="test-client",
                subject=str(subject),
                scopes=["evangelism:read", "evangelism:edit", "evangelism:manage"],
            )
        )
    )


class TestMcpEvangelismContract:
    def test_registers_private_tools(self):
        import asyncio

        from backend.mcp_evangelism import mass_event_mcp

        tools = asyncio.run(mass_event_mcp.list_tools())
        names = {tool.name for tool in tools}
        assert {
            "list_mass_events",
            "ensure_mass_event",
            "search_mass_event_people",
            "get_mass_event_attendance",
            "register_mass_event_attendance",
        } <= names

    def test_lists_strategies_with_the_authenticated_user_context(self, monkeypatch, mass_event):
        import backend.mcp_evangelism as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(mass_event["admin_id"])
        try:
            result = module.list_evangelism_strategies(limit=20)
        finally:
            auth_context_var.reset(token)

        assert "items" in result
        assert result["count"] == len(result["items"])

    def test_register_attendance_rejects_person_from_other_sede(self, monkeypatch, mass_event):
        import backend.mcp_evangelism as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(mass_event["admin_id"])
        try:
            result = module.register_mass_event_attendance(
                event_id=mass_event["event"].id,
                session_date=date(2026, 8, 20),
                persona_ids=[mass_event["other_person"].id],
            )
        finally:
            auth_context_var.reset(token)

        assert result["status"] == "rejected"
        assert str(mass_event["other_person"].id) in result["invalid_persona_ids"]

    def test_register_and_read_attendance_without_groups(self, monkeypatch, mass_event):
        import backend.mcp_evangelism as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(mass_event["admin_id"])
        try:
            saved = module.register_mass_event_attendance(
                event_id=mass_event["event"].id,
                session_date=date(2026, 8, 20),
                persona_ids=[mass_event["person"].id],
            )
            report = module.get_mass_event_attendance(
                event_id=mass_event["event"].id,
                session_date=date(2026, 8, 20),
            )
        finally:
            auth_context_var.reset(token)

        assert saved["status"] == "success"
        assert saved["created"] == 1
        assert report["counts"]["present"] == 1
        assert report["counts"]["absent"] >= 1
        assert report["expected_count"] >= 2
        assert report["present"][0]["persona_id"] == str(mass_event["person"].id)

    def test_register_attendance_reactivates_soft_deleted_row(self, monkeypatch, mass_event, db_session):
        import backend.mcp_evangelism as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        event = mass_event["event"]
        person = mass_event["person"]
        session_date = date(2026, 8, 20)

        # Fila soft-deleted para la misma terna (evento, fecha, persona): la
        # UniqueConstraint(event_id, session_date, persona_id) no considera
        # deleted_at, así que debe reutilizarse en vez de reventar con
        # IntegrityError (regresión Hallazgo 2).
        existing = models.EventAttendance(
            id=uuid.uuid4(),
            event_id=event.id,
            session_date=session_date,
            persona_id=person.id,
            attended=True,
            status="present",
            source="manual",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(existing)
        db_session.commit()

        token = _authenticate(mass_event["admin_id"])
        try:
            result = module.register_mass_event_attendance(
                event_id=event.id,
                session_date=session_date,
                persona_ids=[person.id],
            )
        finally:
            auth_context_var.reset(token)

        assert result["status"] == "success"
        assert result["created"] == 0  # reutilizó la fila, no insertó duplicado

        db_session.expire_all()
        rows = (
            db_session.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event.id,
                models.EventAttendance.session_date == session_date,
                models.EventAttendance.persona_id == person.id,
            )
            .all()
        )
        assert len(rows) == 1
        assert rows[0].deleted_at is None
        assert rows[0].attended is True

    def test_empty_selection_requires_explicit_confirmation(self, monkeypatch, mass_event):
        import backend.mcp_evangelism as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(mass_event["admin_id"])
        try:
            with pytest.raises(ValueError, match="allow_empty"):
                module.register_mass_event_attendance(
                    event_id=mass_event["event"].id,
                    session_date=date(2026, 8, 20),
                    persona_ids=[],
                )
        finally:
            auth_context_var.reset(token)

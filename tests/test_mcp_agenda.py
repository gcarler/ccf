"""Pruebas del MCP privado de Calendario/Agenda."""

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
def agenda_scope(db_session):
    admin, person, sede = seed_admin(db_session, email="mcp-agenda-admin@test.com")
    event = models.EventoAgenda(
        id=uuid.uuid4(),
        sede_id=sede.id,
        titulo="Agenda MCP",
        fecha_inicio=datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 8, 20, 11, 0, tzinfo=timezone.utc),
        organizador_persona_id=person.id,
        visibilidad="SEDE",
        estado="ACTIVO",
    )
    resource = models.RecursoFisico(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Salón MCP",
        tipo="salon",
        capacidad_maxima=30,
        activo=True,
    )
    other_sede = models.Sede(id=uuid.uuid4(), nombre="Otra sede Agenda", ciudad="Cali", es_activa=True)
    other_event = models.EventoAgenda(
        id=uuid.uuid4(),
        sede_id=other_sede.id,
        titulo="Evento externo",
        fecha_inicio=datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 8, 20, 11, 0, tzinfo=timezone.utc),
        organizador_persona_id=person.id,
        visibilidad="SEDE",
        estado="ACTIVO",
    )
    db_session.add_all([event, resource, other_sede, other_event])
    db_session.commit()
    return {"admin_id": admin.id, "person": person, "event": event, "resource": resource, "other_event": other_event}


def _authenticate(subject):
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="agenda-test-token",
                client_id="test-client",
                subject=str(subject),
                scopes=["spiritual_life:read", "spiritual_life:edit", "spiritual_life:manage"],
            )
        )
    )


class TestMcpAgendaContract:
    def test_registers_calendar_tools(self):
        from backend.mcp_agenda import agenda_mcp

        tools = asyncio.run(agenda_mcp.list_tools())
        names = {tool.name for tool in tools}
        assert {
            "list_calendar_events",
            "create_calendar_event",
            "create_calendar_resource",
            "add_calendar_participant",
            "create_calendar_reservation",
        } <= names

    def test_events_are_scoped_and_lifecycle_works(self, monkeypatch, agenda_scope):
        import backend.mcp_agenda as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(agenda_scope["admin_id"])
        try:
            listed = module.list_calendar_events(limit=100)
            created = module.create_calendar_event(
                title="Evento creado por MCP",
                start_at="2026-09-01T10:00:00Z",
                end_at="2026-09-01T11:00:00Z",
            )
            archived = module.archive_calendar_event(uuid.UUID(created["event_id"]))
        finally:
            auth_context_var.reset(token)

        ids = {item["event_id"] for item in listed["items"]}
        assert str(agenda_scope["event"].id) in ids
        assert str(agenda_scope["other_event"].id) not in ids
        assert archived["status"] == "archived"

    def test_reservation_conflict_and_cross_sede_event_are_rejected(self, monkeypatch, agenda_scope):
        import backend.mcp_agenda as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(agenda_scope["admin_id"])
        try:
            first = module.create_calendar_reservation(
                event_id=agenda_scope["event"].id,
                resource_id=agenda_scope["resource"].id,
                starts_at="2026-08-20T10:00:00Z",
                ends_at="2026-08-20T11:00:00Z",
            )
            with pytest.raises(ValueError, match="reservado"):
                module.create_calendar_reservation(
                    event_id=agenda_scope["event"].id,
                    resource_id=agenda_scope["resource"].id,
                    starts_at="2026-08-20T10:30:00Z",
                    ends_at="2026-08-20T11:30:00Z",
                )
            with pytest.raises(ValueError, match="no encontrado"):
                module.get_calendar_event(agenda_scope["other_event"].id)
        finally:
            auth_context_var.reset(token)

        assert first["event_id"] == str(agenda_scope["event"].id)

    def test_participant_requires_person_from_same_sede(self, monkeypatch, agenda_scope, db_session):
        external = models.Persona(
            id=uuid.uuid4(),
            first_name="Persona",
            last_name="Externa",
            sede_id=agenda_scope["other_event"].sede_id,
        )
        db_session.add(external)
        db_session.commit()
        import backend.mcp_agenda as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(agenda_scope["admin_id"])
        try:
            with pytest.raises(ValueError, match="sede"):
                module.add_calendar_participant(agenda_scope["event"].id, external.id)
        finally:
            auth_context_var.reset(token)

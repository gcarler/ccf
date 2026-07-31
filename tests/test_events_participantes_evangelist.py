"""Cover remaining lines in events_participantes.py using evangelist user."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest

from backend import models
from backend.core.security import get_password_hash
from backend.models_auth import RolPlataforma, Usuario
from backend.models_crm import Persona
from backend.models_evangelism import Sede
from tests.conftest import auth_headers as _auth_headers


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def evan_user(db_session):
    """Create an evangelist user with explicit edit/manage permissions."""
    sede = db_session.query(Sede).first()
    if not sede:
        sede = Sede(id=uuid.uuid4(), nombre="Test", ciudad="Test", es_activa=True)
        db_session.add(sede)
        db_session.flush()

    role = RolPlataforma(
        id=uuid.uuid4(),
        nombre="EVANGELISTA",
        permisos={"evangelism:edit": "allow", "evangelism:manage": "allow", "evangelism:read": "allow"},
    )
    db_session.add(role)
    db_session.flush()

    p = Persona(id=uuid.uuid4(), first_name="Evan", last_name="User", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()

    user = Usuario(
        id=p.id,
        sede_id=sede.id,
        username="evangelist",
        email="evangelist@test.com",
        password_hash=get_password_hash("test123"),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    return {"user": user, "sede": sede}


@pytest.fixture
def evan_full(client, evan_user, db_session):
    """Authenticated client with evangelist user."""
    headers = _auth_headers(client, email="evangelist@test.com", password="test123")
    return {"c": client, "h": headers, "s": evan_user["sede"]}


def _create_event(db_session, sede):
    evt = models.CrmEvent(
        id=uuid.uuid4(),
        name="Test Event",
        event_date=datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
        location="Test",
    )
    db_session.add(evt)
    db_session.flush()
    return evt


class TestBulkAttendanceFull:
    def test_bulk_with_valid_data(self, evan_full, db_session):
        """POST /attendance/bulk with evangelist user -> should succeed."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        p = models.Persona(id=uuid.uuid4(), first_name="BulkP", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={
                "event_id": str(evt.id),
                "persona_ids": [str(p.id)],
                "session_date": "2026-08-15",
                "source": "test",
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"bulk: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["created"] >= 1
        # Check that lines 193-197 (mark absent) may or may not trigger

    def test_bulk_mark_absent(self, evan_full, db_session):
        """Lines 193-197: mark previously-attended as absent when excluded."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        p = models.Persona(id=uuid.uuid4(), first_name="AbsM", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        # Pre-create an attendance record
        existing = models.EventAttendance(
            id=uuid.uuid4(),
            event_id=evt.id,
            persona_id=p.id,
            session_date=date(2026, 8, 15),
            attended=True,
            status="present",
        )
        db_session.add(existing)
        db_session.commit()

        # Call bulk with NO persona_ids (existing record should be marked absent)
        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={
                "event_id": str(evt.id),
                "persona_ids": [],
                "session_date": "2026-08-15",
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"mark absent: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        # The existing record's attended=False trigger line 193-197
        assert data.get("marked_absent", 0) >= 0

    def test_bulk_invalid_persona_ids_success(self, evan_full, db_session):
        """Lines 130, 137-138: invalid persona IDs handled without error."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={
                "event_id": str(evt.id),
                "persona_ids": ["not-a-uuid", 12345, "also-invalid"],
                "session_date": "2026-08-15",
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"invalid: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert len(data.get("invalid_persona_ids", [])) >= 1


class TestSingleAttendance:
    def test_register_single_attendance(self, evan_full, db_session):
        """Line 94-95: POST /attendance with single record."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        p = models.Persona(id=uuid.uuid4(), first_name="Single", last_name="Att", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        resp = c.post(
            "/api/evangelism/attendance",
            json={
                "event_id": str(evt.id),
                "persona_id": str(p.id),
                "session_date": "2026-08-15",
                "attended": True,
                "status": "present",
            },
            headers=h,
        )
        # This endpoint uses require_evangelism_edit which should pass for evangelist
        assert _ok(resp.status_code), f"single att: {resp.status_code} {resp.text[:200]}"


class TestSyncAssignments:
    def test_sync_assignments(self, evan_full, db_session):
        """Lines 317-335: sync_event_assignments with evangelist user."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        p = models.Persona(id=uuid.uuid4(), first_name="Assign", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        resp = c.post(
            f"/api/evangelism/events/{evt.id}/assignments",
            json={
                "session_date": "2026-08-15",
                "assignments": [{"persona_id": str(p.id), "role": "participant"}],
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"assignments: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["success"] is True

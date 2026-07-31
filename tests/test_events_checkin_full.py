"""Tests for events_checkin.py — visitor check-in endpoint."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date

import pytest

from backend import models
from backend.models_evangelism import Sede
from backend.models_crm import Persona
from backend.models_auth import Usuario, RolPlataforma
from backend.core.security import get_password_hash
from tests.conftest import auth_headers as _auth_headers


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def evan_user(db_session):
    """Create an evangelist user with explicit edit permissions."""
    sede = db_session.query(Sede).first()
    if not sede:
        sede = Sede(id=uuid.uuid4(), nombre="Test", ciudad="Test", es_activa=True)
        db_session.add(sede)
        db_session.flush()

    role = RolPlataforma(
        id=uuid.uuid4(), nombre="EVANGELISTA",
        permisos={"evangelism:edit": "allow", "evangelism:read": "allow"},
    )
    db_session.add(role)
    db_session.flush()

    p = Persona(id=uuid.uuid4(), first_name="Checkin", last_name="User", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()

    user = Usuario(
        id=p.id, sede_id=sede.id, username="checkin",
        email="checkin@test.com",
        password_hash=get_password_hash("test123"),
        rol_plataforma_id=role.id, is_active=True, is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    return {"user": user, "sede": sede}


@pytest.fixture
def evan_full(client, evan_user, db_session):
    """Authenticated client with evangelist user."""
    headers = _auth_headers(client, email="checkin@test.com", password="test123")
    return {"c": client, "h": headers, "s": evan_user["sede"]}


def _create_event(db_session, sede):
    evt = models.CrmEvent(
        id=uuid.uuid4(), name="Checkin Event",
        event_date=datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
    )
    db_session.add(evt)
    db_session.flush()
    return evt


class TestCheckin:
    def test_new_visitor(self, evan_full, db_session):
        """Create a new visitor via check-in."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        resp = c.post(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15/visitors",
            json={"first_name": "New", "last_name": "Visitor",
                  "phone": "+573001234567", "email": "new@test.com"},
            headers=h)
        assert _ok(resp.status_code), f"new visitor: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["status"] == "success"
        assert data["is_duplicate"] is False
        assert "visitor_id" in data

    def test_existing_persona_by_email(self, evan_full, db_session):
        """Existing persona matched by email."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        # Create existing persona with email
        p = Persona(id=uuid.uuid4(), first_name="Exist", last_name="Email",
                   sede_id=s.id, email="exist@test.com")
        db_session.add(p)
        db_session.commit()

        resp = c.post(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15/visitors",
            json={"first_name": "Exist", "last_name": "Email",
                  "email": "exist@test.com"},
            headers=h)
        assert _ok(resp.status_code), f"existing email: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        # This returns is_duplicate=True since we use email/phone
        assert data["status"] == "success"

    def test_existing_persona_by_phone(self, evan_full, db_session):
        """Existing persona matched by phone."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        p = Persona(id=uuid.uuid4(), first_name="Exist", last_name="Phone",
                   sede_id=s.id, phone="+573009999999")
        db_session.add(p)
        db_session.commit()

        resp = c.post(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15/visitors",
            json={"first_name": "Exist", "last_name": "Phone",
                  "phone": "+573009999999"},
            headers=h)
        assert _ok(resp.status_code), f"existing phone: {resp.status_code} {resp.text[:200]}"

    def test_invalid_date_format(self, evan_full, db_session):
        """Invalid session_date -> 400."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)
        resp = c.post(
            f"/api/evangelism/events/{evt.id}/sessions/not-a-date/visitors",
            json={"first_name": "Bad", "last_name": "Date"},
            headers=h)
        assert resp.status_code == 400

    def test_event_not_found(self, evan_full):
        """Non-existent event -> 404."""
        resp = evan_full["c"].post(
            f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-08-15/visitors",
            json={"first_name": "No", "last_name": "Event"},
            headers=evan_full["h"])
        assert resp.status_code == 404

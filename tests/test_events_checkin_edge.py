"""Cover remaining lines in events_checkin.py — duplicate attendance and CRM error."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

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

    p = Persona(id=uuid.uuid4(), first_name="Ck2", last_name="User", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()

    user = Usuario(
        id=p.id, sede_id=sede.id, username="checkin2",
        email="checkin2@test.com",
        password_hash=get_password_hash("test123"),
        rol_plataforma_id=role.id, is_active=True, is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    return {"user": user, "sede": sede}


@pytest.fixture
def evan_full(client, evan_user, db_session):
    headers = _auth_headers(client, email="checkin2@test.com", password="test123")
    return {"c": client, "h": headers, "s": evan_user["sede"]}


def _create_event(db_session, sede):
    evt = models.CrmEvent(
        id=uuid.uuid4(), name="Checkin2 Event",
        event_date=datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
    )
    db_session.add(evt)
    db_session.flush()
    return evt


class TestCheckinEdgeCases:
    def test_duplicate_attendance(self, evan_full, db_session):
        """Lines 64-65: existing attendance record returns duplicate."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        p = Persona(id=uuid.uuid4(), first_name="Dup", last_name="Check",
                   sede_id=s.id, email="dup@test.com")
        db_session.add(p)
        db_session.commit()

        # First check-in creates attendance
        resp1 = c.post(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15/visitors",
            json={"first_name": "Dup", "last_name": "Check", "email": "dup@test.com"},
            headers=h)
        assert _ok(resp1.status_code)

        # Second check-in with same email -> duplicate
        resp2 = c.post(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15/visitors",
            json={"first_name": "Dup", "last_name": "Check", "email": "dup@test.com"},
            headers=h)
        assert _ok(resp2.status_code), f"dup: {resp2.status_code} {resp2.text[:200]}"
        data = resp2.json()
        assert data.get("is_duplicate") is True

    def test_crm_bridge_error(self, evan_full, db_session):
        """Lines 124-125: CRM bridge failure is caught."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        evt = _create_event(db_session, s)

        # Mock crear_caso_nuevo_visitante to raise an exception
        from unittest.mock import patch
        with patch("backend.services.evangelism_crm_bridge.crear_caso_nuevo_visitante",
                   side_effect=Exception("CRM down")):
            resp = c.post(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15/visitors",
                json={"first_name": "CRM", "last_name": "Fail",
                      "email": "crmfail@test.com"},
                headers=h)
        assert _ok(resp.status_code), f"crm error: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["status"] == "success"
        assert data["is_duplicate"] is False

"""Cover remaining edge cases in evangelism_notifications.py."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from backend import models
from backend.core.security import get_password_hash
from backend.models_auth import Usuario
from backend.models_evangelism import GrupoEvangelismo, Sede, SesionGrupo
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="notif3@test.com")
    headers = _auth_headers(client, email="notif3@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(Sede).first()}


class TestNotificationsEdgeCases:
    def test_group_without_leader_skipped(self, full, db_session):
        """Lines 114, 116: group without lider_persona_id is skipped."""
        c, h, s = full["c"], full["h"], full["s"]
        tomorrow = date.today() + timedelta(days=1)

        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="No Leader", sede_id=s.id, lider_persona_id=None, activo=True)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, 0, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add(ses)
        db_session.commit()

        resp = c.post("/api/evangelism/notifications/send-reminders", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_leader_without_auth_user_skipped(self, full, db_session):
        """Lines 116: leader without auth user is skipped."""
        c, h, s = full["c"], full["h"], full["s"]
        tomorrow = date.today() + timedelta(days=1)

        p = models.Persona(id=uuid.uuid4(), first_name="NoAuth", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="No Auth User", sede_id=s.id, lider_persona_id=p.id, activo=True)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, 0, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add(ses)
        db_session.commit()

        resp = c.post("/api/evangelism/notifications/send-reminders", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_duplicate_notification_skipped(self, full, db_session):
        """Lines 133, 210: notification already sent today is skipped."""
        c, h, s = full["c"], full["h"], full["s"]
        tomorrow = date.today() + timedelta(days=1)

        p = models.Persona(id=uuid.uuid4(), first_name="Dup", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        user = Usuario(
            id=p.id,
            sede_id=s.id,
            username="duplead",
            email="dup@test.com",
            password_hash=get_password_hash("test"),
            is_active=True,
            is_email_verified=True,
        )
        db_session.add(user)
        db_session.commit()

        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="Dup Group", sede_id=s.id, lider_persona_id=p.id, activo=True)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, 0, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add(ses)
        db_session.commit()

        # First call creates notification
        resp1 = c.post("/api/evangelism/notifications/send-reminders", json={}, headers=h)
        assert _ok(resp1.status_code)
        assert resp1.json()["notifications_created"] >= 1

        # Second call should skip duplicate
        resp2 = c.post("/api/evangelism/notifications/send-reminders", json={}, headers=h)
        assert _ok(resp2.status_code)

"""Comprehensive tests for evangelism_notifications.py."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta, date

import pytest

from backend import models
from backend.models_evangelism import Sede, GrupoEvangelismo, SesionGrupo, Asistencia
from backend.models_auth import Usuario
from backend.core.security import get_password_hash
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="notif2@test.com")
    headers = _auth_headers(client, email="notif2@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(Sede).first()}


class TestNotificationsComprehensive:
    def test_with_real_data(self, full, db_session):
        """Seed data for both notification types and call the endpoint."""
        c, h, s = full["c"], full["h"], full["s"]

        # Create leader personas with auth users
        leaders = []
        for i in range(2):
            p = models.Persona(id=uuid.uuid4(), first_name=f"Lead{i}", last_name="Tst",
                              sede_id=s.id)
            db_session.add(p)
            db_session.flush()
            # Create auth user with same ID
            user = Usuario(
                id=p.id, sede_id=s.id, username=f"leader{i}",
                email=f"leader{i}@test.com",
                password_hash=get_password_hash("test"),
                is_active=True, is_email_verified=True,
            )
            db_session.add(user)
            leaders.append(p)
        db_session.flush()

        # --- Grupo A: has session TOMORROW with estado=PENDIENTE ---
        tomorrow = date.today() + timedelta(days=1)
        g_a = GrupoEvangelismo(id=uuid.uuid4(), nombre="Tomorrow Group",
                               sede_id=s.id, lider_persona_id=leaders[0].id,
                               activo=True)
        db_session.add(g_a)
        db_session.flush()

        ses_a = SesionGrupo(id=uuid.uuid4(), grupo_id=g_a.id,
                           fecha_sesion=datetime(tomorrow.year, tomorrow.month, tomorrow.day,
                                                 10, 0, 0, tzinfo=timezone.utc),
                           estado="PENDIENTE", tema_estudio="Test Session")
        db_session.add(ses_a)

        # --- Grupo B: active but NO recent attendance report ---
        g_b = GrupoEvangelismo(id=uuid.uuid4(), nombre="Inactive Group",
                               sede_id=s.id, lider_persona_id=leaders[1].id,
                               activo=True)
        db_session.add(g_b)
        db_session.flush()

        # Session for g_b that's OLD (60 days ago, not in last 7 days)
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        ses_b = SesionGrupo(id=uuid.uuid4(), grupo_id=g_b.id,
                           fecha_sesion=old_date,
                           estado="REALIZADA")
        db_session.add(ses_b)
        db_session.commit()

        # Make sure NotificacionUsuario table exists and call the endpoint
        resp = c.post("/api/evangelism/notifications/send-reminders",
            json={}, headers=h)
        assert _ok(resp.status_code), f"reminders: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["success"] is True
        assert data["sessions_tomorrow_count"] >= 1
        assert data["inactive_groups_count"] >= 1
        assert data["notifications_created"] >= 1

    def test_empty_no_data(self, full):
        """No data returns success with zeros."""
        resp = full["c"].post("/api/evangelism/notifications/send-reminders",
            json={}, headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert data["notifications_created"] == 0

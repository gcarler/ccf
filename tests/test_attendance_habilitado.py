"""Attendance tests with properly HABILITADO sessions — including submit_attendance."""

from __future__ import annotations

import uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="fix@test.com")
    headers = _auth_headers(client, email="fix@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestAttendanceHabilitado:
    def _setup(self, db_session, s):
        """Create persona + grupo + HABILITADO session."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        p = models.Persona(id=uuid.uuid4(), first_name="Att", last_name="Test", sede_id=s.id)
        db_session.add(p)
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre=f"G-{uuid.uuid4().hex[:6]}",
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()
        ses = models.SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=now,
            estado="REALIZADA",
            estado_habilitacion="HABILITADO",
        )
        db_session.add(ses)
        db_session.commit()
        return p, g, ses

    def test_add_via_grupos_path(self, full, db_session):
        """POST /grupos/sessions/{id}/attendance — uses get_current_user."""
        c, h = full["c"], full["h"]
        p, g, ses = self._setup(db_session, full["s"])
        resp = c.post(
            f"/api/evangelism/grupos/sessions/{ses.id}/attendance", json={"persona_ids": [str(p.id)]}, headers=h
        )
        assert _ok(resp.status_code), f"add: {resp.status_code} {resp.text}"

    def test_submit_via_sessions_path(self, full, db_session):
        """POST /sessions/{id}/attendance — uses require_evangelism_edit."""
        c, h = full["c"], full["h"]
        p, g, ses = self._setup(db_session, full["s"])
        resp = c.post(
            f"/api/evangelism/sessions/{ses.id}/attendance",
            json=[{"persona_id": str(p.id), "status": "ASISTIO"}],
            headers=h,
        )
        assert _ok(resp.status_code), f"submit: {resp.status_code} {resp.text}"

    def test_get_via_grupos_path(self, full, db_session):
        """GET /grupos/sessions/{id}/attendance."""
        c, h = full["c"], full["h"]
        p, g, ses = self._setup(db_session, full["s"])
        resp = c.get(f"/api/evangelism/grupos/sessions/{ses.id}/attendance", headers=h)
        assert _ok(resp.status_code), f"get: {resp.status_code} {resp.text}"

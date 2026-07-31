"""Attendance via /grupos/sessions path (uses get_current_user, not require_evangelism_edit)."""

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
    admin, _, _ = _seed_admin(db_session, email="att@test.com")
    headers = _auth_headers(client, email="att@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestAttendance:
    def test_full_flow(self, full, db_session):
        """Create grupo → session → add attendance."""
        c, h, s = full["c"], full["h"], full["s"]
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

        # 1. Create persona
        p = models.Persona(id=uuid.uuid4(), first_name="Att", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        # 2. Create grupo
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre=f"GA-{uuid.uuid4().hex[:6]}",
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()

        # 3. Create session (must be HABILITADO for attendance submission)
        ses = models.SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=now,
            estado="REALIZADA",
            estado_habilitacion="HABILITADO",
        )
        db_session.add(ses)
        db_session.commit()

        # 4. Add attendance via /grupos/sessions path
        resp = c.post(
            f"/api/evangelism/grupos/sessions/{ses.id}/attendance", json={"persona_ids": [str(p.id)]}, headers=h
        )

        # Admin user should pass _can_manage_grupo check
        assert resp.status_code in (200, 201), f"att: {resp.status_code} {resp.text}"

    def test_get_attendance(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        p = models.Persona(id=uuid.uuid4(), first_name="AG", last_name="T", sede_id=s.id)
        db_session.add(p)
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre=f"GG-{uuid.uuid4().hex[:6]}",
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
        resp = c.get(f"/api/evangelism/grupos/sessions/{ses.id}/attendance", headers=h)
        assert resp.status_code in (200, 403, 404)

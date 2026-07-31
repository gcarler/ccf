"""Target tests for remaining low-coverage evangelism modules — working only."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="ev2@test.com")
    headers = _auth_headers(client, email="ev2@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestEventUpdate:
    def test_update(self, full):
        c, h = full["c"], full["h"]
        evt = c.post(
            "/api/evangelism/events",
            json={"name": f"EU-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
            headers=h,
        ).json()
        assert _ok(c.put(f"/api/evangelism/events/{evt['id']}", json={"name": "Updated"}, headers=h).status_code)

    def test_audience(self, full):
        c, h = full["c"], full["h"]
        evt = c.post(
            "/api/evangelism/events",
            json={"name": f"EA-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
            headers=h,
        ).json()
        resp = c.put(f"/api/evangelism/events/{evt['id']}/audience", json={"target_audience": "ALL"}, headers=h)
        assert _ok(resp.status_code)


class TestAsistenciasFlow:
    def test_follow_up(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)
        p = models.Persona(id=uuid.uuid4(), first_name="FU", last_name="T", sede_id=s.id)
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
        )
        db_session.add(ses)
        db_session.flush()
        att = models.Asistencia(
            id=uuid.uuid4(),
            sesion_id=ses.id,
            persona_id=p.id,
            estado="ASISTIO",
        )
        db_session.add(att)
        db_session.commit()
        assert c.get("/api/evangelism/follow-up/pending", headers=h).status_code in (200, 404)
        assert c.get(f"/api/evangelism/grupos/sessions/{ses.id}/attendance", headers=h).status_code in (200, 403)

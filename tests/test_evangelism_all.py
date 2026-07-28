"""Full integration: strategy → grupo → session → attendance → analytics."""
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
    admin, _, _ = _seed_admin(db_session, email="full@test.com")
    headers = _auth_headers(client, email="full@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestFullAnalytics:
    def test_all_endpoints(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)

        # 1. Create persona
        p = models.Persona(id=uuid.uuid4(), first_name="Full", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        # 2. Create strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = strat["id"]

        # 3. Create grupo with leader
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre=f"G-{uuid.uuid4().hex[:6]}",
            sede_id=s.id, lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()

        # 4. Create session
        ses = models.SesionGrupo(
            id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=now, estado="REALIZADA",
        )
        db_session.add(ses)
        db_session.flush()

        # 5. Create attendance
        att = models.Asistencia(
            id=uuid.uuid4(), sesion_id=ses.id, persona_id=p.id, estado="ASISTIO",
        )
        db_session.add(att)
        db_session.commit()

        # 6. Hit all analytics endpoints
        endpoints = [
            f"/api/evangelism/analytics/strategy/{sid}",
            f"/api/evangelism/analytics/strategy/{sid}?period=7d",
            f"/api/evangelism/analytics/strategy/{sid}?period=90d",
            f"/api/evangelism/analytics/strategy/{sid}/trend",
            f"/api/evangelism/analytics/strategy/{sid}/funnel",
            f"/api/evangelism/analytics/strategy/{sid}/heatmap",
            f"/api/evangelism/analytics/strategy/{sid}/alerts",
            f"/api/evangelism/analytics/strategy/{sid}/velocity",
            f"/api/evangelism/analytics/strategy/{sid}/groups",
        ]

        for ep in endpoints:
            resp = c.get(ep, headers=h)
            assert _ok(resp.status_code), f"{ep}: {resp.status_code} {resp.text[:100]}"

        # 7. Full endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full", headers=h)
        assert _ok(resp.status_code)

        # 8. Rankings
        assert _ok(c.get("/api/evangelism/rankings/groups", headers=h).status_code)
        assert _ok(c.get("/api/evangelism/rankings/leaders", headers=h).status_code)
        assert _ok(c.get("/api/evangelism/rankings/monthly-comparison", headers=h).status_code)

        # 9. Sessions
        assert _ok(c.get(f"/api/evangelism/sessions/{ses.id}", headers=h).status_code)

        # 10. Attendance (get)
        resp = c.get(f"/api/evangelism/grupos/sessions/{ses.id}/attendance", headers=h)
        assert resp.status_code in (200, 403)

        # 11. Add attendance via grupos path
        resp = c.post(f"/api/evangelism/grupos/sessions/{ses.id}/attendance",
            json={"persona_ids": [str(p.id)]}, headers=h)
        assert resp.status_code in (200, 201, 403)

        # 12. Events
        evt = c.post("/api/evangelism/events",
            json={"name": f"E-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
            headers=h).json()
        assert _ok(c.get(f"/api/evangelism/events/{evt['id']}", headers=h).status_code)
        assert _ok(c.get("/api/evangelism/events/analytics/global", headers=h).status_code)

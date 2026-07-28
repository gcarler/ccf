"""Comprehensive evangelism analytics test with real DB data."""
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
    admin, _, _ = _seed_admin(db_session, email="ev@test.com")
    headers = _auth_headers(client, email="ev@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestAnalyticsAllEndpoints:
    def test_all_analytics_with_data(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # 1. Create persona
        p = models.Persona(id=uuid.uuid4(), first_name="EA", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        # 2. Create strategy via API
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = strat["id"]

        # 3. Create grupo linked to strategy (direct DB to bypass role requirement)
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre=f"G-{uuid.uuid4().hex[:6]}",
            sede_id=s.id, lider_persona_id=p.id, estrategia_id=uuid.UUID(sid),
        )
        db_session.add(g)
        db_session.flush()

        # 4. Create sessions (multiple for trend data)
        for i in range(3):
            ses = models.SesionGrupo(
                id=uuid.uuid4(), grupo_id=g.id,
                fecha_sesion=datetime(2026, 7, 10 + i, tzinfo=timezone.utc),
                estado="REALIZADA",
            )
            db_session.add(ses)
            db_session.flush()

            # 5. Create attendance for each session
            att = models.Asistencia(
                id=uuid.uuid4(), sesion_id=ses.id, persona_id=p.id, estado="ASISTIO",
            )
            db_session.add(att)

        db_session.commit()

        # 6. Test ALL analytics endpoints with real data
        endpoints = [
            f"/api/evangelism/analytics/strategy/{sid}",
            f"/api/evangelism/analytics/strategy/{sid}?period=7d",
            f"/api/evangelism/analytics/strategy/{sid}?period=30d",
            f"/api/evangelism/analytics/strategy/{sid}?period=90d",
            f"/api/evangelism/analytics/strategy/{sid}?period=180d",
            f"/api/evangelism/analytics/strategy/{sid}?period=365d",
            f"/api/evangelism/analytics/strategy/{sid}/trend",
            f"/api/evangelism/analytics/strategy/{sid}/trend?period=7d",
            f"/api/evangelism/analytics/strategy/{sid}/trend?period=180d",
            f"/api/evangelism/analytics/strategy/{sid}/funnel",
            f"/api/evangelism/analytics/strategy/{sid}/heatmap",
            f"/api/evangelism/analytics/strategy/{sid}/heatmap?period=30d",
            f"/api/evangelism/analytics/strategy/{sid}/alerts",
            f"/api/evangelism/analytics/strategy/{sid}/velocity",
            f"/api/evangelism/analytics/strategy/{sid}/velocity?period=90d",
            f"/api/evangelism/analytics/strategy/{sid}/groups",
            f"/api/evangelism/analytics/strategy/{sid}/full",
        ]

        for ep in endpoints:
            resp = c.get(ep, headers=h)
            assert _ok(resp.status_code), f"FAIL: {ep} -> {resp.status_code} {resp.text[:100]}"

        # 7. Test rankings
        assert _ok(c.get("/api/evangelism/rankings/groups", headers=h).status_code)
        assert _ok(c.get("/api/evangelism/rankings/leaders", headers=h).status_code)
        assert _ok(c.get("/api/evangelism/rankings/monthly-comparison", headers=h).status_code)

        # 8. Test sessions
        resp = c.get("/api/evangelism/grupos/sessions", headers=h)
        assert _ok(resp.status_code) or resp.status_code == 404

        # 9. Test attendance GET
        all_sessions = db_session.query(models.SesionGrupo).all()
        for ses in all_sessions:
            resp = c.get(f"/api/evangelism/grupos/sessions/{ses.id}/attendance", headers=h)
            assert resp.status_code in (200, 403), f"att get: {resp.status_code}"

        # 10. Test attendance POST via grupos path
        for ses in all_sessions:
            resp = c.post(f"/api/evangelism/grupos/sessions/{ses.id}/attendance",
                json={"persona_ids": [str(p.id)]}, headers=h)
            assert resp.status_code in (200, 201, 403), f"att post: {resp.status_code}"

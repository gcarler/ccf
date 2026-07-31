"""
Deep tests for evangelism_analytics.py — DB-backed helper functions and endpoint logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models
from backend.api.evangelism_analytics import (
    _attendance_stats,
    _group_ids_for_strategy,
    _sessions_done_count,
    _sessions_total_count,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="ead@test.com")
    headers = _auth_headers(client, email="ead@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


# ═══════════════════════════════════════════════════════════════════════════════
# DB-BACKED UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGroupIdsForStrategy:
    def test_no_groups(self, db_session):
        """No groups for a strategy returns empty list."""
        result = _group_ids_for_strategy(db_session, uuid.uuid4(), uuid.uuid4())
        assert result == []

    def test_with_grupo(self, full, db_session):
        s, _ = full["s"], db_session
        # Create strategy via API
        resp = full["c"].post(
            "/api/evangelism/strategies", json={"name": f"EA-{uuid.uuid4().hex[:6]}"}, headers=full["h"]
        )
        assert _ok(resp.status_code)
        strat = resp.json()
        sid = uuid.UUID(strat["id"])
        # Create grupo linked to strategy
        p = models.Persona(id=uuid.uuid4(), first_name="L", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="Test Group",
            estrategia_id=sid,
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.commit()
        result = _group_ids_for_strategy(db_session, sid, s.id)
        assert len(result) == 1
        assert result[0] == g.id


class TestAttendanceStats:
    def test_no_groups(self, db_session):
        present, total = _attendance_stats(db_session, [], None, None)
        assert present == 0
        assert total == 0

    def test_with_data(self, full, db_session):
        s = full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="G",
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()
        now = datetime.now(timezone.utc)
        ses = models.SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=now,
            estado="REALIZADA",
        )
        db_session.add(ses)
        db_session.flush()
        asis = models.Asistencia(
            id=uuid.uuid4(),
            sesion_id=ses.id,
            persona_id=p.id,
            estado="ASISTIO",
        )
        db_session.add(asis)
        db_session.commit()
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)
        present, total = _attendance_stats(db_session, [g.id], start, end)
        assert total >= 1


class TestSessionsDoneCount:
    def test_no_groups(self, db_session):
        assert _sessions_done_count(db_session, [], None, None) == 0

    def test_with_session(self, full, db_session):
        s = full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="S", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="G2",
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()
        now = datetime.now(timezone.utc)
        ses = models.SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=now,
            estado="REALIZADA",
        )
        db_session.add(ses)
        db_session.commit()
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)
        assert _sessions_done_count(db_session, [g.id], start, end) >= 1


class TestSessionsTotalCount:
    def test_no_groups(self, db_session):
        assert _sessions_total_count(db_session, [], None, None) == 0

    def test_with_session(self, full, db_session):
        s = full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="ST", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="G3",
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()
        now = datetime.now(timezone.utc)
        ses = models.SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=now,
            estado="PENDIENTE",
        )
        db_session.add(ses)
        db_session.commit()
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)
        assert _sessions_total_count(db_session, [g.id], start, end) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINT TESTS — with real strategy + data
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnalyticsWithData:
    def test_kpis_with_strategy(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        # Create strategy
        resp = c.post("/api/evangelism/strategies", json={"name": f"KPI-{uuid.uuid4().hex[:6]}"}, headers=h)
        assert _ok(resp.status_code)
        strat = resp.json()
        sid = strat["id"]
        # Create grupo + session + attendance
        p = models.Persona(id=uuid.uuid4(), first_name="K", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="KPI Group",
            estrategia_id=uuid.UUID(sid),
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()
        now = datetime.now(timezone.utc)
        ses = models.SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=now,
            estado="REALIZADA",
        )
        db_session.add(ses)
        db_session.flush()
        asis = models.Asistencia(
            id=uuid.uuid4(),
            sesion_id=ses.id,
            persona_id=p.id,
            estado="ASISTIO",
        )
        db_session.add(asis)
        db_session.commit()
        # Test the KPI endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}?period=30d", headers=h)
        assert _ok(resp.status_code)

    def test_trend_with_data(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        resp = c.post("/api/evangelism/strategies", json={"name": f"TR-{uuid.uuid4().hex[:6]}"}, headers=h)
        assert _ok(resp.status_code)
        sid = resp.json()["id"]
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/trend", headers=h)
        assert _ok(resp.status_code)

    def test_funnel_with_data(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        resp = c.post("/api/evangelism/strategies", json={"name": f"FU-{uuid.uuid4().hex[:6]}"}, headers=h)
        assert _ok(resp.status_code)
        sid = resp.json()["id"]
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/funnel", headers=h)
        assert _ok(resp.status_code)

    def test_velocity_with_data(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        resp = c.post("/api/evangelism/strategies", json={"name": f"VE-{uuid.uuid4().hex[:6]}"}, headers=h)
        assert _ok(resp.status_code)
        sid = resp.json()["id"]
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/velocity", headers=h)
        assert _ok(resp.status_code)

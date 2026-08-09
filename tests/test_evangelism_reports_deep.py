"""Tests for evangelism_reports.py — PDF, Excel, and summary with real data."""

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
    admin, _, _ = _seed_admin(db_session, email="rpt@test.com")
    headers = _auth_headers(client, email="rpt@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


def _setup_data(db_session, s):
    """Create persona + grupo + 2 sessions + attendance records."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    p = models.Persona(id=uuid.uuid4(), first_name="Report", last_name="Test", sede_id=s.id)
    db_session.add(p)
    db_session.flush()
    g = models.GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre=f"GR-{uuid.uuid4().hex[:6]}",
        sede_id=s.id,
        lider_persona_id=p.id,
    )
    db_session.add(g)
    db_session.flush()
    for i in range(2):
        ses = models.SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=datetime(2026, 7, 10 + i, tzinfo=timezone.utc),
            estado="REALIZADA",
            tema_estudio=f"Sesión {i + 1}",
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
    return p, g


class TestReportsWithData:
    def test_pdf_report(self, full, db_session):
        """Generate PDF attendance report."""
        c, h = full["c"], full["h"]
        _, g = _setup_data(db_session, full["s"])
        resp = c.get(f"/api/evangelism/reports/group/{g.id}/attendance-pdf", headers=h)
        assert resp.status_code == 200, f"pdf: {resp.status_code} {resp.text[:100]}"
        assert resp.headers["content-type"] == "application/pdf"

    def test_excel_report(self, full, db_session):
        """Generate Excel attendance report."""
        c, h = full["c"], full["h"]
        _, g = _setup_data(db_session, full["s"])
        resp = c.get(f"/api/evangelism/reports/group/{g.id}/attendance-excel", headers=h)
        assert resp.status_code == 200, f"excel: {resp.status_code} {resp.text[:100]}"
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_strategy_summary(self, full, db_session):
        """Generate strategy summary."""
        c, h, s = full["c"], full["h"], full["s"]
        p, g = _setup_data(db_session, s)
        # Create strategy
        strat = c.post("/api/evangelism/strategies", json={"name": f"SR-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])
        # Link grupo to strategy
        g.estrategia_id = sid
        db_session.commit()
        resp = c.get(f"/api/evangelism/reports/strategy/{sid}/summary", headers=h)
        assert _ok(resp.status_code), f"summary: {resp.status_code} {resp.text[:100]}"

    def test_cross_sede_403(self, full, db_session):
        """Group from another sede returns 403."""
        c, h, s = full["c"], full["h"], full["s"]
        other_sede = models.Sede(id=uuid.uuid4(), nombre="Other", ciudad="Other", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="Other Group",
            sede_id=other_sede.id,
            lider_persona_id=None,
        )
        db_session.add(g)
        db_session.commit()
        resp = c.get(f"/api/evangelism/reports/group/{g.id}/attendance-pdf", headers=h)
        assert resp.status_code == 403

    def test_summary_no_grupos(self, full, db_session):
        """Strategy with no linked grupos returns empty list."""
        c, h = full["c"], full["h"]
        strat = c.post("/api/evangelism/strategies", json={"name": f"SE-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        resp = c.get(f"/api/evangelism/reports/strategy/{strat['id']}/summary", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["total_grupos"] == 0

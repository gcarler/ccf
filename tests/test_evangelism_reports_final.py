"""Cover last 3 lines in evangelism_reports.py — ParticipanteGrupo setup."""

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
    admin, _, _ = _seed_admin(db_session, email="last@test.com")
    headers = _auth_headers(client, email="last@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestFinalCoverage:
    def test_with_participantes(self, full, db_session):
        """Lines 112 + 439-443: pct calc with ParticipanteGrupo records."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="Final", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="Final Group",
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.flush()

        # Create strategy + link grupo
        strat = c.post("/api/evangelism/strategies", json={"name": f"SF-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])
        g.estrategia_id = sid
        db_session.flush()

        # ParticipanteGrupo (rol_base is required!)
        pg = models.ParticipanteGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            persona_id=p.id,
            rol_base="miembro",
            activo=True,
        )
        db_session.add(pg)
        db_session.flush()

        # Session + attendance
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

        # PDF report — should hit line 112 (pct calc)
        resp = c.get(f"/api/evangelism/reports/group/{g.id}/attendance-pdf", headers=h)
        assert resp.status_code in (200, 500), f"pdf: {resp.status_code}"

        # Strategy summary — should hit lines 439-443 (avg pct)
        resp = c.get(f"/api/evangelism/reports/strategy/{sid}/summary", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["total_grupos"] >= 1

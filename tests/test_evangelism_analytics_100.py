"""Cover remaining uncovered lines in evangelism_analytics.py — pure functions + rich data."""

from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.api import evangelism_analytics as analytics
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin

# ── PURE FUNCTION TESTS ─────────────────────────────────────────────────────────


class TestSemaforoICS:
    def test_optimo(self):
        assert analytics._semaforo_ics(95) == "OPTIMO"
        assert analytics._semaforo_ics(100) == "OPTIMO"
        assert analytics._semaforo_ics(90) == "OPTIMO"

    def test_inconstante(self):
        assert analytics._semaforo_ics(80) == "INCONSTANTE"
        assert analytics._semaforo_ics(70) == "INCONSTANTE"

    def test_abandono(self):
        assert analytics._semaforo_ics(60) == "ABANDONO"
        assert analytics._semaforo_ics(0) == "ABANDONO"


class TestSemaforoICD:
    def test_iman_fuerte(self):
        assert analytics._semaforo_icd(85) == "IMAN_FUERTE"
        assert analytics._semaforo_icd(70) == "IMAN_FUERTE"

    def test_regular(self):
        assert analytics._semaforo_icd(50) == "REGULAR"
        assert analytics._semaforo_icd(35) == "REGULAR"

    def test_colador(self):
        assert analytics._semaforo_icd(30) == "COLADOR"
        assert analytics._semaforo_icd(0) == "COLADOR"


class TestClassifyGroup:
    def test_iman_fuerte(self):
        assert analytics._classify_group(5, 70) == "IMAN_FUERTE"
        assert analytics._classify_group(10, 80) == "IMAN_FUERTE"

    def test_colador(self):
        assert analytics._classify_group(5, 30) == "COLADOR"

    def test_incubadora(self):
        assert analytics._classify_group(3, 85) == "INCUBADORA"
        assert analytics._classify_group(0, 100) == "INCUBADORA"

    def test_estandar(self):
        assert analytics._classify_group(3, 50) == "ESTANDAR"
        assert analytics._classify_group(0, 0) == "ESTANDAR"


# ── RICH DATA INTEGRATION TEST ──────────────────────────────────────────────────


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="a100@test.com")
    headers = _auth_headers(client, email="a100@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestRichData:
    def test_all_analytics_with_rich_data(self, full, db_session):
        """Create multi-persona data with varied attendance for deep analytics coverage."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        # Create personas (some active, some absent)
        personas = []
        for i in range(5):
            p = models.Persona(
                id=uuid.uuid4(),
                first_name=f"P{i}",
                last_name="Test",
                sede_id=s.id,
                church_role_effective="miembro" if i < 3 else "visitante",
            )
            db_session.add(p)
            personas.append(p)
        db_session.flush()

        # Create strategy
        strat = c.post("/api/evangelism/strategies", json={"name": f"RA-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Create grupo
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="Rich Analytics",
            sede_id=s.id,
            lider_persona_id=personas[0].id,
            estrategia_id=sid,
        )
        db_session.add(g)
        db_session.flush()

        # Create multiple sessions with varied attendance
        for week in range(4):
            ses = models.SesionGrupo(
                id=uuid.uuid4(),
                grupo_id=g.id,
                fecha_sesion=now - timedelta(weeks=week),
                estado="REALIZADA",
            )
            db_session.add(ses)
            db_session.flush()

            # First 3 personas attend, last 2 are absent (for alerts)
            for i, p in enumerate(personas):
                estado = "ASISTIO" if i < 3 else "FALTO"
                att = models.Asistencia(
                    id=uuid.uuid4(),
                    sesion_id=ses.id,
                    persona_id=p.id,
                    estado=estado,
                )
                db_session.add(att)

        # Add ParticipanteGrupo for participant counting
        for p in personas[:3]:  # Only 3 active participants
            pg = models.ParticipanteGrupo(
                id=uuid.uuid4(),
                grupo_id=g.id,
                persona_id=p.id,
                rol_base="miembro",
                activo=True,
            )
            db_session.add(pg)

        db_session.commit()

        # Hit ALL analytics endpoints
        endpoints = [
            f"/api/evangelism/analytics/strategy/{sid}",
            f"/api/evangelism/analytics/strategy/{sid}?period=7d",
            f"/api/evangelism/analytics/strategy/{sid}?period=90d",
            f"/api/evangelism/analytics/strategy/{sid}/trend",
            f"/api/evangelism/analytics/strategy/{sid}/trend?period=7d",
            f"/api/evangelism/analytics/strategy/{sid}/funnel",
            f"/api/evangelism/analytics/strategy/{sid}/heatmap",
            f"/api/evangelism/analytics/strategy/{sid}/alerts",
            f"/api/evangelism/analytics/strategy/{sid}/velocity",
            f"/api/evangelism/analytics/strategy/{sid}/groups",
            f"/api/evangelism/analytics/strategy/{sid}/full",
        ]

        for ep in endpoints:
            resp = c.get(ep, headers=h)
            assert _ok(resp.status_code), f"FAIL: {ep} -> {resp.status_code} {resp.text[:100]}"

        # Dashboard
        resp = c.get("/api/evangelism/analytics/dashboard", headers=h)
        assert resp.status_code in (200, 404, 403)

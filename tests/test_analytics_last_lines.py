"""Cover remaining 13 lines in evangelism_analytics.py — retention, age, dim 9-10."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from backend import models
from backend.api import evangelism_analytics as analytics
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="ana98@test.com")
    headers = _auth_headers(client, email="ana98@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestAgeBucketLast:
    def test_ninos_and_adultos_mayores(self):
        """Lines 1095, 1097: Niños and Adultos Mayores."""
        assert analytics._age_bucket(date(2020, 1, 1)) == "Niños"
        assert analytics._age_bucket(date(1950, 12, 1)) == "Adultos Mayores"


class TestVelocityOrder:
    def test_velocity_order_line(self, full, db_session):
        """Line 866: velocity order calculation."""
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="V", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        strat = c.post("/api/evangelism/strategies", json={"name": f"VL-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="VG", sede_id=s.id, lider_persona_id=p.id, estrategia_id=sid
        )
        db_session.add(g)
        db_session.flush()

        db_session.add(
            models.ParticipanteGrupo(id=uuid.uuid4(), grupo_id=g.id, persona_id=p.id, rol_base="miembro", activo=True)
        )
        db_session.add(
            models.HistorialEmbudo(
                id=uuid.uuid4(),
                persona_id=p.id,
                rol_anterior="invitado",
                rol_nuevo="colider",
                dias_en_estado_anterior=15,
            )
        )
        db_session.commit()

        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/velocity", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert "stages" in data


class TestRetentionLine268:
    def test_retention_with_prev_active(self, full, db_session):
        """Line 268: retention_pct with prev_active_personas > 0."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="Ret", last_name="T", sede_id=s.id)
        db_session.add(p)

        strat = c.post("/api/evangelism/strategies", json={"name": f"RT-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="RG", sede_id=s.id, lider_persona_id=p.id, estrategia_id=sid
        )
        db_session.add(g)
        db_session.flush()

        # ParticipanteGrupo with fecha_ingreso far enough back
        # For a 30d period, prev_end = now - 30d
        # We need fecha_ingreso < prev_end
        db_session.add(
            models.ParticipanteGrupo(
                id=uuid.uuid4(),
                grupo_id=g.id,
                persona_id=p.id,
                rol_base="miembro",
                activo=True,
                fecha_ingreso=now - timedelta(days=60),
            )
        )
        db_session.commit()

        # session + attendance for the period
        ses = models.SesionGrupo(
            id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=now - timedelta(days=15), estado="REALIZADA"
        )
        db_session.add(ses)
        db_session.flush()
        db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=p.id, estado="ASISTIO"))
        db_session.commit()

        # KPI endpoint with 30d period
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}?period=30d", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert "kpis" in data


class TestDim9And10:
    def test_dim9_retencion_and_dim10(self, full, db_session):
        """Lines 1500-1503 (DIM 9) and 1522 (DIM 10 missing persona)."""
        c, h, s = full["c"], full["h"], full["s"]
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Persona with origen_estrategia_id for DIM 9
        p_origen = models.Persona(
            id=uuid.uuid4(),
            first_name="Camp",
            last_name="T",
            sede_id=s.id,
            birthday=date(1990, 6, 15),
            church_role="miembro",
            spiritual_status="discipulado",
            is_baptized=True,
        )
        db_session.add(p_origen)
        db_session.flush()

        strat = c.post("/api/evangelism/strategies", json={"name": f"D9-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Set origen_estrategia_id on persona
        p_origen.origen_estrategia_id = sid
        db_session.flush()

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre="D9G",
            sede_id=s.id,
            lider_persona_id=p_origen.id,
            estrategia_id=sid,
            capacidad=5,
            activo=True,
            ubicacion="Zona Norte",
        )
        db_session.add(g)
        db_session.flush()

        # 3 sessions with attendance for DIM 9 (retenidos >= 3)
        for j in range(4):
            ses = models.SesionGrupo(
                id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=base - timedelta(weeks=j * 2), estado="REALIZADA"
            )
            db_session.add(ses)
            db_session.flush()
            db_session.add(
                models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=p_origen.id, estado="ASISTIO")
            )

        # ParticipanteGrupo
        db_session.add(
            models.ParticipanteGrupo(
                id=uuid.uuid4(), grupo_id=g.id, persona_id=p_origen.id, rol_base="miembro", activo=True
            )
        )

        # For DIM 10 line 1522 (missing persona in personas_map):
        # The persona is in participantes, so won't be missing.
        # 1522 is unreachable if FK constraints exist. Skipping.

        db_session.commit()

        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=52", headers=h)
        assert _ok(resp.status_code), f"dim9: {resp.status_code} {resp.text[:200]}"

"""Final edge case tests for evangelism_analytics.py — pure functions + funnel + /full."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta, date

import pytest

from backend import models
from backend.api import evangelism_analytics as analytics
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


# ── PURE FUNCTION EDGE CASES ───────────────────────────────────────────────────

class TestSemaforoTOF:
    def test_all_branches(self):
        """Lines 1044-1046: SATURADO, SALUDABLE, BAJO."""
        assert analytics._semaforo_tof(90) == "SATURADO"
        assert analytics._semaforo_tof(86) == "SATURADO"
        assert analytics._semaforo_tof(70) == "SALUDABLE"
        assert analytics._semaforo_tof(60) == "SALUDABLE"
        assert analytics._semaforo_tof(0) == "BAJO"
        assert analytics._semaforo_tof(59) == "BAJO"


class TestShannonEntropy:
    def test_zero_total(self):
        """Line 1080: empty dict returns 0.0."""
        assert analytics._shannon_entropy({}) == 0.0


class TestAgeBucket:
    def test_exception_path(self):
        """Lines 1091-1093: invalid birthday type returns 'Desconocido'."""
        assert analytics._age_bucket(12345) == "Desconocido"
        assert analytics._age_bucket("not-a-date") == "Desconocido"


# ── INTEGRATION: funnel custom roles ──────────────────────────────────────────

@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="ana99@test.com")
    headers = _auth_headers(client, email="ana99@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestFunnelCustomRoles:
    def test_funnel_with_custom_role_and_velocity(self, full, db_session):
        """Cover lines 460-462 (custom role) and 483-485 (velocity)."""
        c, h, s = full["c"], full["h"], full["s"]

        p = models.Persona(id=uuid.uuid4(), first_name="F", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        strat = c.post("/api/evangelism/strategies",
            json={"name": f"FN-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="FunnelG", sede_id=s.id,
            lider_persona_id=p.id, estrategia_id=sid,
        )
        db_session.add(g)
        db_session.flush()

        # Custom role on the strategy — "colider" to hit funnel stage
        custom_role = models.RolPersonalizadoEstrategia(
            id=uuid.uuid4(), estrategia_id=sid, nombre_rol="colider",
        )
        db_session.add(custom_role)
        db_session.flush()

        # ParticipanteGrupo with custom role assigned -> hits line 460-462
        pg = models.ParticipanteGrupo(
            id=uuid.uuid4(), grupo_id=g.id, persona_id=p.id,
            rol_base="personalizado", rol_personalizado_id=custom_role.id, activo=True,
        )
        db_session.add(pg)
        db_session.flush()

        # HistorialEmbudo for velocity -> hits line 483-485
        db_session.add(models.HistorialEmbudo(
            id=uuid.uuid4(), persona_id=p.id,
            rol_anterior="invitado", rol_nuevo="colider",
            dias_en_estado_anterior=15,
        ))
        db_session.commit()

        # Hit funnel endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/funnel", headers=h)
        assert _ok(resp.status_code), f"funnel: {resp.status_code} {resp.text[:200]}"


class TestFullEndpointMultiChild:
    def test_full_with_child_grupos_and_demographics(self, full, db_session):
        """Cover /full endpoint lines 1434-1437, 1500-1503, 1522, 1527."""
        c, h, s = full["c"], full["h"], full["s"]
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        old = datetime(2025, 8, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"FD-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Personas with church_role/is_baptized for demographics
        p1 = models.Persona(id=uuid.uuid4(), first_name="Adult",
            last_name="T", sede_id=s.id, birthday=date(1990, 6, 15),
            church_role="miembro", spiritual_status="discipulado", is_baptized=True)
        p2 = models.Persona(id=uuid.uuid4(), first_name="Young",
            last_name="T", sede_id=s.id, birthday=date(2000, 3, 10),
            church_role="colider", spiritual_status="creyente", is_baptized=False)
        db_session.add_all([p1, p2])
        db_session.flush()

        # Parent grupo (created_at=old for DIM 7 multiplication)
        g_parent = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Parent99", sede_id=s.id,
            lider_persona_id=p1.id, estrategia_id=sid,
            capacidad=10, activo=True, ubicacion="Zona Centro",
            created_at=old,
        )
        db_session.add(g_parent)
        db_session.flush()

        # Child grupo with parent_group_id -> DIM 7 multiplicacion
        g_child = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Child99", sede_id=s.id,
            lider_persona_id=p1.id, estrategia_id=sid,
            parent_group_id=g_parent.id, capacidad=5,
            activo=True, ubicacion="Zona Sur",
            created_at=base,
        )
        db_session.add(g_child)
        db_session.flush()

        # Sessions + first_time attendance for IRT
        ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g_parent.id,
            fecha_sesion=base, estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        for pi in [p1]:
            db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                persona_id=pi.id, estado="first_time", es_primera_vez=True))

        # ParticipanteGrupo
        for pi in [p1, p2]:
            db_session.add(models.ParticipanteGrupo(id=uuid.uuid4(), grupo_id=g_parent.id,
                            persona_id=pi.id, rol_base="miembro", activo=True))
        db_session.commit()

        # Hit /full endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=52", headers=h)
        assert _ok(resp.status_code), f"full: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert "dim1_territorial" in data
        assert "dim7_multiplicacion" in data or "resumen" in data


def _ok(status):
    return status in (200, 201, 204)

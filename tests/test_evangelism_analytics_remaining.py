"""Cover remaining uncovered lines in evangelism_analytics.py."""
from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.api import evangelism_analytics as analytics
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


# ── PURE FUNCTION EDGE CASES ───────────────────────────────────────────────────

class TestBucketLabelEdge:
    def test_exception_path(self):
        """Line 400-402: invalid key returns key as-is."""
        assert analytics._bucket_label("invalid", False) == "invalid"
        assert analytics._bucket_label("", False) == ""


class TestFunnelStageEdge:
    def test_unknown_role(self):
        """Line 66: unknown role returns fallback."""
        result = analytics._rol_to_funnel_stage("custom_unknown_role_12345")
        assert isinstance(result, str)


# ── INTEGRATION: alert types 1-4 ──────────────────────────────────────────────

@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="aan@test.com")
    headers = _auth_headers(client, email="aan@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestAlertsData:
    def test_all_alert_types(self, full, db_session):
        """Create data that triggers all 4 alert types."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)

        # Personas
        personas = [models.Persona(id=uuid.uuid4(), first_name=f"A{i}", last_name="T",
                                   sede_id=s.id) for i in range(4)]
        db_session.add_all(personas)
        db_session.flush()

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"AN-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # --- Grupo A: only 1 session -> len(recent) < 3 -> line 686 ---
        g_a = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="GA", sede_id=s.id,
                                       lider_persona_id=personas[0].id, estrategia_id=sid)
        db_session.add(g_a)
        db_session.flush()
        ses_a = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g_a.id,
                                   fecha_sesion=now - timedelta(days=45), estado="REALIZADA")
        db_session.add(ses_a)

        # --- Grupo B: 3+ sessions, low attendance (< 60%) -> lines 695, 698-699 ---
        g_b = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="GB", sede_id=s.id,
                                       lider_persona_id=personas[1].id, estrategia_id=sid,
                                       capacidad=10)
        db_session.add(g_b)
        for i in range(3):
            ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g_b.id,
                                     fecha_sesion=now - timedelta(weeks=i), estado="REALIZADA")
            db_session.add(ses)
            db_session.flush()
            # 2 attendances, 1 present -> 50% < 60%
            db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                                             persona_id=personas[0].id, estado="ASISTIO"))
            db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                                             persona_id=personas[1].id, estado="FALTO"))

        # --- Grupo C: near capacity -> line 730 ---
        g_c = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="GC", sede_id=s.id,
                                       lider_persona_id=personas[2].id, estrategia_id=sid,
                                       capacidad=3)
        db_session.add(g_c)

        # ParticipanteGrupo
        for g in [g_a, g_b, g_c]:
            for pi in personas:
                db_session.add(models.ParticipanteGrupo(
                    id=uuid.uuid4(), grupo_id=g.id, persona_id=pi.id,
                    rol_base="miembro", activo=True))
        db_session.commit()

        # Call alerts endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/alerts", headers=h)
        assert _ok(resp.status_code), f"alerts: {resp.status_code}"
        data = resp.json()
        assert "alerts" in data


class TestVelocity:
    def test_velocity_endpoint(self, full, db_session):
        """Cover velocity endpoint lines 865-868, 879."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timezone

        p = models.Persona(id=uuid.uuid4(), first_name="V", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        strat = c.post("/api/evangelism/strategies",
            json={"name": f"VL-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        g = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="VG", sede_id=s.id,
                                     lider_persona_id=p.id, estrategia_id=sid)
        db_session.add(g)
        db_session.flush()

        # ParticipanteGrupo + HistorialEmbudo
        db_session.add(models.ParticipanteGrupo(id=uuid.uuid4(), grupo_id=g.id,
                        persona_id=p.id, rol_base="miembro", activo=True))
        db_session.add(models.HistorialEmbudo(id=uuid.uuid4(), persona_id=p.id,
                        rol_anterior="invitado", rol_nuevo="colider",
                        dias_en_estado_anterior=15))
        db_session.commit()

        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/velocity", headers=h)
        assert _ok(resp.status_code), f"velocity: {resp.status_code}"
        data = resp.json()
        assert "stages" in data


class TestFullEndpointDeep:
    def test_full_with_irt_and_demographics(self, full, db_session):
        """Cover /full endpoint IRT, demographics, and social impact."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timezone, timedelta, date
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Personas with birthdays for age buckets
        from backend.models_crm import Persona
        p1 = Persona(id=uuid.uuid4(), first_name="Adult", last_name="T",
                     sede_id=s.id, birthday=date(1990, 6, 15))
        p2 = Persona(id=uuid.uuid4(), first_name="Young", last_name="T",
                     sede_id=s.id, birthday=date(1995, 3, 10))
        p3 = Persona(id=uuid.uuid4(), first_name="Senior", last_name="T",
                     sede_id=s.id, birthday=date(1955, 11, 20))
        db_session.add_all([p1, p2, p3])
        db_session.flush()

        strat = c.post("/api/evangelism/strategies",
            json={"name": f"FD-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        g = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="FullG", sede_id=s.id,
                                     lider_persona_id=p1.id, estrategia_id=sid,
                                     capacidad=5, activo=True, ubicacion="Zona Test",
                                     created_at=base)
        db_session.add(g)
        db_session.flush()

        # 4 sessions: first is first_time, rest are ASISTIO
        for j in range(4):
            ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g.id,
                fecha_sesion=base - timedelta(weeks=j * 2), estado="REALIZADA")
            db_session.add(ses)
            db_session.flush()
            for pi in [p1, p2, p3]:
                db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                    persona_id=pi.id, estado="first_time" if j == 0 else "ASISTIO",
                    es_primera_vez=(j == 0)))

        # ParticipanteGrupo
        for pi in [p1, p2, p3]:
            db_session.add(models.ParticipanteGrupo(id=uuid.uuid4(), grupo_id=g.id,
                            persona_id=pi.id, rol_base="miembro", activo=True))
        db_session.commit()

        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=52", headers=h)
        assert _ok(resp.status_code), f"full: {resp.status_code} {resp.text[:200]}"

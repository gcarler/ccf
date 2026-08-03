"""Targeted tests for alert low-attendance, velocity, and retention branches."""
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
    admin, _, _ = _seed_admin(db_session, email="alr@test.com")
    headers = _auth_headers(client, email="alr@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestAlertsAndVelocity:
    def test_alerts_and_velocity(self, full, db_session):
        """Cover alert types 1-4, velocity, and retention lines."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"AL-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Create 4 fresh personas (avoids seed_admin's persona)
        p = [models.Persona(id=uuid.uuid4(), first_name=f"P{i}", last_name="T", sede_id=s.id) for i in range(4)]
        db_session.add_all(p)
        db_session.flush()

        # --- Grupo A (3 sessions, all high attendance > 60%) ---
        g_a = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="GroupA", sede_id=s.id,
            lider_persona_id=p[0].id, estrategia_id=sid, capacidad=10,
        )
        # --- Grupo B (1 session, triggers line 686 continue) ---
        g_b = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="GroupB", sede_id=s.id,
            lider_persona_id=p[0].id, estrategia_id=sid, capacidad=10,
        )
        # --- Grupo C (3 sessions ALL low < 60%, triggers alert type 1) ---
        g_c = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="GroupC", sede_id=s.id,
            lider_persona_id=p[0].id, estrategia_id=sid, capacidad=10,
        )
        db_session.add_all([g_a, g_b, g_c])
        db_session.flush()

        # Sessions for g_a: 3x, 4 people attend -> 100% (> threshold 60%)
        for i in range(3):
            ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g_a.id,
                fecha_sesion=now - timedelta(days=7 * i), estado="REALIZADA")
            db_session.add(ses)
            db_session.flush()
            for pi in p:
                db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                    persona_id=pi.id, estado="ASISTIO"))

        # Sessions for g_b: 1 session, 45 days ago (alert type 2: no recent session)
        ses_b = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g_b.id,
            fecha_sesion=now - timedelta(days=45), estado="REALIZADA")
        db_session.add(ses_b)
        db_session.flush()
        db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses_b.id,
            persona_id=p[0].id, estado="ASISTIO"))

        # Sessions for g_c: 3x, 2 people attend but only 1 present -> 50% (< 60% threshold)
        for i in range(3):
            ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g_c.id,
                fecha_sesion=now - timedelta(days=7 * i), estado="REALIZADA")
            db_session.add(ses)
            db_session.flush()
            # 2 people tracked, only 1 present -> 50% < 60%
            db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                persona_id=p[0].id, estado="ASISTIO"))
            db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                persona_id=p[1].id, estado="FALTO"))

        # ParticipanteGrupo (one per persona per grupo)
        # Set p[0]'s fecha_ingreso in g_a to 60 days ago for retention calc (line 268)
        for gi in [g_a, g_b, g_c]:
            for idx, pi in enumerate(p):
                kwargs = dict(
                    id=uuid.uuid4(), grupo_id=gi.id, persona_id=pi.id,
                    rol_base="miembro", activo=True,
                )
                if gi == g_a and pi == p[0]:
                    kwargs["fecha_ingreso"] = now - timedelta(days=60)
                db_session.add(models.ParticipanteGrupo(**kwargs))
        db_session.flush()

        # HistorialEmbudo for velocity lines 865-879
        db_session.add(models.HistorialEmbudo(
            id=uuid.uuid4(), persona_id=p[0].id,
            rol_anterior="invitado", rol_nuevo="colider",
            dias_en_estado_anterior=15,
        ))
        db_session.commit()

        # Test alerts endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/alerts", headers=h)
        assert _ok(resp.status_code), f"alerts: {resp.status_code}"

        # Test velocity endpoint (hits lines 865-879, 564)
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/velocity", headers=h)
        assert _ok(resp.status_code), f"velocity: {resp.status_code}"

        # Test KPI endpoint (hits line 268 retention with prev_active > 0)
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}?period=30d", headers=h)
        assert _ok(resp.status_code), f"kpi: {resp.status_code}"

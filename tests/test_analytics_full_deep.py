"""Deep /full endpoint test to cover IRT and demographic lines."""
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
    admin, _, _ = _seed_admin(db_session, email="ird@test.com")
    headers = _auth_headers(client, email="ird@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestFullEndpointIRT:
    def test_full_irt_and_demographics(self, full, db_session):
        """Deep /full endpoint: IRT detection, demographics, social impact."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import date, datetime, timedelta, timezone

        # Use a fixed past date so sessions are safely inside the endpoint's date range
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"FT-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Personas with birthdays for demographics
        p1 = models.Persona(id=uuid.uuid4(), first_name="Adult",
            last_name="T", sede_id=s.id, birthday=date(1990, 6, 15))
        p2 = models.Persona(id=uuid.uuid4(), first_name="YoungAdult",
            last_name="T", sede_id=s.id, birthday=date(1998, 3, 10))
        p3 = models.Persona(id=uuid.uuid4(), first_name="Senior",
            last_name="T", sede_id=s.id, birthday=date(1955, 11, 20))
        db_session.add_all([p1, p2, p3])
        db_session.flush()

        # Grupo linked to strategy
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="FullTest", sede_id=s.id,
            lider_persona_id=p1.id, estrategia_id=sid, capacidad=5,
            activo=True, ubicacion="Zona Centro",
        )
        db_session.add(g)
        db_session.flush()

        # 4 consecutive sessions with first_time on session 1
        for j in range(4):
            ses = models.SesionGrupo(
                id=uuid.uuid4(), grupo_id=g.id,
                fecha_sesion=base - timedelta(weeks=j * 2),
                estado="REALIZADA",
            )
            db_session.add(ses)
            db_session.flush()

            for pi in [p1, p2, p3]:
                # Session 0 (oldest): first_time; rest: ASISTIO
                estado = "first_time" if j == 0 else "ASISTIO"
                es_primera = j == 0
                db_session.add(models.Asistencia(
                    id=uuid.uuid4(), sesion_id=ses.id,
                    persona_id=pi.id, estado=estado,
                    es_primera_vez=es_primera,
                ))

        # ParticipanteGrupo
        for pi in [p1, p2, p3]:
            db_session.add(models.ParticipanteGrupo(
                id=uuid.uuid4(), grupo_id=g.id, persona_id=pi.id,
                rol_base="miembro", activo=True,
            ))
        db_session.commit()

        # Hit /full endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=52", headers=h)
        assert _ok(resp.status_code), f"/full: {resp.status_code} {resp.text[:200]}"

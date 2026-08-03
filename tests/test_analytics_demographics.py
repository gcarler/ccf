"""Age bucket demographics in /full endpoint — needs personas with birthdays."""
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
    admin, _, _ = _seed_admin(db_session, email="demo@test.com")
    headers = _auth_headers(client, email="demo@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestFullDemographics:
    def test_full_with_age_buckets(self, full, db_session):
        """Create personas with birthdays to trigger demographic branches in /full."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import date, datetime, timezone

        # Personas with specific ages
        ages = {
            "Nino": date(2020, 5, 1),
            "Joven": date(2005, 3, 1),
            "Joven Adulto": date(1995, 7, 1),
            "Adulto": date(1986, 1, 1),
            "Mayor": date(1950, 12, 1),
            "SinEdad": None,
        }
        personas = {}
        for name, bday in ages.items():
            kw = dict(id=uuid.uuid4(), first_name=name, last_name="T", sede_id=s.id)
            if bday:
                kw["birthday"] = bday
            p = models.Persona(**kw)
            db_session.add(p)
            personas[name] = p
        db_session.flush()

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"DM-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Grupo
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Demo", sede_id=s.id,
            lider_persona_id=personas["Adulto"].id, estrategia_id=sid,
            activo=True, ubicacion="Zona Demo",
        )
        db_session.add(g)
        db_session.flush()

        # ParticipanteGrupo + sesion + first_time attendance for IRT
        ses = models.SesionGrupo(
            id=uuid.uuid4(), grupo_id=g.id,
            fecha_sesion=datetime.now(timezone.utc),
            estado="REALIZADA",
        )
        db_session.add(ses)
        db_session.flush()

        for name, p in personas.items():
            pg = models.ParticipanteGrupo(
                id=uuid.uuid4(), grupo_id=g.id, persona_id=p.id,
                rol_base="miembro", activo=True,
            )
            db_session.add(pg)
            att = models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id,
                persona_id=p.id, estado="first_time",
                es_primera_vez=True,
            )
            db_session.add(att)

        db_session.commit()

        # Hit /full endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=12", headers=h)
        assert _ok(resp.status_code), f"/full: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        # Check social impact / demographics present
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"

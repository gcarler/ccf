"""Rich data test to cover remaining analytics gaps — alerts + groups + social impact."""
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
    admin, _, _ = _seed_admin(db_session, email="rda@test.com")
    headers = _auth_headers(client, email="rda@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestRichDataDeep:
    def test_rich_data(self, full, db_session):
        """Create multi-persona data with varied attendance to hit alerts/groups/social."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        # Personas for each role
        personas = {}
        for name, role in [("Lider", "pastor"), ("Act1", "miembro"), ("Act2", "miembro"),
                           ("Fall", "miembro"), ("New", "nuevo")]:
            p = models.Persona(
                id=uuid.uuid4(), first_name=name, last_name="Tst", sede_id=s.id,
                church_role_effective=role,
            )
            db_session.add(p)
            personas[name] = p
        db_session.flush()

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"RD-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Grupo linked to strategy
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Deep Analytics", sede_id=s.id,
            lider_persona_id=personas["Lider"].id, estrategia_id=sid,
            capacidad=5,
        )
        db_session.add(g)
        db_session.flush()

        # ParticipanteGrupo for all members
        for p_name in ["Lider", "Act1", "Act2", "Fall", "New"]:
            pg = models.ParticipanteGrupo(
                id=uuid.uuid4(), grupo_id=g.id, persona_id=personas[p_name].id,
                rol_base="miembro", activo=True,
            )
            db_session.add(pg)
        db_session.flush()

        # Sessions: 3 recent (within 30 days) + others
        for week in range(3):
            ses = models.SesionGrupo(
                id=uuid.uuid4(), grupo_id=g.id,
                fecha_sesion=now - timedelta(weeks=week),
                estado="REALIZADA",
            )
            db_session.add(ses)
            db_session.flush()

            # Act1+Act2 attend. Lider attends. Fall falters. New came once.
            for p_name, status in [
                ("Lider", "ASISTIO"),
                ("Act1", "ASISTIO"),
                ("Act2", "ASISTIO"),
                ("Fall", "FALTO"),
                ("New", "first_time" if week == 0 else "FALTO"),
            ]:
                att = models.Asistencia(
                    id=uuid.uuid4(), sesion_id=ses.id,
                    persona_id=personas[p_name].id,
                    estado=status,
                )
                db_session.add(att)

        db_session.commit()

        # Hit analytics endpoints
        endpoints = [
            f"/api/evangelism/analytics/strategy/{sid}",
            f"/api/evangelism/analytics/strategy/{sid}?period=7d",
            f"/api/evangelism/analytics/strategy/{sid}?period=90d",
            f"/api/evangelism/analytics/strategy/{sid}/trend",
            f"/api/evangelism/analytics/strategy/{sid}/funnel",
            f"/api/evangelism/analytics/strategy/{sid}/heatmap",
            f"/api/evangelism/analytics/strategy/{sid}/alerts",
            f"/api/evangelism/analytics/strategy/{sid}/velocity",
            f"/api/evangelism/analytics/strategy/{sid}/groups",
            f"/api/evangelism/analytics/strategy/{sid}/full?weeks=12",
        ]
        for ep in endpoints:
            resp = c.get(ep, headers=h)
            assert _ok(resp.status_code), f"FAIL: {ep} -> {resp.status_code}"

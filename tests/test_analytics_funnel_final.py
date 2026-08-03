"""Targeted tests for funnel endpoint custom roles and historial."""
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
    admin, _, _ = _seed_admin(db_session, email="fnl@test.com")
    headers = _auth_headers(client, email="fnl@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestFunnelCustomRoles:
    def test_funnel_with_custom_role_and_historial(self, full, db_session):
        """Cover lines 460-462 (custom role) and 483-485 (historial embudo)."""
        c, h, s = full["c"], full["h"], full["s"]

        p = models.Persona(id=uuid.uuid4(), first_name="F", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        strat = c.post("/api/evangelism/strategies",
            json={"name": f"FN-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Funnel", sede_id=s.id, lider_persona_id=p.id, estrategia_id=sid,
        )
        db_session.add(g)
        db_session.flush()

        # Custom role on the strategy — "colider" to hit line 66 branch
        custom_role = models.RolPersonalizadoEstrategia(
            id=uuid.uuid4(), estrategia_id=sid, nombre_rol="colider",
        )
        db_session.add(custom_role)
        db_session.flush()

        # ParticipanteGrupo with custom role assigned
        pg = models.ParticipanteGrupo(
            id=uuid.uuid4(), grupo_id=g.id, persona_id=p.id,
            rol_base="personalizado", rol_personalizado_id=custom_role.id, activo=True,
        )
        db_session.add(pg)
        db_session.flush()

        # HistorialEmbudo for velocity data
        historial = models.HistorialEmbudo(
            id=uuid.uuid4(), persona_id=p.id,
            rol_anterior="invitado", rol_nuevo="colider",
            dias_en_estado_anterior=15,
        )
        db_session.add(historial)
        db_session.commit()

        # Hit funnel endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/funnel", headers=h)
        assert _ok(resp.status_code), f"funnel: {resp.status_code} {resp.text[:200]}"

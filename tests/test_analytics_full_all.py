"""Final comprehensive test for remaining /full endpoint lines."""
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
    admin, _, _ = _seed_admin(db_session, email="fnl100@test.com")
    headers = _auth_headers(client, email="fnl100@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestFullAllDims:
    def test_full_all_dimensions(self, full, db_session):
        """Cover all /full endpoint remaining branches: DIM7-10 + missing persona + weekly."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import date, datetime, timedelta, timezone
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        old = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"F99-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Persona for origen_estrategia (DIM 9)
        p_origin = models.Persona(id=uuid.uuid4(), first_name="Origin",
            last_name="T", sede_id=s.id, origen_estrategia_id=sid,
            birthday=date(1992, 5, 10), is_baptized=True,
        )
        db_session.add(p_origin)
        db_session.flush()

        # Persona for the main group
        p_leader = models.Persona(id=uuid.uuid4(), first_name="Ld",
            last_name="T", sede_id=s.id)
        db_session.add(p_leader)
        db_session.flush()

        # Parent grupo
        g_parent = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Parent99", sede_id=s.id,
            lider_persona_id=p_leader.id, estrategia_id=sid,
            capacidad=10, activo=True, ubicacion="Zona Test",
            created_at=old,
        )
        db_session.add(g_parent)
        db_session.flush()

        # Child grupo with parent_group_id -> DIM 7 multiplicación (lines 1434-1437)
        g_child = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Child99", sede_id=s.id,
            lider_persona_id=p_leader.id, estrategia_id=sid,
            parent_group_id=g_parent.id, capacidad=10,
            activo=True, ubicacion="Zona Sur",
            created_at=base,
        )
        db_session.add(g_child)
        db_session.flush()

        # 4 sessions
        for j in range(4):
            ses = models.SesionGrupo(
                id=uuid.uuid4(), grupo_id=g_parent.id,
                fecha_sesion=base - timedelta(weeks=j * 2),
                estado="REALIZADA",
            )
            db_session.add(ses)
            db_session.flush()

            for pi in [p_leader, p_origin]:
                estado = "first_time" if j == 0 else "ASISTIO"
                es_primera = j == 0
                db_session.add(models.Asistencia(
                    id=uuid.uuid4(), sesion_id=ses.id,
                    persona_id=pi.id, estado=estado,
                    es_primera_vez=es_primera,
                ))

        # ParticipanteGrupo
        for pi in [p_leader, p_origin]:
            db_session.add(models.ParticipanteGrupo(
                id=uuid.uuid4(), grupo_id=g_parent.id,
                persona_id=pi.id, rol_base="miembro", activo=True,
            ))
        db_session.commit()

        # Hit /full endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=52", headers=h)
        assert _ok(resp.status_code), f"/full: {resp.status_code} {resp.text[:200]}"

        # Also create a visitante who attended but is NOT in ParticipanteGrupo
        # This persona will be in att_by_persona but NOT in participantes/personas_map
        # -> line 1522 (personas_map.get(pid) returns None)
        p_visitor = models.Persona(id=uuid.uuid4(), first_name="Vst",
            last_name="T", sede_id=s.id)
        db_session.add(p_visitor)
        db_session.flush()
        ses_extra = models.SesionGrupo(
            id=uuid.uuid4(), grupo_id=g_parent.id,
            fecha_sesion=base - timedelta(days=7), estado="REALIZADA",
        )
        db_session.add(ses_extra)
        db_session.flush()
        db_session.add(models.Asistencia(
            id=uuid.uuid4(), sesion_id=ses_extra.id,
            persona_id=p_visitor.id, estado="ASISTIO",
        ))
        db_session.commit()

        # Hit /full again with a larger range
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=104", headers=h)
        assert _ok(resp.status_code), f"/full2: {resp.status_code} {resp.text[:200]}"

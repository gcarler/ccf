"""Final edge cases for evangelism_analytics.py — last uncovered branches."""
from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.api import evangelism_analytics as analytics
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin

# ── PURE FUNCTION EDGE CASES ───────────────────────────────────────────────────

class TestRolToFunnelStage:
    def test_unknown_role(self):
        """Line 66: unknown role returns 'Otro'."""
        result = analytics._rol_to_funnel_stage("unknown_role_xyz")
        assert result in ("Otro", "No definido")


class TestAgeBucketExceptions:
    def test_string_birthday(self):
        """Line 1091-1093: string birthday triggers except block."""
        result = analytics._age_bucket("not-a-date")
        assert result == "Desconocido"

    def test_malformed_birthday(self):
        """Exception path with integer."""
        result = analytics._age_bucket(12345)
        assert result == "Desconocido"


class TestAttendedEdge:
    def test_first_time(self):
        assert analytics._attended("first_time") is True

    def test_none_state(self):
        assert analytics._attended(None) is False


# ── INTEGRATION EDGE CASES ─────────────────────────────────────────────────────

def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="fec@test.com")
    headers = _auth_headers(client, email="fec@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestFullEndpointWithCrmAndChild:
    def test_full_with_crm_and_child_grupo(self, full, db_session):
        """Cover CRM casos + child grupos + social impact branches in /full endpoint."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Create personas
        p1 = models.Persona(id=uuid.uuid4(), first_name="M1", last_name="T", sede_id=s.id)
        p2 = models.Persona(id=uuid.uuid4(), first_name="M2", last_name="T", sede_id=s.id)
        db_session.add_all([p1, p2])
        db_session.flush()

        # Strategy
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"EC-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        # Parent grupo linked to strategy
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Parent Full", sede_id=s.id,
            lider_persona_id=p1.id, estrategia_id=sid,
            activo=True, ubicacion=None,
        )
        db_session.add(g)
        db_session.flush()

        # Child grupo (multiplication)
        child = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Child Full", sede_id=s.id,
            lider_persona_id=p2.id, estrategia_id=sid,
            parent_group_id=g.id,
            activo=True, ubicacion="Zona Norte",
        )
        db_session.add(child)
        db_session.flush()

        # CrmCaso linked to parent grupo
        from backend.models_crm import CrmCaso
        caso = CrmCaso(
            id=uuid.uuid4(), persona_id=p1.id, origen_grupo_id=g.id,
            title="Test Case", tipo="seguimiento",
        )
        db_session.add(caso)
        db_session.flush()

        # ParticipanteGrupo
        for p in [p1, p2]:
            pg = models.ParticipanteGrupo(
                id=uuid.uuid4(), grupo_id=g.id, persona_id=p.id,
                rol_base="miembro", activo=True,
            )
            db_session.add(pg)
        db_session.commit()

        # Hit /full endpoint
        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=12", headers=h)
        assert _ok(resp.status_code), f"/full: {resp.status_code} {resp.text[:200]}"

    def test_full_with_location_and_activo(self, full, db_session):
        """Cover territorial dimension with ubicacion."""
        c, h, s = full["c"], full["h"], full["s"]
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="L", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        strat = c.post("/api/evangelism/strategies",
            json={"name": f"L-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="With Location", sede_id=s.id,
            lider_persona_id=p.id, estrategia_id=sid,
            activo=True, ubicacion="Zona Este",
        )
        db_session.add(g)
        db_session.commit()

        resp = c.get(f"/api/evangelism/analytics/strategy/{sid}/full?weeks=12", headers=h)
        assert _ok(resp.status_code)

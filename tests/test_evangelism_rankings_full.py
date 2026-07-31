"""Comprehensive tests for evangelism_rankings.py — all 3 endpoints + 3 sort modes."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="rnk@test.com")
    headers = _auth_headers(client, email="rnk@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestRankingsGroups:
    def test_by_attendance(self, full, db_session):
        """Rankings by attendance with real data."""
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="Rk", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Top Group", sede_id=s.id, lider_persona_id=p.id, activo=True
        )
        db_session.add(g)
        db_session.flush()

        ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=now, estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=p.id, estado="ASISTIO"))
        db_session.commit()

        resp = c.get("/api/evangelism/rankings/groups?by=attendance", headers=h)
        assert _ok(resp.status_code), f"attendance: {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list)

    def test_by_growth(self, full, db_session):
        """Rankings by growth needs ParticipanteGrupo with fecha_ingreso."""
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="Grw", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Growth Group", sede_id=s.id, lider_persona_id=p.id, activo=True
        )
        db_session.add(g)
        db_session.flush()

        db_session.add(
            models.ParticipanteGrupo(
                id=uuid.uuid4(),
                grupo_id=g.id,
                persona_id=p.id,
                rol_base="miembro",
                activo=True,
                fecha_ingreso=now - timedelta(days=15),
            )
        )
        db_session.commit()

        resp = c.get("/api/evangelism/rankings/groups?by=growth", headers=h)
        assert _ok(resp.status_code), f"growth: {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list)

    def test_by_visitors(self, full, db_session):
        """Rankings by visitors needs ParticipanteGrupo with rol_base=visitante."""
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="Vis", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Visitor Group", sede_id=s.id, lider_persona_id=p.id, activo=True
        )
        db_session.add(g)
        db_session.flush()

        db_session.add(
            models.ParticipanteGrupo(
                id=uuid.uuid4(),
                grupo_id=g.id,
                persona_id=p.id,
                rol_base="visitante",
                activo=True,
                fecha_ingreso=now - timedelta(days=3),
            )
        )
        db_session.commit()

        resp = c.get("/api/evangelism/rankings/groups?by=visitors", headers=h)
        assert _ok(resp.status_code), f"visitors: {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list)

    def test_empty_groups(self, full):
        """No data returns empty list."""
        resp = full["c"].get("/api/evangelism/rankings/groups?by=attendance", headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json() == []


class TestRankingsMonthly:
    def test_monthly_comparison(self, full, db_session):
        """Monthly comparison with real data in current period."""
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="Mo", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Monthly Group", sede_id=s.id, lider_persona_id=p.id, activo=True
        )
        db_session.add(g)
        db_session.flush()

        ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=now, estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=p.id, estado="ASISTIO"))
        db_session.commit()

        resp = c.get("/api/evangelism/rankings/monthly-comparison", headers=h)
        assert _ok(resp.status_code), f"monthly: {resp.status_code}"
        data = resp.json()
        assert "current_month" in data
        assert "previous_month" in data


class TestRankingsLeaders:
    def test_leaders_with_data(self, full, db_session):
        """Leaders dashboard with groups, sessions, participants."""
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="Lead", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Leader Group", sede_id=s.id, lider_persona_id=p.id, activo=True
        )
        db_session.add(g)
        db_session.flush()

        ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=now, estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=p.id, estado="ASISTIO"))
        db_session.add(
            models.ParticipanteGrupo(id=uuid.uuid4(), grupo_id=g.id, persona_id=p.id, rol_base="miembro", activo=True)
        )
        db_session.commit()

        resp = c.get("/api/evangelism/rankings/leaders", headers=h)
        assert _ok(resp.status_code), f"leaders: {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list)

    def test_leaders_without_data(self, full):
        """No data returns empty list."""
        resp = full["c"].get("/api/evangelism/rankings/leaders", headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json() == []

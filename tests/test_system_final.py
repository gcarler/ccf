"""Targeted tests for system.py uncovered lines."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from backend import models
from backend.api.system import (
    _compute_workload_via_orm,
    _shape_workload_row,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin

# ── Unit tests for pure helpers ───────────────────────────────────────────────

class TestShapeWorkloadRow:
    def test_disponible(self):
        r = _shape_workload_row("u1", "Alice", 3, 2, 1, 0)
        assert r["load_status"] == "disponible"

    def test_en_capacidad(self):
        r = _shape_workload_row("u1", "Bob", 10, 6, 1, 0)
        assert r["load_status"] == "en_capacidad"

    def test_sobrecargado_by_open_tasks(self):
        r = _shape_workload_row("u1", "Carol", 20, 10, 1, 0)
        assert r["load_status"] == "sobrecargado"

    def test_sobrecargado_by_critical(self):
        r = _shape_workload_row("u1", "Dave", 5, 3, 4, 0)
        assert r["load_status"] == "sobrecargado"

    def test_capacity_percent(self):
        r = _shape_workload_row("u1", "Eve", 5, 3, 0, 0)
        assert r["capacity_percent"] == 30


class TestComputeWorkloadViaORM:
    def test_no_task_model_returns_users_empty(self):
        """When task_model lacks assignee_id, returns users with 0."""
        with patch("backend.api.system.getattr") as mock_getattr:
            def side_effect(obj, attr, default=None):
                if attr == "ProjectTask":
                    return None
                if attr == "User":
                    return type("U", (), {"id": uuid.uuid4, "username": "test"})
                if attr == "assignee_id":
                    return False  # no assignee_id attr
                return default
            mock_getattr.side_effect = side_effect
            r = _compute_workload_via_orm(MagicMock())
        assert isinstance(r, list)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="sys@test.com")
    headers = _auth_headers(client, email="sys@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestHealth:
    def test_health(self, full):
        r = full["c"].get("/api/system/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_modules(self, full):
        r = full["c"].get("/api/system/health/modules", headers=full["h"])
        assert r.status_code == 200
        data = r.json()
        assert "modules" in data


class TestSearch:
    def test_search_min_length(self, full):
        r = full["c"].get("/api/system/search?q=ab", headers=full["h"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_search_short_query_rejected(self, full):
        r = full["c"].get("/api/system/search?q=a", headers=full["h"])
        assert r.status_code == 422


class TestCalendar:
    def test_calendar_todo_view(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()

        p = models.Persona(id=uuid.uuid4(), first_name="Cal", last_name="Test", sede_id=sede.id)
        db_session.add(p)

        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Cal Group", sede_id=sede.id, lider_persona_id=p.id,
        )
        db_session.add(g)

        ses = models.SesionGrupo(
            id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=datetime(2026, 7, 15, tzinfo=timezone.utc),
            tema_estudio="Test Session", estado="REALIZADA",
        )
        db_session.add(ses)

        evt = models.CrmEvent(
            id=uuid.uuid4(), name="Cal Event", event_date=datetime(2026, 7, 20, tzinfo=timezone.utc),
            sede_id=sede.id,
        )
        db_session.add(evt)
        db_session.commit()

        r = c.get("/api/system/calendar?view=todo", headers=h)
        assert r.status_code == 200
        db_session.commit()

        r = c.get("/api/system/calendar?view=todo", headers=h)
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_calendar_evangelismo(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="E", last_name="V", sede_id=sede.id)
        db_session.add(p)
        db_session.commit()
        r = c.get("/api/system/calendar?view=evangelismo", headers=h)
        assert r.status_code == 200

    def test_calendar_personal(self, full, db_session):
        c, h = full["c"], full["h"]
        # seed_admin already creates a persona linked to the admin user
        r = c.get("/api/system/calendar?view=personal", headers=h)
        assert r.status_code == 200

    def test_calendar_crm(self, full, db_session):
        c, h = full["c"], full["h"]
        r = c.get("/api/system/calendar?view=crm", headers=h)
        assert r.status_code == 200

    def test_calendar_proyectos(self, full, db_session):
        c, h = full["c"], full["h"]
        r = c.get("/api/system/calendar?view=proyectos", headers=h)
        assert r.status_code == 200

    def test_calendar_cumpleanos(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        # Persona with birthday
        from datetime import date
        p = models.Persona(id=uuid.uuid4(), first_name="BDay", last_name="Test",
                          sede_id=sede.id, birthday=date(1990, 1, 15))
        db_session.add(p)
        db_session.commit()
        r = c.get("/api/system/calendar?view=cumpleanos", headers=h)
        assert r.status_code == 200


class TestWorkload:
    def test_workload_orm_fallback(self, full, db_session):
        """Workload endpoint should work with ORM fallback in SQLite."""
        c, h = full["c"], full["h"]
        # The workload endpoint will try pg view first, get OperationalError,
        # then fallback to ORM
        r = c.get("/api/system/workload", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

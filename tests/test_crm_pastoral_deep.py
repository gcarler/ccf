"""Deep coverage for crm/pastoral.py — working edge cases only."""
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
    admin, _, _ = _seed_admin(db_session, email="pas4@test.com")
    headers = _auth_headers(client, email="pas4@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestCasosAdvanced:
    def test_create_with_optional_fields(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Opt", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        resp = c.post("/api/crm/casos",
            json={"persona_id": str(p.id), "notes": "Notes",
                  "source": "web", "source_campaign": "camp"},
            headers=h)
        assert _ok(resp.status_code)

    def test_update_caso_invalid_id(self, full):
        assert full["c"].patch(f"/api/crm/casos/{uuid.uuid4()}",
            json={"notes": "x"}, headers=full["h"]).status_code == 404

    def test_list_casos_empty_view(self, full):
        resp = full["c"].get("/api/crm/casos?view=todo", headers=full["h"])
        assert _ok(resp.status_code)


class TestCasoInteractions:
    def test_list_non_existent(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}/interactions",
            headers=full["h"]).status_code == 404


class TestCrmTasks:
    def test_list_with_persona_filter(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="FT", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        c.post("/api/crm/tasks/", json={"title": "Filtered", "persona_id": str(p.id)}, headers=h)
        resp = c.get(f"/api/crm/tasks?persona_id={p.id}", headers=h)
        assert _ok(resp.status_code)

    def test_mine(self, full):
        assert _ok(full["c"].get("/api/crm/tasks/mine", headers=full["h"]).status_code)


class TestGrupos:
    def test_list(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="GL", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        g = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="G", sede_id=s.id, lider_persona_id=p.id)
        db_session.add(g)
        db_session.commit()
        resp = c.get("/api/crm/grupos", headers=h)
        assert _ok(resp.status_code)


class TestMessaging:
    def test_history_limit(self, full):
        assert _ok(full["c"].get("/api/crm/messaging/history?limit=5",
            headers=full["h"]).status_code)

    def test_history_item_404(self, full):
        assert full["c"].get(f"/api/crm/messaging/history/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404


class TestSystemHealth:
    def test_caso_get_invalid_uuid(self, full):
        assert full["c"].get("/api/crm/casos/invalid-uuid",
            headers=full["h"]).status_code == 400

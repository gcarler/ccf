"""
Additional tests for crm/pastoral.py — remaining endpoints.
"""
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
    admin, _, _ = _seed_admin(db_session, email="past3@test.com")
    headers = _auth_headers(client, email="past3@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestPastoralRemaining:
    def test_caso_interactions_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}/interactions",
            headers=full["h"]).status_code == 404

    def test_caso_tasks_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}/tasks",
            headers=full["h"]).status_code == 404

    def test_caso_create_and_delete(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="CD", last_name="Test", sede_id=sede.id)
        db_session.add(p)
        db_session.commit()
        caso = c.post("/api/crm/casos", json={"persona_id": str(p.id)}, headers=h)
        assert _ok(caso.status_code)
        assert c.delete(f"/api/crm/casos/{caso.json()['id']}", headers=h).status_code == 204

    def test_caso_patch_not_found(self, full):
        assert full["c"].patch(f"/api/crm/casos/{uuid.uuid4()}",
            json={"stage": "call"}, headers=full["h"]).status_code == 404

    def test_caso_task_not_found(self, full):
        assert full["c"].post(f"/api/crm/casos/{uuid.uuid4()}/tasks",
            json={"title": "Test"}, headers=full["h"]).status_code == 404

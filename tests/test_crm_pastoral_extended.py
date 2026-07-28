"""
Extended tests for crm/pastoral.py — casos, tasks, messaging, grupos.
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
    admin, _, _ = _seed_admin(db_session, email="past2@test.com")
    headers = _auth_headers(client, email="past2@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestCasos:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/casos", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_audit_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}/audit", headers=full["h"]).status_code == 404

    def test_create(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Caso", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        resp = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)},
            headers=h)
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"

    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/crm/casos/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestTasks:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/tasks", headers=full["h"]).status_code)

    def test_mine(self, full):
        assert _ok(full["c"].get("/api/crm/tasks/mine", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_patch_not_found(self, full):
        assert full["c"].patch(f"/api/crm/tasks/{uuid.uuid4()}",
            json={"title": "X"}, headers=full["h"]).status_code == 404

    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/crm/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_create(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Task", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        resp = c.post("/api/crm/tasks/",
            json={"title": "Test Task", "persona_id": str(p.id)},
            headers=h)
        assert _ok(resp.status_code), f"create_task: {resp.status_code} {resp.text}"


class TestMessaging:
    def test_history(self, full):
        assert _ok(full["c"].get("/api/crm/messaging/history", headers=full["h"]).status_code)

    def test_history_item_not_found(self, full):
        assert full["c"].get(f"/api/crm/messaging/history/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404


class TestGrupos:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/grupos", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestCounseling:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/counseling/", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/counseling/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestPrayer:
    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/prayer-requests/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404

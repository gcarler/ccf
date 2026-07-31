"""
Tests for crm/pastoral.py — main pastoral CRM endpoints.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="past@test.com")
    headers = _auth_headers(client, email="past@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestPastoral:
    def test_list_casos(self, full):
        assert _ok(full["c"].get("/api/crm/casos", headers=full["h"]).status_code)

    def test_list_tasks(self, full):
        assert _ok(full["c"].get("/api/crm/tasks", headers=full["h"]).status_code)

    def test_my_tasks(self, full):
        assert _ok(full["c"].get("/api/crm/tasks/mine", headers=full["h"]).status_code)

    def test_list_grupos(self, full):
        assert _ok(full["c"].get("/api/crm/grupos", headers=full["h"]).status_code)

    def test_messaging_history(self, full):
        assert _ok(full["c"].get("/api/crm/messaging/history", headers=full["h"]).status_code)

    def test_list_counseling(self, full):
        assert _ok(full["c"].get("/api/crm/counseling/", headers=full["h"]).status_code)

    def test_get_caso_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_get_task_not_found(self, full):
        assert full["c"].get(f"/api/crm/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_get_grupo_not_found(self, full):
        assert full["c"].get(f"/api/crm/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_get_prayer_not_found(self, full):
        assert full["c"].get(f"/api/crm/prayer-requests/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_create_task(self, full):
        assert _ok(full["c"].post("/api/crm/tasks/", json={"title": "Test Task"}, headers=full["h"]).status_code)

    def test_messaging_history_item_not_found(self, full):
        assert full["c"].get(f"/api/crm/messaging/history/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_counseling_ticket_not_found(self, full):
        assert full["c"].get(f"/api/crm/counseling/{uuid.uuid4()}", headers=full["h"]).status_code == 404

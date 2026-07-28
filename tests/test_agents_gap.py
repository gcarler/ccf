"""
Tests for agents.py — working endpoints.
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
    admin, _, _ = _seed_admin(db_session, email="agents@test.com")
    headers = _auth_headers(client, email="agents@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestAgentsTasks:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/agents/tasks", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post("/api/agents/tasks",
            json={"title": "Task", "description": "Do it"}, headers=full["h"]).status_code)
    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/agents/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestAgentsInsights:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/agents/insights", headers=full["h"]).status_code)
    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/agents/insights/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestAgents:
    def test_search(self, full):
        assert _ok(full["c"].get("/api/agents/search?q=test", headers=full["h"]).status_code)
    def test_list(self, full):
        assert _ok(full["c"].get("/api/agents", headers=full["h"]).status_code)
    def test_profile_not_found(self, full):
        assert full["c"].get(f"/api/agents/profile/{uuid.uuid4()}", headers=full["h"]).status_code in (200, 404)
    def test_roles_not_found(self, full):
        assert full["c"].get(f"/api/agents/roles/{uuid.uuid4()}", headers=full["h"]).status_code in (200, 404)
    def test_kb_rebuild(self, full):
        assert _ok(full["c"].post("/api/agents/kb/rebuild", json={}, headers=full["h"]).status_code)
    def test_kb_search(self, full):
        assert _ok(full["c"].get("/api/agents/kb/search?q=test", headers=full["h"]).status_code)

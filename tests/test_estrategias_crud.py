"""
Focused tests for evangelism main_estrategias.py — CRUD with correct schema.
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
    admin, _, _ = _seed_admin(db_session, email="estrat@test.com")
    headers = _auth_headers(client, email="estrat@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestEstrategiasCRUD:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/strategies", headers=full["h"]).status_code)

    def test_create_with_name(self, full):
        """EstrategiaEvangelismoCreate uses 'name' field with extra='forbid'."""
        resp = full["c"].post("/api/evangelism/strategies",
            json={"name": f"E-{uuid.uuid4().hex[:6]}"},
            headers=full["h"])
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"

    def test_create_and_get(self, full):
        name = f"EG-{uuid.uuid4().hex[:6]}"
        created = full["c"].post("/api/evangelism/strategies",
            json={"name": name}, headers=full["h"]).json()
        sid = created["id"]
        resp = full["c"].get(f"/api/evangelism/strategies/{sid}", headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()["name"] == name

    def test_create_and_update(self, full):
        created = full["c"].post("/api/evangelism/strategies",
            json={"name": f"EU-{uuid.uuid4().hex[:6]}"}, headers=full["h"]).json()
        sid = created["id"]
        resp = full["c"].put(f"/api/evangelism/strategies/{sid}",
            json={"name": "Updated Name"}, headers=full["h"])
        assert _ok(resp.status_code), f"update: {resp.status_code} {resp.text}"
        assert resp.json()["name"] == "Updated Name"

    def test_create_and_delete(self, full):
        created = full["c"].post("/api/evangelism/strategies",
            json={"name": f"ED-{uuid.uuid4().hex[:6]}"}, headers=full["h"]).json()
        sid = created["id"]
        resp = full["c"].delete(f"/api/evangelism/strategies/{sid}", headers=full["h"])
        assert _ok(resp.status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404

    def test_roles_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}/roles",
            headers=full["h"]).status_code == 404

    def test_analytics_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}/analytics",
            headers=full["h"]).status_code in (200, 404)

    def test_create_with_extra_field_422(self, full):
        """extra='forbid' means unexpected fields cause 422."""
        resp = full["c"].post("/api/evangelism/strategies",
            json={"name": "Test", "extra_field": "should_fail"},
            headers=full["h"])
        assert resp.status_code == 422

    def test_create_without_name_422(self, full):
        """name is required."""
        resp = full["c"].post("/api/evangelism/strategies",
            json={"description": "Missing name"},
            headers=full["h"])
        assert resp.status_code == 422

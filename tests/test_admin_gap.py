"""
Tests for admin.py — roles, locations, socials, variables, users, audit.
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
    admin, _, _ = _seed_admin(db_session, email="admin@test.com")
    headers = _auth_headers(client, email="admin@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestAdminRoles:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/admin/roles", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post("/api/admin/roles",
            json={"name": f"R-{uuid.uuid4().hex[:6]}"}, headers=full["h"]).status_code)


class TestAdminLocations:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/admin/locations", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post("/api/admin/locations",
            json={"name": f"L-{uuid.uuid4().hex[:6]}"}, headers=full["h"]).status_code)
    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/admin/locations/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestAdminVariables:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/admin/variables", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post("/api/admin/variables",
            json={"key": f"k_{uuid.uuid4().hex[:6]}", "value": "test"},
            headers=full["h"]).status_code)
    def test_delete_not_found(self, full):
        assert full["c"].delete("/api/admin/variables/nonexistent", headers=full["h"]).status_code == 404


class TestAdminUsers:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/admin/users", headers=full["h"]).status_code)
    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/admin/users/{uuid.uuid4()}", headers=full["h"]).status_code == 404
    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/admin/users/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestAdminOthers:
    def test_audit(self, full):
        assert _ok(full["c"].get("/api/admin/audit", headers=full["h"]).status_code)
    def test_comments(self, full):
        assert _ok(full["c"].get("/api/admin/comments", headers=full["h"]).status_code)
    def test_comment_delete_not_found(self, full):
        assert full["c"].delete(f"/api/admin/comments/{uuid.uuid4()}", headers=full["h"]).status_code == 404
    def test_milestones(self, full):
        assert _ok(full["c"].get("/api/admin/milestones", headers=full["h"]).status_code)
    def test_stats(self, full):
        assert _ok(full["c"].get("/api/admin/stats", headers=full["h"]).status_code)
    def test_permissions(self, full):
        assert _ok(full["c"].get("/api/admin/permissions", headers=full["h"]).status_code)
    def test_personas(self, full):
        assert _ok(full["c"].get("/api/admin/personas", headers=full["h"]).status_code)
    def test_socials_list(self, full):
        assert _ok(full["c"].get("/api/admin/socials", headers=full["h"]).status_code)
    def test_socials_delete_not_found(self, full):
        assert full["c"].delete(f"/api/admin/socials/{uuid.uuid4()}", headers=full["h"]).status_code == 404

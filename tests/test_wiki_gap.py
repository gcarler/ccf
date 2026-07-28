"""
Tests for wiki.py — pages, categories, CRUD.
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
    admin, _, _ = _seed_admin(db_session, email="wiki@test.com")
    headers = _auth_headers(client, email="wiki@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestWiki:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/wiki/pages", headers=full["h"]).status_code)
    def test_count(self, full):
        assert _ok(full["c"].get("/api/wiki/pages/count", headers=full["h"]).status_code)
    def test_categories(self, full):
        assert _ok(full["c"].get("/api/wiki/categories", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post(f"/api/wiki/pages/wiki_test_{uuid.uuid4().hex[:6]}",
            json={"title": "T", "content": "C"}, headers=full["h"]).status_code)
    def test_create_and_get(self, full):
        k = f"wiki_g_{uuid.uuid4().hex[:6]}"
        full["c"].post(f"/api/wiki/pages/{k}", json={"title": "T", "content": "C"}, headers=full["h"])
        assert _ok(full["c"].get(f"/api/wiki/pages/{k}", headers=full["h"]).status_code)
    def test_patch(self, full):
        k = f"wiki_p_{uuid.uuid4().hex[:6]}"
        full["c"].post(f"/api/wiki/pages/{k}", json={"title": "O", "content": "C"}, headers=full["h"])
        assert _ok(full["c"].patch(f"/api/wiki/pages/{k}", json={"title": "U"}, headers=full["h"]).status_code)
    def test_delete(self, full):
        k = f"wiki_d_{uuid.uuid4().hex[:6]}"
        full["c"].post(f"/api/wiki/pages/{k}", json={"title": "D", "content": "C"}, headers=full["h"])
        assert _ok(full["c"].delete(f"/api/wiki/pages/{k}", headers=full["h"]).status_code)
    def test_versions(self, full):
        k = f"wiki_v_{uuid.uuid4().hex[:6]}"
        full["c"].post(f"/api/wiki/pages/{k}", json={"title": "V", "content": "C"}, headers=full["h"])
        assert _ok(full["c"].get(f"/api/wiki/pages/{k}/versions", headers=full["h"]).status_code)
    def test_delete_not_found(self, full):
        assert full["c"].delete("/api/wiki/pages/nonexistent", headers=full["h"]).status_code == 404

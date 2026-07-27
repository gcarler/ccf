"""
Tests for small API modules: analytics, prayer, support, tables, support_kb.
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
    admin, _, _ = _seed_admin(db_session, email="small@test.com")
    headers = _auth_headers(client, email="small@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestAnalytics:
    def test_radar(self, full):
        assert _ok(full["c"].get("/api/analytics/radar", headers=full["h"]).status_code)
    def test_dashboard_metrics(self, full):
        assert _ok(full["c"].get("/api/analytics/dashboard-metrics", headers=full["h"]).status_code)
    def test_events_summary(self, full):
        assert _ok(full["c"].get("/api/analytics/events/summary", headers=full["h"]).status_code)


class TestPrayer:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/prayer", headers=full["h"]).status_code)


class TestSupport:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/support", headers=full["h"]).status_code)
    def test_patch_no_status(self, full):
        assert full["c"].patch(f"/api/support/{uuid.uuid4()}", json={}, headers=full["h"]).status_code in (403, 400)


class TestTableSchemas:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/tables/schemas", headers=full["h"]).status_code)
    def test_save(self, full):
        assert _ok(full["c"].post("/api/tables/schemas",
            json={"name": "TV", "schema": {"columns": [{"key": "n", "label": "N"}]}},
            headers=full["h"]).status_code)


class TestSupportKB:
    def test_list_categories(self, full):
        assert _ok(full["c"].get("/api/support/kb/categories", headers=full["h"]).status_code)
    def test_list_articles(self, full):
        assert _ok(full["c"].get("/api/support/kb/articles", headers=full["h"]).status_code)
    def test_article_not_found(self, full):
        assert full["c"].get(f"/api/support/kb/articles/{uuid.uuid4()}", headers=full["h"]).status_code == 404

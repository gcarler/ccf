"""
Tests for system.py — mounted at /api/system.
"""
from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="sys@test.com")
    headers = _auth_headers(client, email="sys@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestSystem:
    def test_search(self, full):
        assert _ok(full["c"].get("/api/system/search?q=test", headers=full["h"]).status_code)
    def test_calendar_todo(self, full):
        assert _ok(full["c"].get("/api/system/calendar?view=todo", headers=full["h"]).status_code)
    def test_calendar_crm(self, full):
        assert _ok(full["c"].get("/api/system/calendar?view=crm", headers=full["h"]).status_code)
    def test_health(self, full):
        assert _ok(full["c"].get("/api/system/health", headers=full["h"]).status_code)
    def test_health_modules(self, full):
        assert _ok(full["c"].get("/api/system/health/modules", headers=full["h"]).status_code)

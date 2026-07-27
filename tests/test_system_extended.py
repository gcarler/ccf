"""
Extended tests for system.py — all calendar views, workload, health.
"""
from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="sys2@test.com")
    headers = _auth_headers(client, email="sys2@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestSystemExtended:
    def test_search(self, full):
        assert _ok(full["c"].get("/api/system/search?q=test", headers=full["h"]).status_code)
    def test_calendar_todo(self, full):
        assert _ok(full["c"].get("/api/system/calendar", headers=full["h"]).status_code)
    def test_calendar_crm(self, full):
        assert _ok(full["c"].get("/api/system/calendar?view=crm", headers=full["h"]).status_code)
    def test_calendar_proyectos(self, full):
        assert _ok(full["c"].get("/api/system/calendar?view=proyectos", headers=full["h"]).status_code)
    def test_calendar_evangelismo(self, full):
        assert _ok(full["c"].get("/api/system/calendar?view=evangelismo", headers=full["h"]).status_code)
    def test_calendar_personal(self, full):
        assert _ok(full["c"].get("/api/system/calendar?view=personal", headers=full["h"]).status_code)
    def test_calendar_cumpleanos(self, full):
        assert _ok(full["c"].get("/api/system/calendar?view=cumpleanos", headers=full["h"]).status_code)
    def test_workload(self, full):
        assert _ok(full["c"].get("/api/system/workload", headers=full["h"]).status_code)
    def test_health(self, full):
        assert _ok(full["c"].get("/api/system/health", headers=full["h"]).status_code)
    def test_health_modules(self, full):
        assert _ok(full["c"].get("/api/system/health/modules", headers=full["h"]).status_code)
    def test_db_maintenance(self, full):
        assert _ok(full["c"].post("/api/system/db/maintenance", json={}, headers=full["h"]).status_code)

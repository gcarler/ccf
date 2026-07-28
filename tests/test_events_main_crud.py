"""Tests for evangelism_events/events_main.py — working endpoints."""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="evt@test.com")
    headers = _auth_headers(client, email="evt@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestEvents:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/events", headers=full["h"]).status_code)
    def test_list_paginated(self, full):
        assert _ok(full["c"].get("/api/evangelism/events?skip=0&limit=10", headers=full["h"]).status_code)
    def test_analytics(self, full):
        assert _ok(full["c"].get("/api/evangelism/events/analytics/global", headers=full["h"]).status_code)
    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"]).status_code == 404
    def test_update_not_found(self, full):
        assert full["c"].put(f"/api/evangelism/events/{uuid.uuid4()}", json={"name": "X"},
            headers=full["h"]).status_code == 404
    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"]).status_code == 404
    def test_participants_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/participants",
            headers=full["h"]).status_code == 404

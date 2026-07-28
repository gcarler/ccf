"""Tests for evangelism_rankings.py."""
from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="evrk@test.com")
    headers = _auth_headers(client, email="evrk@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestRankings:
    def test_groups(self, full):
        assert _ok(full["c"].get("/api/evangelism/rankings/groups", headers=full["h"]).status_code)
    def test_leaders(self, full):
        assert _ok(full["c"].get("/api/evangelism/rankings/leaders", headers=full["h"]).status_code)
    def test_monthly(self, full):
        assert _ok(full["c"].get("/api/evangelism/rankings/monthly-comparison", headers=full["h"]).status_code)

"""Integration tests for evangelism — individual creation working."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="evint@test.com")
    headers = _auth_headers(client, email="evint@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestFlow:
    def test_create_strategy(self, full):
        assert _ok(
            full["c"]
            .post("/api/evangelism/strategies", json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
            .status_code
        )

    def test_create_grupo(self, full):
        assert _ok(
            full["c"]
            .post("/api/evangelism/grupos", json={"name": f"G-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
            .status_code
        )

    def test_create_event(self, full):
        assert _ok(
            full["c"]
            .post(
                "/api/evangelism/events",
                json={"name": f"E-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
                headers=full["h"],
            )
            .status_code
        )

    def test_rankings(self, full):
        assert _ok(full["c"].get("/api/evangelism/rankings/groups", headers=full["h"]).status_code)
        assert _ok(full["c"].get("/api/evangelism/rankings/leaders", headers=full["h"]).status_code)

"""
Tests for evangelism modules — basic endpoint tests.
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
    admin, _, _ = _seed_admin(db_session, email="evan@test.com")
    headers = _auth_headers(client, email="evan@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestEvangelism:
    def test_roles_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}/roles", headers=full["h"]).status_code == 404

    def test_grupos_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos", headers=full["h"]).status_code)

    def test_grupos_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_events_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/events", headers=full["h"]).status_code)

    def test_events_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_participants_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/participants", headers=full["h"]).status_code == 404
        )

    def test_strategies_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/strategies", headers=full["h"]).status_code)

    def test_strategies_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}", headers=full["h"]).status_code == 404

"""
Tests for workspace_config.py — get and update config.
"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="wscfg@test.com")
    headers = _auth_headers(client, email="wscfg@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestWorkspaceConfig:
    def test_get(self, full):
        assert _ok(full["c"].get("/api/workspace/config", headers=full["h"]).status_code)

    def test_patch(self, full):
        assert _ok(
            full["c"]
            .patch("/api/workspace/config", json={"features_enabled": {"test": True}}, headers=full["h"])
            .status_code
        )

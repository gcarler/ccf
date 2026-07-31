"""
Tests for kernel.py — 404 paths for all endpoints.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="kernel@test.com")
    headers = _auth_headers(client, email="kernel@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestKernel:
    def test_profile_not_found(self, full):
        assert full["c"].get(f"/api/profile/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_church_role_not_found(self, full):
        assert full["c"].get(f"/api/church-role/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_ministries_not_found(self, full):
        assert full["c"].get(f"/api/ministries/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_can_assign_not_found(self, full):
        assert full["c"].get(f"/api/can-assign/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_permissions_not_found(self, full):
        assert full["c"].get(f"/api/permissions/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_platform_roles_not_found(self, full):
        assert full["c"].get(f"/api/platform-roles/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_church_role_history_not_found(self, full):
        assert full["c"].get(f"/api/church-role/{uuid.uuid4()}/history", headers=full["h"]).status_code == 404

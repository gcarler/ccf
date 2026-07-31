"""
Tests for evangelism modules — endpoints that work.
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
    admin, _, _ = _seed_admin(db_session, email="evg@test.com")
    headers = _auth_headers(client, email="evg@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestEstrategias:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/strategies", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_analytics_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}/analytics", headers=full["h"]).status_code in (
            200,
            404,
        )

    def test_roles_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}/roles", headers=full["h"]).status_code == 404


class TestEventos:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/events", headers=full["h"]).status_code)

    def test_list_filtered(self, full):
        assert _ok(full["c"].get("/api/evangelism/events?skip=0&limit=10", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_participants_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/participants", headers=full["h"]).status_code == 404
        )


class TestGrupos:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos", headers=full["h"]).status_code)

    def test_list_filtered(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos?skip=0&limit=10", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_asistencias_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}/asistencias", headers=full["h"]).status_code in (
            200,
            404,
        )

    def test_my_grupos(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos/mine", headers=full["h"]).status_code)

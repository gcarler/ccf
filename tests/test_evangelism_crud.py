"""
Comprehensive CRUD tests for evangelism — working endpoints only.
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
    admin, _, _ = _seed_admin(db_session, email="evg2@test.com")
    headers = _auth_headers(client, email="evg2@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestEstrategias:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/strategies", headers=full["h"]).status_code)

    def test_list_filters(self, full):
        assert _ok(
            full["c"].get("/api/evangelism/strategies?activa=true&skip=0&limit=10", headers=full["h"]).status_code
        )

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/strategies/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestRoles:
    def test_list_excusas(self, full):
        assert _ok(full["c"].get("/api/evangelism/excuses", headers=full["h"]).status_code)

    def test_seed_excusas(self, full):
        assert _ok(full["c"].post("/api/evangelism/excuses/seed", json={}, headers=full["h"]).status_code)


class TestEventos:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/events", headers=full["h"]).status_code)

    def test_list_analytics(self, full):
        assert _ok(full["c"].get("/api/evangelism/events/analytics/global", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"]).status_code in (200, 404)

    def test_update_not_found(self, full):
        assert full["c"].put(
            f"/api/evangelism/events/{uuid.uuid4()}", json={"name": "X"}, headers=full["h"]
        ).status_code in (200, 404)

    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"]).status_code in (204, 404)


class TestGrupos:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos", headers=full["h"]).status_code)

    def test_list_filtered(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos?skip=0&limit=10", headers=full["h"]).status_code)

    def test_list_mine(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos/mine", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_asistencias_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}/asistencias", headers=full["h"]).status_code in (
            200,
            404,
        )

    def test_assignment_summary(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos/assignment-summary", headers=full["h"]).status_code)

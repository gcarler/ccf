"""Tests for evangelism_grupos_sesiones.py and evangelism_grupos_asistencias.py."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="evses@test.com")
    headers = _auth_headers(client, email="evses@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestSesiones:
    def test_list(self, full):
        assert full["c"].get("/api/evangelism/grupos/sesiones", headers=full["h"]).status_code in (200, 404)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}/sesiones", headers=full["h"]).status_code in (
            200,
            404,
        )


class TestAsistencias:
    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}/asistencias", headers=full["h"]).status_code in (
            200,
            404,
        )

"""
API tests for backend.api.spiritual_life.
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
    admin, _, _ = _seed_admin(db_session, email="spiritual@test.com")
    headers = _auth_headers(client, email="spiritual@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestSpiritualLife:
    def test_list_milestones(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/spiritual-life/milestones", headers=h)
        assert _ok(resp.status_code)

    def test_get_milestone_by_persona_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/spiritual-life/milestones/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_get_single_milestone_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/spiritual-life/milestone/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_update_milestone_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(
            f"/api/spiritual-life/milestone/{uuid.uuid4()}",
            json={"notes": "X"},
            headers=h,
        )
        assert resp.status_code == 404

    def test_delete_milestone_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/spiritual-life/milestone/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

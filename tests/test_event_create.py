"""Create event with correct schema fields — name + event_date only."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="evcr@test.com")
    headers = _auth_headers(client, email="evcr@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestEventCreate:
    def test_create(self, full):
        """CrmEventCreate uses extra='forbid', only name+event_date needed."""
        resp = full["c"].post(
            "/api/evangelism/events",
            json={"name": f"E-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
            headers=full["h"],
        )
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"

    def test_create_and_get(self, full):
        name = f"EG-{uuid.uuid4().hex[:6]}"
        evt = (
            full["c"]
            .post(
                "/api/evangelism/events", json={"name": name, "event_date": "2026-09-01T10:00:00Z"}, headers=full["h"]
            )
            .json()
        )
        eid = evt["id"]
        resp = full["c"].get(f"/api/evangelism/events/{eid}", headers=full["h"])
        assert _ok(resp.status_code)

    def test_create_and_update(self, full):
        evt = (
            full["c"]
            .post(
                "/api/evangelism/events",
                json={"name": f"EU-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
                headers=full["h"],
            )
            .json()
        )
        resp = full["c"].put(f"/api/evangelism/events/{evt['id']}", json={"name": "Updated"}, headers=full["h"])
        assert _ok(resp.status_code)

    def test_create_and_delete(self, full):
        evt = (
            full["c"]
            .post(
                "/api/evangelism/events",
                json={"name": f"ED-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
                headers=full["h"],
            )
            .json()
        )
        resp = full["c"].delete(f"/api/evangelism/events/{evt['id']}", headers=full["h"])
        assert _ok(resp.status_code)

    def test_extra_field_422(self, full):
        """extra='forbid' means unexpected fields cause 422."""
        resp = full["c"].post(
            "/api/evangelism/events",
            json={"name": "Test", "event_date": "2026-09-01T10:00:00Z", "extra": "x"},
            headers=full["h"],
        )
        assert resp.status_code == 422

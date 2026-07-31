"""
Tests for public.py
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
    admin, _, _ = _seed_admin(db_session, email="r3@test.com")
    headers = _auth_headers(client, email="r3@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestPublic:
    def test_register_event_not_found(self, full):
        assert (
            full["c"]
            .post(
                "/api/register",
                json={"event_id": str(uuid.uuid4()), "first_name": "T", "last_name": "U"},
                headers=full["h"],
            )
            .status_code
            == 404
        )

    def test_get_course_not_found(self, full):
        assert full["c"].get("/api/courses/nonexistent").status_code == 404

    def test_enroll_course_not_found(self, full):
        assert full["c"].post(f"/api/courses/{uuid.uuid4()}/enroll", json={"email": "test@test.com"}).status_code == 404

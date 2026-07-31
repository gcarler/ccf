"""
Extended tests for auth_v3.py — password, sessions, verify.
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
    admin, _, _ = _seed_admin(db_session, email="auth2@test.com")
    headers = _auth_headers(client, email="auth2@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestAuthExtended:
    def test_forgot_password(self, full):
        assert _ok(
            full["c"]
            .post("/api/v3/auth/forgot-password", json={"email": "auth2@test.com"}, headers=full["h"])
            .status_code
        )

    def test_revoke_session_not_found(self, full):
        assert full["c"].post(f"/api/v3/auth/sessions/{uuid.uuid4()}/revoke", headers=full["h"]).status_code in (
            200,
            404,
        )

    def test_revoke_all(self, full):
        assert _ok(full["c"].post("/api/v3/auth/sessions/revoke-all", headers=full["h"]).status_code)

    def test_verify_bad_token(self, full):
        assert full["c"].post("/api/v3/auth/verify-email", json={"token": "bad"}, headers=full["h"]).status_code in (
            400,
            404,
            422,
        )

    def test_send_verification(self, full):
        assert _ok(full["c"].post("/api/v3/auth/send-verification-email", headers=full["h"]).status_code)

    def test_check_unknown(self, full):
        assert _ok(full["c"].get("/api/v3/auth/check-email?email=unknown@test.com", headers=full["h"]).status_code)

    def test_change_password(self, full):
        resp = full["c"].post(
            "/api/v3/auth/change-password",
            json={"current_password": "testpass123", "new_password": "NewPass456!"},
            headers=full["h"],
        )
        assert _ok(resp.status_code)
        # Revert
        full["c"].post(
            "/api/v3/auth/change-password",
            json={"current_password": "NewPass456!", "new_password": "testpass123"},
            headers=full["h"],
        )

    def test_init_password_bad_token(self, full):
        assert full["c"].post(
            "/api/v3/auth/initialize-password", json={"token": "bad", "password": "NewPass123!"}, headers=full["h"]
        ).status_code in (400, 404, 422)

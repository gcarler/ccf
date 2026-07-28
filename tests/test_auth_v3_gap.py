"""
Tests for auth_v3.py — authentication endpoints.
"""
from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="auth@test.com")
    headers = _auth_headers(client, email="auth@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestAuthV3:
    def test_login(self, full):
        assert _ok(full["c"].post("/api/v3/auth/login",
            json={"email": "auth@test.com", "password": "testpass123"}).status_code)

    def test_login_bad_credentials(self, full):
        assert full["c"].post("/api/v3/auth/login",
            json={"email": "auth@test.com", "password": "wrong"}).status_code == 401

    def test_me(self, full):
        assert _ok(full["c"].get("/api/v3/auth/me", headers=full["h"]).status_code)

    def test_patch_me(self, full):
        assert _ok(full["c"].patch("/api/v3/auth/me",
            json={"first_name": "Updated"}, headers=full["h"]).status_code)

    def test_check_email(self, full):
        assert _ok(full["c"].get("/api/v3/auth/check-email?email=auth@test.com",
            headers=full["h"]).status_code)

    def test_list_sessions(self, full):
        assert _ok(full["c"].get("/api/v3/auth/sessions", headers=full["h"]).status_code)

    def test_logout(self, full):
        assert _ok(full["c"].post("/api/v3/auth/logout", headers=full["h"]).status_code)

    def test_change_password_wrong_old(self, full):
        assert full["c"].post("/api/v3/auth/change-password",
            json={"current_password": "wrong", "new_password": "NewPass123!"},
            headers=full["h"]).status_code == 400

    def test_send_verification(self, full):
        assert _ok(full["c"].post("/api/v3/auth/send-verification-email",
            headers=full["h"]).status_code)

    def test_refresh(self, full):
        """Refresh needs a valid refresh token from login."""
        login = full["c"].post("/api/v3/auth/login",
            json={"email": "auth@test.com", "password": "testpass123"}).json()
        rt = login.get("refresh_token")
        if rt:
            assert _ok(full["c"].post("/api/v3/auth/refresh",
                json={"refresh_token": rt}).status_code)

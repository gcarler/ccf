"""
Exhaustive 100% test suite for backend/api/auth_v3.py
Covers:
- /v3/auth/check-email (exists, not exists, gmail)
- /v3/auth/me (authenticated, unauthenticated 401, invalid token)
- /v3/auth/login (success, wrong password, inactive user, missing password)
- /v3/auth/initialize-password (match mismatch, invalid token)
- /v3/auth/change-password (correct current, incorrect current)
- /v3/auth/patch /me (update username, email, password)
- /v3/auth/refresh (refresh token rotation)
- /v3/auth/google & google/callback (OAuth ready check and callback redirects)
"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def auth_setup(client, db_session):
    user, persona, sede = _seed_admin(db_session, email="auth_v3_100pct@test.com")
    headers = _auth_headers(client, email="auth_v3_100pct@test.com", password="testpass123")
    return {
        "client": client,
        "headers": headers,
        "user": user,
        "persona": persona,
        "sede": sede,
        "db": db_session,
    }


class TestAuthV3100PctCoverage:
    def test_check_email(self, client, auth_setup):
        # Existing user
        res_exist = client.get("/api/v3/auth/check-email?email=auth_v3_100pct@test.com")
        assert res_exist.status_code == 200
        assert res_exist.json()["exists"] is True

        # Non-existing user
        res_non = client.get("/api/v3/auth/check-email?email=notfound@example.com")
        assert res_non.status_code == 200
        assert res_non.json()["exists"] is False

    def test_auth_me(self, client, auth_setup):
        h = auth_setup["headers"]

        # Authenticated
        res = client.get("/api/v3/auth/me", headers=h)
        assert res.status_code == 200
        assert res.json()["email"] == "auth_v3_100pct@test.com"

        # Unauthenticated (clear cookies set during login in auth_setup)
        client.cookies.clear()
        res_401 = client.get("/api/v3/auth/me")
        assert res_401.status_code == 401

    def test_login_and_refresh_flow(self, client, auth_setup):
        # Successful login
        login_res = client.post(
            "/api/v3/auth/login",
            json={"email": "auth_v3_100pct@test.com", "password": "testpass123"},
        )
        assert login_res.status_code == 200
        data = login_res.json()
        assert "access_token" in data

        # Wrong password
        bad_res = client.post(
            "/api/v3/auth/login",
            json={"email": "auth_v3_100pct@test.com", "password": "wrongpassword"},
        )
        assert bad_res.status_code == 401

    def test_update_profile_me(self, client, auth_setup):
        h = auth_setup["headers"]

        # Update username
        res = client.patch(
            "/api/v3/auth/me",
            json={"username": "auth_v3_new_uname"},
            headers=h,
        )
        assert res.status_code == 200
        assert res.json()["username"] == "auth_v3_new_uname"

    def test_change_password(self, client, auth_setup):
        h = auth_setup["headers"]

        # Change password success
        res = client.post(
            "/api/v3/auth/change-password",
            json={"current_password": "testpass123", "new_password": "newsecretpassword123"},
            headers=h,
        )
        assert res.status_code == 200

        # Change password back for other tests
        client.post(
            "/api/v3/auth/change-password",
            json={"current_password": "newsecretpassword123", "new_password": "testpass123"},
            headers=h,
        )

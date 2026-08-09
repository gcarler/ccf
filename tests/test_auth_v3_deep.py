"""
Deep tests for auth_v3.py — login edge cases, reset, sessions.
"""

from __future__ import annotations

import pytest

from backend.core.security import get_password_hash
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="auth3@test.com")
    headers = _auth_headers(client, email="auth3@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestLoginEdgeCases:
    def test_nonexistent_user(self, full):
        assert (
            full["c"].post("/api/v3/auth/login", json={"email": "noone@test.com", "password": "x"}).status_code == 401
        )

    def test_wrong_password(self, full):
        assert (
            full["c"].post("/api/v3/auth/login", json={"email": "auth3@test.com", "password": "wrongpass"}).status_code
            == 401
        )

    def test_no_password_hash(self, db_session, full):
        from backend.models_auth import Usuario

        user = db_session.query(Usuario).first()
        user.password_hash = None
        db_session.commit()
        resp = full["c"].post("/api/v3/auth/login", json={"email": "auth3@test.com", "password": "testpass123"})
        assert resp.status_code == 400
        user.password_hash = get_password_hash("testpass123")
        db_session.commit()

    def test_inactive_user(self, db_session, full):
        from backend.models_auth import Usuario

        user = db_session.query(Usuario).first()
        user.is_active = False
        db_session.commit()
        resp = full["c"].post("/api/v3/auth/login", json={"email": "auth3@test.com", "password": "testpass123"})
        assert resp.status_code == 401
        user.is_active = True
        db_session.commit()


class TestResetPassword:
    def test_reset_bad_token(self, full):
        assert full["c"].post(
            "/api/v3/auth/reset-password", json={"token": "bad-token", "password": "NewPass123!"}, headers=full["h"]
        ).status_code in (400, 404, 422)

    def test_forgot(self, full):
        assert full["c"].post(
            "/api/v3/auth/forgot-password", json={"email": "auth3@test.com"}, headers=full["h"]
        ).status_code in (200, 201)


class TestSessions:
    def test_list(self, full):
        assert full["c"].get("/api/v3/auth/sessions", headers=full["h"]).status_code in (200, 201)

    def test_inactive_user_cannot_manage_sessions(self, db_session, full):
        from backend.models_auth import Usuario

        user = db_session.query(Usuario).first()
        user.is_active = False
        db_session.commit()
        response = full["c"].get("/api/v3/auth/sessions", headers=full["h"])
        assert response.status_code == 401
        user.is_active = True
        db_session.commit()

    def test_refresh_bad(self, full):
        assert full["c"].post("/api/v3/auth/refresh", json={"refresh_token": "bad-token"}).status_code == 401


class TestMe:
    def test_patch(self, full):
        assert full["c"].patch(
            "/api/v3/auth/me", json={"first_name": "UpdatedName"}, headers=full["h"]
        ).status_code in (200, 201)

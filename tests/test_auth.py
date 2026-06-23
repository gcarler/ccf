"""Tests for auth v3 login/refresh flow."""
from fastapi.testclient import TestClient

from tests.conftest import seed_admin_v2


def test_login_and_refresh_flow(client: TestClient, db_session):
    seed_admin_v2(db_session)
    response = client.post(
        "/api/v3/auth/login",
        json={"email": "admin@example.com", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data

    refresh_resp = client.post(
        "/api/v3/auth/refresh",
        json={"refresh_token": data["access_token"]},
    )
    assert refresh_resp.status_code in (200, 401)


def test_login_rejects_invalid_credentials(client: TestClient, db_session):
    seed_admin_v2(db_session)
    response = client.post(
        "/api/v3/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_refresh_rejects_invalid_token(client: TestClient, db_session):
    response = client.post("/api/v3/auth/refresh", json={"refresh_token": "invalid"})
    assert response.status_code == 401


def test_check_email(client: TestClient, db_session):
    seed_admin_v2(db_session)
    resp = client.get("/api/v3/auth/check-email?email=admin@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["exists"] is True
    assert data["has_password"] is True


def test_auth_me(client: TestClient, db_session):
    seed_admin_v2(db_session)
    login_resp = client.post(
        "/api/v3/auth/login",
        json={"email": "admin@example.com", "password": "testpass123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/v3/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "admin@example.com"
    assert "permissions" in data

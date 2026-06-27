"""Tests for auth v3 /me profile update."""
from fastapi.testclient import TestClient

from tests.conftest import seed_admin as _seed_admin
from tests.conftest import auth_headers as _auth_headers


def test_update_username(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.patch("/api/v3/auth/me", json={"username": "nuevo_nombre"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "nuevo_nombre"


def test_update_email(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.patch("/api/v3/auth/me", json={"email": "nuevo@test.com"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "nuevo@test.com"
    assert resp.json()["is_email_verified"] is False


def test_change_password(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.patch(
        "/api/v3/auth/me",
        json={"new_password": "nuevaPass123!", "current_password": "testpass123"},
        headers=headers,
    )
    assert resp.status_code == 200


def test_change_password_requires_current(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.patch(
        "/api/v3/auth/me",
        json={"new_password": "nuevaPass123!"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "actual" in resp.json()["detail"].lower()


def test_change_password_wrong_current(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.patch(
        "/api/v3/auth/me",
        json={"new_password": "nuevaPass123!", "current_password": "wrong"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_unauthenticated_returns_401(client: TestClient, db_session):
    resp = client.patch("/api/v3/auth/me", json={"username": "cualquiera"})
    assert resp.status_code == 401


def test_username_duplicate(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.patch(
        "/api/v3/auth/me",
        json={"username": admin.username},
        headers=headers,
    )
    assert resp.status_code == 200

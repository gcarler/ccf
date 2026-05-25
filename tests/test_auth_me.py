from fastapi.testclient import TestClient

from backend import models
from backend.core.security import get_password_hash


def seed_user(db_session, email="user@test.com", password="secret123", role="estudiante"):
    user = models.User(
        username="testuser",
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_header(client, email="user@test.com", password="secret123"):
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_update_username(client: TestClient, db_session):
    seed_user(db_session)
    headers = _auth_header(client)
    resp = client.patch("/api/auth/me", json={"username": "nuevo_nombre"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "nuevo_nombre"


def test_update_email(client: TestClient, db_session):
    seed_user(db_session)
    headers = _auth_header(client)
    resp = client.patch("/api/auth/me", json={"email": "nuevo@test.com"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "nuevo@test.com"
    # Changing email should set is_email_verified to False
    assert resp.json()["is_email_verified"] is False


def test_change_password(client: TestClient, db_session):
    seed_user(db_session)
    headers = _auth_header(client)
    resp = client.patch(
        "/api/auth/me",
        json={"new_password": "nuevaPass1", "current_password": "secret123"},
        headers=headers,
    )
    assert resp.status_code == 200
    # Login with new password
    resp2 = client.post(
        "/api/auth/login",
        data={"username": "user@test.com", "password": "nuevaPass1", "grant_type": "password"},
    )
    assert resp2.status_code == 200


def test_change_password_requires_current(client: TestClient, db_session):
    seed_user(db_session)
    headers = _auth_header(client)
    resp = client.patch(
        "/api/auth/me",
        json={"new_password": "nuevaPass1"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "actual" in resp.json()["detail"].lower()


def test_change_password_wrong_current(client: TestClient, db_session):
    seed_user(db_session)
    headers = _auth_header(client)
    resp = client.patch(
        "/api/auth/me",
        json={"new_password": "nuevaPass1", "current_password": "wrong"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_password_too_short(client: TestClient, db_session):
    seed_user(db_session)
    headers = _auth_header(client)
    resp = client.patch(
        "/api/auth/me",
        json={"new_password": "abc", "current_password": "secret123"},
        headers=headers,
    )
    assert resp.status_code == 422  # Pydantic validation


def _seed_two_users(db_session):
    u1 = models.User(
        username="user_one",
        email="first@test.com",
        password_hash=get_password_hash("secret123"),
        role="estudiante",
        is_active=True,
    )
    db_session.add(u1)
    u2 = models.User(
        username="user_two",
        email="second@test.com",
        password_hash=get_password_hash("secret123"),
        role="estudiante",
        is_active=True,
    )
    db_session.add(u2)
    db_session.commit()


def test_email_duplicate(client: TestClient, db_session):
    _seed_two_users(db_session)
    headers = _auth_header(client, email="second@test.com")
    resp = client.patch(
        "/api/auth/me",
        json={"email": "first@test.com"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "correo" in resp.json()["detail"].lower()


def test_username_duplicate(client: TestClient, db_session):
    _seed_two_users(db_session)
    headers = _auth_header(client, email="second@test.com")
    # "user_one" está tomado por el primer usuario
    resp = client.patch(
        "/api/auth/me",
        json={"username": "user_one"},
        headers=headers,
    )
    assert resp.status_code == 400

    headers = _auth_header(client, email="second@test.com")
    resp = client.patch(
        "/api/auth/me",
        json={"username": "usuario1"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_unauthenticated_returns_401(client: TestClient, db_session):
    resp = client.patch("/api/auth/me", json={"username": "cualquiera"})
    assert resp.status_code == 401

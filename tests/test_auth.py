from fastapi.testclient import TestClient

from backend import models
from backend.core.security import get_password_hash


def seed_user(db_session, email="admin@example.com", password="secret123"):
    user = models.User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_and_refresh_flow(client: TestClient, db_session):
    seed_user(db_session)
    response = client.post(
        "/api/auth/login",
        data={
            "username": "admin@example.com",
            "password": "secret123",
            "grant_type": "password",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "refresh_token" in data

    refresh_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert refresh_data["access_token"] != data["access_token"]
    assert refresh_data["refresh_token"] != data["refresh_token"]


def test_login_rejects_invalid_credentials(client: TestClient, db_session):
    seed_user(db_session)
    response = client.post(
        "/api/auth/login",
        data={
            "username": "admin@example.com",
            "password": "wrong",
            "grant_type": "password",
        },
    )
    assert response.status_code == 401


def test_refresh_rejects_invalid_token(client: TestClient, db_session):
    response = client.post("/api/auth/refresh", json={"refresh_token": "invalid"})
    assert response.status_code == 401


def test_refresh_token_rotation_invalidates_old_token(client: TestClient, db_session):
    """Verifica que al hacer refresh, el token anterior queda revocado y no puede reutilizarse."""
    seed_user(db_session)
    login_resp = client.post(
        "/api/auth/login",
        data={
            "username": "admin@example.com",
            "password": "secret123",
            "grant_type": "password",
        },
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    original_refresh = tokens["refresh_token"]

    # Primer refresh — obtiene un token nuevo
    refresh1_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refresh1_resp.status_code == 200

    # Segundo refresh con el token original (ya revocado) — debe fallar
    refresh2_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert (
        refresh2_resp.status_code == 401
    ), "El refresh token original debe estar revocado después de usarlo"

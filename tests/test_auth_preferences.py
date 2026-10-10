"""Tests for user UI preferences and accessibility configuration."""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def test_get_preferences_default_empty(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.get("/api/v3/auth/preferences", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(admin.id)
    assert isinstance(data["settings"], dict)


def test_update_and_get_preferences(client: TestClient, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    payload = {
        "settings": {
            "theme_mode": "night",
            "ui_scale": "comfortable",
            "accent": "emerald",
        }
    }
    put_resp = client.put("/api/v3/auth/preferences", json=payload, headers=headers)
    assert put_resp.status_code == 200
    put_data = put_resp.json()
    assert put_data["settings"]["theme_mode"] == "night"
    assert put_data["settings"]["ui_scale"] == "comfortable"
    assert put_data["settings"]["accent"] == "emerald"

    get_resp = client.get("/api/v3/auth/preferences", headers=headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["settings"]["theme_mode"] == "night"
    assert get_data["settings"]["ui_scale"] == "comfortable"
    assert get_data["settings"]["accent"] == "emerald"


def test_preferences_unauthenticated_returns_401(client: TestClient):
    resp = client.get("/api/v3/auth/preferences")
    assert resp.status_code == 401

    put_resp = client.put("/api/v3/auth/preferences", json={"settings": {}})
    assert put_resp.status_code == 401

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.core.permissions import require_active_user
from backend.mesh_websockets import manager
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


class DummyUser:
    id = 1
    role = "admin"
    email = "dummy@example.com"


@pytest.fixture(autouse=True)
def clear_manager_state():
    app.dependency_overrides[require_active_user] = lambda: DummyUser()
    manager.rooms.clear()
    manager.active_connections.clear()
    yield
    app.dependency_overrides.pop(require_active_user, None)
    manager.rooms.clear()
    manager.active_connections.clear()


def test_presence_endpoint(client: TestClient, db_session):
    admin, _persona, _sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    manager.rooms["general"].add("client-a")
    response = client.get("/api/messaging/presence/general", headers=headers)
    assert response.status_code == 200
    clients = response.json()["clients"]
    client_ids = [c["client_id"] for c in clients]
    assert "client-a" in client_ids


def test_notification_endpoint(client: TestClient, db_session):
    admin, _persona, _sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    response = client.post(
        "/api/messaging/notifications",
        json={"event": "test", "body": {"foo": "bar"}, "room": "general"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"

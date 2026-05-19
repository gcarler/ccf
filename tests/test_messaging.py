import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.auth import require_active_user
from backend.mesh_websockets import manager


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


def test_presence_endpoint(client: TestClient):
    manager.rooms["room"].add("client-a")
    response = client.get("/api/messaging/presence/room")
    assert response.status_code == 200
    assert "client-a" in response.json()["clients"]


def test_notification_endpoint(client: TestClient):
    response = client.post(
        "/api/messaging/notifications",
        json={"event": "test", "body": {"foo": "bar"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"

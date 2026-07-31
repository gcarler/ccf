"""Tests for CMS v2 Presence Real-Time Collaboration endpoints (WebSocket & REST)."""
import json
import urllib.parse
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.api.cms_v2.presence import presence_manager, _parse_user_from_token


@pytest.fixture(autouse=True)
def reset_presence():
    """Reset presence manager state before each test."""
    presence_manager.rooms.clear()
    yield
    presence_manager.rooms.clear()


def test_token_parsing_helper():
    """Test user payload parsing from token."""
    # Plain text / string ID token
    u1 = _parse_user_from_token("user-123")
    assert u1["user_id"] == "user-123"
    assert u1["name"] == "Usuario user-1"
    assert "color" in u1
    assert u1["initials"] == "UU"

    # JSON token
    json_token = json.dumps({"user_id": "usr-456", "name": "Maria Lopez", "color": "#FF0000", "avatar_initials": "ML"})
    u2 = _parse_user_from_token(json_token)
    assert u2["user_id"] == "usr-456"
    assert u2["name"] == "Maria Lopez"
    assert u2["color"] == "#FF0000"
    assert u2["initials"] == "ML"

    # Empty token
    u3 = _parse_user_from_token(None)
    assert u3["user_id"] == "anon-user"


def test_rest_presence_empty():
    """GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence returns empty list when no users connected."""
    client = TestClient(app)
    response = client.get("/api/cms/v2/sites/main/pages/home/presence")
    assert response.status_code == 200
    data = response.json()
    assert "presence_users" in data
    assert data["presence_users"] == []


def test_websocket_presence_flow():
    """Test WebSocket connection, presence broadcast, and disconnection."""
    client = TestClient(app)
    token_user1 = urllib.parse.quote(json.dumps({"user_id": "usr-1", "name": "Carlos Gomez", "color": "#10B981", "avatar_initials": "CG"}))
    token_user2 = urllib.parse.quote(json.dumps({"user_id": "usr-2", "name": "Elena Diaz", "color": "#EF4444", "avatar_initials": "ED"}))

    # Client 1 connects
    with client.websocket_connect(f"/api/cms/v2/ws/presence/main/home?token={token_user1}") as ws1:
        data1 = ws1.receive_json()
        assert data1["type"] == "presence_update"
        assert len(data1["presence_users"]) == 1
        assert data1["presence_users"][0]["name"] == "Carlos Gomez"

        # Check REST endpoint reflects 1 connected user
        resp = client.get("/api/cms/v2/sites/main/pages/home/presence")
        assert resp.status_code == 200
        rest_data = resp.json()
        assert len(rest_data["presence_users"]) == 1
        assert rest_data["presence_users"][0]["user_id"] == "usr-1"

        # Client 2 connects
        with client.websocket_connect(f"/api/cms/v2/ws/presence/main/home?token={token_user2}") as ws2:

            data2_ws2 = ws2.receive_json()
            assert data2_ws2["type"] == "presence_update"
            assert len(data2_ws2["presence_users"]) == 2

            # Client 1 receives broadcast update containing user 2
            data1_update = ws1.receive_json()
            assert data1_update["type"] == "presence_update"
            assert len(data1_update["presence_users"]) == 2

            # REST endpoint reflects 2 connected users
            resp2 = client.get("/api/cms/v2/sites/main/pages/home/presence")
            assert len(resp2.json()["presence_users"]) == 2

        # Client 2 disconnects when exiting context block. Client 1 receives broadcast update
        data1_disconnect = ws1.receive_json()
        assert data1_disconnect["type"] == "presence_update"
        assert len(data1_disconnect["presence_users"]) == 1
        assert data1_disconnect["presence_users"][0]["user_id"] == "usr-1"

    # Client 1 disconnects when exiting context block
    import time
    time.sleep(0.05)
    resp_empty = client.get("/api/cms/v2/sites/main/pages/home/presence")
    assert len(resp_empty.json()["presence_users"]) == 0


from unittest.mock import patch

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin
from tests.conftest import seed_user_with_role


def test_search_chat_users(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(
        db_session, "estudiante", "user2@example.com"
    )
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)
    resp = client.get("/api/chat/users/search?q=User&limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(isinstance(item["id"], str) for item in data)
    assert any(item["id"] == str(user2.id) for item in data)


def test_create_and_list_conversations(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(db_session, "estudiante", "user2@example.com")
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None

    resp2 = client.get("/api/chat/conversations", headers=headers)
    assert resp2.status_code == 200
    convs = resp2.json()
    assert len(convs) >= 1


def test_send_and_list_messages(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(db_session, "estudiante", "user2@example.com")
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    conv_id = resp.json()["id"]

    resp2 = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "Hola!"},
        headers=headers,
    )
    assert resp2.status_code == 201
    msg = resp2.json()
    assert msg["content"] == "Hola!"

    resp3 = client.get(
        f"/api/chat/conversations/{conv_id}/messages", headers=headers
    )
    assert resp3.status_code == 200
    messages = resp3.json()
    assert len(messages) >= 1
    assert all(isinstance(item["sender_id"], str) for item in messages)


def test_mark_conversation_read(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(db_session, "estudiante", "user2@example.com")
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    conv_id = resp.json()["id"]

    resp2 = client.post(
        f"/api/chat/conversations/{conv_id}/read", headers=headers
    )
    assert resp2.status_code == 200
    assert resp2.json()["ok"] is True


def test_delete_own_message(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    msg = models.ChatMessage(
        sender_id=persona.id,
        content="Mensaje de prueba",
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)

    resp = client.delete(f"/api/chat/messages/{msg.id}", headers=headers)
    assert resp.status_code == 200


def test_search_chat_users_includes_avatar_url(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(
        db_session, "estudiante", "avataruser@example.com"
    )
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    persona2.photo_url = "https://example.com/photo.jpg"
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.get("/api/chat/users/search?q=User&limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    user_result = next((u for u in data if u["id"] == str(persona2.id)), None)
    assert user_result is not None
    assert user_result["avatar_url"] == "https://example.com/photo.jpg"


def test_delete_own_dm_message_with_room_id(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(
        db_session, "ADMIN", "user2del@example.com"
    )
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    assert resp.status_code == 201
    conv_id = resp.json()["id"]

    resp_m = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "Test delete with room_id"},
        headers=headers,
    )
    assert resp_m.status_code == 201
    msg_id = resp_m.json()["id"]

    resp_d = client.delete(f"/api/chat/messages/{msg_id}", headers=headers)
    assert resp_d.status_code == 200

    resp_m2 = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "Msg for cross-user delete test"},
        headers=headers,
    )
    assert resp_m2.status_code == 201
    msg_id2 = resp_m2.json()["id"]

    headers2 = _auth_headers(client, email="user2del@example.com", password="testpass123")
    resp_d2 = client.delete(f"/api/chat/messages/{msg_id2}", headers=headers2)
    assert resp_d2.status_code == 404


def test_list_messages_before_cursor_pagination(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(
        db_session, "estudiante", "user2pag@example.com"
    )
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    assert resp.status_code == 201
    conv_id = resp.json()["id"]

    for i in range(5):
        resp_m = client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"content": f"msg-{i}"},
            headers=headers,
        )
        assert resp_m.status_code == 201

    resp1 = client.get(
        f"/api/chat/conversations/{conv_id}/messages?limit=3",
        headers=headers,
    )
    assert resp1.status_code == 200
    page1 = resp1.json()
    assert len(page1) == 3

    oldest_created_at = page1[-1]["created_at"]
    resp2 = client.get(
        f"/api/chat/conversations/{conv_id}/messages?limit=5&before={oldest_created_at}",
        headers=headers,
    )
    assert resp2.status_code == 200
    page2 = resp2.json()
    assert len(page2) >= 1
    for msg in page2:
        assert msg["created_at"] < oldest_created_at, (
            f"Pagination broken: {msg['created_at']} not before {oldest_created_at}"
        )


def test_ws_broadcast_payload_on_send(client, db_session):
    """CHAT-MED-011: Verificar que enviar un mensaje agenda un broadcast
    con el payload correcto (event, conversation_id, message fields)."""
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(
        db_session, "estudiante", "user2ws@example.com"
    )
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    assert resp.status_code == 201
    conv_id = resp.json()["id"]

    calls = []

    async def _capture_broadcast(event, room=None):
        calls.append({"event": event, "room": room})

    with patch("backend.api.chat.manager.broadcast_event", side_effect=_capture_broadcast):
        resp_msg = client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"content": "WS broadcast test"},
            headers=headers,
        )
        assert resp_msg.status_code == 201
        msg_data = resp_msg.json()

    assert len(calls) == 1, f"Expected 1 broadcast call, got {len(calls)}"
    payload = calls[0]
    assert payload["room"] == f"dm_{conv_id}"
    evt = payload["event"]
    assert evt["event"] == "direct_message"
    assert evt["conversation_id"] == conv_id
    assert evt["message"]["content"] == "WS broadcast test"
    assert evt["message"]["sender_id"] == str(admin.id)
    assert evt["message"]["is_read"] is False
    assert evt["message"]["id"] == msg_data["id"]


def test_send_empty_content_rejected(client, db_session):
    """CHAT-MED: DirectMessageCreate validation rejects empty content."""
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(
        db_session, "estudiante", "user2empty@example.com"
    )
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    conv_id = resp.json()["id"]

    for bad_content in ["", "   ", "\t\n"]:
        resp_msg = client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"content": bad_content},
            headers=headers,
        )
        assert resp_msg.status_code == 422, (
            f"Empty content '{bad_content!r}' should be rejected, got {resp_msg.status_code}"
        )


def test_create_duplicate_conversation_returns_existing(client, db_session):
    """CHAT-MED-005: Creating the same DM conversation twice returns the existing one."""
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role(
        db_session, "estudiante", "user2dedup@example.com"
    )
    user2.sede_id = sede.id
    persona2.sede_id = sede.id
    db_session.add_all([user2, persona2])
    db_session.commit()
    headers = _auth_headers(client)

    resp1 = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    assert resp1.status_code == 201
    conv1_id = resp1.json()["id"]

    resp2 = client.post(
        "/api/chat/conversations",
        json={"participant_ids": [str(user2.id)]},
        headers=headers,
    )
    assert resp2.status_code == 201
    conv2_id = resp2.json()["id"]
    assert conv1_id == conv2_id, "Duplicate DM conversation should return existing"

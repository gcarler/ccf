import uuid

from backend import models
from tests.conftest import seed_admin_v2 as _seed_admin
from tests.conftest import auth_headers_v2 as _auth_headers
from tests.conftest import seed_user_with_role_v2


def test_search_chat_users(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    user2, persona2, _ = seed_user_with_role_v2(
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
    user2, persona2, _ = seed_user_with_role_v2(db_session, "estudiante", "user2@example.com")
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
    user2, persona2, _ = seed_user_with_role_v2(db_session, "estudiante", "user2@example.com")
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
    user2, persona2, _ = seed_user_with_role_v2(db_session, "estudiante", "user2@example.com")
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

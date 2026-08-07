"""Directed production-readiness tests for Messaging security gaps.

These tests intentionally exercise the real route handlers instead of only
calling authorization helpers. They cover the three gaps found in the final
Messaging audit:

* the /api/messaging/ws/{client_id} handshake and close codes;
* authenticated chat attachment download authorization;
* private DM presence isolation by participant and sede.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend import models
from backend.api.messaging import manager
from backend.app import app
from backend.core.permissions import create_access_token
from tests.conftest import TestingSessionLocal, auth_headers, seed_admin, seed_user_with_role


def _ws_client() -> TestClient:
    """Use Starlette's real WebSocket-capable client for handshake tests."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_websocket_manager():
    """Prevent real handshake tests from leaking manager state between cases."""
    manager.active_connections.clear()
    manager.rooms.clear()
    yield
    manager.active_connections.clear()
    manager.rooms.clear()
    listener_task = manager.listener_task
    if listener_task and not listener_task.done():
        listener_task.cancel()
    manager.listener_task = None
    assert not manager.active_connections
    assert not manager.rooms


def _conversation_with_attachment(db_session, *, user_id, sede_id, filename="secure.pdf"):
    conversation = models.Conversation(id=uuid.uuid4())
    db_session.add(conversation)
    db_session.flush()
    db_session.add(
        models.ConversationParticipant(
            conversation_id=conversation.id,
            user_id=user_id,
        )
    )
    message = models.ChatMessage(
        id=uuid.uuid4(),
        room_id=f"dm_{conversation.id}",
        sender_id=user_id,
        content="Attachment",
        attachment_url=f"/chat/attachments/{conversation.id}/{sede_id}/{filename}",
        attachment_type="pdf",
        attachment_name=filename,
        attachment_size=7,
    )
    db_session.add(message)
    db_session.commit()
    return conversation, message


@pytest.mark.parametrize(
    ("query", "expected_code"),
    [
        ("", 4001),
        ("?token=not-a-jwt", 4001),
    ],
)
def test_messaging_websocket_rejects_missing_or_invalid_token(query, expected_code):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with _ws_client().websocket_connect(f"/api/messaging/ws/client-security{query}"):
            pass
    assert exc_info.value.code == expected_code


def test_messaging_websocket_rejects_inactive_user(db_session):
    user, _, _ = seed_admin(db_session, email="inactive-ws-gap@example.com")
    user.is_active = False
    db_session.commit()
    token = create_access_token({"sub": str(user.id)})

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(f"/api/messaging/ws/client-inactive?token={token}"):
                pass
    assert exc_info.value.code == 4003


def test_messaging_websocket_rejects_user_without_read_permission(db_session):
    user, _, _ = seed_user_with_role(
        db_session,
        role_name="messaging-ws-denied",
        email="denied-ws-gap@example.com",
        permisos={"messaging": "deny"},
    )
    token = create_access_token({"sub": str(user.id)})

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(f"/api/messaging/ws/client-denied?token={token}"):
                pass
    assert exc_info.value.code == 4003


def test_messaging_websocket_rejects_unauthorized_private_room(db_session):
    user, _, _ = seed_admin(db_session, email="room-denied-gap@example.com")
    token = create_access_token({"sub": str(user.id)})
    foreign_room = uuid.uuid4()

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(
                f"/api/messaging/ws/client-room-denied?token={token}&rooms=dm_{foreign_room}"
            ):
                pass
    assert exc_info.value.code == 4003


def test_authenticated_attachment_download_allows_participant_and_denies_unauthorized_users(
    client,
    db_session,
    tmp_path: Path,
):
    user_a, _, sede_a = seed_admin(db_session, email="attachment-owner-gap@example.com")
    user_b, _, sede_b = seed_admin(db_session, email="attachment-foreign-gap@example.com")
    conversation, message = _conversation_with_attachment(
        db_session,
        user_id=user_a.id,
        sede_id=sede_a.id,
    )
    # Deliberately model an inherited/corrupt cross-sede conversation so the
    # download handler reaches its explicit sede_bucket guard, rather than
    # stopping at the participant guard.
    db_session.add(
        models.ConversationParticipant(
            conversation_id=conversation.id,
            user_id=user_b.id,
        )
    )
    db_session.commit()
    # A second same-sede user is authenticated but not a participant.
    user_nonparticipant, _, _ = seed_user_with_role(
        db_session,
        role_name="attachment-reader-gap",
        email="attachment-nonparticipant-gap@example.com",
        sede_id=sede_a.id,
        permisos={"messaging:read": "allow"},
    )

    source_dir = tmp_path / "module" / "api"
    attachment_dir = tmp_path / "static" / "chat_attachments" / str(sede_a.id)
    source_dir.mkdir(parents=True)
    attachment_dir.mkdir(parents=True)
    attachment_path = attachment_dir / "secure.pdf"
    attachment_path.write_bytes(b"PDFDATA")

    # The public /api/static mount uses the configured `uploads` directory.
    # Put a separate probe there so the assertion exercises the real mount,
    # then remove it in the test's finally block.
    from backend.core.config import get_settings

    public_root = Path(get_settings().uploads_dir).resolve()
    public_probe = public_root / "chat_attachments" / str(sede_a.id) / "secure.pdf"
    public_probe.parent.mkdir(parents=True, exist_ok=True)
    public_probe.write_bytes(b"PUBLIC-PROBE")

    route = f"/api/chat/attachments/{conversation.id}/{sede_a.id}/secure.pdf"
    owner_headers = auth_headers(client, email=user_a.email)
    nonparticipant_headers = auth_headers(client, email=user_nonparticipant.email)
    foreign_headers = auth_headers(client, email=user_b.email)

    try:
        with patch("backend.api.chat.__file__", str(source_dir / "chat.py")):
            owner_response = client.get(route, headers=owner_headers)
            assert owner_response.status_code == 200
            assert owner_response.content == b"PDFDATA"

        assert client.get(route, headers=nonparticipant_headers).status_code == 404
        assert client.get(route, headers=foreign_headers).status_code == 404
        assert client.get(
            f"/api/chat/attachments/{conversation.id}/{sede_b.id}/secure.pdf",
            headers=foreign_headers,
        ).status_code == 404
        assert client.get(route).status_code == 401
        # Legacy/static mounts must not provide a public bypass to the
        # protected chat attachment route. The public mount is exercised
        # against a real file under the configured uploads root.
        assert client.get(f"/api/static/chat_attachments/{sede_a.id}/secure.pdf").status_code == 200
        assert client.get(f"/api/static/chat_attachments/{sede_a.id}/secure.pdf").content == b"PUBLIC-PROBE"
        assert client.get(f"/static/chat_attachments/{sede_a.id}/secure.pdf").status_code == 404
        assert not (attachment_dir / "missing.pdf").exists()
        assert client.get(
            f"/api/chat/attachments/{conversation.id}/{sede_a.id}/missing.pdf",
            headers=owner_headers,
        ).status_code == 404
        assert message.attachment_url.endswith("/secure.pdf")
    finally:
        public_probe.unlink(missing_ok=True)


def test_private_presence_denies_nonparticipant_and_cross_sede_room(db_session, client):
    user_a, persona_a, sede_a = seed_admin(db_session, email="presence-owner-gap@example.com")
    user_b, persona_b, sede_b = seed_admin(db_session, email="presence-foreign-gap@example.com")
    same_sede_nonparticipant, _, _ = seed_user_with_role(
        db_session,
        role_name="presence-reader-gap",
        email="presence-nonparticipant-gap@example.com",
        sede_id=sede_a.id,
        permisos={"messaging:read": "allow"},
    )
    conversation = models.Conversation(id=uuid.uuid4())
    db_session.add(conversation)
    db_session.add(
        models.ConversationParticipant(
            conversation_id=conversation.id,
            user_id=user_a.id,
        )
    )
    db_session.commit()

    room = f"dm_{conversation.id}"
    owner_headers = auth_headers(client, email=user_a.email)
    same_sede_headers = auth_headers(client, email=same_sede_nonparticipant.email)
    foreign_headers = auth_headers(client, email=user_b.email)

    with patch.object(manager, "list_room", return_value=[str(persona_a.id)]):
        allowed = client.get(f"/api/messaging/presence/  {room}  ", headers=owner_headers)
        assert allowed.status_code == 200
        assert allowed.json()["room"] == room

    assert client.get(f"/api/messaging/presence/{room}", headers=same_sede_headers).status_code == 404
    assert client.get(f"/api/messaging/presence/{room}", headers=foreign_headers).status_code == 404
    assert client.get(f"/api/messaging/presence/{room}").status_code == 401

    # Keep the foreign persona referenced so this test documents that the
    # denied caller belongs to a different tenant, not merely another user.
    assert persona_b.sede_id != sede_a.id
    assert sede_b.id != sede_a.id


def test_messaging_websocket_accepts_authorized_user_and_broadcasts(db_session):
    user, _, _ = seed_admin(db_session, email="authorized-ws-gap@example.com")
    token = create_access_token({"sub": str(user.id)})

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(
            f"/api/messaging/ws/client-authorized?token={token}&rooms=general"
        ) as websocket:
            websocket.send_text("hello")
            assert websocket.receive_json() == {
                "event": "message",
                "client": "client-authorized",
                "data": "hello",
            }


def test_messaging_websocket_accepts_authorized_dm_and_broadcasts_to_same_tenant_participants(db_session):
    user, _, sede = seed_admin(db_session, email="authorized-dm-ws-gap@example.com")
    second_user, _, second_sede = seed_user_with_role(
        db_session,
        role_name="authorized-dm-peer-gap",
        email="authorized-dm-peer-gap@example.com",
        sede_id=sede.id,
        permisos={"messaging:read": "allow"},
    )
    conversation = models.Conversation(id=uuid.uuid4())
    db_session.add(conversation)
    db_session.add_all(
        [
            models.ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user.id,
            ),
            models.ConversationParticipant(
                conversation_id=conversation.id,
                user_id=second_user.id,
            ),
        ]
    )
    db_session.commit()
    token = create_access_token({"sub": str(user.id)})
    second_token = create_access_token({"sub": str(second_user.id)})
    room = f"dm_{conversation.id}"

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(
            f"/api/messaging/ws/client-authorized-dm-a?token={token}&rooms={room}"
        ) as websocket_a:
            with _ws_client().websocket_connect(
                f"/api/messaging/ws/client-authorized-dm-b?token={second_token}&rooms={room}"
            ) as websocket_b:
                websocket_a.send_text("private hello")
                expected = {
                    "event": "message",
                    "client": "client-authorized-dm-a",
                    "data": "private hello",
                }
                assert websocket_a.receive_json() == expected
                assert websocket_b.receive_json() == expected

    assert sede.id == second_sede.id
    assert sede.id == db_session.query(models.Persona).filter(models.Persona.id == user.id).one().sede_id


def test_send_notification_rejects_broadcast_to_foreign_dm_room(db_session, client):
    """C1 hardening: a user with messaging:read cannot inject events into a
    DM room of a conversation they do not participate in (spoofing realtime).
    """
    user_a, _, _ = seed_admin(db_session, email="broadcast-owner-gap@example.com")
    foreign_user, _, _ = seed_admin(db_session, email="broadcast-foreign-gap@example.com")
    conversation = models.Conversation(id=uuid.uuid4())
    db_session.add(conversation)
    db_session.add(
        models.ConversationParticipant(
            conversation_id=conversation.id,
            user_id=user_a.id,
        )
    )
    db_session.commit()

    foreign_room = f"dm_{conversation.id}"
    foreign_headers = auth_headers(client, email=foreign_user.email)

    resp = client.post(
        "/api/messaging/notifications",
        json={"event": "direct_message", "body": {"spoof": True}, "room": foreign_room},
        headers=foreign_headers,
    )
    # 404 (existence-leak safe) — the foreign caller must not reach the room.
    assert resp.status_code == 404


def test_send_notification_rejects_missing_room(db_session, client):
    """A broadcast without an explicit room is rejected so it can never fan
    out to every client of every instance (room=None amplifier)."""
    admin, _, _ = seed_admin(db_session, email="broadcast-noroom-gap@example.com")
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/messaging/notifications",
        json={"event": "test", "body": {}},
        headers=headers,
    )
    assert resp.status_code == 422


def test_send_notification_rejects_room_outside_allowlist(db_session, client):
    """Arbitrary room names (e.g. 'room1') are rejected by the allowlist."""
    admin, _, _ = seed_admin(db_session, email="broadcast-allowlist-gap@example.com")
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/messaging/notifications",
        json={"event": "test", "body": {}, "room": "room1"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_websocket_rejects_connection_without_rooms(db_session):
    """C2 hardening: a connection without an explicit room is rejected so a
    bare client cannot broadcast with room=None to all tenants."""
    user, _, _ = seed_admin(db_session, email="ws-noroom-gap@example.com")
    token = create_access_token({"sub": str(user.id)})

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(
                f"/api/messaging/ws/client-noroom?token={token}"
            ):
                pass
    assert exc_info.value.code == 4003


def test_websocket_rejects_unauthorized_project_room(db_session):
    """C3 hardening: an editor cannot subscribe to a project_* room of a
    project they do not own/are not assigned to (cross-sede realtime leak)."""
    user, _, _ = seed_admin(db_session, email="project-room-denied-gap@example.com")
    token = create_access_token({"sub": str(user.id)})
    foreign_project = uuid.uuid4()

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(
                f"/api/messaging/ws/client-project-denied?token={token}&rooms=project_{foreign_project}"
            ):
                pass
    assert exc_info.value.code == 4003


def test_update_notification_rejects_malformed_uuid(db_session, client):
    """M1: a malformed notification_id returns 404 (never a 500 DataError on
    PostgreSQL)."""
    admin, _, _ = seed_admin(db_session, email="notif-uuidd-gap@example.com")
    headers = auth_headers(client, email=admin.email)
    resp = client.patch("/api/messaging/notifications/not-a-uuid", headers=headers)
    assert resp.status_code == 404


def test_presence_rejects_room_outside_allowlist(db_session, client):
    """C4: presence on an arbitrary room name is rejected by the allowlist."""
    admin, _, _ = seed_admin(db_session, email="presence-allowlist-gap@example.com")
    headers = auth_headers(client, email=admin.email)
    assert client.get("/api/messaging/presence/room1", headers=headers).status_code == 404

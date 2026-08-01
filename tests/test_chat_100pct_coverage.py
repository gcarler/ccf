"""
Exhaustive test suite for backend/api/chat.py to achieve 100% test coverage.
Covers all edge cases: cross-sede defense, TOCTOU guards, orphan/invalid UUIDs, pagination formats, and message deletion.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend import crud, models
from backend.api.chat import (
    _assert_actor_is_active_participant,
    _assert_actor_still_participant_at_commit_time,
    _assert_conversation_sede_aligned,
    _assert_sender_sede_matches_actor,
    _persona_display_name,
    _validate_attachment_reference,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def chat_setup(client, db_session):
    admin, user, persona = _seed_admin(db_session, email="chat_100pct@test.com")
    sede1 = db_session.query(models.Sede).first()
    if persona:
        persona.sede_id = sede1.id
        db_session.commit()
    user.sede_id = sede1.id
    db_session.commit()
    headers = _auth_headers(client, email="chat_100pct@test.com", password="testpass123")
    return {
        "client": client,
        "headers": headers,
        "admin": admin,
        "user": user,
        "persona": persona,
        "sede1": sede1,
        "db": db_session,
    }


class TestChat100PctCoverage:
    def test_persona_display_name(self, chat_setup):
        assert _persona_display_name(None) == "Usuario"

        p1 = models.Persona(id=uuid.uuid4(), first_name="Juan", last_name="Pérez")
        assert _persona_display_name(p1) == "Juan Pérez"

    def test_assert_conversation_sede_aligned_edge_cases(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]

        # Create another Sede
        sede2 = models.Sede(id=uuid.uuid4(), nombre="Sede 2", ciudad="Ciudad 2", es_activa=True)
        db.add(sede2)
        db.commit()

        # Persona in another Sede
        p_other = models.Persona(id=uuid.uuid4(), first_name="Other", last_name="Sede", sede_id=sede2.id)
        db.add(p_other)
        db.commit()

        # Conversation with participant in another Sede
        conv = crud.create_conversation(db, [user.id, p_other.id])

        # Expect 404 (existence-leak safe) when actor belongs to Sede 1 and partner belongs to Sede 2
        with pytest.raises(HTTPException) as exc_info:
            _assert_conversation_sede_aligned(db, conv, user)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Conversation not found"

    def test_assert_sender_sede_matches_actor_edge_cases(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede2 = models.Sede(id=uuid.uuid4(), nombre="Sede 3", ciudad="Ciudad 3", es_activa=True)
        db.add(sede2)

        p_other = models.Persona(id=uuid.uuid4(), first_name="Sender", last_name="OtherSede", sede_id=sede2.id)
        db.add(p_other)
        db.commit()

        msg = models.ChatMessage(
            id=uuid.uuid4(),
            room_id="dm_test",
            sender_id=p_other.id,
            content="Cross-sede msg",
        )
        db.add(msg)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            _assert_sender_sede_matches_actor(db, msg, user)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Message not found"

    def test_assert_actor_still_participant_at_commit_time_edge_cases(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]

        # None conv_id
        with pytest.raises(HTTPException) as exc_info:
            _assert_actor_still_participant_at_commit_time(db, None, user)
        assert exc_info.value.status_code == 404

        # Malformed UUID string
        with pytest.raises(HTTPException) as exc_info:
            _assert_actor_still_participant_at_commit_time(db, "invalid-uuid-str", user)
        assert exc_info.value.status_code == 404

        # Non-participant UUID
        with pytest.raises(HTTPException) as exc_info:
            _assert_actor_still_participant_at_commit_time(db, uuid.uuid4(), user)
        assert exc_info.value.status_code == 404

    def test_assert_actor_is_active_participant_edge_cases(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]

        # Non-dm room_id (no-op)
        msg_system = models.ChatMessage(id=uuid.uuid4(), room_id="global_chat", sender_id=user.id, content="Hi")
        _assert_actor_is_active_participant(db, msg_system, user)

        # Invalid UUID suffix in room_id
        msg_bad_suffix = models.ChatMessage(id=uuid.uuid4(), room_id="dm_not-a-uuid", sender_id=user.id, content="Hi")
        with pytest.raises(HTTPException) as exc_info:
            _assert_actor_is_active_participant(db, msg_bad_suffix, user)
        assert exc_info.value.status_code == 404

        # Valid UUID suffix but user not participant
        msg_other_conv = models.ChatMessage(
            id=uuid.uuid4(), room_id=f"dm_{uuid.uuid4()}", sender_id=user.id, content="Hi"
        )
        with pytest.raises(HTTPException) as exc_info:
            _assert_actor_is_active_participant(db, msg_other_conv, user)
        assert exc_info.value.status_code == 404

    def test_create_conversation_validation_rules(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]

        # Less than 2 participants
        res = c.post("/api/chat/conversations", json={"participant_ids": []}, headers=h)
        assert res.status_code == 400
        assert "A conversation needs at least 2 participants" in res.json()["detail"]

    def test_list_messages_pagination_formats(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = db.query(models.Sede).first()

        p2 = models.Persona(id=uuid.uuid4(), first_name="Friend", last_name="User", sede_id=sede.id)
        db.add(p2)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p2.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        # Post message
        c.post(f"/api/chat/conversations/{conv_id}/messages", json={"content": "Msg 1"}, headers=h)

        # Query messages with ISO date pagination
        res1 = c.get(f"/api/chat/conversations/{conv_id}/messages?before=2026-01-01T00:00:00", headers=h)
        assert res1.status_code == 200

        # Query messages with UUID pagination
        res2 = c.get(f"/api/chat/conversations/{conv_id}/messages?before={uuid.uuid4()}", headers=h)
        assert res2.status_code == 200

        # Query messages with invalid before string
        res3 = c.get(f"/api/chat/conversations/{conv_id}/messages?before=invalid_cursor", headers=h)
        assert res3.status_code == 200

    def test_delete_own_chat_message(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = db.query(models.Sede).first()

        p2 = models.Persona(id=uuid.uuid4(), first_name="Friend2", last_name="User", sede_id=sede.id)
        db.add(p2)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p2.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        msg_res = c.post(
            f"/api/chat/conversations/{conv_id}/messages", json={"content": "To be deleted"}, headers=h
        ).json()
        msg_id = msg_res["id"]

        # Delete message
        del_res = c.delete(f"/api/chat/messages/{msg_id}", headers=h)
        assert del_res.status_code == 200
        assert del_res.json()["ok"] is True

    def test_get_persona_returns_none_when_no_persona(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        from backend.api.chat import _get_persona
        from backend.models_auth import Usuario

        u = db.query(Usuario).filter(Usuario.id != user.id).first()
        if not u:
            u = Usuario(
                id=uuid.uuid4(),
                sede_id=chat_setup["sede1"].id,
                username="no_persona",
                email="no_persona@test.com",
                is_active=True,
                is_email_verified=True,
            )
            db.add(u)
            db.commit()
        persona = _get_persona(db, u)
        assert persona is None

    def test_assert_conversation_sede_aligned_superadmin(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        from unittest.mock import patch

        from backend.api.chat import _assert_conversation_sede_aligned

        with patch("backend.api.chat.get_user_sede_id", return_value=None):
            conv = models.Conversation(id=uuid.uuid4())
            db.add(conv)
            db.commit()
            _assert_conversation_sede_aligned(db, conv, user)

    def test_assert_conversation_sede_aligned_self_dm(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        conv = crud.create_conversation(db, [user.id])
        from backend.api.chat import _assert_conversation_sede_aligned

        _assert_conversation_sede_aligned(db, conv, user)

    def test_get_persona_returns_none_when_no_persona(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        from backend.api.chat import _get_persona
        from backend.models_auth import Usuario

        u = db.query(Usuario).filter(Usuario.id != user.id).first()
        if not u:
            u = Usuario(
                id=uuid.uuid4(),
                sede_id=chat_setup["sede1"].id,
                username="no_persona",
                email="no_persona@test.com",
                is_active=True,
                is_email_verified=True,
            )
            db.add(u)
            db.commit()
        persona = _get_persona(db, u)
        assert persona is None

    def test_assert_conversation_sede_aligned_orphan_participant(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = chat_setup["sede1"]
        p_orphan = models.Persona(id=uuid.uuid4(), first_name="Orphan", last_name="NoSede", sede_id=None)
        db.add(p_orphan)
        db.commit()
        conv = crud.create_conversation(db, [user.id, p_orphan.id])
        from backend.api.chat import _assert_conversation_sede_aligned

        _assert_conversation_sede_aligned(db, conv, user)

    def test_assert_conversation_sede_aligned_no_other_user_ids(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        from unittest.mock import patch

        from backend.api.chat import _assert_conversation_sede_aligned

        class FakeParticipant:
            user_id = None

        class FakeConv:
            participants = [FakeParticipant()]

        with patch("backend.api.chat.get_user_sede_id", return_value=uuid.uuid4()):
            _assert_conversation_sede_aligned(db, FakeConv(), user)

    def test_assert_sender_sede_matches_actor_superadmin(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        from unittest.mock import patch

        from backend.api.chat import _assert_sender_sede_matches_actor

        msg = models.ChatMessage(id=uuid.uuid4(), sender_id=user.id, content="test")
        db.add(msg)
        db.commit()
        with patch("backend.api.chat.get_user_sede_id", return_value=None):
            _assert_sender_sede_matches_actor(db, msg, user)

    def test_assert_sender_sede_matches_actor_orphan_sender(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = chat_setup["sede1"]
        p_orphan = models.Persona(id=uuid.uuid4(), first_name="Orphan2", last_name="NoSede2", sede_id=None)
        db.add(p_orphan)
        db.commit()
        msg = models.ChatMessage(id=uuid.uuid4(), sender_id=p_orphan.id, content="test")
        db.add(msg)
        db.commit()
        from backend.api.chat import _assert_sender_sede_matches_actor

        _assert_sender_sede_matches_actor(db, msg, user)

    def test_schema_deduplicate_participants(self):
        from backend.schemas.chat import ConversationCreate

        payload = ConversationCreate(participant_ids=[uuid.UUID(int=1), uuid.UUID(int=2), uuid.UUID(int=1)])
        deduped = payload.deduplicate_participants()
        assert len(deduped.participant_ids) == 2

    def test_schema_content_too_long_raises(self):
        import pytest

        from backend.schemas.chat import DirectMessageCreate

        with pytest.raises(ValueError, match="exceeds 5000"):
            DirectMessageCreate(content="x" * 5001)

    def test_list_conversations_no_persona_returns_empty(self, chat_setup):
        db = chat_setup["db"]
        user = chat_setup["user"]
        from unittest.mock import patch

        from backend.api.chat import _get_persona_id

        with patch("backend.api.chat.resolve_persona_id_for_user", return_value=None):
            pid = _get_persona_id(db, user)
            assert pid is None

    def test_list_conversations_persona_none(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        from unittest.mock import patch

        with patch("backend.api.chat._get_persona_id", return_value=None):
            resp = c.get("/api/chat/conversations", headers=h)
            assert resp.status_code == 200
            assert resp.json() == []

    def test_create_conversation_persona_not_found(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        sede = chat_setup["sede1"]
        p = models.Persona(id=uuid.uuid4(), first_name="Temp", last_name="User", sede_id=sede.id)
        chat_setup["db"].add(p)
        chat_setup["db"].commit()
        with patch("backend.api.chat._get_persona_id", return_value=None):
            resp = c.post("/api/chat/conversations", json={"participant_ids": [str(p.id)]}, headers=h)
            assert resp.status_code == 404
            assert "Persona not found" in resp.json()["detail"]

    def test_create_conversation_orphan_participant_blocked(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        sede = chat_setup["sede1"]
        p_orphan = models.Persona(id=uuid.uuid4(), first_name="Orphan3", last_name="NoSede3", sede_id=None)
        db.add(p_orphan)
        db.commit()
        resp = c.post("/api/chat/conversations", json={"participant_ids": [str(p_orphan.id)]}, headers=h)
        assert resp.status_code == 404

    def test_list_direct_messages_persona_not_found(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        with patch("backend.api.chat._get_persona_id", return_value=None):
            resp = c.get(f"/api/chat/conversations/{uuid.uuid4()}/messages", headers=h)
            assert resp.status_code == 404

    def test_list_my_messages_no_user_id(self, chat_setup):
        c = chat_setup["client"]
        from unittest.mock import patch

        mock_user = type("MockUser", (), {"id": None})()
        with patch("backend.api.chat.require_module_access") as mock_req:
            mock_req.return_value = lambda: mock_user
            resp = c.get("/api/chat/my-messages", headers=chat_setup["headers"])
            assert resp.status_code == 200

    def test_list_my_messages_no_convs(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        from unittest.mock import patch

        with patch("backend.api.chat.crud.get_user_conversations", return_value=[]):
            resp = c.get("/api/chat/my-messages", headers=h)
            assert resp.status_code == 200
            assert resp.json() == []

    def test_list_my_mentions_no_persona(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        with patch("backend.api.chat._get_persona_id", return_value=None):
            resp = c.get("/api/chat/mentions", headers=h)
            assert resp.status_code == 200
            assert resp.json() == []

    def test_list_my_mentions_no_convs(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        with patch("backend.api.chat.crud.get_user_conversations", return_value=[]):
            resp = c.get("/api/chat/mentions", headers=h)
            assert resp.status_code == 200
            assert resp.json() == []

    def test_list_my_mentions_parse_error_skipped(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = chat_setup["sede1"]

        p2 = models.Persona(id=uuid.uuid4(), first_name="Mention", last_name="User", sede_id=sede.id)
        db.add(p2)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p2.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        persona_id = chat_setup["user"].id
        msg = models.ChatMessage(
            id=uuid.uuid4(),
            room_id=f"dm_{conv_id}",
            sender_id=p2.id,
            content="@me test",
            mentions_raw=str(persona_id),
        )
        db.add(msg)
        db.commit()

        resp = c.get("/api/chat/mentions", headers=h)
        assert resp.status_code == 200

    def test_list_my_mentions_filter_not_my_mention(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = chat_setup["sede1"]

        p2 = models.Persona(id=uuid.uuid4(), first_name="Mention2", last_name="User", sede_id=sede.id)
        db.add(p2)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p2.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        persona_id = str(chat_setup["user"].id)
        not_my_id = persona_id + "0"
        msg = models.ChatMessage(
            id=uuid.uuid4(),
            room_id=f"dm_{conv_id}",
            sender_id=p2.id,
            content="hello @someone",
            mentions_raw=json.dumps([not_my_id]),
        )
        db.add(msg)
        db.commit()

        resp = c.get("/api/chat/mentions", headers=h)
        assert resp.status_code == 200

    def test_build_admin_message_with_mentions_raw_invalid(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = chat_setup["sede1"]

        p2 = models.Persona(id=uuid.uuid4(), first_name="Mention3", last_name="User", sede_id=sede.id)
        db.add(p2)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p2.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        c.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"content": "msg with bad mentions raw"},
            headers=h,
        )
        msg = db.query(models.ChatMessage).filter(models.ChatMessage.content == "msg with bad mentions raw").first()
        msg.mentions_raw = "not-valid-json{{{"
        db.commit()

        resp = c.get("/api/chat/my-messages", headers=h)
        assert resp.status_code == 200

    def test_send_direct_message_persona_not_found(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        with patch("backend.api.chat._get_persona_id", return_value=None):
            resp = c.post(f"/api/chat/conversations/{uuid.uuid4()}/messages", json={"content": "Hi"}, headers=h)
            assert resp.status_code == 404

    def test_send_direct_message_with_attachment_and_reply(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = chat_setup["sede1"]

        p2 = models.Persona(id=uuid.uuid4(), first_name="Attach", last_name="User", sede_id=sede.id)
        db.add(p2)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p2.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        resp = c.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={
                "content": "With attachment",
                "attachment_url": "http://example.com/file.pdf",
                "attachment_type": "pdf",
                "attachment_name": "doc.pdf",
                "attachment_size": 1024,
                "reply_to_id": str(uuid.uuid4()),
                "mentions": [str(p2.id)],
            },
            headers=h,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "With attachment"
        assert data["attachment_url"] == "http://example.com/file.pdf"

    def test_mark_conversation_read_persona_not_found(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        with patch("backend.api.chat._get_persona_id", return_value=None):
            resp = c.post(f"/api/chat/conversations/{uuid.uuid4()}/read", headers=h)
            assert resp.status_code == 404

    def test_delete_chat_message_persona_not_found(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        msg = models.ChatMessage(id=uuid.uuid4(), sender_id=chat_setup["user"].id, content="test")
        db.add(msg)
        db.commit()
        with patch("backend.api.chat._get_persona_id", return_value=None):
            resp = c.delete(f"/api/chat/messages/{msg.id}", headers=h)
            assert resp.status_code == 404

    def test_upload_chat_attachment_success(self, chat_setup):
        import io

        c = chat_setup["client"]
        h = chat_setup["headers"]
        resp = c.post(
            "/api/chat/upload-attachment",
            files={"file": ("test.jpg", io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"), "image/jpeg")},
            headers={"Authorization": h.get("Authorization", "")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert data["type"] == "image"

    def test_protected_attachment_reference_is_bound_to_conversation(self, chat_setup):
        conversation_id = uuid.uuid4()
        other_conversation_id = uuid.uuid4()

        _validate_attachment_reference(
            f"/chat/attachments/{conversation_id}/_global/file.pdf",
            conversation_id,
        )
        _validate_attachment_reference("https://example.com/file.pdf", conversation_id)

        with pytest.raises(HTTPException) as exc_info:
            _validate_attachment_reference(
                f"/api/chat/attachments/{other_conversation_id}/_global/file.pdf",
                conversation_id,
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "Invalid attachment reference"

    def test_upload_chat_attachment_invalid_type(self, chat_setup):
        import io

        c = chat_setup["client"]
        h = chat_setup["headers"]
        resp = c.post(
            "/api/chat/upload-attachment",
            files={"file": ("test.exe", io.BytesIO(b"bad"), "application/x-msdownload")},
            headers={"Authorization": h.get("Authorization", "")},
        )
        assert resp.status_code == 422

    def test_upload_chat_attachment_too_large(self, chat_setup):
        import io

        c = chat_setup["client"]
        h = chat_setup["headers"]
        big_data = b"x" * (26 * 1024 * 1024)
        resp = c.post(
            "/api/chat/upload-attachment",
            files={"file": ("big.jpg", io.BytesIO(big_data), "image/jpeg")},
            headers={"Authorization": h.get("Authorization", "")},
        )
        assert resp.status_code == 413

    def test_list_direct_messages_not_participant_404(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        sede = chat_setup["sede1"]

        p_other = models.Persona(id=uuid.uuid4(), first_name="Other", last_name="Participant", sede_id=sede.id)
        db.add(p_other)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p_other.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        from tests.conftest import seed_user_with_role

        u_third, p_third, _ = seed_user_with_role(
            db_session=db,
            role_name="chat_user",
            email="thirdparty@test.com",
            password="testpass123",
            sede_id=sede.id,
            permisos={"messaging:read": "allow", "messaging:edit": "allow"},
        )

        resp_l = c.post("/api/v3/auth/login", json={"email": "thirdparty@test.com", "password": "testpass123"})
        assert resp_l.status_code == 200
        token = resp_l.json()["access_token"]
        h3 = {"Authorization": f"Bearer {token}"}

        resp = c.get(f"/api/chat/conversations/{conv_id}/messages", headers=h3)
        assert resp.status_code == 404

    def test_list_direct_messages_calls_sede_aligned(self, chat_setup):
        c = chat_setup["client"]
        h = chat_setup["headers"]
        db = chat_setup["db"]
        user = chat_setup["user"]
        sede = chat_setup["sede1"]

        p2 = models.Persona(id=uuid.uuid4(), first_name="MsgSede", last_name="User", sede_id=sede.id)
        db.add(p2)
        db.commit()

        conv_res = c.post("/api/chat/conversations", json={"participant_ids": [str(p2.id)]}, headers=h).json()
        conv_id = conv_res["id"]

        c.post(f"/api/chat/conversations/{conv_id}/messages", json={"content": "hi"}, headers=h)

        resp = c.get(f"/api/chat/conversations/{conv_id}/messages", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_list_my_messages_no_user_id_empty(self, chat_setup):
        db = chat_setup["db"]
        from backend.api.chat import list_my_chat_messages
        from backend.models_auth import Usuario

        mock_user = Usuario(
            id=None,
            sede_id=None,
            username="test",
            email="test@test.com",
            is_active=True,
            is_email_verified=True,
        )
        result = list_my_chat_messages(db=db, current_user=mock_user)
        assert result == []

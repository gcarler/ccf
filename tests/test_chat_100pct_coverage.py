"""
Exhaustive test suite for backend/api/chat.py to achieve 100% test coverage.
Covers all edge cases: cross-sede defense, TOCTOU guards, orphan/invalid UUIDs, pagination formats, and message deletion.
"""
from __future__ import annotations

import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models, crud
from backend.api.chat import (
    _persona_display_name,
    _assert_conversation_sede_aligned,
    _assert_sender_sede_matches_actor,
    _assert_actor_still_participant_at_commit_time,
    _assert_actor_is_active_participant,
)
from tests.conftest import auth_headers as _auth_headers, seed_admin as _seed_admin


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
        msg_other_conv = models.ChatMessage(id=uuid.uuid4(), room_id=f"dm_{uuid.uuid4()}", sender_id=user.id, content="Hi")
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

        msg_res = c.post(f"/api/chat/conversations/{conv_id}/messages", json={"content": "To be deleted"}, headers=h).json()
        msg_id = msg_res["id"]

        # Delete message
        del_res = c.delete(f"/api/chat/messages/{msg_id}", headers=h)
        assert del_res.status_code == 200
        assert del_res.json()["ok"] is True

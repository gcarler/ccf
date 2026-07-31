"""Tests exhaustivos y estructurales para backend/services/conversation_memory.py (100% Cobertura)."""

import uuid
from unittest.mock import patch

import pytest

from backend import models
from backend.models_conversation import AgentConversation, AgentMessage
from backend.services.conversation_memory import (
    create_conversation,
    delete_conversation,
    get_conversation_history,
    get_conversation_messages,
    get_user_conversations,
    save_conversation_turn,
)


class TestConversationMemory100Pct:
    def test_create_conversation_invalid_persona_raises(self, db_session):
        with patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=None):
            with pytest.raises(ValueError, match="No se pudo resolver la persona"):
                create_conversation(user_id=str(uuid.uuid4()), db=db_session)

    def test_create_conversation_success(self, db_session):
        sede = models.Sede(nombre="Sede Conv", ciudad="Bogotá")
        db_session.add(sede)
        db_session.commit()

        persona = models.Persona(first_name="Pedro", last_name="Pascal", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        with patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=persona.id):
            conv_id = create_conversation(
                user_id=str(uuid.uuid4()), title="Mi Chat", agent_name="Optimus", db=db_session
            )
            assert conv_id is not None

            conv = db_session.query(AgentConversation).filter(AgentConversation.id == conv_id).first()
            assert conv is not None
            assert conv.title == "Mi Chat"
            assert conv.agent_name == "Optimus"

    def test_get_user_conversations(self, db_session):
        sede = models.Sede(nombre="Sede List", ciudad="Cali")
        db_session.add(sede)
        db_session.commit()

        persona = models.Persona(first_name="Lucía", last_name="Mora", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        with patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=None):
            assert get_user_conversations(user_id=str(uuid.uuid4()), db=db_session) == []

        with patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=persona.id):
            conv1 = AgentConversation(persona_id=persona.id, title="Conv 1", agent_name="Agent1", is_active=True)
            conv2 = AgentConversation(persona_id=persona.id, title="Conv 2", agent_name="Agent2", is_active=False)
            db_session.add_all([conv1, conv2])
            db_session.commit()

            msg = AgentMessage(conversation_id=conv1.id, role="user", content="Hola")
            db_session.add(msg)
            db_session.commit()

            res = get_user_conversations(user_id=str(uuid.uuid4()), limit=10, db=db_session)
            assert len(res) == 1
            assert res[0]["title"] == "Conv 1"
            assert res[0]["message_count"] == 1

    def test_get_conversation_history_and_save_turn(self, db_session):
        sede = models.Sede(nombre="Sede Turn", ciudad="Medellín")
        db_session.add(sede)
        db_session.commit()

        persona = models.Persona(first_name="Mateo", last_name="Ríos", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        conv = AgentConversation(persona_id=persona.id, title="History Test", agent_name="Helper")
        db_session.add(conv)
        db_session.commit()
        conv_id = conv.id

        with patch("backend.services.conversation_memory.SessionLocal", return_value=db_session):
            save_conversation_turn(conv_id, "user", "Hola agente", tools_used=["search", "calculator"])
            save_conversation_turn(conv_id, "assistant", "Hola usuario!")

            history = get_conversation_history(conv_id, max_turns=5)
            assert len(history) == 2
            assert history[0] == {"role": "user", "content": "Hola agente"}
            assert history[1] == {"role": "assistant", "content": "Hola usuario!"}

            msgs = get_conversation_messages(conv_id, limit=10, db=db_session)
            assert len(msgs) == 2
            assert msgs[0]["tools_used"] == ["search", "calculator"]
            assert msgs[1]["tools_used"] is None

    def test_delete_conversation(self, db_session):
        sede = models.Sede(nombre="Sede Del", ciudad="Pereira")
        db_session.add(sede)
        db_session.commit()

        persona = models.Persona(first_name="Esteban", last_name="Quito", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        conv = AgentConversation(persona_id=persona.id, title="To Delete", is_active=True)
        db_session.add(conv)
        db_session.commit()

        # 1. Invalid persona
        with patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=None):
            assert delete_conversation(conv.id, user_id=str(uuid.uuid4()), db=db_session) is False

        # 2. Conv not found for persona
        other_persona_id = uuid.uuid4()
        with patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=other_persona_id):
            assert delete_conversation(conv.id, user_id=str(uuid.uuid4()), db=db_session) is False

        # 3. Successful soft delete
        with patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=persona.id):
            assert delete_conversation(conv.id, user_id=str(uuid.uuid4()), db=db_session) is True
            assert conv.is_active is False

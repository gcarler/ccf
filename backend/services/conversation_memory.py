"""Conversation Memory — Persistencia de conversaciones multi-turno.

Almacena historial de conversaciones para que los agentes mantengan
contexto entre turnos.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.core.database import Base, SessionLocal

log = logging.getLogger(__name__)


def _utcnow():
    return datetime.utcnow()


class AgentConversation(Base):
    """Conversación entre un usuario y un agente."""
    __tablename__ = "agent_conversations"
    __table_args__ = (
        Index("ix_conv_user", "user_id", "created_at"),
        Index("ix_conv_active", "user_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(300), nullable=True)
    agent_name = Column(String(100), nullable=False, server_default="Optimus")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "AgentMessage", back_populates="conversation",
        cascade="all, delete-orphan",
    )


class AgentMessage(Base):
    """Mensaje individual dentro de una conversación."""
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("ix_msg_conv", "conversation_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tools_used = Column("tools_used_json", Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    conversation = relationship(
        "AgentConversation", back_populates="messages",
    )


# ──────────────────────────────────────────────
# FUNCIONES DE ALTO NIVEL
# ──────────────────────────────────────────────

def create_conversation(
    user_id: int, title: str = None, agent_name: str = "Optimus",
) -> int:
    """Crea una nueva conversación y retorna su ID."""
    db = SessionLocal()
    try:
        conv = AgentConversation(
            user_id=user_id,
            title=title or f"Conversación con {agent_name}",
            agent_name=agent_name,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv.id
    finally:
        db.close()


def get_user_conversations(
    user_id: int, limit: int = 20,
) -> List[Dict[str, Any]]:
    """Lista conversaciones de un usuario."""
    db = SessionLocal()
    try:
        convs = db.query(AgentConversation).filter(
            AgentConversation.user_id == user_id,
            AgentConversation.is_active == True,
        ).order_by(
            AgentConversation.updated_at.desc(),
        ).limit(limit).all()

        return [
            {
                "id": c.id,
                "title": c.title,
                "agent_name": c.agent_name,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "message_count": len(c.messages) if c.messages else 0,
            }
            for c in convs
        ]
    finally:
        db.close()


def get_conversation_history(
    conversation_id: int, max_turns: int = 10,
) -> List[Dict[str, str]]:
    """Obtiene historial de una conversación en formato LLM messages."""
    db = SessionLocal()
    try:
        messages = db.query(AgentMessage).filter(
            AgentMessage.conversation_id == conversation_id,
        ).order_by(
            AgentMessage.created_at.desc(),
        ).limit(max_turns * 2).all()  # *2 for user+assistant pairs

        # Reverse to chronological order
        messages = list(reversed(messages))

        result = []
        for m in messages:
            result.append({
                "role": m.role,
                "content": m.content,
            })
        return result
    finally:
        db.close()


def save_conversation_turn(
    conversation_id: int,
    role: str,
    content: str,
    tools_used: list = None,
):
    """Guarda un turno de conversación."""
    db = SessionLocal()
    try:
        msg = AgentMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tools_used=json.dumps(tools_used, ensure_ascii=False) if tools_used else None,
        )
        db.add(msg)

        # Update conversation timestamp
        conv = db.query(AgentConversation).filter(
            AgentConversation.id == conversation_id,
        ).first()
        if conv:
            conv.updated_at = _utcnow()

        db.commit()
    finally:
        db.close()


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """Elimina una conversación (soft delete)."""
    db = SessionLocal()
    try:
        conv = db.query(AgentConversation).filter(
            AgentConversation.id == conversation_id,
            AgentConversation.user_id == user_id,
        ).first()
        if not conv:
            return False
        conv.is_active = False
        db.commit()
        return True
    finally:
        db.close()


def get_conversation_messages(
    conversation_id: int, limit: int = 50,
) -> List[Dict[str, Any]]:
    """Obtiene mensajes de una conversación."""
    db = SessionLocal()
    try:
        messages = db.query(AgentMessage).filter(
            AgentMessage.conversation_id == conversation_id,
        ).order_by(
            AgentMessage.created_at.asc(),
        ).limit(limit).all()

        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tools_used": json.loads(m.tools_used) if m.tools_used else None,
                "created_at": m.created_at,
            }
            for m in messages
        ]
    finally:
        db.close()

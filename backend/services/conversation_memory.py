"""Conversation Memory — Persistencia de conversaciones multi-turno.

Almacena historial de conversaciones para que los agentes mantengan
contexto entre turnos.
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Index, Integer, String, Text, UUID,
)
from sqlalchemy.orm import Session, relationship

from backend.core.database import Base, SessionLocal
from backend.crud.crm import resolve_persona_id_for_user

log = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


def _get_session(db: Session | None = None) -> tuple[Session, bool]:
    if db is not None:
        return db, False
    return SessionLocal(), True


class AgentConversation(Base):
    """Conversación entre un usuario y un agente."""
    __tablename__ = "agent_conversations"
    __table_args__ = (
        Index("ix_conv_user", "persona_id", "created_at"),
        Index("ix_conv_active", "persona_id", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    title = Column(String(300), nullable=True)
    agent_name = Column(String(100), nullable=False, server_default="Optimus")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tools_used = Column("tools_used_json", Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    conversation = relationship(
        "AgentConversation", back_populates="messages",
    )


# ──────────────────────────────────────────────
# FUNCIONES DE ALTO NIVEL
# ──────────────────────────────────────────────

def create_conversation(
    user_id: _uuid.UUID | str,
    title: str = None,
    agent_name: str = "Optimus",
    db: Session | None = None,
) -> _uuid.UUID:
    """Crea una nueva conversación y retorna su ID."""
    db, should_close = _get_session(db)
    try:
        persona_id = resolve_persona_id_for_user(db, user_id)
        if not persona_id:
            raise ValueError("No se pudo resolver la persona para el usuario")
        conv = AgentConversation(
            persona_id=persona_id,
            title=title or f"Conversación con {agent_name}",
            agent_name=agent_name,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv.id
    finally:
        if should_close:
            db.close()


def get_user_conversations(
    user_id: _uuid.UUID | str,
    limit: int = 20,
    db: Session | None = None,
) -> List[Dict[str, Any]]:
    """Lista conversaciones de un usuario."""
    db, should_close = _get_session(db)
    try:
        persona_id = resolve_persona_id_for_user(db, user_id)
        if not persona_id:
            return []
        convs = db.query(AgentConversation).filter(
            AgentConversation.persona_id == persona_id,
            AgentConversation.is_active,
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
        if should_close:
            db.close()


def get_conversation_history(
    conversation_id: _uuid.UUID, max_turns: int = 10,
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
    conversation_id: _uuid.UUID,
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
            tools_used=(
            json.dumps(tools_used, ensure_ascii=False)
            if tools_used else None
        ),
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


def delete_conversation(
    conversation_id: _uuid.UUID,
    user_id: _uuid.UUID | str,
    db: Session | None = None,
) -> bool:
    """Elimina una conversación (soft delete)."""
    db, should_close = _get_session(db)
    try:
        persona_id = resolve_persona_id_for_user(db, user_id)
        if not persona_id:
            return False
        conv = db.query(AgentConversation).filter(
            AgentConversation.id == conversation_id,
            AgentConversation.persona_id == persona_id,
        ).first()
        if not conv:
            return False
        conv.is_active = False
        db.commit()
        return True
    finally:
        if should_close:
            db.close()


def get_conversation_messages(
    conversation_id: _uuid.UUID,
    limit: int = 50,
    db: Session | None = None,
) -> List[Dict[str, Any]]:
    """Obtiene mensajes de una conversación."""
    db, should_close = _get_session(db)
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
        if should_close:
            db.close()

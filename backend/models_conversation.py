"""Conversation Memory — Modelos de conversaciones multi-turno.

Historial de conversaciones entre usuarios y agentes.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text, UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AgentConversation(Base):
    """Conversación entre un usuario y un agente."""

    __tablename__ = "agent_conversations"
    __table_args__ = (
        Index("ix_conv_user", "persona_id", "created_at"),
        Index("ix_conv_active", "persona_id", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True
    )
    title = Column(String(300), nullable=True)
    agent_name = Column(String(100), nullable=False, server_default="Optimus")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "AgentMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class AgentMessage(Base):
    """Mensaje individual dentro de una conversación."""

    __tablename__ = "agent_messages"
    __table_args__ = (Index("ix_msg_conv", "conversation_id", "created_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tools_used = Column("tools_used_json", Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    conversation = relationship(
        "AgentConversation",
        back_populates="messages",
    )

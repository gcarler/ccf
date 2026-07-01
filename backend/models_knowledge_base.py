"""Knowledge Base — Modelo de documentos de conocimiento indexados.

Base de conocimiento usada por el sistema multiagente.
"""

import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Index, String,
                        Text, UUID)

from backend.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AgentKnowledgeBase(Base):
    """Documento de conocimiento indexado para los agentes."""

    __tablename__ = "agent_knowledge_base"
    __table_args__ = (
        Index("ix_kb_category", "category"),
        Index("ix_kb_source", "source_module"),
        Index("ix_kb_active", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)
    category = Column(String(50), nullable=False, index=True)
    source_module = Column(String(50), nullable=False, index=True)
    source_id = Column(String(120), nullable=True)
    source_url = Column(String(500), nullable=True)
    relevance_score = Column(Float, default=0.5)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    indexed_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)

    def __repr__(self):
        return f"<KB {self.title[:50]} [{self.category}]>"

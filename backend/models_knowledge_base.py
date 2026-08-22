"""Knowledge Base — Modelo de documentos de conocimiento indexados.

Base de conocimiento usada por el sistema multiagente y Pastoral RAG.
"""

import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import UUID, Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text

from backend.core.database import Base
from backend.core.pgvector_compat import VectorEmbedding


def _utcnow():
    return datetime.now(timezone.utc)


class KnowledgeBaseArticle(Base):
    """Artículo o documento de la base de conocimiento para RAG ministerial."""

    __tablename__ = "knowledge_base_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)
    category = Column(String(100), nullable=False, default="general", index=True)
    source_module = Column(String(50), nullable=True, default="knowledge_base", index=True)
    source_id = Column(String(120), nullable=True)
    source_url = Column(String(500), nullable=True)
    relevance_score = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    embedding = Column(VectorEmbedding(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<KnowledgeBaseArticle {self.title[:50]} [{self.category}]>"


class AgentKnowledgeBase(Base):
    """Documento de conocimiento indexado para los agentes (compatibilidad)."""

    __tablename__ = "agent_knowledge_base"

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
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    embedding = Column(VectorEmbedding(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    indexed_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)

    def __repr__(self):
        return f"<KB {self.title[:50]} [{self.category}]>"

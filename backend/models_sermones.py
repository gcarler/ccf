"""Sermones — Modelo de predicaciones y mensajes pastorales para Pastoral RAG."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from backend.core.database import Base
from backend.core.pgvector_compat import VectorEmbedding
from backend.models_shared import _utcnow


class Sermon(Base):
    """Predicación / Mensaje pastoral indexado para RAG y búsqueda semántica."""

    __tablename__ = "sermones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    preacher = Column(String(255), nullable=True)
    passage = Column(String(255), nullable=True)
    content = Column(Text, nullable=False, default="")
    summary = Column(Text, nullable=True)
    series = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, default="sermon", index=True)
    date = Column(DateTime(timezone=True), nullable=True)
    video_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    embedding = Column(VectorEmbedding(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Sermon {self.title[:50]} [{self.preacher or 'N/A'}]>"


# Aliases for flexible domain imports
Sermones = Sermon
SermonModel = Sermon

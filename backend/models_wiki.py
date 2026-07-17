"""Standalone wiki documents for the platform knowledge base."""

from backend.models_shared import *
from backend.models_shared import _utcnow


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_key = Column(String(120), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, nullable=True, default=list)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class WikiPageVersion(Base):
    """Version history for wiki pages. Snapshots created on every PATCH."""
    __tablename__ = "wiki_page_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wiki_page_id = Column(UUID(as_uuid=True), ForeignKey("wiki_pages.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False, default="")
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

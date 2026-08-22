"""Agent Identity Model — Canonical person identity for the CCF platform."""

import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.models_shared import JSON, Base


def _utcnow():
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(50), unique=True, nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    spiritual_stage = Column(String(30), nullable=False, default="visitor", index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    updated_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    auth_credentials = relationship("AgentAuth", back_populates="agent", cascade="all, delete-orphan")
    contacts = relationship(
        "AgentContact", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentContact.agent_id"
    )
    roles = relationship(
        "AgentRole", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentRole.agent_id"
    )
    activities = relationship(
        "AgentActivity", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentActivity.agent_id"
    )
    families_as_agent = relationship("AgentFamily", cascade="all, delete-orphan", foreign_keys="AgentFamily.agent_id")
    families_as_related = relationship(
        "AgentFamily", cascade="all, delete-orphan", foreign_keys="AgentFamily.related_agent_id"
    )
    journey_entries = relationship(
        "AgentJourney", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentJourney.agent_id"
    )
    permissions = relationship(
        "AgentPermission", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentPermission.agent_id"
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class AgentAuth(Base):
    __tablename__ = "agent_auth"
    __table_args__ = (UniqueConstraint("agent_id", "provider", name="uq_agent_provider"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    provider = Column(String(30), default="local")
    provider_id = Column(String(255), nullable=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    agent = relationship("Agent", back_populates="auth_credentials", foreign_keys=[agent_id])


class AgentContact(Base):
    __tablename__ = "agent_contact"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)
    value = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    agent = relationship("Agent", back_populates="contacts", foreign_keys=[agent_id])


class AgentRole(Base):
    __tablename__ = "agent_roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    role_type = Column(String(30), nullable=False, index=True)
    role_value = Column(String(50), nullable=False, index=True)
    context_id = Column(UUID(as_uuid=True), nullable=True)
    context_type = Column(String(30), nullable=True)
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_primary = Column(Boolean, default=False)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    agent = relationship("Agent", back_populates="roles", foreign_keys=[agent_id])


class AgentActivity(Base):
    __tablename__ = "agent_activities"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    details = Column(JSON, default={})
    occurred_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    agent = relationship("Agent", back_populates="activities", foreign_keys=[agent_id])


class AgentFamily(Base):
    __tablename__ = "agent_families"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    related_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type = Column(String(30), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class AgentJourney(Base):
    __tablename__ = "agent_journeys"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), nullable=True, index=True)
    from_stage = Column(String(50), nullable=True, index=True)
    to_stage = Column(String(50), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    triggered_by = Column(String(50), nullable=True)
    triggered_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    achieved_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    agent = relationship("Agent", back_populates="journey_entries", foreign_keys=[agent_id])


class AgentPermission(Base):
    __tablename__ = "agent_permissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_key = Column(String(100), nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), default=_utcnow)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    agent = relationship("Agent", back_populates="permissions", foreign_keys=[agent_id])


class AgentTask(Base):
    """Tareas asignadas o generadas para agentes."""
    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="pending", index=True)
    source = Column(String(50), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    agent_type = Column(String(50), nullable=True)
    task_data = Column(JSON, default={})
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AgentInsight(Base):
    """Insights y diagnósticos generados por agentes de IA."""
    __tablename__ = "agent_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    insight_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    confidence = Column(Integer, default=80)
    source_agent = Column(String(50), nullable=True)
    insight_payload = Column(JSON, default={})
    insight_data = Column(JSON, default={})
    acknowledged = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


class ToolExecutionLog(Base):
    """Log de telemetría y trazabilidad de ejecuciones MCP/IA."""
    __tablename__ = "tool_execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    arguments = Column(JSON, default={})
    result_summary = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    execution_time_ms = Column(Integer, default=0)
    status = Column(String(30), default="success", index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

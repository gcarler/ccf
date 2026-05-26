"""Agent Identity Model — Canonical person identity for the CCF platform."""
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint, JSON)
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow():
    return datetime.utcnow()


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(50), unique=True, nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    spiritual_stage = Column(String(30), nullable=False, default="visitor", index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(Integer, ForeignKey("agents.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("agents.id"), nullable=True)

    auth_credentials = relationship("AgentAuth", back_populates="agent", cascade="all, delete-orphan")
    contacts = relationship("AgentContact", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentContact.agent_id")
    roles = relationship("AgentRole", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentRole.agent_id")
    activities = relationship("AgentActivity", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentActivity.agent_id")
    families_as_agent = relationship("AgentFamily", cascade="all, delete-orphan", foreign_keys="AgentFamily.agent_id")
    families_as_related = relationship("AgentFamily", cascade="all, delete-orphan", foreign_keys="AgentFamily.related_agent_id")
    journey_entries = relationship("AgentJourney", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentJourney.agent_id")
    permissions = relationship("AgentPermission", back_populates="agent", cascade="all, delete-orphan", foreign_keys="AgentPermission.agent_id")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class AgentAuth(Base):
    __tablename__ = "agent_auth"
    __table_args__ = (UniqueConstraint("agent_id", "provider", name="uq_agent_provider"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    provider = Column(String(30), default="local")
    provider_id = Column(String(255), nullable=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    last_login_at = Column(DateTime, nullable=True)
    agent = relationship("Agent", back_populates="auth_credentials", foreign_keys=[agent_id])


class AgentContact(Base):
    __tablename__ = "agent_contact"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)
    value = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    created_by = Column(Integer, ForeignKey("agents.id"), nullable=True)
    agent = relationship("Agent", back_populates="contacts", foreign_keys=[agent_id])


class AgentRole(Base):
    __tablename__ = "agent_roles"
    __table_args__ = (Index("ix_agent_roles_lookup", "agent_id", "role_type", "role_value"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    role_type = Column(String(30), nullable=False, index=True)
    role_value = Column(String(50), nullable=False, index=True)
    context_id = Column(Integer, nullable=True)
    context_type = Column(String(30), nullable=True)
    started_at = Column(DateTime, default=_utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_primary = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("agents.id"), nullable=True)
    agent = relationship("Agent", back_populates="roles", foreign_keys=[agent_id])


class AgentActivity(Base):
    __tablename__ = "agent_activities"
    __table_args__ = (
        Index("ix_agent_activities_lookup", "agent_id", "activity_type", "occurred_at"),
        Index("ix_agent_activities_source", "source_type", "source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(String(40), nullable=False, index=True)
    source_type = Column(String(30), nullable=False, index=True)
    source_id = Column(Integer, nullable=True)
    status = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=_utcnow, index=True)
    created_at = Column(DateTime, default=_utcnow)
    agent = relationship("Agent", back_populates="activities", foreign_keys=[agent_id])


class AgentFamily(Base):
    __tablename__ = "agent_families"
    __table_args__ = (UniqueConstraint("agent_id", "related_agent_id", "relationship", name="uq_family_relationship"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    related_agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class AgentJourney(Base):
    __tablename__ = "agent_journey"
    __table_args__ = (Index("ix_agent_journey_agent", "agent_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage = Column(String(30), nullable=True)
    to_stage = Column(String(30), nullable=False)
    reason = Column(String(100), nullable=True)
    triggered_by = Column(String(30), nullable=True)
    triggered_by_id = Column(Integer, nullable=True)
    journey_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    agent = relationship("Agent", back_populates="journey_entries", foreign_keys=[agent_id])


class AgentPermission(Base):
    __tablename__ = "agent_permissions"
    __table_args__ = (UniqueConstraint("agent_id", "permission", name="uq_agent_permission"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    permission = Column(String(50), nullable=False, index=True)
    granted_via = Column(String(50), nullable=True)
    granted_at = Column(DateTime, default=_utcnow)
    expires_at = Column(DateTime, nullable=True)
    agent = relationship("Agent", back_populates="permissions", foreign_keys=[agent_id])


class AgentTask(Base):
    """Tarea asignada a un agente (o creada por un agente)."""
    __tablename__ = "agent_tasks"
    __table_args__ = (
        Index("ix_agent_tasks_status", "status", "priority"),
        Index("ix_agent_tasks_assigned", "assigned_to"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, server_default="")
    priority = Column(String(20), nullable=False, server_default="medium", index=True)
    status = Column(String(20), nullable=False, server_default="pending", index=True)
    source = Column(String(50), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    agent_type = Column(String(50), nullable=True)
    task_data = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    completed_at = Column(DateTime, nullable=True)


class AgentInsight(Base):
    """Insight generado por un agente (análisis, detección, recomendación)."""
    __tablename__ = "agent_insights"
    __table_args__ = (
        Index("ix_agent_insights_type", "insight_type"),
        Index("ix_agent_insights_ack", "acknowledged"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, server_default="")
    insight_type = Column(String(50), nullable=False, server_default="observation", index=True)
    confidence = Column(Integer, nullable=False, server_default="50")
    source_agent = Column(String(100), nullable=True)
    insight_payload = Column("payload", JSON, nullable=True)
    insight_data = Column("metadata", JSON, nullable=True)
    acknowledged = Column(Boolean, nullable=False, server_default="false", index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

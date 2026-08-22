import uuid as _uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.models_shared import Base, _utcnow


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    actor_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    action = Column(String(120), nullable=False, index=True)
    resource_type = Column(String(120), nullable=True, index=True)
    resource_id = Column(String(120), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    severity = Column(String(20), default="info")
    metadata_json = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    trigger_type = Column(String(100), nullable=False, index=True)
    action_type = Column(String(100), nullable=True, index=True)
    action_payload = Column(JSON, default={})
    config_json = Column(Text, nullable=True, default="{}")
    is_active = Column(Boolean, default=True, index=True)
    last_run = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, index=True)


class GovernancePolicy(Base):
    """Políticas y normativas eclesiales institucionales."""
    __tablename__ = "governance_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    category = Column(String(50), default="OPERACIONAL", index=True)  # DOCTRINAL, OPERACIONAL, ADMINISTRATIVA, MINISTERIAL
    content = Column(Text, nullable=False)
    status = Column(String(30), default="BORRADOR", index=True)  # BORRADOR, EN_REVISION, APROBADA, PUBLICADA, ARCHIVADA
    version = Column(Integer, default=1)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    created_by = relationship("Persona", foreign_keys=[created_by_id], lazy="joined")
    approved_by = relationship("Persona", foreign_keys=[approved_by_id], lazy="joined")


class GovernanceResolution(Base):
    """Actas y resoluciones formales del cuerpo pastoral y directivo."""
    __tablename__ = "governance_resolutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    number = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(30), default="BORRADOR", index=True)  # BORRADOR, APROBADA, FIRMADA, ARCHIVADA
    session_date = Column(DateTime(timezone=True), default=_utcnow, index=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    created_by = relationship("Persona", foreign_keys=[created_by_id], lazy="joined")
    signatures = relationship("GovernanceSignature", back_populates="resolution", cascade="all, delete-orphan")


class GovernanceCommittee(Base):
    """Comités pastorales, disciplinarios, financieros o de gestión."""
    __tablename__ = "governance_committees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    committee_type = Column(String(50), default="PASTORAL", index=True)  # PASTORAL, FINANCIERO, DISCIPLINARIO, EVENTOS, AUDITORIA
    is_active = Column(Boolean, default=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    members = relationship("CommitteeMember", back_populates="committee", cascade="all, delete-orphan")


class CommitteeMember(Base):
    """Miembros asignados a comités eclesiales."""
    __tablename__ = "governance_committee_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    committee_id = Column(UUID(as_uuid=True), ForeignKey("governance_committees.id"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    role = Column(String(50), default="VOCAL", index=True)  # PRESIDENTE, SECRETARIO, VOCAL, ASESOR
    joined_at = Column(DateTime(timezone=True), default=_utcnow)
    is_active = Column(Boolean, default=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    committee = relationship("GovernanceCommittee", back_populates="members")
    persona = relationship("Persona", lazy="joined")


class GovernanceSignature(Base):
    """Registro de firmas digitales y respaldo de resoluciones."""
    __tablename__ = "governance_signatures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    resolution_id = Column(UUID(as_uuid=True), ForeignKey("governance_resolutions.id"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    signature_hash = Column(String(128), nullable=True)
    status = Column(String(30), default="PENDIENTE", index=True)  # PENDIENTE, FIRMADO, RECHAZADO
    observations = Column(Text, nullable=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    resolution = relationship("GovernanceResolution", back_populates="signatures")
    persona = relationship("Persona", lazy="joined")

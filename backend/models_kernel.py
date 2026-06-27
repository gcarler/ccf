"""Kernel — Protocolo de Identidad y Roles.

Modelos para el protocolo de identidad desacoplada (3 dimensiones + estado vital).
Centrado en Persona (UUID PK), no en User.

Dimensión A: Ministerios (Efesios 4:11) — vocación espiritual
Dimensión B: Roles Iglesia — embudo de consolidación
Dimensión C: Roles Plataforma — permisos RBAC
Estado Vital: ACTIVO / INACTIVO
"""
from datetime import datetime, timezone

import enum
import uuid as _uuid

from sqlalchemy import (Boolean, Column, DateTime, Enum as SAEnum, ForeignKey,
                        Index, String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# ENUMS DEL KERNEL
# ──────────────────────────────────────────────

class ActivityStatus(str, enum.Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class MinistryOffice(str, enum.Enum):
    """Dimensión A — Ministerios (El Llamado / Oficio) — Efesios 4:11."""
    APOSTOL = "APOSTOL"
    PROFETA = "PROFETA"
    EVANGELISTA = "EVANGELISTA"
    PASTOR = "PASTOR"
    MAESTRO = "MAESTRO"


class ChurchRole(str, enum.Enum):
    """Dimensión B — Roles en la Iglesia (embudo de consolidación)."""
    LIDER = "LIDER"
    SERVIDOR = "SERVIDOR"
    MIEMBRO_BAUTIZADO = "MIEMBRO_BAUTIZADO"
    SIMPATIZANTE = "SIMPATIZANTE"
    VISITANTE_SERVICIO = "VISITANTE_SERVICIO"
    VISITANTE_EVANGELISMO = "VISITANTE_EVANGELISMO"
    VISITANTE_ONLINE = "VISITANTE_ONLINE"



# ──────────────────────────────────────────────
# DIMENSIÓN A: MINISTERIOS
# ──────────────────────────────────────────────

class PersonaMinistry(Base):
    """Dimensión A — Ministerio espiritual de una persona (Efesios 4:11)."""
    __tablename__ = "persona_ministries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ministry = Column(SAEnum(MinistryOffice), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    recognized_at = Column(DateTime(timezone=True), default=_utcnow)
    recognized_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    persona = relationship("Persona", foreign_keys=[persona_id], back_populates="ministerios_kernel")
    recognized_by_persona = relationship("Persona", foreign_keys=[recognized_by_persona_id])

    __table_args__ = (
        UniqueConstraint("persona_id", "ministry", name="uq_persona_ministry"),
        Index("ix_persona_ministries_lookup", "persona_id", "ministry"),
    )


# ──────────────────────────────────────────────
# DIMENSIÓN B: ROL EN LA IGLESIA
# ──────────────────────────────────────────────

class PersonaRoleAssignment(Base):
    """Dimensión B — Rol en la iglesia (embudo de consolidación).

    Cada persona tiene UN rol principal en la iglesia en un momento dado.
    El historial de cambios se conserva en PersonaRoleHistory.
    """
    __tablename__ = "persona_church_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    church_role = Column(
        SAEnum(ChurchRole),
        nullable=False,
        default=ChurchRole.VISITANTE_ONLINE,
        index=True,
    )
    assigned_at = Column(DateTime(timezone=True), default=_utcnow)
    assigned_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    notes = Column(Text, nullable=True)

    persona = relationship("Persona", foreign_keys=[persona_id], back_populates="rol_iglesia")
    assigned_by_persona = relationship("Persona", foreign_keys=[assigned_by_persona_id])


class PersonaRoleHistory(Base):
    """Historial de cambios en el rol de iglesia (Dimensión B)."""
    __tablename__ = "persona_role_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_role = Column(SAEnum(ChurchRole), nullable=True)
    to_role = Column(SAEnum(ChurchRole), nullable=False)
    reason = Column(String(200), nullable=True)
    changed_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    changed_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    persona = relationship("Persona", foreign_keys=[persona_id])
    changed_by_persona = relationship("Persona", foreign_keys=[changed_by_persona_id])

    __table_args__ = (
        Index("ix_persona_role_history_lookup", "persona_id", "changed_at"),
    )


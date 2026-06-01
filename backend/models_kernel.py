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

from sqlalchemy import (Boolean, Column, DateTime, Enum as SAEnum, ForeignKey,
                        Index, Integer, JSON, String, Text, UniqueConstraint)
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


class PlatformRole(str, enum.Enum):
    """Dimensión C — Roles de Plataforma (permisos RBAC)."""
    ADMINISTRADOR = "ADMINISTRADOR"
    GESTOR = "GESTOR"
    EDITOR = "EDITOR"
    LECTOR = "LECTOR"


# ──────────────────────────────────────────────
# DIMENSIÓN A: MINISTERIOS
# ──────────────────────────────────────────────

class PersonaMinistry(Base):
    """Dimensión A — Ministerio espiritual de una persona (Efesios 4:11)."""
    __tablename__ = "persona_ministries"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ministry = Column(SAEnum(MinistryOffice), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    recognized_at = Column(DateTime(timezone=True), default=_utcnow)
    recognized_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    persona = relationship("Persona", back_populates="ministerios_kernel")
    recognized_by_user = relationship("User", foreign_keys=[recognized_by])

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

    id = Column(Integer, primary_key=True, index=True)
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
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    persona = relationship("Persona", back_populates="rol_iglesia")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class PersonaRoleHistory(Base):
    """Historial de cambios en el rol de iglesia (Dimensión B)."""
    __tablename__ = "persona_role_history"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_role = Column(SAEnum(ChurchRole), nullable=True)
    to_role = Column(SAEnum(ChurchRole), nullable=False)
    reason = Column(String(200), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    persona = relationship("Persona")
    changed_by_user = relationship("User", foreign_keys=[changed_by])

    __table_args__ = (
        Index("ix_persona_role_history_lookup", "persona_id", "changed_at"),
    )


# ──────────────────────────────────────────────
# DIMENSIÓN C: ROLES DE PLATAFORMA (RBAC)
# ──────────────────────────────────────────────

class PlatformRoleDefinition(Base):
    """Dimensión C — Definición de roles de plataforma con permisos predefinidos."""
    __tablename__ = "platform_role_definitions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(SAEnum(PlatformRole), unique=True, nullable=False, index=True)
    permissions = Column(
        JSON, nullable=False, default={
            "ADMINISTRADOR": {
                "*": ["create", "read", "update", "delete", "admin"],
            },
            "GESTOR": {
                "crm": ["create", "read", "update"],
                "academy": ["create", "read", "update"],
                "projects": ["create", "read", "update"],
                "evangelism": ["create", "read", "update"],
                "cms": ["read", "update"],
                "community": ["create", "read", "update"],
                "agenda": ["create", "read", "update"],
                "finances": ["read"],
            },
            "EDITOR": {
                "crm": ["read", "update"],
                "academy": ["read"],
                "projects": ["read", "update"],
                "evangelism": ["read", "update"],
                "cms": ["read", "update"],
                "community": ["create", "read", "update"],
                "agenda": ["read"],
            },
            "LECTOR": {
                "crm": ["read"],
                "academy": ["read"],
                "projects": ["read"],
                "evangelism": ["read"],
                "cms": ["read"],
                "community": ["read"],
                "agenda": ["read"],
            },
        },
        comment="Permisos por módulo: {module: [actions]}"
    )
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    persona_roles = relationship("PersonaPlatformRole", back_populates="role_definition")


class PersonaPlatformRole(Base):
    """Dimensión C — Asignación de rol de plataforma a una persona."""
    __tablename__ = "persona_platform_roles"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        Integer, ForeignKey("platform_role_definitions.id"), nullable=False, index=True
    )
    assigned_at = Column(DateTime(timezone=True), default=_utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)

    persona = relationship("Persona", back_populates="roles_plataforma")
    role_definition = relationship("PlatformRoleDefinition", back_populates="persona_roles")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint("persona_id", "role_id", name="uq_persona_platform_role"),
    )


# ──────────────────────────────────────────────
# BACKWARD COMPAT ALIASES (tablas viejas user_*)
# Los stubs permiten que código legado que aún importe estas clases
# no rompa mientras se migra gradualmente.
# ──────────────────────────────────────────────

UserMinistry = PersonaMinistry
UserRoleAssignment = PersonaRoleAssignment
UserRoleHistory = PersonaRoleHistory
UserPlatformRole = PersonaPlatformRole

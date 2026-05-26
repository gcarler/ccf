"""CCF Kernel — Protocolo de Identidad y Roles.

Modelos para el protocolo de identidad desacoplada (3 dimensiones + estado vital).

Dimensión A: Ministerios (Efesios 4:11) — vocación espiritual
Dimensión B: Roles Iglesia — embudo de consolidación
Dimensión C: Roles Plataforma — permisos RBAC
Estado Vital: ACTIVO / INACTIVO
"""
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Enum as SAEnum, ForeignKey,
                        Index, Integer, JSON, String, Text, UniqueConstraint)
from sqlalchemy.orm import relationship

from backend.core.database import Base
import enum


# ──────────────────────────────────────────────
# ENUMS DEL KERNEL
# ──────────────────────────────────────────────

def _utcnow():
    return datetime.utcnow()


class ActivityStatus(str, enum.Enum):
    """Estado Vital — participación actual de la persona en la comunidad."""
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
# MODELOS DEL KERNEL
# ──────────────────────────────────────────────

class UserMinistry(Base):
    """Dimensión A — Ministerio espiritual de una persona (Efesios 4:11).

    Relación N:M: un usuario puede tener múltiples ministerios reconocidos
    (ej: PASTOR + MAESTRO), y un ministerio puede pertenecer a muchas personas.
    """
    __tablename__ = "user_ministries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ministry = Column(SAEnum(MinistryOffice), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    recognized_at = Column(DateTime, default=_utcnow)
    recognized_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id], backref="kernel_ministries")
    recognized_by_user = relationship("User", foreign_keys=[recognized_by])

    __table_args__ = (
        UniqueConstraint("user_id", "ministry", name="uq_user_ministry"),
        Index("ix_user_ministries_lookup", "user_id", "ministry"),
    )


class UserRoleAssignment(Base):
    """Dimensión B — Rol en la iglesia (embudo de consolidación).

    Cada persona tiene UN rol principal en la iglesia en un momento dado.
    El historial de cambios se conserva en kernel_role_history.
    """
    __tablename__ = "user_church_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        unique=True, index=True
    )
    church_role = Column(
        SAEnum(ChurchRole), nullable=False,
        default=ChurchRole.VISITANTE_ONLINE, index=True,
    )
    assigned_at = Column(DateTime, default=_utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id], backref="kernel_church_role")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class UserRoleHistory(Base):
    """Historial de cambios en el rol de iglesia (Dimensión B).

    Cada transición se registra aquí para auditoría del camino espiritual.
    """
    __tablename__ = "kernel_role_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_role = Column(SAEnum(ChurchRole), nullable=True)
    to_role = Column(SAEnum(ChurchRole), nullable=False)
    reason = Column(String(200), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime, default=_utcnow, index=True)

    user = relationship("User", foreign_keys=[user_id], backref="kernel_role_history")
    changed_by_user = relationship("User", foreign_keys=[changed_by])

    __table_args__ = (
        Index("ix_role_history_user", "user_id", "changed_at"),
    )


class PlatformRoleDefinition(Base):
    """Dimensión C — Definición de roles de plataforma con permisos predefinidos.

    Cada rol tiene un conjunto de permisos granulares (JSON) que definen
    qué puede hacer el usuario en la plataforma.
    """
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
    created_at = Column(DateTime, default=_utcnow)

    users = relationship("UserPlatformRole", back_populates="role_definition")


class UserPlatformRole(Base):
    """Dimensión C — Asignación de rol de plataforma a un usuario.

    Relación N:M: un usuario puede tener múltiples roles de plataforma
    (ej: GESTOR en CRM + EDITOR en CMS).
    """
    __tablename__ = "user_platform_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id = Column(
        Integer, ForeignKey("platform_role_definitions.id"), nullable=False, index=True
    )
    assigned_at = Column(DateTime, default=_utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id], backref="kernel_platform_roles")
    role_definition = relationship("PlatformRoleDefinition", back_populates="users")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_platform_role"),
    )

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, JSON,
                        String, Text)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import relationship

from backend.models_shared import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ==========================================
# 1. CATÁLOGOS Y ROLES DE ACCESO (RBAC)
# ==========================================

class RolPlataforma(Base):
    __tablename__ = "auth_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    permisos = Column(JSON, nullable=False, default=dict)


class NivelGamificado(Base):
    __tablename__ = "auth_levels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    title = Column(String(100), nullable=False)
    min_xp = Column(Integer, nullable=False, unique=True)
    icon_key = Column(String(50))


# ==========================================
# 2. TABLA PRINCIPAL DE CREDENCIALES
# ==========================================

class Usuario(Base):
    __tablename__ = "auth_users"

    id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), primary_key=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    username = Column(CITEXT, nullable=False, unique=True)
    email = Column(CITEXT, nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    rol_plataforma_id = Column(UUID(as_uuid=True), ForeignKey("auth_roles.id"), nullable=True)
    platform_role_id = Column(Integer, ForeignKey("platform_role_definitions.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True))
    mfa_secret = Column(String(100))
    is_mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_backup_codes = Column(JSON, default=list)
    xp = Column(Integer, default=0, nullable=False)
    current_level_id = Column(UUID(as_uuid=True), ForeignKey("auth_levels.id"))
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    persona = relationship("backend.models_crm.Persona", foreign_keys=[id], primaryjoin="Usuario.id == backend.models_crm.Persona.id")
    rol_plataforma = relationship("RolPlataforma", foreign_keys=[rol_plataforma_id])
    platform_role = relationship("backend.models_kernel.PlatformRoleDefinition", foreign_keys=[platform_role_id])
    roles_modulares = relationship("UsuarioRolModulo", back_populates="usuario", cascade="all, delete-orphan")


# ==========================================
# 3. ROLES MODULARES GRANULARES
# ==========================================

class UsuarioRolModulo(Base):
    __tablename__ = "auth_user_module_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    modulo = Column(String(50), nullable=False)
    rol_id = Column(UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    usuario = relationship("Usuario", back_populates="roles_modulares")
    rol = relationship("RolPlataforma")


# ==========================================
# 4. CONTROL DE SESIONES Y SEGURIDAD
# ==========================================

class TokenSesion(Base):
    __tablename__ = "auth_refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), nullable=False, unique=True)
    revoked = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_active = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class TokenResetContrasena(Base):
    __tablename__ = "auth_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class TokenVerificacionEmail(Base):
    __tablename__ = "auth_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class LogSeguridad(Base):
    __tablename__ = "auth_security_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    evento = Column(String(100), nullable=False)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    detalles = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class HistorialContrasena(Base):
    __tablename__ = "auth_password_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ==========================================
# 5. PREFERENCIAS, NOTIFICACIONES, RECORDATORIOS
# ==========================================

class PreferenciaUI(Base):
    __tablename__ = "auth_user_ui_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    settings = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class NotificacionUsuario(Base):
    __tablename__ = "auth_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class RecordatorioUsuario(Base):
    __tablename__ = "auth_user_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    priority = Column(String(20), default="MEDIA")
    is_dismissed = Column(Boolean, default=False, nullable=False)
    related_type = Column(String(50))
    related_id = Column(String(100))


# ==========================================
# 6. GAMIFICACIÓN
# ==========================================

class Medalla(Base):
    __tablename__ = "auth_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    icon_key = Column(String(50))
    xp_reward = Column(Integer, default=50, nullable=False)


class MedallaUsuario(Base):
    __tablename__ = "auth_user_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("auth_badges.id", ondelete="CASCADE"), nullable=False)
    earned_at = Column(DateTime(timezone=True), default=_utcnow)

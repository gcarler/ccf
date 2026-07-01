from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field

from backend.schemas._common import orm_config

# ==========================================
# Auth v3 — Schemas Pydantic
# ==========================================

# ── Roles ─────────────────────────────────────────────────────────────────

class RolPlataformaBase(BaseModel):
    nombre: str
    permisos: dict[str, Any] = Field(default_factory=dict)


class RolPlataformaCreate(RolPlataformaBase):
    pass


class RolPlataformaUpdate(BaseModel):
    nombre: Optional[str] = None
    permisos: Optional[dict[str, Any]] = None


class RolPlataformaRead(RolPlataformaBase):
    id: uuid.UUID
    model_config = orm_config


# ── Niveles / Gamificación ───────────────────────────────────────────────

class NivelGamificadoBase(BaseModel):
    title: str
    min_xp: int
    icon_key: Optional[str] = None


class NivelGamificadoCreate(NivelGamificadoBase):
    pass


class NivelGamificadoRead(NivelGamificadoBase):
    id: uuid.UUID
    model_config = orm_config


# ── Usuarios ─────────────────────────────────────────────────────────────

class UsuarioBase(BaseModel):
    sede_id: str
    username: str
    email: EmailStr
    is_active: bool = True
    xp: int = 0


class UsuarioCreate(UsuarioBase):
    password: str = Field(min_length=8)
    rol_plataforma_id: uuid.UUID


class UsuarioUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    rol_plataforma_id: Optional[uuid.UUID] = None
    sede_id: Optional[str] = None


class UsuarioLogin(BaseModel):
    username: str
    password: str


class UsuarioRead(UsuarioBase):
    id: uuid.UUID
    sede_id: str
    username: str
    email: EmailStr
    rol_plataforma_id: uuid.UUID
    is_active: bool
    is_email_verified: bool
    is_mfa_enabled: bool
    xp: int
    current_level_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class UsuarioSelfUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(default=None, min_length=8)


# ── Roles Modulares ──────────────────────────────────────────────────────

class UsuarioRolModuloBase(BaseModel):
    modulo: str
    rol_id: uuid.UUID


class UsuarioRolModuloCreate(UsuarioRolModuloBase):
    pass


class UsuarioRolModuloRead(UsuarioRolModuloBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    model_config = orm_config


# ── Tokens / Sesiones ────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    user: UsuarioRead


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenSesionRead(BaseModel):
    id: uuid.UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    last_active: Optional[datetime] = None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False
    model_config = orm_config


# ── Seguridad ────────────────────────────────────────────────────────────

class LogSeguridadRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    evento: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    detalles: Optional[dict[str, Any]] = None
    created_at: datetime
    model_config = orm_config


class CambioPasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


# ── Notificaciones / Recordatorios ───────────────────────────────────────

class NotificacionRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    content: str
    is_read: bool
    created_at: datetime
    model_config = orm_config


class RecordatorioCreate(BaseModel):
    title: str
    description: Optional[str] = None
    remind_at: datetime
    priority: str = "MEDIA"
    related_type: Optional[str] = None
    related_id: Optional[str] = None


class RecordatorioRead(RecordatorioCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    is_dismissed: bool
    model_config = orm_config


# ── Preferencias UI ──────────────────────────────────────────────────────

class PreferenciaUIUpdate(BaseModel):
    settings: dict[str, Any]


class PreferenciaUIRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    settings: dict[str, Any]
    updated_at: datetime
    model_config = orm_config


# ── Medallas ─────────────────────────────────────────────────────────────

class MedallaCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon_key: Optional[str] = None
    xp_reward: int = 50


class MedallaRead(MedallaCreate):
    id: uuid.UUID
    model_config = orm_config


class MedallaUsuarioRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    badge_id: uuid.UUID
    earned_at: datetime
    model_config = orm_config


# ── MFA ──────────────────────────────────────────────────────────────────

class MfaSetupResponse(BaseModel):
    secret: str
    qr_code_url: str


class MfaVerifyRequest(BaseModel):
    token: str


class MfaRecoveryResponse(BaseModel):
    backup_codes: list[str]


# ── Estadísticas ─────────────────────────────────────────────────────────

class AuthStatsSummary(BaseModel):
    total_users: int
    active_users: int
    verified_users: int
    mfa_enabled: int
    by_role: dict[str, int]

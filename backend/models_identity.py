"""Identity support models for auth-adjacent preferences and notifications."""
from backend.models_shared import *
from backend.models_shared import _utcnow


from backend.models_auth import (
    Usuario as User,
    RolPlataforma as Role,
    TokenSesion as RefreshToken,
    TokenResetContrasena as ResetToken,
    TokenVerificacionEmail as VerificationToken,
    Medalla as Badge,
    MedallaUsuario as UserBadge,
    PreferenciaUI as UserUIPreference,
    NotificacionUsuario as Notification,
    RecordatorioUsuario as UserReminder,
    NivelGamificado as Level,
)

__all__ = ["User", "Role", "RefreshToken", "ResetToken", "VerificationToken",
           "Badge", "UserBadge", "UserUIPreference", "Notification", "UserReminder", "Level"]


class Level(Base):
    __tablename__ = "levels"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(50), unique=True, nullable=False)
    min_xp = Column(Integer, default=0)
    icon_key = Column(String(50), nullable=True)


class Badge(Base):
    __tablename__ = "badges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon_key = Column(String(50), nullable=False)
    xp_reward = Column(Integer, default=50)


class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id"), nullable=False, index=True)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime(timezone=True), default=_utcnow)


class UserUIPreference(Base):
    __tablename__ = "user_ui_preferences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id"), unique=True, nullable=False)
    settings = Column(JSON, default={})
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class UserPermission(Base):
    """Permisos individuales por usuario."""
    __tablename__ = "user_permissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    permissions = Column(JSON, default={})
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


class UserReminder(Base):
    __tablename__ = "user_reminders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    remind_at = Column(DateTime(timezone=True), nullable=False, index=True)
    priority = Column(String(20), default="normal")
    related_type = Column(String(50), nullable=True, index=True)
    related_id = Column(UUID(as_uuid=True), nullable=True)
    is_dismissed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

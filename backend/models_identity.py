"""English domain names for the canonical Auth v3 models."""

from backend.models_auth import (
    Medalla as Badge,
    MedallaUsuario as UserBadge,
    NivelGamificado as Level,
    NotificacionUsuario as Notification,
    PreferenciaUI as UserUIPreference,
    RecordatorioUsuario as UserReminder,
    RolPlataforma as Role,
    TokenResetContrasena as ResetToken,
    TokenSesion as RefreshToken,
    TokenVerificacionEmail as VerificationToken,
    Usuario as User,
)

__all__ = [
    "Badge",
    "Level",
    "Notification",
    "RefreshToken",
    "ResetToken",
    "Role",
    "User",
    "UserBadge",
    "UserReminder",
    "UserUIPreference",
    "VerificationToken",
]

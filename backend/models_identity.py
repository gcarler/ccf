"""English domain names for the canonical Auth v3 models."""

from backend.models_auth import (
    Medalla as Badge,
)
from backend.models_auth import (
    MedallaUsuario as UserBadge,
)
from backend.models_auth import (
    NivelGamificado as Level,
)
from backend.models_auth import (
    NotificacionUsuario as Notification,
)
from backend.models_auth import (
    PreferenciaUI as UserUIPreference,
)
from backend.models_auth import (
    RecordatorioUsuario as UserReminder,
)
from backend.models_auth import (
    RolPlataforma as Role,
)
from backend.models_auth import (
    TokenResetContrasena as ResetToken,
)
from backend.models_auth import (
    TokenSesion as RefreshToken,
)
from backend.models_auth import (
    TokenVerificacionEmail as VerificationToken,
)
from backend.models_auth import (
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

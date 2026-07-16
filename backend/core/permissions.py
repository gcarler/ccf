"""
Centralized role & permission logic for CCF Mesh.

All modules should import from here for:
  - Permission constants & role matrix
  - Role normalization & checks
  - FastAPI dependency guards (require_*)
  - JWT token creation / user resolution
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.core.cache import get_redis
from backend.core.config import get_settings
from backend.core.context import user_role_context
from backend.core.database import get_db
from backend.core.security import verify_password

log = logging.getLogger(__name__)
settings = get_settings()

# ── JWT ────────────────────────────────────────────────────────────────
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v3/auth/login")

# ── Role aliases & valid set ──────────────────────────────────────────
ROLE_ALIASES: Dict[str, str] = {
    "student": "estudiante",
    "leader": "coordinador",
    "lider": "coordinador",
    "staff": "docente",
    "pastor": "pastor",
    "administrador": "admin",
}

VALID_ROLES: set[str] = {
    "aspirante",
    "estudiante",
    "docente",
    "coordinador",
    "pastor",
    "admin",
}

# ── Permission taxonomy ────────────────────────────────────────────────
PERMISSIONS: Dict[str, Dict[str, str]] = {
    "system:config": {
        "label": "Configurar sistema",
        "description": "Acceso total para configurar el sistema (Super Admin)",
    },
    "profile:manage": {
        "label": "Gestionar perfil",
        "description": "Permite al usuario gestionar su propia información personal",
    },
    "messaging:read": {
        "label": "Mensajes: lector",
        "description": "Ver mensajes y notificaciones",
    },
    "messaging:edit": {
        "label": "Mensajes: editor",
        "description": "Enviar y gestionar mensajes",
    },
    "crm:read": {
        "label": "CRM: lector",
        "description": "Solo lectura de contactos e historial",
    },
    "crm:edit": {
        "label": "CRM: editor",
        "description": "Editar contactos, registrar interacciones",
    },
    "crm:manage": {
        "label": "CRM: gestor",
        "description": "Gestionar CRM, eventos y personas",
    },
    "finance:read": {
        "label": "Finanzas: lector",
        "description": "Solo lectura del módulo de finanzas",
    },
    "finance:edit": {
        "label": "Finanzas: editor",
        "description": "Registrar transacciones y donaciones",
    },
    "finance:manage": {
        "label": "Finanzas: gestor",
        "description": "Gestionar transacciones, donaciones y presupuestos",
    },
    "projects:read": {
        "label": "Proyectos: lector",
        "description": "Solo lectura de proyectos y tareas",
    },
    "projects:edit": {
        "label": "Proyectos: editor",
        "description": "Crear y editar tareas",
    },
    "projects:manage": {
        "label": "Proyectos: gestor",
        "description": "Gestionar proyectos, tareas y tableros",
    },
    "cms:read": {
        "label": "CMS: lector",
        "description": "Ver borradores y contenido interno del CMS",
    },
    "cms:edit": {
        "label": "CMS: editor",
        "description": "Editar contenido y páginas",
    },
    "cms:manage": {
        "label": "CMS: gestor",
        "description": "Gestionar el contenido web, páginas y multimedia",
    },
    "academy:read": {
        "label": "Academia: lector",
        "description": "Ver cursos y contenido académico",
    },
    "academy:study": {
        "label": "Academia: participante",
        "description": "Inscribirse en cursos y desarrollar evaluaciones",
    },
    "academy:edit": {
        "label": "Academia: editor",
        "description": "Crear y editar contenido de cursos",
    },
    "academy:manage": {
        "label": "Academia: gestor",
        "description": "Gestionar cursos, lecciones y calificaciones",
    },
    "evangelism:read": {
        "label": "Evangelismo: lector",
        "description": "Ver estrategias y campañas de evangelismo",
    },
    "evangelism:edit": {
        "label": "Evangelismo: editor",
        "description": "Crear y editar estrategias de evangelismo",
    },
    "evangelism:manage": {
        "label": "Evangelismo: gestor",
        "description": "Gestionar evangelismo, campañas y salidas",
    },
    "community:read": {
        "label": "Comunidad: lector",
        "description": "Ver grupos y actividades comunitarias",
    },
    "community:edit": {
        "label": "Comunidad: editor",
        "description": "Crear y editar grupos y eventos comunitarios",
    },
    "community:manage": {
        "label": "Comunidad: gestor",
        "description": "Gestionar la comunidad, grupos y células",
    },
    "spiritual_life:read": {
        "label": "Vida Espiritual: lector",
        "description": "Ver contenido y recursos espirituales",
    },
    "spiritual_life:edit": {
        "label": "Vida Espiritual: editor",
        "description": "Crear y editar contenido espiritual",
    },
    "spiritual_life:manage": {
        "label": "Vida Espiritual: gestor",
        "description": "Gestionar el módulo de vida espiritual",
    },
}

# ── Permission expansion helpers (must be before DEFAULT_ROLES) ────────

PERMISSION_LEVELS = {
    "read": {"read"},
    "edit": {"read", "edit"},
    "manage": {"read", "edit", "manage"},
}

MODULE_PERMISSION_MAP: Dict[str, Dict[str, str]] = {
    "crm": {"read": "crm:read", "edit": "crm:edit", "manage": "crm:manage"},
    "finance": {
        "read": "finance:read",
        "edit": "finance:edit",
        "manage": "finance:manage",
    },
    "projects": {
        "read": "projects:read",
        "edit": "projects:edit",
        "manage": "projects:manage",
    },
    "cms": {"read": "cms:read", "edit": "cms:edit", "manage": "cms:manage"},
    "academy": {
        "read": "academy:read",
        "study": "academy:study",
        "edit": "academy:edit",
        "manage": "academy:manage",
    },
    "messaging": {"read": "messaging:read", "edit": "messaging:edit"},
    "evangelism": {
        "read": "evangelism:read",
        "edit": "evangelism:edit",
        "manage": "evangelism:manage",
    },
    "community": {
        "read": "community:read",
        "edit": "community:edit",
        "manage": "community:manage",
    },
    "spiritual_life": {
        "read": "spiritual_life:read",
        "edit": "spiritual_life:edit",
        "manage": "spiritual_life:manage",
    },
}


def expand_module_permissions(module: str, level: str) -> List[str]:
    """Retorna los permisos concretos para un módulo dado un nivel (read/edit/manage)."""
    module_perms = MODULE_PERMISSION_MAP.get(module, {})
    levels = PERMISSION_LEVELS.get(level, {level})
    return [module_perms[lvl] for lvl in levels if lvl in module_perms]


# ── Default role matrix ────────────────────────────────────────────────
DEFAULT_ROLES: List[Dict[str, Any]] = [
    {
        "name": "Super administrador",
        "label": "Super administrador",
        "permissions": [
            "system:config",
            *expand_module_permissions("crm", "manage"),
            *expand_module_permissions("finance", "manage"),
            *expand_module_permissions("projects", "manage"),
            *expand_module_permissions("cms", "manage"),
            *expand_module_permissions("academy", "manage"),
            *expand_module_permissions("messaging", "edit"),
            "profile:manage",
        ],
    },
    {
        "name": "Administrador",
        "label": "Administrador",
        "permissions": [
            *expand_module_permissions("crm", "manage"),
            *expand_module_permissions("finance", "manage"),
            *expand_module_permissions("projects", "manage"),
            *expand_module_permissions("cms", "manage"),
            *expand_module_permissions("academy", "manage"),
            *expand_module_permissions("messaging", "edit"),
            "profile:manage",
        ],
    },
    {
        "name": "Gestor",
        "label": "Gestor",
        "permissions": [
            *expand_module_permissions("crm", "manage"),
            *expand_module_permissions("projects", "manage"),
            *expand_module_permissions("academy", "manage"),
            *expand_module_permissions("messaging", "edit"),
            "profile:manage",
        ],
    },
    {
        "name": "Editor",
        "label": "Editor",
        "permissions": [
            *expand_module_permissions("crm", "edit"),
            *expand_module_permissions("projects", "edit"),
            *expand_module_permissions("academy", "edit"),
            *expand_module_permissions("messaging", "edit"),
            "profile:manage",
        ],
    },
    {
        "name": "Lector",
        "label": "Lector",
        "permissions": [
            *expand_module_permissions("academy", "study"),
            "profile:manage",
        ],
    },
    {
        "name": "Miembro",
        "label": "Miembro",
        "permissions": [
            *expand_module_permissions("academy", "study"),
            "profile:manage",
        ],
    },
    {
        "name": "Estudiante",
        "label": "Estudiante",
        "permissions": [
            *expand_module_permissions("academy", "study"),
            "profile:manage",
        ],
    },
    {
        "name": "Aspirante",
        "label": "Aspirante",
        "permissions": [
            *expand_module_permissions("academy", "study"),
            "profile:manage",
        ],
    },
]

# ── Helpers ────────────────────────────────────────────────────────────


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_role(role: str) -> str:
    """Normalize a role string (handle aliases, case, whitespace)."""
    role_value = str(role or "").strip().lower()
    return ROLE_ALIASES.get(role_value, role_value)


def role_in(user_role: str, allowed_roles: set[str]) -> bool:
    """Check if a normalized role is in the allowed set."""
    return normalize_role(user_role) in allowed_roles


def is_crm_privileged(role: str) -> bool:
    """Verifica si un rol tiene acceso total al CRM (Administradores y Pastores)."""
    return normalize_role(role) in {"admin", "pastor"}


# ── Public helpers ─────────────────────────────────────────────────────


def get_all_permissions() -> Dict[str, Dict[str, str]]:
    return {k: dict(v) for k, v in PERMISSIONS.items()}


def get_default_roles() -> List[Dict[str, Any]]:
    return list(DEFAULT_ROLES)


def get_user_effective_permissions(db: Session, user) -> dict:
    """Compute effective permissions for a user.

    Resolution order: admin bypass, Auth v3 platform role, then canonical defaults.
    Returns a dict of {permission_key: "allow"}.
    """
    role = normalize_role(getattr(user, "role", ""))

    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)

    # Admin bypass: full access
    if role in {"admin", "administrador", "super administrador"}:
        perms = {}
        for p_key in PERMISSIONS:
            perms[p_key] = "allow"
        return perms

    user_perms: dict = {}

    if hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role_perms = user.rol_plataforma.permisos or {}
        if isinstance(role_perms, dict):
            for k in role_perms:
                user_perms[k] = "allow"

    if not user_perms:
        for role_def in DEFAULT_ROLES:
            if role_def["name"].lower() == role:
                for p in role_def["permissions"]:
                    user_perms[p] = "allow"
                break

    return user_perms


def require_module_access(module: str, min_level: str = "read"):
    """Factory: return a FastAPI dependency that checks module-level access.

    Usage: require_module_access("crm", "read") or require_module_access("projects", "edit")
    Maps to the appropriate permission key via MODULE_PERMISSION_MAP.
    """
    module_map = MODULE_PERMISSION_MAP.get(module)
    if not module_map:
        raise ValueError(f"Unknown module: {module}")

    # Resolve the actual permission key for the given level
    perm_key = module_map.get(min_level)
    if not perm_key:
        raise ValueError(f"Unknown permission level '{min_level}' for module '{module}'")

    return require_permission(perm_key)


# ── JWT token creation ─────────────────────────────────────────────────


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = _utcnow()
    expire = now + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "iat": now.timestamp()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(db: Session, user_id: uuid.UUID | str, ip_address: str = None, user_agent: str = None) -> str:
    """Create a cryptographically random refresh token and persist it."""
    token = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(days=settings.refresh_token_expire_days)
    from backend.models_auth import TokenSesion

    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    db.add(
        TokenSesion(
            user_id=user_uuid,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    db.commit()
    return token


def record_session(user_id: uuid.UUID | str, token: str) -> None:
    """Record an active session in Redis."""
    redis_client = get_redis()
    ttl = settings.access_token_expire_minutes * 60
    redis_client.setex(f"session:{user_id}:{token}", ttl, "active")


# ── User resolution dependencies ───────────────────────────────────────


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Resolve the current user from a JWT bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = str(payload.get("sub") or "")
        if not subject:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_exception

    from sqlalchemy.orm import joinedload

    from backend.models_auth import Usuario

    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.rol_plataforma))
        .filter(Usuario.id == user_id)
        .first()
    )

    if user is None:
        raise credentials_exception

    # Set context for RBAC in schemas
    role_str = str(getattr(user, "role", ""))
    if not role_str and hasattr(user, "rol_plataforma"):
        role_str = user.rol_plataforma.nombre if user.rol_plataforma else ""

    user_role_context.set(role_str)
    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    """Require an active (non-disabled) user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ── Permission guard factory ───────────────────────────────────────────


def _has_permission(role: str, user_perms: set | dict, required: str) -> bool:
    """Check if a user has a permission, considering hierarchy.

    Higher-level permissions imply lower-level ones (manage > edit > read).
    """
    if role in {"admin", "administrador"}:
        return True

    module = required.split(":")[0]
    level = required.split(":")[1]

    # Build set of effective permissions from user_perms
    if isinstance(user_perms, dict):
        user_perms = set(user_perms.keys()) if user_perms else set()
    elif not isinstance(user_perms, set):
        user_perms = set(user_perms or [])

    # Direct match
    if required in user_perms:
        return True

    # Hierarchy: higher levels imply lower ones within the same module
    hierarchy = {
        "manage": {"manage", "edit", "read"},
        "edit": {"edit", "read"},
        "read": {"read"},
        "study": {"study", "read"},
        "config": {"config"},
    }

    if level not in hierarchy:
        return required in user_perms

    for user_perm in user_perms:
        user_module = user_perm.split(":")[0] if ":" in user_perm else ""
        user_level = user_perm.split(":")[1] if ":" in user_perm else ""
        if user_module == module and user_level in hierarchy:
            if level in hierarchy.get(user_level, set()):
                return True

    return False


def require_permission(permission: str):
    """Factory: return a FastAPI dependency that checks a specific permission."""

    async def _check(
        current_user=Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        role = normalize_role(str(getattr(current_user, "role", "")))
        if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
            role = normalize_role(current_user.rol_plataforma.nombre)

        user_perms: set[str] = set()

        # Granular permissions from Auth v3 roles.
        if hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
            rol_perms = current_user.rol_plataforma.permisos or {}
            if isinstance(rol_perms, dict):
                user_perms.update(k for k, v in rol_perms.items() if v)

        if _has_permission(role, user_perms, permission):
            return current_user

        # Role-based allowance for platform roles without explicit granular permissions.
        if role in {"admin", "administrador"}:
            return current_user
        if permission.startswith("crm:") and role == "pastor":
            return current_user
        if permission in {"academy:read", "academy:study"} and role in {
            "coordinador",
            "docente",
            "pastor",
            "estudiante",
            "lector",
            "miembro",
            "aspirante",
        }:
            return current_user
        if permission == "academy:edit" and role in {"coordinador", "docente", "pastor"}:
            return current_user
        if permission == "academy:manage" and role in {"coordinador", "pastor"}:
            return current_user
        if permission.startswith("projects:") and role in {
            "coordinador",
            "docente",
            "pastor",
        }:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permisos insuficientes. Se requiere: {permission}",
        )

    return _check


# ── Named guards (convenience aliases) ─────────────────────────────────

require_active_user = get_current_active_user
require_admin = require_permission("system:config")
require_staff_or_admin = require_permission("academy:manage")
require_teacher_or_admin = require_permission("academy:manage")
require_coordinator_or_admin = require_permission("projects:manage")


async def require_pastor_or_admin(
    current_user=Depends(get_current_active_user),
):
    """Require pastor or admin role (CRM-level access)."""
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
        role = normalize_role(current_user.rol_plataforma.nombre)
    if role in {"admin", "administrador", "pastor"}:
        return current_user
    # Permission-based access for custom role names.
    permisos = {}
    if hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
        permisos = current_user.rol_plataforma.permisos or {}
    if permisos.get("system:config") == "allow" or permisos.get("crm:manage") == "allow":
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permisos insuficientes. Se requiere: crm:manage",
    )


# ── Password auth helpers ──────────────────────────────────────────────


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user by email + password. Returns user or False."""
    from backend import crud  # avoid circular import

    user = crud.get_user_by_email(db, email=email)
    if not user:
        return False
    hashed_password = str(getattr(user, "password_hash", ""))
    if not verify_password(password, hashed_password):
        return False
    return user


def hash_password(password: str) -> str:
    """Hash a plaintext password using the platform security helper."""
    from backend.core.security import get_password_hash

    return get_password_hash(password)

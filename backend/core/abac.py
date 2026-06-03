"""
ABAC Middleware — Attribute-Based Access Control para CCF.

Implementa:
1. Regla de Propiedad: LECTOR solo puede acceder/modificar sus propios recursos
2. Bloqueo de escritura: LECTOR no puede modificar estructura académica
3. Decorador require_owner_or_higher para endpoints de recursos personales

Basado en platform_role_definitions como fuente única de roles (Dimensión C).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.database import get_db

log = logging.getLogger(__name__)
settings = get_settings()
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"


# ─── Protected resources (owner-only for LECTOR) ─────────────────────────

PROTECTED_OWNER_RESOURCES = {
    "persona": {"read", "update"},
    "profile": {"read", "update"},
    "communication_log": {"read"},
    "enrollment": {"read"},
    "assignment_submission": {"read", "create", "update"},
    "forum_comment": {"read", "create", "update"},
    "assessment_attempt": {"read", "create"},
}

# Academy structure tables that LECTOR cannot modify
ACADEMY_STRUCTURE_TABLES = {
    "academy_courses": {"create", "update", "delete"},
    "academy_lessons": {"create", "update", "delete"},
    "academy_assessments": {"create", "update", "delete"},
    "academy_assessment_questions": {"create", "update", "delete"},
    "academy_assessment_options": {"create", "update", "delete"},
}

# LECTOR can only read the structure
LECTOR_ACADEMY_STRUCTURE_PERMISSIONS = {"read"}

# Module -> allowed operations for LECTOR
LECTOR_MODULE_ACCESS = {
    "crm": ["read"],
    "academy": ["read"],  # Can read course catalog, enroll, but no structure writes
    "projects": ["read"],
    "evangelism": ["read"],
    "cms": ["read"],
    "community": ["read"],
    "agenda": ["read"],
    "profile": ["read", "update"],  # Own profile only
}


# ─── Helper functions ────────────────────────────────────────────────────

def get_current_user_id(request: Request) -> Optional[str]:
    """Extract user UUID from JWT token in cookie or Authorization header."""
    token = request.cookies.get(settings.access_token_cookie_name) or ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def get_current_platform_role(request: Request) -> str:
    """Extract platform_role from JWT token."""
    token = request.cookies.get(settings.access_token_cookie_name) or ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        return "LECTOR"

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("platform_role", "LECTOR")
    except JWTError:
        return "LECTOR"


def require_auth(request: Request) -> str:
    """Dependency: require valid authenticated user, return user_id."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


# ─── Decorador: require_owner_or_higher ──────────────────────────────────

def require_owner_or_higher(
    resource: str,
    operation: str,
    resource_id_param: str = "persona_id",
    param_source: str = "path",
):
    """
    Decorator / dependency factory que valida propiedad del recurso.

    Para LECTOR: el resource_id_param debe coincidir con el user_id del JWT.
    Para EDITOR/GESTOR/ADMINISTRADOR: acceso completo.

    Args:
        resource: nombre del recurso (ej: "persona", "profile", "enrollment")
        operation: "read" | "create" | "update" | "delete"
        resource_id_param: nombre del parámetro con el ID del recurso
        param_source: "path" | "query" | "body"
    """

    async def _dependency(
        request: Request,
        db: Session = Depends(get_db),
    ):
        user_id = get_current_user_id(request)
        role = get_current_platform_role(request)

        if not user_id:
            raise HTTPException(status_code=401, detail="No autenticado")

        # ADMINISTRADOR y GESTOR tienen acceso completo
        if role in ("ADMINISTRADOR", "GESTOR"):
            return user_id

        # EDITOR: permisos según módulo
        if role == "EDITOR":
            module = resource.split("_")[0] if "_" in resource else resource
            if operation in LECTOR_MODULE_ACCESS.get(module, []):
                return user_id
            raise HTTPException(status_code=403, detail=f"EDITOR no puede {operation} {resource}")

        # LECTOR: solo owner-access
        if role == "LECTOR":
            # Bloquear escritura en estructura académica
            if resource in ACADEMY_STRUCTURE_TABLES:
                if operation in ACADEMY_STRUCTURE_TABLES[resource]:
                    raise HTTPException(
                        status_code=403,
                        detail="No tienes permisos para modificar la estructura del curso",
                    )

            # Verificar regla de propiedad
            if operation in ("read", "update"):
                # Extraer resource_id del request
                resource_id = None
                if param_source == "path":
                    resource_id = request.path_params.get(resource_id_param)
                elif param_source == "query":
                    resource_id = request.query_params.get(resource_id_param)

                if resource_id and resource_id != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail=f"No puedes acceder a {resource} de otra persona",
                    )

            return user_id

        # Fallback
        return user_id

    return _dependency


# ─── Middleware helper para verificar permisos en endpoints Academy ──────

def check_academy_write_permission(role: str, table: str) -> bool:
    """
    Verifica si un rol puede escribir en tablas de estructura académica.
    Solo ADMINISTRADOR y GESTOR pueden.
    """
    if role in ("ADMINISTRADOR",):
        return True
    if role == "GESTOR" and table.replace("academy_", "") in ("courses", "lessons", "assessments"):
        return True
    return False


# ─── Authorization dependency self-contained ────────────────────────────

async def authorize(
    request: Request,
    required_role: Optional[str] = None,
    required_permission: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Dependencia universal de autorización.
    
    Args:
        required_role: rol mínimo requerido (ADMINISTRADOR, GESTOR, EDITOR, LECTOR)
        required_permission: permiso específico (ej: "crm:read", "academy:write")
    
    Returns: user_id del usuario autenticado
    """
    user_id = get_current_user_id(request)
    role = get_current_platform_role(request)

    if not user_id:
        raise HTTPException(status_code=401, detail="No autenticado")

    # Si se requiere un rol mínimo, verificar jerarquía
    if required_role:
        role_hierarchy = {
            "ADMINISTRADOR": 4,
            "GESTOR": 3,
            "EDITOR": 2,
            "LECTOR": 1,
        }
        user_level = role_hierarchy.get(role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere rol {required_role} o superior (tienes: {role})",
            )

    # Si se requiere un permiso específico, verificar
    if required_permission:
        allowed = _check_permission(role, required_permission)
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail=f"No tienes permiso: {required_permission}",
            )

    return user_id


def _check_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission based on platform_role_definitions."""
    
    MODULE_PERMISSIONS = {
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
    }

    if role not in MODULE_PERMISSIONS:
        return False

    # Parse permission like "crm:read" or "academy:write"
    if ":" in permission:
        module, op = permission.split(":", 1)
    else:
        module, op = permission, "read"

    role_perms = MODULE_PERMISSIONS[role]

    # ADMIN has all
    if "*" in role_perms:
        return True

    # Check if module has the operation
    if module in role_perms:
        if op in role_perms[module]:
            return True

    return False

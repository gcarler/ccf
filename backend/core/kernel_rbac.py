"""Motor RBAC del Kernel CCF — Integra Dimensión C con permisos granulares.

Este motor calcula permisos efectivos combinando:
1. Roles de plataforma del Kernel (ADMINISTRADOR, GESTOR, EDITOR, LECTOR)
2. Permisos del modelo de roles y roles textuales
3. Roles de Auth v3

Resolución: Kernel de Personas + Auth v3
"""

from __future__ import annotations

import logging
from typing import Dict, Set
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.permissions import get_current_active_user, normalize_role

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# PERMISOS POR ROL DE PLATAFORMA (KERNEL Dimensión C)
# ──────────────────────────────────────────────

KERNEL_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "ADMINISTRADOR": {
        "system:config",
        "crm:manage", "crm:read", "crm:edit",
        "academy:manage", "academy:read", "academy:edit", "academy:study",
        "projects:manage", "projects:read", "projects:edit",
        "evangelism:manage", "evangelism:read", "evangelism:edit",
        "cms:manage", "cms:read", "cms:edit",
        "finances:manage", "finances:read", "finances:edit",
        "community:manage", "community:read", "community:edit",
        "agenda:manage", "agenda:read", "agenda:edit",
        "support:manage", "support:read",
        "spiritual_life:manage", "spiritual_life:read", "spiritual_life:edit",
        "profile:manage",
        "messaging:edit", "messaging:read",
        "governance:manage", "governance:read",
    },
    "GESTOR": {
        "crm:manage", "crm:read", "crm:edit",
        "academy:manage", "academy:read", "academy:edit",
        "projects:manage", "projects:read", "projects:edit",
        "evangelism:manage", "evangelism:read", "evangelism:edit",
        "cms:read", "cms:edit",
        "community:manage", "community:read", "community:edit",
        "agenda:read", "agenda:edit",
        "finances:read",
        "profile:manage",
        "messaging:edit", "messaging:read",
    },
    "EDITOR": {
        "crm:read", "crm:edit",
        "academy:read",
        "projects:read", "projects:edit",
        "evangelism:read", "evangelism:edit",
        "cms:read", "cms:edit",
        "community:read", "community:edit",
        "agenda:read",
        "profile:manage",
        "messaging:read",
    },
    "LECTOR": {
        "academy:study",
        "profile:manage",
    },
}


def _resolve_kernel_permissions(db: Session, user_id: UUID) -> Set[str]:
    """Resuelve permisos desde el Kernel (Dimensión C)."""
    from backend.crud.kernel import get_persona_effective_permissions

    perms_dict = get_persona_effective_permissions(db, str(user_id))
    result: Set[str] = set()

    for module, actions in perms_dict.items():
        if module == "*":
            # Wildcard: todos los permisos
            result.update(KERNEL_ROLE_PERMISSIONS.get("ADMINISTRADOR", set()))
        else:
            for action in actions:
                perm_key = f"{module}:{action}"
                result.add(perm_key)

    return result


def _resolve_role_model_permissions(db: Session, user) -> Set[str]:
    """Resuelve permisos desde roles textuales y Role model."""
    from backend.core.permissions import DEFAULT_ROLES, get_user_effective_permissions

    result: Set[str] = set()

    role_permissions = get_user_effective_permissions(db, user)
    for perm_key, value in role_permissions.items():
        if value == "allow":
            result.add(perm_key)

    if not result:
        role = normalize_role(getattr(user, "role", ""))
        for role_def in DEFAULT_ROLES:
            if role_def["name"].lower() == role:
                for p in role_def["permissions"]:
                    result.add(p)
                break

    return result


def resolve_effective_permissions(
    db: Session, user
) -> Set[str]:
    """Calcula los permisos efectivos de un usuario.

    Orden de resolución:
    1. Kernel de Personas (dimensión de plataforma)
    2. Rol Auth v3
    3. Nombre de rol canónico

    El resultado es la UNIÓN de todos los permisos resueltos.
    """
    kernel_perms = _resolve_kernel_permissions(db, user.id)
    role_model_perms = _resolve_role_model_permissions(db, user)

    return kernel_perms | role_model_perms


def has_permission(
    db: Session, user, permission: str
) -> bool:
    """Verifica si un usuario tiene un permiso específico.

    También verifica el estado vital — usuarios INACTIVOS no tienen permisos.
    """
    from backend.crud.kernel import is_persona_active
    if not is_persona_active(db, str(user.id)):
        return False

    effective = resolve_effective_permissions(db, user)

    # Verificar permiso directo
    if permission in effective:
        return True

    # Wildcard admin
    if "system:config" in effective:
        return True

    # Jerarquía: manage implica edit y read
    module, level = permission.split(":", 1) if ":" in permission else (permission, "")
    hierarchy = {
        "manage": {"manage", "edit", "read"},
        "edit": {"edit", "read"},
        "read": {"read"},
        "study": {"study", "read"},
    }

    if level in hierarchy:
        for eff_perm in effective:
            if ":" in eff_perm:
                eff_module, eff_level = eff_perm.split(":", 1)
                if eff_module == module and eff_level in hierarchy:
                    if level in hierarchy.get(eff_level, set()):
                        return True

    return False


# ──────────────────────────────────────────────
# DEPENDENCIAS FASTAPI
# ──────────────────────────────────────────────

def require_kernel_permission(permission: str):
    """Factory: dependencia FastAPI que verifica un permiso del Kernel.

    Combina verificación de Kernel RBAC + estado vital + permisos por rol.
    """

    async def _check(
        current_user=Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        if has_permission(db, current_user, permission):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permisos insuficientes. Se requiere: {permission}",
        )

    return _check


def require_kernel_module_access(module: str, min_level: str = "read"):
    """Factory: dependencia FastAPI que verifica acceso a un módulo del Kernel.

    Equivalente a require_module_access pero con resolución Kernel-aware.
    """
    permission = f"{module}:{min_level}"
    return require_kernel_permission(permission)


def require_active_for_assignment():
    """Verifica que un usuario está ACTIVO y puede recibir asignaciones.

    Regla de Inactividad: Usuarios INACTIVOS no pueden ser delegados
    en tareas de proyectos, ni aparecer en listas de selección activa.
    """

    async def _check(
        current_user=Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        from backend.crud.kernel import is_persona_active
        if is_persona_active(db, str(current_user.id)):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario INACTIVO: no puede recibir nuevas asignaciones",
        )

    return _check

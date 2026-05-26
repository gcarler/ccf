"""CCF MESH - ROUTER DE IDENTIDAD KERNEL

Endpoints para el Protocolo de Identidad y Roles (Kernel CCF).

- Estado Vital (ACTIVO/INACTIVO)
- Dimensión A: Ministerios (Efesios 4:11)
- Dimensión B: Roles en la Iglesia (embudo)
- Dimensión C: Roles de Plataforma (RBAC)
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.kernel_rbac import (require_kernel_permission,
                                       require_active_for_assignment)
from backend.core.permissions import require_active_user

log = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter(prefix="/api/kernel", tags=["Kernel Identidad"])


# ──────────────────────────────────────────────
# PYDANTIC SCHEMAS (inline para evitar dependencia circular)
# ──────────────────────────────────────────────


class MinistryCreate(BaseModel):
    ministry: str
    is_primary: bool = False
    notes: Optional[str] = None


class ChurchRoleUpdate(BaseModel):
    church_role: str
    reason: Optional[str] = None
    notes: Optional[str] = None


class PlatformRoleAssign(BaseModel):
    platform_role: str
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ActivityStatusUpdate(BaseModel):
    status: str  # "ACTIVO" or "INACTIVO"


# ──────────────────────────────────────────────
# PERFIL COMPLETO KERNEL
# ──────────────────────────────────────────────

@router.get("/profile/{user_id}")
def get_kernel_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Retorna el perfil completo del Kernel para un usuario."""
    from backend.crud import kernel as kernel_crud

    # Solo admin o el propio usuario pueden ver el perfil kernel
    if current_user.id != user_id:
        role = str(getattr(current_user, "role", "")).lower()
        if role not in ("admin", "pastor"):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Solo el propio usuario o un admin/pastor puede "
                    "ver el perfil kernel"
                ),
            )

    profile = kernel_crud.get_kernel_profile(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return profile


@router.get("/profile/me")
def get_my_kernel_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Retorna el perfil kernel del usuario autenticado."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_kernel_profile(db, current_user.id)


# ──────────────────────────────────────────────
# ESTADO VITAL
# ──────────────────────────────────────────────

@router.put("/status/{user_id}")
def update_activity_status(
    user_id: int,
    payload: ActivityStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Cambia el estado vital de un usuario (ACTIVO/INACTIVO)."""
    from backend.crud import kernel as kernel_crud

    if payload.status not in ("ACTIVO", "INACTIVO"):
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido: {payload.status}. Debe ser ACTIVO o INACTIVO",
        )

    user = kernel_crud.set_user_activity_status(
        db, user_id, payload.status, changed_by_id=current_user.id
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "user_id": user.id,
        "estado_vital": payload.status,
        "message": f"Estado vital cambiado a {payload.status}",
    }


# ──────────────────────────────────────────────
# DIMENSIÓN A: MINISTERIOS (EFESIOS 4:11)
# ──────────────────────────────────────────────

@router.get("/ministries/{user_id}")
def get_ministries(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Retorna los ministerios reconocidos de un usuario."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_user_ministries(db, user_id)


@router.post("/ministries/{user_id}")
def add_ministry(
    user_id: int,
    payload: MinistryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Agrega un ministerio reconocido a un usuario."""
    from backend.crud import kernel as kernel_crud

    result = kernel_crud.add_user_ministry(
        db,
        user_id=user_id,
        ministry=payload.ministry,
        is_primary=payload.is_primary,
        recognized_by_id=current_user.id,
        notes=payload.notes,
    )
    if not result:
        raise HTTPException(
            status_code=400,
            detail="El usuario ya tiene este ministerio o el ministerio es inválido",
        )
    return result


@router.delete("/ministries/{user_id}/{ministry}")
def remove_ministry(
    user_id: int,
    ministry: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Elimina un ministerio reconocido de un usuario."""
    from backend.crud import kernel as kernel_crud

    if not kernel_crud.remove_user_ministry(db, user_id, ministry):
        raise HTTPException(
            status_code=404,
            detail="Ministerio no encontrado para este usuario",
        )
    return {"message": f"Ministerio {ministry} eliminado"}


@router.put("/ministries/{user_id}/{ministry}/primary")
def set_primary_ministry(
    user_id: int,
    ministry: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Establece un ministerio como principal."""
    from backend.crud import kernel as kernel_crud

    if not kernel_crud.set_primary_ministry(db, user_id, ministry):
        raise HTTPException(
            status_code=404,
            detail="Ministerio no encontrado para este usuario",
        )
    return {"message": f"Ministerio {ministry} establecido como principal"}


# ──────────────────────────────────────────────
# DIMENSIÓN B: ROLES EN LA IGLESIA
# ──────────────────────────────────────────────

@router.get("/church-role/{user_id}")
def get_church_role(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Retorna el rol actual en la iglesia de un usuario."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_user_church_role(db, user_id)


@router.put("/church-role/{user_id}")
def update_church_role(
    user_id: int,
    payload: ChurchRoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Cambia el rol en la iglesia de un usuario."""
    from backend.crud import kernel as kernel_crud

    result = kernel_crud.set_user_church_role(
        db,
        user_id=user_id,
        church_role=payload.church_role,
        changed_by_id=current_user.id,
        reason=payload.reason,
        notes=payload.notes,
    )
    if not result:
        raise HTTPException(status_code=400, detail="No se pudo actualizar el rol")
    return result


@router.get("/church-role/{user_id}/history")
def get_church_role_history(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Retorna el historial de cambios de rol de iglesia."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_church_role_history(db, user_id, limit=limit)


@router.get("/church-role/{role}/users")
def get_users_by_role(
    role: str,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("crm:read")),
):
    """Retorna todos los usuarios con un rol de iglesia específico."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_users_by_church_role(db, role, active_only=active_only)


# ──────────────────────────────────────────────
# DIMENSIÓN C: ROLES DE PLATAFORMA
# ──────────────────────────────────────────────

@router.get("/platform-roles")
def get_platform_role_definitions(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Retorna todas las definiciones de roles de plataforma."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_platform_role_definitions(db)


@router.get("/platform-roles/{user_id}")
def get_user_platform_roles(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Retorna los roles de plataforma de un usuario."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_user_platform_roles(db, user_id)


@router.get("/permissions/{user_id}")
def get_user_effective_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Calcula y retorna los permisos efectivos de un usuario."""
    from backend.crud import kernel as kernel_crud

    if current_user.id != user_id:
        role = str(getattr(current_user, "role", "")).lower()
        if role not in ("admin", "pastor"):
            raise HTTPException(status_code=403, detail="Acceso denegado")

    return kernel_crud.get_user_effective_permissions(db, user_id)


@router.post("/platform-roles/{user_id}")
def assign_platform_role(
    user_id: int,
    payload: PlatformRoleAssign,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Asigna un rol de plataforma a un usuario."""
    from backend.crud import kernel as kernel_crud

    result = kernel_crud.assign_platform_role(
        db,
        user_id=user_id,
        platform_role=payload.platform_role,
        assigned_by_id=current_user.id,
        expires_at=payload.expires_at,
        notes=payload.notes,
    )
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Rol inválido o el usuario ya tiene este rol activo",
        )
    return result


@router.delete("/platform-roles/{user_id}/{platform_role}")
def revoke_platform_role(
    user_id: int,
    platform_role: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Revoca un rol de plataforma de un usuario."""
    from backend.crud import kernel as kernel_crud

    if not kernel_crud.revoke_platform_role(db, user_id, platform_role):
        raise HTTPException(
            status_code=404,
            detail="Rol no encontrado para este usuario",
        )
    return {"message": f"Rol {platform_role} revocado"}


# ──────────────────────────────────────────────
# VERIFICACIÓN DE ASIGNACIÓN (REGLA DE INACTIVIDAD)
# ──────────────────────────────────────────────

@router.get("/can-assign/{user_id}")
def check_can_receive_assignment(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_for_assignment()),
):
    """Verifica si un usuario puede recibir nuevas asignaciones.

    Regla de Inactividad: Usuarios INACTIVOS no pueden ser delegados.
    """
    from backend.crud import kernel as kernel_crud

    can_assign = kernel_crud.can_receive_assignment(db, user_id)
    return {
        "user_id": user_id,
        "can_receive_assignment": can_assign,
    }

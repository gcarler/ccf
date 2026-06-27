"""Kernel — Router de Identidad

Endpoints del Protocolo de Identidad y Roles, centrados en Persona (UUID).

- Estado Vital (ACTIVO/INACTIVO)
- Dimensión A: Ministerios (Efesios 4:11)
- Dimensión B: Roles en la Iglesia (embudo)
- Dimensión C: Roles de Plataforma (RBAC)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.crud._utils import _utcnow
from backend.crud.crm import resolve_persona_id_for_user
from backend.core.kernel_rbac import (
    require_kernel_permission,
    require_active_for_assignment,
)
from backend.core.permissions import require_active_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/kernel", tags=["Kernel Identidad"])


# ──────────────────────────────────────────────
# SCHEMAS
# ──────────────────────────────────────────────


class MinistryCreate(BaseModel):
    ministry: str
    is_primary: bool = False
    notes: Optional[str] = None


class ChurchRoleUpdate(BaseModel):
    church_role: str
    reason: Optional[str] = None
    notes: Optional[str] = None


class ActivityStatusUpdate(BaseModel):
    status: str


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────


def _resolve_persona_id(db: Session, current_user, persona_id: str) -> str:
    """Permite que un admin/pastor actúe sobre cualquier persona_id.
    Un usuario normal solo puede actuar sobre su propia persona."""
    from backend import models
    import uuid as _uuid

    target = db.query(models.Persona).filter(models.Persona.id == _uuid.UUID(persona_id)).first()
    if not target:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    current_persona_id = resolve_persona_id_for_user(db, current_user.id)

    # Acceso propio: solo si la persona corresponde al usuario actual
    if current_persona_id and str(target.id) == str(current_persona_id):
        return persona_id

    role = str(getattr(current_user, "role", "")).lower()
    if not role and getattr(current_user, "rol_plataforma", None):
        role = str(getattr(current_user.rol_plataforma, "nombre", "")).lower()
    if role not in ("admin", "administrador", "pastor"):
        raise HTTPException(
            status_code=403,
            detail="Solo el propio usuario o un admin/pastor puede acceder a este perfil",
        )
    return persona_id


def _my_persona_id(db: Session, current_user) -> str:
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    if not persona_id:
        raise HTTPException(status_code=404, detail="No tiene un perfil de persona asociado")
    return str(persona_id)


# ──────────────────────────────────────────────
# PERFIL COMPLETO KERNEL
# ──────────────────────────────────────────────


@router.get("/profile/me")
def get_my_kernel_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from backend.crud import kernel as kernel_crud

    persona_id = _my_persona_id(db, current_user)
    profile = kernel_crud.get_kernel_profile(db, persona_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return profile


@router.get("/profile/{persona_id}")
def get_kernel_profile(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from backend.crud import kernel as kernel_crud

    _resolve_persona_id(db, current_user, persona_id)
    profile = kernel_crud.get_kernel_profile(db, persona_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return profile


# ──────────────────────────────────────────────
# ESTADO VITAL
# ──────────────────────────────────────────────


@router.put("/status/{persona_id}")
def update_activity_status(
    persona_id: str,
    payload: ActivityStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    from backend.crud import kernel as kernel_crud

    if payload.status not in ("ACTIVO", "INACTIVO"):
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido: {payload.status}. Debe ser ACTIVO o INACTIVO",
        )
    persona = kernel_crud.set_persona_activity_status(db, persona_id, payload.status, changed_by_persona_id=None)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return {
        "persona_id": persona_id,
        "estado_vital": payload.status,
        "message": f"Estado vital cambiado a {payload.status}",
    }


# ──────────────────────────────────────────────
# DIMENSIÓN A: MINISTERIOS
# ──────────────────────────────────────────────


@router.get("/ministries/me")
def get_my_ministries(db: Session = Depends(get_db), current_user=Depends(require_active_user)):
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_persona_ministries(db, _my_persona_id(db, current_user))


@router.get("/ministries/{persona_id}")
def get_ministries(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from backend.crud import kernel as kernel_crud

    _resolve_persona_id(db, current_user, persona_id)
    return kernel_crud.get_persona_ministries(db, persona_id)


@router.post("/ministries/{persona_id}")
def add_ministry(
    persona_id: str,
    payload: MinistryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    from backend.crud import kernel as kernel_crud

    persona_id = resolve_persona_id_for_user(db, current_user.id)
    if not persona_id:
        raise HTTPException(status_code=404, detail="No tiene un perfil de persona asociado")
    result = kernel_crud.add_persona_ministry(
        db,
        persona_id=persona_id,
        ministry=payload.ministry,
        is_primary=payload.is_primary,
        recognized_by_persona_id=str(persona_id) if persona_id else None,
        notes=payload.notes,
    )
    if not result:
        raise HTTPException(
            status_code=400,
            detail="La persona ya tiene este ministerio o el ministerio es inválido",
        )
    return result


@router.delete("/ministries/{persona_id}/{ministry}")
def remove_ministry(
    persona_id: str,
    ministry: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    from backend.crud import kernel as kernel_crud

    if not kernel_crud.remove_persona_ministry(db, persona_id, ministry):
        raise HTTPException(status_code=404, detail="Ministerio no encontrado para esta persona")
    return {"message": f"Ministerio {ministry} eliminado"}


@router.put("/ministries/{persona_id}/{ministry}/primary")
def set_primary_ministry(
    persona_id: str,
    ministry: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    from backend.crud import kernel as kernel_crud

    if not kernel_crud.set_primary_ministry(db, persona_id, ministry):
        raise HTTPException(status_code=404, detail="Ministerio no encontrado para esta persona")
    return {"message": f"Ministerio {ministry} establecido como principal"}


# ──────────────────────────────────────────────
# DIMENSIÓN B: ROL EN LA IGLESIA
# ──────────────────────────────────────────────


@router.get("/church-role/me")
def get_my_church_role(db: Session = Depends(get_db), current_user=Depends(require_active_user)):
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_persona_church_role(db, _my_persona_id(db, current_user))


@router.get("/church-role/{persona_id}")
def get_church_role(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from backend.crud import kernel as kernel_crud

    _resolve_persona_id(db, current_user, persona_id)
    return kernel_crud.get_persona_church_role(db, persona_id)


@router.put("/church-role/{persona_id}")
def update_church_role(
    persona_id: str,
    payload: ChurchRoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    from backend.crud import kernel as kernel_crud
    from backend.models_kernel import ChurchRole

    valid_roles = [r.value for r in ChurchRole]
    if payload.church_role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido: {payload.church_role}. Válidos: {valid_roles}",
        )
    result = kernel_crud.set_persona_church_role(
        db,
        persona_id=persona_id,
        church_role=payload.church_role,
        changed_by_persona_id=None,
        reason=payload.reason,
        notes=payload.notes,
    )
    if not result:
        raise HTTPException(status_code=400, detail="No se pudo actualizar el rol")
    return result


@router.get("/church-role/{persona_id}/history")
def get_church_role_history(
    persona_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from backend.crud import kernel as kernel_crud

    _resolve_persona_id(db, current_user, persona_id)
    return kernel_crud.get_church_role_history(db, persona_id, limit=limit)


@router.get("/church-role-by/{role}/personas")
def get_personas_by_role(
    role: str,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("crm:read")),
):
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_personas_by_church_role(db, role, active_only=active_only)


# ──────────────────────────────────────────────
# DIMENSIÓN C: ROLES DE PLATAFORMA
# ──────────────────────────────────────────────


@router.get("/platform-roles")
def get_platform_role_definitions(db: Session = Depends(get_db), current_user=Depends(require_active_user)):
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_platform_role_definitions(db)


@router.get("/platform-roles/me")
def get_my_platform_roles(db: Session = Depends(get_db), current_user=Depends(require_active_user)):
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_persona_platform_roles(db, _my_persona_id(db, current_user))


@router.get("/platform-roles/{persona_id}")
def get_persona_platform_roles(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from backend.crud import kernel as kernel_crud

    _resolve_persona_id(db, current_user, persona_id)
    return kernel_crud.get_persona_platform_roles(db, persona_id)


@router.get("/permissions/me")
def get_my_permissions(db: Session = Depends(get_db), current_user=Depends(require_active_user)):
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_persona_effective_permissions(db, _my_persona_id(db, current_user))


@router.get("/permissions/{persona_id}")
def get_persona_permissions(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from backend.crud import kernel as kernel_crud

    _resolve_persona_id(db, current_user, persona_id)
    return kernel_crud.get_persona_effective_permissions(db, persona_id)


# ──────────────────────────────────────────────
# VERIFICACIÓN DE ASIGNACIÓN
# ──────────────────────────────────────────────


@router.get("/can-assign/{persona_id}")
def check_can_receive_assignment(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_for_assignment()),
):
    from backend.crud import kernel as kernel_crud

    can_assign = kernel_crud.can_receive_assignment(db, persona_id)
    return {"persona_id": persona_id, "can_receive_assignment": can_assign}


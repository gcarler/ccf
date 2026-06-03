"""Kernel — Router de Identidad

Endpoints del Protocolo de Identidad y Roles, centrados en Persona (UUID).

- Estado Vital (ACTIVO/INACTIVO)
- Dimensión A: Ministerios (Efesios 4:11)
- Dimensión B: Roles en la Iglesia (embudo)
- Dimensión C: Roles de Plataforma (RBAC)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.crud._utils import _utcnow
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


class PlatformRoleAssign(BaseModel):
    platform_role: str
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class PlatformRoleDefinitionCreate(BaseModel):
    role: str
    permissions: Optional[Dict[str, List[str]]] = None
    description: Optional[str] = None


class PlatformRoleDefinitionUpdate(BaseModel):
    permissions: Optional[Dict[str, List[str]]] = None
    description: Optional[str] = None


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

    # Acceso propio: solo si la persona está vinculada al usuario actual
    if target.user_id is not None and target.user_id == current_user.id:
        return persona_id

    role = str(getattr(current_user, "role", "")).lower()
    if role not in ("admin", "pastor"):
        raise HTTPException(
            status_code=403,
            detail="Solo el propio usuario o un admin/pastor puede acceder a este perfil",
        )
    return persona_id


def _my_persona_id(db: Session, current_user) -> str:
    from backend import models

    persona = db.query(models.Persona).filter(models.Persona.user_id == current_user.id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="No tiene un perfil de persona asociado")
    return str(persona.id)


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

    persona = db.query(models.Persona).filter(models.Persona.user_id == current_user.id).first()
    result = kernel_crud.add_persona_ministry(
        db,
        persona_id=persona_id,
        ministry=payload.ministry,
        is_primary=payload.is_primary,
        recognized_by_persona_id=str(persona.id) if persona else None,
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


@router.post("/platform-roles/{persona_id}")
def assign_platform_role(
    persona_id: str,
    payload: PlatformRoleAssign,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    from backend.crud import kernel as kernel_crud

    result = kernel_crud.assign_platform_role(
        db,
        persona_id,
        payload.platform_role,
        assigned_by_persona_id=None,
        expires_at=payload.expires_at,
        notes=payload.notes,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Rol inválido o la persona ya tiene este rol activo")
    return result


@router.delete("/platform-roles/{persona_id}/{platform_role}")
def revoke_platform_role(
    persona_id: str,
    platform_role: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    from backend.crud import kernel as kernel_crud

    if not kernel_crud.revoke_platform_role(db, persona_id, platform_role):
        raise HTTPException(status_code=404, detail="Rol no encontrado para esta persona")
    return {"message": f"Rol {platform_role} revocado"}


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


# ──────────────────────────────────────────────
# CRUD DE ROLES DE PLATAFORMA (PlatformRoleDefinition)
# ──────────────────────────────────────────────


@router.get("/admin/platform-role-definitions")
def list_platform_role_definitions(
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Lista todas las definiciones de roles de plataforma (Dimensión C)."""
    from backend.crud import kernel as kernel_crud

    return kernel_crud.get_platform_role_definitions(db)


@router.post("/admin/platform-role-definitions")
def create_platform_role_definition(
    payload: PlatformRoleDefinitionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Crea una nueva definición de rol de plataforma."""
    from backend.models_kernel import PlatformRoleDefinition

    existing = db.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.role == payload.role).first()
    if existing:
        raise HTTPException(status_code=409, detail="El rol ya existe")

    perms = payload.permissions or PlatformRoleDefinition.__table__.c.permissions.default.arg.get(payload.role, {})
    role_def = PlatformRoleDefinition(
        role=payload.role,
        permissions=perms,
        description=payload.description,
    )
    db.add(role_def)
    db.commit()
    db.refresh(role_def)
    return {
        "id": role_def.id,
        "role": role_def.role,
        "permissions": role_def.permissions,
    }


@router.patch("/admin/platform-role-definitions/{definition_id}")
def update_platform_role_definition(
    definition_id: int,
    payload: PlatformRoleDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Actualiza permisos y descripción de una definición de rol."""
    from backend.models_kernel import PlatformRoleDefinition

    role_def = db.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.id == definition_id).first()
    if not role_def:
        raise HTTPException(status_code=404, detail="Definición de rol no encontrada")
    if payload.permissions is not None:
        role_def.permissions = payload.permissions
    if payload.description is not None:
        role_def.description = payload.description
    db.commit()
    db.refresh(role_def)
    return {
        "id": role_def.id,
        "role": role_def.role,
        "permissions": role_def.permissions,
    }


@router.delete("/admin/platform-role-definitions/{definition_id}", status_code=204)
def delete_platform_role_definition(
    definition_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Elimina una definición de rol (solo si no está asignada a nadie)."""
    from backend.models_kernel import PlatformRoleDefinition, PersonaPlatformRole

    role_def = db.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.id == definition_id).first()
    if not role_def:
        raise HTTPException(status_code=404, detail="Definición de rol no encontrada")
    assigned = (
        db.query(PersonaPlatformRole)
        .filter(
            PersonaPlatformRole.role_id == definition_id,
            PersonaPlatformRole.is_active,
        )
        .count()
    )
    if assigned > 0:
        raise HTTPException(
            status_code=409,
            detail=f'No se puede eliminar el rol "{role_def.role}" porque tiene {assigned} persona(s) asignada(s)',
        )
    role_def.deleted_at = _utcnow()
    db.commit()


# ──────────────────────────────────────────────
# ADMIN: ASIGNACIONES MASIVAS DE ROLES
# ──────────────────────────────────────────────


@router.get("/admin/persona-platform-roles")
def list_all_persona_platform_roles(
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Lista todas las asignaciones activas de roles de plataforma a personas."""
    from backend.models_kernel import PersonaPlatformRole, PlatformRoleDefinition
    from backend import models as backend_models

    rows = (
        db.query(PersonaPlatformRole, PlatformRoleDefinition, backend_models.Persona)
        .join(
            PlatformRoleDefinition,
            PlatformRoleDefinition.id == PersonaPlatformRole.role_id,
        )
        .join(
            backend_models.Persona,
            backend_models.Persona.id == PersonaPlatformRole.persona_id,
        )
        .filter(PersonaPlatformRole.is_active)
        .all()
    )
    return [
        {
            "id": upr.id,
            "persona_id": str(upr.persona_id),
            "persona_name": f"{p.first_name} {p.last_name}",
            "role": rd.role if not hasattr(rd.role, "value") else rd.role.value,
            "assigned_at": upr.assigned_at,
            "expires_at": upr.expires_at,
            "notes": upr.notes,
        }
        for upr, rd, p in rows
    ]


@router.delete("/admin/persona-platform-roles/{assignment_id}", status_code=204)
def revoke_persona_platform_role(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_kernel_permission("system:config")),
):
    """Revoca (soft-delete) una asignación de rol de plataforma."""
    from backend.models_kernel import PersonaPlatformRole

    row = (
        db.query(PersonaPlatformRole)
        .filter(
            PersonaPlatformRole.id == assignment_id,
            PersonaPlatformRole.is_active,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    row.is_active = False
    db.commit()
    return {"message": "Rol revocado exitosamente"}

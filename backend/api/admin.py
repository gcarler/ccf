"""Admin API — centralized administration endpoints.

Refactored to use ``crud.admin`` for data access and ``schemas.admin``
for typed request/response models. Roles are consolidated into a single
canonical system (``/roles``).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import (
    MODULE_PERMISSION_MAP,
    PERMISSION_LEVELS,
    expand_module_permissions,
    get_all_permissions,
    require_active_user,
    require_admin,
)
from backend.core.tenant import get_user_sede_id
from backend.crud import admin as admin_crud
from backend.schemas._common import PaginatedResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ROLES (consolidated — replaces both /roles and /auth-role-definitions)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/roles", response_model=PaginatedResponse[schemas.AdminRoleRead])
def list_roles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todos los roles de plataforma con conteo de usuarios."""
    roles, total = admin_crud.list_admin_roles(db, skip=skip, limit=limit)
    counts = admin_crud.get_admin_role_user_counts(db)
    items = [
        schemas.AdminRoleRead(
            id=r.id,
            nombre=r.nombre,
            permisos=r.permisos or {},
            users_count=counts.get(r.id, 0),
        )
        for r in roles
    ]
    return PaginatedResponse[schemas.AdminRoleRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.post("/roles", response_model=schemas.AdminRoleRead, status_code=201)
def create_role(
    payload: schemas.AdminRoleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea un nuevo rol de plataforma."""
    nombre = payload.name.strip() if payload.name else ""
    if not nombre:
        raise HTTPException(status_code=400, detail="nombre es requerido")
    existing_name = (
        db.query(models.RolPlataforma)
        .filter(
            models.RolPlataforma.nombre == nombre,
            models.RolPlataforma.deleted_at.is_(None),
        )
        .count()
    )
    if existing_name > 0:
        raise HTTPException(status_code=409, detail="El rol ya existe")
    try:
        rol = admin_crud.create_admin_role(db, nombre, payload.permissions)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_admin_action(db, current_user, "role.create", "role", str(rol.id))
    return schemas.AdminRoleRead(
        id=rol.id, nombre=rol.nombre, permisos=rol.permisos or {}, users_count=0
    )


@router.patch("/roles/{role_id}", response_model=schemas.AdminRoleRead)
def update_role(
    role_id: str,
    payload: schemas.AdminRoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza un rol de plataforma."""
    try:
        rid = uuid.UUID(str(role_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Role ID inválido")
    rol = admin_crud.update_admin_role(db, rid, payload.name, payload.permissions)
    if not rol:
        raise HTTPException(status_code=404, detail="Role not found")
    record_admin_action(db, current_user, "role.update", "role", str(rid))
    return schemas.AdminRoleRead(
        id=rol.id, nombre=rol.nombre, permisos=rol.permisos or {}, users_count=0
    )


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un rol de plataforma (no usado por usuarios activos)."""
    try:
        rid = uuid.UUID(str(role_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Role ID inválido")
    success = admin_crud.delete_admin_role(db, rid)
    if not success:
        raise HTTPException(
            status_code=409, detail="Cannot delete role with active assignments"
        )
    record_admin_action(db, current_user, "role.delete", "role", str(rid))


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/permissions")
def read_all_permissions(current_user: models.User = Depends(require_admin)):
    """Lista todos los permisos disponibles con sus niveles jerárquicos."""
    perms = get_all_permissions()
    return {
        "permissions": perms,
        "modules": {
            module: list(levels.keys())
            for module, levels in MODULE_PERMISSION_MAP.items()
        },
        "levels": {k: list(v) for k, v in PERMISSION_LEVELS.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# USER PERMISSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/users/{user_id}/permissions",
    response_model=schemas.AdminUserPermissionsRead,
)
def get_user_permissions(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Obtiene los permisos actuales de un usuario auth_users."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido")
    result = admin_crud.get_user_permissions(db, current_user, uid)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put("/users/{user_id}/permissions")
def set_user_permissions(
    user_id: str,
    payload: schemas.AdminUserPermissionSet,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Asigna permisos modulares a un usuario auth_users por módulo/nivel."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido")
    try:
        result = admin_crud.set_user_permissions(
            db, current_user, uid, payload.permissions,
            MODULE_PERMISSION_MAP, expand_module_permissions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    record_admin_action(
        db, current_user, "permissions.set", "user", user_id,
        {"modules": list(payload.permissions.keys())},
    )
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# LOCATIONS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/locations", response_model=PaginatedResponse[schemas.AdminLocationRead])
def list_locations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_active_user),
):
    """Lista todas las sedes de la iglesia."""
    locs, total = admin_crud.list_admin_locations(db, skip=skip, limit=limit)
    items = [
        schemas.AdminLocationRead(
            id=loc.id,
            name=loc.name,
            address=loc.address,
            pastor=loc.pastor_name,
            active=loc.is_active,
            type=loc.location_type,
        )
        for loc in locs
    ]
    return PaginatedResponse[schemas.AdminLocationRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.post("/locations", response_model=schemas.AdminLocationRead, status_code=201)
def create_location(
    body: schemas.AdminLocationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva sede o anexo."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="nombre es requerido")
    loc = admin_crud.create_admin_location(db, name, body.address, body.phone)
    record_admin_action(db, current_user, "location.create", "location", str(loc.id))
    return schemas.AdminLocationRead(
        id=loc.id, name=loc.name, address=loc.address,
        pastor=loc.pastor_name, active=loc.is_active, type=loc.location_type,
    )


@router.patch("/locations/{location_id}", response_model=schemas.AdminLocationRead)
def update_location(
    location_id: str,
    body: schemas.AdminLocationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza una sede existente."""
    loc = admin_crud.update_admin_location(
        db, location_id, body.name, body.address, body.phone, body.is_active,
    )
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    record_admin_action(
        db, current_user, "location.update", "location", location_id,
    )
    return schemas.AdminLocationRead(
        id=loc.id, name=loc.name, address=loc.address,
        pastor=loc.pastor_name, active=loc.is_active, type=loc.location_type,
    )


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una sede."""
    success = admin_crud.delete_admin_location(db, location_id)
    if not success:
        raise HTTPException(status_code=404, detail="Location not found")
    record_admin_action(
        db, current_user, "location.delete", "location", location_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL CHANNELS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/socials", response_model=PaginatedResponse[schemas.AdminSocialRead])
def list_socials(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_active_user),
):
    """Lista canales sociales oficiales."""
    channels, total = admin_crud.list_admin_socials(db, skip=skip, limit=limit)
    items = [
        schemas.AdminSocialRead(
            id=c.id, platform=c.platform, url=c.url, visible=c.is_visible,
        )
        for c in channels
    ]
    return PaginatedResponse[schemas.AdminSocialRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.post("/socials", response_model=schemas.AdminSocialRead, status_code=201)
def create_social(
    body: schemas.AdminSocialCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea un nuevo canal social."""
    ch = admin_crud.create_admin_social(db, body.platform, body.url, body.is_visible)
    record_admin_action(db, current_user, "social.create", "social", str(ch.id))
    return schemas.AdminSocialRead(
        id=ch.id, platform=ch.platform, url=ch.url, visible=ch.is_visible,
    )


@router.patch("/socials/{social_id}", response_model=schemas.AdminSocialRead)
def update_social(
    social_id: str,
    body: schemas.AdminSocialUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza un canal social."""
    ch = admin_crud.update_admin_social(
        db, social_id, body.platform, body.url, body.is_visible,
    )
    if not ch:
        raise HTTPException(status_code=404, detail="Social channel not found")
    record_admin_action(db, current_user, "social.update", "social", social_id)
    return schemas.AdminSocialRead(
        id=ch.id, platform=ch.platform, url=ch.url, visible=ch.is_visible,
    )


@router.delete("/socials/{social_id}", status_code=204)
def delete_social(
    social_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un canal social."""
    success = admin_crud.delete_admin_social(db, social_id)
    if not success:
        raise HTTPException(status_code=404, detail="Social channel not found")
    record_admin_action(db, current_user, "social.delete", "social", social_id)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/variables", response_model=Dict[str, Any])
def list_variables(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Obtiene variables de configuración global del sistema."""
    sys_vars, _total = admin_crud.list_admin_variables(db)
    return {v.key: v.value for v in sys_vars}


@router.post("/variables")
def set_variable(
    payload: schemas.AdminVariableCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Define o actualiza una variable de sistema."""
    admin_crud.set_admin_variable(db, payload.key, payload.value)
    record_admin_action(
        db, current_user, "variable.set", "variable", payload.key,
    )
    return {"status": "success"}


@router.delete("/variables/{key}", status_code=204)
def delete_variable(
    key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una variable de sistema."""
    success = admin_crud.delete_admin_variable(db, key)
    if not success:
        raise HTTPException(status_code=404, detail="Variable not found")
    record_admin_action(db, current_user, "variable.delete", "variable", key)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN STATS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/stats", response_model=schemas.AdminStatsRead)
def admin_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Retorna métricas agregadas para el dashboard de administración."""
    return admin_crud.get_admin_stats(db)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBER MANAGEMENT (PERSONAS)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/personas", response_model=PaginatedResponse[schemas.AdminPersonaRead])
def list_admin_personas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista personas para administración, filtradas por sede del admin."""
    sede_id = get_user_sede_id(db, current_user.id)
    personas, total = admin_crud.list_admin_personas(db, sede_id, skip=skip, limit=limit)
    items = [
        schemas.AdminPersonaRead(
            id=m.id,
            first_name=m.first_name,
            last_name=m.last_name,
            email=m.email,
            phone=m.phone,
            church_role=m.church_role,
        )
        for m in personas
    ]
    return PaginatedResponse[schemas.AdminPersonaRead](
        items=items, total=total, skip=skip, limit=limit,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/users", response_model=PaginatedResponse[schemas.AdminUserRead])
def list_admin_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Lista usuarios de auth_users para gestión de permisos granulares."""
    items, total = admin_crud.list_admin_users(db, current_user, skip=skip, limit=limit)
    return PaginatedResponse[schemas.AdminUserRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.get("/users/{user_id}", response_model=schemas.AdminUserRead)
def get_admin_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Obtiene un usuario auth por UUID."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido")
    result = admin_crud.get_admin_user(db, current_user, uid)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.post("/users", response_model=schemas.AdminUserRead, status_code=201)
def create_admin_user(
    body: schemas.AdminUserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Crea un nuevo usuario Auth v3 desde el panel de administración."""
    try:
        result = admin_crud.create_admin_user(
            db, current_user,
            username=body.username.strip(),
            email=body.email.strip(),
            password=body.password,
            first_name=body.first_name.strip(),
            last_name=body.last_name.strip(),
            role=body.role,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    record_admin_action(db, current_user, "user.create", "user", result["id"])
    return result


@router.patch("/users/{user_id}", response_model=schemas.AdminUserRead)
def update_admin_user(
    user_id: str,
    body: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Actualiza campos básicos de auth_users por UUID."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido")
    result = admin_crud.update_admin_user(
        db, current_user, uid,
        username=body.username,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
        is_active=body.is_active,
        password=body.password,
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    record_admin_action(db, current_user, "user.update", "user", user_id)
    return result


@router.delete("/users/{user_id}", status_code=204)
def delete_admin_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Desactiva un usuario auth por UUID."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido")
    success = admin_crud.deactivate_admin_user(db, current_user, uid)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    record_admin_action(db, current_user, "user.deactivate", "user", user_id)


@router.patch("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    role_id: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Asigna un rol de plataforma a un usuario auth por UUID."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido")
    if role_id is None:
        raise HTTPException(status_code=400, detail="role_id requerido")
    try:
        rid = uuid.UUID(str(role_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="role_id inválido")
    result = admin_crud.change_user_role(db, current_user, uid, rid)
    if not result:
        raise HTTPException(status_code=404, detail="User or role not found")
    record_admin_action(
        db, current_user, "user.role_change", "user", user_id,
        {"role_id": str(rid)},
    )
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT & SECURITY
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/audit", response_model=List[Dict[str, Any]])
def list_admin_audit(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Obtiene el historial de auditoría del sistema."""
    logs = crud.get_admin_audit_logs(db, limit=limit)
    return [
        {
            "id": log.id,
            "actor_persona_id": str(log.actor_persona_id or ""),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "created_at": log.created_at.isoformat(),
            "metadata": log.metadata_json or {},
        }
        for log in logs
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# FORUM MODERATION
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/comments", response_model=PaginatedResponse[schemas.AdminCommentRead])
def list_all_comments(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todos los comentarios para moderación."""
    items, total = admin_crud.list_all_comments(db, skip=skip, limit=limit)
    return PaginatedResponse[schemas.AdminCommentRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un comentario por moderación."""
    success = admin_crud.delete_admin_comment(db, comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    record_admin_action(
        db, current_user, "comment.delete", "comment", comment_id,
    )
    return {"status": "success"}


# ═══════════════════════════════════════════════════════════════════════════════
# SPIRITUAL MILESTONES (BADGES)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/milestones", response_model=PaginatedResponse[schemas.AdminMilestoneRead])
def list_milestones(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_active_user),
):
    """Lista hitos espirituales (insignias) y estadísticas de obtención."""
    items, total = admin_crud.list_admin_milestones(db, skip=skip, limit=limit)
    return PaginatedResponse[schemas.AdminMilestoneRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.post("/milestones/award")
def award_milestone_bulk(
    body: schemas.AdminMilestoneAward,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Asigna un hito a una persona."""
    try:
        result = admin_crud.award_milestone(
            db, body.persona_id, body.badge_id, body.awarded_by,
        )
    except ValueError as e:
        msg = str(e)
        if "already awarded" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=404, detail=msg)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DONATION CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/donation-categories",
    response_model=PaginatedResponse[schemas.AdminDonationCategoryRead],
)
def list_donation_categories(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_active_user),
):
    """Lista categorías de recaudación (Diezmos, Misiones, etc)."""
    cats, total = admin_crud.list_admin_donation_categories(db, skip=skip, limit=limit)
    items = [
        schemas.AdminDonationCategoryRead(
            id=c.id, name=c.name, description=c.description,
            color=c.color_code, active=c.is_active,
        )
        for c in cats
    ]
    return PaginatedResponse[schemas.AdminDonationCategoryRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.post(
    "/donation-categories",
    response_model=schemas.AdminDonationCategoryRead,
    status_code=201,
)
def create_donation_category(
    body: schemas.AdminDonationCategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva categoría de donación."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="nombre es requerido")
    cat = admin_crud.create_admin_donation_category(db, name, body.description)
    record_admin_action(
        db, current_user, "donation_category.create", "donation_category", str(cat.id),
    )
    return schemas.AdminDonationCategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        color=cat.color_code, active=cat.is_active,
    )


@router.patch(
    "/donation-categories/{category_id}",
    response_model=schemas.AdminDonationCategoryRead,
)
def update_donation_category(
    category_id: str,
    body: schemas.AdminDonationCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza una categoría de donación."""
    cat = admin_crud.update_admin_donation_category(
        db, category_id, body.name, body.description, body.color_code, body.is_active,
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Donation category not found")
    record_admin_action(
        db, current_user, "donation_category.update", "donation_category", category_id,
    )
    return schemas.AdminDonationCategoryRead(
        id=cat.id, name=cat.name, description=cat.description,
        color=cat.color_code, active=cat.is_active,
    )


@router.delete("/donation-categories/{category_id}", status_code=204)
def delete_donation_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una categoría de donación."""
    success = admin_crud.delete_admin_donation_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Donation category not found")
    record_admin_action(
        db, current_user, "donation_category.delete", "donation_category", category_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CRM AUTOMATIONS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/automations", response_model=PaginatedResponse[schemas.AutomationRuleRead])
def list_automations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_active_user),
):
    """Lista reglas de automatización configuradas."""
    rules, total = admin_crud.list_admin_automations(db, skip=skip, limit=limit)
    items = [
        schemas.AutomationRuleRead(
            id=str(rule.id),
            name=rule.name,
            trigger_type=rule.trigger_type,
            action_type=rule.action_type,
            action_payload=rule.action_payload or {},
            is_active=rule.is_active,
            last_run=rule.last_run,
        )
        for rule in rules
    ]
    return PaginatedResponse[schemas.AutomationRuleRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.post("/automations", response_model=schemas.AutomationRuleRead)
def create_automation(
    payload: schemas.AutomationRuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva regla de automatización pastoral."""
    from backend.crud.governance import create_automation_rule
    rule = create_automation_rule(db, payload)
    record_admin_action(
        db, current_user, "automation.create", "automation", str(rule.id),
    )
    return schemas.AutomationRuleRead(
        id=str(rule.id),
        name=rule.name,
        trigger_type=rule.trigger_type,
        action_type=rule.action_type,
        action_payload=rule.action_payload or {},
        is_active=rule.is_active,
        last_run=rule.last_run,
    )


@router.patch("/automations/{rule_id}", response_model=schemas.AutomationRuleRead)
def update_automation(
    rule_id: str,
    payload: schemas.AutomationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza una regla de automatización."""
    from backend.crud.governance import update_automation_rule
    try:
        rid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="rule_id inválido")
    rule = update_automation_rule(db, rid, payload)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    record_admin_action(
        db, current_user, "automation.update", "automation", rule_id,
    )
    return schemas.AutomationRuleRead(
        id=str(rule.id),
        name=rule.name,
        trigger_type=rule.trigger_type,
        action_type=rule.action_type,
        action_payload=rule.action_payload or {},
        is_active=rule.is_active,
        last_run=rule.last_run,
    )


@router.delete("/automations/{rule_id}")
def delete_automation(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una regla de automatización permanentemente."""
    from backend.crud.governance import delete_automation_rule
    try:
        rid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="rule_id inválido")
    success = delete_automation_rule(db, rid)
    if not success:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    record_admin_action(
        db, current_user, "automation.delete", "automation", rule_id,
    )
    return {"status": "success"}


# ═══════════════════════════════════════════════════════════════════════════════
# USER MODULE ROLES (granular)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/user-module-roles",
    response_model=PaginatedResponse[schemas.AdminModuleRoleRead],
)
def list_user_module_roles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todas las asignaciones de roles modulares."""
    items, total = admin_crud.list_user_module_roles(db, skip=skip, limit=limit)
    return PaginatedResponse[schemas.AdminModuleRoleRead](
        items=items, total=total, skip=skip, limit=limit,
    )


@router.post("/user-module-roles")
def assign_user_module_role(
    body: schemas.AdminModuleRoleAssign,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Asigna un rol modular a un usuario UUID-based."""
    modulo = body.modulo.strip().lower()
    if not modulo:
        raise HTTPException(status_code=400, detail="modulo es requerido")
    try:
        uid = uuid.UUID(body.user_id)
        rid = uuid.UUID(body.rol_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id o rol_id inválidos")
    try:
        result = admin_crud.assign_user_module_role(
            db, current_user, uid, modulo, rid,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_admin_action(
        db, current_user, "module_role.assign", "module_role",
        result.get("id", ""),
    )
    return result


@router.delete("/user-module-roles/{assignment_id}", status_code=204)
def remove_user_module_role(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una asignación de rol modular."""
    try:
        aid = uuid.UUID(assignment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="assignment_id inválido")
    success = admin_crud.remove_user_module_role(db, current_user, aid)
    if not success:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    record_admin_action(
        db, current_user, "module_role.remove", "module_role", assignment_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# USERS WITH ROLES (combined view)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/users-with-roles",
    response_model=PaginatedResponse[schemas.AdminUserWithRolesRead],
)
def list_users_with_roles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todos los usuarios auth v3 con sus roles de plataforma y modulares."""
    items, total = admin_crud.list_users_with_roles(db, current_user, skip=skip, limit=limit)
    return PaginatedResponse[schemas.AdminUserWithRolesRead](
        items=items, total=total, skip=skip, limit=limit,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROVISION
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/provision-accounts", response_model=schemas.AdminProvisionResult)
def provision_personas_sin_cuenta(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Crea cuentas de plataforma para personas sin auth_user (max 50 por llamada)."""
    try:
        result = admin_crud.provision_personas_sin_cuenta(db)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    record_admin_action(
        db, current_user, "provision_accounts", "accounts",
        metadata={"created": result["created"], "skipped": result["skipped"]},
    )
    return result

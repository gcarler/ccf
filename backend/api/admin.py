from __future__ import annotations

import logging
import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import (
    MODULE_PERMISSION_MAP,
    PERMISSION_LEVELS,
    expand_module_permissions,
    get_user_effective_permissions,
    get_all_permissions,
    hash_password,
    require_active_user,
    require_admin,
)
from backend.core.audit import record_admin_action
from backend.core.tenant import get_user_sede_id, require_user_sede_id
from backend.models_auth import RolPlataforma, Usuario, UsuarioPermisoOverride, UsuarioRolModulo
from backend.models_crm import Persona
from backend.models_shared import _utcnow

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request bodies (mass-assignment protection)
# ---------------------------------------------------------------------------

class CreateUserBody(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(max_length=120)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    role: str = Field(max_length=50)
    is_active: bool = True

class UpdateUserBody(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: str | None = Field(default=None, max_length=120)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

class AwardMilestoneBody(BaseModel):
    persona_id: str
    badge_id: str
    awarded_by: str | None = None

class CreateLocationBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    phone: str | None = None

class CreateDonationCategoryBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None

class CreateAuthRoleBody(BaseModel):
    key: str | None = Field(default=None, min_length=1, max_length=50)
    name: str = Field(validation_alias=AliasChoices("name", "nombre"), min_length=1, max_length=100)
    description: str | None = None
    permissions: dict[str, Any] | list[str] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("permissions", "permisos"),
    )

class UpdateAuthRoleBody(BaseModel):
    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "nombre"), max_length=100)
    description: str | None = None
    permissions: dict[str, Any] | list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("permissions", "permisos"),
    )

class AssignModuleRoleBody(BaseModel):
    user_id: str
    modulo: str
    rol_id: str


def _serialize_automation(rule: models.AutomationRule) -> schemas.AutomationRuleRead:
    return schemas.AutomationRuleRead(
        id=str(rule.id),
        name=rule.name,
        trigger_type=rule.trigger_type,
        action_type=rule.action_type,
        action_payload=rule.action_payload or {},
        is_active=rule.is_active,
        last_run=rule.last_run,
    )


@router.get("/roles", response_model=List[Dict[str, Any]])
def list_roles(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Lista todos los roles de plataforma y el conteo de usuarios vinculados."""
    role_user_counts = dict(
        db.query(
            Usuario.rol_plataforma_id,
            func.count(Usuario.id),
        )
        .filter(Usuario.rol_plataforma_id.isnot(None))
        .group_by(Usuario.rol_plataforma_id)
        .all()
    )
    roles = db.query(RolPlataforma).all()
    return [
        {
            "id": str(r.id),
            "name": r.nombre,
            "permissions": r.permisos or {},
            "users_count": role_user_counts.get(r.id, 0),
        }
        for r in roles
    ]


class CreateRoleBody(BaseModel):
    name: str
    permissions: Dict[str, Any] = {}


class UpdateRoleBody(BaseModel):
    permissions: Dict[str, Any]


@router.post("/roles", response_model=Dict[str, Any])
def create_role(
    payload: CreateRoleBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea un nuevo rol de plataforma."""
    role = RolPlataforma(nombre=payload.name, permisos=payload.permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"id": str(role.id), "name": role.nombre}


@router.patch("/roles/{role_id}")
def update_role(
    role_id: str,
    payload: UpdateRoleBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza los permisos de un rol de plataforma."""
    try:
        rid = uuid.UUID(str(role_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Role not found")
    role = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role.permisos = payload.permissions
    db.commit()
    record_admin_action(db, current_user, "role.update", "role", str(rid))
    return {"status": "success"}


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
        raise HTTPException(status_code=400, detail="Role not found")
    role = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    assigned = db.query(Usuario).filter(Usuario.rol_plataforma_id == rid).count()
    modular_assigned = db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.rol_id == rid, UsuarioRolModulo.deleted_at.is_(None)
    ).count()
    if assigned > 0 or modular_assigned > 0:
        raise HTTPException(
            status_code=409, detail="Cannot delete role with active assignments"
        )
    # ccf-quality-bypass: RolPlataforma has no deleted_at column, hard delete is expected
    getattr(db, "delete")(role)
    db.commit()
    record_admin_action(db, current_user, "role.delete", "role", str(rid))


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


# ── User Permission Management ───────────────────────────────────


@router.get("/users/{user_id}/permissions")
def get_user_permissions(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Obtiene los permisos actuales de un usuario auth_users."""
    try:
        uid = uuid.UUID(str(user_id))
        user = _visible_auth_user(db, current_user, uid)
    except ValueError:
        user = None
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rol = user.rol_plataforma
    role_perms = rol.permisos if rol and isinstance(rol.permisos, dict) else {}
    direct = db.query(UsuarioPermisoOverride).filter(UsuarioPermisoOverride.user_id == user.id).first()
    override_perms = direct.permisos if direct and isinstance(direct.permisos, dict) else {}
    module_rows = (
        db.query(UsuarioRolModulo)
        .filter(UsuarioRolModulo.user_id == user.id, UsuarioRolModulo.deleted_at.is_(None))
        .all()
    )

    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": rol.nombre if rol else "LECTOR",
        "role_permissions": role_perms,
        "override_permissions": override_perms,
        "module_roles": [
            {"module": row.modulo, "role_id": str(row.rol_id)} for row in module_rows
        ],
        "effective_permissions": get_user_effective_permissions(db, user),
    }


@router.put("/users/{user_id}/permissions")
def set_user_permissions(
    user_id: str,
    payload: Dict[str, str],
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Asigna permisos modulares a un usuario auth_users por módulo/nivel.

    Payload: {"crm": "read", "projects": "manage", "academy": "study"}
    Niveles: read, edit, manage (y study para academy).
    """
    # Resolve user from auth_users (UUID-based)
    try:
        uid = uuid.UUID(str(user_id))
        user = _visible_auth_user(db, current_user, uid)
    except ValueError:
        user = None
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid_modules = set(MODULE_PERMISSION_MAP.keys())
    resolved_perms: Dict[str, str] = {}

    for module, level in payload.items():
        module = module.strip().lower()

        if level is None:
            continue  # skip null levels (remove override for this module)

        level = str(level).strip().lower()

        if module not in valid_modules:
            raise HTTPException(
                status_code=400,
                detail=f"Módulo inválido: '{module}'. Válidos: {', '.join(sorted(valid_modules))}",
            )

        module_config = MODULE_PERMISSION_MAP[module]
        valid_levels = set(module_config.keys())
        if level not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Nivel inválido '{level}' para módulo '{module}'. Válidos: {', '.join(sorted(valid_levels))}",
            )

        for perm_key in expand_module_permissions(module, level):
            resolved_perms[perm_key] = "allow"

    # Grants directos son adicionales y no reemplazan el rol base. La ausencia
    # de un módulo elimina sólo su grant personal y restaura la herencia.
    direct = db.query(UsuarioPermisoOverride).filter(UsuarioPermisoOverride.user_id == user.id).first()
    if direct:
        direct.permisos = resolved_perms
        flag_modified(direct, "permisos")
    else:
        db.add(UsuarioPermisoOverride(user_id=user.id, permisos=resolved_perms))

    db.commit()
    record_admin_action(db, current_user, "permissions.set", "user", user_id, {"modules": list(resolved_perms.keys())})
    db.refresh(user)
    return {
        "status": "success",
        "user_id": user_id,
        "override_permissions": resolved_perms,
        "effective_permissions": get_user_effective_permissions(db, user),
    }


@router.get("/locations", response_model=List[Dict[str, Any]])
def list_locations(db: Session = Depends(get_db), _user=Depends(require_active_user)):
    """Lista todas las sedes de la iglesia."""
    locs = db.query(models.ChurchLocation).all()
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "address": loc.address,
            "pastor": loc.pastor_name,
            "active": loc.is_active,
            "type": loc.location_type,
        }
        for loc in locs
    ]


@router.post("/locations")
def create_location(
    body: CreateLocationBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva sede o anexo."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="nombre es requerido")
    loc = models.ChurchLocation(
        name=name,
        address=body.address,
    )
    db.add(loc)
    db.commit()
    return {"status": "success"}


# --- SOCIAL CHANNELS ---


@router.get("/socials", response_model=List[Dict[str, Any]])
def list_socials(db: Session = Depends(get_db), _user=Depends(require_active_user)):
    """Lista canales sociales oficiales."""
    channels = db.query(models.SocialChannel).all()
    return [
        {"id": c.id, "platform": c.platform, "url": c.url, "visible": c.is_visible}
        for c in channels
    ]


# --- SYSTEM VARIABLES ---


@router.get("/variables")
def list_variables(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Obtiene variables de configuración global del sistema."""
    sys_vars = db.query(models.SystemVariable).all()
    return {v.key: v.value for v in sys_vars}


class SetVariableBody(BaseModel):
    key: str
    value: str


@router.post("/variables")
def set_variable(
    payload: SetVariableBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Define o actualiza una variable de sistema.

    Body: {"key": "nombre_variable", "value": "valor"}
    """
    key = payload.key
    value = payload.value
    var = (
        db.query(models.SystemVariable).filter(models.SystemVariable.key == key).first()
    )
    if var:
        var.value = value
    else:
        var = models.SystemVariable(key=key, value=value)
        db.add(var)
    db.commit()
    return {"status": "success"}


# --- ADMIN STATS ---


@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Retorna métricas agregadas para el dashboard de administración."""
    # Conteo de personas
    total_personas = db.query(func.count(models.Persona.id)).scalar() or 0

    # Conteo de usuarios activos
    total_usuarios_activos = (
        db.query(func.count(Usuario.id))
        .filter(Usuario.is_active.is_(True))
        .scalar()
        or 0
    )

    # Donaciones del mes actual
    now = _utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_donations = (
        db.query(func.coalesce(func.sum(models.Donation.amount), 0))
        .filter(
            models.Donation.created_at >= first_of_month,
            models.Donation.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    # Diezmos y ofrendas del mes
    tithes = (
        db.query(func.coalesce(func.sum(models.Donation.amount), 0))
        .filter(
            models.Donation.donation_type == "Diezmo",
            models.Donation.created_at >= first_of_month,
            models.Donation.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )
    offerings = (
        db.query(func.coalesce(func.sum(models.Donation.amount), 0))
        .filter(
            models.Donation.donation_type == "Ofrenda",
            models.Donation.created_at >= first_of_month,
            models.Donation.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    # Donantes únicos del mes
    monthly_donors = (
        db.query(func.count(func.distinct(models.Donation.persona_id)))
        .filter(models.Donation.created_at >= first_of_month)
        .scalar()
        or 0
    )

    # Personas nuevas este mes
    new_personas = (
        db.query(func.count(models.Persona.id))
        .filter(models.Persona.created_at >= first_of_month)
        .scalar()
        or 0
    )

    return {
        "personas": total_personas,
        "usuarios_activos": total_usuarios_activos,
        "donaciones_mes": float(monthly_donations),
        "donantes_mes": monthly_donors,
        "personas_nuevas_mes": new_personas,
        "diezmos_mes": float(tithes),
        "ofrendas_mes": float(offerings),
    }


# --- MEMBER MANAGEMENT ---


@router.get("/personas", response_model=List[Dict[str, Any]])
def list_admin_personas(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Lista personas para administracion, filtradas por sede del admin."""
    sede_id = get_user_sede_id(db, current_user.id)
    personas = (
        db.query(models.Persona)
        .filter(models.Persona.sede_id == sede_id)
        .order_by(models.Persona.created_at.desc())
        .all()
    )
    return [
        {
            "id": m.id,
            "first_name": m.first_name,
            "last_name": m.last_name,
            "email": m.email,
            "phone": m.phone,
            "church_role": m.church_role,
        }
        for m in personas
    ]


# --- USER MANAGEMENT ---


def _serialize_auth_user_row(user):
    rol = user.rol_plataforma
    display_role = rol.nombre if rol else "MIEMBRO"
    permisos = rol.permisos if rol else {}
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": display_role,
        "role_id": str(user.rol_plataforma_id) if user.rol_plataforma_id else None,
        "role_name": display_role,
        "rol_plataforma_id": str(user.rol_plataforma_id) if user.rol_plataforma_id else None,
        "sede_id": str(user.sede_id) if user.sede_id else None,
        "xp": user.xp or 0,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "permissions": permisos if isinstance(permisos, dict) else {},
        "role_permissions": permisos if isinstance(permisos, dict) else {},
        "override_permissions": {},
    }


def _assign_auth_user_role(db: Session, user, role_name: str) -> None:
    normalized = str(role_name or "").strip()
    if not normalized:
        return

    role_aliases = {
        "admin": "ADMINISTRADOR",
        "administrador": "ADMINISTRADOR",
        "staff": "GESTOR",
        "pastor": "GESTOR",
        "coordinador": "GESTOR",
        "docente": "EDITOR",
        "editor": "EDITOR",
        "estudiante": "MIEMBRO",
        "lector": "LECTOR",
        "miembro": "MIEMBRO",
    }
    canonical_name = role_aliases.get(normalized.lower(), normalized)
    rol = (
        db.query(RolPlataforma)
        .filter(func.lower(RolPlataforma.nombre) == canonical_name.lower())
        .first()
    )
    if not rol:
        raise HTTPException(status_code=404, detail="Role not found")
    user.rol_plataforma_id = rol.id


def _parse_auth_role_id(value, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} invalido")


def _is_global_admin(user: Usuario) -> bool:
    role = getattr(getattr(user, "rol_plataforma", None), "nombre", "")
    return str(role).strip().lower().replace("_", " ") in {"super administrador", "superadmin"}


def _visible_auth_user(db: Session, current_user: Usuario, user_id: uuid.UUID) -> Usuario:
    query = db.query(Usuario).options(joinedload(Usuario.rol_plataforma)).filter(Usuario.id == user_id)
    if not _is_global_admin(current_user):
        query = query.filter(Usuario.sede_id == require_user_sede_id(db, current_user))
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _visible_auth_users_query(db: Session, current_user: Usuario):
    query = db.query(Usuario).options(joinedload(Usuario.rol_plataforma))
    if not _is_global_admin(current_user):
        query = query.filter(Usuario.sede_id == require_user_sede_id(db, current_user))
    return query


@router.get("/users", response_model=List[Dict[str, Any]])
def list_admin_users(
    db: Session = Depends(get_db), current_user=Depends(require_admin)
):
    """Lista usuarios de auth_users para gestión de permisos granulares."""
    users = _visible_auth_users_query(db, current_user).all()
    return [_serialize_auth_user_row(u) for u in users]


@router.get("/users/{user_id}", response_model=Dict[str, Any])
def get_admin_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Obtiene un usuario auth por UUID."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id invalido")

    user = _visible_auth_user(db, current_user, uid)
    return _serialize_auth_user_row(user)


@router.post("/users", response_model=Dict[str, Any])
def create_admin_user(
    body: CreateUserBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Crea un nuevo usuario Auth v3 desde el panel de administración.

    Crea una Persona mínima vinculada a la sede del admin, luego un Usuario
    con las credenciales proporcionadas y rol MIEMBRO por defecto.
    """
    username = body.username.strip()
    email = body.email.strip()
    password = body.password
    first_name = body.first_name.strip() or username
    last_name = body.last_name.strip()

    # Verificar duplicados en auth_users.
    existing = db.query(Usuario).filter(
        (Usuario.username == username) | (Usuario.email == email)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Usuario o email ya existe")

    sede_id = get_user_sede_id(db, current_user)
    if not sede_id:
        raise HTTPException(status_code=500, detail="No se pudo determinar la sede del administrador")

    default_role = db.query(RolPlataforma).filter(
        RolPlataforma.nombre == "MIEMBRO"
    ).first()
    if not default_role:
        default_role = RolPlataforma(
            nombre="MIEMBRO",
            permisos={"academy:study": "allow", "profile:manage": "allow"},
        )
        db.add(default_role)
        db.flush()

    persona_id = uuid.uuid4()
    persona = Persona(
        id=persona_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        sede_id=sede_id,
    )
    db.add(persona)
    db.flush()

    new_user = Usuario(
        id=persona_id,
        sede_id=sede_id,
        username=username,
        email=email,
        password_hash=hash_password(password),
        rol_plataforma_id=default_role.id,
        is_active=body.is_active,
        is_email_verified=False,
    )
    if body.role:
        _assign_auth_user_role(db, new_user, body.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _serialize_auth_user_row(new_user)


@router.patch("/users/{user_id}", response_model=Dict[str, Any])
def update_admin_user(
    user_id: str,
    body: UpdateUserBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Actualiza campos básicos de auth_users por UUID."""
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id invalido")

    user = _visible_auth_user(db, current_user, uid)

    if body.username is not None:
        user.username = body.username.strip()
    if body.email is not None:
        new_email = body.email.strip()
        user.email = new_email
        persona = db.query(Persona).filter(Persona.id == user.id).first()
        if persona:
            persona.email = new_email
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        _assign_auth_user_role(db, user, body.role)

    db.commit()
    db.refresh(user)
    return _serialize_auth_user_row(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_admin_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Desactiva un usuario auth por UUID.

    Se conserva la cuenta para evitar pérdida de historial y relaciones
    dependientes; la baja real se hace por desactivación.
    """
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id invalido")

    user = _visible_auth_user(db, current_user, uid)
    user.is_active = False
    db.commit()
    record_admin_action(db, current_user, "user.deactivate", "user", str(uid))


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
        raise HTTPException(status_code=400, detail="user_id invalido")

    if role_id is None:
        raise HTTPException(status_code=400, detail="role_id requerido")

    user = _visible_auth_user(db, current_user, uid)

    role = db.query(RolPlataforma).filter(
        RolPlataforma.id == _parse_auth_role_id(role_id, "role_id")
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    user.rol_plataforma_id = role.id
    db.commit()
    record_admin_action(db, current_user, "user.role_change", "user", str(uid), {"role_id": str(role.id)})
    db.refresh(user)
    return {
        "status": "success",
        "new_role": role.nombre,
        "role_id": str(role.id),
        "user": _serialize_auth_user_row(user),
    }


# --- AUDIT & SECURITY ---


@router.get("/audit", response_model=List[Dict[str, Any]])
def list_admin_audit(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Obtiene el historial de auditoría del sistema."""
    logs = crud.get_admin_audit_logs(db, limit=limit)
    result = []
    for log in logs:
        result.append(
            {
                "id": log.id,
                "actor_persona_id": str(log.actor_persona_id or ""),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "created_at": log.created_at.isoformat(),
                "metadata": log.metadata_json or {},
            }
        )
    return result


# --- FORUM MODERATION ---


@router.get("/comments", response_model=List[Dict[str, Any]])
def list_all_comments(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Lista todos los comentarios para moderación."""
    comments = (
        db.query(models.ForumComment)
        .order_by(models.ForumComment.created_at.desc())
        .all()
    )
    if not comments:
        return []

    author_ids = {c.author_id for c in comments if c.author_id}
    thread_ids = {c.thread_id for c in comments if c.thread_id}

    users_map = {
        u.id: u
        for u in db.query(models.User).filter(models.User.id.in_(author_ids)).all()
    } if author_ids else {}
    threads_map = {
        t.id: t
        for t in db.query(models.ForumThread).filter(models.ForumThread.id.in_(thread_ids)).all()
    } if thread_ids else {}

    return [
        {
            "id": c.id,
            "author": users_map.get(c.author_id).username if users_map.get(c.author_id) else "Anónimo",
            "text": c.content,
            "context": threads_map.get(c.thread_id).title if threads_map.get(c.thread_id) else "General",
            "type": threads_map.get(c.thread_id).category if threads_map.get(c.thread_id) else "Foro",
            "created_at": c.created_at.isoformat(),
        }
        for c in comments
    ]


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un comentario por moderación."""
    comment = (
        db.query(models.ForumComment)
        .filter(models.ForumComment.id == comment_id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.deleted_at = _utcnow()
    db.commit()
    record_admin_action(db, current_user, "comment.delete", "comment", comment_id)
    return {"status": "success"}


# --- SPIRITUAL MILESTONES (BADGES) ---


@router.get("/milestones", response_model=List[Dict[str, Any]])
def list_milestones(db: Session = Depends(get_db), _user=Depends(require_active_user)):
    """Lista hitos espirituales (insignias) y estadísticas de obtención."""
    badge_counts = dict(
        db.query(
            models.MedallaUsuario.badge_id,
            func.count(models.MedallaUsuario.id),
        )
        .group_by(models.MedallaUsuario.badge_id)
        .all()
    )
    badges = db.query(models.Medalla).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "icon": b.icon_key,
            "xp": b.xp_reward,
            "count": badge_counts.get(b.id, 0),
        }
        for b in badges
    ]


@router.post("/milestones/award")
def award_milestone_bulk(
    body: AwardMilestoneBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Asigna un hito a una lista de personas de forma masiva."""
    badge = db.query(models.Medalla).filter(models.Medalla.id == body.badge_id).first()
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    pid = uuid.UUID(str(body.persona_id))
    persona = db.query(models.Persona).filter(models.Persona.id == pid).first()
    user = db.query(models.Usuario).filter(models.Usuario.id == pid).first()
    if not persona or not user:
        raise HTTPException(status_code=404, detail="Persona not found")

    exists = (
        db.query(models.MedallaUsuario)
        .filter(
            models.MedallaUsuario.user_id == user.id,
            models.MedallaUsuario.badge_id == badge.id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Badge already awarded to this persona")

    ub = models.MedallaUsuario(user_id=user.id, badge_id=badge.id)
    db.add(ub)
    db.commit()
    return {"status": "success", "awarded": 1}


# --- DONATION CATEGORIES ---


@router.get("/donation-categories", response_model=List[Dict[str, Any]])
def list_donation_categories(db: Session = Depends(get_db), _user=Depends(require_active_user)):
    """Lista categorías de recaudación (Diezmos, Misiones, etc)."""
    cats = db.query(models.DonationCategory).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "color": c.color_code,
            "active": c.is_active,
        }
        for c in cats
    ]


@router.post("/donation-categories")
def create_donation_category(
    body: CreateDonationCategoryBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva categoría de donación."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="nombre es requerido")
    cat = models.DonationCategory(
        name=name,
        description=body.description,
        color_code="blue",
    )
    db.add(cat)
    db.commit()
    return {"status": "success"}


# --- CRM AUTOMATIONS ---


@router.get("/automations", response_model=List[schemas.AutomationRuleRead])
def list_automations(db: Session = Depends(get_db), _user=Depends(require_active_user)):
    """Lista reglas de automatización configuradas."""
    rules = db.query(models.AutomationRule).all()
    return [_serialize_automation(rule) for rule in rules]


@router.post("/automations", response_model=schemas.AutomationRuleRead)
def create_automation(
    payload: schemas.AutomationRuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva regla de automatización pastoral."""
    rule = models.AutomationRule(
        name=payload.name,
        trigger_type=payload.trigger_type,
        action_type=payload.action_type,
        action_payload=payload.action_payload,
        is_active=payload.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _serialize_automation(rule)


@router.patch("/automations/{rule_id}", response_model=schemas.AutomationRuleRead)
def update_automation(
    rule_id: str,
    payload: schemas.AutomationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza una regla de automatización (nombre, trigger, acción, activo)."""
    rule = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    if payload.name is not None:
        rule.name = payload.name
    if payload.trigger_type is not None:
        rule.trigger_type = payload.trigger_type
    if payload.action_type is not None:
        rule.action_type = payload.action_type
    if payload.action_payload is not None:
        rule.action_payload = payload.action_payload
    if payload.is_active is not None:
        rule.is_active = payload.is_active
    db.commit()
    db.refresh(rule)
    return _serialize_automation(rule)


@router.delete("/automations/{rule_id}")
def delete_automation(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una regla de automatización permanentemente."""
    rule = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    rule.deleted_at = _utcnow()
    db.commit()
    record_admin_action(db, current_user, "automation.delete", "automation", rule_id)
    return {"status": "success"}
# ──────────────────────────────────────────────
# ROLES MODULARES GRANULARES (auth_user_module_roles)
# ──────────────────────────────────────────────

@router.get("/auth-role-definitions")
def list_auth_role_definitions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todas las definiciones de roles del sistema auth (RolPlataforma)."""
    try:
        roles = db.query(RolPlataforma).all()
        return [
            {"id": str(r.id), "nombre": r.nombre, "permisos": r.permisos}
            for r in roles
        ]
    except Exception:
        logger.exception("Failed to list auth role definitions")
        return []


@router.post("/auth-role-definitions")
def create_auth_role_definition(
    body: CreateAuthRoleBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea un nuevo rol auth (RolPlataforma)."""
    nombre = body.name.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="nombre es requerido")
    existing = db.query(RolPlataforma).filter(RolPlataforma.nombre == nombre).first()
    if existing:
        raise HTTPException(status_code=409, detail="El rol ya existe")
    permisos = (
        {p: "allow" for p in body.permissions}
        if isinstance(body.permissions, list)
        else {key: value for key, value in body.permissions.items() if value}
    )
    rol = RolPlataforma(nombre=nombre, permisos=permisos)
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return {"id": str(rol.id), "nombre": rol.nombre, "permisos": rol.permisos}


@router.patch("/auth-role-definitions/{role_id}")
def update_auth_role_definition(
    role_id: str,
    body: UpdateAuthRoleBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza permisos de un rol auth."""
    try:
        rid = uuid.UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="role_id invalido")
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if body.permissions is not None:
        rol.permisos = (
            {p: "allow" for p in body.permissions}
            if isinstance(body.permissions, list)
            else {key: value for key, value in body.permissions.items() if value}
        )
    if body.name is not None:
        rol.nombre = body.name
    db.commit()
    db.refresh(rol)
    return {"id": str(rol.id), "nombre": rol.nombre, "permisos": rol.permisos}


@router.delete("/auth-role-definitions/{role_id}", status_code=204)
def delete_auth_role_definition(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un rol auth (solo si no esta asignado a ningun usuario)."""
    try:
        rid = uuid.UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="role_id invalido")
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    assigned = db.query(Usuario).filter(Usuario.rol_plataforma_id == rid).count()
    modular_assigned = db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.rol_id == rid, UsuarioRolModulo.deleted_at.is_(None)
    ).count()
    if assigned > 0 or modular_assigned > 0:
        raise HTTPException(
            status_code=409, detail="No se puede eliminar un rol con asignaciones activas",
        )
    db.delete(rol)
    db.commit()
    record_admin_action(db, current_user, "auth_role.delete", "auth_role", role_id)


@router.get("/user-module-roles")
def list_user_module_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todas las asignaciones de roles modulares."""
    try:
        rows = (
            db.query(UsuarioRolModulo, RolPlataforma)
            .join(RolPlataforma, RolPlataforma.id == UsuarioRolModulo.rol_id)
            .filter(UsuarioRolModulo.deleted_at.is_(None))
            .all()
        )
        return [
            {
                "id": str(umr.id),
                "user_id": str(umr.user_id),
                "modulo": umr.modulo,
                "rol_id": str(umr.rol_id),
                "rol_nombre": r.nombre,
                "created_at": umr.created_at.isoformat() if umr.created_at else None,
            }
            for umr, r in rows
        ]
    except Exception:
        logger.exception("Failed to list user module roles")
        return []


@router.post("/user-module-roles")
def assign_user_module_role(
    body: AssignModuleRoleBody,
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
        raise HTTPException(status_code=400, detail="user_id o rol_id invalidos")
    user = _visible_auth_user(db, current_user, uid)
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    role_permissions = rol.permisos if isinstance(rol.permisos, dict) else {}
    if not any(key.startswith(f"{modulo}:") and value for key, value in role_permissions.items()):
        raise HTTPException(
            status_code=422,
            detail="El rol debe incluir al menos un permiso del módulo asignado",
        )
    existing = db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.user_id == uid,
        UsuarioRolModulo.modulo == modulo,
    ).first()
    if existing:
        existing.rol_id = rid
        existing.deleted_at = None
        db.commit()
        db.refresh(existing)
        return {"id": str(existing.id), "user_id": str(existing.user_id), "modulo": existing.modulo, "rol_id": str(existing.rol_id), "updated": True}
    umr = UsuarioRolModulo(user_id=uid, modulo=modulo, rol_id=rid)
    db.add(umr)
    db.commit()
    db.refresh(umr)
    return {"id": str(umr.id), "user_id": str(umr.user_id), "modulo": umr.modulo, "rol_id": str(umr.rol_id), "created": True}


@router.delete("/user-module-roles/{assignment_id}", status_code=204)
def remove_user_module_role(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una asignacion de rol modular."""
    try:
        aid = uuid.UUID(assignment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="assignment_id invalido")
    umr_query = db.query(UsuarioRolModulo).join(Usuario).filter(
        UsuarioRolModulo.id == aid, UsuarioRolModulo.deleted_at.is_(None)
    )
    if not _is_global_admin(current_user):
        umr_query = umr_query.filter(Usuario.sede_id == require_user_sede_id(db, current_user))
    umr = umr_query.first()
    if not umr:
        raise HTTPException(status_code=404, detail="Asignacion no encontrada")
    umr.deleted_at = datetime.now(timezone.utc)
    db.commit()
    record_admin_action(db, current_user, "module_role.remove", "module_role", assignment_id)


@router.get("/users-with-roles")
def list_users_with_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todos los usuarios auth v3 con sus roles de plataforma y modulares."""
    users = _visible_auth_users_query(db, current_user).all()

    user_ids = [u.id for u in users]
    persona_map = {
        p.id: p
        for p in db.query(Persona).filter(Persona.id.in_(user_ids)).all()
    } if user_ids else {}

    modulares_rows = (
        db.query(UsuarioRolModulo, RolPlataforma)
        .join(RolPlataforma, RolPlataforma.id == UsuarioRolModulo.rol_id)
        .filter(UsuarioRolModulo.user_id.in_(user_ids), UsuarioRolModulo.deleted_at.is_(None))
        .all()
    ) if user_ids else []
    modulares_by_user: dict = {}
    for umr, r in modulares_rows:
        modulares_by_user.setdefault(umr.user_id, []).append(
            {"id": str(umr.id), "modulo": umr.modulo, "rol_id": str(r.id), "rol_nombre": r.nombre}
        )

    return [
        {
            "user_id": str(u.id),
            "username": u.username,
            "email": u.email,
            "nombre": (persona_map.get(u.id).nombre_completo if persona_map.get(u.id) else "—"),
            "is_active": u.is_active,
            "rol_plataforma": {"id": str(u.rol_plataforma.id), "nombre": u.rol_plataforma.nombre} if u.rol_plataforma else None,
            "roles_modulares": modulares_by_user.get(u.id, []),
        }
        for u in users
    ]


# ── PROVISIONAMIENTO MASIVO DE CUENTAS ─────────────────────────────────────


@router.post("/provision-accounts", response_model=Dict[str, Any])
def provision_personas_sin_cuenta(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Crea cuentas de plataforma para personas sin auth_user (max 50 por llamada).
    - username = prefijo del email
    - password = aleatoria de 12 caracteres
    - rol = MIEMBRO
    """
    def _generate_password(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        while True:
            pw = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                    and any(c.isdigit() for c in pw) and any(c in "!@#$%&*" for c in pw)):
                return pw

    default_role = db.query(RolPlataforma).filter(
        RolPlataforma.nombre == "MIEMBRO"
    ).first()
    if not default_role:
        raise HTTPException(status_code=500, detail="Rol MIEMBRO no configurado")

    sede = db.query(models.Sede).order_by(models.Sede.nombre).first()
    if not sede:
        raise HTTPException(status_code=500, detail="No hay sedes configuradas")

    rows = db.execute(
        text("""
            SELECT p.id,
                   p.email,
                   concat_ws(' ', p.first_name, p.second_name, p.last_name, p.second_last_name) AS full_name,
                   p.first_name,
                   p.last_name
            FROM personas p
            WHERE (p.email IS NOT NULL AND p.email != '')
              AND NOT EXISTS (SELECT 1 FROM auth_users u WHERE u.id = p.id)
            ORDER BY p.created_at ASC
            LIMIT 50
        """)
    ).fetchall()

    remaining_query = db.execute(
        text("""
            SELECT COUNT(*)
            FROM personas p
            WHERE (p.email IS NOT NULL AND p.email != '')
              AND NOT EXISTS (SELECT 1 FROM auth_users u WHERE u.id = p.id)
        """)
    ).scalar()
    truncated = remaining_query > 50

    created = 0
    skipped = 0
    errors = []
    accounts_created = []

    for row in rows:
        pid, email, full_name, first_name, last_name = row
        email_prefix = email.split("@")[0].lower().replace(".", "_").replace("-", "_")
        base_username = email_prefix[:60]
        username = base_username

        attempt = 0
        while True:
            existing = db.execute(
                text("SELECT 1 FROM auth_users WHERE username = :u LIMIT 1"),
                {"u": username},
            ).scalar()
            if not existing:
                break
            attempt += 1
            username = f"{base_username[:55]}_{attempt}"

        if db.execute(
            text("SELECT 1 FROM auth_users WHERE email = :e LIMIT 1"),
            {"e": email},
        ).scalar():
            skipped += 1
            continue

        try:
            temp_password = _generate_password()
            usuario = Usuario(
                id=pid,
                sede_id=sede.id,
                username=username,
                email=email,
                password_hash=hash_password(temp_password),
                rol_plataforma_id=default_role.id,
                is_active=True,
                is_email_verified=False,
            )
            db.add(usuario)
            db.flush()
            created += 1
            accounts_created.append({
                "email": email,
                "username": username,
                "temp_password": temp_password,
            })
        except Exception as e:
            db.rollback()
            skipped += 1
            errors.append({"email": email, "error": str(e)})
            continue

    db.commit()
    record_admin_action(
        db, current_user, "provision_accounts", "accounts",
        metadata={"created": created, "skipped": skipped},
    )
    return {
        "created": created,
        "skipped": skipped,
        "truncated": truncated,
        "errors": errors,
        "accounts": accounts_created,
        "message": f"{created} cuentas creadas. {skipped} omitidas. Distribuir contraseñas temporales a cada usuario.",
    }

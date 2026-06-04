from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models_shared import _utcnow
from backend import crud, models, schemas
from backend.auth import require_active_user, require_admin
from backend.crud.crm import get_user_sede_id
from backend.core.database import get_db
from backend.core.permissions import (MODULE_PERMISSION_MAP, PERMISSION_LEVELS,
                                      expand_module_permissions,
                                      get_all_permissions)

router = APIRouter()


def _serialize_automation(rule: models.AutomationRule) -> schemas.AutomationRuleRead:
    return schemas.AutomationRuleRead(
        id=rule.id,
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
    """Lista todos los roles y el conteo de usuarios vinculados."""
    roles = db.query(models.Role).all()
    result = []
    for r in roles:
        count = db.query(models.User).filter(models.User.role_id == r.role_id).count()
        result.append(
            {
                "id": r.role_id,
                "name": r.name,
                "permissions": r.permissions or {},
                "users_count": count,
            }
        )
    return result


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
    """Crea un nuevo rol ministerial."""
    role = models.Role(name=payload.name, permissions=payload.permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"id": role.role_id, "name": role.name}


@router.patch("/roles/{role_id}")
def update_role(
    role_id: int,
    payload: UpdateRoleBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza los permisos de un rol."""
    role = db.query(models.Role).filter(models.Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role.permissions = payload.permissions
    db.commit()
    return {"status": "success"}


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un rol ministerial (no usado por usuarios activos)."""
    role = db.query(models.Role).filter(models.Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    assigned = db.query(models.User).filter(models.User.role_id == role_id).count()
    if assigned > 0:
        raise HTTPException(
            status_code=409, detail=f"Cannot delete role with {assigned} assigned users"
        )
    role.deleted_at = _utcnow()
    db.commit()


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
    import uuid as _uuid
    from backend.models_auth import Usuario
    from sqlalchemy.orm import joinedload
    try:
        uid = _uuid.UUID(str(user_id))
        user = db.query(Usuario).options(joinedload(Usuario.rol_plataforma)).filter(Usuario.id == uid).first()
    except ValueError:
        user = None
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rol = user.rol_plataforma
    permisos = rol.permisos if rol else {}
    if not isinstance(permisos, dict):
        permisos = {}

    # Separar permisos base de plataforma vs granulares personales
    personal_nombre = f"PERSONALIZADO_{str(user.id).replace('-', '').upper()}"
    is_personal_rol = rol and rol.nombre == personal_nombre
    # override_permissions = granulares personales; role_permissions = del rol compartido
    override_perms = permisos if is_personal_rol else {}
    role_perms = {} if is_personal_rol else permisos

    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": rol.nombre if rol else "LECTOR",
        "role_permissions": role_perms,
        "override_permissions": override_perms,
        "effective_permissions": permisos,
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
    import uuid as _uuid
    from backend.models_auth import Usuario, RolPlataforma
    from sqlalchemy.orm import joinedload

    # Resolve user from auth_users (UUID-based)
    try:
        uid = _uuid.UUID(str(user_id))
        user = db.query(Usuario).options(joinedload(Usuario.rol_plataforma)).filter(Usuario.id == uid).first()
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

    # profile:manage siempre se preserva
    resolved_perms["profile:manage"] = "allow"

    # Preservar system:config si el usuario actual lo tenía (evita lockout de admins)
    current_rol = user.rol_plataforma
    if current_rol:
        current_perms = current_rol.permisos or {}
        if isinstance(current_perms, dict) and current_perms.get("system:config"):
            resolved_perms["system:config"] = "allow"

    # Persist en RolPlataforma personal del usuario (nunca tocar roles compartidos)
    from backend.models_auth import RolPlataforma
    from sqlalchemy.orm.attributes import flag_modified

    personal_nombre = f"PERSONALIZADO_{str(user.id).replace('-', '').upper()}"
    is_personal = current_rol and current_rol.nombre == personal_nombre

    if is_personal:
        # Reemplazar completamente — permite quitar permisos
        current_rol.permisos = resolved_perms
        flag_modified(current_rol, "permisos")
    else:
        # Buscar si ya existe un rol personal creado antes para este usuario
        existing_personal = db.query(RolPlataforma).filter(
            RolPlataforma.nombre == personal_nombre
        ).first()
        if existing_personal:
            existing_personal.permisos = resolved_perms
            flag_modified(existing_personal, "permisos")
            user.rol_plataforma_id = existing_personal.id
        else:
            # Crear rol personal nuevo sin modificar el rol compartido
            new_rol = RolPlataforma(nombre=personal_nombre, permisos=resolved_perms)
            db.add(new_rol)
            db.flush()
            user.rol_plataforma_id = new_rol.id

    db.commit()
    return {"status": "success", "user_id": user_id, "permissions": resolved_perms}


# --- CHURCH LOCATIONS ---


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
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva sede o anexo."""
    loc = models.ChurchLocation(
        name=payload["name"],
        address=payload.get("address"),
        pastor_name=payload.get("pastor"),
        location_type=payload.get("type", "Sede"),
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
    vars = db.query(models.SystemVariable).all()
    return {v.key: v.value for v in vars}


@router.post("/variables")
def set_variable(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Define o actualiza una variable de sistema."""
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


# --- MEMBER MANAGEMENT ---


@router.get("/personas", response_model=List[Dict[str, Any]])
def list_admin_members(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Lista miembros para administracion."""
    personas = db.query(models.Persona).filter(models.Persona.sede_id == get_user_sede_id(db, current_user.id)).all()
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


@router.get("/users", response_model=List[Dict[str, Any]])
def list_admin_users(
    db: Session = Depends(get_db), current_user=Depends(require_admin)
):
    """Lista usuarios de auth_users para gestión de permisos granulares."""
    from backend.models_auth import Usuario, RolPlataforma
    from sqlalchemy.orm import joinedload
    users = db.query(Usuario).options(joinedload(Usuario.rol_plataforma)).all()
    result = []
    for u in users:
        rol = u.rol_plataforma
        permisos = rol.permisos if rol else {}
        result.append(
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "role": rol.nombre if rol else "LECTOR",
                "role_id": str(u.rol_plataforma_id) if u.rol_plataforma_id else None,
                "is_active": u.is_active,
                "permissions": permisos if isinstance(permisos, dict) else {},
                "role_permissions": permisos if isinstance(permisos, dict) else {},
                "override_permissions": {},
            }
        )
    return result


@router.post("/users", response_model=Dict[str, Any])
def create_admin_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Crea un nuevo usuario en auth_users (v2) desde el panel de administración.

    Crea una Persona mínima vinculada a la sede principal, luego un Usuario
    con las credenciales proporcionadas y rol LECTOR por defecto.
    """
    import uuid as _uuid
    from backend.core.permissions import hash_password
    from backend.models_auth import Usuario
    from backend.models_kernel import PlatformRoleDefinition, PlatformRole
    from backend.models_crm import Persona

    username = str(payload.get("username", "")).strip()
    email = str(payload.get("email", "")).strip()
    password = str(payload.get("password", ""))
    first_name = str(payload.get("first_name", payload.get("nombre", username))).strip()
    last_name = str(payload.get("last_name", payload.get("apellido", ""))).strip()

    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="username, email y password son requeridos")

    # Verificar duplicados en auth_users (v2)
    existing = db.query(Usuario).filter(
        (Usuario.username == username) | (Usuario.email == email)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Usuario o email ya existe")

    # Obtener sede_id (usar la primera sede disponible)
    sede = db.query(models.Sede).first()
    if not sede:
        raise HTTPException(status_code=500, detail="No hay sedes configuradas en el sistema")

    # Resolver rol LECTOR de PlatformRoleDefinition
    lector_role = db.query(PlatformRoleDefinition).filter(
        PlatformRoleDefinition.role == PlatformRole.LECTOR
    ).first()

    # Crear Persona mínima (requerido como FK de Usuario)
    persona_id = _uuid.uuid4()
    persona = Persona(
        id=persona_id,
        first_name=first_name or username,
        last_name=last_name,
        email=email,
        sede_id=sede.id,
    )
    db.add(persona)
    db.flush()

    # Crear Usuario en auth_users (v2)
    new_user = Usuario(
        id=persona_id,
        sede_id=sede.id,
        username=username,
        email=email,
        password_hash=hash_password(password),
        platform_role_id=lector_role.id if lector_role else None,
        is_active=True,
        is_email_verified=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "id": str(new_user.id),
        "username": new_user.username,
        "email": new_user.email,
        "role": lector_role.role.value if lector_role else "LECTOR",
        "is_active": new_user.is_active,
        "permissions": {},
    }


@router.patch("/users/{user_id}/role")
def change_user_role(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Asigna un rol de sistema a un usuario."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(models.Role).filter(models.Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    user.role_id = role_id
    user.role = role.name.lower().replace(
        " ", "_"
    )  # Keep the flat role field aligned with the role catalog
    db.commit()
    return {"status": "success", "new_role": role.name}


# --- AUDIT & SECURITY ---


@router.get("/audit", response_model=List[Dict[str, Any]])
def list_admin_audit(
    limit: int = 100,
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
    result = []
    for c in comments:
        user = db.query(models.User).filter(models.User.id == c.author_id).first()
        thread = (
            db.query(models.ForumThread)
            .filter(models.ForumThread.id == c.thread_id)
            .first()
        )
        result.append(
            {
                "id": c.id,
                "author": user.username if user else "Anónimo",
                "text": c.content,
                "context": thread.title if thread else "General",
                "type": thread.category if thread else "Foro",
                "created_at": c.created_at.isoformat(),
            }
        )
    return result


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
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
    return {"status": "success"}


# --- SPIRITUAL MILESTONES (BADGES) ---


@router.get("/milestones", response_model=List[Dict[str, Any]])
def list_milestones(db: Session = Depends(get_db), _user=Depends(require_active_user)):
    """Lista hitos espirituales (insignias) y estadísticas de obtención."""
    badges = db.query(models.Badge).all()
    result = []
    for b in badges:
        count = (
            db.query(models.UserBadge).filter(models.UserBadge.badge_id == b.id).count()
        )
        result.append(
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "icon": b.icon_key,
                "xp": b.xp_reward,
                "count": count,
            }
        )
    return result


@router.post("/milestones/award")
def award_milestone_bulk(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Asigna un hito a una lista de miembros de forma masiva."""
    badge_id = payload["badge_id"]
    persona_ids = payload.get("persona_ids", payload.get("member_ids", []))

    import uuid as _uuid
    awarded_count = 0
    for persona_id in persona_ids:
        try:
            pid = _uuid.UUID(str(persona_id))
        except (ValueError, AttributeError):
            continue
        persona = db.query(models.Persona).filter(models.Persona.id == pid).first()
        if persona and persona.user_id:
            exists = (
                db.query(models.UserBadge)
                .filter(
                    models.UserBadge.user_id == persona.user_id,
                    models.UserBadge.badge_id == badge_id,
                )
                .first()
            )

            if not exists:
                ub = models.UserBadge(user_id=persona.user_id, badge_id=badge_id)
                db.add(ub)
                awarded_count += 1

    db.commit()
    return {"status": "success", "awarded": awarded_count}


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
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea una nueva categoría de donación."""
    cat = models.DonationCategory(
        name=payload["name"],
        description=payload.get("description"),
        color_code=payload.get("color", "blue"),
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
    rule_id: int,
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
    rule_id: int,
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
        from backend.models_auth import RolPlataforma
        roles = db.query(RolPlataforma).all()
        return [
            {"id": str(r.id), "nombre": r.nombre, "permisos": r.permisos}
            for r in roles
        ]
    except Exception:
        return []


@router.post("/auth-role-definitions")
def create_auth_role_definition(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea un nuevo rol auth (RolPlataforma)."""
    from backend.models_auth import RolPlataforma
    nombre = str(payload.get("nombre", "")).strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="nombre es requerido")
    existing = db.query(RolPlataforma).filter(RolPlataforma.nombre == nombre).first()
    if existing:
        raise HTTPException(status_code=409, detail="El rol ya existe")
    permisos = payload.get("permisos", {})
    rol = RolPlataforma(nombre=nombre, permisos=permisos)
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return {"id": str(rol.id), "nombre": rol.nombre, "permisos": rol.permisos}


@router.patch("/auth-role-definitions/{role_id}")
def update_auth_role_definition(
    role_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza permisos de un rol auth."""
    import uuid
    from backend.models_auth import RolPlataforma
    try:
        rid = uuid.UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="role_id invalido")
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if "permisos" in payload:
        rol.permisos = payload["permisos"]
    if "nombre" in payload:
        rol.nombre = payload["nombre"]
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
    import uuid
    from backend.models_auth import RolPlataforma, Usuario
    try:
        rid = uuid.UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="role_id invalido")
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    assigned = db.query(Usuario).filter(Usuario.rol_plataforma_id == rid).count()
    if assigned > 0:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar el rol \"{rol.nombre}\" porque tiene {assigned} usuario(s) asignado(s)",
        )
    rol.deleted_at = _utcnow()
    db.commit()


@router.get("/user-module-roles")
def list_user_module_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todas las asignaciones de roles modulares."""
    try:
        from backend.models_auth import UsuarioRolModulo, RolPlataforma
        rows = (
            db.query(UsuarioRolModulo, RolPlataforma)
            .join(RolPlataforma, RolPlataforma.id == UsuarioRolModulo.rol_id)
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
        return []


@router.post("/user-module-roles")
def assign_user_module_role(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Asigna un rol modular a un usuario UUID-based."""
    import uuid
    from backend.models_auth import UsuarioRolModulo, RolPlataforma, Usuario
    user_id_str = str(payload.get("user_id", ""))
    modulo = str(payload.get("modulo", "")).strip().lower()
    rol_id_str = str(payload.get("rol_id", ""))
    if not user_id_str or not modulo or not rol_id_str:
        raise HTTPException(status_code=400, detail="user_id, modulo y rol_id son requeridos")
    try:
        uid = uuid.UUID(user_id_str)
        rid = uuid.UUID(rol_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id o rol_id invalidos")
    user = db.query(Usuario).filter(Usuario.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    existing = db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.user_id == uid,
        UsuarioRolModulo.modulo == modulo,
    ).first()
    if existing:
        existing.rol_id = rid
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
    from datetime import datetime, timezone
    import uuid
    from backend.models_auth import UsuarioRolModulo
    try:
        aid = uuid.UUID(assignment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="assignment_id invalido")
    umr = db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.id == aid,
        UsuarioRolModulo.deleted_at.is_(None)
    ).first()
    if not umr:
        raise HTTPException(status_code=404, detail="Asignacion no encontrada")
    umr.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/users-with-roles")
def list_users_with_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista todos los usuarios auth v3 con sus roles de plataforma y modulares.

    Util para el panel de administracion de permisos granulares.
    """
    import uuid
    from backend.models_auth import Usuario, RolPlataforma, UsuarioRolModulo
    from backend.models_crm import Persona

    users = db.query(Usuario).all()
    result = []
    for u in users:
        persona = db.query(Persona).filter(Persona.id == u.id).first()
        nombre = persona.nombre_completo if persona else "—"

        rol_plat = db.query(RolPlataforma).filter(RolPlataforma.id == u.rol_plataforma_id).first() if u.rol_plataforma_id else None

        modulares = db.query(UsuarioRolModulo, RolPlataforma).join(
            RolPlataforma, RolPlataforma.id == UsuarioRolModulo.rol_id
        ).filter(UsuarioRolModulo.user_id == u.id).all()

        result.append({
            "user_id": str(u.id),
            "username": u.username,
            "email": u.email,
            "nombre": nombre,
            "is_active": u.is_active,
            "rol_plataforma": {"id": str(rol_plat.id), "nombre": rol_plat.nombre} if rol_plat else None,
            "roles_modulares": [
                {"id": str(umr.id), "modulo": umr.modulo, "rol_id": str(r.id), "rol_nombre": r.nombre}
                for umr, r in modulares
            ],
        })
    return result

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_admin
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
    db.delete(role)
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
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Obtiene los permisos actuales de un usuario (rol + override)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Role-based permissions
    role_perms = {}
    if user.user_role_obj:
        perms = user.user_role_obj.permissions or {}
        role_perms = dict(perms) if isinstance(perms, dict) else {}

    # Per-user overrides
    override_perms = {}
    if user.permissions_override:
        perms = user.permissions_override.permissions or {}
        override_perms = dict(perms) if isinstance(perms, dict) else {}

    # Effective permissions (merged)
    effective = dict(role_perms)
    effective.update(override_perms)

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "role_permissions": role_perms,
        "override_permissions": override_perms,
        "effective_permissions": effective,
    }


@router.put("/users/{user_id}/permissions")
def set_user_permissions(
    user_id: int,
    payload: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Asigna permisos modulares a un usuario (nivel lector/editor/gestor).

    Ejemplo del payload:
    ```json
    {
        "crm": "read",
        "projects": "manage",
        "academy": "study",
        "finance": "read"
    }
    ```
    Usar ``null`` o omitir un módulo para quitar el permiso.
    Los módulos válidos son: crm, finance, projects, cms, academy, messaging.
    Los niveles válidos son: read, edit, manage (y study para academy).
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
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
            resolved_perms[perm_key] = level

    # Upsert UserPermission row
    override = (
        db.query(models.UserPermission)
        .filter(models.UserPermission.user_id == user_id)
        .first()
    )

    if override:
        override.permissions = resolved_perms
    else:
        override = models.UserPermission(user_id=user_id, permissions=resolved_perms)
        db.add(override)

    db.commit()
    return {"status": "success", "user_id": user_id, "permissions": resolved_perms}


# --- CHURCH LOCATIONS ---


@router.get("/locations", response_model=List[Dict[str, Any]])
def list_locations(db: Session = Depends(get_db), _user=Depends(require_active_user)):
    """Lista todas las sedes de la iglesia."""
    locs = db.query(models.ChurchLocation).all()
    return [
        {
            "id": l.id,
            "name": l.name,
            "address": l.address,
            "pastor": l.pastor_name,
            "active": l.is_active,
            "type": l.location_type,
        }
        for l in locs
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


@router.get("/members", response_model=List[Dict[str, Any]])
def list_admin_members(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Lista miembros para administracion."""
    personas = db.query(models.Persona).all()
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
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    """Lista usuarios para gestión de permisos."""
    users = db.query(models.User).all()
    result = []
    for u in users:
        # Resolver permisos efectivos para que el frontend pueda mostrarlos
        role_perms = {}
        if u.user_role_obj:
            rp = u.user_role_obj.permissions or {}
            role_perms = dict(rp) if isinstance(rp, dict) else {}
        override_perms = {}
        if u.permissions_override:
            op = u.permissions_override.permissions or {}
            override_perms = dict(op) if isinstance(op, dict) else {}
        effective = dict(role_perms)
        effective.update(override_perms)
        result.append(
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "role_id": u.role_id,
                "is_active": u.is_active,
                "permissions": effective,
                "role_permissions": role_perms,
                "override_permissions": override_perms,
            }
        )
    return result


@router.post("/users", response_model=Dict[str, Any])
def create_admin_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea un nuevo usuario desde el panel de administracion."""
    from backend.core.permissions import hash_password

    username = str(payload.get("username", "")).strip()
    email = str(payload.get("email", "")).strip()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "estudiante")).strip()
    if not username or not email or not password:
        raise HTTPException(
            status_code=400, detail="username, email y password son requeridos"
        )
    existing = (
        db.query(models.User)
        .filter((models.User.username == username) | (models.User.email == email))
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Usuario o email ya existe")
    user = models.User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
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
    for l in logs:
        result.append(
            {
                "id": l.id,
                "actor_user_id": l.actor_user_id,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "created_at": l.created_at.isoformat(),
                "metadata": l.metadata_json or {},
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
    db.delete(comment)
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
    db.delete(rule)
    db.commit()
    return {"status": "success"}

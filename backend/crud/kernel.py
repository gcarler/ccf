"""CRUD del Kernel — Protocolo de Identidad y Roles.

Todas las operaciones reciben persona_id (UUID str), no user_id (int).

Dimensión A: Ministerios (Efesios 4:11)
Dimensión B: Roles en la Iglesia (embudo de consolidación)
Dimensión C: Roles de Plataforma (RBAC)
Estado Vital: ACTIVO / INACTIVO
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow


def _enum_val(e):
    return e.value if hasattr(e, "value") else e


def _get_persona(db: Session, persona_id: str):
    return (
        db.query(models.Persona)
        .filter(models.Persona.id == uuid.UUID(persona_id))
        .first()
    )


# ──────────────────────────────────────────────
# ESTADO VITAL (ACTIVO / INACTIVO)
# ──────────────────────────────────────────────

def get_persona_activity_status(db: Session, persona_id: str) -> Optional[str]:
    persona = _get_persona(db, persona_id)
    if not persona:
        return None
    return persona.estado_vital or "ACTIVO"


def set_persona_activity_status(
    db: Session, persona_id: str, status: str, changed_by_persona_id: str | None = None
) -> Optional[models.Persona]:
    persona = _get_persona(db, persona_id)
    if not persona:
        return None

    persona.estado_vital = status

    if status == "INACTIVO":
        from backend.models_governance import AdminAuditLog
        db.add(AdminAuditLog(
            actor_persona_id=None,  # changed_by_id is user.id; persona resolution needed at call site
            action="persona_deactivated",
            resource_type="persona",
            resource_id=str(persona_id),
            metadata_json={"reason": "Estado vital cambiado a INACTIVO", "changed_by": str(changed_by_persona_id) if changed_by_persona_id else None},
        ))

    db.commit()
    db.refresh(persona)
    return persona


def is_persona_active(db: Session, persona_id: str) -> bool:
    persona = _get_persona(db, persona_id)
    if not persona:
        return False
    return (persona.estado_vital or "ACTIVO") == "ACTIVO"


def can_receive_assignment(db: Session, persona_id_or_user_id) -> bool:
    if isinstance(persona_id_or_user_id, int):
        return is_user_active(db, persona_id_or_user_id)
    return is_persona_active(db, str(persona_id_or_user_id))


# ──────────────────────────────────────────────
# DIMENSIÓN A: MINISTERIOS
# ──────────────────────────────────────────────

def get_persona_ministries(db: Session, persona_id: str) -> List[dict]:
    from backend.models_kernel import PersonaMinistry
    rows = (
        db.query(PersonaMinistry)
        .filter(PersonaMinistry.persona_id == uuid.UUID(persona_id), PersonaMinistry.deleted_at.is_(None))
        .order_by(PersonaMinistry.is_primary.desc(), PersonaMinistry.recognized_at)
        .all()
    )
    return [
        {
            "id": r.id,
            "ministry": _enum_val(r.ministry),
            "is_primary": r.is_primary,
            "recognized_at": r.recognized_at,
            "recognized_by_persona_id": str(r.recognized_by_persona_id) if r.recognized_by_persona_id else None,
            "notes": r.notes,
        }
        for r in rows
    ]


def add_persona_ministry(
    db: Session,
    persona_id: str,
    ministry: str,
    is_primary: bool = False,
    recognized_by_persona_id: str | None = None,
    notes: str = None,
) -> Optional[dict]:
    from backend.models_kernel import PersonaMinistry
    pid = uuid.UUID(persona_id)
    existing = (
        db.query(PersonaMinistry)
        .filter(PersonaMinistry.persona_id == pid, PersonaMinistry.ministry == ministry)
        .first()
    )
    if existing:
        return None

    if is_primary:
        db.query(PersonaMinistry).filter(PersonaMinistry.persona_id == pid).update({"is_primary": False})

    row = PersonaMinistry(persona_id=pid, ministry=ministry, is_primary=is_primary,
                          recognized_by_persona_id=recognized_by_persona_id, notes=notes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "ministry": _enum_val(row.ministry),
            "is_primary": row.is_primary, "recognized_at": row.recognized_at}


def remove_persona_ministry(db: Session, persona_id: str, ministry: str) -> bool:
    from backend.models_kernel import PersonaMinistry
    row = (
        db.query(PersonaMinistry)
        .filter(PersonaMinistry.persona_id == uuid.UUID(persona_id),
                PersonaMinistry.ministry == ministry)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def set_primary_ministry(db: Session, persona_id: str, ministry: str) -> bool:
    from backend.models_kernel import PersonaMinistry
    pid = uuid.UUID(persona_id)
    row = (
        db.query(PersonaMinistry)
        .filter(PersonaMinistry.persona_id == pid, PersonaMinistry.ministry == ministry)
        .first()
    )
    if not row:
        return False
    db.query(PersonaMinistry).filter(
        PersonaMinistry.persona_id == pid, PersonaMinistry.ministry != ministry
    ).update({"is_primary": False})
    row.is_primary = True
    db.commit()
    return True


# ──────────────────────────────────────────────
# DIMENSIÓN B: ROL EN LA IGLESIA
# ──────────────────────────────────────────────

def get_persona_church_role(db: Session, persona_id: str) -> Optional[dict]:
    from backend.models_kernel import PersonaRoleAssignment
    row = (
        db.query(PersonaRoleAssignment)
        .filter(PersonaRoleAssignment.persona_id == uuid.UUID(persona_id))
        .first()
    )
    if not row:
        return None
    return {"id": row.id, "church_role": _enum_val(row.church_role),
            "assigned_at": row.assigned_at, "assigned_by_persona_id": str(row.assigned_by_persona_id) if row.assigned_by_persona_id else None, "notes": row.notes}


def set_persona_church_role(
    db: Session,
    persona_id: str,
    church_role: str,
    changed_by_persona_id: str | None = None,
    reason: str = None,
    notes: str = None,
) -> Optional[dict]:
    from backend.models_kernel import PersonaRoleAssignment, PersonaRoleHistory
    pid = uuid.UUID(persona_id)
    current = (
        db.query(PersonaRoleAssignment)
        .filter(PersonaRoleAssignment.persona_id == pid)
        .first()
    )
    old_role = current.church_role if current else None

    if current:
        current.church_role = church_role
        current.assigned_by_persona_id = changed_by_persona_id
        if notes:
            current.notes = notes
        row = current
    else:
        row = PersonaRoleAssignment(persona_id=pid, church_role=church_role,
                                    assigned_by_persona_id=changed_by_persona_id, notes=notes)
        db.add(row)

    db.add(PersonaRoleHistory(persona_id=pid, from_role=old_role, to_role=church_role,
                               reason=reason, changed_by_persona_id=changed_by_persona_id))
    db.commit()
    db.refresh(row)
    return {"id": row.id, "church_role": _enum_val(row.church_role),
            "assigned_at": row.assigned_at,
            "old_role": _enum_val(old_role) if old_role else None}


def get_church_role_history(db: Session, persona_id: str, limit: int = 50) -> List[dict]:
    from backend.models_kernel import PersonaRoleHistory
    rows = (
        db.query(PersonaRoleHistory)
        .filter(PersonaRoleHistory.persona_id == uuid.UUID(persona_id))
        .order_by(PersonaRoleHistory.changed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "from_role": _enum_val(r.from_role) if r.from_role else None,
            "to_role": _enum_val(r.to_role),
            "reason": r.reason,
            "changed_by": str(r.changed_by_persona_id) if r.changed_by_persona_id else None,
            "changed_at": r.changed_at,
        }
        for r in rows
    ]


def get_personas_by_church_role(
    db: Session, church_role: str, active_only: bool = True
) -> List[dict]:
    from backend.models_kernel import PersonaRoleAssignment
    query = (
        db.query(PersonaRoleAssignment, models.Persona)
        .join(models.Persona, models.Persona.id == PersonaRoleAssignment.persona_id)
        .filter(PersonaRoleAssignment.church_role == church_role)
    )
    if active_only:
        query = query.filter(
            (models.Persona.estado_vital == "ACTIVO") | (models.Persona.estado_vital.is_(None))
        )
    return [
        {
            "persona_id": str(p.id),
            "nombre_completo": p.first_name + " " + p.last_name,
            "email": p.email,
            "church_role": _enum_val(r.church_role),
        }
        for r, p in query.all()
    ]


# ──────────────────────────────────────────────
# DIMENSIÓN C: ROLES DE PLATAFORMA (RBAC)
# ──────────────────────────────────────────────

def get_platform_role_definitions(db: Session) -> List[dict]:
    from backend.models_kernel import PlatformRoleDefinition
    return [
        {"id": r.id, "role": _enum_val(r.role),
         "permissions": r.permissions, "description": r.description}
        for r in db.query(PlatformRoleDefinition).all()
    ]


def get_persona_platform_roles(db: Session, persona_id: str) -> List[dict]:
    from backend.models_kernel import PersonaPlatformRole, PlatformRoleDefinition
    rows = (
        db.query(PersonaPlatformRole, PlatformRoleDefinition)
        .join(PlatformRoleDefinition,
              PlatformRoleDefinition.id == PersonaPlatformRole.role_id)
        .filter(PersonaPlatformRole.persona_id == uuid.UUID(persona_id),
                PersonaPlatformRole.is_active)
        .all()
    )
    return [
        {"id": upr.id, "role": _enum_val(rd.role), "permissions": rd.permissions,
         "assigned_at": upr.assigned_at, "expires_at": upr.expires_at, "notes": upr.notes}
        for upr, rd in rows
    ]


def get_persona_effective_permissions(db: Session, persona_id: str) -> dict:
    from backend.models_kernel import PersonaPlatformRole, PlatformRoleDefinition
    rows = (
        db.query(PlatformRoleDefinition.permissions)
        .join(PersonaPlatformRole,
              PersonaPlatformRole.role_id == PlatformRoleDefinition.id)
        .filter(
            PersonaPlatformRole.persona_id == uuid.UUID(persona_id),
            PersonaPlatformRole.is_active,
            or_(
                PersonaPlatformRole.expires_at.is_(None),
                PersonaPlatformRole.expires_at > _utcnow(),
            ),
        )
        .all()
    )
    effective: dict = {}
    for (perms,) in rows:
        for module, actions in perms.items():
            if module not in effective:
                effective[module] = set()
            effective[module].update(actions)
    return {module: list(actions) for module, actions in effective.items()}


def assign_platform_role(
    db: Session,
    persona_id: str,
    platform_role: str,
    assigned_by_persona_id: str | None = None,
    expires_at: datetime = None,
    notes: str = None,
) -> Optional[dict]:
    from backend.models_kernel import PersonaPlatformRole, PlatformRoleDefinition
    role_def = (
        db.query(PlatformRoleDefinition)
        .filter(PlatformRoleDefinition.role == platform_role)
        .first()
    )
    if not role_def:
        return None
    pid = uuid.UUID(persona_id)
    existing = (
        db.query(PersonaPlatformRole)
        .filter(PersonaPlatformRole.persona_id == pid,
                PersonaPlatformRole.role_id == role_def.id,
                PersonaPlatformRole.is_active)
        .first()
    )
    if existing:
        return None
    row = PersonaPlatformRole(persona_id=pid, role_id=role_def.id,
                               assigned_by_persona_id=assigned_by_persona_id, expires_at=expires_at, notes=notes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "role": platform_role, "assigned_at": row.assigned_at,
            "expires_at": row.expires_at}


def revoke_platform_role(db: Session, persona_id: str, platform_role: str) -> bool:
    from backend.models_kernel import PersonaPlatformRole, PlatformRoleDefinition
    role_def = (
        db.query(PlatformRoleDefinition)
        .filter(PlatformRoleDefinition.role == platform_role)
        .first()
    )
    if not role_def:
        return False
    row = (
        db.query(PersonaPlatformRole)
        .filter(PersonaPlatformRole.persona_id == uuid.UUID(persona_id),
                PersonaPlatformRole.role_id == role_def.id,
                PersonaPlatformRole.is_active)
        .first()
    )
    if not row:
        return False
    row.is_active = False
    db.commit()
    return True


def persona_has_permission(db: Session, persona_id: str, module: str, action: str) -> bool:
    perms = get_persona_effective_permissions(db, persona_id)
    if "*" in perms and action in perms["*"]:
        return True
    return module in perms and action in perms[module]


# ──────────────────────────────────────────────
# PERFIL COMPLETO KERNEL
# ──────────────────────────────────────────────

def get_kernel_profile(db: Session, persona_id: str) -> Optional[dict]:
    persona = _get_persona(db, persona_id)
    if not persona:
        return None
    return {
        "persona_id": str(persona.id),
        "nombre_completo": persona.first_name + " " + persona.last_name,
        "email": persona.email,
        "estado_vital": persona.estado_vital or "ACTIVO",
        "dimension_a_ministerios": get_persona_ministries(db, persona_id),
        "dimension_b_rol_iglesia": get_persona_church_role(db, persona_id),
        "dimension_c_roles_plataforma": get_persona_platform_roles(db, persona_id),
        "permisos_efectivos": get_persona_effective_permissions(db, persona_id),
    }


# ──────────────────────────────────────────────
# BACKWARD COMPAT (user_id → persona_id via personas.user_id)
# ──────────────────────────────────────────────

def _persona_id_for_user(db: Session, user_id: int) -> Optional[str]:
    persona = (
        db.query(models.Persona)
        .filter(models.Persona.user_id == user_id)
        .first()
    )
    return str(persona.id) if persona else None


def get_user_ministries(db: Session, user_id: int) -> List[dict]:
    pid = _persona_id_for_user(db, user_id)
    return get_persona_ministries(db, pid) if pid else []


def add_user_ministry(db: Session, user_id: int, ministry: str, **kwargs) -> Optional[dict]:
    pid = _persona_id_for_user(db, user_id)
    return add_persona_ministry(db, pid, ministry, **{k:v for k,v in kwargs.items() if k != "changed_by_id"}) if pid else None


def remove_user_ministry(db: Session, user_id: int, ministry: str) -> bool:
    pid = _persona_id_for_user(db, user_id)
    return remove_persona_ministry(db, pid, ministry) if pid else False


def get_user_church_role(db: Session, user_id: int) -> Optional[dict]:
    pid = _persona_id_for_user(db, user_id)
    return get_persona_church_role(db, pid) if pid else None


def set_user_church_role(db: Session, user_id: int, church_role: str, **kwargs) -> Optional[dict]:
    pid = _persona_id_for_user(db, user_id)
    return set_persona_church_role(db, pid, church_role, **kwargs) if pid else None


def get_church_role_history_by_user(db: Session, user_id: int, limit: int = 50) -> List[dict]:
    pid = _persona_id_for_user(db, user_id)
    return get_church_role_history(db, pid, limit=limit) if pid else []


def get_users_by_church_role(db: Session, church_role: str, active_only: bool = True) -> List[dict]:
    return get_personas_by_church_role(db, church_role, active_only=active_only)


def get_user_platform_roles(db: Session, user_id: int) -> List[dict]:
    pid = _persona_id_for_user(db, user_id)
    return get_persona_platform_roles(db, pid) if pid else []


def get_user_effective_permissions(db: Session, user_id: int) -> dict:
    pid = _persona_id_for_user(db, user_id)
    return get_persona_effective_permissions(db, pid) if pid else {}


def set_user_activity_status(db: Session, user_id: int, status: str, changed_by_persona_id: str | None = None):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    user.is_active = (status == "ACTIVO")
    pid = _persona_id_for_user(db, user_id)
    if pid:
        set_persona_activity_status(db, pid, status, changed_by_persona_id)
    db.commit()
    db.refresh(user)
    return user


def get_user_activity_status(db: Session, user_id: int) -> Optional[str]:
    pid = _persona_id_for_user(db, user_id)
    return get_persona_activity_status(db, pid) if pid else None


def is_user_active(db: Session, user_id: int) -> bool:
    pid = _persona_id_for_user(db, user_id)
    if pid:
        return is_persona_active(db, pid)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return bool(user.is_active) if user else False


def set_primary_ministry(db: Session, persona_id_or_user_id, ministry: str) -> bool:
    if isinstance(persona_id_or_user_id, int):
        pid = _persona_id_for_user(db, persona_id_or_user_id)
        return False if not pid else set_primary_ministry_by_persona(db, pid, ministry)
    return set_primary_ministry_by_persona(db, str(persona_id_or_user_id), ministry)


def set_primary_ministry_by_persona(db: Session, persona_id: str, ministry: str) -> bool:
    from backend.models_kernel import PersonaMinistry
    pid = uuid.UUID(persona_id)
    row = (
        db.query(PersonaMinistry)
        .filter(PersonaMinistry.persona_id == pid, PersonaMinistry.ministry == ministry)
        .first()
    )
    if not row:
        return False
    db.query(PersonaMinistry).filter(
        PersonaMinistry.persona_id == pid, PersonaMinistry.ministry != ministry
    ).update({"is_primary": False})
    row.is_primary = True
    db.commit()
    return True


def assign_platform_role(
    db: Session,
    persona_id_or_user_id,
    platform_role: str,
    assigned_by_persona_id: str | None = None,
    expires_at=None,
    notes: str = None,
) -> Optional[dict]:
    if isinstance(persona_id_or_user_id, int):
        pid = _persona_id_for_user(db, persona_id_or_user_id)
        if not pid:
            return None
        persona_id = pid
    else:
        persona_id = str(persona_id_or_user_id)
    return _assign_platform_role_by_persona(db, persona_id, platform_role, assigned_by_persona_id, expires_at, notes)


def _assign_platform_role_by_persona(
    db: Session,
    persona_id: str,
    platform_role: str,
    assigned_by_persona_id: str | None = None,
    expires_at=None,
    notes: str = None,
) -> Optional[dict]:
    from backend.models_kernel import PersonaPlatformRole, PlatformRoleDefinition
    role_def = (
        db.query(PlatformRoleDefinition)
        .filter(PlatformRoleDefinition.role == platform_role)
        .first()
    )
    if not role_def:
        return None
    pid = uuid.UUID(persona_id)
    existing = (
        db.query(PersonaPlatformRole)
        .filter(PersonaPlatformRole.persona_id == pid,
                PersonaPlatformRole.role_id == role_def.id,
                PersonaPlatformRole.is_active)
        .first()
    )
    if existing:
        return None
    row = PersonaPlatformRole(persona_id=pid, role_id=role_def.id,
                               assigned_by_persona_id=assigned_by_persona_id, expires_at=expires_at, notes=notes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "role": platform_role, "assigned_at": row.assigned_at,
            "expires_at": row.expires_at}


def revoke_platform_role(db: Session, persona_id_or_user_id, platform_role: str) -> bool:
    if isinstance(persona_id_or_user_id, int):
        pid = _persona_id_for_user(db, persona_id_or_user_id)
        if not pid:
            return False
        persona_id = pid
    else:
        persona_id = str(persona_id_or_user_id)
    return _revoke_platform_role_by_persona(db, persona_id, platform_role)


def _revoke_platform_role_by_persona(db: Session, persona_id: str, platform_role: str) -> bool:
    from backend.models_kernel import PersonaPlatformRole, PlatformRoleDefinition
    role_def = (
        db.query(PlatformRoleDefinition)
        .filter(PlatformRoleDefinition.role == platform_role)
        .first()
    )
    if not role_def:
        return False
    row = (
        db.query(PersonaPlatformRole)
        .filter(PersonaPlatformRole.persona_id == uuid.UUID(persona_id),
                PersonaPlatformRole.role_id == role_def.id,
                PersonaPlatformRole.is_active)
        .first()
    )
    if not row:
        return False
    row.is_active = False
    db.commit()
    return True


def get_church_role_history(db: Session, persona_or_user_id, limit: int = 50) -> List[dict]:
    if isinstance(persona_or_user_id, int):
        return get_church_role_history_by_user(db, persona_or_user_id, limit=limit)
    from backend.models_kernel import PersonaRoleHistory
    rows = (
        db.query(PersonaRoleHistory)
        .filter(PersonaRoleHistory.persona_id == uuid.UUID(str(persona_or_user_id)))
        .order_by(PersonaRoleHistory.changed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "from_role": _enum_val(r.from_role) if r.from_role else None,
            "to_role": _enum_val(r.to_role),
            "reason": r.reason,
            "changed_by": str(r.changed_by_persona_id) if r.changed_by_persona_id else None,
            "changed_at": r.changed_at,
        }
        for r in rows
    ]


def get_kernel_profile(db: Session, persona_or_user_id, **kwargs) -> Optional[dict]:
    if isinstance(persona_or_user_id, int):
        pid = _persona_id_for_user(db, persona_or_user_id)
        if not pid:
            return None
        result = _get_kernel_profile_by_persona(db, pid)
        if result:
            result["user_id"] = persona_or_user_id
        return result
    return _get_kernel_profile_by_persona(db, str(persona_or_user_id))


def _get_kernel_profile_by_persona(db: Session, persona_id: str) -> Optional[dict]:
    persona = _get_persona(db, persona_id)
    if not persona:
        return None
    return {
        "persona_id": str(persona.id),
        "nombre_completo": persona.first_name + " " + persona.last_name,
        "email": persona.email,
        "estado_vital": persona.estado_vital or "ACTIVO",
        "dimension_a_ministerios": get_persona_ministries(db, persona_id),
        "dimension_b_rol_iglesia": get_persona_church_role(db, persona_id),
        "dimension_c_roles_plataforma": get_persona_platform_roles(db, persona_id),
        "permisos_efectivos": get_persona_effective_permissions(db, persona_id),
    }

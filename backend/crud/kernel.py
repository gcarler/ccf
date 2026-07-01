"""CRUD del Kernel — Protocolo de Identidad y Roles.

Todas las operaciones reciben persona_id (UUID str), no user_id (int).

Dimensión A: Ministerios (Efesios 4:11)
Dimensión B: Roles en la Iglesia (embudo de consolidación)
Dimensión C: Roles de Plataforma (RBAC)
Estado Vital: ACTIVO / INACTIVO
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow


def _enum_val(e):
    return e.value if hasattr(e, "value") else e


def _get_persona(db: Session, persona_id: str):
    return db.query(models.Persona).filter(models.Persona.id == uuid.UUID(persona_id)).first()


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

        db.add(
            AdminAuditLog(
                actor_persona_id=None,  # changed_by_id is user.id; persona resolution needed at call site
                action="persona_deactivated",
                resource_type="persona",
                resource_id=str(persona_id),
                metadata_json={
                    "reason": "Estado vital cambiado a INACTIVO",
                    "changed_by": str(changed_by_persona_id) if changed_by_persona_id else None,
                },
            )
        )

    db.commit()
    db.refresh(persona)
    return persona


def is_persona_active(db: Session, persona_id: str) -> bool:
    persona = _get_persona(db, persona_id)
    if not persona:
        return False
    return (persona.estado_vital or "ACTIVO") == "ACTIVO"


def can_receive_assignment(db: Session, persona_id: str) -> bool:
    return is_persona_active(db, str(persona_id))


# ──────────────────────────────────────────────
# DIMENSIÓN A: MINISTERIOS
# ──────────────────────────────────────────────


def get_persona_ministries(db: Session, persona_id: str) -> List[dict]:
    from backend.models_kernel import PersonaMinistry

    rows = (
        db.query(PersonaMinistry)
        .filter(
            PersonaMinistry.persona_id == uuid.UUID(persona_id),
            PersonaMinistry.deleted_at.is_(None),
        )
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

    row = PersonaMinistry(
        persona_id=pid,
        ministry=ministry,
        is_primary=is_primary,
        recognized_by_persona_id=recognized_by_persona_id,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "ministry": _enum_val(row.ministry),
        "is_primary": row.is_primary,
        "recognized_at": row.recognized_at,
    }


def remove_persona_ministry(db: Session, persona_id: str, ministry: str) -> bool:
    from backend.models_kernel import PersonaMinistry

    row = (
        db.query(PersonaMinistry)
        .filter(
            PersonaMinistry.persona_id == uuid.UUID(persona_id),
            PersonaMinistry.ministry == ministry,
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ──────────────────────────────────────────────
# DIMENSIÓN B: ROL EN LA IGLESIA
# ──────────────────────────────────────────────


def get_persona_church_role(db: Session, persona_id: str) -> Optional[dict]:
    from backend.models_kernel import PersonaRoleAssignment

    row = db.query(PersonaRoleAssignment).filter(PersonaRoleAssignment.persona_id == uuid.UUID(persona_id)).first()
    if not row:
        return None
    return {
        "id": row.id,
        "church_role": _enum_val(row.church_role),
        "assigned_at": row.assigned_at,
        "assigned_by_persona_id": str(row.assigned_by_persona_id) if row.assigned_by_persona_id else None,
        "notes": row.notes,
    }


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
    current = db.query(PersonaRoleAssignment).filter(PersonaRoleAssignment.persona_id == pid).first()
    old_role = current.church_role if current else None

    if current:
        current.church_role = church_role
        current.assigned_by_persona_id = changed_by_persona_id
        if notes:
            current.notes = notes
        row = current
    else:
        row = PersonaRoleAssignment(
            persona_id=pid,
            church_role=church_role,
            assigned_by_persona_id=changed_by_persona_id,
            notes=notes,
        )
        db.add(row)

    db.add(
        PersonaRoleHistory(
            persona_id=pid,
            from_role=old_role,
            to_role=church_role,
            reason=reason,
            changed_by_persona_id=changed_by_persona_id,
        )
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "church_role": _enum_val(row.church_role),
        "assigned_at": row.assigned_at,
        "old_role": _enum_val(old_role) if old_role else None,
    }


def get_personas_by_church_role(db: Session, church_role: str, active_only: bool = True) -> List[dict]:
    from backend.models_kernel import PersonaRoleAssignment

    query = (
        db.query(PersonaRoleAssignment, models.Persona)
        .join(models.Persona, models.Persona.id == PersonaRoleAssignment.persona_id)
        .filter(PersonaRoleAssignment.church_role == church_role)
    )
    if active_only:
        query = query.filter((models.Persona.estado_vital == "ACTIVO") | (models.Persona.estado_vital.is_(None)))
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
# ROLES DE PLATAFORMA (AUTH V3)
# ──────────────────────────────────────────────


def get_platform_role_definitions(db: Session) -> List[dict]:
    from backend.models_auth import RolPlataforma

    return [
        {
            "id": str(role.id),
            "role": role.nombre,
            "permissions": role.permisos or {},
        }
        for role in db.query(RolPlataforma).order_by(RolPlataforma.nombre).all()
    ]


def get_persona_platform_roles(db: Session, persona_id: str) -> List[dict]:
    from backend.models_auth import Usuario

    user = db.query(Usuario).filter(Usuario.id == uuid.UUID(str(persona_id))).first()
    if not user or not user.rol_plataforma:
        return []
    role = user.rol_plataforma
    return [
        {
            "id": str(user.id),
            "role": role.nombre,
            "permissions": role.permisos or {},
            "assigned_at": user.updated_at or user.created_at,
            "expires_at": None,
            "notes": None,
        }
    ]


def get_persona_effective_permissions(db: Session, persona_id: str) -> dict:
    from backend.models_auth import Usuario
    from backend.core.permissions import get_user_effective_permissions

    user = db.query(Usuario).filter(Usuario.id == uuid.UUID(str(persona_id))).first()
    return get_user_effective_permissions(db, user) if user else {}


def persona_has_permission(db: Session, persona_id: str, module: str, action: str) -> bool:
    permissions = get_persona_effective_permissions(db, persona_id)
    return (
        f"{module}:{action}" in permissions
        or f"{module}:manage" in permissions
        or "*" in permissions
    )


def set_primary_ministry(db: Session, persona_id: str, ministry: str) -> bool:
    from backend.models_kernel import PersonaMinistry

    pid = uuid.UUID(str(persona_id))
    row = db.query(PersonaMinistry).filter(
        PersonaMinistry.persona_id == pid,
        PersonaMinistry.ministry == ministry,
    ).first()
    if not row:
        return False
    db.query(PersonaMinistry).filter(
        PersonaMinistry.persona_id == pid,
        PersonaMinistry.ministry != ministry,
    ).update({"is_primary": False})
    row.is_primary = True
    db.commit()
    return True


def get_church_role_history(db: Session, persona_id: str, limit: int = 50) -> List[dict]:
    from backend.models_kernel import PersonaRoleHistory

    rows = (
        db.query(PersonaRoleHistory)
        .filter(PersonaRoleHistory.persona_id == uuid.UUID(str(persona_id)))
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


def get_kernel_profile(db: Session, persona_id: str) -> Optional[dict]:
    return _get_kernel_profile_by_persona(db, str(persona_id))


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

"""CRUD del Kernel CCF — Protocolo de Identidad y Roles.

Dimensión A: Ministerios (Efesios 4:11)
Dimensión B: Roles en la Iglesia (embudo de consolidación)
Dimensión C: Roles de Plataforma (RBAC)
Estado Vital: ACTIVO / INACTIVO
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow


def _enum_val(e):
    """Safely extract enum value or return the raw value."""
    return e.value if hasattr(e, 'value') else e


# ──────────────────────────────────────────────
# ESTADO VITAL (ACTIVO / INACTIVO)
# ──────────────────────────────────────────────

def get_user_activity_status(db: Session, user_id: int) -> Optional[str]:
    """Retorna 'ACTIVO' o 'INACTIVO' para un usuario."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    return "ACTIVO" if user.is_active else "INACTIVO"


def set_user_activity_status(
    db: Session, user_id: int, status: str, changed_by_id: int = None
) -> Optional[models.User]:
    """Cambia el estado vital de un usuario.

    Regla de Inactividad: Si se marca como INACTIVO, el historial permanece
    intacto pero el perfil se bloquea para nuevas asignaciones.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    was_active = user.is_active
    user.is_active = status == "ACTIVO"

    # Registrar transición en historial si cambió de rol de iglesia
    if not user.is_active and was_active:
        # Registrar en auditoría que se desactivó
        from backend.models_governance import AdminAuditLog

        audit = AdminAuditLog(
            actor_user_id=changed_by_id,
            action="user_deactivated",
            resource_type="user",
            resource_id=user_id,
            metadata_json={
                "reason": "Estado vital cambiado a INACTIVO",
                "changed_by": changed_by_id,
            },
        )
        db.add(audit)

    db.commit()
    db.refresh(user)
    return user


def is_user_active(db: Session, user_id: int) -> bool:
    """Verifica si un usuario está ACTIVO. Para chequeos rápidos."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user.is_active if user else False


def can_receive_assignment(db: Session, user_id: int) -> bool:
    """Verifica si un usuario puede recibir nuevas asignaciones.

    Regla de Inactividad: Usuarios INACTIVOS no pueden ser delegados
    en tareas de proyectos, ni aparecer en listas de selección activa.
    """
    if not is_user_active(db, user_id):
        return False
    return True


# ──────────────────────────────────────────────
# DIMENSIÓN A: MINISTERIOS (EFESIOS 4:11)
# ──────────────────────────────────────────────

def get_user_ministries(db: Session, user_id: int) -> List[dict]:
    """Retorna todos los ministerios reconocidos de un usuario."""
    from backend.models_kernel import UserMinistry

    rows = (
        db.query(UserMinistry)
        .filter(UserMinistry.user_id == user_id)
        .order_by(UserMinistry.is_primary.desc(), UserMinistry.recognized_at)
        .all()
    )
    return [
        {
            "id": r.id,
            "ministry": _enum_val(r.ministry),
            "is_primary": r.is_primary,
            "recognized_at": r.recognized_at,
            "recognized_by": r.recognized_by,
            "notes": r.notes,
        }
        for r in rows
    ]


def add_user_ministry(
    db: Session,
    user_id: int,
    ministry: str,
    is_primary: bool = False,
    recognized_by_id: int = None,
    notes: str = None,
) -> Optional[dict]:
    """Agrega un ministerio reconocido a un usuario."""
    from backend.models_kernel import UserMinistry

    # Verificar que no exista ya
    existing = (
        db.query(UserMinistry)
        .filter(UserMinistry.user_id == user_id, UserMinistry.ministry == ministry)
        .first()
    )
    if existing:
        return None

    # Si es primary, quitar el flag de los demás
    if is_primary:
        (
            db.query(UserMinistry)
            .filter(UserMinistry.user_id == user_id)
            .update({"is_primary": False})
        )

    row = UserMinistry(
        user_id=user_id,
        ministry=ministry,
        is_primary=is_primary,
        recognized_by=recognized_by_id,
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


def remove_user_ministry(db: Session, user_id: int, ministry: str) -> bool:
    """Elimina un ministerio reconocido de un usuario."""
    from backend.models_kernel import UserMinistry

    row = (
        db.query(UserMinistry)
        .filter(UserMinistry.user_id == user_id, UserMinistry.ministry == ministry)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def set_primary_ministry(db: Session, user_id: int, ministry: str) -> bool:
    """Establece un ministerio como principal."""
    from backend.models_kernel import UserMinistry

    # Verificar que existe
    row = (
        db.query(UserMinistry)
        .filter(UserMinistry.user_id == user_id, UserMinistry.ministry == ministry)
        .first()
    )
    if not row:
        return False

    # Quitar primary de los demás
    (
        db.query(UserMinistry)
        .filter(UserMinistry.user_id == user_id, UserMinistry.ministry != ministry)
        .update({"is_primary": False})
    )
    row.is_primary = True
    db.commit()
    return True


# ──────────────────────────────────────────────
# DIMENSIÓN B: ROLES EN LA IGLESIA
# ──────────────────────────────────────────────

def get_user_church_role(db: Session, user_id: int) -> Optional[dict]:
    """Retorna el rol actual en la iglesia de un usuario."""
    from backend.models_kernel import UserRoleAssignment

    row = (
        db.query(UserRoleAssignment)
        .filter(UserRoleAssignment.user_id == user_id)
        .first()
    )
    if not row:
        return None
    return {
        "id": row.id,
        "church_role": _enum_val(row.church_role),
        "assigned_at": row.assigned_at,
        "assigned_by": row.assigned_by,
        "notes": row.notes,
    }


def set_user_church_role(
    db: Session,
    user_id: int,
    church_role: str,
    changed_by_id: int = None,
    reason: str = None,
    notes: str = None,
) -> Optional[dict]:
    """Cambia el rol en la iglesia de un usuario y registra el historial."""
    from backend.models_kernel import UserRoleAssignment, UserRoleHistory

    # Obtener rol anterior
    current = (
        db.query(UserRoleAssignment)
        .filter(UserRoleAssignment.user_id == user_id)
        .first()
    )
    old_role = current.church_role if current else None

    # Crear o actualizar asignación
    if current:
        current.church_role = church_role
        current.assigned_by = changed_by_id
        if notes:
            current.notes = notes
        row = current
    else:
        row = UserRoleAssignment(
            user_id=user_id,
            church_role=church_role,
            assigned_by=changed_by_id,
            notes=notes,
        )
        db.add(row)

    # Registrar en historial
    history = UserRoleHistory(
        user_id=user_id,
        from_role=old_role,
        to_role=church_role,
        reason=reason,
        changed_by=changed_by_id,
    )
    db.add(history)

    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "church_role": _enum_val(row.church_role),
        "assigned_at": row.assigned_at,
        "old_role": _enum_val(old_role) if old_role else None,
    }


def get_church_role_history(
    db: Session, user_id: int, limit: int = 50
) -> List[dict]:
    """Retorna el historial de cambios de rol de iglesia."""
    from backend.models_kernel import UserRoleHistory

    rows = (
        db.query(UserRoleHistory)
        .filter(UserRoleHistory.user_id == user_id)
        .order_by(UserRoleHistory.changed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "from_role": _enum_val(r.from_role) if r.from_role else None,
            "to_role": r.to_role.value if hasattr(r.to_role, "value") else r.to_role,
            "reason": r.reason,
            "changed_by": r.changed_by,
            "changed_at": r.changed_at,
        }
        for r in rows
    ]


def get_users_by_church_role(
    db: Session, church_role: str, active_only: bool = True
) -> List[dict]:
    """Retorna todos los usuarios con un rol de iglesia específico."""
    from backend.models_kernel import UserRoleAssignment

    query = (
        db.query(UserRoleAssignment, models.User)
        .join(models.User, models.User.id == UserRoleAssignment.user_id)
        .filter(UserRoleAssignment.church_role == church_role)
    )
    if active_only:
        query = query.filter(models.User.is_active)

    results = query.all()
    return [
        {
            "user_id": u.id,
            "username": u.username,
            "email": u.email,
            "church_role": _enum_val(r.church_role),
        }
        for r, u in results
    ]


# ──────────────────────────────────────────────
# DIMENSIÓN C: ROLES DE PLATAFORMA (RBAC)
# ──────────────────────────────────────────────

def get_platform_role_definitions(db: Session) -> List[dict]:
    """Retorna todas las definiciones de roles de plataforma."""
    from backend.models_kernel import PlatformRoleDefinition

    rows = db.query(PlatformRoleDefinition).all()
    return [
        {
            "id": r.id,
            "role": r.role.value if hasattr(r.role, "value") else r.role,
            "permissions": r.permissions,
            "description": r.description,
        }
        for r in rows
    ]


def get_user_platform_roles(db: Session, user_id: int) -> List[dict]:
    """Retorna todos los roles de plataforma activos de un usuario."""
    from backend.models_kernel import UserPlatformRole, PlatformRoleDefinition

    rows = (
        db.query(UserPlatformRole, PlatformRoleDefinition)
        .join(
            PlatformRoleDefinition,
            PlatformRoleDefinition.id == UserPlatformRole.role_id,
        )
        .filter(
            UserPlatformRole.user_id == user_id,
            UserPlatformRole.is_active,
        )
        .all()
    )
    return [
        {
            "id": upr.id,
            "role": rd.role.value if hasattr(rd.role, "value") else rd.role,
            "permissions": rd.permissions,
            "assigned_at": upr.assigned_at,
            "expires_at": upr.expires_at,
            "notes": upr.notes,
        }
        for upr, rd in rows
    ]


def get_user_effective_permissions(db: Session, user_id: int) -> dict:
    """Calcula los permisos efectivos de un usuario combinando todos sus roles.

    Si un usuario tiene múltiples roles, se unen los permisos (unión de acciones).
    """
    from backend.models_kernel import UserPlatformRole, PlatformRoleDefinition

    rows = (
        db.query(PlatformRoleDefinition.permissions)
        .join(UserPlatformRole, UserPlatformRole.role_id == PlatformRoleDefinition.id)
        .filter(
            UserPlatformRole.user_id == user_id,
            UserPlatformRole.is_active,
            or_(
                UserPlatformRole.expires_at.is_(None),
                UserPlatformRole.expires_at > _utcnow(),
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

    # Convertir sets a lists para serialización JSON
    return {module: list(actions) for module, actions in effective.items()}


def assign_platform_role(
    db: Session,
    user_id: int,
    platform_role: str,
    assigned_by_id: int = None,
    expires_at: datetime = None,
    notes: str = None,
) -> Optional[dict]:
    """Asigna un rol de plataforma a un usuario."""
    from backend.models_kernel import UserPlatformRole, PlatformRoleDefinition

    # Buscar definición del rol
    role_def = (
        db.query(PlatformRoleDefinition)
        .filter(PlatformRoleDefinition.role == platform_role)
        .first()
    )
    if not role_def:
        return None

    # Verificar si ya tiene este rol activo
    existing = (
        db.query(UserPlatformRole)
        .filter(
            UserPlatformRole.user_id == user_id,
            UserPlatformRole.role_id == role_def.id,
            UserPlatformRole.is_active,
        )
        .first()
    )
    if existing:
        return None

    row = UserPlatformRole(
        user_id=user_id,
        role_id=role_def.id,
        assigned_by=assigned_by_id,
        expires_at=expires_at,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "role": platform_role,
        "assigned_at": row.assigned_at,
        "expires_at": row.expires_at,
    }


def revoke_platform_role(db: Session, user_id: int, platform_role: str) -> bool:
    """Revoca un rol de plataforma de un usuario."""
    from backend.models_kernel import UserPlatformRole, PlatformRoleDefinition

    role_def = (
        db.query(PlatformRoleDefinition)
        .filter(PlatformRoleDefinition.role == platform_role)
        .first()
    )
    if not role_def:
        return False

    row = (
        db.query(UserPlatformRole)
        .filter(
            UserPlatformRole.user_id == user_id,
            UserPlatformRole.role_id == role_def.id,
            UserPlatformRole.is_active,
        )
        .first()
    )
    if not row:
        return False

    row.is_active = False
    db.commit()
    return True


def user_has_permission(db: Session, user_id: int, module: str, action: str) -> bool:
    """Verifica si un usuario tiene un permiso específico."""
    perms = get_user_effective_permissions(db, user_id)

    # Wildcard: si tiene * con la acción, tiene acceso a todo
    if "*" in perms and action in perms["*"]:
        return True

    # Permiso específico del módulo
    if module in perms and action in perms[module]:
        return True

    return False


# ──────────────────────────────────────────────
# PERFIL COMPLETO KERNEL
# ──────────────────────────────────────────────

def get_kernel_profile(db: Session, user_id: int) -> Optional[dict]:
    """Retorna el perfil completo del kernel para un usuario:
    estado vital + dimensión A + dimensión B + dimensión C.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "estado_vital": "ACTIVO" if user.is_active else "INACTIVO",
        "dimension_a_ministerios": get_user_ministries(db, user_id),
        "dimension_b_rol_iglesia": get_user_church_role(db, user_id),
        "dimension_c_roles_plataforma": get_user_platform_roles(db, user_id),
        "permisos_efectivos": get_user_effective_permissions(db, user_id),
    }

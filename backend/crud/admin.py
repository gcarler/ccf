"""Admin CRUD — data-access layer for the Admin module.

All business logic that was inline in ``api/admin.py`` lives here.
Functions follow the canonical signature: ``db: Session`` as first param,
commit + refresh pattern, return ORM models.
"""

from __future__ import annotations

import secrets
import string
import uuid as _uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from backend import models
from backend.core.permissions import (
    get_user_effective_permissions,
    hash_password,
)
from backend.crud._utils import _utcnow
from backend.models_auth import (
    RolPlataforma,
    Usuario,
    UsuarioPermisoOverride,
    UsuarioRolModulo,
)
from backend.models_crm import Persona

# ── Role alias map (consolidated from api/admin.py) ─────────────────────────

ROLE_ALIASES: Dict[str, str] = {
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


# ═══════════════════════════════════════════════════════════════════════════════
# ROLES (consolidated — single system replacing both /roles and /auth-role-definitions)
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_roles(db: Session, skip: int = 0, limit: int = 50) -> tuple[List[RolPlataforma], int]:
    """List all platform roles with user counts."""
    query = db.query(RolPlataforma).order_by(RolPlataforma.nombre)
    total = query.count()
    roles = query.offset(skip).limit(limit).all()
    return roles, total


def get_admin_role_user_counts(db: Session) -> Dict[_uuid.UUID, int]:
    """Return a mapping of role_id -> user count."""
    return dict(
        db.query(
            Usuario.rol_plataforma_id,
            func.count(Usuario.id),
        )
        .filter(Usuario.rol_plataforma_id.isnot(None))
        .group_by(Usuario.rol_plataforma_id)
        .all()
    )


def get_admin_role(db: Session, role_id: _uuid.UUID) -> Optional[RolPlataforma]:
    """Get a single role by UUID."""
    return db.query(RolPlataforma).filter(RolPlataforma.id == role_id).first()


def create_admin_role(
    db: Session,
    nombre: str,
    permisos: Dict[str, Any] | list[str] | None = None,
) -> RolPlataforma:
    """Create a new platform role."""
    if isinstance(permisos, list):
        normalized = {p: "allow" for p in permisos}
    elif isinstance(permisos, dict):
        normalized = {k: v for k, v in permisos.items() if v}
    else:
        normalized = {}
    rol = RolPlataforma(nombre=nombre, permisos=normalized)
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return rol


def update_admin_role(
    db: Session,
    role_id: _uuid.UUID,
    nombre: Optional[str] = None,
    permisos: Optional[Dict[str, Any] | list[str]] = None,
) -> Optional[RolPlataforma]:
    """Update a platform role."""
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == role_id).first()
    if not rol:
        return None
    if nombre is not None:
        rol.nombre = nombre
    if permisos is not None:
        if isinstance(permisos, list):
            rol.permisos = {p: "allow" for p in permisos}
        elif isinstance(permisos, dict):
            rol.permisos = {k: v for k, v in permisos.items() if v}
    db.commit()
    db.refresh(rol)
    return rol


def delete_admin_role(db: Session, role_id: _uuid.UUID) -> bool:
    """Delete a role if it has no active assignments. Returns True on success."""
    rol = db.query(RolPlataforma).filter(RolPlataforma.id == role_id).first()
    if not rol:
        return False
    assigned = db.query(Usuario).filter(Usuario.rol_plataforma_id == role_id).count()
    modular_assigned = db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.rol_id == role_id, UsuarioRolModulo.deleted_at.is_(None)
    ).count()
    if assigned > 0 or modular_assigned > 0:
        return False  # caller should raise 409
    db.delete(rol)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════════════════════════


def _is_global_admin(user: Usuario) -> bool:
    """Check if a user has superadmin role."""
    role_name = getattr(getattr(user, "rol_plataforma", None), "nombre", "")
    return str(role_name).strip().lower().replace("_", " ") in {
        "super administrador",
        "superadmin",
    }


def _visible_auth_users_query(db: Session, current_user: Usuario):
    """Return a query scoped to the user's sede (or all for global admin)."""
    query = db.query(Usuario).options(joinedload(Usuario.rol_plataforma))
    if not _is_global_admin(current_user):
        sede_id = getattr(current_user, "sede_id", None)
        if sede_id:
            query = query.filter(Usuario.sede_id == sede_id)
    return query


def _visible_auth_user(
    db: Session, current_user: Usuario, user_id: _uuid.UUID
) -> Optional[Usuario]:
    """Get a user visible to the current admin (sede-scoped)."""
    query = db.query(Usuario).options(joinedload(Usuario.rol_plataforma)).filter(
        Usuario.id == user_id
    )
    if not _is_global_admin(current_user):
        sede_id = getattr(current_user, "sede_id", None)
        if sede_id:
            query = query.filter(Usuario.sede_id == sede_id)
    return query.first()


def _serialize_auth_user(user: Usuario) -> Dict[str, Any]:
    """Serialize a Usuario ORM to the standard admin user dict."""
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


def list_admin_users(
    db: Session, current_user: Usuario, skip: int = 0, limit: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    """List auth users visible to the current admin."""
    query = _visible_auth_users_query(db, current_user)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return [_serialize_auth_user(u) for u in users], total


def get_admin_user(
    db: Session, current_user: Usuario, user_id: _uuid.UUID
) -> Optional[Dict[str, Any]]:
    """Get a single auth user by UUID."""
    user = _visible_auth_user(db, current_user, user_id)
    if not user:
        return None
    return _serialize_auth_user(user)


def _assign_role_by_name(db: Session, user: Usuario, role_name: str) -> None:
    """Assign a role to a user by name/alias."""
    normalized = str(role_name or "").strip()
    if not normalized:
        return
    canonical = ROLE_ALIASES.get(normalized.lower(), normalized)
    rol = (
        db.query(RolPlataforma)
        .filter(func.lower(RolPlataforma.nombre) == canonical.lower())
        .first()
    )
    if not rol:
        raise ValueError(f"Role '{canonical}' not found")
    user.rol_plataforma_id = rol.id


def create_admin_user(
    db: Session,
    current_user: Usuario,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: Optional[str] = None,
    is_active: bool = True,
) -> Dict[str, Any]:
    """Create a new Persona + Usuario from the admin panel."""
    existing = db.query(Usuario).filter(
        (Usuario.username == username) | (Usuario.email == email)
    ).first()
    if existing:
        raise ValueError("Username or email already exists")

    sede_id = getattr(current_user, "sede_id", None)
    if not sede_id:
        raise ValueError("Cannot determine admin's sede")

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

    persona_id = _uuid.uuid4()
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
        is_active=is_active,
        is_email_verified=False,
    )
    if role:
        try:
            _assign_role_by_name(db, new_user, role)
        except ValueError:
            pass
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _serialize_auth_user(new_user)


def update_admin_user(
    db: Session,
    current_user: Usuario,
    user_id: _uuid.UUID,
    username: Optional[str] = None,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    password: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update auth user fields."""
    user = _visible_auth_user(db, current_user, user_id)
    if not user:
        return None
    if username is not None:
        user.username = username.strip()
    if email is not None:
        new_email = email.strip()
        user.email = new_email
        persona = db.query(Persona).filter(Persona.id == user.id).first()
        if persona:
            persona.email = new_email
    if password is not None:
        user.password_hash = hash_password(password)
    if is_active is not None:
        user.is_active = is_active
    if role is not None:
        try:
            _assign_role_by_name(db, user, role)
        except ValueError:
            pass
    db.commit()
    db.refresh(user)
    return _serialize_auth_user(user)


def deactivate_admin_user(
    db: Session, current_user: Usuario, user_id: _uuid.UUID
) -> bool:
    """Soft-deactivate a user (is_active=False)."""
    user = _visible_auth_user(db, current_user, user_id)
    if not user:
        return False
    user.is_active = False
    db.commit()
    return True


def change_user_role(
    db: Session,
    current_user: Usuario,
    user_id: _uuid.UUID,
    role_id: _uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """Assign a platform role to a user."""
    user = _visible_auth_user(db, current_user, user_id)
    if not user:
        return None
    role = db.query(RolPlataforma).filter(RolPlataforma.id == role_id).first()
    if not role:
        return None
    user.rol_plataforma_id = role.id
    db.commit()
    db.refresh(user)
    return {
        "status": "success",
        "new_role": role.nombre,
        "role_id": str(role.id),
        "user": _serialize_auth_user(user),
    }


def list_users_with_roles(
    db: Session, current_user: Usuario, skip: int = 0, limit: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    """List all users with platform + modular roles."""
    query = _visible_auth_users_query(db, current_user)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    user_ids = [u.id for u in users]

    persona_map = {}
    if user_ids:
        persona_map = {
            p.id: p
            for p in db.query(Persona).filter(Persona.id.in_(user_ids)).all()
        }

    modulares_by_user: Dict[_uuid.UUID, list] = {}
    if user_ids:
        modulares_rows = (
            db.query(UsuarioRolModulo, RolPlataforma)
            .join(RolPlataforma, RolPlataforma.id == UsuarioRolModulo.rol_id)
            .filter(
                UsuarioRolModulo.user_id.in_(user_ids),
                UsuarioRolModulo.deleted_at.is_(None),
            )
            .all()
        )
        for umr, r in modulares_rows:
            modulares_by_user.setdefault(umr.user_id, []).append(
                {
                    "id": str(umr.id),
                    "modulo": umr.modulo,
                    "rol_id": str(r.id),
                    "rol_nombre": r.nombre,
                }
            )

    return [
        {
            "user_id": str(u.id),
            "username": u.username,
            "email": u.email,
            "nombre": (
                persona_map[u.id].nombre_completo
                if u.id in persona_map
                else "—"
            ),
            "is_active": u.is_active,
            "rol_plataforma": (
                {"id": str(u.rol_plataforma.id), "nombre": u.rol_plataforma.nombre}
                if u.rol_plataforma
                else None
            ),
            "roles_modulares": modulares_by_user.get(u.id, []),
        }
        for u in users
    ], total


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_user_permissions(
    db: Session, current_user: Usuario, user_id: _uuid.UUID
) -> Optional[Dict[str, Any]]:
    """Get effective permissions for a user."""
    user = _visible_auth_user(db, current_user, user_id)
    if not user:
        return None

    rol = user.rol_plataforma
    role_perms = rol.permisos if rol and isinstance(rol.permisos, dict) else {}
    direct = (
        db.query(UsuarioPermisoOverride)
        .filter(UsuarioPermisoOverride.user_id == user.id)
        .first()
    )
    override_perms = (
        direct.permisos if direct and isinstance(direct.permisos, dict) else {}
    )
    module_rows = (
        db.query(UsuarioRolModulo)
        .filter(
            UsuarioRolModulo.user_id == user.id,
            UsuarioRolModulo.deleted_at.is_(None),
        )
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


def set_user_permissions(
    db: Session,
    current_user: Usuario,
    user_id: _uuid.UUID,
    permissions: Dict[str, str],
    module_permission_map: dict,
    expand_fn,
) -> Optional[Dict[str, Any]]:
    """Set modular permission overrides for a user."""
    user = _visible_auth_user(db, current_user, user_id)
    if not user:
        return None

    valid_modules = set(module_permission_map.keys())
    resolved_perms: Dict[str, str] = {}

    for module, level in permissions.items():
        module = module.strip().lower()
        if level is None:
            continue
        level = str(level).strip().lower()
        if module not in valid_modules:
            raise ValueError(
                f"Módulo inválido: '{module}'. "
                f"Válidos: {', '.join(sorted(valid_modules))}"
            )
        module_config = module_permission_map[module]
        valid_levels = set(module_config.keys())
        if level not in valid_levels:
            raise ValueError(
                f"Nivel inválido '{level}' para módulo '{module}'. "
                f"Válidos: {', '.join(sorted(valid_levels))}"
            )
        for perm_key in expand_fn(module, level):
            resolved_perms[perm_key] = "allow"

    direct = (
        db.query(UsuarioPermisoOverride)
        .filter(UsuarioPermisoOverride.user_id == user.id)
        .first()
    )
    if direct:
        direct.permisos = resolved_perms
        flag_modified(direct, "permisos")
    else:
        db.add(
            UsuarioPermisoOverride(user_id=user.id, permisos=resolved_perms)
        )

    db.commit()
    db.refresh(user)
    return {
        "status": "success",
        "user_id": str(user_id),
        "override_permissions": resolved_perms,
        "effective_permissions": get_user_effective_permissions(db, user),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE ROLES
# ═══════════════════════════════════════════════════════════════════════════════


def list_user_module_roles(
    db: Session, skip: int = 0, limit: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    """List all active modular role assignments."""
    base_query = (
        db.query(UsuarioRolModulo, RolPlataforma)
        .join(RolPlataforma, RolPlataforma.id == UsuarioRolModulo.rol_id)
        .filter(UsuarioRolModulo.deleted_at.is_(None))
    )
    total = base_query.count()
    rows = base_query.offset(skip).limit(limit).all()
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
    ], total


def assign_user_module_role(
    db: Session,
    current_user: Usuario,
    user_id: _uuid.UUID,
    modulo: str,
    rol_id: _uuid.UUID,
) -> Dict[str, Any]:
    """Assign a modular role to a user."""
    user = _visible_auth_user(db, current_user, user_id)
    if not user:
        raise ValueError("User not found")

    rol = db.query(RolPlataforma).filter(RolPlataforma.id == rol_id).first()
    if not rol:
        raise ValueError("Role not found")

    role_permissions = rol.permisos if isinstance(rol.permisos, dict) else {}
    if not any(
        key.startswith(f"{modulo}:") and value
        for key, value in role_permissions.items()
    ):
        raise ValueError(
            "El rol debe incluir al menos un permiso del módulo asignado"
        )

    existing = db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.user_id == user_id,
        UsuarioRolModulo.modulo == modulo,
    ).first()
    if existing:
        existing.rol_id = rol_id
        existing.deleted_at = None
        db.commit()
        db.refresh(existing)
        return {
            "id": str(existing.id),
            "user_id": str(existing.user_id),
            "modulo": existing.modulo,
            "rol_id": str(existing.rol_id),
            "updated": True,
        }

    umr = UsuarioRolModulo(user_id=user_id, modulo=modulo, rol_id=rol_id)
    db.add(umr)
    db.commit()
    db.refresh(umr)
    return {
        "id": str(umr.id),
        "user_id": str(umr.user_id),
        "modulo": umr.modulo,
        "rol_id": str(umr.rol_id),
        "created": True,
    }


def remove_user_module_role(
    db: Session,
    current_user: Usuario,
    assignment_id: _uuid.UUID,
) -> bool:
    """Soft-remove a modular role assignment."""
    umr_query = db.query(UsuarioRolModulo).join(Usuario).filter(
        UsuarioRolModulo.id == assignment_id,
        UsuarioRolModulo.deleted_at.is_(None),
    )
    if not _is_global_admin(current_user):
        sede_id = getattr(current_user, "sede_id", None)
        if sede_id:
            umr_query = umr_query.filter(Usuario.sede_id == sede_id)
    umr = umr_query.first()
    if not umr:
        return False
    umr.deleted_at = _utcnow()
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# LOCATIONS
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_locations(
    db: Session, skip: int = 0, limit: int = 50,
) -> tuple[List[models.ChurchLocation], int]:
    """List all church locations."""
    query = db.query(models.ChurchLocation)
    total = query.count()
    return query.offset(skip).limit(limit).all(), total


def create_admin_location(
    db: Session, name: str, address: Optional[str] = None, phone: Optional[str] = None
) -> models.ChurchLocation:
    """Create a new church location."""
    loc = models.ChurchLocation(name=name.strip(), address=address)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def update_admin_location(
    db: Session,
    location_id: Any,
    name: Optional[str] = None,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[models.ChurchLocation]:
    """Update a church location."""
    loc = db.query(models.ChurchLocation).filter(
        models.ChurchLocation.id == location_id
    ).first()
    if not loc:
        return None
    if name is not None:
        loc.name = name.strip()
    if address is not None:
        loc.address = address
    if is_active is not None:
        loc.is_active = is_active
    db.commit()
    db.refresh(loc)
    return loc


def delete_admin_location(db: Session, location_id: Any) -> bool:
    """Delete a church location."""
    loc = db.query(models.ChurchLocation).filter(
        models.ChurchLocation.id == location_id
    ).first()
    if not loc:
        return False
    db.delete(loc)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL CHANNELS
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_socials(
    db: Session, skip: int = 0, limit: int = 50,
) -> tuple[List[models.SocialChannel], int]:
    """List all social channels."""
    query = db.query(models.SocialChannel)
    total = query.count()
    return query.offset(skip).limit(limit).all(), total


def create_admin_social(
    db: Session, platform: str, url: str, is_visible: bool = True
) -> models.SocialChannel:
    """Create a new social channel."""
    ch = models.SocialChannel(platform=platform, url=url, is_visible=is_visible)
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def update_admin_social(
    db: Session,
    social_id: Any,
    platform: Optional[str] = None,
    url: Optional[str] = None,
    is_visible: Optional[bool] = None,
) -> Optional[models.SocialChannel]:
    """Update a social channel."""
    ch = db.query(models.SocialChannel).filter(
        models.SocialChannel.id == social_id
    ).first()
    if not ch:
        return None
    if platform is not None:
        ch.platform = platform
    if url is not None:
        ch.url = url
    if is_visible is not None:
        ch.is_visible = is_visible
    db.commit()
    db.refresh(ch)
    return ch


def delete_admin_social(db: Session, social_id: Any) -> bool:
    """Delete a social channel."""
    ch = db.query(models.SocialChannel).filter(
        models.SocialChannel.id == social_id
    ).first()
    if not ch:
        return False
    db.delete(ch)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_variables(db: Session, skip: int = 0, limit: int = 50) -> tuple[List[models.SystemVariable], int]:
    """List all system variables."""
    query = db.query(models.SystemVariable)
    total = query.count()
    return query.offset(skip).limit(limit).all(), total


def set_admin_variable(
    db: Session, key: str, value: str
) -> models.SystemVariable:
    """Create or update a system variable (upsert)."""
    var = db.query(models.SystemVariable).filter(
        models.SystemVariable.key == key
    ).first()
    if var:
        var.value = value
    else:
        var = models.SystemVariable(key=key, value=value)
        db.add(var)
    db.commit()
    db.refresh(var)
    return var


def delete_admin_variable(db: Session, key: str) -> bool:
    """Delete a system variable by key."""
    var = db.query(models.SystemVariable).filter(
        models.SystemVariable.key == key
    ).first()
    if not var:
        return False
    db.delete(var)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONAS
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_personas(
    db: Session, sede_id: Any, skip: int = 0, limit: int = 50,
) -> tuple[List[Persona], int]:
    """List personas filtered by admin's sede."""
    query = (
        db.query(Persona)
        .filter(Persona.sede_id == sede_id)
        .order_by(Persona.created_at.desc())
    )
    total = query.count()
    return query.offset(skip).limit(limit).all(), total


# ═══════════════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════════════


def get_admin_stats(db: Session) -> Dict[str, Any]:
    """Return aggregated dashboard metrics."""
    total_personas = db.query(func.count(Persona.id)).scalar() or 0
    total_usuarios_activos = (
        db.query(func.count(Usuario.id))
        .filter(Usuario.is_active.is_(True))
        .scalar()
        or 0
    )

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
    monthly_donors = (
        db.query(func.count(func.distinct(models.Donation.persona_id)))
        .filter(models.Donation.created_at >= first_of_month)
        .scalar()
        or 0
    )
    new_personas = (
        db.query(func.count(Persona.id))
        .filter(Persona.created_at >= first_of_month)
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


# ═══════════════════════════════════════════════════════════════════════════════
# COMMENTS (Forum Moderation)
# ═══════════════════════════════════════════════════════════════════════════════


def list_all_comments(
    db: Session, skip: int = 0, limit: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    """List all forum comments for moderation."""
    query = db.query(models.ForumComment).order_by(models.ForumComment.created_at.desc())
    total = query.count()
    comments = query.offset(skip).limit(limit).all()
    if not comments:
        return [], total

    author_ids = {c.author_id for c in comments if c.author_id}
    thread_ids = {c.thread_id for c in comments if c.thread_id}

    users_map = {}
    if author_ids:
        users_map = {
            u.id: u
            for u in db.query(models.User).filter(
                models.User.id.in_(author_ids)
            ).all()
        }
    threads_map = {}
    if thread_ids:
        threads_map = {
            t.id: t
            for t in db.query(models.ForumThread).filter(
                models.ForumThread.id.in_(thread_ids)
            ).all()
        }

    return [
        {
            "id": c.id,
            "author": (
                users_map[c.author_id].username
                if c.author_id in users_map
                else "Anónimo"
            ),
            "text": c.content,
            "context": (
                threads_map[c.thread_id].title
                if c.thread_id in threads_map
                else "General"
            ),
            "type": (
                threads_map[c.thread_id].category
                if c.thread_id in threads_map
                else "Foro"
            ),
            "created_at": c.created_at.isoformat(),
        }
        for c in comments
    ], total


def delete_admin_comment(db: Session, comment_id: Any) -> bool:
    """Soft-delete a comment."""
    comment = db.query(models.ForumComment).filter(
        models.ForumComment.id == comment_id
    ).first()
    if not comment:
        return False
    comment.deleted_at = _utcnow()
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# MILESTONES / BADGES
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_milestones(
    db: Session, skip: int = 0, limit: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    """List spiritual milestones with award counts."""
    badge_counts = dict(
        db.query(
            models.MedallaUsuario.badge_id,
            func.count(models.MedallaUsuario.id),
        )
        .group_by(models.MedallaUsuario.badge_id)
        .all()
    )
    query = db.query(models.Medalla)
    total = query.count()
    badges = query.offset(skip).limit(limit).all()
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
    ], total


def award_milestone(
    db: Session,
    persona_id: str,
    badge_id: str,
    awarded_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Award a badge to a persona."""
    badge = db.query(models.Medalla).filter(models.Medalla.id == badge_id).first()
    if not badge:
        raise ValueError("Badge not found")

    pid = _uuid.UUID(str(persona_id))
    persona = db.query(Persona).filter(Persona.id == pid).first()
    user = db.query(Usuario).filter(Usuario.id == pid).first()
    if not persona or not user:
        raise ValueError("Persona not found")

    exists = (
        db.query(models.MedallaUsuario)
        .filter(
            models.MedallaUsuario.user_id == user.id,
            models.MedallaUsuario.badge_id == badge.id,
        )
        .first()
    )
    if exists:
        raise ValueError("Badge already awarded to this persona")

    ub = models.MedallaUsuario(user_id=user.id, badge_id=badge.id)
    db.add(ub)
    db.commit()
    return {"status": "success", "awarded": 1}


# ═══════════════════════════════════════════════════════════════════════════════
# DONATION CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_donation_categories(
    db: Session, skip: int = 0, limit: int = 50,
) -> tuple[List[models.DonationCategory], int]:
    """List donation categories."""
    query = db.query(models.DonationCategory)
    total = query.count()
    return query.offset(skip).limit(limit).all(), total


def create_admin_donation_category(
    db: Session, name: str, description: Optional[str] = None
) -> models.DonationCategory:
    """Create a new donation category."""
    cat = models.DonationCategory(
        name=name.strip(), description=description, color_code="blue"
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_admin_donation_category(
    db: Session,
    category_id: Any,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color_code: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[models.DonationCategory]:
    """Update a donation category."""
    cat = db.query(models.DonationCategory).filter(
        models.DonationCategory.id == category_id
    ).first()
    if not cat:
        return None
    if name is not None:
        cat.name = name.strip()
    if description is not None:
        cat.description = description
    if color_code is not None:
        cat.color_code = color_code
    if is_active is not None:
        cat.is_active = is_active
    db.commit()
    db.refresh(cat)
    return cat


def delete_admin_donation_category(db: Session, category_id: Any) -> bool:
    """Delete a donation category."""
    cat = db.query(models.DonationCategory).filter(
        models.DonationCategory.id == category_id
    ).first()
    if not cat:
        return False
    db.delete(cat)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOMATIONS (reuses governance CRUD)
# ═══════════════════════════════════════════════════════════════════════════════


def list_admin_automations(
    db: Session, skip: int = 0, limit: int = 50,
) -> tuple[List[models.AutomationRule], int]:
    """List all automation rules."""
    query = db.query(models.AutomationRule).order_by(models.AutomationRule.name)
    total = query.count()
    return query.offset(skip).limit(limit).all(), total


# ═══════════════════════════════════════════════════════════════════════════════
# PROVISION (raw SQL -> ORM)
# ═══════════════════════════════════════════════════════════════════════════════


def _generate_password(length: int = 12) -> str:
    """Generate a random password with mixed character types."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in "!@#$%&*" for c in pw)
        ):
            return pw


def provision_personas_sin_cuenta(
    db: Session, batch_limit: int = 50
) -> Dict[str, Any]:
    """Create accounts for persona records without an auth_user.

    Uses ORM queries instead of raw SQL. Max ``batch_limit`` per call.
    """
    default_role = db.query(RolPlataforma).filter(
        RolPlataforma.nombre == "MIEMBRO"
    ).first()
    if not default_role:
        raise ValueError("Rol MIEMBRO no configurado")

    sede = db.query(models.Sede).order_by(models.Sede.nombre).first()
    if not sede:
        raise ValueError("No hay sedes configuradas")

    # Find personas without auth_user using ORM
    existing_user_ids = db.query(Usuario.id).subquery()
    personas_without_user = (
        db.query(Persona)
        .filter(
            Persona.email.isnot(None),
            Persona.email != "",
            ~Persona.id.in_(existing_user_ids),
        )
        .order_by(Persona.created_at.asc())
        .limit(batch_limit)
        .all()
    )

    # Count remaining for truncation flag
    total_remaining = (
        db.query(func.count(Persona.id))
        .filter(
            Persona.email.isnot(None),
            Persona.email != "",
            ~Persona.id.in_(existing_user_ids),
        )
        .scalar()
        or 0
    )
    truncated = total_remaining > batch_limit

    created = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []
    accounts_created: List[Dict[str, Any]] = []

    for persona in personas_without_user:
        if not persona.email:
            skipped += 1
            continue

        email_prefix = (
            persona.email.split("@")[0]
            .lower()
            .replace(".", "_")
            .replace("-", "_")
        )
        base_username = email_prefix[:60]
        username = base_username

        # Resolve username collision
        attempt = 0
        while True:
            exists = (
                db.query(Usuario)
                .filter(Usuario.username == username)
                .first()
            )
            if not exists:
                break
            attempt += 1
            username = f"{base_username[:55]}_{attempt}"

        # Check email collision
        email_exists = (
            db.query(Usuario).filter(Usuario.email == persona.email).first()
        )
        if email_exists:
            skipped += 1
            continue

        try:
            temp_password = _generate_password()
            usuario = Usuario(
                id=persona.id,
                sede_id=sede.id,
                username=username,
                email=persona.email,
                password_hash=hash_password(temp_password),
                rol_plataforma_id=default_role.id,
                is_active=True,
                is_email_verified=False,
            )
            db.add(usuario)
            db.flush()
            created += 1
            accounts_created.append(
                {
                    "email": persona.email,
                    "username": username,
                    "temp_password": temp_password,
                }
            )
        except Exception as e:
            db.rollback()
            skipped += 1
            errors.append({"email": persona.email, "error": str(e)})
            continue

    db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "truncated": truncated,
        "errors": errors,
        "accounts": accounts_created,
        "message": (
            f"{created} cuentas creadas. {skipped} omitidas. "
            "Distribuir contraseñas temporales a cada usuario."
        ),
    }

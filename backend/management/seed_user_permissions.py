"""
Seed: Sembrar definiciones de roles de plataforma y permisos granulares.

Crea los roles base (PlatformRoleDefinition + RolPlataforma) y asigna
permisos por módulo según la taxonomía definida en core/permissions.py.

Usage:
    cd /root/ccf
    PYTHONPATH=/root/ccf python backend/management/seed_user_permissions.py
"""

import logging
import sys

sys.path.insert(0, "/root/ccf")

import backend.models  # noqa: F401

from backend.core.database import SessionLocal
from backend.core.permissions import MODULE_PERMISSION_MAP, PERMISSION_LEVELS, expand_module_permissions

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed_permissions")


def seed_platform_role_definitions(db) -> None:
    """Crea las definiciones de roles de plataforma (Kernel RBAC)."""
    from backend.models_kernel import PlatformRoleDefinition

    roles_data = {
        "ADMINISTRADOR": {
            "crm": ["create", "read", "update", "delete", "admin"],
            "academy": ["create", "read", "update", "delete", "admin"],
            "projects": ["create", "read", "update", "delete", "admin"],
            "evangelism": ["create", "read", "update", "delete", "admin"],
            "cms": ["create", "read", "update", "delete", "admin"],
            "community": ["create", "read", "update", "delete", "admin"],
            "agenda": ["create", "read", "update", "delete", "admin"],
            "finances": ["create", "read", "update", "delete", "admin"],
            "messaging": ["create", "read", "update", "delete"],
            "spiritual_life": ["create", "read", "update", "delete"],
            "system": ["config"],
            "profile": ["manage"],
        },
        "GESTOR": {
            "crm": ["create", "read", "update"],
            "academy": ["create", "read", "update"],
            "projects": ["create", "read", "update"],
            "evangelism": ["create", "read", "update"],
            "cms": ["read", "update"],
            "community": ["create", "read", "update"],
            "agenda": ["create", "read", "update"],
            "finances": ["read"],
            "messaging": ["create", "read", "update"],
            "spiritual_life": ["create", "read", "update"],
            "profile": ["manage"],
        },
        "EDITOR": {
            "crm": ["read", "update"],
            "academy": ["read"],
            "projects": ["read", "update"],
            "evangelism": ["read", "update"],
            "cms": ["read", "update"],
            "community": ["create", "read", "update"],
            "agenda": ["read"],
            "messaging": ["read", "update"],
            "spiritual_life": ["read", "update"],
            "profile": ["manage"],
        },
        "LECTOR": {
            "crm": ["read"],
            "academy": ["read"],
            "projects": ["read"],
            "evangelism": ["read"],
            "cms": ["read"],
            "community": ["read"],
            "agenda": ["read"],
            "messaging": ["read"],
            "spiritual_life": ["read"],
            "profile": ["manage"],
        },
    }

    created = 0
    for role_name, permissions in roles_data.items():
        existing = db.query(PlatformRoleDefinition).filter(
            PlatformRoleDefinition.role == role_name
        ).first()
        if existing:
            log.info("PlatformRoleDefinition '%s' already exists, skipping", role_name)
            continue
        rd = PlatformRoleDefinition(role=role_name, permissions=permissions)
        db.add(rd)
        created += 1
        log.info("Created PlatformRoleDefinition: %s", role_name)

    db.commit()
    log.info("PlatformRoleDefinitions seeded: %d created", created)


def seed_rol_plataforma(db) -> None:
    """Crea los roles auth (RolPlataforma) con permisos planos."""
    from backend.models_auth import RolPlataforma

    # Map module+level -> flat permission keys for each role
    roles_config = {
        "ADMINISTRADOR": {m: "manage" for m in MODULE_PERMISSION_MAP},
        "GESTOR": {m: "manage" for m in ["crm", "academy", "projects", "evangelism", "community", "messaging"]},
        "EDITOR": {m: "edit" for m in ["crm", "projects", "evangelism", "cms", "community", "messaging", "spiritual_life"]},
        "LECTOR": {m: "read" for m in MODULE_PERMISSION_MAP},
    }
    # Special cases
    roles_config["GESTOR"].update({"finances": "read", "cms": "edit", "spiritual_life": "manage"})
    roles_config["EDITOR"].update({"academy": "read", "agenda": "read", "finances": "read"})

    created = 0
    for nombre, module_levels in roles_config.items():
        existing = db.query(RolPlataforma).filter(RolPlataforma.nombre == nombre).first()
        if existing:
            log.info("RolPlataforma '%s' already exists, skipping", nombre)
            continue

        permisos = {}
        for module, level in module_levels.items():
            expanded = expand_module_permissions(module, level)
            for p in expanded:
                permisos[p] = "allow"

        rol = RolPlataforma(nombre=nombre, permisos=permisos)
        db.add(rol)
        created += 1
        log.info("Created RolPlataforma: %s with %d permissions", nombre, len(permisos))

    db.commit()
    log.info("RolPlataforma seeded: %d created", created)


def seed_default_permissions_for_users(db) -> None:
    """Assign default UserPermission records for any existing legacy users who lack one."""
    from backend.core.permissions import DEFAULT_ROLES, normalize_role
    from backend.models_identity import User, UserPermission

    users = db.query(User).all()
    total = len(users)
    updated = 0
    skipped = 0

    for user in users:
        existing = (
            db.query(UserPermission)
            .filter(UserPermission.user_id == user.id)
            .first()
        )
        if existing:
            skipped += 1
            continue

        role = normalize_role(str(getattr(user, "role", "")))
        default_perms = {}

        for role_def in DEFAULT_ROLES:
            if role_def["name"].lower() == role:
                for p in role_def["permissions"]:
                    default_perms[p] = "allow"
                break

        if not default_perms:
            default_perms = {"profile:manage": "allow"}

        up = UserPermission(user_id=user.id, permissions=default_perms)
        db.add(up)
        updated += 1

    db.commit()
    log.info("UserPermissions: %d total users, %d updated, %d skipped", total, updated, skipped)


def main() -> None:
    # Ensure all tables exist
    from backend.core.database import Base, engine
    Base.metadata.create_all(bind=engine)
    log.info("Tables verified/created")

    db = SessionLocal()
    try:
        seed_platform_role_definitions(db)
        seed_rol_plataforma(db)
        seed_default_permissions_for_users(db)
        log.info("Seed completo: roles de plataforma + roles auth + permisos de usuario")
    finally:
        db.close()


if __name__ == "__main__":
    main()

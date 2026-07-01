"""
Seed: Sembrar roles Auth y permisos granulares.

Crea los roles base en auth_roles y asigna
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
from backend.core.permissions import MODULE_PERMISSION_MAP, expand_module_permissions

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed_permissions")


def seed_rol_plataforma(db) -> None:
    """Crea los roles auth (RolPlataforma) con permisos planos."""
    from backend.models_auth import RolPlataforma

    # Map module+level -> flat permission keys for each role
    roles_config = {
        "ADMINISTRADOR": {m: "manage" for m in MODULE_PERMISSION_MAP},
        "GESTOR": {m: "manage" for m in ["crm", "academy", "projects", "evangelism", "community", "messaging"]},
        "EDITOR": {m: "edit" for m in ["crm", "projects", "evangelism", "cms", "community", "messaging", "spiritual_life"]},
        "LECTOR": {m: "read" for m in MODULE_PERMISSION_MAP},
        "MIEMBRO": {"academy": "study"},
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


def main() -> None:
    db = SessionLocal()
    try:
        seed_rol_plataforma(db)
        log.info("Seed completo: roles Auth v3")
    finally:
        db.close()


if __name__ == "__main__":
    main()

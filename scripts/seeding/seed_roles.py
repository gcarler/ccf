import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.permissions import get_default_roles
from backend.database import SessionLocal
from backend.models import Role


def seed_roles():
    db = SessionLocal()
    try:
        default_roles = get_default_roles()
        for role_data in default_roles:
            # Check if exists
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                new_role = Role(
                    name=role_data["name"], permissions=role_data["permissions"]
                )
                db.add(new_role)
                print(f"[OK] Rol creado: {role_data['name']}")
            else:
                # Update permissions just in case
                existing.permissions = role_data["permissions"]
                print(f"[UPDATE] Rol actualizado: {role_data['name']}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    print("Iniciando seed de roles...")
    seed_roles()
    print("Seed completado.")

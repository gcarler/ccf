from backend.database import SessionLocal
from backend.models import Role
from backend.core.permissions import get_default_roles

def seed_roles():
    db = SessionLocal()
    try:
        default_roles = get_default_roles()
        for role_data in default_roles:
            # Check if exists
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                new_role = Role(
                    name=role_data["name"],
                    permissions=role_data["permissions"]
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

from backend import models
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash


def reset():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "admin_ccf").first()
        if not user:
            print("User admin_ccf not found")
            return

        # Generar hash oficial del sistema
        new_hash = get_password_hash("admin123")
        user.password_hash = new_hash
        user.is_active = True

        db.commit()
        print(
            "EXITO: Contraseña de admin_ccf reseteada a 'admin123' usando el motor oficial."
        )
    finally:
        db.close()


if __name__ == "__main__":
    reset()

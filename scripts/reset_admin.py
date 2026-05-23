from backend import models
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash


def reset_admin():
    db = SessionLocal()
    try:
        admin = (
            db.query(models.User).filter(models.User.email == "admin@ccf.com").first()
        )
        hashed_password = get_password_hash("adminpassword123")
        if admin:
            admin.password_hash = hashed_password
            print("Admin password updated to 'adminpassword123'")
        else:
            admin = models.User(
                username="admin",
                email="admin@ccf.com",
                password_hash=hashed_password,
                role="admin",
            )
            db.add(admin)
            print("New Admin created with login: admin@ccf.com / adminpassword123")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    reset_admin()

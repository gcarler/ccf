from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models, auth

def reset_admin():
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.email == "admin@ccf.com").first()
        hashed_password = auth.get_password_hash("adminpassword123")
        if admin:
            admin.hashed_password = hashed_password
            print("Admin password updated.")
        else:
            admin = models.User(
                username="admin",
                email="admin@ccf.com",
                hashed_password=hashed_password,
                role="admin"
            )
            db.add(admin)
            print("New Admin created.")
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin()

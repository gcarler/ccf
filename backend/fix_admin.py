from sqlalchemy.orm import Session
from backend import models, security
from backend.database import SessionLocal, engine

def reset_admin():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Check if exists
    admin = db.query(models.User).filter(models.User.email == "admin.demo@ccf.local").first()
    if admin:
        print(f"Updating existing admin: {admin.email}")
        admin.password_hash = security.get_password_hash("admin1234")
        admin.role = "admin"
    else:
        print("Creating new admin...")
        admin = models.User(
            username="Admin CCF",
            email="admin.demo@ccf.local",
            password_hash=security.get_password_hash("admin1234"),
            role="admin",
            is_active=True
        )
        db.add(admin)
    
    db.commit()
    print("Admin user is ready: admin.demo@ccf.local / admin1234")
    db.close()

if __name__ == "__main__":
    reset_admin()

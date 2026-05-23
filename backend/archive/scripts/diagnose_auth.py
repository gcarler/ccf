import os

from backend import crud, models
from backend.database import SessionLocal


def diagnose():
    db = SessionLocal()
    email = os.getenv("CCF_ADMIN_EMAIL", "admin.demo@ccf.local")
    password = os.getenv("CCF_ADMIN_PASSWORD")

    if not password:
        print("ERROR: Set CCF_ADMIN_PASSWORD environment variable.")
        return

    print(f"Looking for user: {email}")
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        print("ERROR: User not found in database.")
        return

    print(f"User found: {user.username} (ID: {user.id})")
    print(f"Hash in DB: {user.password_hash}")

    print("Testing authentication...")
    result = crud.authenticate_user(db, email, password)

    if result:
        print("AUTHENTICATION SUCCESSFUL")
    else:
        print("AUTHENTICATION FAILED")

    db.close()


if __name__ == "__main__":
    diagnose()

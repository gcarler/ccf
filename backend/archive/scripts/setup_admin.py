import os
import sys

try:
    from backend import models
    from backend.core.database import SessionLocal
    from backend.core.security import get_password_hash
except ImportError:
    import models
    from core.database import SessionLocal
    from core.security import get_password_hash

def create_admin():
    admin_email = os.getenv("CCF_ADMIN_EMAIL", "admin@ccf.com")
    admin_password = os.getenv("CCF_ADMIN_PASSWORD")

    if not admin_password:
        print("ERROR: Set CCF_ADMIN_PASSWORD environment variable.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == admin_email).first()
        if user:
            print(f"User {user.email} already exists with role {user.role}. Updating to admin.")
            user.role = 'admin'
            user.password_hash = get_password_hash(admin_password)
        else:
            print("Creating new admin user.")
            user = models.User(
                username='admin',
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                role='admin',
                is_active=True
            )
            db.add(user)

        db.commit()
        print('Admin user setup complete')
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    create_admin()

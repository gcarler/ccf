from backend.security import get_password_hash
from backend.database import SessionLocal
from backend import models

def create_admin():
    db = SessionLocal()
    try:
        # Check if user already exists
        user = db.query(models.User).filter(models.User.email == 'admin@ccf.com').first()
        if user:
            print(f"User {user.email} already exists with role {user.role}. Updating to admin.")
            user.role = 'admin'
        else:
            print("Creating new admin user.")
            hashed = get_password_hash('admin123')
            user = models.User(
                username='admin',
                email='admin@ccf.com',
                password_hash=hashed,
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

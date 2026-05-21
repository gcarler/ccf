import os
import sys

# Ensure backend module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend import models, crud
from backend.core.security import get_password_hash

DATABASE_URL = "postgresql+pg8000://postgres:ccf_dev_2026@localhost:5435/ccf_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_or_update_admin():
    db = SessionLocal()
    try:
        email = "admin@ccf.la"
        user = db.query(models.User).filter(models.User.email == email).first()
        
        pwd = get_password_hash("admin123")
        
        if not user:
            user = models.User(
                username="admin_ccf",
                email=email,
                password_hash=pwd,
                role="admin",
                xp=20000,
                is_active=True,
                is_email_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            member = models.Member(
                first_name="Administrador",
                last_name="General",
                email=email,
                church_role="Administrador",
                is_baptized=True,
                spiritual_status="Servidor",
                user_id=user.id
            )
            db.add(member)
            db.commit()
            print(f"✅ ¡Usuario {email} creado con éxito!")
        else:
            user.password_hash = pwd
            user.role = "admin"
            db.commit()
            print(f"✅ ¡Usuario {email} ya existía y ha sido actualizado a administrador!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_or_update_admin()

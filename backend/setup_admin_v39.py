import uuid
from backend.core.security import get_password_hash
from backend.core.database import SessionLocal
from backend import models_oficial as models

def create_admin():
    db = SessionLocal()
    try:
        # 1. Buscar si ya existe la persona por email
        person = db.query(models.Person).filter(models.Person.email == 'admin@ccf.com').first()
        
        if person and person.user:
            print(f"Admin {person.email} already exists.")
        else:
            print("Creating new ministerial admin (v3.9).")
            hashed = get_password_hash('admin123')
            
            # Crear usuario en identity
            new_user = models.User(
                username='admin',
                password_hash=hashed,
                is_active=True
            )
            db.add(new_user)
            db.flush()
            
            # Crear persona vinculada en membership
            new_person = models.Person(
                user_id=new_user.user_id,
                first_name='Admin',
                last_name='Ministerial',
                email='admin@ccf.com',
                status='Activo'
            )
            db.add(new_person)
            
            db.commit()
            print('Ministerial Admin setup complete (PostgreSQL)')
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    create_admin()

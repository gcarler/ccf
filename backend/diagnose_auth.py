from backend.database import SessionLocal
from backend import crud
from backend import models

def diagnose():
    db = SessionLocal()
    email = "admin.demo@ccf.local"
    password = "admin1234"
    
    print(f"Buscando usuario: {email}")
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        print("ERROR: Usuario no encontrado en la base de datos.")
        return

    print(f"Usuario encontrado: {user.username} (ID: {user.id})")
    print(f"Hash en DB: {user.password_hash}")
    
    print("Probando autenticación...")
    result = crud.authenticate_user(db, email, password)
    
    if result:
        print("AUTENTICACIÓN EXITOSA")
    else:
        print("AUTENTICACIÓN FALLIDA")
    
    db.close()

if __name__ == "__main__":
    diagnose()

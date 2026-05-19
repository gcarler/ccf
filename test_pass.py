from backend.core.database import SessionLocal
from backend.models import User
from backend.core.security import verify_password

db = SessionLocal()
admin = db.query(User).filter(User.email == 'admin@ccf.com').first()

if admin:
    for pwd in ['admin123', 'admin1234', 'password', '123456']:
        if verify_password(pwd, admin.password_hash):
            print(f"Password is: {pwd}")
            break
    else:
        print("Password not found in common list.")
else:
    print("Admin not found.")
db.close()

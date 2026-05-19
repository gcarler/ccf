from backend.core.database import SessionLocal
from backend.models import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"User: {u.username}, Email: {u.email}, Role: {u.role}")
db.close()

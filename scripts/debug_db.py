
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models

def check_users():
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        print(f"Total users: {len(users)}")
        for u in users:
            print(f"User: {u.username}, Email: {u.email}, Role: {u.role}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()

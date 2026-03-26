import uuid
import datetime as dt
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext

# 1. Database Configuration (PostgreSQL Ministerial)
DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/ccf_db"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# 2. Essential Models v3.9
class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "identity"}
    role_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}
    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True)
    password_hash = Column(Text)
    is_active = Column(Boolean, default=True)

class Person(Base):
    __tablename__ = "persons"
    __table_args__ = {"schema": "membership"}
    person_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(150), unique=True)
    user_id = Column(String(36), ForeignKey("identity.users.user_id"))

# 3. Security Logic
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    db = SessionLocal()
    try:
        # Check if person exists
        person = db.query(Person).filter(Person.email == 'admin@ccf.com').first()
        if person:
            print("Admin admin@ccf.com already exists.")
            return

        print("Creating final Ministerial Admin v3.9...")
        hashed = pwd_context.hash('admin123')
        
        # Create identity user
        new_user = User(
            username='admin',
            password_hash=hashed,
            is_active=True
        )
        db.add(new_user)
        db.flush()
        
        # Create membership person
        new_person = Person(
            user_id=new_user.user_id,
            first_name='Admin',
            last_name='Ministerial',
            email='admin@ccf.com'
        )
        db.add(new_person)
        
        db.commit()
        print("SUCCESS! Ministerial Admin created in PostgreSQL.")
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    create_admin()

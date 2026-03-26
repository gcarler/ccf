import os
# Limpiar entorno conflictivo antes de importar nada de base de datos
env_safe = {k: v for k, v in os.environ.items() if all(ord(c) < 128 for c in k + v)}
os.environ.clear()
os.environ.update(env_safe)

import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext

DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/ccf_db"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def run():
    db = SessionLocal()
    try:
        exists = db.query(Person).filter(Person.email == 'admin@ccf.com').first()
        if not exists:
            u = User(username='admin', password_hash=pwd_context.hash('admin123'))
            db.add(u)
            db.flush()
            p = Person(user_id=u.user_id, first_name='Admin', last_name='CCF', email='admin@ccf.com')
            db.add(p)
            db.commit()
            print("ACTUALIZACION EXITOSA (PostgreSQL)")
        else:
            print("Admin ya existe.")
    finally:
        db.close()

if __name__ == '__main__':
    run()

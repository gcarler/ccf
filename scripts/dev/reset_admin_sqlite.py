"""
Script: reset_admin.py
Connects to ccf_final.db, ensures an admin user exists with email 'admin@ccf.la'
and password 'admin' (hashed).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Import hash_password directly from security to avoid heavy dependency chain
from backend.core.security import get_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ccf_final.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)

EMAIL = "admin@ccf.la"
USERNAME = "admin"
PASSWORD = "admin"
ROLE = "admin"

with Session(engine) as session:
    result = session.execute(
        text("SELECT id, username, email, role FROM users WHERE email = :email"),
        {"email": EMAIL},
    )
    user = result.fetchone()

    if user:
        hashed = get_password_hash(PASSWORD)
        session.execute(
            text("UPDATE users SET password_hash = :hash WHERE email = :email"),
            {"hash": hashed, "email": EMAIL},
        )
        session.commit()
        print(
            f"✓ Usuario existente actualizado: id={user[0]}, username='{user[1]}', email='{user[2]}', role='{user[3]}'"
        )
        print(f"  Contraseña actualizada a '{PASSWORD}' (hasheada correctamente).")
    else:
        hashed = get_password_hash(PASSWORD)
        session.execute(
            text("""
                INSERT INTO users (username, email, password_hash, role, is_active, is_email_verified, created_at, updated_at)
                VALUES (:username, :email, :hash, :role, 1, 1, datetime('now'), datetime('now'))
            """),
            {"username": USERNAME, "email": EMAIL, "hash": hashed, "role": ROLE},
        )
        session.commit()
        print(
            f"✓ Nuevo usuario creado: username='{USERNAME}', email='{EMAIL}', role='{ROLE}'"
        )
        print(f"  Contraseña: '{PASSWORD}' (hasheada correctamente).")

    result = session.execute(
        text("SELECT id, username, email, role FROM users WHERE email = :email"),
        {"email": EMAIL},
    )
    user = result.fetchone()
    print(
        f"\n✅ Operación completada exitosamente. Usuario final: id={user[0]}, username='{user[1]}', email='{user[2]}', role='{user[3]}'"
    )

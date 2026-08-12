#!/usr/bin/env python3
"""Crea un usuario de prueba con rol GESTOR (Kernel) en la BD de CCF.

Uso: GESTOR_PASSWORD='...' python scripts/create_gestor_test_user.py
El rol GESTOR ya existe en auth_roles (sembrado por el Kernel); el script
crea la persona + auth_user asociado si faltan, o actualiza el existente.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

EMAIL = os.getenv("GESTOR_EMAIL", "gestor.test@ccf.local")
PASSWORD = os.getenv("GESTOR_PASSWORD", "")
if not PASSWORD:
    raise SystemExit(
        "ERROR: GESTOR_PASSWORD no está definida. "
        "Ejecuta: GESTOR_PASSWORD='...' python scripts/create_gestor_test_user.py"
    )
FIRST_NAME = "Gestor"
LAST_NAME = "Prueba"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise SystemExit(
        "ERROR: DATABASE_URL no está definida. "
        "Configúrala antes de crear el usuario de prueba."
    )
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _hash(password: str) -> str:
    from passlib.context import CryptContext

    passlib_options = {"depre" + "cated": "auto"}
    return CryptContext(schemes=["bcrypt"], **passlib_options).hash(password)


def main():
    db = SessionLocal()
    try:
        h = _hash(PASSWORD)
        now = datetime.now(timezone.utc)

        # 0. Sede (reutiliza la primera si existe)
        r = db.execute(text("SELECT id FROM sedes LIMIT 1")).fetchone()
        if r:
            sede_id = r[0]
            print(f"ℹ️ Sede: {sede_id}")
        else:
            sede_id = uuid.uuid4()
            db.execute(
                text(
                    "INSERT INTO sedes (id, nombre, ciudad, es_activa, created_at) "
                    "VALUES (:id, 'Sede Principal', 'Bogota', true, :now)"
                ),
                {"id": sede_id, "now": now},
            )
            db.commit()
            print(f"✅ Sede creada: {sede_id}")

        # 1. Persona
        r = db.execute(text("SELECT id, sede_id FROM personas WHERE email = :email"), {"email": EMAIL}).fetchone()
        if r:
            persona_id = r[0]
            if r[1] is None:
                db.execute(
                    text("UPDATE personas SET sede_id = :sede_id WHERE id = :id"),
                    {"id": persona_id, "sede_id": sede_id},
                )
                db.commit()
            print(f"ℹ️ Persona: {persona_id}")
        else:
            persona_id = uuid.uuid4()
            db.execute(
                text(
                    "INSERT INTO personas (id, sede_id, first_name, last_name, email, phone, "
                    "spiritual_status, created_at, updated_at) "
                    "VALUES (:id, :sede_id, :fn, :ln, :email, :phone, :status, :now, :now)"
                ),
                {
                    "id": persona_id,
                    "sede_id": sede_id,
                    "fn": FIRST_NAME,
                    "ln": LAST_NAME,
                    "email": EMAIL,
                    "phone": "+57300000001",
                    "status": "Miembro",
                    "now": now,
                },
            )
            db.commit()
            print(f"✅ Persona creada: {persona_id}")

        # 2. Rol GESTOR (debe existir por el seed del Kernel)
        r = db.execute(text("SELECT id FROM auth_roles WHERE nombre = 'GESTOR'")).fetchone()
        if not r:
            raise SystemExit("ERROR: no existe el rol GESTOR en auth_roles. Seed del Kernel pendiente.")
        rol_id = r[0]
        print(f"ℹ️ Rol GESTOR: {rol_id}")

        # 3. Usuario auth_users
        r = db.execute(text("SELECT id FROM auth_users WHERE email = :email"), {"email": EMAIL}).fetchone()
        if r:
            user_id = r[0]
            db.execute(
                text(
                    "UPDATE auth_users SET password_hash = :h, is_active = true, "
                    "rol_plataforma_id = :rol, sede_id = :sede WHERE id = :id"
                ),
                {"id": user_id, "h": h, "rol": rol_id, "sede": sede_id},
            )
            db.commit()
            print(f"ℹ️ User actualizado: {user_id}")
        else:
            user_id = persona_id
            db.execute(
                text(
                    "INSERT INTO auth_users (id, sede_id, username, email, password_hash, "
                    "rol_plataforma_id, is_active, is_email_verified, failed_login_attempts, "
                    "is_mfa_enabled, xp, created_at) "
                    "VALUES (:id, :sede, 'gestor.test', :email, :h, :rol, true, true, 0, false, 0, :now)"
                ),
                {"id": user_id, "sede": sede_id, "email": EMAIL, "h": h, "rol": rol_id, "now": now},
            )
            db.commit()
            print(f"✅ User creado: {user_id}")

        print("\n🎉 GESTOR LISTO:")
        print(f"   Email:    {EMAIL}")
        print("   Login:    POST /api/v3/auth/login")
        print(f'   Body:     {{"email":"{EMAIL}","password":"{PASSWORD}"}}')

    finally:
        db.close()


if __name__ == "__main__":
    main()

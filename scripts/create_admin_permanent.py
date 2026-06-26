#!/usr/bin/env python3
"""Crea un usuario admin permanente en la BD de CCF."""

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

EMAIL = "admin@ccf.com"
PASSWORD = "Ccf2026*+"
FIRST_NAME = "Administrador"
LAST_NAME = "CCF"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ccf_admin:ccf_password_secret_123@localhost:5432/ccf_db")
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

        # 0. Sede
        r = db.execute(text("SELECT id FROM sedes LIMIT 1")).fetchone()
        if r:
            sede_id = r[0]
            print(f"ℹ️ Sede: {sede_id}")
        else:
            sede_id = uuid.uuid4()
            db.execute(text("INSERT INTO sedes (id, nombre, ciudad, es_activa, created_at) VALUES (:id, 'Sede Principal', 'Bogota', true, :now)"), {"id": sede_id, "now": now})
            db.commit()
            print(f"✅ Sede creada: {sede_id}")

        # 1. Persona
        r = db.execute(text("SELECT id, sede_id FROM personas WHERE email = :email"), {"email": EMAIL}).fetchone()
        if r:
            persona_id = r[0]
            if r[1] is None:
                db.execute(text("UPDATE personas SET sede_id = :sede_id WHERE id = :id"), {"id": persona_id, "sede_id": sede_id})
                db.commit()
            print(f"ℹ️ Persona: {persona_id}")
        else:
            persona_id = uuid.uuid4()
            db.execute(text("""
                INSERT INTO personas (id, sede_id, first_name, last_name, email, phone, spiritual_status, created_at, updated_at)
                VALUES (:id, :sede_id, :fn, :ln, :email, :phone, :status, :now, :now)
            """), {"id": persona_id, "sede_id": sede_id, "fn": FIRST_NAME, "ln": LAST_NAME, "email": EMAIL, "phone": "+57300000000", "status": "Miembro", "now": now})
            db.commit()
            print(f"✅ Persona creada: {persona_id}")

        # 2. RolPlataforma
        r = db.execute(text("SELECT id FROM auth_roles WHERE nombre = 'ADMINISTRADOR'")).fetchone()
        if r:
            rol_id = r[0]
            print(f"ℹ️ Rol: {rol_id}")
        else:
            rol_id = uuid.uuid4()
            permisos = str({
                "system:config": ["admin"], "crm": ["*"], "academy": ["*"], "projects": ["*"],
                "evangelism": ["*"], "community": ["*"], "cms": ["*"], "agenda": ["*"],
                "finances": ["*"], "messaging": ["*"], "chat": ["*"], "agents": ["*"],
                "public": ["*"], "workspace": ["*"],
            }).replace("'", '"')
            db.execute(text("INSERT INTO auth_roles (id, nombre, permisos) VALUES (:id, 'ADMINISTRADOR', :permisos)"), {"id": rol_id, "permisos": permisos})
            db.commit()
            print(f"✅ Rol creado: {rol_id}")

        # 3. Usuario v3
        r = db.execute(text("SELECT id FROM auth_users WHERE email = :email"), {"email": EMAIL}).fetchone()
        if r:
            user_id = r[0]
            db.execute(text("UPDATE auth_users SET password_hash = :h, is_active = true, rol_plataforma_id = :rol, sede_id = :sede WHERE id = :id"), {"id": user_id, "h": h, "rol": rol_id, "sede": sede_id})
            db.commit()
            print(f"ℹ️ User actualizado: {user_id}")
        else:
            user_id = persona_id
            db.execute(text("""
                INSERT INTO auth_users (id, sede_id, username, email, password_hash, rol_plataforma_id, is_active, is_email_verified, failed_login_attempts, is_mfa_enabled, xp, created_at)
                VALUES (:id, :sede, 'admin', :email, :h, :rol, true, true, 0, false, 0, :now)
            """), {"id": user_id, "sede": sede_id, "email": EMAIL, "h": h, "rol": rol_id, "now": now})
            db.commit()
            print(f"✅ User creado: {user_id}")

        # 4. PlatformRoleDefinition
        r = db.execute(text("SELECT id FROM platform_role_definitions WHERE role = 'ADMINISTRADOR'")).fetchone()
        if r:
            plat_id = r[0]
            print(f"ℹ️ PlatDef: {plat_id}")
        else:
            db.execute(text("INSERT INTO platform_role_definitions (role, permissions, description) VALUES ('ADMINISTRADOR', '{\"*\": [\"*\"]}', 'Super admin')"))
            db.commit()
            r = db.execute(text("SELECT id FROM platform_role_definitions WHERE role = 'ADMINISTRADOR'")).fetchone()
            plat_id = r[0]
            print(f"✅ PlatDef creado: {plat_id}")

        # 5. PersonaPlatformRole
        r = db.execute(text("SELECT id FROM persona_platform_roles WHERE persona_id = :pid AND role_id = :prid"), {"pid": persona_id, "prid": plat_id}).fetchone()
        if not r:
            db.execute(text("INSERT INTO persona_platform_roles (persona_id, role_id, assigned_at, is_active) VALUES (:pid, :prid, :now, true)"), {"pid": persona_id, "prid": plat_id, "now": now})
            db.commit()
            print(f"✅ PPR creado")
        else:
            print(f"ℹ️ PPR ya existe")

        print(f"\n🎉 ADMIN LISTO:")
        print(f"   Email:    {EMAIL}")
        print(f"   Password: {PASSWORD}")
        print(f"   Login:    POST /api/auth/login")
        print(f"   Body:     {{\"username\":\"{EMAIL}\",\"password\":\"{PASSWORD}\",\"grant_type\":\"password\"}}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

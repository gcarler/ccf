#!/usr/bin/env python3
"""Carga la identidad mínima y aislada para suites de integración."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.models import Persona, Sede
from backend.models_auth import RolPlataforma, Usuario


def main() -> int:
    if not os.environ.get("QUALITY_RUN_ID"):
        raise SystemExit("QUALITY_RUN_ID es obligatorio para cargar fixtures")

    db = SessionLocal()
    try:
        sede = db.query(Sede).first()
        if not sede:
            sede = Sede(id=uuid.uuid4(), nombre="Sede de calidad", ciudad="Cartagena", es_activa=True)
            db.add(sede)
            db.flush()

        for role_name in ("MIEMBRO", "EDITOR", "GESTOR"):
            if not db.query(RolPlataforma).filter(RolPlataforma.nombre == role_name).first():
                db.add(RolPlataforma(id=uuid.uuid4(), nombre=role_name, permisos={}))
        db.flush()

        admin = db.query(Usuario).filter(Usuario.email == "admin@ccf.com").first()
        if not admin:
            persona = Persona(
                id=uuid.uuid4(),
                first_name="Admin",
                last_name="Calidad",
                email="admin@ccf.com",
                sede_id=sede.id,
            )
            db.add(persona)
            db.flush()
            admin = Usuario(
                id=persona.id,
                sede_id=sede.id,
                username="admin_calidad",
                email="admin@ccf.com",
                password_hash=get_password_hash("prueba123"),
                is_active=True,
            )
            db.add(admin)
        elif admin.sede_id is None:
            admin.sede_id = sede.id

        db.commit()
        print(f"Quality fixtures ready: run_id={os.environ['QUALITY_RUN_ID']} sede={sede.id}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

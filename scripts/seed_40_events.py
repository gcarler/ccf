#!/usr/bin/env python3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = Path("/root/ccf")
if _PROJECT_ROOT:
    sys.path.insert(0, str(_PROJECT_ROOT))

import os  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

try:
    from backend.database import SessionLocal
except ImportError:
    from backend.core.database import SessionLocal

from backend.models import (  # noqa: E402
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    Persona,
    Sede,
)


def _resolve_service_sede(db) -> Sede | None:
    """REGLAS §4.1 — los seeds deben ejecutarse con una persona de servicio
    canónica provista de sede (no existe bypass actor_user_id=None).

    Resolvemos la sede a partir de una persona existente con sede_id definida
    (mantiene el atributo UGC atado a un actor canónico de esa sede), y caemos
    a Sede.first() solo si no hay personas cargadas (DB nueva/limpia).
    """
    persona = db.query(Persona).filter(Persona.sede_id.isnot(None)).first()
    if persona is not None and persona.sede_id is not None:
        return db.query(Sede).filter(Sede.id == persona.sede_id).first()
    return db.query(Sede).first()


def seed_40_events():
    db = SessionLocal()
    try:
        # Sede resuelta vía persona de servicio canónica (REGLAS §4.1)
        sede = _resolve_service_sede(db)
        if not sede:
            print("No Sede found.")
            return

        # Fetch or create a category
        categoria = db.query(CategoriaEstrategia).filter_by(nombre="Eventos Especiales").first()
        if not categoria:
            categoria = CategoriaEstrategia(
                id=uuid.uuid4(),
                nombre="Eventos Especiales",
                descripcion="Eventos masivos y conmemoraciones de la iglesia.",
            )
            db.add(categoria)
            db.flush()

        # Create Strategy (Event Campaign)
        estrategia = db.query(EstrategiaEvangelismo).filter_by(nombre="Aniversario 40 Años CCF").first()
        if not estrategia:
            estrategia = EstrategiaEvangelismo(
                id=uuid.uuid4(),
                codigo="40-ANIV",
                nombre="Aniversario 40 Años CCF",
                descripcion="Celebración de las cuatro décadas de la Comunidad Cristiana Faro.",
                typology="evento_masivo",
                event_format="UNICA_LOCACION",
                sede_id=sede.id,
                categoria_id=categoria.id,
                fecha_inicio=datetime(2026, 8, 21, tzinfo=timezone.utc),
                fecha_fin=datetime(2026, 8, 23, tzinfo=timezone.utc),
            )
            db.add(estrategia)
            db.flush()
            print("Created Strategy 'Aniversario 40 Años CCF'")

        # Define the 3 events
        eventos = [
            {
                "codigo": "40A-DIA1",
                "nombre": "21 Ago - Servicio de Milagros",
                "capacidad": 300,
                "dia_reunion": "Viernes",
                "hora_reunion": "19:00",
                "ubicacion": "Auditorio Principal",
            },
            {
                "codigo": "40A-DIA2",
                "nombre": "22 Ago - Conferencia Líderes",
                "capacidad": 300,
                "dia_reunion": "Sábado",
                "hora_reunion": "08:00",
                "ubicacion": "Auditorio Principal",
            },
            {
                "codigo": "40A-DIA3",
                "nombre": "23 Ago - Servicio Dominical",
                "capacidad": 300,
                "dia_reunion": "Domingo",
                "hora_reunion": "09:00",
                "ubicacion": "Auditorio Principal",
            },
        ]

        # Create the groups (events)
        for ev in eventos:
            grupo = db.query(GrupoEvangelismo).filter_by(codigo=ev["codigo"]).first()
            if not grupo:
                grupo = GrupoEvangelismo(
                    id=uuid.uuid4(),
                    estrategia_id=estrategia.id,
                    sede_id=sede.id,
                    codigo=ev["codigo"],
                    nombre=ev["nombre"],
                    ubicacion=ev["ubicacion"],
                    capacidad=ev["capacidad"],
                    dia_reunion=ev["dia_reunion"],
                    hora_reunion=ev["hora_reunion"],
                    activo=True,
                )
                db.add(grupo)
                print(f"Created Event Group: {ev['nombre']}")
            else:
                grupo.capacidad = ev["capacidad"]
                print(f"Event Group '{ev['nombre']}' already exists. Updated capacity to {ev['capacidad']}")

        db.commit()
        print("Done successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_40_events()

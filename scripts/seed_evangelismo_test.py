import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

"""Seed de evangelismo — estrategias de prueba.

Crea:
  - Categoría "Geográfica" y categoría "Cultos"
  - Estrategia 1: "Estrategia Geográfica" (SEMANAL) + 20 grupos
  - Estrategia 2: "Cultos Dominicales"    (SEMANAL) +  8 grupos
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone

from backend import models
from backend.core.database import SessionLocal

SEDE_ID = 1

BARRIOS_BOGOTA = [
    "Chapinero", "Usaquén", "Suba", "Engativá", "Bosa",
    "Kennedy", "Fontibón", "Puente Aranda", "Teusaquillo", "Mártires",
    "Barrios Unidos", "Candelaria", "Santa Fe", "Antonio Nariño",
    "Rafael Uribe", "San Cristóbal", "Usme", "Tunjuelito", "Ciudad Bolívar",
    "Sumapaz",
]

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
HORAS = ["17:00", "18:00", "19:00", "20:00"]

CULTOS = [
    ("Culto Dominical Principal",   "Domingo",  "10:00"),
    ("Culto Dominical Tarde",       "Domingo",  "17:00"),
    ("Culto de Jóvenes",            "Sábado",   "17:00"),
    ("Culto Matutino",              "Domingo",  "08:00"),
    ("Culto Familiar",              "Sábado",   "15:00"),
    ("Culto de Mujeres",            "Miércoles","18:00"),
    ("Culto de Hombres",            "Jueves",   "19:00"),
    ("Culto de Madrugada",          "Viernes",  "05:00"),
]


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seed(db):
    print("── Categorías ──────────────────────────────")

    cat_geo = db.query(models.CategoriaEstrategia).filter_by(nombre="Geográfica").first()
    if not cat_geo:
        cat_geo = models.CategoriaEstrategia(nombre="Geográfica", descripcion="Grupos organizados por zona o barrio")
        db.add(cat_geo)
        db.flush()
        print(f"  ✓ Categoría 'Geográfica' creada (id={cat_geo.id})")
    else:
        print(f"  · Categoría 'Geográfica' ya existe (id={cat_geo.id})")

    cat_cultos = db.query(models.CategoriaEstrategia).filter_by(nombre="Cultos").first()
    if not cat_cultos:
        cat_cultos = models.CategoriaEstrategia(nombre="Cultos", descripcion="Cultos dominicales y servicios regulares")
        db.add(cat_cultos)
        db.flush()
        print(f"  ✓ Categoría 'Cultos' creada (id={cat_cultos.id})")
    else:
        print(f"  · Categoría 'Cultos' ya existe (id={cat_cultos.id})")

    print("\n── Estrategia 1: Geográfica ─────────────────")

    est_geo = db.query(models.EstrategiaEvangelismo).filter_by(id="estrategia-geografica").first()
    if not est_geo:
        est_geo = models.EstrategiaEvangelismo(
            id="estrategia-geografica",
            nombre="Estrategia Geográfica",
            categoria_id=cat_geo.id,
            sede_id=SEDE_ID,
            frecuencia="SEMANAL",
            fecha_inicio=_now(),
            activa=True,
        )
        db.add(est_geo)
        db.flush()
        print(f"  ✓ Estrategia '{est_geo.nombre}' creada")
    else:
        print(f"  · Estrategia '{est_geo.nombre}' ya existe")

    grupos_geo_existentes = db.query(models.GrupoEvangelismo).filter_by(estrategia_id="estrategia-geografica").count()
    grupos_a_crear = max(0, 20 - grupos_geo_existentes)
    print(f"  · Grupos existentes: {grupos_geo_existentes} — creando {grupos_a_crear} más")

    for i in range(grupos_a_crear):
        num = grupos_geo_existentes + i + 1
        barrio = BARRIOS_BOGOTA[(num - 1) % len(BARRIOS_BOGOTA)]
        dia = DIAS[(num - 1) % 5]        # lunes a viernes
        hora = HORAS[(num - 1) % len(HORAS)]
        codigo = f"GEO-{num:02d}"
        grupo = models.GrupoEvangelismo(
            estrategia_id="estrategia-geografica",
            sede_id=SEDE_ID,
            codigo=codigo,
            nombre=f"Grupo Geográfico {barrio}",
            ubicacion=barrio,
            direccion=f"Barrio {barrio}, Bogotá",
            capacidad=15,
            dia_reunion=dia,
            hora_reunion=hora,
            activo=True,
        )
        db.add(grupo)
        print(f"    + {codigo}: {grupo.nombre} ({dia} {hora})")

    print("\n── Estrategia 2: Cultos Dominicales ─────────")

    est_cultos = db.query(models.EstrategiaEvangelismo).filter_by(id="estrategia-cultos-dominicales").first()
    if not est_cultos:
        est_cultos = models.EstrategiaEvangelismo(
            id="estrategia-cultos-dominicales",
            nombre="Cultos Dominicales",
            categoria_id=cat_cultos.id,
            sede_id=SEDE_ID,
            frecuencia="SEMANAL",
            fecha_inicio=_now(),
            activa=True,
        )
        db.add(est_cultos)
        db.flush()
        print(f"  ✓ Estrategia '{est_cultos.nombre}' creada")
    else:
        print(f"  · Estrategia '{est_cultos.nombre}' ya existe")

    grupos_cultos_existentes = db.query(models.GrupoEvangelismo).filter_by(estrategia_id="estrategia-cultos-dominicales").count()
    cultos_a_crear = [c for c in CULTOS[grupos_cultos_existentes:]]
    print(f"  · Grupos existentes: {grupos_cultos_existentes} — creando {len(cultos_a_crear)} más")

    for i, (nombre, dia, hora) in enumerate(cultos_a_crear):
        num = grupos_cultos_existentes + i + 1
        codigo = f"CUL-{num:02d}"
        grupo = models.GrupoEvangelismo(
            estrategia_id="estrategia-cultos-dominicales",
            sede_id=SEDE_ID,
            codigo=codigo,
            nombre=nombre,
            ubicacion="Templo Central",
            direccion="Sede Principal, Bogotá",
            capacidad=200,
            dia_reunion=dia,
            hora_reunion=hora,
            activo=True,
        )
        db.add(grupo)
        print(f"    + {codigo}: {nombre} ({dia} {hora})")

    db.commit()
    print("\n✓ Seed completado")

    # Resumen
    total_grupos = db.query(models.GrupoEvangelismo).count()
    print("\nResumen final:")
    for e in db.query(models.EstrategiaEvangelismo).all():
        n = db.query(models.GrupoEvangelismo).filter_by(estrategia_id=e.id).count()
        print(f"  {e.id}: {e.nombre} — {n} grupos ({e.frecuencia})")
    print(f"  Total grupos en DB: {total_grupos}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        db.close()

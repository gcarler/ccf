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

#!/usr/bin/env python3
"""
Migration: Add missing indexes on foreign key columns for evangelism tables.

PostgreSQL does not auto-index foreign key columns. Over time, JOINs
on these columns scan full tables. Adding CONCURRENTLY avoids locking.

Usage:
    cd /root/ccf && ./venv/bin/python scripts/migrations/add_evangelism_indexes.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")

from sqlalchemy import text
from backend.core.database import engine


def index_exists(index_name: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT 1 FROM pg_indexes WHERE indexname = :name"
            ),
            {"name": index_name},
        )
        return result.first() is not None


def run():
    # CONCURRENTLY requires autocommit (no transaction)
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")

    indexes = [
        # estrategias_evangelismo
        ("idx_estrategias_sede_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_estrategias_sede_id ON estrategias_evangelismo(sede_id)"),
        ("idx_estrategias_categoria_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_estrategias_categoria_id ON estrategias_evangelismo(categoria_id)"),

        # grupos_evangelismo
        ("idx_grupos_sede_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grupos_sede_id ON grupos_evangelismo(sede_id)"),
        ("idx_grupos_lider", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grupos_lider ON grupos_evangelismo(lider_persona_id)"),
        ("idx_grupos_asistente", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grupos_asistente ON grupos_evangelismo(asistente_persona_id)"),
        ("idx_grupos_anfitrion", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grupos_anfitrion ON grupos_evangelismo(anfitrion_persona_id)"),

        # grupo_participantes
        ("idx_participantes_grupo_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participantes_grupo_id ON grupo_participantes(grupo_id)"),
        ("idx_participantes_persona_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participantes_persona_id ON grupo_participantes(persona_id)"),
        ("idx_participantes_rol_pers", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participantes_rol_pers ON grupo_participantes(rol_personalizado_id)"),

        # sesiones_grupo
        ("idx_sesiones_grupo_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sesiones_grupo_id ON sesiones_grupo(grupo_id)"),

        # asistencias
        ("idx_asistencias_sesion_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asistencias_sesion_id ON asistencias(sesion_id)"),
        ("idx_asistencias_persona_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asistencias_persona_id ON asistencias(persona_id)"),
        ("idx_asistencias_motivo_excusa", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asistencias_motivo_excusa ON asistencias(motivo_excusa_id)"),

        # registros_seguimiento
        ("idx_seguimiento_asistencia_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seguimiento_asistencia_id ON registros_seguimiento(asistencia_id)"),
        ("idx_seguimiento_responsable", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seguimiento_responsable ON registros_seguimiento(responsable_id)"),

        # historial_embudo
        ("idx_historial_persona_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_historial_persona_id ON historial_embudo(persona_id)"),

        # logs_auditoria
        ("idx_logs_usuario_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_usuario_id ON logs_auditoria(usuario_id)"),
    ]

    created = 0
    skipped = 0
    for name, ddl in indexes:
        if index_exists(name):
            print(f"  → {name} already exists, skipping...")
            skipped += 1
        else:
            print(f"  ✓ Creating {name}...")
            conn.execute(text(ddl))
            created += 1

    conn.close()
    print(f"\nDone! {created} indexes created, {skipped} already existed.")


if __name__ == "__main__":
    print("Adding missing evangelism FK indexes...")
    run()

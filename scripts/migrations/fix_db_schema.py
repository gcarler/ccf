"""
Script de reparación de base de datos — Crea tablas faltantes y añade columnas.

Ejecución: python fix_db_schema.py
"""

import logging
import sys

from sqlalchemy import inspect, text

from backend import models  # noqa: F401 — ensures all models are registered
from backend.core.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("fix_db")

# ── Columnas que deben existir en cada tabla ──────────────────────────
REQUIRED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "projects": [
        ("owner_id", "INTEGER"),
        ("color", "VARCHAR(20)"),
        ("icon", "VARCHAR(50)"),
        ("updated_at", "DATETIME"),
    ],
    "project_tasks": [
        ("parent_id", "INTEGER"),
        ("order_index", "INTEGER DEFAULT 0"),
        ("updated_at", "DATETIME"),
        ("attachments", "TEXT DEFAULT '[]'"),
    ],
}


def main() -> None:
    log.info("=== Paso 1: Crear tablas ORM faltantes ===")
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    orm_tables = set(Base.metadata.tables.keys())
    missing = sorted(orm_tables - existing)

    if missing:
        log.info("Tablas faltantes (%d): %s", len(missing), missing)
        Base.metadata.create_all(bind=engine)
        log.info("Tablas creadas correctamente.")
    else:
        log.info("Todas las tablas ORM ya existen.")

    # Verify
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    still_missing = sorted(orm_tables - existing)
    if still_missing:
        log.error("Aún faltan tablas: %s", still_missing)
        sys.exit(1)
    log.info("Total tablas en DB: %d", len(existing))

    log.info("=== Paso 2: Añadir columnas faltantes ===")
    with engine.connect() as conn:
        for table_name, columns in REQUIRED_COLUMNS.items():
            db_cols = {c["name"] for c in inspector.get_columns(table_name)}
            for col_name, col_type in columns:
                if col_name in db_cols:
                    log.info("  %s.%s ya existe — saltando", table_name, col_name)
                    continue
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    log.info("  + %s.%s (%s) — OK", table_name, col_name, col_type)
                except Exception as exc:
                    conn.rollback()
                    log.warning("  ~ %s.%s — error: %s", table_name, col_name, exc)

    # Verify final state
    log.info("=== Paso 3: Verificación final ===")
    inspector = inspect(engine)
    for table_name, columns in REQUIRED_COLUMNS.items():
        db_cols = {c["name"] for c in inspector.get_columns(table_name)}
        for col_name, _ in columns:
            status = "✓" if col_name in db_cols else "✗"
            log.info("  %s %s.%s", status, table_name, col_name)

    log.info("=== Reparación completada ===")


if __name__ == "__main__":
    main()

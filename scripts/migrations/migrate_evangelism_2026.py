#!/usr/bin/env python3
"""
Migration: Add new columns for evangelism refactoring.

Adds codigo/clase_raiz/activa to evangelism_strategies,
estado/es_primera_vez/requiere_seguimiento to asistencias,
rol_personalizado_id/fecha_ingreso/activo to grupo_participantes,
tags/origen_* to members, and creates new tables.

Usage:
    cd /root/ccf && ./venv/bin/python scripts/migrations/migrate_evangelism_2026.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")

from sqlalchemy import text
from backend.core.database import engine, SessionLocal


def column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ),
            {"table": table, "column": column},
        )
        return result.first() is not None


def table_exists(table: str) -> bool:
    """Check if a table exists."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = :table"
            ),
            {"table": table},
        )
        return result.first() is not None


def run():
    db = SessionLocal()

    # ── 1. evangelism_strategies — add codigo, clase_raiz, activa ──
    if not column_exists("evangelism_strategies", "codigo"):
        print("[1/10] Adding codigo to evangelism_strategies...")
        db.execute(text("ALTER TABLE evangelism_strategies ADD COLUMN codigo VARCHAR(20) UNIQUE"))
        db.execute(text("UPDATE evangelism_strategies SET codigo = 'EVG-' || id WHERE codigo IS NULL"))
    else:
        print("[1/10] codigo already exists, skipping...")

    if not column_exists("evangelism_strategies", "clase_raiz"):
        print("[2/10] Adding clase_raiz to evangelism_strategies...")
        db.execute(text("ALTER TABLE evangelism_strategies ADD COLUMN clase_raiz VARCHAR(50)"))
        db.execute(text("UPDATE evangelism_strategies SET clase_raiz = typology WHERE clase_raiz IS NULL AND typology IS NOT NULL"))
    else:
        print("[2/10] clase_raiz already exists, skipping...")

    if not column_exists("evangelism_strategies", "activa"):
        print("[3/10] Adding activa to evangelism_strategies...")
        db.execute(text("ALTER TABLE evangelism_strategies ADD COLUMN activa BOOLEAN DEFAULT TRUE"))
        db.execute(text("UPDATE evangelism_strategies SET activa = (status = 'active') WHERE activa IS NULL"))
    else:
        print("[3/10] activa already exists, skipping...")

    # ── 2. grupo_participantes — add rol_personalizado_id, fecha_ingreso, activo ──
    if not column_exists("grupo_participantes", "rol_personalizado_id"):
        print("[4/10] Adding rol_personalizado_id to grupo_participantes...")
        db.execute(text(
            "ALTER TABLE grupo_participantes ADD COLUMN rol_personalizado_id INTEGER "
            "REFERENCES roles_personalizados_estrategia(id) ON DELETE SET NULL"
        ))
    else:
        print("[4/10] rol_personalizado_id already exists, skipping...")

    if not column_exists("grupo_participantes", "fecha_ingreso"):
        print("[5/10] Adding fecha_ingreso to grupo_participantes...")
        db.execute(text("ALTER TABLE grupo_participantes ADD COLUMN fecha_ingreso TIMESTAMP DEFAULT NOW()"))
        db.execute(text("UPDATE grupo_participantes SET fecha_ingreso = NOW() WHERE fecha_ingreso IS NULL"))
    else:
        print("[5/10] fecha_ingreso already exists, skipping...")

    if not column_exists("grupo_participantes", "activo"):
        print("[6/10] Adding activo to grupo_participantes...")
        db.execute(text("ALTER TABLE grupo_participantes ADD COLUMN activo BOOLEAN DEFAULT TRUE"))
        db.execute(text("UPDATE grupo_participantes SET activo = TRUE WHERE activo IS NULL"))
    else:
        print("[6/10] activo already exists, skipping...")

    # ── 3. asistencias — add estado, es_primera_vez, requiere_seguimiento ──
    if not column_exists("asistencias", "estado"):
        print("[7/10] Adding estado/es_primera_vez/requiere_seguimiento to asistencias...")
        db.execute(text("ALTER TABLE asistencias ADD COLUMN estado VARCHAR(20) DEFAULT 'presente'"))
        db.execute(text(
            "UPDATE asistencias SET estado = "
            "CASE "
            "  WHEN status = 'first_time' THEN 'primera_vez' "
            "  WHEN attended = TRUE THEN 'presente' "
            "  ELSE 'ausente' "
            "END "
            "WHERE estado IS NULL"
        ))
        db.execute(text("ALTER TABLE asistencias ADD COLUMN es_primera_vez BOOLEAN DEFAULT FALSE"))
        db.execute(text("UPDATE asistencias SET es_primera_vez = TRUE WHERE status = 'first_time'"))
        db.execute(text("ALTER TABLE asistencias ADD COLUMN requiere_seguimiento BOOLEAN DEFAULT FALSE"))
    else:
        print("[7/10] estado already exists, skipping...")

    # ── 4. Create new tables ──
    if not table_exists("roles_personalizados_estrategia"):
        print("[8/12] Creating roles_personalizados_estrategia...")
        db.execute(text("""
            CREATE TABLE roles_personalizados_estrategia (
                id SERIAL PRIMARY KEY,
                estrategia_id VARCHAR(20) NOT NULL REFERENCES evangelism_strategies(codigo) ON DELETE CASCADE,
                nombre_rol VARCHAR(100) NOT NULL,
                descripcion VARCHAR,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX idx_roles_estrategia_id ON roles_personalizados_estrategia(estrategia_id)"))
    else:
        print("[8/12] roles_personalizados_estrategia already exists...")
        # Rename columna nombre -> nombre_rol si es necesario
        if column_exists("roles_personalizados_estrategia", "nombre") \
           and not column_exists("roles_personalizados_estrategia", "nombre_rol"):
            print("    → Renombrando columna nombre → nombre_rol")
            db.execute(text("ALTER TABLE roles_personalizados_estrategia RENAME COLUMN nombre TO nombre_rol"))
        print("[8/12] done.")

    if not table_exists("registros_seguimiento"):
        print("[9/12] Creating registros_seguimiento...")
        db.execute(text("""
            CREATE TABLE registros_seguimiento (
                id SERIAL PRIMARY KEY,
                asistencia_id INTEGER NOT NULL REFERENCES asistencias(id) ON DELETE CASCADE,
                tipo VARCHAR(20) NOT NULL,
                fecha_programada TIMESTAMP,
                fecha_realizada TIMESTAMP,
                realizado_por_member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
                notas TEXT,
                completado BOOLEAN DEFAULT FALSE,
                resultado VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX idx_seguimiento_asistencia ON registros_seguimiento(asistencia_id)"))
        db.execute(text("CREATE INDEX idx_seguimiento_tipo ON registros_seguimiento(tipo)"))
        db.execute(text("CREATE INDEX idx_seguimiento_completado ON registros_seguimiento(completado)"))
    else:
        print("[9/12] registros_seguimiento already exists, skipping...")

    if not table_exists("motivos_excusa"):
        print("[10/12] Creating motivos_excusa...")
        db.execute(text("""
            CREATE TABLE motivos_excusa (
                id SERIAL PRIMARY KEY,
                descripcion VARCHAR NOT NULL UNIQUE,
                es_del_sistema BOOLEAN DEFAULT FALSE,
                activo BOOLEAN DEFAULT TRUE
            )
        """))
        # Seed data
        for desc in ["SALUD", "TRABAJO", "FAMILIA", "OTRA (VER DETALLE)"]:
            db.execute(text(
                "INSERT INTO motivos_excusa (descripcion, es_del_sistema, activo) "
                "VALUES (:desc, TRUE, TRUE) ON CONFLICT (descripcion) DO NOTHING"
            ), {"desc": desc})
    else:
        print("[10/12] motivos_excusa already exists, skipping...")

    # ── 5. members — add tags, origen_* ──
    if not column_exists("members", "tags"):
        print("[11/12] Adding tags/origen_*/origen_fecha to members...")
        db.execute(text("ALTER TABLE members ADD COLUMN tags JSON DEFAULT '[]'::json"))
        db.execute(text(
            "ALTER TABLE members ADD COLUMN origen_estrategia_id INTEGER "
            "REFERENCES evangelism_strategies(id) ON DELETE SET NULL"
        ))
        db.execute(text(
            "ALTER TABLE members ADD COLUMN origen_grupo_id INTEGER "
            "REFERENCES grupos_evangelismo(id) ON DELETE SET NULL"
        ))
        db.execute(text("ALTER TABLE members ADD COLUMN origen_fecha TIMESTAMP"))
    else:
        print("[11/12] tags already exists, skipping...")

    # ── 6. Seed excusas base si la tabla ya existía ──
    if table_exists("motivos_excusa"):
        print("[12/12] Seeding base excuses...")
        for desc in ["SALUD", "TRABAJO", "FAMILIA", "OTRA (VER DETALLE)"]:
            db.execute(text(
                "INSERT INTO motivos_excusa (descripcion, es_del_sistema, activo) "
                "VALUES (:desc, TRUE, TRUE) ON CONFLICT (descripcion) DO NOTHING"
            ), {"desc": desc})
    else:
        print("[12/12] Skipping (table not found)...")

    db.commit()
    print("\nMigration complete!")


if __name__ == "__main__":
    run()

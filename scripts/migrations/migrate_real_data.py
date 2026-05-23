import logging

from sqlalchemy import text

from backend.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration-RealData")


def column_exists(db, table_name, column_name):
    """Verifica si una columna existe en una tabla de SQLite."""
    try:
        cursor = db.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except Exception:
        return False


def migrate():
    db = SessionLocal()

    migrations = [
        ("donations", "status", "VARCHAR(20) DEFAULT 'completed'"),
        ("donations", "reference_code", "VARCHAR(100)"),
        ("donations", "payment_method", "VARCHAR(50) DEFAULT 'Transferencia'"),
        ("admin_audit_logs", "ip_address", "VARCHAR(45)"),
        ("admin_audit_logs", "severity", "VARCHAR(20) DEFAULT 'info'"),
        ("assessments", "description", "TEXT"),
        ("assessments", "course_id", "INTEGER REFERENCES courses(id)"),
        ("cms_media_items", "dimensions", "VARCHAR(50)"),
        ("prayer_requests", "category", "VARCHAR(50) DEFAULT 'General'"),
        ("pastoral_call_logs", "duration_seconds", "INTEGER DEFAULT 0"),
    ]

    try:
        logger.info("Iniciando migración compatible con SQLite...")
        for table, col, type_def in migrations:
            if not column_exists(db, table, col):
                try:
                    db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {type_def}"))
                    logger.info(f"✅ Columna añadida: {table}.{col}")
                except Exception as e:
                    logger.error(f"❌ Error al añadir {table}.{col}: {e}")
            else:
                logger.info(f"ℹ️ La columna {table}.{col} ya existe.")

        db.commit()
        logger.info("✅ Proceso de migración finalizado.")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

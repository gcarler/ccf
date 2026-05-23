import logging

from sqlalchemy import text

from backend.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration-Indices")


def index_exists(db, index_name):
    """Verifica si un índice existe en SQLite o PostgreSQL."""
    try:
        dialect_name = db.bind.dialect.name
        if dialect_name == "postgresql":
            cursor = db.execute(
                text("SELECT indexname FROM pg_indexes WHERE indexname = :idx"),
                {"idx": index_name},
            )
        else:
            cursor = db.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name = :idx"
                ),
                {"idx": index_name},
            )
        return cursor.fetchone() is not None
    except Exception:
        return False


def migrate():
    db = SessionLocal()

    # Índices estratégicos para búsqueda rápida y rendimiento de JOINs
    indices = [
        ("idx_donations_status", "donations", "status"),
        ("idx_donations_ref", "donations", "reference_code"),
        ("idx_audit_resource", "admin_audit_logs", "resource_type, resource_id"),
        ("idx_audit_action", "admin_audit_logs", "action"),
        ("idx_prayer_category", "prayer_requests", "category"),
        ("idx_prayer_status", "prayer_requests", "status"),
        ("idx_tasks_status", "crm_tasks", "status"),
        ("idx_tasks_due", "crm_tasks", "due_date"),
        ("idx_lessons_course", "lessons", "course_id"),
        ("idx_enrollments_user_course", "enrollments", "user_id, course_id"),
        ("idx_user_reminders_user_id", "user_reminders", "user_id"),
    ]

    try:
        logger.info("Iniciando creación de índices para optimización de motor...")
        for idx_name, table, cols in indices:
            # Recheck exists (using a fresh transaction context)
            if not index_exists(db, idx_name):
                try:
                    db.execute(text(f"CREATE INDEX {idx_name} ON {table} ({cols})"))
                    db.commit()
                    logger.info(f"✅ Índice creado: {idx_name} en {table}({cols})")
                except Exception as e:
                    db.rollback()
                    logger.error(f"❌ Error al crear {idx_name}: {e}")
            else:
                logger.info(f"ℹ️ El índice {idx_name} ya existe.")

        logger.info("✅ Optimización de índices finalizada.")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

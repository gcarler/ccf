import logging

from sqlalchemy import text

from backend.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration-Reminders")


def table_exists(db, table_name):
    """Verifica si una tabla existe en SQLite."""
    try:
        cursor = db.execute(
            text(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            )
        )
        return cursor.fetchone() is not None
    except Exception:
        return False


def migrate():
    db = SessionLocal()

    try:
        if not table_exists(db, "user_reminders"):
            logger.info("Creando tabla user_reminders...")
            db.execute(
                text(
                    """
                CREATE TABLE user_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    remind_at DATETIME NOT NULL,
                    priority VARCHAR(20) DEFAULT 'normal',
                    related_type VARCHAR(50),
                    related_id INTEGER,
                    is_sent BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """
                )
            )
            db.execute(
                text(
                    "CREATE INDEX idx_user_reminders_user_id ON user_reminders (user_id)"
                )
            )
            db.execute(
                text(
                    "CREATE INDEX idx_user_reminders_remind_at ON user_reminders (remind_at)"
                )
            )
            logger.info("✅ Tabla user_reminders creada con éxito.")
        else:
            logger.info("ℹ️ La tabla user_reminders ya existe.")

        db.commit()
    except Exception as e:
        logger.error(f"❌ Error en la migración: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

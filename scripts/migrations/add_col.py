import sys
import os

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from sqlalchemy import create_engine, text
from backend.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

with engine.begin() as conn:
    try:
        if settings.database_url.startswith("sqlite"):
            try:
                conn.execute(text("ALTER TABLE project_tasks ADD COLUMN attachments JSON DEFAULT '[]'"))
                print("Migrated sqlite correctly.")
            except Exception as e:
                print("SQLite Migration error ignored:", str(e))
        else:
            try:
                conn.execute(text("ALTER TABLE project_tasks ADD COLUMN attachments JSONB DEFAULT '[]'::jsonb"))
                print("Migrated postgres correctly.")
            except Exception as e:
                print("Postgres Migration error ignored:", str(e))
    except Exception as e:
        print("General Error:", str(e))

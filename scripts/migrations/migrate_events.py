from sqlalchemy import text

from backend.database import engine
from backend.models import Base

# Create new tables
Base.metadata.create_all(bind=engine)

# Alter existing table
with engine.connect() as conn:
    try:
        conn.execute(
            text("ALTER TABLE event_attendances ADD COLUMN session_date DATE NULL;")
        )
        conn.commit()
        print("Added session_date to event_attendances")
    except Exception as e:
        print(f"Column might already exist or error: {e}")

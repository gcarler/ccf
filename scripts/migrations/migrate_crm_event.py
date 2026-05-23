from backend.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text('ALTER TABLE crm_events ADD COLUMN target_audience VARCHAR(50) DEFAULT "ALL"'))
    db.execute(text('ALTER TABLE crm_events ADD COLUMN target_role_id INTEGER REFERENCES role_definitions(id)'))
    db.commit()
    print("Migration applied!")
except Exception as e:
    print(f"Error (maybe already exists?): {e}")
finally:
    db.close()

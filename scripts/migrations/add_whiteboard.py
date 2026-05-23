from backend.core.database import engine
from sqlalchemy import text

def add_col():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE projects ADD COLUMN whiteboard_data TEXT DEFAULT '[]'"))
            conn.commit()
            print("Column 'whiteboard_data' added successfully!")
    except Exception as e:
        print(f"Schema update error (might already exist): {e}")

if __name__ == "__main__":
    add_col()

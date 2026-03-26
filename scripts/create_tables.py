from backend.core.database import Base, engine
from backend.models import Notification

def create_notifications_table():
    try:
        # This will create only missing tables
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully (if they didn't exist).")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_notifications_table()

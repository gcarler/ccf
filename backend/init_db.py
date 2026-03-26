from backend.core.database import Base, engine
import backend.models  # Ensure all models are loaded

def init_db():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()

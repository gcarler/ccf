from __future__ import annotations
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.database import engine, Base
from backend import models # Import models to register them with Base

def ensure_tables():
    print("--- Synchronizing Database Schema ---")
    try:
        Base.metadata.create_all(bind=engine)
        print("--- All tables created/verified successfully! ---")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    ensure_tables()

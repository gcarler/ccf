"""Add source column to prayer_requests table."""

import os
import sys

# Ensure D:\ccf is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from backend.core.database import engine


def migrate():
    with engine.connect() as conn:
        # Add source column if it doesn't exist
        try:
            conn.execute(
                text(
                    "ALTER TABLE prayer_requests ADD COLUMN source VARCHAR(50) DEFAULT 'crm'"
                )
            )
            conn.commit()
            print("  Added source column to prayer_requests")
        except Exception as e:
            print(f"  (source column may already exist: {e})")

        # Create index on source
        try:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_prayer_requests_source ON prayer_requests(source)"
                )
            )
            conn.commit()
            print("  Created index on source column")
        except Exception as e:
            print(f"  (index may already exist: {e})")


if __name__ == "__main__":
    migrate()
    print("Migration complete.")

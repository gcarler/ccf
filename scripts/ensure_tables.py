from __future__ import annotations
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.management.schema import print_schema_drift_report, upgrade_with_optional_bootstrap

def ensure_tables():
    print("--- Synchronizing Database Schema ---")
    try:
        bootstrapped = upgrade_with_optional_bootstrap()
        if bootstrapped:
            print("--- Bootstrapped unmanaged tables via create_all ---")
            for table in bootstrapped:
                print(f" - {table}")
        print_schema_drift_report()
        print("--- Schema synchronization finished ---")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    ensure_tables()

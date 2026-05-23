from backend.management.schema import (
    print_schema_drift_report,
    reset_database_for_local_bootstrap,
)


def reset_database():
    try:
        print("Dropping all tables and rebuilding from metadata for local/test use...")
        reset_database_for_local_bootstrap()
        print_schema_drift_report()
        print("Database schema reset successfully.")
    except Exception as e:
        print(f"Error resetting database: {e}")


if __name__ == "__main__":
    reset_database()

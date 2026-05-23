from backend.management.schema import (print_schema_drift_report,
                                       upgrade_with_optional_bootstrap)


def init_db():
    print("Applying Alembic migrations...")
    bootstrapped = upgrade_with_optional_bootstrap()
    if bootstrapped:
        print("Bootstrapped unmanaged tables via create_all:")
        for table in bootstrapped:
            print(f" - {table}")
    print_schema_drift_report()
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()

from backend.management.schema import (print_schema_drift_report,
                                       upgrade_with_optional_bootstrap)


def create_notifications_table():
    try:
        bootstrapped = upgrade_with_optional_bootstrap()
        if bootstrapped:
            print("Bootstrapped unmanaged tables via create_all:")
            for table in bootstrapped:
                print(f" - {table}")
        print_schema_drift_report()
        print("Schema sync completed.")
    except Exception as e:
        print(f"Error creating tables: {e}")


if __name__ == "__main__":
    create_notifications_table()

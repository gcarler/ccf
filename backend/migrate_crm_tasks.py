"""
CRM Tasks migration utility.
Reads database connection from environment variables.
"""
import os
import sys
import pg8000


def get_connection():
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5435"))
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME", "ccf_db")

    if not user or not password:
        print("ERROR: Set DB_USER and DB_PASSWORD environment variables.", file=sys.stderr)
        sys.exit(1)

    return pg8000.connect(host=host, port=port, user=user, password=password, database=database)


def main():
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    # Add category column if missing
    try:
        cur.execute("ALTER TABLE crm_tasks ADD COLUMN category VARCHAR(100) DEFAULT 'Pastoral'")
        print("Added: category column")
    except Exception as e:
        if "already exists" in str(e):
            print("category column already exists — skipping")
        else:
            print(f"Error adding category: {e}")

    # Normalize CRM task statuses from the previous enum
    try:
        cur.execute("UPDATE crm_tasks SET status = 'pending' WHERE status = 'todo'")
        print("Updated 'todo' -> 'pending'")
        cur.execute("UPDATE crm_tasks SET priority = 'medium' WHERE priority = 'normal'")
        print("Updated 'normal' -> 'medium'")
    except Exception as e:
        print(f"Error updating: {e}")

    # Check columns
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'crm_tasks' ORDER BY ordinal_position"
    )
    cols = [r[0] for r in cur.fetchall()]
    print(f"Final columns: {cols}")

    cur.close()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()

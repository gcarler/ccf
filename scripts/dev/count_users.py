import os
import sqlite3

db_path = "d:/ccf/ccf_v2.db"

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM members")
        members_count = cursor.fetchone()[0]

        print(f"Total de usuarios registrados: {users_count}")
        print(f"Total de miembros registrados: {members_count}")
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

dsn = "postgresql://postgres:postgres@localhost:5432/postgres"
try:
    conn = psycopg2.connect(dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='ccf_db'")
    exists = cursor.fetchone()
    if not exists:
        print("Creating ccf_db...")
        cursor.execute("CREATE DATABASE ccf_db")
        print("Success!")
    else:
        print("ccf_db already exists.")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Failed to manage DB: {e}")

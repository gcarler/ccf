#!/usr/bin/env python3
"""
create_db.py
Creates ccf_final.db by executing master_schema.sql.
"""
import sqlite3

SCHEMA_FILE = "/root/ccf/master_schema.sql"
DB_FILE = "/root/ccf/ccf_final.db"


def main():
    with open(SCHEMA_FILE, "r") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(DB_FILE)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print(f"[OK] Database created: {DB_FILE}")


if __name__ == "__main__":
    main()

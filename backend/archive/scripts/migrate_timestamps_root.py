import sqlite3
import os

db_path = 'd:/ccf/ccf_v2.db'

print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['users', 'testimonials', 'courses', 'enrollments', 'members', 'families', 'events', 'glory_houses', 'volunteers', 'donations', 'communication_logs', 'mesh_capabilities']

ALLOWED_TABLES = set(tables)

for table in tables:
    if table not in ALLOWED_TABLES:
        print(f"Skipping unknown table: {table}")
        continue
    try:
        print(f"Checking table {table}...")
        cursor.execute('PRAGMA table_info("{}")'.format(table))
        columns = [row[1] for row in cursor.fetchall()]

        if 'created_at' not in columns:
            print(f"Adding created_at to {table}")
            cursor.execute('ALTER TABLE "{}" ADD COLUMN created_at DATETIME DEFAULT \'2026-03-01 00:00:00\''.format(table))

        if 'updated_at' not in columns:
            print(f"Adding updated_at to {table}")
            cursor.execute('ALTER TABLE "{}" ADD COLUMN updated_at DATETIME DEFAULT \'2026-03-01 00:00:00\''.format(table))

    except Exception as e:
        print(f"Error on table {table}: {e}")

conn.commit()
conn.close()
print("Migration done for ROOT DB.")

import sqlite3
import os

db_path = 'ccf_v2.db'
if not os.path.exists(db_path):
    # Try parent dir as per .env
    db_path = '../ccf_v2.db'

print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['users', 'testimonials', 'courses', 'enrollments', 'members', 'families', 'events', 'glory_houses', 'volunteers', 'donations', 'communication_logs', 'mesh_capabilities']

for table in tables:
    try:
        print(f"Checking table {table}...")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'created_at' not in columns:
            print(f"Adding created_at to {table}")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN created_at DATETIME DEFAULT '2026-03-01 00:00:00'")
        
        if 'updated_at' not in columns:
            print(f"Adding updated_at to {table}")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN updated_at DATETIME DEFAULT '2026-03-01 00:00:00'")
            
    except Exception as e:
        print(f"Error on table {table}: {e}")

conn.commit()
conn.close()
print("Migration done.")

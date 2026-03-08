import sqlite3
import os

db_path = 'd:/ccf/ccf_v2.db'

print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Full list of tables from models.py
tables = [
    'users', 'testimonials', 'courses', 'lessons', 'resources', 
    'assessments', 'enrollments', 'assessment_attempts', 'formal_actas', 
    'certificates', 'families', 'members', 'events', 'attendance', 
    'assignment_submissions', 'announcements', 'sermons', 'books', 
    'page_contents', 'volunteers', 'consolidation_pipeline', 
    'pastoral_call_logs', 'consolidation_automations', 
    'counseling_sessions', 'donations', 'communication_logs', 
    'mesh_capabilities', 'glory_houses'
]

for table in tables:
    try:
        print(f"Checking table {table}...")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if not columns:
            print(f"Table {table} does not exist. Skipping.")
            continue

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
print("Comprehensive migration done.")

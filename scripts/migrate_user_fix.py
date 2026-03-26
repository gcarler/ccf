import sqlite3
import os

db_path = r'D:\ccf_v2.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'is_email_verified' not in columns:
        print("Adding is_email_verified column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 0")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column already exists.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)

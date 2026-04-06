import pg8000

conn = pg8000.connect(
    host="localhost",
    port=5435,
    user="postgres",
    password="admin123",
    database="ccf_db"
)
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

# Update old 'todo' statuses to 'pending' for frontend compatibility
try:
    cur.execute("UPDATE crm_tasks SET status = 'pending' WHERE status = 'todo'")
    print("Updated 'todo' -> 'pending'")
    cur.execute("UPDATE crm_tasks SET priority = 'medium' WHERE priority = 'normal'") 
    print("Updated 'normal' -> 'medium'")
except Exception as e:
    print(f"Error updating: {e}")

# Check columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'crm_tasks' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print(f"Final columns: {cols}")

cur.close()
conn.close()
print("Migration complete.")

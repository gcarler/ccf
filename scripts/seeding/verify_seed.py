import sqlite3

conn = sqlite3.connect('d:\\ccf_v2.db')
cursor = conn.cursor()

print("Projects:")
cursor.execute("SELECT id, title FROM projects ORDER BY id DESC LIMIT 2")
for row in cursor.fetchall():
    print(row)

print("\nMilestones (Levels):")
cursor.execute("SELECT project_id, title FROM project_milestones ORDER BY id DESC LIMIT 6")
for row in cursor.fetchall():
    print(row)

print("\nTasks (Activities & Tareas):")
cursor.execute("SELECT project_id, parent_id, title FROM project_tasks ORDER BY id DESC LIMIT 10")
for row in cursor.fetchall():
    print(row)

conn.close()

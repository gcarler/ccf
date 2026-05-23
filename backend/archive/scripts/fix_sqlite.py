import sqlite3
import json

conn = sqlite3.connect(r"d:\ccf\ccf_v2.db")
c = conn.cursor()

c.execute("SELECT id, labels FROM project_tasks")
rows = c.fetchall()
updated = 0
for r in rows:
    task_id = r[0]
    labels = r[1]
    
    if labels:
        try:
            parsed = json.loads(labels)
            if not isinstance(parsed, list):
                new_labels = json.dumps([str(parsed)])
                c.execute("UPDATE project_tasks SET labels = ? WHERE id = ?", (new_labels, task_id))
                updated += 1
        except json.JSONDecodeError:
            new_labels = json.dumps([str(labels)])
            c.execute("UPDATE project_tasks SET labels = ? WHERE id = ?", (new_labels, task_id))
            updated += 1

conn.commit()
print(f"Fixed {updated} tasks.")
conn.close()

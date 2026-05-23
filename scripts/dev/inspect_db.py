import sqlite3

conn = sqlite3.connect("d:\\ccf_v2.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(projects)")
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()

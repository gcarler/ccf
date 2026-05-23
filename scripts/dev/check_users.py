import sqlite3

conn = sqlite3.connect("d:\\ccf_v2.db")
cursor = conn.cursor()
cursor.execute("SELECT id, username, role FROM users LIMIT 10")
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()

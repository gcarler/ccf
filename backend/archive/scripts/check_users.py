import sqlite3

conn = sqlite3.connect(r"d:\ccf\ccf_v2.db")
c = conn.cursor()
c.execute("SELECT email, username, role FROM users LIMIT 10")
for row in c.fetchall():
    print(row)
conn.close()

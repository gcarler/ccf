import sqlite3

try:
    conn = sqlite3.connect('ccf_v2.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, is_active FROM users;")
    users = cursor.fetchall()
    print("Usuarios encontrados:")
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Activo: {user[2]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")

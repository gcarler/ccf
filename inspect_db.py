import sqlite3
import json

def inspect():
    conn = sqlite3.connect('d:\\ccf_v2.db')
    cursor = conn.cursor()
    
    print("--- USERS ---")
    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()
    for u in users:
        print(f"ID: {u[0]}, Username: {u[1]}, Role: {u[2]}")
        
    print("\n--- PROJECTS ---")
    cursor.execute("SELECT id, title FROM projects")
    projects = cursor.fetchall()
    for p in projects:
        print(f"ID: {p[0]}, Title: {p[1]}")
        
    print("\n--- MEMBERS ---")
    cursor.execute("SELECT id, first_name, last_name FROM members LIMIT 5")
    members = cursor.fetchall()
    for m in members:
        print(f"ID: {m[0]}, Name: {m[1]} {m[2]}")
        
    conn.close()

if __name__ == "__main__":
    inspect()

import sqlite3
import sys

# Agregamos d:\ccf al sys.path para importar get_password_hash
sys.path.insert(0, r"d:\ccf")

from backend.core.security import get_password_hash

hash_str = get_password_hash("admin1234")

conn = sqlite3.connect(r"d:\ccf\ccf_v2.db")
c = conn.cursor()
c.execute("UPDATE users SET password_hash = ? WHERE email = ?", (hash_str, 'admin@ccf.la'))
conn.commit()
print("Password reset to admin1234 for admin@ccf.la")
conn.close()

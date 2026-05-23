import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
dsn = os.getenv("DATABASE_URL")
print(f"Testing connection to: {dsn}")
try:
    conn = psycopg2.connect(dsn)
    print("Success!")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")

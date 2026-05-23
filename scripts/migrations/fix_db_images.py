import re
import sqlite3

conn = sqlite3.connect("ccf_v2.db")
cursor = conn.cursor()

# We don't know exactly which table holds the CMS content, but we can search all text columns in all tables.
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

updated = 0
for (table,) in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()

    # Get all column names that are TEXT or VARCHAR or JSON
    text_cols = [
        col[1]
        for col in columns
        if "TEXT" in col[2].upper()
        or "VARCHAR" in col[2].upper()
        or "JSON" in col[2].upper()
    ]

    if not text_cols:
        continue

    # Fetch all rows
    cursor.execute(f"SELECT rowid, {','.join(text_cols)} FROM {table}")
    rows = cursor.fetchall()

    for row in rows:
        rowid = row[0]
        values = list(row[1:])
        changed = False

        for i, val in enumerate(values):
            if val and isinstance(val, str) and "images.unsplash.com" in val:
                # Replace with picsum
                new_val = re.sub(
                    r'https://images\.unsplash\.com/photo-([a-zA-Z0-9\-]+)(?:\?[^"\'\s]+)?',
                    r"https://picsum.photos/seed/\1/800/600",
                    val,
                )
                if new_val != val:
                    values[i] = new_val
                    changed = True

        if changed:
            set_clause = ", ".join([f"{col} = ?" for col in text_cols])
            cursor.execute(
                f"UPDATE {table} SET {set_clause} WHERE rowid = ?", values + [rowid]
            )
            updated += 1

conn.commit()
conn.close()
print(f"Updated {updated} rows in DB.")

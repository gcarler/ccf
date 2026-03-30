import sqlite3
import os

db_path = 'd:/ccf/ccf_v2.db'

def repair_db():
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Añadiendo columnas de gestión ministerial a la tabla 'members'...")
        
        # Añadir columnas si no existen
        columns_to_add = [
            ("talents", "TEXT"),
            ("spiritual_gifts", "TEXT"),
            ("pastoral_notes", "TEXT")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE members ADD COLUMN {col_name} {col_type}")
                print(f"Columna '{col_name}' añadida con éxito.")
            except sqlite3.OperationalError:
                print(f"La columna '{col_name}' ya existe.")

        # Crear la tabla de donaciones si no existe
        print("Verificando tabla 'donations'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                amount REAL NOT NULL,
                donation_type VARCHAR(50) DEFAULT 'Diezmo',
                fund_id INTEGER,
                person_id INTEGER,
                donor_name VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(member_id) REFERENCES members(id)
            )
        """)
        print("Tabla 'donations' lista.")

        conn.commit()
        conn.close()
        print("Reparación completada con éxito.")
        
    except Exception as e:
        print(f"Error durante la reparación: {e}")

if __name__ == "__main__":
    repair_db()

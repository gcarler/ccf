import os
import sqlite3

db_path = "d:/ccf/ccf_v2.db"


def ensure_tasks_table():
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Verificando tabla 'crm_tasks'...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS crm_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                member_id INTEGER,
                lead_id INTEGER,
                assignee_id INTEGER NOT NULL,
                due_date DATETIME,
                status VARCHAR(20) DEFAULT 'todo',
                priority VARCHAR(20) DEFAULT 'normal',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(member_id) REFERENCES members(id),
                FOREIGN KEY(lead_id) REFERENCES consolidation_pipeline(id),
                FOREIGN KEY(assignee_id) REFERENCES users(id)
            )
        """
        )
        print("Tabla 'crm_tasks' lista.")

        conn.commit()
        conn.close()
        print("Sincronización de tablas completada.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    ensure_tasks_table()

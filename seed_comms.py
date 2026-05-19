import sqlite3
import datetime
import json

def seed_communications_ecosystem_v2():
    conn = sqlite3.connect('d:\\ccf_v2.db')
    cursor = conn.cursor()
    
    # Ensure project_whiteboards exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_whiteboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL,
            elements_json TEXT NOT NULL DEFAULT '[]',
            thumbnail_url VARCHAR(500),
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    now = datetime.datetime.now()

    # 1. Main Project: Ecosistema de Comunicaciones CCF
    cursor.execute("""
        INSERT INTO projects (title, description, status, owner_id, color, icon, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Ecosistema de Comunicaciones CCF", 
          "Programa integral para la gestión de la identidad, el alcance y la co-creación ministerial.", 
          "active", 1, "#8b5cf6", "Megaphone", now.isoformat(), now.isoformat()))
    project_id = cursor.lastrowid

    # 2. Level 2 Projects
    # 2.1 Comunicación Organizacional (Admin - ID 1)
    cursor.execute("""
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, "PROYECTO: Comunicación Organizacional", 
          "Fortalecimiento de los flujos de información interna.", 
          "todo", "high", 1, 0, now.isoformat(), now.isoformat()))
    org_comm_id = cursor.lastrowid

    # 2.2 Evangelismo (Pastor Pedro - ID 3)
    cursor.execute("""
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, "PROYECTO: Evangelismo", 
          "Campañas de impacto masivo.", 
          "active", "urgent", 3, 1, now.isoformat(), now.isoformat()))
    ev_comm_id = cursor.lastrowid

    # 2.3 Talleres de Co-creación (Lider Ana - ID 4)
    cursor.execute("""
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, "PROYECTO: Talleres de Co-creación", 
          "Espacios participativos.", 
          "todo", "normal", 4, 2, now.isoformat(), now.isoformat()))
    co_comm_id = cursor.lastrowid

    # 3. Project Dashboard
    dashboard_elements = [
        {"id": "1", "type": "text", "x": 50, "y": 50, "text": "Dashboard de Comunicaciones CCF", "fontSize": 24, "fontWeight": "bold"},
        {"id": "2", "type": "rect", "x": 50, "y": 100, "width": 200, "height": 100, "fill": "#8b5cf6", "label": "Comunicación Org."},
        {"id": "3", "type": "rect", "x": 300, "y": 100, "width": 200, "height": 100, "fill": "#ef4444", "label": "Evangelismo"},
        {"id": "4", "type": "rect", "x": 550, "y": 100, "width": 200, "height": 100, "fill": "#10b981", "label": "Co-creación"}
    ]
    
    cursor.execute("""
        INSERT INTO project_whiteboards (project_id, title, elements_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (project_id, "Panel de Control Comunicaciones", json.dumps(dashboard_elements), now.isoformat(), now.isoformat()))

    conn.commit()
    print(f"Successfully created Communications Project with Dashboard.")
    conn.close()

if __name__ == "__main__":
    seed_communications_ecosystem_v2()

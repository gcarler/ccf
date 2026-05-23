import datetime
import sqlite3


def seed_evangelism_v2():
    conn = sqlite3.connect("d:\\ccf_v2.db")
    cursor = conn.cursor()

    # 1. Ensure project_milestones table exists
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            target_date DATETIME,
            is_completed BOOLEAN DEFAULT 0,
            created_at DATETIME,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """
    )

    # 2. Ensure parent_id exists in project_tasks
    cursor.execute("PRAGMA table_info(project_tasks)")
    columns = [row[1] for row in cursor.fetchall()]
    if "parent_id" not in columns:
        print("Adding parent_id column to project_tasks...")
        cursor.execute(
            "ALTER TABLE project_tasks ADD COLUMN parent_id INTEGER REFERENCES project_tasks(id) ON DELETE CASCADE"
        )

    now = datetime.datetime.now()

    # Project 1: Plan de Invasión Urbana 2026
    cursor.execute(
        """
        INSERT INTO projects (title, description, status, owner_id, color, icon, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "Plan de Invasión Urbana 2026",
            "Estrategia masiva de alcance territorial y servicio social en zonas críticas.",
            "active",
            3,
            "#ef4444",
            "MapPin",
            now.isoformat(),
            now.isoformat(),
        ),
    )
    p1_id = cursor.lastrowid

    # Milestones (Levels) for P1
    milestones_p1 = [
        ("Preparación Espiritual", "Cadena de ayuno y oración por los equipos.", 15),
        (
            "Incursión Territorial",
            "Despliegue de brigadas en los barrios asignados.",
            30,
        ),
        ("Cosecha y Seguimiento", "Consolidación de las personas contactadas.", 60),
    ]
    for m in milestones_p1:
        cursor.execute(
            """
            INSERT INTO project_milestones (project_id, title, description, target_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                p1_id,
                m[0],
                m[1],
                (now + datetime.timedelta(days=m[2])).isoformat(),
                now.isoformat(),
            ),
        )

    # Activities (Parent Tasks) for P1
    # Activity 1: Entrenamiento de Brigadas
    cursor.execute(
        """
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            p1_id,
            "Entrenamiento de Brigadas",
            "Capacitación técnica y espiritual para los voluntarios.",
            "todo",
            "high",
            3,
            0,
            now.isoformat(),
            now.isoformat(),
        ),
    )
    act1_id = cursor.lastrowid

    # Subtasks for Activity 1
    subtasks_act1 = [
        (
            "Clase de Primeros Auxilios Espirituales",
            "Cómo abordar crisis emocionales durante el evangelismo.",
            4,
        ),
        (
            "Mapeo de zonas calientes",
            "Identificación de puntos estratégicos en Barrio Sur.",
            1,
        ),
    ]
    for st in subtasks_act1:
        cursor.execute(
            """
            INSERT INTO project_tasks (project_id, parent_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                p1_id,
                act1_id,
                st[0],
                st[1],
                "todo",
                "normal",
                st[2],
                0,
                now.isoformat(),
                now.isoformat(),
            ),
        )

    # Activity 2: Operativo de Compasión
    cursor.execute(
        """
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            p1_id,
            "Operativo de Compasión",
            "Acciones directas de servicio en la comunidad.",
            "todo",
            "urgent",
            1,
            1,
            now.isoformat(),
            now.isoformat(),
        ),
    )
    act2_id = cursor.lastrowid

    # Subtasks for Activity 2
    subtasks_act2 = [
        ("Reparto de kits de aseo", "Distribución a familias vulnerables.", 4),
        ("Toma de presión y oración", "Punto de atención en la plaza central.", 1),
    ]
    for st in subtasks_act2:
        cursor.execute(
            """
            INSERT INTO project_tasks (project_id, parent_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                p1_id,
                act2_id,
                st[0],
                st[1],
                "todo",
                "high",
                st[2],
                0,
                now.isoformat(),
                now.isoformat(),
            ),
        )

    # Project 2: Misión Digital: Redes de Gracia
    cursor.execute(
        """
        INSERT INTO projects (title, description, status, owner_id, color, icon, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "Misión Digital: Redes de Gracia",
            "Proyecto de evangelismo en plataformas digitales y redes sociales.",
            "active",
            4,
            "#3b82f6",
            "Share2",
            now.isoformat(),
            now.isoformat(),
        ),
    )
    p2_id = cursor.lastrowid

    # Milestones (Levels) for P2
    milestones_p2 = [
        (
            "Arquitectura de Contenido",
            "Definición de pilares de contenido y diseño visual.",
            10,
        ),
        ("Lanzamiento Viral", "Puesta en marcha de las campañas publicitarias.", 25),
        ("Discipulado Online", "Integración de nuevos creyentes a grupos de Zoom.", 50),
    ]
    for m in milestones_p2:
        cursor.execute(
            """
            INSERT INTO project_milestones (project_id, title, description, target_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                p2_id,
                m[0],
                m[1],
                (now + datetime.timedelta(days=m[2])).isoformat(),
                now.isoformat(),
            ),
        )

    # Activity 1: Campaña TikTok 'Mi Cambio'
    cursor.execute(
        """
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            p2_id,
            "Campaña TikTok 'Mi Cambio'",
            "Testimonios cortos de transformación de vida.",
            "in_progress",
            "medium",
            4,
            0,
            now.isoformat(),
            now.isoformat(),
        ),
    )
    act3_id = cursor.lastrowid

    # Subtasks for Activity 1
    subtasks_act3 = [
        (
            "Edición de 10 testimonios",
            "Grabar y editar videos de máximo 60 segundos.",
            4,
        ),
        (
            "Gestión de influencers locales",
            "Contactar jóvenes líderes para amplificar el mensaje.",
            1,
        ),
    ]
    for st in subtasks_act3:
        cursor.execute(
            """
            INSERT INTO project_tasks (project_id, parent_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                p2_id,
                act3_id,
                st[0],
                st[1],
                "todo",
                "normal",
                st[2],
                0,
                now.isoformat(),
                now.isoformat(),
            ),
        )

    # Activity 2: Célula Digital (Zoom)
    cursor.execute(
        """
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            p2_id,
            "Célula Digital (Zoom)",
            "Reuniones virtuales de estudio bíblico y acogida.",
            "todo",
            "high",
            3,
            1,
            now.isoformat(),
            now.isoformat(),
        ),
    )
    act4_id = cursor.lastrowid

    # Subtasks for Activity 2
    subtasks_act4 = [
        (
            "Capacitación de anfitriones",
            "Taller sobre manejo de salas y dinámicas online.",
            3,
        ),
        (
            "Diseño de guía de estudio PDF",
            "Material descargable para los participantes.",
            4,
        ),
    ]
    for st in subtasks_act4:
        cursor.execute(
            """
            INSERT INTO project_tasks (project_id, parent_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                p2_id,
                act4_id,
                st[0],
                st[1],
                "todo",
                "medium",
                st[2],
                0,
                now.isoformat(),
                now.isoformat(),
            ),
        )

    conn.commit()
    print(f"Successfully seeded projects, milestones, activities, and tasks.")
    conn.close()


if __name__ == "__main__":
    seed_evangelism_v2()

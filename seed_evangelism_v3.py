import sqlite3
import datetime

def update_evangelism_v3():
    conn = sqlite3.connect('d:\\ccf_v2.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    two_years_later = now + datetime.timedelta(days=730) # Approx 2 years

    # Project 1: Plan de Invasión Urbana 2026 (Responsable: Pastor Pedro - ID 3)
    cursor.execute("""
        INSERT INTO projects (title, description, status, owner_id, color, icon, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Plan de Invasión Urbana (2 Años)", 
          "Visión a largo plazo para transformar el tejido social y espiritual de la ciudad durante los próximos 24 meses.", 
          "active", 3, "#dc2626", "Shield", now.isoformat(), now.isoformat()))
    p1_id = cursor.lastrowid
    
    # Milestones (Levels) spread over 2 years
    milestones_p1 = [
        ("Fase 1: Diagnóstico y Oración", "Primeros 6 meses de preparación.", 180),
        ("Fase 2: Expansión Territorial", "Ejecución masiva en campo.", 365),
        ("Fase 3: Consolidación y Relevo", "Establecimiento de nuevas sedes.", 730)
    ]
    for m in milestones_p1:
        cursor.execute("""
            INSERT INTO project_milestones (project_id, title, description, target_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (p1_id, m[0], m[1], (now + datetime.timedelta(days=m[2])).isoformat(), now.isoformat()))

    # Activities and Tasks with Responsibles
    # Activity 1: Entrenamiento de Líderes (Responsable: Pastor Pedro - ID 3)
    cursor.execute("""
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (p1_id, "Escuela de Evangelismo Continuo", "Capacitación trimestral para nuevos obreros.", "todo", "high", 3, 0, now.isoformat(), now.isoformat()))
    act1_id = cursor.lastrowid
    
    # Subtasks with specific responsibles
    # Assigning to Lider Ana (ID 4) and others
    subtasks_act1 = [
        ("Módulo de Apologética", "Defensa de la fe en contextos urbanos.", 4),
        ("Logística de Sedes", "Organización de espacios físicos.", 1) # Admin
    ]
    for st in subtasks_act1:
        cursor.execute("""
            INSERT INTO project_tasks (project_id, parent_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p1_id, act1_id, st[0], st[1], "todo", "normal", st[2], 0, now.isoformat(), now.isoformat()))


    # Project 2: Redes de Gracia 2.0 (Responsable: Lider Ana - ID 4)
    cursor.execute("""
        INSERT INTO projects (title, description, status, owner_id, color, icon, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Ecosistema Digital de Gracia (2 Años)", 
          "Desarrollo de una plataforma digital robusta para el evangelismo global y discipulado automatizado.", 
          "active", 4, "#2563eb", "Globe", now.isoformat(), now.isoformat()))
    p2_id = cursor.lastrowid
    
    # Milestones over 2 years
    milestones_p2 = [
        ("Desarrollo de Infraestructura", "Creación de la App y plataforma web.", 180),
        ("Lanzamiento Global", "Campañas en 3 continentes.", 365),
        ("Madurez del Ecosistema", "10,000 usuarios activos en discipulado.", 730)
    ]
    for m in milestones_p2:
        cursor.execute("""
            INSERT INTO project_milestones (project_id, title, description, target_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (p2_id, m[0], m[1], (now + datetime.timedelta(days=m[2])).isoformat(), now.isoformat()))

    # Activity: Producción Multimedia (Responsable: Lider Ana - ID 4)
    cursor.execute("""
        INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (p2_id, "Factoría de Contenido Viral", "Producción ininterrumpida de contenido bíblico.", "in_progress", "medium", 4, 0, now.isoformat(), now.isoformat()))
    act2_id = cursor.lastrowid
    
    # Subtasks
    subtasks_act2 = [
        ("Series de Micro-Documentales", "Historias de fe en alta calidad.", 4),
        ("Mantenimiento de Servidores", "Soporte técnico para la plataforma.", 1) # Admin
    ]
    for st in subtasks_act2:
        cursor.execute("""
            INSERT INTO project_tasks (project_id, parent_id, title, description, status, priority, assignee_id, order_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p2_id, act2_id, st[0], st[1], "todo", "medium", st[2], 0, now.isoformat(), now.isoformat()))

    conn.commit()
    print(f"Successfully created 2-year projects with responsibles.")
    conn.close()

if __name__ == "__main__":
    update_evangelism_v3()

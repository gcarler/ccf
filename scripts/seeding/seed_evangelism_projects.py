import sqlite3
import datetime

def seed():
    conn = sqlite3.connect('d:\\ccf_v2.db')
    cursor = conn.cursor()
    
    # Project 1: Campaña de Alcance Barrio Sur
    cursor.execute("""
        INSERT INTO projects (title, description, status, owner_id, color, icon)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("Campaña de Alcance Barrio Sur", "Actividad de evangelismo explosivo y servicio social en el sector sur de la ciudad.", "active", 1, "#4f46e5", "Tent"))
    p1_id = cursor.lastrowid
    
    # Tasks for P1
    tasks_p1 = [
        ("Logística de sonido y tarima", "Coordinar el transporte y montaje del equipo de audio para el evento al aire libre.", "todo", "high", 1),
        ("Preparación de folletos y literatura", "Diseñar e imprimir 500 folletos con el mensaje del evangelio y datos de contacto.", "in_progress", "medium", 227),
        ("Entrenamiento de equipo de acogida", "Capacitar a los voluntarios en cómo abordar a las personas con amor y respeto.", "todo", "medium", 228),
        ("Permisos municipales", "Gestionar los permisos legales para el uso del espacio público.", "done", "high", 1)
    ]
    
    for t in tasks_p1:
        cursor.execute("""
            INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, due_date, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (p1_id, t[0], t[1], t[2], t[3], t[4], (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat(), 0))

    # Project 2: Impacto Universitario
    cursor.execute("""
        INSERT INTO projects (title, description, status, owner_id, color, icon)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("Impacto Universitario", "Misión enfocada en estudiantes de la Universidad Nacional para compartir principios del Reino.", "active", 227, "#06b6d4", "GraduationCap"))
    p2_id = cursor.lastrowid
    
    # Tasks for P2
    tasks_p2 = [
        ("Reserva de auditorio", "Asegurar un espacio dentro del campus para la charla principal.", "todo", "medium", 227),
        ("Invitaciones en redes sociales", "Crear campaña visual en Instagram y TikTok para atraer jóvenes.", "in_progress", "low", 228),
        ("Selección de oradores", "Confirmar a los líderes que compartirán su testimonio profesional.", "todo", "medium", 1)
    ]
    
    for t in tasks_p2:
        cursor.execute("""
            INSERT INTO project_tasks (project_id, title, description, status, priority, assignee_id, due_date, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (p2_id, t[0], t[1], t[2], t[3], t[4], (datetime.datetime.now() + datetime.timedelta(days=14)).isoformat(), 0))

    conn.commit()
    print(f"Successfully seeded {cursor.rowcount} projects and their tasks.")
    conn.close()

if __name__ == "__main__":
    seed()

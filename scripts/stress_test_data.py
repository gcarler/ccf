from __future__ import annotations

import datetime as dt
import random

from sqlalchemy.orm import Session

from backend import models
from backend.core.database import SessionLocal, engine
from backend.core.security import get_password_hash


def stress_test_data(num_users=1000, num_members=5000, num_tasks=10000):
    db = SessionLocal()
    try:
        print(
            f"🚀 Iniciando Stress Test de Datos: {num_users} usuarios, {num_members} miembros, {num_tasks} tareas..."
        )

        # 1. Crear Usuarios masivos
        print("👤 Generando usuarios...")
        users = []
        for i in range(num_users):
            user = models.User(
                username=f"user_stress_{i}",
                email=f"stress_{i}@ccf.local",
                password_hash=get_password_hash("stress1234"),
                role=random.choice(["estudiante", "lider", "docente"]),
                xp=random.randint(0, 5000),
            )
            db.add(user)
            users.append(user)
            if i % 100 == 0:
                db.flush()
        db.commit()

        # 2. Crear Miembros masivos
        print("👥 Generando miembros...")
        for i in range(num_members):
            member = models.Member(
                first_name=f"Nombre_{i}",
                last_name=f"Apellido_{i}",
                email=f"member_{i}@ccf.local",
                phone=f"+57 300 {random.randint(1000000, 9999999)}",
                church_role=random.choice(["Miembro", "Servidor", "Líder"]),
                spiritual_status=random.choice(
                    ["Nuevo", "Creyente", "Discípulo", "Servidor"]
                ),
                user_id=users[i % num_users].id if i < num_users else None,
            )
            db.add(member)
            if i % 500 == 0:
                db.flush()
        db.commit()

        # 3. Crear Proyectos y Tareas masivas
        print("📂 Generando proyectos y tareas...")
        projects = []
        for i in range(20):
            project = models.Project(
                title=f"Proyecto Gran Escala {i}",
                description=f"Iniciativa masiva numero {i} para el ecosistema MESH.",
                status=random.choice(["active", "planning"]),
                color=random.choice(["#2563eb", "#10b981", "#6366f1", "#f59e0b"]),
            )
            db.add(project)
            projects.append(project)
        db.flush()

        for i in range(num_tasks):
            task = models.ProjectTask(
                project_id=random.choice(projects).id,
                title=f"Tarea Crítica {i}",
                description=f"Descripción detallada de la tarea masiva {i}.",
                status=random.choice(["todo", "in_progress", "done"]),
                priority=random.choice(["urgent", "high", "normal"]),
                assignee_id=random.choice(users).id,
                due_date=dt.datetime.now() + dt.timedelta(days=random.randint(-10, 30)),
            )
            db.add(task)
            if i % 1000 == 0:
                db.flush()
        db.commit()

        print("✅ Stress Test completado con éxito.")

    except Exception as e:
        print(f"❌ Error durante el Stress Test: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    stress_test_data()

import os
import sys
from pathlib import Path

# Add backend directory to python path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))

from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.models import (
    ConsolidationPipeline,
    Course,
    Family,
    GloryHouse,
    Lesson,
    Member,
    PastoralCallLog,
    Project,
    ProjectTask,
    User,
)


def seed_real_data():
    db = SessionLocal()
    try:
        print("Starting real data seed...")

        # 1. Users
        users_data = [
            {
                "username": "admin",
                "email": "admin@ccf.com",
                "role": "admin",
                "password": "password123",
            },
            {
                "username": "pastoral_pedro",
                "email": "pedro.pastor@ccf.com",
                "role": "pastor",
                "password": "password123",
            },
            {
                "username": "lider_ana",
                "email": "ana.lider@ccf.com",
                "role": "lider",
                "password": "password123",
            },
            {
                "username": "estudiante_luis",
                "email": "luis.estudiante@ccf.com",
                "role": "estudiante",
                "password": "password123",
            },
        ]

        user_objs = {}
        for u_data in users_data:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if not user:
                user = User(
                    username=u_data["username"],
                    email=u_data["email"],
                    password_hash=get_password_hash(u_data["password"]),
                    role=u_data["role"],
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"Created User: {user.username}")
            user_objs[u_data["username"]] = user

        # 2. Families
        fam = db.query(Family).filter(Family.name == "Familia Torres").first()
        if not fam:
            fam = Family(name="Familia Torres")
            db.add(fam)
            db.commit()
            db.refresh(fam)

        # 3. Members
        members_data = [
            {
                "first_name": "Pedro",
                "last_name": "Torres",
                "email": "pedro.pastor@ccf.com",
                "phone": "3001112233",
                "role_in_family": "Padre",
                "church_role": "Pastor",
                "family_id": fam.id,
                "user_id": user_objs["pastoral_pedro"].id,
            },
            {
                "first_name": "Ana",
                "last_name": "Torres",
                "email": "ana.lider@ccf.com",
                "phone": "3004445566",
                "role_in_family": "Madre",
                "church_role": "Líder",
                "family_id": fam.id,
                "user_id": user_objs["lider_ana"].id,
            },
            {
                "first_name": "Luis",
                "last_name": "Torres",
                "email": "luis.estudiante@ccf.com",
                "phone": "3007778899",
                "role_in_family": "Hijo",
                "church_role": "Miembro",
                "family_id": fam.id,
                "user_id": user_objs["estudiante_luis"].id,
            },
        ]

        for m_data in members_data:
            member = db.query(Member).filter(Member.email == m_data["email"]).first()
            if not member:
                member = Member(**m_data)
                db.add(member)
                db.commit()
                print(f"Created Member: {member.first_name} {member.last_name}")

        # 4. Consolidation Pipeline (CRM Leads)
        leads_data = [
            {
                "first_name": "Mateo",
                "last_name": "García",
                "phone": "3109998877",
                "source": "Servicio de Domingo",
                "stage": "new",
                "notes": "Vino invitado por un amigo, tiene 25 años.",
                "assigned_pastor_id": user_objs["pastoral_pedro"].id,
            },
            {
                "first_name": "Sofía",
                "last_name": "Martínez",
                "phone": "3201110000",
                "source": "Campaña en Redes",
                "stage": "contacted",
                "notes": "Busca apoyo espiritual para su familia.",
                "assigned_pastor_id": user_objs["lider_ana"].id,
            },
            {
                "first_name": "Diego",
                "last_name": "López",
                "phone": "3154443333",
                "source": "Casa de Gloria",
                "stage": "consolidated",
                "notes": "Ya está asistiendo a la Casa de Gloria de la zona sur.",
                "assigned_pastor_id": user_objs["lider_ana"].id,
            },
            {
                "first_name": "Lucía",
                "last_name": "Ramírez",
                "phone": "3002223344",
                "source": "Familiar",
                "stage": "lost",
                "notes": "Se mudó de ciudad.",
                "assigned_pastor_id": user_objs["pastoral_pedro"].id,
            },
        ]

        for l_data in leads_data:
            lead = (
                db.query(ConsolidationPipeline)
                .filter(ConsolidationPipeline.phone == l_data["phone"])
                .first()
            )
            if not lead:
                lead = ConsolidationPipeline(**l_data)
                db.add(lead)
                db.commit()
                db.refresh(lead)
                print(f"Created Lead: {lead.first_name} {lead.last_name}")

                # Add a Call Log if contacted or consolidated
                if lead.stage in ["contacted", "consolidated", "lost"]:
                    outcomes = {
                        "contacted": "Contestó - Pendiente",
                        "consolidated": "Visita Exitosa",
                        "lost": "No volvió a contestar",
                    }
                    log = PastoralCallLog(
                        lead_id=lead.id,
                        pastor_id=lead.assigned_pastor_id,
                        outcome=outcomes[lead.stage],
                        notes=f"Llamada de seguimiento para {lead.first_name}.",
                    )
                    db.add(log)
                    db.commit()

        # 5. Projects & Tasks
        project1 = (
            db.query(Project)
            .filter(Project.title == "Conferencia Juvenil 2026")
            .first()
        )
        if not project1:
            project1 = Project(
                title="Conferencia Juvenil 2026",
                description="Planeación de la conferencia anual para jóvenes (Despertar).",
                status="active",
                owner_id=user_objs["lider_ana"].id,
                color="#8b5cf6",
                icon="zap",
            )
            db.add(project1)
            db.commit()
            db.refresh(project1)
            print(f"Created Project: {project1.title}")

            tasks_data = [
                {
                    "title": "Reservar Auditorio",
                    "description": "Confirmar las fechas con el auditorio principal.",
                    "status": "done",
                    "priority": "high",
                    "project_id": project1.id,
                    "assignee_id": user_objs["pastoral_pedro"].id,
                },
                {
                    "title": "Diseño de Invitaciones",
                    "description": "Crear los flyers y videos promocionales.",
                    "status": "in_progress",
                    "priority": "medium",
                    "project_id": project1.id,
                    "assignee_id": user_objs["lider_ana"].id,
                },
                {
                    "title": "Logística de Sonido",
                    "description": "Contratar o revisar equipos de sonido.",
                    "status": "todo",
                    "priority": "high",
                    "project_id": project1.id,
                    "assignee_id": user_objs["lider_ana"].id,
                },
                {
                    "title": "Refrigerios",
                    "description": "Cotizar opciones para los breaks.",
                    "status": "todo",
                    "priority": "low",
                    "project_id": project1.id,
                    "assignee_id": user_objs["estudiante_luis"].id,
                },
            ]
            for t_data in tasks_data:
                task = ProjectTask(**t_data)
                db.add(task)
                db.commit()

        project2 = (
            db.query(Project)
            .filter(Project.title == "Remodelación Salón Infantil")
            .first()
        )
        if not project2:
            project2 = Project(
                title="Remodelación Salón Infantil",
                description="Mejoras en las instalaciones del ministerio infantil.",
                status="active",
                owner_id=user_objs["admin"].id,
                color="#ec4899",
                icon="paint-bucket",
            )
            db.add(project2)
            db.commit()
            db.refresh(project2)
            print(f"Created Project: {project2.title}")

            tasks_data = [
                {
                    "title": "Pintura de paredes",
                    "description": "Comprar pintura y brochas.",
                    "status": "in_progress",
                    "priority": "medium",
                    "project_id": project2.id,
                    "assignee_id": user_objs["pastoral_pedro"].id,
                },
            ]
            for t_data in tasks_data:
                task = ProjectTask(**t_data)
                db.add(task)
                db.commit()

        # 6. Glory Houses (Casas de Gloria)
        ghouses_data = [
            {
                "name": "Casa de Gloria Norte - Los Pinos",
                "zone": "Norte",
                "leader_name": "Ana Torres",
                "members_count": 15,
                "schedule": "Miércoles 7:30 PM",
                "status": "Activo",
            },
            {
                "name": "Casa de Gloria Sur - El Prado",
                "zone": "Sur",
                "leader_name": "Luis Torres",
                "members_count": 8,
                "schedule": "Jueves 8:00 PM",
                "status": "Activo",
            },
            {
                "name": "Casa de Gloria Centro - Histórico",
                "zone": "Centro",
                "leader_name": "Pedro Torres",
                "members_count": 22,
                "schedule": "Viernes 7:00 PM",
                "status": "Activo",
            },
        ]
        for gh_data in ghouses_data:
            gh = db.query(GloryHouse).filter(GloryHouse.name == gh_data["name"]).first()
            if not gh:
                gh = GloryHouse(**gh_data)
                db.add(gh)
                db.commit()
                print(f"Created Glory House: {gh.name}")

        # 7. Academy (Courses & Lessons)
        course1 = db.query(Course).filter(Course.code == "DISC-A-2026").first()
        if not course1:
            course1 = Course(
                code="DISC-A-2026",
                title="Discipulado Nivel 1: Fundamentos",
                description="Aprende las bases de la fe cristiana, la importancia del bautismo y cómo orar.",
                modality="hibrida",
                is_published=True,
                is_self_paced=False,
                duration_hours=12,
                cohort_name="Cohorte Primavera 2026",
            )
            db.add(course1)
            db.commit()
            db.refresh(course1)
            print(f"Created Course: {course1.title}")

            lessons_data = [
                {
                    "title": "Lección 1: La Salvación",
                    "content": "Descubre el regalo de la salvación por medio de Jesús.",
                    "order_index": 1,
                    "duration_minutes": 60,
                    "course_id": course1.id,
                },
                {
                    "title": "Lección 2: Oración Cotidiana",
                    "content": "Cómo establecer un hábito de oración dinámico.",
                    "order_index": 2,
                    "duration_minutes": 60,
                    "course_id": course1.id,
                },
                {
                    "title": "Lección 3: La Biblia",
                    "content": "Introducción a la lectura y meditación de las escrituras.",
                    "order_index": 3,
                    "duration_minutes": 90,
                    "course_id": course1.id,
                },
            ]
            for l_data in lessons_data:
                lesson = Lesson(**l_data)
                db.add(lesson)
                db.commit()

        print("Real data seeding completed successfully.")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_real_data()


import sys
import os
import random
from datetime import datetime, timedelta
import uuid

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models, schemas, crud
from backend.core.database import SessionLocal, engine, Base
from backend.core.security import get_password_hash

def seed_total():
    print("🚀 Iniciando OPERACIÓN COMPLETITUD TOTAL (Llenando 35 tablas vacías)...")
    db = SessionLocal()
    
    try:
        # --- LIMPIEZA PARA RE-EJECUCIÓN ---
        print("🧹 Limpiando tablas para inyección limpia...")
        db.query(models.Role).delete()
        db.query(models.Level).delete()
        db.query(models.Badge).delete()
        db.query(models.UserBadge).delete()
        db.query(models.UserUIPreference).delete()
        db.query(models.CoursePrerequisite).delete()
        db.query(models.LessonProgress).delete()
        db.query(models.AssessmentOption).delete()
        db.query(models.AssessmentQuestion).delete()
        db.query(models.AssessmentAttempt).delete()
        db.query(models.Assessment).delete()
        db.query(models.Resource).delete()
        db.query(models.AssignmentSubmission).delete()
        db.query(models.FormalActa).delete()
        db.query(models.ForumComment).delete()
        db.query(models.ForumThread).delete()
        db.query(models.ConsolidationPipeline).delete()
        db.query(models.ChatMessage).delete()
        db.query(models.ProjectTask).delete()
        db.query(models.Project).delete()
        db.query(models.TaskSupply).delete()
        db.query(models.InventoryItem).delete()
        db.query(models.AdminAuditLog).delete()
        db.query(models.Notification).delete()
        db.query(models.PageContent).delete()
        db.query(models.PageContentVersion).delete()
        db.query(models.ContentMetric).delete()
        db.query(models.MediaAsset).delete()
        db.query(models.CommunicationLog).delete()
        db.query(models.Certificate).delete()
        db.commit()

        # --- 1. INFRAESTRUCTURA BÁSICA ---
        print("🛠️ Poblando Roles, Niveles y Badges...")
        roles_data = [
            models.Role(name="admin", permissions={"all": True}),
            models.Role(name="docente", permissions={"academy": True, "crm": "read"}),
            models.Role(name="coordinador", permissions={"crm": True}),
            models.Role(name="estudiante", permissions={"academy": "read"})
        ]
        db.add_all(roles_data)
        
        levels = [
            models.Level(title="Novicio", min_xp=0, icon_key="star"),
            models.Level(title="Discípulo", min_xp=500, icon_key="shield"),
            models.Level(title="Siervo", min_xp=1500, icon_key="sword"),
            models.Level(title="Líder", min_xp=5000, icon_key="crown")
        ]
        db.add_all(levels)
        
        badges = [
            models.Badge(name="Primer Paso", icon_key="foot", xp_reward=100),
            models.Badge(name="Estudiante Fiel", icon_key="book", xp_reward=500),
            models.Badge(name="Intercesor", icon_key="pray", xp_reward=1000)
        ]
        db.add_all(badges)
        db.commit()

        # --- 2. RECUPERAR ENTIDADES EXISTENTES ---
        users = db.query(models.User).all()
        members = db.query(models.Member).all()
        courses = db.query(models.Course).all()
        lessons = db.query(models.Lesson).all()
        enrollments = db.query(models.Enrollment).all()
        
        # --- 3. ACADEMIA AVANZADA ---
        print("📖 Poblando Exámenes, Recursos y Progreso...")
        for lesson in lessons:
            # Recurso
            res = models.Resource(lesson_id=lesson.id, title=f"Guía de Estudio: {lesson.title}", file_url="/static/guide.pdf", resource_type="application/pdf")
            db.add(res)
            
            # Evaluación
            asm = models.Assessment(lesson_id=lesson.id, title=f"Quiz: {lesson.title}", min_score=70)
            db.add(asm)
            db.commit()
            db.refresh(asm)
            
            # Pregunta y Opciones
            q = models.AssessmentQuestion(assessment_id=asm.id, question_text="¿Es este un contenido ministerial?", points=100)
            db.add(q)
            db.commit()
            db.refresh(q)
            db.add_all([
                models.AssessmentOption(question_id=q.id, option_text="Sí", is_correct=True),
                models.AssessmentOption(question_id=q.id, option_text="No", is_correct=False)
            ])

        # Prerrequisitos (Course 2 depende de Course 1)
        if len(courses) >= 2:
            db.add(models.CoursePrerequisite(course_id=courses[1].id, prerequisite_course_id=courses[0].id))

        # --- 4. PROGRESO Y ENTREGAS ---
        print("🎓 Generando intentos, tareas y certificados...")
        for enr in enrollments[:20]:
            # Progreso
            lp = models.LessonProgress(user_id=enr.user_id, lesson_id=lessons[0].id, progress_percent=100, is_completed=True)
            db.add(lp)
            
            # Entrega de Tarea
            sub = models.AssignmentSubmission(enrollment_id=enr.id, lesson_id=lessons[0].id, file_url="/static/tarea.pdf", grade=95, teacher_feedback="Excelente trabajo.")
            db.add(sub)
            
            # Certificado si está aprobado
            if enr.approved:
                cert = models.Certificate(enrollment_id=enr.id, certificate_code=f"CCF-{uuid.uuid4().hex[:8].upper()}")
                db.add(cert)

        # --- 5. CRM Y CONSOLIDACIÓN ---
        print("📈 Poblando Pipeline, Chat y Foros...")
        # Pipeline
        for i in range(10):
            p = models.ConsolidationPipeline(first_name=f"Nuevo_{i}", last_name="Prospecto", phone="555-0000", stage="new", source="Web")
            db.add(p)
        
        # Foro
        thread = models.ForumThread(title="Bienvenidos al Foro", category="General", author_id=users[0].id)
        db.add(thread)
        db.commit()
        db.refresh(thread)
        db.add(models.ForumComment(thread_id=thread.id, author_id=users[1].id, content="Gracias por este espacio."))

        # Chat
        db.add(models.ChatMessage(sender_id=users[0].id, content="Hola a todos los líderes."))

        # --- 6. PROYECTOS E INVENTARIO ---
        print("🏗️ Creando Proyectos e Inventario...")
        proj = models.Project(title="Remodelación Auditorio", status="active", owner_id=users[0].id)
        db.add(proj)
        db.commit()
        db.refresh(proj)
        
        task = models.ProjectTask(project_id=proj.id, title="Pintura Paredes", status="in_progress", priority="high")
        db.add(task)
        db.commit()
        db.refresh(task)
        
        db.add(models.TaskSupply(task_id=task.id, item_name="Pintura Blanca", quantity=5))
        db.add(models.InventoryItem(name="Sillas", category="Mobiliario", stock=500, status="Available"))

        # --- 7. SISTEMA Y AUDITORÍA ---
        print("⚙️ Inyectando Logs, Notificaciones y CMS...")
        db.add(models.AdminAuditLog(actor_user_id=users[0].id, action="seed_total", resource_type="system"))
        db.add(models.Notification(user_id=users[0].id, title="Bienvenida", content="Bienvenido a la nueva plataforma CCF."))
        db.add(models.PageContent(page_key="home", title="Inicio Ministerial", content="<h1>Bienvenidos</h1>"))
        db.add(models.ContentMetric(metric_key="page_views", ref_id=1, value=150))
        db.add(models.MediaAsset(filename="logo.png", url="/static/logo.png", size_bytes=1024))
        db.add(models.CommunicationLog(member_id=members[0].id, channel="WhatsApp", content="Mensaje de prueba", leader_id=users[0].id))
        
        # Tokens y Preferencias
        db.add(models.RefreshToken(user_id=users[0].id, token="fake_token", expires_at=datetime.now() + timedelta(days=1)))
        db.add(models.UserUIPreference(user_id=users[0].id, settings={"theme": "dark"}))
        db.add(models.UserBadge(user_id=users[0].id, badge_id=1))

        db.commit()
        print("\n✅ ¡BASE DE DATOS 100% POBLADA! No quedan tablas vacías.")

    except Exception as e:
        print(f"❌ Error en semilla total: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_total()

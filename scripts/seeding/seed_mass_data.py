import os
import sys
import uuid
from datetime import datetime, timedelta

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import crud, models, schemas
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.management.schema import upgrade_with_optional_bootstrap


def seed_everything():
    print("🌟 Iniciando Inyección Masiva de Datos Reales (CRM + Academia + Staff)...")

    # Aplicar migraciones y bootstrap explícito si aún hay tablas no migradas.
    upgrade_with_optional_bootstrap()
    db = SessionLocal()

    try:
        # --- 1. LIMPIEZA TOTAL ---
        print("🧹 Limpiando base de datos para una semilla fresca...")
        db.query(models.AssessmentOption).delete()
        db.query(models.AssessmentQuestion).delete()
        db.query(models.AssessmentAttempt).delete()
        db.query(models.Assessment).delete()
        db.query(models.LessonProgress).delete()
        db.query(models.Lesson).delete()
        db.query(models.Enrollment).delete()
        db.query(models.CoursePrerequisite).delete()
        db.query(models.Course).delete()
        db.query(models.EventAttendance).delete()
        db.query(models.CrmEvent).delete()
        db.query(models.CounselingTicket).delete()
        db.query(models.PrayerRequest).delete()
        db.query(models.CommunicationLog).delete()
        db.query(models.ConsolidationPipeline).delete()
        db.query(models.Member).delete()
        db.query(models.GrupoEvangelismo).delete()
        db.query(models.Family).delete()
        db.query(models.User).delete()
        db.commit()

        # --- 2. STAFF MINISTERIAL ---
        print("👥 Creando Staff Ministerial...")
        pwd = get_password_hash("admin123")

        admin = models.User(
            username="admin_ccf", email="admin@ccf.la", password_hash=pwd, role="admin"
        )
        pastor = models.User(
            username="pastor_juan",
            email="juan@ccf.la",
            password_hash=pwd,
            role="docente",
        )
        pastora = models.User(
            username="pastora_elena",
            email="elena@ccf.la",
            password_hash=pwd,
            role="coordinador",
        )
        estudiante = models.User(
            username="estudiante_demo",
            email="demo@ccf.la",
            password_hash=pwd,
            role="estudiante",
        )

        db.add_all([admin, pastor, pastora, estudiante])
        db.commit()
        db.refresh(admin)
        db.refresh(pastor)
        db.refresh(estudiante)

        # --- 3. FAMILIAS Y MIEMBROS (CRM) ---
        print("🏠 Creando Núcleos Familiares...")
        fam1 = models.Family(name="Familia Rodríguez")
        fam2 = models.Family(name="Familia García")
        db.add_all([fam1, fam2])
        db.commit()
        db.refresh(fam1)
        db.refresh(fam2)

        m1 = models.Member(
            first_name="Juan",
            last_name="Rodríguez",
            email="juan@ccf.la",
            family_id=fam1.id,
            church_role="Pastor",
            user_id=pastor.id,
        )
        m2 = models.Member(
            first_name="Elena",
            last_name="García",
            email="elena@ccf.la",
            family_id=fam2.id,
            church_role="Líder",
            user_id=pastora.id,
        )
        m3 = models.Member(
            first_name="Carlos",
            last_name="Demo",
            email="demo@ccf.la",
            family_id=fam1.id,
            church_role="Miembro",
            user_id=estudiante.id,
        )

        db.add_all([m1, m2, m3])
        db.commit()

        # --- 4. CASAS DE GLORIA (GRUPOS PEQUEÑOS) ---
        print("🏘️ Configurando Casas de Gloria...")
        gh1 = models.GrupoEvangelismo(
            name="Bethel - Norte",
            zone="Norte",
            leader_name="Juan Rodríguez",
            members_count=12,
            schedule="Jueves 7:00 PM",
        )
        gh2 = models.GrupoEvangelismo(
            name="Sion - Centro",
            zone="Centro",
            leader_name="Elena García",
            members_count=8,
            schedule="Martes 6:30 PM",
        )
        db.add_all([gh1, gh2])
        db.commit()

        # --- 5. PIPELINE DE CONSOLIDACIÓN (NUEVOS) ---
        print("📈 Poblando Pipeline de Consolidación...")
        p1 = models.ConsolidationPipeline(
            first_name="Ricardo",
            last_name="Mendoza",
            phone="555-0101",
            source="Invitación",
            stage="new",
        )
        p2 = models.ConsolidationPipeline(
            first_name="Sofía",
            last_name="Castro",
            phone="555-0202",
            source="Facebook",
            stage="contacted",
            assigned_pastor_id=pastor.id,
        )
        db.add_all([p1, p2])
        db.commit()

        # --- 6. EVENTOS Y ASISTENCIA ---
        print("🗓️ Creando Eventos Ministeriales...")
        e1 = models.CrmEvent(
            title="Culto de Celebración",
            description="Servicio principal dominical",
            event_date=datetime.now() + timedelta(days=2),
            location="Auditorio Principal",
        )
        e2 = models.CrmEvent(
            title="Noche de Jóvenes",
            description="Encuentro generacional",
            event_date=datetime.now() + timedelta(days=5),
            location="Salón de Usos Múltiples",
        )
        db.add_all([e1, e2])
        db.commit()
        db.refresh(e1)

        # Registro de asistencia simulado
        att = models.EventAttendance(event_id=e1.id, member_id=m3.id, status="present")
        db.add(att)

        # --- 7. CONSEJERÍA Y ORACIÓN ---
        print("🙏 Registrando Peticiones de Oración y Consejería...")
        pr1 = models.PrayerRequest(
            requester_name="Carlos Demo",
            request_text="Petición por la salud de mi abuela en cirugía.",
            is_public=True,
            status="praying",
        )
        pr2 = models.PrayerRequest(
            requester_name="Elena García",
            request_text="Agradecimiento por nuevo empleo.",
            is_public=False,
            status="answered",
        )

        ct1 = models.CounselingTicket(
            member_id=m3.id,
            pastor_id=pastor.id,
            subject="Orientación Familiar",
            notes="Se requiere seguimiento tras la primera charla.",
            status="in_progress",
        )

        db.add_all([pr1, pr2, ct1])
        db.commit()

        # --- 8. ACADEMIA (CURSOS Y EXÁMENES) ---
        print("🎓 Configurando Estructura Académica Avanzada...")
        c1 = models.Course(
            code="FUND-01",
            title="Fundamentos I: Vida Nueva",
            modality="formal",
            is_published=True,
        )
        c2 = models.Course(
            code="TEOL-02",
            title="Teología II: Doctrina",
            modality="formal",
            is_published=True,
        )
        db.add_all([c1, c2])
        db.commit()
        db.refresh(c1)
        db.refresh(c2)

        # Prerrequisito
        db.add(models.CoursePrerequisite(course_id=c2.id, prerequisite_course_id=c1.id))

        # Lección y Examen para Fundamentos I
        l1 = models.Lesson(
            course_id=c1.id,
            title="Introducción a la Gracia",
            content="Contenido sobre la gracia divina...",
            order_index=1,
        )
        db.add(l1)
        db.commit()
        db.refresh(l1)

        assessment = models.Assessment(
            lesson_id=l1.id, title="Examen de Gracia", min_score=70
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        q1 = models.AssessmentQuestion(
            assessment_id=assessment.id, question_text="¿Qué es la gracia?", points=50
        )
        db.add(q1)
        db.commit()
        db.refresh(q1)

        db.add_all(
            [
                models.AssessmentOption(
                    question_id=q1.id,
                    option_text="Un favor inmerecido",
                    is_correct=True,
                ),
                models.AssessmentOption(
                    question_id=q1.id,
                    option_text="Un premio por obras",
                    is_correct=False,
                ),
            ]
        )

        db.commit()

        print("\n✅ ¡INYECCIÓN MASIVA COMPLETADA CON ÉXITO!")
        print(
            f"📊 Resumen: 4 Usuarios, 3 Miembros, 2 Familias, 2 Casas, 2 Eventos, 2 Cursos."
        )
        print("La plataforma está lista para ser navegada con datos 100% realistas.")

    except Exception as e:
        print(f"❌ Error durante el seeding: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_everything()

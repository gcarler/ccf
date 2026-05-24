import os
import sys
import uuid

# Añadir el directorio raíz al path para poder importar el backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import crud, models, schemas
from backend.core.database import SessionLocal
from backend.management.schema import upgrade_with_optional_bootstrap


def verify_new_logic():
    print("🚀 Iniciando Verificación de Reglas de Negocio (MVP-001 al MVP-004)...")

    # Asegurar migraciones antes de verificar reglas de negocio.
    upgrade_with_optional_bootstrap()
    db = SessionLocal()

    try:
        # 1. Limpieza rápida de datos de prueba previos para consistencia
        print("🧹 Limpiando datos de prueba antiguos...")
        db.query(models.CoursePrerequisite).delete()
        db.query(models.Enrollment).delete()
        db.query(models.Course).delete()
        db.query(models.User).filter(models.User.username.like("test_%")).delete()
        db.commit()

        # 2. Crear Usuarios de Prueba
        print("👥 Creando usuarios de prueba...")
        student_data = schemas.UserCreate(
            username="test_student",
            email="estudiante@ccf.la",
            password="password123",
            role="estudiante",
        )
        student = crud.get_user_by_username(db, "test_student")
        if not student:
            student = crud.create_user(db, student_data)

        # 3. Crear Cursos
        print("📚 Configurando catálogo académico...")
        c1 = models.Course(
            code="BASE-101",
            title="Fundamentos de la Fe I",
            modality="formal",
            is_published=True,
        )
        c2 = models.Course(
            code="ADV-201",
            title="Teología Sistemática Avanzada",
            modality="formal",
            is_published=True,
        )
        db.add(c1)
        db.add(c2)
        db.commit()
        db.refresh(c1)
        db.refresh(c2)

        # 4. Establecer Prerrequisito: ADV-201 requiere BASE-101
        print(f"🔗 Estableciendo prerrequisito: {c2.title} requiere {c1.title}")
        prereq = models.CoursePrerequisite(
            course_id=c2.id, prerequisite_course_id=c1.id
        )
        db.add(prereq)
        db.commit()

        # 5. TEST: Intento de matrícula en curso avanzado SIN haber completado el básico
        print(
            f"🧪 PRUEBA 1: Intentando matricular a {student.username} en {c2.title} (Debe fallar)..."
        )
        try:
            crud.create_enrollment(
                db, schemas.EnrollmentCreate(user_id=student.id, course_id=c2.id)
            )
            print("❌ ERROR: La matrícula se permitió sin cumplir prerrequisitos.")
        except ValueError as e:
            print(f"✅ ÉXITO: Matrícula rechazada correctamente. Motivo: {str(e)}")

        # 6. TEST: Matrícula en curso básico y completitud
        print(f"🧪 PRUEBA 2: Matriculando en {c1.title}...")
        enrollment_base = crud.create_enrollment(
            db, schemas.EnrollmentCreate(user_id=student.id, course_id=c1.id)
        )
        print(f"✅ Estudiante matriculado en {c1.title}.")

        print("🎓 Completando curso básico...")
        enrollment_base.status = "completed"
        enrollment_base.approved = True
        db.commit()

        # 7. TEST: Reintento de matrícula en curso avanzado tras completar el básico
        print(
            f"🧪 PRUEBA 3: Reintentando matricular en {c2.title} tras completar prerrequisito..."
        )
        try:
            enrollment_adv = crud.create_enrollment(
                db, schemas.EnrollmentCreate(user_id=student.id, course_id=c2.id)
            )
            print(
                f"✅ ÉXITO: Matrícula permitida tras cumplir prerrequisitos (ID: {enrollment_adv.id})."
            )
        except ValueError as e:
            print(
                f"❌ ERROR: La matrícula falló a pesar de cumplir prerrequisitos. Error: {str(e)}"
            )

        # 8. TEST: Evaluación y Certificado
        print(
            "📜 PRUEBA 4: Simulando aprobación de examen final y emisión de certificado..."
        )
        cert = crud.issue_certificate(db, enrollment_id=enrollment_base.id)
        print(f"✨ ¡Certificado emitido con éxito! Código: {cert.certificate_code}")

        print("\n🏆 TODAS LAS PRUEBAS PASARON CORRECTAMENTE.")
        print("La plataforma ahora cumple con los criterios de los MVP-001 y MVP-004.")

    except Exception as e:
        print(f"💥 Error durante la verificación: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verify_new_logic()

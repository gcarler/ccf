import os
import sys
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend import models

def seed_curriculum():
    db: Session = SessionLocal()
    try:
        print("Iniciando carga de currículo ministerial...")

        # 1. CURSO FORMAL: Escuela de Líderes - Nivel 1
        el1 = db.query(models.Course).filter(models.Course.code == "EL-N1").first()
        if not el1:
            el1 = models.Course(
                code="EL-N1",
                title="Escuela de Líderes: Fundamentos",
                description="Primer nivel de formación ministerial enfocado en el carácter del siervo y la visión de la casa.",
                modality="formal",
                certificate_type="Diplomado",
                xp_per_lesson=50,
                is_published=True
            )
            db.add(el1)
            db.flush()

            # Lecciones EL-N1
            lessons = [
                ("La Visión del Faro", "Entendiendo nuestro propósito como comunidad.", 1),
                ("Carácter Cristiano", "La base interna del liderazgo.", 2),
                ("Intercesión y Guerra Espiritual", "Nuestras armas no son carnales.", 3),
                ("El Poder del Servicio", "Siguiendo el ejemplo de Cristo.", 4)
            ]
            for title, desc, idx in lessons:
                lesson = models.Lesson(
                    course_id=el1.id,
                    title=title,
                    content=desc,
                    content_type="video",
                    order_index=idx,
                    duration_minutes=45
                )
                db.add(lesson)

        # 2. CURSO NO FORMAL: Vida Devocional
        vd = db.query(models.Course).filter(models.Course.code == "NF-VD").first()
        if not vd:
            vd = models.Course(
                code="NF-VD",
                title="Vida Devocional Efectiva",
                description="Aprende a cultivar una relación diaria y profunda con Dios a través de la oración y la palabra.",
                modality="no_formal",
                certificate_type="Microcertificado",
                xp_per_lesson=30,
                is_published=True
            )
            db.add(vd)
            db.flush()

            # Lecciones Vida Devocional
            lessons_vd = [
                ("El Altar Familiar", "Cómo levantar oración en casa.", 1),
                ("Métodos de Estudio Bíblico", "Herramientas para profundizar.", 2),
                ("La Voz de Dios", "Aprendiendo a escuchar al Espíritu Santo.", 3)
            ]
            for title, desc, idx in lessons_vd:
                db.add(models.Lesson(
                    course_id=vd.id,
                    title=title,
                    content=desc,
                    content_type="pdf",
                    order_index=idx,
                    duration_minutes=30
                ))

        # 3. CURSO NO FORMAL: Finanzas del Reino
        fr = db.query(models.Course).filter(models.Course.code == "NF-FR").first()
        if not fr:
            fr = models.Course(
                code="NF-FR",
                title="Mayordomía y Finanzas",
                description="Principios bíblicos para la administración del recurso que Dios pone en tus manos.",
                modality="no_formal",
                certificate_type="Microcertificado",
                xp_per_lesson=30,
                is_published=True
            )
            db.add(fr)
            db.flush()

            db.add(models.Lesson(
                course_id=fr.id,
                title="Diezmos y Ofrendas",
                content="La generosidad como llave de bendición.",
                content_type="video",
                order_index=1,
                duration_minutes=60
            ))

        db.commit()
        print("✅ Currículo cargado exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante la carga: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure backend is in path
    sys.path.append(os.getcwd())
    seed_curriculum()

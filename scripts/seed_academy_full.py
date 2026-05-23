import datetime as dt

from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.models import Course, Lesson, User


def seed_complete_academy():
    db = SessionLocal()
    try:
        # Asegurar que el usuario admin existe para asociar cosas si es necesario
        admin = db.query(User).filter(User.username == "admin").first()

        # Limpiar cursos previos para evitar duplicados
        db.query(Lesson).delete()
        db.query(Course).delete()
        db.commit()

        courses_data = [
            {
                "code": "DISC-1",
                "title": "Discipulado Nivel 1: Fundamentos de la Fe",
                "description": "Explora los pilares básicos del cristianismo y fortalece tu relación inicial con Dios.",
                "modality": "hibrida",
                "duration_hours": 20,
                "lessons": [
                    {
                        "title": "La Salvación y el Arrepentimiento",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "La Importancia de la Biblia",
                        "type": "pdf",
                        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                    },
                    {
                        "title": "La Oración como Estilo de Vida",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "Entendiendo el Bautismo",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {"title": "Evaluación de Fundamentos", "type": "quiz", "url": ""},
                ],
            },
            {
                "code": "DISC-2",
                "title": "Discipulado Nivel 2: Crecimiento Espiritual",
                "description": "Profundiza en la vida del Espíritu Santo y el carácter cristiano.",
                "modality": "virtual",
                "duration_hours": 25,
                "lessons": [
                    {
                        "title": "El Fruto del Espíritu",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "Guerra Espiritual y Victoria",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "Mayordomía y Generosidad",
                        "type": "pdf",
                        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                    },
                    {
                        "title": "El Poder del Testimonio",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                ],
            },
            {
                "code": "LID-1",
                "title": "Liderazgo Nivel 1: El Carácter del Líder",
                "description": "Formación integral para futuros servidores y líderes de grupos pequeños.",
                "modality": "presencial",
                "duration_hours": 30,
                "lessons": [
                    {
                        "title": "Liderazgo de Servicio (Modelo Jesús)",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "Manejo de Conflictos en el Ministerio",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "Integridad y Ética Ministerial",
                        "type": "pdf",
                        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                    },
                    {
                        "title": "Comunicación Efectiva",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                ],
            },
            {
                "code": "LID-2",
                "title": "Liderazgo Nivel 2: Gestión Ministerial",
                "description": "Herramientas avanzadas para la administración de ministerios y sedes.",
                "modality": "hibrida",
                "duration_hours": 40,
                "lessons": [
                    {
                        "title": "Visión y Planeación Estratégica",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "Formación de Equipos de Alto Rendimiento",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                    {
                        "title": "Gestión de Recursos y Presupuesto",
                        "type": "pdf",
                        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                    },
                    {
                        "title": "Multiplicación de Casas de Gloria",
                        "type": "video",
                        "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    },
                ],
            },
        ]

        for c_data in courses_data:
            course = Course(
                code=c_data["code"],
                title=c_data["title"],
                description=c_data["description"],
                modality=c_data["modality"],
                duration_hours=c_data["duration_hours"],
                is_published=True,
            )
            db.add(course)
            db.flush()  # Para obtener el ID del curso

            for i, l_data in enumerate(c_data["lessons"]):
                lesson = Lesson(
                    course_id=course.id,
                    title=l_data["title"],
                    content=f"Contenido detallado para {l_data['title']}",
                    content_type=l_data["type"],
                    media_url=l_data["url"],
                    order_index=i + 1,
                    duration_minutes=15,
                )
                db.add(lesson)

        db.commit()
        print("ACADEMY_CONTENT_READY")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_complete_academy()

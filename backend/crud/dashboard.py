"""Dashboard metrics, pilot readiness, and knowledge base."""
from types import SimpleNamespace

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.cache import cached


@cached(ttl=600)
def get_dashboard_metrics(db: Session):
    active_students = db.query(models.Enrollment).filter(models.Enrollment.status == "active").count()
    total_enrollments = db.query(models.Enrollment).count()
    completed_enrollments = db.query(models.Enrollment).filter(models.Enrollment.status == "completed").count()

    completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
    certificates_issued = db.query(models.Enrollment).filter(models.Enrollment.certificate_issued).count()

    formal_total = db.query(models.Enrollment).join(models.Course).filter(models.Course.modality == "formal").count()
    formal_comp = db.query(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "formal", models.Enrollment.status == "completed"
    ).count()
    formal_avg = db.query(func.avg(models.AssessmentAttempt.score)).join(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "formal"
    ).scalar() or 0

    nf_total = db.query(models.Enrollment).join(models.Course).filter(models.Course.modality == "no_formal").count()
    nf_comp = db.query(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "no_formal", models.Enrollment.status == "completed"
    ).count()
    nf_avg = db.query(func.avg(models.AssessmentAttempt.score)).join(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "no_formal"
    ).scalar() or 0

    top_courses_rows = db.query(
        models.Course.title,
        func.count(models.Enrollment.id).label("enroll_count")
    ).join(models.Enrollment).group_by(models.Course.id).order_by(text("enroll_count DESC")).limit(5).all()

    top_courses = [{"title": r[0], "count": r[1]} for r in top_courses_rows]

    avg_progress = db.query(func.avg(models.Enrollment.progress_percent)).scalar() or 0

    cards = [
        {
            "title": "Progreso Académico",
            "value": f"{round(float(avg_progress))}%",
            "trend": "+5% este mes",
            "color": "blue"
        },
        {
            "title": "Estudiantes Activos",
            "value": str(active_students),
            "trend": "Global MESH",
            "color": "green"
        },
        {
            "title": "Certificados Emitidos",
            "value": str(certificates_issued),
            "trend": "Histórico CCF",
            "color": "purple"
        },
        {
            "title": "Tasa de Finalización",
            "value": f"{round(completion_rate)}%",
            "trend": "Meta: 80%",
            "color": "orange"
        }
    ]

    return {
        "active_students": active_students,
        "completion_rate": round(completion_rate, 2),
        "certificates_issued": certificates_issued,
        "cards": cards,
        "formal_stats": {
            "total": formal_total,
            "completed": formal_comp,
            "rate": round((formal_comp / formal_total * 100) if formal_total > 0 else 0, 2),
            "avg_grade": round(float(formal_avg), 1)
        },
        "no_formal_stats": {
            "total": nf_total,
            "completed": nf_comp,
            "rate": round((nf_comp / nf_total * 100) if nf_total > 0 else 0, 2),
            "avg_grade": round(float(nf_avg), 1)
        },
        "top_courses": top_courses
    }


def get_pastor_radar(db: Session):
    return {
        "membresia_viva": db.query(models.Member).count(),
        "bautismos_este_anio": 0,
        "estudiantes_activos": db.query(models.Enrollment).filter(models.Enrollment.status == "active").count(),
        "recaudacion_mes": 0.0
    }


def get_pilot_readiness(db: Session) -> schemas.PilotReadiness:
    checklist = [
        {"key": "courses", "label": "Catálogo de Cursos", "completed": db.query(models.Course).count() >= 5},
        {"key": "users", "label": "Usuarios Estudiantes", "completed": db.query(models.User).filter(models.User.role == 'estudiante').count() >= 10},
        {"key": "enrollments", "label": "Matrículas Activas", "completed": db.query(models.Enrollment).count() >= 5}
    ]
    completed_count = sum(1 for item in checklist if item['completed'])
    readiness_score = (completed_count / len(checklist)) if checklist else 0.0

    return schemas.PilotReadiness(
        environment_ready=True,
        readiness_score=readiness_score,
        checklist=checklist
    )


def search_knowledge_base(db: Session, query: str):
    if not query:
        return []
    mock_docs = [
        {
            "title": "Protocolo de Consolidación Ministerial",
            "content": "Lineamientos para la bienvenida de nuevos miembros y seguimiento pastoral en las primeras 48 horas tras su primera visita.",
            "category": "Operaciones",
            "relevance": 0.98
        },
        {
            "title": "Manual de Liderazgo: Casas de Gloria",
            "content": "Principios bíblicos para la gestión de grupos pequeños, resolución de conflictos y multiplicación celular en zonas urbanas.",
            "category": "Liderazgo",
            "relevance": 0.85
        },
        {
            "title": "Directiva de Seguridad Digital y Auditoría",
            "content": "Normativas para el manejo de datos sensibles de la congregación, protección de privacidad y registro exhaustivo de acciones administrativas.",
            "category": "Seguridad",
            "relevance": 0.72
        },
        {
            "title": "Reglamento Académico MESH",
            "content": "Estatutos para la formación teológica formal y no formal, criterios de evaluación y requisitos para la certificación ministerial.",
            "category": "Educación",
            "relevance": 0.65
        }
    ]
    results = [doc for doc in mock_docs if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower()]
    if not results:
        results = mock_docs[:3]
    return [SimpleNamespace(**doc) for doc in results]

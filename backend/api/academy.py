from __future__ import annotations

import logging
import uuid
from typing import List, Optional, cast

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile, status)
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.crud.crm import get_user_sede_id
from backend.crud.crm import resolve_persona_id_for_user as resolve_persona_uuid_for_user
from backend.auth import (normalize_role, require_admin,
                          require_coordinator_or_admin, require_module_access,
                          require_teacher_or_admin)
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.storage import storage_service
from backend.core.uploads import sanitize_filename

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


def coerce_user_id(user_id):
    if user_id is None:
        return None
    if isinstance(user_id, uuid.UUID):
        return str(user_id)
    if isinstance(user_id, str) and _is_uuid_like(user_id):
        return user_id
    if isinstance(user_id, int):
        return user_id
    if isinstance(user_id, str) and user_id.isdigit():
        return int(user_id)
    return user_id


def _is_uuid_like(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


def _enrollment_identity_filter(db: Session, user_id):
    if _is_uuid_like(user_id):
        return models.Enrollment.persona_id == uuid.UUID(str(user_id))
    pid = resolve_persona_uuid_for_user(db, user_id)
    return models.Enrollment.persona_id == pid


def _lesson_progress_identity_filter(db: Session, user_id):
    if _is_uuid_like(user_id):
        return models.LessonProgress.persona_id == uuid.UUID(str(user_id))
    pid = resolve_persona_uuid_for_user(db, user_id)
    return models.LessonProgress.persona_id == pid


def _current_role(current_user) -> str:
    role = normalize_role(str(getattr(current_user, "role", "") or ""))
    rol_plataforma = getattr(current_user, "rol_plataforma", None)
    if not role and rol_plataforma:
        role = normalize_role(str(rol_plataforma.nombre))
    return role


def _can_access_identity(current_user, identity: str) -> bool:
    current_id = coerce_user_id(getattr(current_user, "id", 0))
    role = _current_role(current_user)
    return str(current_id) == str(identity) or role in {"admin", "administrador", "coordinador"}


def _serialize_enrollment(row) -> dict:
    course = getattr(row, "course", None)
    data = {
        "id": row.id,
        "user_id": row.persona.user_id if (getattr(row, "persona", None) and row.persona) else None,
        "persona_id": str(row.persona_id) if row.persona_id else None,
        "course_id": row.course_id,
        "status": row.status,
        "progress_percent": row.progress_percent,
        "final_grade": row.final_grade,
        "attendance_percent": row.attendance_percent,
        "approved": row.approved,
        "acta_closed": row.acta_closed,
        "certificate_issued": row.certificate_issued,
        "enrolled_at": str(row.enrolled_at) if getattr(row, "enrolled_at", None) else None,
        "created_at": str(row.created_at) if getattr(row, "created_at", None) else None,
    }
    if course:
        data["course"] = {
            "id": course.id,
            "code": getattr(course, "code", "") or f"course-{course.id}",
            "title": getattr(course, "title", None) or getattr(course, "name", None) or f"Curso #{course.id}",
            "description": getattr(course, "description", None),
            "modality": getattr(course, "modality", None) or "formal",
            "duration_hours": getattr(course, "duration_hours", 0) or 0,
            "is_self_paced": bool(getattr(course, "is_self_paced", False)),
            "cohort_name": getattr(course, "cohort_name", None),
            "certificate_type": getattr(course, "certificate_type", None),
        }
    return data


def _enrollments_for_identity(db: Session, identity: str):
    return (
        db.query(models.Enrollment)
        .filter(_enrollment_identity_filter(db, identity))
        .all()
    )


def _serialize_submission_review(
    row: tuple[models.AssignmentSubmission, str, str],
) -> schemas.AssignmentSubmissionReview:
    submission, lesson_title, student_name = row
    return schemas.AssignmentSubmissionReview(
        id=submission.id,
        enrollment_id=submission.enrollment_id,
        lesson_id=submission.lesson_id,
        student_name=student_name,
        lesson_title=lesson_title,
        file_url=submission.file_url,
        comment=submission.comment,
        grade=submission.grade,
        teacher_feedback=submission.teacher_feedback,
        submitted_at=submission.created_at,
    )


def _resolve_persona_for_user(db: Session, user_id: object):
    persona_id = resolve_persona_uuid_for_user(db, user_id)
    return (
        db.query(models.Persona).filter(models.Persona.id == persona_id).first()
        if persona_id
        else None
    )


def _resolve_academy_account(db: Session, persona: models.Persona):
    from backend.models_auth import Usuario

    return db.query(Usuario).filter(Usuario.id == persona.id).first()


def _enrollment_matches_current_user(db: Session, current_user, enrollment) -> bool:
    current_identity = coerce_user_id(getattr(current_user, "id", None))
    persona = _resolve_persona_for_user(db, current_identity)
    return bool(persona and getattr(enrollment, "persona_id", None) == persona.id)


@router.get("/courses/", response_model=List[schemas.Course])
def read_courses(
    skip: int = 0,
    limit: int = 100,
    modality: Optional[str] = None,
    published_only: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "read")),
):
    sede_id = get_user_sede_id(db, current_user.id)
    return crud.get_courses(
        db, skip=skip, limit=limit, modality=modality, published_only=published_only, sede_id=sede_id
    )


@router.get("/courses/{course_id}", response_model=schemas.Course)
def read_course(course_id: int, db: Session = Depends(get_db)):
    db_course = crud.get_course(db, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course


@router.get("/courses/{course_id}/lessons", response_model=List[schemas.Lesson])
def read_course_lessons(course_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Lesson)
        .filter(models.Lesson.course_id == course_id)
        .order_by(models.Lesson.order_index)
        .all()
    )


@router.get("/courses/{course_id}/assessments", response_model=List[schemas.Assessment])
def read_course_assessments(course_id: int, db: Session = Depends(get_db)):
    """Lista todas las evaluaciones disponibles para un curso específico."""
    return (
        db.query(models.Assessment)
        .join(models.Lesson)
        .filter(models.Lesson.course_id == course_id)
        .all()
    )


@router.get("/assessments/{assessment_id}", response_model=schemas.Assessment)
def read_assessment(assessment_id: int, db: Session = Depends(get_db)):
    db_assessment = crud.get_assessment_with_questions(db, assessment_id)
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return db_assessment


@router.post(
    "/assessments/{assessment_id}/submit", response_model=schemas.AssessmentAttempt
)
def submit_assessment_direct(
    assessment_id: int,
    payload: schemas.AssessmentAttemptSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Envia una evaluación directamente con respuestas detalladas o puntaje."""
    # Encontrar la inscripción del usuario para este curso/evaluación
    assessment = crud.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    enrollment = (
        db.query(models.Enrollment)
        .filter(
            _enrollment_identity_filter(db, getattr(current_user, "id", None)),
            models.Enrollment.course_id == assessment.course_id,
        )
        .first()
    )

    if not enrollment:
        raise HTTPException(status_code=403, detail="No estás inscrito en este curso")

    if payload.answers:
        # Submission with detailed answers
        try:
            return crud.submit_assessment_attempt(
                db,
                assessment_id=assessment_id,
                enrollment_id=enrollment.id,
                answers=[a.model_dump() for a in payload.answers],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    elif payload.submitted_score is not None:
        # Legacy/Shortcut submission with just score
        return crud.create_or_update_assessment_attempt(
            db,
            enrollment=enrollment,
            assessment=assessment,
            submitted_score=payload.submitted_score,
        )
    else:
        raise HTTPException(
            status_code=400, detail="Debe proporcionar respuestas o un puntaje"
        )


@router.get("/lessons/{lesson_id}/progress")
def read_lesson_progress(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    progress = crud.get_lesson_progress(
        db, user_id=current_user.id, lesson_id=lesson_id
    )
    if not progress:
        return {
            "progress_percent": 0.0,
            "last_position_seconds": 0,
            "is_completed": False,
        }
    return progress


class ProgressUpdate(BaseModel):
    progress_percent: float
    last_position_seconds: int


@router.post("/lessons/{lesson_id}/progress")
def update_lesson_progress(
    lesson_id: int,
    payload: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    return crud.update_lesson_progress(
        db,
        user_id=current_user.id,
        lesson_id=lesson_id,
        progress_percent=payload.progress_percent,
        last_position=payload.last_position_seconds,
    )


@router.get(
    "/courses/{course_id}/attendance", response_model=List[schemas.CourseAttendance]
)
def list_course_attendance(course_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.CourseAttendance)
        .join(models.Enrollment)
        .filter(models.Enrollment.course_id == course_id)
        .all()
    )


@router.post(
    "/courses/{course_id}/attendance/bulk", status_code=status.HTTP_201_CREATED
)
def record_bulk_attendance(
    course_id: int,
    payload: schemas.BulkAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    # Verify course exists
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    recorded_count = 0
    for record in payload.records:
        # Verify enrollment belongs to course
        enrollment = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.id == record.enrollment_id,
                models.Enrollment.course_id == course_id,
            )
            .first()
        )

        if enrollment:
            persona = _resolve_persona_for_user(db, getattr(current_user, "id", None))
            db_attendance = models.CourseAttendance(
                enrollment_id=record.enrollment_id,
                status=record.status,
                session_date=payload.session_date,
                recorded_by_persona_id=persona.id if persona else None,
            )
            db.add(db_attendance)
            recorded_count += 1

    db.commit()
    return {"message": f"Se registraron {recorded_count} asistencias con éxito"}


@router.post(
    "/enrollments/{enrollment_id}/request-certificate",
    response_model=schemas.Certificate,
)
def request_certificate(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    try:
        return crud.issue_certificate(db, enrollment_id=enrollment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/certificates/validate/{code}", response_model=schemas.Certificate)
def validate_certificate(code: str, db: Session = Depends(get_db)):
    cert = crud.get_certificate_by_code(db, code=code)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert


@router.get("/dashboard/metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    return crud.get_dashboard_metrics(db)


@router.get("/dashboard/pilot-readiness", response_model=schemas.PilotReadiness)
def get_pilot_readiness(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    return crud.get_pilot_readiness(db)


@router.post(
    "/courses/{course_id}/formal/close-acta", response_model=schemas.FormalActa
)
def close_formal_acta(
    course_id: int,
    payload: schemas.FormalActaCloseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    acta = crud.close_formal_acta(
        db,
        course_id=course_id,
        closed_by_user_id=coerce_user_id(getattr(current_user, "id", 0)),
        closed_by_persona_id=crud.resolve_persona_id_for_user(
            db, getattr(current_user, "id", None)
        ),
        min_grade=payload.min_grade,
        min_attendance=payload.min_attendance,
    )
    record_admin_action(
        db,
        current_user,
        action="close_formal_acta",
        resource_type="formal_acta",
        resource_id=str(acta.id),
        metadata={
            "course_id": course_id,
            "min_grade": payload.min_grade,
            "min_attendance": payload.min_attendance,
        },
    )
    return acta


@router.get(
    "/courses/{course_id}/formal/last-acta", response_model=Optional[schemas.FormalActa]
)
def read_last_formal_acta(course_id: int, db: Session = Depends(get_db)):
    return crud.get_latest_acta_by_course(db, course_id)


@router.post("/enrollments/", response_model=schemas.Enrollment)
def create_enrollment(
    enrollment: schemas.EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "read")),
):
    """Inscribe a un usuario en un curso, respetando el access_level del curso.

    - open: cualquier usuario autenticado (academy:read)
    - member: requiere academy:study
    - advanced: requiere academy:edit
    """
    from backend.models_academy_core import Curso
    from backend.core.permissions import get_user_effective_permissions

    user_id = coerce_user_id(getattr(current_user, "id", 0))
    requested_user_id = coerce_user_id(enrollment.user_id)
    persona_curr = _resolve_persona_for_user(db, user_id)
    persona_req = _resolve_persona_for_user(db, requested_user_id)
    # Obtener role correcto tanto en auth v1 como v2
    role = _current_role(current_user)

    # Verificar access_level usando el modelo correcto (academy_courses)
    curso = db.query(Curso).filter(Curso.id == enrollment.course_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    access = curso.access_level or "member"
    if access not in {"open", "member", "advanced"}:
        access = "member"  # valor inválido en DB → comportamiento seguro por defecto

    if access in {"member", "advanced"}:
        required_perm = "academy:study" if access == "member" else "academy:edit"
        detail = (
            "Este curso requiere membresía activa (academy:study)."
            if access == "member"
            else "Este curso es solo para formadores (academy:edit)."
        )
        eff = get_user_effective_permissions(db, current_user)
        if role not in {"admin", "administrador"} and required_perm not in eff:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    # access == "open": cualquier registrado con academy:read puede inscribirse

    if (
        role != "admin"
        and (not persona_curr or not persona_req or persona_curr.id != persona_req.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create your own enrollment",
        )
    try:
        return crud.create_enrollment(db, enrollment)
    except MemoryError:
        raise
    except Exception:  # pragma: no cover
        logger.exception(
            "Failed to create academy enrollment", extra={"user_id": user_id}
        )
        raise HTTPException(status_code=400, detail="No se pudo crear la inscripcion")


@router.post("/enrollments/{enrollment_id}/check-in", response_model=schemas.Attendance)
def check_in_attendance(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    enrollment = crud.get_enrollment(db, enrollment_id)
    if not enrollment or not _enrollment_matches_current_user(db, current_user, enrollment):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return crud.record_activity_attendance(db, enrollment_id)


@router.post(
    "/enrollments/{enrollment_id}/assessments/{assessment_id}/submit",
    response_model=schemas.AssessmentAttempt,
)
def submit_assessment(
    enrollment_id: int,
    assessment_id: int,
    payload: schemas.AssessmentAttemptSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    enrollment = crud.get_enrollment(db, enrollment_id)
    assessment = crud.get_assessment(db, assessment_id)
    if not enrollment or not assessment:
        raise HTTPException(status_code=404, detail="Not found")
    if not _enrollment_matches_current_user(db, current_user, enrollment):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if payload.answers:
        return crud.submit_assessment_attempt(
            db,
            assessment_id=assessment_id,
            enrollment_id=enrollment_id,
            answers=[a.model_dump() for a in payload.answers],
        )

    return crud.create_or_update_assessment_attempt(
        db,
        enrollment=enrollment,
        assessment=assessment,
        submitted_score=payload.submitted_score or 0,
    )


@router.get("/me/certificates", response_model=List[schemas.Certificate])
def read_my_certificates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Obtiene certificados del usuario actual (IDOR protegido)."""
    return crud.get_certificates_by_user(db, current_user.id)


@router.get("/me/enrollments", response_model=List[dict])
def read_my_enrollments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Obtiene inscripciones del usuario actual (IDOR protegido)."""
    return [_serialize_enrollment(row) for row in _enrollments_for_identity(db, str(current_user.id))]


@router.get("/enrollments", response_model=List[dict])
def list_all_enrollments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    """Lista todas las inscripciones (admin/coordinador)."""
    enrollments = db.query(models.Enrollment).all()
    result = []
    for e in enrollments:
        result.append(
            {
                "id": e.id,
                "user_id": e.persona.user_id if (getattr(e, "persona", None) and e.persona) else None,
                "course_id": e.course_id,
                "progress_percent": e.progress_percent,
                "enrolled_at": str(e.enrolled_at) if e.enrolled_at else None,
            }
        )
    return result


@router.get("/me/progress", response_model=List[dict])
def get_my_course_progress(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Devuelve progreso academico del usuario actual sin exponer user_id legacy."""
    return get_user_course_progress(str(current_user.id), db, current_user)


@router.get("/personas", response_model=List[dict])
def list_academy_personas(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    """Lista personas academicas con identidad UUID."""
    from backend.models_auth import RolPlataforma, Usuario

    query = (
        db.query(models.Persona, Usuario, RolPlataforma)
        .outerjoin(Usuario, Usuario.id == models.Persona.id)
        .outerjoin(RolPlataforma, RolPlataforma.id == Usuario.rol_plataforma_id)
    )
    if role:
        role_value = role.lower()
        aliases = {
            "student": {"student", "estudiante", "lector"},
            "teacher": {"teacher", "docente", "facilitador", "editor"},
        }.get(role_value, {role_value})
        rows = [
            row for row in query.all()
            if (row[2] and str(row[2].nombre).lower() in aliases)
            or (row[1] and getattr(row[1], "platform_role", None) and str(row[1].platform_role.role).lower() in aliases)
        ]
    else:
        rows = query.all()

    return [
        {
            "id": str(persona.id),
            "persona_id": str(persona.id),
            "name": persona.full_name,
            "full_name": persona.full_name,
            "email": persona.email or getattr(user, "email", None),
            "role": getattr(rol, "nombre", None) or getattr(getattr(user, "platform_role", None), "role", None),
            "status": getattr(persona, "activity_status", None) or "active",
            "course_count": 0,
            "progress": 0,
            "active_students": 0,
        }
        for persona, user, rol in rows
    ]


@router.get("/personas/{persona_id}/enrollments", response_model=List[dict])
def get_persona_enrollments(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Obtiene inscripciones por persona UUID."""
    if not _is_uuid_like(persona_id):
        raise HTTPException(status_code=400, detail="persona_id invalido")
    if not _can_access_identity(current_user, persona_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return [_serialize_enrollment(row) for row in _enrollments_for_identity(db, persona_id)]


@router.get("/personas/{persona_id}/progress", response_model=List[dict])
def get_persona_course_progress(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Devuelve progreso academico por persona UUID."""
    if not _is_uuid_like(persona_id):
        raise HTTPException(status_code=400, detail="persona_id invalido")
    return get_user_course_progress(persona_id, db, current_user)


@router.get("/users/{user_id}/enrollments", response_model=List[dict])
def get_user_enrollments(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Obtiene las inscripciones de un usuario. Usa Matricula (UUID) si existe persona vinculada."""
    persona = _resolve_persona_for_user(db, user_id)
    if persona:
        matriculas = (
            db.query(models.Matricula)
            .filter(
                models.Matricula.persona_id == persona.id,
                models.Matricula.deleted_at.is_(None),
            )
            .all()
        )
        return [
            {
                "id": str(m.id),
                "persona_id": str(m.persona_id),
                "course_id": m.course_id,
                "status": m.status,
                "progress_percent": m.progress_percent,
                "approved": m.approved,
                "completed_at": str(m.completed_at) if m.completed_at else None,
            }
            for m in matriculas
        ]
    # Fallback: legacy Integer enrollment model
    enrollments = db.query(models.Enrollment).filter(_enrollment_identity_filter(db, user_id)).all()
    return [_serialize_enrollment(e) for e in enrollments]


@router.get("/users", response_model=List[dict])
def list_academy_users(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    """Lista usuarios de la academia con filtro opcional por rol."""
    from backend.models_auth import Usuario

    q = db.query(Usuario)
    if role:
        role_norm = normalize_role(role)
        q = q.join(Usuario.rol_plataforma, isouter=True)
        q = q.filter(
            (models.func.lower(Usuario.username) == role_norm)
            | (models.func.lower(Usuario.email) == role_norm)
        )
    users = q.all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "role": (
                str(getattr(getattr(u, "rol_plataforma", None), "nombre", "") or getattr(getattr(u, "platform_role", None), "role", "") or "estudiante")
            ),
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.post("/lessons/{lesson_id}/resources", response_model=schemas.Resource)
async def upload_resource(
    lesson_id: int,
    title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    original_name = file.filename or "resource"
    sanitized = sanitize_filename(cast(str, original_name))
    try:
        contents = await file.read()
        url = storage_service.save_file(contents, sanitized, subfolder="academy")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db_resource = models.Resource(
        title=title,
        file_url=url,
        resource_type=file.content_type or "application/octet-stream",
        lesson_id=lesson_id,
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    record_admin_action(
        db,
        current_user,
        action="upload_lesson_resource",
        resource_type="lesson_resource",
        resource_id=str(db_resource.id),
        metadata={"lesson_id": lesson_id, "title": title},
    )
    return db_resource


@router.post(
    "/lessons/{lesson_id}/submit-assignment",
    response_model=schemas.AssignmentSubmission,
)
async def submit_assignment_file(
    lesson_id: int,
    enrollment_id: int = Form(...),
    comment: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    enrollment = crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    role = _current_role(current_user)
    if not _enrollment_matches_current_user(db, current_user, enrollment) and role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if int(getattr(lesson, "course_id", 0)) != int(getattr(enrollment, "course_id", 0)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lesson does not belong to enrollment",
        )

    original_name = file.filename or "assignment"
    sanitized = sanitize_filename(cast(str, original_name))
    try:
        contents = await file.read()
        url = storage_service.save_file(contents, sanitized, subfolder="academy")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    submission = crud.create_assignment_submission(
        db,
        enrollment_id=enrollment_id,
        lesson_id=lesson_id,
        file_url=url,
        comment=comment,
    )
    return submission


@router.get(
    "/admin/submissions", response_model=List[schemas.AssignmentSubmissionReview]
)
def admin_list_submissions(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    rows = crud.list_assignment_submissions_with_meta(db, limit=limit)
    return [_serialize_submission_review(row) for row in rows]


@router.patch(
    "/admin/submissions/{submission_id}/grade",
    response_model=schemas.AssignmentSubmissionReview,
)
def admin_grade_submission(
    submission_id: int,
    grade: Optional[float] = Query(None),
    feedback: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    if grade is None and feedback is None:
        raise HTTPException(status_code=400, detail="grade or feedback required")
    if grade is not None and (grade < 0 or grade > 100):
        raise HTTPException(status_code=400, detail="grade must be between 0 and 100")
    updated = crud.grade_assignment_submission(
        db, submission_id, grade=grade, feedback=feedback
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Submission not found")
    row = crud.get_assignment_submission_with_meta(db, submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _serialize_submission_review(row)


@router.post("/certificates/sync", response_model=List[schemas.Certificate])
def sync_certificates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    issued = crud.issue_pending_certificates(db)
    record_admin_action(
        db,
        current_user,
        action="sync_certificates",
        resource_type="certificate",
        metadata={"issued_count": len(issued)},
    )
    return issued


@router.get("/me/profile", response_model=schemas.AcademyStudentProfile)
def get_my_academy_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    user_id = coerce_user_id(current_user.id)
    db_user = None if _is_uuid_like(user_id) else crud.get_user(db, user_id)
    db_user = db_user or current_user
    enrollments = (
        db.query(models.Enrollment).filter(_enrollment_identity_filter(db, user_id)).all()
    )
    certificates = (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(_enrollment_identity_filter(db, user_id))
        .all()
    )

    total_progress = (
        sum(float(e.progress_percent or 0) for e in enrollments) / len(enrollments)
        if enrollments
        else 0.0
    )

    return {
        "user_id": user_id,
        "username": getattr(db_user, "username", None)
        or getattr(db_user, "email", "").split("@")[0],
        "total_progress": round(total_progress, 1),
        "enrollments_count": len(enrollments),
        "certificates_count": len(certificates),
        "active_courses": enrollments,
        "recent_certificates": certificates[-3:] if certificates else [],
    }


@router.get("/users/{user_id}/progress", response_model=List[dict])
def get_user_course_progress(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Devuelve el progreso agregado por curso para un usuario."""
    current_id = coerce_user_id(getattr(current_user, "id", 0))
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and getattr(current_user, "rol_plataforma", None):
        role = normalize_role(str(current_user.rol_plataforma.nombre))
    if str(current_id) != str(user_id) and role not in {
        "admin",
        "coordinador",
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    enrollments = (
        db.query(models.Enrollment).filter(_enrollment_identity_filter(db, user_id)).all()
    )
    if not enrollments:
        return []

    course_ids = [enrollment.course_id for enrollment in enrollments]
    lesson_counts = {
        course_id: total
        for course_id, total in db.query(
            models.Lesson.course_id, func.count(models.Lesson.id)
        )
        .filter(models.Lesson.course_id.in_(course_ids))
        .group_by(models.Lesson.course_id)
        .all()
    }
    completed_counts = {
        course_id: completed
        for course_id, completed in db.query(
            models.Lesson.course_id, func.count(models.LessonProgress.id)
        )
        .join(models.Lesson, models.Lesson.id == models.LessonProgress.lesson_id)
        .filter(
            _lesson_progress_identity_filter(db, user_id),
            models.Lesson.course_id.in_(course_ids),
        )
        .group_by(models.Lesson.course_id)
        .all()
    }
    latest_updates = {
        course_id: updated_at
        for course_id, updated_at in db.query(
            models.Lesson.course_id, func.max(models.LessonProgress.updated_at)
        )
        .join(models.Lesson, models.Lesson.id == models.LessonProgress.lesson_id)
        .filter(
            _lesson_progress_identity_filter(db, user_id),
            models.Lesson.course_id.in_(course_ids),
        )
        .group_by(models.Lesson.course_id)
        .all()
    }

    result = []
    for enrollment in enrollments:
        course = getattr(enrollment, "course", None)
        total_lessons = int(lesson_counts.get(enrollment.course_id, 0))
        lessons_completed = int(completed_counts.get(enrollment.course_id, 0))
        progress_percent = float(enrollment.progress_percent or 0)
        result.append(
            {
                "id": enrollment.course_id,
                "title": getattr(course, "name", None)
                or getattr(course, "title", None)
                or f"Curso #{enrollment.course_id}",
                "progress_percent": round(progress_percent, 2),
                "status": enrollment.status,
                "average_grade": round(progress_percent, 2),
                "lessons_completed": lessons_completed,
                "total_lessons": total_lessons,
                "last_activity": (
                    latest_updates.get(enrollment.course_id).isoformat()
                    if latest_updates.get(enrollment.course_id)
                    else (
                        enrollment.created_at.isoformat()
                        if enrollment.created_at
                        else None
                    )
                ),
                "certificate_issued": bool(enrollment.certificate_issued),
            }
        )
    return result


@router.get("/analytics/candidates", response_model=List[schemas.User])
def get_academy_candidates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    return crud.get_academy_candidates(db)


# -----------------
# Forum API
# -----------------
@router.get("/personas/{persona_id}/profile")
def get_member_academy_profile(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    """Obtiene el perfil academico de un miembro del CRM."""
    try:
        persona_uuid = uuid.UUID(persona_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="persona_id invalido")
    persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    account = _resolve_academy_account(db, persona)
    if not account:
        return {"is_linked": False, "message": "No tiene cuenta de academia vinculada"}

    enrollments = db.query(models.Enrollment).filter(_enrollment_identity_filter(db, persona.id)).all()
    certificates = (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(_enrollment_identity_filter(db, persona.id))
        .all()
    )

    return {
        "is_linked": True,
        "user_id": str(persona.id),
        "username": getattr(account, "username", "Unknown"),
        "enrollments": enrollments,
        "certificates": certificates,
        "total_progress": (
            sum(float(e.progress_percent or 0) for e in enrollments) / len(enrollments)
            if enrollments
            else 0.0
        ),
    }


class CreateAcademyAccountRequest(BaseModel):
    password: str


@router.post("/personas/{persona_id}/create-account")
def create_academy_account(
    persona_id: str,
    payload: CreateAcademyAccountRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    """Crea una cuenta de usuario (Academia) para un miembro del CRM."""
    try:
        persona_uuid = uuid.UUID(persona_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="persona_id invalido")
    persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    existing_account = _resolve_academy_account(db, persona)
    if existing_account:
        raise HTTPException(
            status_code=400, detail="La persona ya tiene una cuenta vinculada"
        )

    if not persona.email:
        raise HTTPException(
            status_code=400, detail="La persona debe tener un email para crear cuenta"
        )

    from backend.core.security import get_password_hash
    from backend.models_auth import RolPlataforma, Usuario
    from backend.models_kernel import PlatformRole as PlatformRoleEnum
    from backend.models_kernel import PlatformRoleDefinition

    existing_auth_user = db.query(Usuario).filter(Usuario.id == persona.id).first()
    if existing_auth_user:
        raise HTTPException(status_code=400, detail="La persona ya tiene una cuenta vinculada")

    lector_role = (
        db.query(PlatformRoleDefinition)
        .filter(PlatformRoleDefinition.role == PlatformRoleEnum.LECTOR)
        .first()
    )
    legacy_role = (
        db.query(RolPlataforma)
        .filter(RolPlataforma.nombre.ilike("lector"))
        .first()
    )

    new_user = Usuario(
        id=persona.id,
        sede_id=persona.sede_id or getattr(current_user, "sede_id", None) or db.query(models.Sede.id).first()[0],
        username=persona.email.split("@")[0],
        email=persona.email,
        password_hash=get_password_hash(payload.password),
        platform_role_id=lector_role.id if lector_role else None,
        rol_plataforma_id=legacy_role.id if legacy_role else None,
        is_active=True,
        is_email_verified=bool(persona.email),
    )
    db.add(new_user)
    db.commit()

    record_admin_action(
        db,
        current_user,
        action="create_member_academy_account",
        resource_type="user",
        resource_id=str(new_user.id),
        metadata={"persona_id": persona_id},
    )

    return {"status": "success", "user_id": str(new_user.id), "username": new_user.username}


@router.get("/forum/threads", response_model=List[schemas.ForumThread])
def get_forum_threads(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    return crud.get_forum_threads(db)


@router.post("/forum/threads", response_model=schemas.ForumThread)
def create_thread(
    thread: schemas.ForumThreadBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    persona = _resolve_persona_for_user(db, getattr(current_user, "id", None))
    if not persona:
        raise HTTPException(status_code=400, detail="No se pudo resolver la persona del autor")
    thread_data = schemas.ForumThreadCreate(
        **thread.model_dump(), author_persona_id=str(persona.id)
    )
    return crud.create_forum_thread(db, thread_data)


# ─── SCHEDULE ────────────────────────────────────────────────────────────────


@router.get("/schedule", response_model=list)
def get_academy_schedule(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """
    Retorna el cronograma de cursos activos para el panel de academia.
    Incluye datos de inscripcion y capacidad para el calendario.
    """
    courses = crud.get_courses(db, skip=0, limit=100, published_only=True)
    schedule = []
    for course in courses:
        enrollments = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.course_id == course.id,
                models.Enrollment.status == "active",
            )
            .count()
        )
        schedule.append(
            {
                "id": course.id,
                "code": course.code,
                "title": course.title,
                "description": course.description,
                "modality": course.modality,
                "enrolled": enrollments,
                "lesson_count": course.lesson_count,
                "total_minutes": course.total_minutes,
                "created_at": (
                    course.created_at.isoformat() if course.created_at else None
                ),
            }
        )
    return schedule


# ── Admin course management ─────────────────────────────────────────────


@router.post("/admin/courses", response_model=schemas.Course)
def create_course_admin(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Crea un nuevo curso desde el panel de administracion."""
    course = models.Course(
        code=payload.get("code", f"C{int(__import__('time').time())}"),
        title=payload["title"],
        description=payload.get("description", ""),
        modality=payload.get("modality", "online"),
        is_published=payload.get("is_published", False),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/admin/courses/{course_id}/students", response_model=List[dict])
def get_course_students_admin(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista los estudiantes inscritos en un curso."""
    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.course_id == course_id)
        .all()
    )
    result = []
    for enrollment in enrollments:
        persona = (
            db.query(models.Persona).filter(models.Persona.id == enrollment.persona_id).first()
            if getattr(enrollment, "persona_id", None)
            else _resolve_persona_for_user(db, getattr(enrollment, "user_id", None))
        )
        account = _resolve_academy_account(db, persona) if persona else None
        result.append(
            {
                "id": enrollment.id,
                "user_id": str(enrollment.persona_id) if enrollment.persona_id else enrollment.user_id,
                "username": getattr(account, "username", "N/A") if account else "N/A",
                "status": enrollment.status,
                "progress_percent": enrollment.progress_percent,
                "approved": enrollment.approved,
            }
        )
    return result


@router.post("/admin/assessments", status_code=201)
def create_assessment_admin(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher_or_admin),
):
    """Create a standalone course-level assessment with questions."""
    course_id = payload.get("course_id")
    lesson_id = payload.get("lesson_id")

    # Need at least one anchor
    if not lesson_id and not course_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="course_id or lesson_id required")

    # If only course_id provided, find or create a placeholder lesson
    if not lesson_id:
        lesson = (
            db.query(models.Lesson).filter(models.Lesson.course_id == course_id).first()
        )
        if not lesson:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=422, detail="No lessons found for this course"
            )
        lesson_id = lesson.id

    assessment = models.Assessment(
        lesson_id=lesson_id,
        course_id=course_id,
        title=payload["title"],
        min_score=payload.get("passing_score", 70),
    )
    db.add(assessment)
    db.flush()

    for q in payload.get("questions", []):
        question = models.AssessmentQuestion(
            assessment_id=assessment.id,
            question_text=q.get("text", ""),
            question_type=q.get("type", "multiple_choice"),
            points=q.get("points", 10),
        )
        db.add(question)
        db.flush()
        for i, opt_text in enumerate(q.get("options", [])):
            db.add(
                models.AssessmentOption(
                    question_id=question.id,
                    option_text=opt_text,
                    is_correct=(i == q.get("correct_option", 0)),
                )
            )

    db.commit()
    db.refresh(assessment)
    return {
        "id": assessment.id,
        "title": assessment.title,
        "min_score": float(assessment.min_score),
    }


@router.patch("/admin/assessments/{assessment_id}")
def update_assessment_admin(
    assessment_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher_or_admin),
):
    assessment = (
        db.query(models.Assessment)
        .filter(models.Assessment.id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if "title" in payload:
        assessment.title = payload["title"]
    if "passing_score" in payload:
        assessment.min_score = payload["passing_score"]
    db.commit()
    db.refresh(assessment)
    return {
        "id": assessment.id,
        "title": assessment.title,
        "min_score": float(assessment.min_score),
    }

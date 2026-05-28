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
from backend.auth import (normalize_role, require_admin,
                          require_coordinator_or_admin, require_module_access,
                          require_teacher_or_admin)
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.uploads import sanitize_filename, save_upload

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


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


@router.get("/courses/", response_model=List[schemas.Course])
def read_courses(
    skip: int = 0,
    limit: int = 100,
    modality: Optional[str] = None,
    published_only: bool = True,
    db: Session = Depends(get_db),
):
    return crud.get_courses(
        db, skip=skip, limit=limit, modality=modality, published_only=published_only
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
            models.Enrollment.user_id == current_user.id,
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
            db_attendance = models.CourseAttendance(
                enrollment_id=record.enrollment_id,
                status=record.status,
                session_date=payload.session_date,
                recorded_by_id=current_user.id,
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
        closed_by_user_id=int(getattr(current_user, "id", 0)),
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
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    user_id = int(getattr(current_user, "id", 0))
    if (
        normalize_role(str(current_user.role)) != "admin"
        and user_id != enrollment.user_id
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
    if not enrollment or int(getattr(enrollment, "user_id", 0)) != int(
        getattr(current_user, "id", 0)
    ):
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
    current_id = int(getattr(current_user, "id", 0))
    if int(getattr(enrollment, "user_id", 0)) != current_id:
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


@router.get("/me/enrollments", response_model=List[schemas.Enrollment])
def read_my_enrollments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Obtiene inscripciones del usuario actual (IDOR protegido)."""
    return crud.get_enrollments_by_user(db, current_user.id)


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
                "user_id": e.user_id,
                "course_id": e.course_id,
                "progress_percent": e.progress_percent,
                "enrolled_at": str(e.enrolled_at) if e.enrolled_at else None,
            }
        )
    return result


@router.get("/users/{user_id}/enrollments", response_model=List[dict])
def get_user_enrollments(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Obtiene las inscripciones de un usuario. Usa Matricula (UUID) si existe persona vinculada."""
    persona = db.query(models.Persona).filter(models.Persona.user_id == user_id).first()
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
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()
    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "course_id": e.course_id,
            "progress_percent": e.progress_percent,
            "enrolled_at": str(e.enrolled_at) if e.enrolled_at else None,
        }
        for e in enrollments
    ]


@router.get("/users", response_model=List[dict])
def list_academy_users(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coordinator_or_admin),
):
    """Lista usuarios de la academia con filtro opcional por rol."""
    q = db.query(models.User)
    if role:
        q = q.filter(models.User.role == role)
    users = q.all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
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
    unique_name = f"res_{lesson_id}_{uuid.uuid4().hex}_{sanitized}"
    try:
        contents = await file.read()
        save_upload(contents, unique_name, settings.uploads_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db_resource = models.Resource(
        title=title,
        file_url=f"/static/{unique_name}",
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
    current_id = int(getattr(current_user, "id", 0))
    if (
        int(getattr(enrollment, "user_id", 0)) != current_id
        and normalize_role(str(current_user.role)) != "admin"
    ):
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
    unique_name = (
        f"assignment_{lesson_id}_{enrollment_id}_{uuid.uuid4().hex}_{sanitized}"
    )
    try:
        contents = await file.read()
        save_upload(contents, unique_name, settings.uploads_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    submission = crud.create_assignment_submission(
        db,
        enrollment_id=enrollment_id,
        lesson_id=lesson_id,
        file_url=f"/static/{unique_name}",
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
    user_id = int(current_user.id)
    db_user = crud.get_user(db, user_id) or current_user
    enrollments = (
        db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()
    )
    certificates = (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(models.Enrollment.user_id == user_id)
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
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("academy", "study")),
):
    """Devuelve el progreso agregado por curso para un usuario."""
    current_id = int(getattr(current_user, "id", 0))
    if current_id != user_id and normalize_role(str(current_user.role)) not in {
        "admin",
        "coordinador",
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    enrollments = (
        db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()
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
            models.LessonProgress.user_id == user_id,
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
            models.LessonProgress.user_id == user_id,
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
    persona = db.query(models.Persona).filter(models.Persona.id == uuid.UUID(persona_id)).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    if not persona.user_id:
        return {"is_linked": False, "message": "No tiene cuenta de academia vinculada"}

    user_id = persona.user_id
    enrollments = (
        db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()
    )
    certificates = (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(models.Enrollment.user_id == user_id)
        .all()
    )

    user = db.query(models.User).filter(models.User.id == user_id).first()

    return {
        "is_linked": True,
        "user_id": user_id,
        "username": user.username if user else "Unknown",
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
    persona = db.query(models.Persona).filter(models.Persona.id == uuid.UUID(persona_id)).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    if persona.user_id:
        raise HTTPException(
            status_code=400, detail="La persona ya tiene una cuenta vinculada"
        )

    if not persona.email:
        raise HTTPException(
            status_code=400, detail="La persona debe tener un email para crear cuenta"
        )

    # Crear Usuario
    from backend.core.security import get_password_hash

    new_user = models.User(
        username=persona.email.split("@")[0],
        email=persona.email,
        password_hash=get_password_hash(payload.password),
        role="estudiante",
    )
    db.add(new_user)
    db.flush()

    persona.user_id = new_user.id
    db.commit()

    record_admin_action(
        db,
        current_user,
        action="create_member_academy_account",
        resource_type="user",
        resource_id=str(new_user.id),
        metadata={"persona_id": persona_id},
    )

    return {"status": "success", "user_id": new_user.id, "username": new_user.username}


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
    thread_data = schemas.ForumThreadCreate(
        **thread.model_dump(), author_id=current_user.id
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
        user = (
            db.query(models.User).filter(models.User.id == enrollment.user_id).first()
        )
        result.append(
            {
                "id": enrollment.id,
                "user_id": enrollment.user_id,
                "username": user.username if user else "N/A",
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


# ═══════════════════════════════════════════════════════════════════
# REDIRECTS — legacy academy → Academy 2.0
# ═══════════════════════════════════════════════════════════════════
from fastapi.responses import RedirectResponse  # noqa: E402


@router.get("/courses/legacy")
def _redirect_academy_courses():
    return RedirectResponse(url="/api/v2/academy/courses", status_code=307)


@router.get("/courses/legacy/{course_id}")
def _redirect_academy_course(course_id: int):
    return RedirectResponse(url=f"/api/v2/academy/courses/{course_id}", status_code=307)


@router.post("/enrollments/legacy")
def _redirect_academy_enrollments():
    return RedirectResponse(url="/api/v2/academy/enrollments", status_code=307)



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


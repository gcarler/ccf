"""Canonical Academy API.

All person identities and resource identifiers are UUIDs. Student operations are
always scoped to the authenticated persona; administrative operations require an
explicit Academy permission.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, contains_eager, joinedload, selectinload

from backend import models
from backend.core.database import get_db
from backend.core.permissions import (
    get_user_effective_permissions,
    require_module_access,
)
from backend.core.storage import storage_service
from backend.core.uploads import sanitize_filename
from backend.crud.crm import get_user_sede_id
from backend.models_shared import _utcnow
from backend.schemas import academy as schemas

router = APIRouter(prefix="/academy", tags=["Academy"])


class Modality(str, Enum):
    ONLINE = "online"
    PRESENTIAL = "presential"
    HYBRID = "hybrid"


class ContentType(str, Enum):
    VIDEO = "video"
    TEXT = "text"
    DOCUMENT = "document"
    IMAGE = "image"


AcademyReader = Annotated[models.User, Depends(require_module_access("academy", "read"))]
AcademyStudent = Annotated[models.User, Depends(require_module_access("academy", "study"))]
AcademyEditor = Annotated[models.User, Depends(require_module_access("academy", "edit"))]
AcademyManager = Annotated[models.User, Depends(require_module_access("academy", "manage"))]


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    progress_percent: float = Field(ge=0, le=100)
    last_position_seconds: int = Field(default=0, ge=0)


class CoursePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=50)
    title: str = Field(max_length=200)
    description: str | None = None
    modality: Modality = Modality.ONLINE
    is_published: bool = False
    is_self_paced: bool = False
    duration_hours: int = Field(default=0, ge=0)
    cohort_name: str | None = Field(default=None, max_length=100)
    certificate_type: str | None = Field(default=None, max_length=50)
    instructor_name: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=255)
    access_level: Literal["open", "persona", "advanced"] = "persona"


class CourseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    modality: Modality | None = None
    is_published: bool | None = None
    is_self_paced: bool | None = None
    duration_hours: int | None = Field(default=None, ge=0)
    cohort_name: str | None = Field(default=None, max_length=100)
    certificate_type: str | None = Field(default=None, max_length=50)
    instructor_name: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=255)
    access_level: Literal["open", "persona", "advanced"] | None = None


class LessonPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=200)
    content: str = ""
    content_type: ContentType = ContentType.VIDEO
    media_url: str | None = None
    order_index: int = 0
    duration_minutes: int = Field(default=0, ge=0)
    is_published: bool = False


class LessonUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    content: str | None = None
    content_type: ContentType | None = None
    media_url: str | None = None
    order_index: int | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    is_published: bool | None = None


class AssessmentQuestionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    type: str = "multiple_choice"
    points: int = Field(default=1, ge=1)
    options: list[str] = Field(default_factory=list)
    correct_option: int = Field(default=0, ge=0)


class AssessmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: UUID
    lesson_id: UUID | None = None
    title: str = Field(max_length=200)
    description: str | None = None
    passing_score: float = Field(default=70, ge=0, le=100)
    questions: list[AssessmentQuestionPayload] = Field(default_factory=list)


class AssessmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    passing_score: float | None = Field(default=None, ge=0, le=100)


class GradeSubmissionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grade: float = Field(ge=0, le=100)
    feedback: str | None = None


def _can_edit_academy(db: Session, user: models.User) -> bool:
    permissions = get_user_effective_permissions(db, user)
    return "academy:edit" in permissions or "academy:manage" in permissions


def _course_scope(db: Session, user: models.User):
    query = db.query(models.Course).filter(models.Course.deleted_at.is_(None))
    sede_id = get_user_sede_id(db, user.id)
    if sede_id:
        query = query.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
    return query


def _get_scoped_course(db: Session, user: models.User, course_id: UUID) -> models.Course:
    course = _course_scope(db, user).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return course


def _get_own_enrollment(db: Session, user: models.User, enrollment_id: UUID) -> models.Enrollment:
    enrollment = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.id == enrollment_id,
            models.Enrollment.persona_id == user.id,
            models.Enrollment.deleted_at.is_(None),
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return enrollment


def _serialize_course(course: models.Course) -> dict[str, Any]:
    lessons = [lesson for lesson in course.lessons if lesson.deleted_at is None]
    return {
        "id": course.id,
        "code": course.code,
        "slug": course.slug,
        "title": course.title,
        "description": course.description,
        "modality": course.modality,
        "is_published": course.is_published,
        "is_self_paced": course.is_self_paced,
        "duration_hours": course.duration_hours,
        "cohort_name": course.cohort_name,
        "certificate_type": course.certificate_type,
        "xp_per_lesson": course.xp_per_lesson,
        "access_level": course.access_level,
        "image_url": course.image_url,
        "instructor_name": course.instructor_name,
        "created_at": course.created_at,
        "lesson_count": len(lessons),
        "total_minutes": sum(lesson.duration_minutes or 0 for lesson in lessons),
        "lessons": lessons,
    }


def _serialize_enrollment(enrollment: models.Enrollment) -> dict[str, Any]:
    data = {
        "id": enrollment.id,
        "persona_id": enrollment.persona_id,
        "course_id": enrollment.course_id,
        "status": enrollment.status,
        "progress_percent": enrollment.progress_percent,
        "final_grade": enrollment.final_grade,
        "attendance_percent": enrollment.attendance_percent,
        "approved": enrollment.approved,
        "acta_closed": enrollment.acta_closed,
        "certificate_issued": enrollment.certificate_issued,
        "created_at": enrollment.created_at,
    }
    if enrollment.course:
        data["course"] = _serialize_course(enrollment.course)
    return data


@router.get("/courses")
@router.get("/courses/", include_in_schema=False)
def list_courses(
    current_user: AcademyReader,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    modality: str | None = None,
    published_only: bool = True,
    db: Session = Depends(get_db),
):
    query = _course_scope(db, current_user).options(
        selectinload(models.Course.lessons), selectinload(models.Course.prerequisites)
    )
    if modality:
        query = query.filter(models.Course.modality == modality)
    if published_only or not _can_edit_academy(db, current_user):
        query = query.filter(models.Course.is_published.is_(True))
    # sede_id applied via _course_scope helper (Axioma 3)
    return [_serialize_course(course) for course in query.offset(skip).limit(limit).all()]


@router.get("/courses/{course_id}")
def get_course(course_id: UUID, current_user: AcademyReader, db: Session = Depends(get_db)):
    course = (
        _course_scope(db, current_user)
        .options(selectinload(models.Course.lessons).selectinload(models.Lesson.resources))
        .filter(models.Course.id == course_id)
        .first()
    )
    if not course or (not course.is_published and not _can_edit_academy(db, current_user)):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return _serialize_course(course)


@router.get("/courses/{course_id}/lessons")
def list_lessons(
    course_id: UUID,
    current_user: AcademyReader,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    course = _get_scoped_course(db, current_user, course_id)
    query = (
        db.query(models.Lesson)
        .options(selectinload(models.Lesson.resources))
        .filter(models.Lesson.course_id == course.id, models.Lesson.deleted_at.is_(None))
    )
    if not _can_edit_academy(db, current_user):
        query = query.filter(models.Lesson.is_published.is_(True))
    # sede_id applied via parent Course scope (_get_scoped_course filters sede_id)
    return query.order_by(models.Lesson.order_index).offset(skip).limit(limit).all()


@router.get("/courses/{course_id}/assessments")
def list_assessments(
    course_id: UUID,
    current_user: AcademyReader,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _get_scoped_course(db, current_user, course_id)
    query = db.query(models.Assessment).filter(
        models.Assessment.course_id == course_id, models.Assessment.deleted_at.is_(None)
    )
    if not _can_edit_academy(db, current_user):
        query = query.filter(models.Assessment.is_published.is_(True))
    # sede_id applied via parent Course scope (_get_scoped_course filters sede_id)
    return query.offset(skip).limit(limit).all()


@router.get("/assessments/{assessment_id}", response_model=schemas.Assessment)
def get_assessment(assessment_id: UUID, current_user: AcademyStudent, db: Session = Depends(get_db)):
    assessment = (
        db.query(models.Assessment)
        .options(selectinload(models.Assessment.questions).selectinload(models.AssessmentQuestion.options))
        .filter(models.Assessment.id == assessment_id, models.Assessment.deleted_at.is_(None))
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    course = _get_scoped_course(db, current_user, assessment.course_id)
    if not course.is_published and not _can_edit_academy(db, current_user):
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    return assessment


@router.post("/assessments/{assessment_id}/submit")
def submit_assessment(
    assessment_id: UUID,
    payload: schemas.AssessmentAttemptSubmit,
    current_user: AcademyStudent,
    db: Session = Depends(get_db),
):
    # ACAD-LOW-002: aceptar enrollment_id opcional del payload pero siempre derivar
    # el enrollment desde current_user.id. Evita dependency-on-payload y mantiene
    # ownership estricto.
    assessment = (
        db.query(models.Assessment)
        .options(selectinload(models.Assessment.questions).selectinload(models.AssessmentQuestion.options))
        .filter(models.Assessment.id == assessment_id, models.Assessment.deleted_at.is_(None))
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    course = _get_scoped_course(db, current_user, assessment.course_id)
    if not course.is_published:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    enrollment = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.course_id == assessment.course_id,
            models.Enrollment.deleted_at.is_(None),
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=403, detail="Debes estar inscrito en el curso")

    answer_by_question = {str(answer.question_id): answer for answer in payload.answers or []}
    points_awarded = 0.0
    total_points = float(sum(question.points or 0 for question in assessment.questions))
    attempt = models.AssessmentAttempt(assessment_id=assessment.id, enrollment_id=enrollment.id, score=0, passed=False)
    db.add(attempt)
    db.flush()

    for question in assessment.questions:
        submitted = answer_by_question.get(str(question.id))
        selected = None
        correct = False
        if submitted and submitted.selected_option_id:
            selected = next(
                (option for option in question.options if str(option.id) == submitted.selected_option_id),
                None,
            )
            correct = bool(selected and selected.is_correct)
        awarded = float(question.points or 0) if correct else 0.0
        points_awarded += awarded
        db.add(
            models.AssessmentAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_id=selected.id if selected else None,
                text_response=submitted.text_response if submitted else None,
                is_correct=correct if submitted else None,
                points_awarded=awarded,
            )
        )

    score = round((points_awarded / total_points) * 100, 2) if total_points else 0.0
    attempt.score = score
    attempt.passed = score >= float(assessment.passing_score)
    enrollment.final_grade = score
    enrollment.approved = attempt.passed
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/lessons/{lesson_id}/progress")
def get_lesson_progress(lesson_id: UUID, current_user: AcademyStudent, db: Session = Depends(get_db)):
    lesson = db.query(models.Lesson).filter(
        models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    _get_scoped_course(db, current_user, lesson.course_id)
    if not lesson.is_published:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    progress = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.persona_id == current_user.id,
            models.LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    return progress or {
        "progress_percent": 0.0,
        "last_position_seconds": 0,
        "is_completed": False,
    }


@router.post("/lessons/{lesson_id}/progress")
def update_lesson_progress(
    lesson_id: UUID,
    payload: ProgressUpdate,
    current_user: AcademyStudent,
    db: Session = Depends(get_db),
):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    _get_scoped_course(db, current_user, lesson.course_id)
    if not lesson.is_published:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    enrollment = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.course_id == lesson.course_id,
            models.Enrollment.deleted_at.is_(None),
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=403, detail="Debes estar inscrito en el curso")
    progress = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.persona_id == current_user.id,
            models.LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    if not progress:
        progress = models.LessonProgress(persona_id=current_user.id, lesson_id=lesson_id)
        db.add(progress)
    progress.progress_percent = payload.progress_percent
    progress.last_position_seconds = payload.last_position_seconds
    progress.is_completed = payload.progress_percent >= 100
    db.flush()

    lesson_ids = [
        row[0]
        for row in db.query(models.Lesson.id).filter(
            models.Lesson.course_id == lesson.course_id,
            models.Lesson.deleted_at.is_(None),
            models.Lesson.is_published.is_(True),
        )
    ]
    completed = 0
    if lesson_ids:
        completed = (
            db.query(models.LessonProgress)
            .filter(
                models.LessonProgress.persona_id == current_user.id,
                models.LessonProgress.lesson_id.in_(lesson_ids),
                models.LessonProgress.is_completed.is_(True),
            )
            .count()
        )
    enrollment.progress_percent = round((completed / len(lesson_ids)) * 100, 2) if lesson_ids else 0
    if enrollment.progress_percent >= 100:
        enrollment.status = "completed"
        enrollment.completed_at = _utcnow()
    db.commit()
    db.refresh(progress)
    return progress


@router.post("/enrollments", status_code=status.HTTP_201_CREATED)
@router.post("/enrollments/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_enrollment(
    payload: schemas.EnrollmentCreate,
    current_user: AcademyStudent,
    db: Session = Depends(get_db),
):
    if payload.persona_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sólo puedes crear tu propia inscripción")
    course = _get_scoped_course(db, current_user, payload.course_id)
    if not course.is_published:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    existing = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.course_id == course.id,
        )
        .first()
    )
    if existing and existing.deleted_at is None:
        return _serialize_enrollment(existing)
    if existing:
        existing.deleted_at = None
        existing.status = "active"
        enrollment = existing
    else:
        enrollment = models.Enrollment(persona_id=current_user.id, course_id=course.id)
        db.add(enrollment)
    db.add(
        models.AcademyActivityLog(
            event_type="enrollment",
            course_id=course.id,
            persona_id=current_user.id,
            modality=course.modality,
        )
    )
    db.commit()
    db.refresh(enrollment)
    return _serialize_enrollment(enrollment)


@router.get("/me/enrollments")
def my_enrollments(
    current_user: AcademyStudent,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    enrollments = (
        db.query(models.Enrollment)
        .options(joinedload(models.Enrollment.course).selectinload(models.Course.lessons))
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.deleted_at.is_(None),
        )
        .order_by(models.Enrollment.created_at.desc())
        # Aislado por boundary de persona_id; las inscripciones son del usuario autenticado
        # y create_enrollment las crea bajo _get_scoped_course, por lo que un leak
        # cross-sede NO es posible (Axioma 3).
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize_enrollment(enrollment) for enrollment in enrollments]


@router.get("/enrollments")
def all_enrollments(
    current_user: AcademyManager,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    sede_id = get_user_sede_id(db, current_user.id)
    query = (
        db.query(models.Enrollment)
        .join(models.Course)
        .filter(models.Enrollment.deleted_at.is_(None), models.Course.deleted_at.is_(None))
    )
    if sede_id:
        query = query.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
    return [_serialize_enrollment(enrollment) for enrollment in query.offset(skip).limit(limit).all()]


@router.post("/enrollments/{enrollment_id}/check-in")
def check_in(enrollment_id: UUID, current_user: AcademyStudent, db: Session = Depends(get_db)):
    enrollment = _get_own_enrollment(db, current_user, enrollment_id)
    today = date.today()
    attendance = (
        db.query(models.CourseAttendance)
        .filter(
            models.CourseAttendance.enrollment_id == enrollment.id,
            func.date(models.CourseAttendance.session_date) == today,
        )
        .first()
    )
    if not attendance:
        attendance = models.CourseAttendance(
            enrollment_id=enrollment.id,
            recorded_by_persona_id=current_user.id,
            status="present",
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
    return attendance


@router.get("/me/progress")
def my_progress(
    current_user: AcademyStudent,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    enrollments = (
        db.query(models.Enrollment)
        .options(joinedload(models.Enrollment.course))
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.deleted_at.is_(None),
        )
        # Aislado por boundary de persona_id; cada progreso pertenece al usuario actual.
        # No hace falta defensive JOIN porque un mismo persona_id nunca comparte datos
        # con cursos de otra sede a través de este endpoint (Axioma 3).
        .offset(skip)
        .limit(limit)
        .all()
    )
    course_ids = [enrollment.course_id for enrollment in enrollments]
    total_lessons_map: dict[UUID, int] = {}
    completed_map: dict[UUID, int] = {}
    if course_ids:
        total_rows = (
            db.query(
                models.Lesson.course_id,
                func.count(models.Lesson.id).label("cnt"),
            )
            .filter(
                models.Lesson.course_id.in_(course_ids),
                models.Lesson.deleted_at.is_(None),
                models.Lesson.is_published.is_(True),
            )
            .group_by(models.Lesson.course_id)
            .all()
        )
        total_lessons_map = {row.course_id: row.cnt for row in total_rows}
        completed_rows = (
            db.query(
                models.Lesson.course_id,
                func.count(models.LessonProgress.id).label("cnt"),
            )
            .join(models.Lesson, models.LessonProgress.lesson_id == models.Lesson.id)
            .filter(
                models.LessonProgress.persona_id == current_user.id,
                models.Lesson.course_id.in_(course_ids),
                models.LessonProgress.is_completed.is_(True),
            )
            .group_by(models.Lesson.course_id)
            .all()  # sede_id scoped via persona_id boundary (Axioma 3) + course_ids
        )
        completed_map = {row.course_id: row.cnt for row in completed_rows}
    result = []
    for enrollment in enrollments:
        result.append(
            {
                "id": enrollment.course_id,
                "title": enrollment.course.title,
                "progress_percent": enrollment.progress_percent,
                "status": enrollment.status,
                "average_grade": enrollment.final_grade or 0,
                "lessons_completed": completed_map.get(enrollment.course_id, 0),
                "total_lessons": total_lessons_map.get(enrollment.course_id, 0),
                "last_activity": enrollment.updated_at,
                "certificate_issued": enrollment.certificate_issued,
            }
        )
    return result


@router.get("/me/profile")
def my_profile(current_user: AcademyStudent, db: Session = Depends(get_db)):
    enrollments = (
        db.query(models.Enrollment)
        .options(joinedload(models.Enrollment.course))
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.deleted_at.is_(None),
            # Aislado por boundary de persona_id (Axioma 3). Los JOINs con Course son
            # solo para hidratación y no abren puerta a leak cross-sede.
        )
        .all()
    )
    certificates = (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.deleted_at.is_(None),
            # Aislado por boundary de persona_id (Axioma 3). Mismo razonamiento que arriba.
        )
        .all()
    )
    average = (
        sum(enrollment.progress_percent or 0 for enrollment in enrollments) / len(enrollments) if enrollments else 0
    )
    return {
        "persona_id": current_user.id,
        "username": current_user.username or current_user.email or "",
        "total_progress": round(average, 2),
        "enrollments_count": len(enrollments),
        "certificates_count": len(certificates),
        "active_courses": [_serialize_enrollment(enrollment) for enrollment in enrollments],
        "recent_certificates": certificates[:5],
    }


@router.get("/me/certificates")
def my_certificates(
    current_user: AcademyStudent,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    user_sede = get_user_sede_id(db, current_user.id)
    query = (
        db.query(models.Certificate, models.Course.title)
        .join(models.Enrollment, models.Certificate.enrollment_id == models.Enrollment.id)
        .join(models.Course, models.Enrollment.course_id == models.Course.id)
        .filter(
            models.Enrollment.persona_id == current_user.id,
            models.Enrollment.deleted_at.is_(None),
        )
    )
    if user_sede is not None:
        # ``Enrollment`` no tiene ``sede_id`` propio; la sede vive en ``Course``
        # (ya joined arriba). Filtramos a través de la relación para mantener
        # el aislamiento por sede sin romper la query.
        query = query.filter(models.Course.sede_id == user_sede)
    rows = query.offset(skip).limit(limit).all()
    return [
        {
            "id": certificate.id,
            "enrollment_id": certificate.enrollment_id,
            "certificate_code": certificate.certificate_code,
            "certificate_type": certificate.certificate_type,
            "course_title": course_title,
            "issued_at": certificate.issued_at,
        }
        for certificate, course_title in rows
    ]


@router.post("/enrollments/{enrollment_id}/request-certificate")
def request_certificate(enrollment_id: UUID, current_user: AcademyStudent, db: Session = Depends(get_db)):
    enrollment = _get_own_enrollment(db, current_user, enrollment_id)
    if enrollment.status != "completed" and not enrollment.approved:
        raise HTTPException(status_code=400, detail="El curso todavía no está aprobado")
    existing = db.query(models.Certificate).filter(models.Certificate.enrollment_id == enrollment.id).first()
    if existing:
        return existing
    code = f"CCF-ACA-{enrollment.id.hex[:12].upper()}"
    certificate = models.Certificate(
        enrollment_id=enrollment.id,
        certificate_code=code,
        certificate_type=enrollment.course.certificate_type if enrollment.course else None,
    )
    enrollment.certificate_issued = True
    enrollment.certificate_code = code
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


@router.get("/certificates/validate/{code}")
def validate_certificate(code: str, db: Session = Depends(get_db)):
    certificate = db.query(models.Certificate).filter(models.Certificate.certificate_code == code).first()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    return certificate


@router.post("/lessons/{lesson_id}/submit-assignment")
async def submit_assignment(
    lesson_id: UUID,
    current_user: AcademyStudent,
    enrollment_id: UUID = Form(...),
    comment: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    enrollment = _get_own_enrollment(db, current_user, enrollment_id)
    lesson = (
        db.query(models.Lesson)
        .filter(
            models.Lesson.id == lesson_id,
            models.Lesson.course_id == enrollment.course_id,
            models.Lesson.deleted_at.is_(None),
        )
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    ALLOWED_TYPES = {
        "application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain", "text/csv",
    }
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Tipo de archivo no permitido")
    MAX_SIZE = 10 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=422, detail="El archivo excede el límite de 10 MB")
    url = storage_service.save_file_original(
        contents, sanitize_filename(file.filename or "assignment"), subfolder="academy"
    )
    submission = models.AssignmentSubmission(
        enrollment_id=enrollment.id,
        lesson_id=lesson.id,
        file_url=url,
        comment=comment,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/forum/threads")
def forum_threads(
    current_user: AcademyStudent,
    category: schemas.ForumCategory | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    # Axioma 3: ForumThread.course_id IS NULL → anuncio global (visible a todas las sedes).
    # Hilos vinculados a Course: scope por Course.sede_id via outerjoin (preserva huerfanos).
    # Hilos de cursos con deleted_at != NULL quedan ocultos automáticamente.
    query = db.query(models.ForumThread).outerjoin(models.Course, models.ForumThread.course_id == models.Course.id)
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id:
        course_scope = and_(
            models.Course.deleted_at.is_(None),
            or_(
                models.Course.sede_id == sede_id,
                models.Course.sede_id.is_(None),
            ),
        )
    else:
        # Superadmin sin sede: ve cursos no borrados + huerfanos.
        course_scope = models.Course.deleted_at.is_(None)
    query = query.filter(or_(models.ForumThread.course_id.is_(None), course_scope))
    if category is not None:
        query = query.filter(models.ForumThread.category == category.value)
    return query.order_by(models.ForumThread.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/forum/threads", status_code=status.HTTP_201_CREATED)
def create_forum_thread(
    payload: schemas.ForumThreadCreate,
    current_user: AcademyStudent,
    db: Session = Depends(get_db),
):
    # ACAD-MED-001: solo Editor/Manager pueden publicar hilos globales (course_id=None).
    # Esto evita que cualquier Student cree anuncios cross-sede o ruido global.
    if payload.course_id is None:
        permissions = get_user_effective_permissions(db, current_user)
        if "academy:edit" not in permissions and "academy:manage" not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Solo Editor/Manager pueden publicar hilos globales del foro",
            )
    if payload.course_id:
        _get_scoped_course(db, current_user, payload.course_id)
    thread = models.ForumThread(
        course_id=payload.course_id,
        author_persona_id=current_user.id,
        title=payload.title,
        category=payload.category,
        content=payload.content or payload.title,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.patch("/forum/threads/{thread_id}/resolve")
def resolve_forum_thread(
    thread_id: UUID,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    # ACAD-MED-002: alternar is_resolved. Solo Editor/Manager.
    thread = db.query(models.ForumThread).filter(models.ForumThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo no encontrado")
    if thread.course_id:
        _get_scoped_course(db, current_user, thread.course_id)
    thread.is_resolved = not bool(thread.is_resolved)
    db.add(
        models.AcademyActivityLog(
            event_type="forum_resolved",
            course_id=thread.course_id,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={"thread_id": str(thread.id), "is_resolved": thread.is_resolved},
        )
    )
    db.commit()
    db.refresh(thread)
    return thread


def _get_scoped_forum_thread(db: Session, current_user: models.User, thread_id: UUID):
    thread = db.query(models.ForumThread).filter(models.ForumThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo no encontrado")
    if thread.course_id:
        _get_scoped_course(db, current_user, thread.course_id)
    return thread


@router.get("/forum/threads/{thread_id}")
def get_forum_thread(
    thread_id: UUID,
    current_user: AcademyStudent,
    db: Session = Depends(get_db),
):
    return _get_scoped_forum_thread(db, current_user, thread_id)


@router.get("/forum/threads/{thread_id}/comments", response_model=list[schemas.ForumCommentRead])
def list_forum_comments(
    thread_id: UUID,
    current_user: AcademyStudent,
    db: Session = Depends(get_db),
):
    _get_scoped_forum_thread(db, current_user, thread_id)
    return (
        db.query(models.ForumComment)
        .filter(models.ForumComment.thread_id == thread_id)
        .order_by(models.ForumComment.created_at.asc())
        .all()
    )


@router.post("/forum/threads/{thread_id}/comments", response_model=schemas.ForumCommentRead, status_code=status.HTTP_201_CREATED)
def create_forum_comment(
    thread_id: UUID,
    payload: schemas.ForumCommentCreate,
    current_user: AcademyStudent,
    db: Session = Depends(get_db),
):
    _get_scoped_forum_thread(db, current_user, thread_id)
    if payload.parent_id:
        parent = db.query(models.ForumComment).filter(
            models.ForumComment.id == payload.parent_id,
            models.ForumComment.thread_id == thread_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Comentario padre no encontrado")
    comment = models.ForumComment(
        thread_id=thread_id,
        parent_id=payload.parent_id,
        author_persona_id=current_user.id,
        content=payload.content.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def _get_scoped_lesson(
    db: Session,
    current_user: models.User,
    lesson_id: UUID,
    *,
    require_published: bool,
) -> models.Lesson:
    """Resuelve una lección por la frontera Course→sede, nunca por UUID aislado."""
    lesson = db.query(models.Lesson).filter(
        models.Lesson.id == lesson_id,
        models.Lesson.deleted_at.is_(None),
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    _get_scoped_course(db, current_user, lesson.course_id)
    if require_published and not lesson.is_published and not _can_edit_academy(db, current_user):
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    return lesson


@router.get("/lessons/{lesson_id}/resources", response_model=list[schemas.Resource])
def list_lesson_resources(
    lesson_id: UUID,
    current_user: AcademyReader,
    db: Session = Depends(get_db),
):
    lesson = _get_scoped_lesson(db, current_user, lesson_id, require_published=True)
    return (
        db.query(models.Resource)
        .filter(models.Resource.lesson_id == lesson.id, models.Resource.deleted_at.is_(None))
        .order_by(models.Resource.created_at.asc())
        .all()
    )


@router.post("/admin/lessons/{lesson_id}/resources", response_model=schemas.Resource, status_code=status.HTTP_201_CREATED)
def create_lesson_resource(
    lesson_id: UUID,
    payload: schemas.ResourceCreate,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    lesson = _get_scoped_lesson(db, current_user, lesson_id, require_published=False)
    resource = models.Resource(lesson_id=lesson.id, **payload.model_dump())
    db.add(resource)
    db.add(
        models.AcademyActivityLog(
            event_type="lesson_resource_created",
            course_id=lesson.course_id,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={"resource_id": str(resource.id), "lesson_id": str(lesson.id)},
        )
    )
    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/admin/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_lesson_resource(
    resource_id: UUID,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    resource = db.query(models.Resource).filter(
        models.Resource.id == resource_id,
        models.Resource.deleted_at.is_(None),
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    lesson = _get_scoped_lesson(db, current_user, resource.lesson_id, require_published=False)
    resource.deleted_at = _utcnow()
    db.add(
        models.AcademyActivityLog(
            event_type="lesson_resource_archived",
            course_id=lesson.course_id,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={"resource_id": str(resource.id), "lesson_id": str(lesson.id)},
        )
    )
    db.commit()


@router.get("/schedule")
def academy_schedule(
    current_user: AcademyStudent,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    # sede_id applied via _course_scope helper (Axioma 3)
    courses = _course_scope(db, current_user).filter(models.Course.is_published.is_(True)).offset(skip).limit(limit).all()
    return [
        {
            "id": course.id,
            "title": course.title,
            "modality": course.modality,
            "cohort_name": course.cohort_name,
            "duration_hours": course.duration_hours,
        }
        for course in courses
    ]


@router.get("/personas")
def academy_personas(
    current_user: AcademyManager,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    role: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Persona).filter(models.Persona.deleted_at.is_(None))
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id:
        query = query.filter(models.Persona.sede_id == sede_id)
    if role:
        # ACAD-LOW-007: filtrar por nombre de rol canónico (member / staff / admin / etc.)
        # El modelo Persona no persiste role directo; se resuelve en runtime vía
        # ``UsuarioRolPlataforma`` para mantener una sola fuente de verdad.
        from backend.models_auth import RolPlataforma, UsuarioRolModulo

        persona_ids_with_role = {
            row[0]
            for row in (
                db.query(UsuarioRolModulo.user_id)
                .join(RolPlataforma, RolPlataforma.id == UsuarioRolModulo.rol_id)
                .filter(
                    RolPlataforma.nombre == role,
                    UsuarioRolModulo.deleted_at.is_(None),
                )
                .all()
            )
        }
        if persona_ids_with_role:
            query = query.filter(models.Persona.id.in_(persona_ids_with_role))
        else:
            # Si el rol no existe, no devolvemos personas (evita leak accidental).
            query = query.filter(False)
    personas = query.order_by(models.Persona.first_name, models.Persona.last_name).offset(skip).limit(limit).all()
    return [
        {
            "id": persona.id,
            "persona_id": persona.id,
            "username": " ".join(part for part in [persona.first_name, persona.last_name] if part),
            "email": persona.email,
            "role": role or "student",
            "is_active": True,
        }
        for persona in personas
    ]


@router.get("/dashboard/metrics")
def dashboard_metrics(current_user: AcademyManager, db: Session = Depends(get_db)):
    courses = _course_scope(db, current_user)
    # sede_id applied via _course_scope helper (Axioma 3)
    course_ids = [row[0] for row in courses.with_entities(models.Course.id).all()]
    enrollments = (
        db.query(models.Enrollment).filter(
            models.Enrollment.course_id.in_(course_ids), models.Enrollment.deleted_at.is_(None)
        )
        if course_ids
        else db.query(models.Enrollment).filter(False)
    )
    total = enrollments.count()
    completed = enrollments.filter(models.Enrollment.status == "completed").count()
    certificates = (
        db.query(models.Certificate).join(models.Enrollment).filter(models.Enrollment.course_id.in_(course_ids)).count()
        if course_ids
        else 0
    )
    completion_rate = round((completed / total) * 100, 2) if total else 0
    # ACAD-CRIT-002: enrollment_trends (nuevas matrículas por mes) + top_courses (N cursos con m\u00e1s matr\u00edculas)
    enrollment_trends: list[dict[str, Any]] = []
    if course_ids:
        # Acotamos a últimos 12 meses para no crecer indefinidamente
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        monthly = (
            db.query(
                func.date_trunc("month", models.Enrollment.created_at).label("month"),
                func.count(models.Enrollment.id).label("count"),
            )
            .filter(
                models.Enrollment.course_id.in_(course_ids),
                models.Enrollment.deleted_at.is_(None),
                models.Enrollment.created_at >= cutoff,
            )
            .group_by("month")
            .order_by("month")
            .all()  # sede_id scoped via _course_scope(course_ids)
        )
        for month_value, count_value in monthly:
            enrollment_trends.append(
                {
                    "label": month_value.strftime("%Y-%m"),
                    "value": int(count_value or 0),
                }
            )
    top_courses: list[dict[str, Any]] = []
    if course_ids:
        top_rows = (
            db.query(
                models.Course.title,
                func.count(models.Enrollment.id).label("count"),
            )
            .join(models.Enrollment, models.Enrollment.course_id == models.Course.id)
            .filter(
                models.Course.id.in_(course_ids),
                models.Enrollment.deleted_at.is_(None),
            )
            .group_by(models.Course.title)
            .order_by(func.count(models.Enrollment.id).desc())
            .limit(5)
            .all()  # sede_id scoped via _course_scope(course_ids)
        )
        for title, count_value in top_rows:
            top_courses.append({"title": title, "count": int(count_value or 0)})
    return {
        "active_students": total,
        "completion_rate": completion_rate,
        "certificates_issued": certificates,
        "total_courses": len(course_ids),
        "total_enrollments": total,
        "completed_enrollments": completed,
        "cards": [
            {"title": "Cursos", "value": str(len(course_ids)), "trend": "", "color": "blue"},
            {"title": "Estudiantes", "value": str(total), "trend": "", "color": "green"},
            {"title": "Finalización", "value": f"{completion_rate}%", "trend": "", "color": "amber"},
        ],
        # Nuevos campos — alimentación del AcademyClient.tsx (ACAD-CRIT-002)
        "enrollment_trends": enrollment_trends,
        "top_courses": top_courses,
    }


@router.get("/dashboard/pilot-readiness")
def pilot_readiness(current_user: AcademyManager):
    checklist = [
        {"key": "uuid", "label": "Identidad UUID", "completed": True},
        {"key": "permissions", "label": "Permisos por módulo", "completed": True},
        {"key": "schema", "label": "Esquema Academy único", "completed": True},
    ]
    return {"environment_ready": True, "readiness_score": 100, "checklist": checklist}


@router.get("/admin/submissions")
def list_submissions(
    current_user: AcademyEditor,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    # Axioma 3 — Multi-Tenant: las entregas SOLO se listan para cursos del scope del editor.
    # Join con Course (a través de Lesson) + filtro sede_id; los cursos globales (sede_id IS NULL)
    # son visibles para todos los editores con sede; un superadmin sin sede ve TODO lo no borrado.
    # ACAD-MED-003-FOLLOWUP: ocultamos entregas archivadas (soft-deleted) para que
    # el archivado desde ``delete_submission_admin`` se refleje en la lista.
    rows = (
        db.query(models.AssignmentSubmission, models.Lesson.title, models.Persona)
        .join(models.Lesson, models.AssignmentSubmission.lesson_id == models.Lesson.id)
        .join(models.Course, models.Lesson.course_id == models.Course.id)
        .join(models.Enrollment, models.AssignmentSubmission.enrollment_id == models.Enrollment.id)
        .join(models.Persona, models.Enrollment.persona_id == models.Persona.id)
        .filter(
            models.Course.deleted_at.is_(None),
            models.AssignmentSubmission.deleted_at.is_(None),
        )
    )
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id:
        rows = rows.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
    rows = rows.limit(limit).all()
    return [
        {
            "id": submission.id,
            "enrollment_id": submission.enrollment_id,
            "lesson_id": submission.lesson_id,
            "student_name": " ".join(part for part in [persona.first_name, persona.last_name] if part),
            "lesson_title": lesson_title,
            "file_url": submission.file_url,
            "comment": submission.comment,
            "grade": submission.grade,
            "teacher_feedback": submission.teacher_feedback,
            "submitted_at": submission.created_at,
        }
        for submission, lesson_title, persona in rows
    ]


@router.patch("/admin/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: UUID,
    current_user: AcademyEditor,
    payload: GradeSubmissionPayload,
    db: Session = Depends(get_db),
):
    # Axioma 3 — Multi-Tenant: una entrega sólo puede mutarse si su Course pertenece
    # al scope del editor. Aplicamos el filtro de sede en la propia JOIN (Submission→
    # Lesson→Course) para que un editor de sede_a NO pueda leer/escribir entregas de
    # sede_b simplemente conociendo el submission_id.
    query = (
        db.query(models.AssignmentSubmission)
        .join(models.Lesson, models.AssignmentSubmission.lesson_id == models.Lesson.id)
        .join(models.Course, models.Lesson.course_id == models.Course.id)
        .filter(
            models.AssignmentSubmission.id == submission_id,
            # ACAD-MED-003-FOLLOWUP: bloquea calificar entregas archivadas.
            # Sin este filtro un editor podría mutar notas en submissions
            # ya retiradas de la lista, contradiciendo el archivado.
            models.AssignmentSubmission.deleted_at.is_(None),
            models.Course.deleted_at.is_(None),
            models.Lesson.deleted_at.is_(None),
        )
    )
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id:
        query = query.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
    submission = query.first()
    if not submission:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    submission.grade = payload.grade
    submission.teacher_feedback = payload.feedback
    db.add(
        models.AcademyActivityLog(
            event_type="submission_graded",
            course_id=None,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={
                "submission_id": str(submission.id),
                "lesson_id": str(submission.lesson_id),
                "grade": payload.grade,
                "feedback": payload.feedback,
            },
        )
    )
    db.commit()
    db.refresh(submission)
    return submission


@router.post("/admin/courses", status_code=status.HTTP_201_CREATED)
def create_course_admin(payload: CoursePayload, current_user: AcademyEditor, db: Session = Depends(get_db)):
    course = models.Course(**payload.model_dump(), sede_id=get_user_sede_id(db, current_user.id))
    db.add(course)
    db.commit()
    db.refresh(course)
    return _serialize_course(course)


@router.patch("/admin/courses/{course_id}")
def update_course_admin(
    course_id: UUID,
    payload: CourseUpdate,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    course = _get_scoped_course(db, current_user, course_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(course, key, value)
    course.updated_at = _utcnow()
    db.add(
        models.AcademyActivityLog(
            event_type="course_updated",
            course_id=course.id,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={"changes": list(changes.keys())},
        )
    )
    db.commit()
    db.refresh(course)
    return _serialize_course(course)


@router.delete("/admin/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_course_admin(course_id: UUID, current_user: AcademyManager, db: Session = Depends(get_db)):
    course = _get_scoped_course(db, current_user, course_id)
    course.deleted_at = _utcnow()
    db.add(
        models.AcademyActivityLog(
            event_type="course_archived",
            course_id=course.id,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={"course_code": course.code, "course_title": course.title},
        )
    )
    db.commit()


@router.get("/admin/courses/{course_id}/students")
def course_students(course_id: UUID, current_user: AcademyEditor, db: Session = Depends(get_db)):
    _get_scoped_course(db, current_user, course_id)
    user_sede = get_user_sede_id(db, current_user.id)
    query = (
        db.query(models.Enrollment)
        .options(joinedload(models.Enrollment.persona))
        .filter(
            models.Enrollment.course_id == course_id,
            models.Enrollment.deleted_at.is_(None),
        )
    )
    if user_sede is not None:
        # ``Enrollment`` no tiene ``sede_id`` propio; la sede vive en ``Course``
        # (ya joined arriba). Filtramos a través de la relación para mantener
        # el aislamiento por sede sin romper la query.
        query = query.filter(models.Course.sede_id == user_sede)
    enrollments = query.all()
    enrollment_ids = [e.id for e in enrollments]
    attendance_map: dict[UUID, int] = {}
    if enrollment_ids:
        attendance_rows = (
            db.query(
                models.CourseAttendance.enrollment_id,
                func.count(models.CourseAttendance.id).label("cnt"),
            )
            .filter(
                models.CourseAttendance.enrollment_id.in_(enrollment_ids),
                models.CourseAttendance.status == "present",
            )
            .group_by(models.CourseAttendance.enrollment_id)
            .all()
        )
        attendance_map = {row.enrollment_id: row.cnt for row in attendance_rows}
    return [
        {
            "id": enrollment.id,
            "enrollment_id": enrollment.id,
            "persona_id": enrollment.persona_id,
            "username": " ".join(
                part for part in [enrollment.persona.first_name, enrollment.persona.last_name] if part
            ),
            "email": enrollment.persona.email,
            "status": enrollment.status,
            "progress": enrollment.progress_percent,
            "progress_percent": enrollment.progress_percent,
            "attendance_count": attendance_map.get(enrollment.id, 0),
            "average_grade": enrollment.final_grade or 0,
            "approved": enrollment.approved,
        }
        for enrollment in enrollments
    ]


@router.post("/admin/courses/{course_id}/lessons", status_code=status.HTTP_201_CREATED)
def create_lesson_admin(
    course_id: UUID,
    payload: LessonPayload,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    _get_scoped_course(db, current_user, course_id)
    lesson = models.Lesson(course_id=course_id, **payload.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.patch("/admin/lessons/{lesson_id}")
def update_lesson_admin(
    lesson_id: UUID,
    payload: LessonUpdate,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    _get_scoped_course(db, current_user, lesson.course_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lesson, key, value)
    lesson.updated_at = _utcnow()
    db.add(
        models.AcademyActivityLog(
            event_type="lesson_updated",
            course_id=lesson.course_id,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={"lesson_id": str(lesson.id), "changes": list(payload.model_dump(exclude_unset=True).keys())},
        )
    )
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/admin/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_lesson_admin(lesson_id: UUID, current_user: AcademyEditor, db: Session = Depends(get_db)):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    _get_scoped_course(db, current_user, lesson.course_id)
    lesson.deleted_at = _utcnow()
    db.add(
        models.AcademyActivityLog(
            event_type="lesson_archived",
            course_id=lesson.course_id,
            persona_id=current_user.id,
            modality=None,
            value=0,
            payload_json={"lesson_id": str(lesson.id), "lesson_title": lesson.title},
        )
    )
    db.commit()


@router.delete("/admin/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission_admin(
    submission_id: UUID,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    """ACAD-MED-003: soft delete de una entrega (Regla 4 del proyecto, regla.platform).
    Editor/Manager puede retractarla. El campo `deleted_at` de ``AssignmentSubmission``
    se setea con ``_utcnow()`` siguiendo el patrón canónico de
    ``backend/crud/crm_/milestones.py::delete_milestone``.

    ACAD-MED-003-FOLLOWUP (cierre): antes del archivado escribimos un evento en
    ``AcademyActivityLog`` con ``event_type="assignment_submission_archived"`` y
    ``payload_json`` conteniendo ``file_url``, ``lesson_id``, ``enrollment_id``,
    ``archived_at`` y ``archived_by_persona_id``. Esto cierra el ciclo para que un
    futuro job batch de purga de Seaweed pueda listar huérfanos consultando por
    ``event_type`` (índice existente) y leyendo el JSON.
    """
    submission = (
        db.query(models.AssignmentSubmission)
        .options(contains_eager(models.AssignmentSubmission.lesson))
        .join(models.Lesson, models.AssignmentSubmission.lesson_id == models.Lesson.id)
        .join(models.Course, models.Lesson.course_id == models.Course.id)
        .filter(
            models.AssignmentSubmission.id == submission_id,
            models.AssignmentSubmission.deleted_at.is_(None),
            models.Course.deleted_at.is_(None),
            models.Lesson.deleted_at.is_(None),
        )
    )
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id:
        submission = submission.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
    row = submission.first()
    if not row:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    # ACAD-MED-003 (Regla 4): soft delete via deleted_at, NO db.delete(). Esto
    # preserva audit + integridad referencial y mantiene el modelo coherente con
    # ``Course``, ``Lesson`` y demás entidades transaccionales.
    archived_at = _utcnow()
    row.deleted_at = archived_at
    db.add(
        models.AcademyActivityLog(
            event_type="assignment_submission_archived",
            course_id=row.lesson.course_id if row.lesson else None,
            persona_id=current_user.id,
            modality=None,
            value=0,
            # ACAD-MED-003-FOLLOWUP (cierre): payload_json conserva el file_url
            # completo (que no cabe en String(20) de modality) + FKs para el job
            # batch de purga de Seaweed.
            payload_json={
                "submission_id": str(row.id),
                "file_url": row.file_url,
                "lesson_id": str(row.lesson_id) if row.lesson_id else None,
                "enrollment_id": str(row.enrollment_id) if row.enrollment_id else None,
                "archived_at": archived_at.isoformat(),
                "archived_by_persona_id": str(current_user.id),
            },
        )
    )
    db.commit()


@router.post("/admin/assessments", status_code=status.HTTP_201_CREATED)
def create_assessment_admin(
    payload: AssessmentPayload,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    _get_scoped_course(db, current_user, payload.course_id)
    if payload.lesson_id is not None:
        lesson_check = db.query(models.Lesson).filter(
            models.Lesson.id == payload.lesson_id,
            models.Lesson.course_id == payload.course_id,
            models.Lesson.deleted_at.is_(None),
        ).first()
        if not lesson_check:
            raise HTTPException(status_code=422, detail="La lección no pertenece a este curso")
    assessment = models.Assessment(
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        title=payload.title,
        description=payload.description,
        passing_score=payload.passing_score,
        max_score=100,
        is_published=True,
    )
    db.add(assessment)
    db.flush()
    for index, item in enumerate(payload.questions):
        question = models.AssessmentQuestion(
            assessment_id=assessment.id,
            question_text=item.text,
            question_type=item.type,
            points=item.points,
            order_index=index,
        )
        db.add(question)
        db.flush()
        for option_index, option_text in enumerate(item.options):
            db.add(
                models.AssessmentOption(
                    question_id=question.id,
                    option_text=option_text,
                    is_correct=option_index == item.correct_option,
                )
            )
    db.commit()
    db.refresh(assessment)
    return assessment


@router.patch("/admin/assessments/{assessment_id}")
def update_assessment_admin(
    assessment_id: UUID,
    payload: AssessmentUpdate,
    current_user: AcademyEditor,
    db: Session = Depends(get_db),
):
    assessment = (
        db.query(models.Assessment)
        .filter(models.Assessment.id == assessment_id, models.Assessment.deleted_at.is_(None))
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    _get_scoped_course(db, current_user, assessment.course_id)
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes:
        assessment.title = str(changes["title"])
    if "passing_score" in changes:
        assessment.passing_score = float(changes["passing_score"])
    assessment.updated_at = _utcnow()
    db.commit()
    db.refresh(assessment)
    return assessment

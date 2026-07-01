"""Canonical data access for Academy UUID resources."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from backend import models
from backend.models_shared import _utcnow
from backend.schemas import academy as schemas


def list_courses(
    db: Session,
    *,
    sede_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    modality: str | None = None,
    published_only: bool = True,
) -> list[models.Course]:
    query = db.query(models.Course).options(
        selectinload(models.Course.lessons),
        selectinload(models.Course.prerequisites),
    ).filter(models.Course.deleted_at.is_(None))
    if sede_id:
        query = query.filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None))
        )
    if modality:
        query = query.filter(models.Course.modality == modality)
    if published_only:
        query = query.filter(models.Course.is_published.is_(True))
    return query.offset(skip).limit(limit).all()


def get_course(db: Session, course_id: UUID) -> models.Course | None:
    return db.query(models.Course).filter(
        models.Course.id == course_id, models.Course.deleted_at.is_(None)
    ).first()


def create_course(db: Session, course_data: dict) -> models.Course:
    course = models.Course(**course_data)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course_id: UUID, course_data: dict) -> models.Course | None:
    course = get_course(db, course_id)
    if not course:
        return None
    for key, value in course_data.items():
        setattr(course, key, value)
    course.updated_at = _utcnow()
    db.commit()
    db.refresh(course)
    return course


def archive_course(db: Session, course_id: UUID) -> bool:
    course = get_course(db, course_id)
    if not course:
        return False
    course.deleted_at = _utcnow()
    db.commit()
    return True


def list_lessons(db: Session, course_id: UUID, *, published_only: bool = False) -> list[models.Lesson]:
    query = db.query(models.Lesson).options(selectinload(models.Lesson.resources)).filter(
        models.Lesson.course_id == course_id,
        models.Lesson.deleted_at.is_(None),
    )
    if published_only:
        query = query.filter(models.Lesson.is_published.is_(True))
    return query.order_by(models.Lesson.order_index).all()


def get_lesson(db: Session, lesson_id: UUID) -> models.Lesson | None:
    return db.query(models.Lesson).filter(
        models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)
    ).first()


def create_lesson(db: Session, course_id: UUID, lesson_data: dict) -> models.Lesson:
    lesson = models.Lesson(course_id=course_id, **lesson_data)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def update_lesson(db: Session, lesson_id: UUID, lesson_data: dict) -> models.Lesson | None:
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        return None
    for key, value in lesson_data.items():
        setattr(lesson, key, value)
    lesson.updated_at = _utcnow()
    db.commit()
    db.refresh(lesson)
    return lesson


def archive_lesson(db: Session, lesson_id: UUID) -> bool:
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        return False
    lesson.deleted_at = _utcnow()
    db.commit()
    return True


def list_enrollments(
    db: Session,
    *,
    persona_id: UUID | None = None,
    course_id: UUID | None = None,
) -> list[models.Enrollment]:
    query = db.query(models.Enrollment).options(
        joinedload(models.Enrollment.course), joinedload(models.Enrollment.persona)
    ).filter(models.Enrollment.deleted_at.is_(None))
    if persona_id:
        query = query.filter(models.Enrollment.persona_id == persona_id)
    if course_id:
        query = query.filter(models.Enrollment.course_id == course_id)
    return query.order_by(models.Enrollment.created_at.desc()).all()


def get_enrollment(db: Session, enrollment_id: UUID) -> models.Enrollment | None:
    return db.query(models.Enrollment).filter(
        models.Enrollment.id == enrollment_id,
        models.Enrollment.deleted_at.is_(None),
    ).first()


def create_enrollment(db: Session, payload: schemas.EnrollmentCreate) -> models.Enrollment:
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.persona_id == payload.persona_id,
        models.Enrollment.course_id == payload.course_id,
    ).first()
    if existing and existing.deleted_at is None:
        raise ValueError("La persona ya está inscrita en este curso")
    if existing:
        existing.deleted_at = None
        existing.status = "active"
        enrollment = existing
    else:
        enrollment = models.Enrollment(
            persona_id=payload.persona_id,
            course_id=payload.course_id,
        )
        db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def list_assessments(db: Session, course_id: UUID) -> list[models.Assessment]:
    return db.query(models.Assessment).filter(
        models.Assessment.course_id == course_id,
        models.Assessment.deleted_at.is_(None),
    ).all()


def get_assessment(db: Session, assessment_id: UUID) -> models.Assessment | None:
    return db.query(models.Assessment).options(
        selectinload(models.Assessment.questions).selectinload(models.AssessmentQuestion.options)
    ).filter(
        models.Assessment.id == assessment_id,
        models.Assessment.deleted_at.is_(None),
    ).first()


def get_lesson_progress(
    db: Session, persona_id: UUID, lesson_id: UUID
) -> models.LessonProgress | None:
    return db.query(models.LessonProgress).filter(
        models.LessonProgress.persona_id == persona_id,
        models.LessonProgress.lesson_id == lesson_id,
    ).first()


def list_certificates(db: Session, persona_id: UUID) -> list[models.Certificate]:
    return db.query(models.Certificate).join(models.Enrollment).filter(
        models.Enrollment.persona_id == persona_id,
        models.Enrollment.deleted_at.is_(None),
    ).all()


def get_certificate_by_code(db: Session, code: str) -> models.Certificate | None:
    return db.query(models.Certificate).filter(
        models.Certificate.certificate_code == code
    ).first()


def list_forum_threads(db: Session) -> list[models.ForumThread]:
    return db.query(models.ForumThread).order_by(models.ForumThread.created_at.desc()).all()

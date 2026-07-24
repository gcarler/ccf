"""Canonical data access for Academy UUID resources.

.. note::
    This CRUD module is **OBSOLETE** and will be removed in a future release.
    The API layer (``backend/api/academy.py``) inlines all queries directly.
    No new code should import from this module. Existing callers should migrate
    to using the API layer's inline queries or the ``schemas/academy.py`` models.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, or_
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
    include_global: bool = False,
) -> list[models.Course]:
    """H-05 (cierre 2026-07-24): ``include_global`` ahora es opt-in (default
    ``False``) para alinear el CRUD con la decisión A-03 (scope admin estricto:
    no incluir ``Course.sede_id IS NULL`` a menos que el caller lo pida
    explicit). El catálogo público del API (_course_scope) sigue
    pidiéndolo con ``include_global=True``; los callers CRUD que querían
    mezclar globales ahora deben hacerlo visible con el flag.
    """
    query = db.query(models.Course).options(
        selectinload(models.Course.lessons),
        selectinload(models.Course.prerequisites),
    ).filter(models.Course.deleted_at.is_(None))
    if sede_id:
        if include_global:
            query = query.filter(
                or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None))
            )
        else:
            # H-05: scope estricto por defecto — sin cursos globales.
            query = query.filter(models.Course.sede_id == sede_id)
    if modality:
        query = query.filter(models.Course.modality == modality)
    if published_only:
        query = query.filter(models.Course.is_published.is_(True))
    return query.offset(skip).limit(limit).all()


def get_course(
    db: Session,
    course_id: UUID,
    *,
    sede_id: UUID | None = None,
) -> models.Course | None:
    """A-06 hardening: ``sede_id`` opcional aplica defense-in-depth Axioma 3.

    Si ``sede_id`` se pasa y el row pertenece a otra sede (distinta del NULL
    global), el getter retorna ``None`` en vez de exponer el row. Los callers
    no-API (workers, seeds) que no pasen ``sede_id`` conservan el comportamiento
    previo (sin filtro) — el flag es opt-in para preservar compatibilidad con
    los tests legacy del módulo CRUD.
    """
    query = db.query(models.Course).filter(
        models.Course.id == course_id, models.Course.deleted_at.is_(None)
    )
    if sede_id is not None:
        query = query.filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None))
        )
    return query.first()


def create_course(db: Session, course_data: dict) -> models.Course:
    course = models.Course(**course_data)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(
    db: Session,
    course_id: UUID,
    course_data: dict,
    *,
    sede_id: UUID | None = None,
) -> models.Course | None:
    # A-07: el pasaje de ``sede_id`` acota el getter a rows visibles — el
    # contraste de sede vive en ``get_course``.
    course = get_course(db, course_id, sede_id=sede_id)
    if not course:
        return None
    for key, value in course_data.items():
        setattr(course, key, value)
    course.updated_at = _utcnow()
    db.commit()
    db.refresh(course)
    return course


def archive_course(
    db: Session,
    course_id: UUID,
    *,
    sede_id: UUID | None = None,
) -> bool:
    course = get_course(db, course_id, sede_id=sede_id)
    if not course:
        return False
    course.deleted_at = _utcnow()
    db.commit()
    return True


def list_lessons(
    db: Session,
    course_id: UUID,
    *,
    published_only: bool = False,
    sede_id: UUID | None = None,
) -> list[models.Lesson]:
    # H-04: si ``sede_id`` se pasa, el course_id debe pertenecer a la sede del
    # actor (o ser global) — sino retorna [].
    if sede_id is not None and not get_course(db, course_id, sede_id=sede_id):
        return []
    query = db.query(models.Lesson).options(selectinload(models.Lesson.resources)).filter(
        models.Lesson.course_id == course_id,
        models.Lesson.deleted_at.is_(None),
    )
    if published_only:
        query = query.filter(models.Lesson.is_published.is_(True))
    return query.order_by(models.Lesson.order_index).all()


def get_lesson(
    db: Session,
    lesson_id: UUID,
    *,
    sede_id: UUID | None = None,
) -> models.Lesson | None:
    query = db.query(models.Lesson).filter(
        models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)
    )
    if sede_id is not None:
        # A-06: join con Course para aplicar scope de sede.
        query = query.join(models.Course).filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)),
            models.Course.deleted_at.is_(None),
        )
    return query.first()


def create_lesson(db: Session, course_id: UUID, lesson_data: dict) -> models.Lesson:
    lesson = models.Lesson(course_id=course_id, **lesson_data)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def update_lesson(
    db: Session,
    lesson_id: UUID,
    lesson_data: dict,
    *,
    sede_id: UUID | None = None,
) -> models.Lesson | None:
    lesson = get_lesson(db, lesson_id, sede_id=sede_id)
    if not lesson:
        return None
    for key, value in lesson_data.items():
        setattr(lesson, key, value)
    lesson.updated_at = _utcnow()
    db.commit()
    db.refresh(lesson)
    return lesson


def archive_lesson(
    db: Session,
    lesson_id: UUID,
    *,
    sede_id: UUID | None = None,
) -> bool:
    lesson = get_lesson(db, lesson_id, sede_id=sede_id)
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
    sede_id: UUID | None = None,
) -> list[models.Enrollment]:
    query = db.query(models.Enrollment).options(
        joinedload(models.Enrollment.course), joinedload(models.Enrollment.persona)
    ).filter(models.Enrollment.deleted_at.is_(None))
    if persona_id:
        query = query.filter(models.Enrollment.persona_id == persona_id)
    if course_id:
        query = query.filter(models.Enrollment.course_id == course_id)
    if sede_id is not None:
        # H-04: filtra por sede del Course del enrollment.
        query = query.join(models.Course).filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None))
        )
    return query.order_by(models.Enrollment.created_at.desc()).all()


def get_enrollment(
    db: Session,
    enrollment_id: UUID,
    *,
    sede_id: UUID | None = None,
) -> models.Enrollment | None:
    query = db.query(models.Enrollment).filter(
        models.Enrollment.id == enrollment_id,
        models.Enrollment.deleted_at.is_(None),
    )
    if sede_id is not None:
        query = query.join(models.Course).filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)),
            models.Course.deleted_at.is_(None),
        )
    return query.first()


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


def get_assessment(
    db: Session,
    assessment_id: UUID,
    *,
    sede_id: UUID | None = None,
) -> models.Assessment | None:
    query = db.query(models.Assessment).options(
        selectinload(models.Assessment.questions).selectinload(models.AssessmentQuestion.options)
    ).filter(
        models.Assessment.id == assessment_id,
        models.Assessment.deleted_at.is_(None),
    )
    if sede_id is not None:
        # A-06: Assessment carece de sede_id propia; el scope proviene del Course
        # al que está asociado.
        query = query.join(models.Course).filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)),
            models.Course.deleted_at.is_(None),
        )
    return query.first()


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


def list_forum_threads(
    db: Session,
    *,
    sede_id: UUID | None = None,
) -> list[models.ForumThread]:
    query = db.query(models.ForumThread)
    if sede_id is not None:
        # M-07: filtra hilos globales (course_id IS NULL) o de Course no
        # archivado de la sede del actor.
        query = query.outerjoin(
            models.Course,
            and_(
                models.ForumThread.course_id == models.Course.id,
                models.Course.deleted_at.is_(None),
                or_(
                    models.Course.sede_id == sede_id,
                    models.Course.sede_id.is_(None),
                ),
            ),
        ).filter(
            or_(
                models.ForumThread.course_id.is_(None),
                models.Course.id.is_not(None),
            )
        )
    return query.order_by(models.ForumThread.created_at.desc()).all()

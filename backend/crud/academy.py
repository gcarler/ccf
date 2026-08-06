"""Canonical data access for Academy UUID resources.

.. note::

    I-01 (cierre 2026-07-24): este CRUD **no** es OBSOLETE. La auditoría
    forense de Academy (`erroresacademia.md` I-01) originalmente marcaba el
    módulo como removible porque la API layer (``backend/api/academy.py``)
    inlinea queries directamente. Sin embargo, los hallazgos A-06, A-07 y
    H-04 endurecieron este módulo con kwargs opt-in ``sede_id`` para
    defense-in-depth (defense-in-depth: la capa CRUD re-valida sede aunque
    la API ya lo haga, protegiendo callers no-API como workers, seeds y
    scripts de migración). La decisión arquitectural final es:
    **mantener ``crud/academy.py`` como capa viva endurecida** — no eliminarla,
    no declararla removible, y todos los getters/mutadores ``get_*``/
    ``list_*``/``update_*``/``create_*`` deben exponer el kwarg ``sede_id=None``
    opt-in. Tests que lo importan (``test_crud_all_modules``,
    ``test_academy_domain``) son válidos y parte del contrato.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from backend import models
from backend.models_shared import _utcnow
from backend.schemas import academy as schemas

logger = logging.getLogger(__name__)


def _commit_or_raise_conflict(db: Session, detail: str = "resource already exists") -> None:
    """H-08 (cierre 2026-07-24): commit helper que distingue 409 de 500.

    Convierte violaciones de unique-key concurrentes en ``409 Conflict`` en
    vez de propagarse como ``500 Internal Server Error``. Sólo traga
    ``IntegrityError`` cuyo ``pgcode == '23505'`` (Postgres) o cuyo mensaje
    SQLite contiene ``"UNIQUE constraint failed"``. Toda otra
    ``IntegrityError`` (NOT NULL, FK, check) es un bug genuino y se
    re-raise post-rollback para que salga como 500 (no como falso 409).

    Patrón alineado con ``backend/api/cms_v2.py::_commit_or_raise_conflict``
    (M-12 defensivo) — reusar para cualquier mutador Academy que pueda
    chocar contra una constraint UNIQUE (course.code, enrollment por
    (persona_id, course_id), etc.).

    Unique-violation detection y contrato 409 delegados a
    ``backend.crud._utils._commit_or_raise_409`` — single source of truth
    compartido con ``crud/cms.py`` y ``api/cms_v2/_shared.py`` (consolidación
    de las 3 copias, 2026-08-05).
    """
    from backend.crud._utils import _commit_or_raise_409

    _commit_or_raise_409(db, detail=detail)


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
    query = (
        db.query(models.Course)
        .options(
            selectinload(models.Course.lessons),
            selectinload(models.Course.prerequisites),
        )
        .filter(models.Course.deleted_at.is_(None))
    )
    if sede_id:
        if include_global:
            query = query.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
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
    los tests del módulo CRUD.
    """
    query = db.query(models.Course).filter(models.Course.id == course_id, models.Course.deleted_at.is_(None))
    if sede_id is not None:
        query = query.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
    return query.first()


def create_course(
    db: Session,
    course_data: dict,
    *,
    sede_id: UUID | None = None,
    actor_persona_id: UUID | None = None,
) -> models.Course:
    """H-07 (cierre 2026-07-24): defense-in-depth sobre ownership del actor.

    ``sede_id`` opt-in: si se pasa, se valida que el ``Course.sede_id`` que
    dicta ``course_data`` sea la misma (o ``None`` para curso global
    legítimo). Si el caller intenta crear un curso atribuyéndolo a otra
    sede, se rechaza con ``ValueError`` (que el handler API convierte a
    400/403). Sin ``sede_id`` se preserva el comportamiento previo (sin
    defense-in-depth — compatibility con callers no-API).

    ``actor_persona_id`` opt-in: meramente lo asigna a ``created_by`` si la
    columna existe en el payload/ORM (Academy Activity es trazada en la API
    vía ``AcademyActivityLog``; aquí no forzamos la columna si no está,
    porque ``Course`` no tiene FK ``created_by`` — el contrato lo respalda
    en el handler API).

    H-08: el commit se hace vía ``_commit_or_raise_conflict`` para distinguir
    ``409 Conflict`` (e.g. ``course.code`` UNIQUE duplicado) de ``500``.
    """
    if sede_id is not None:
        target = course_data.get("sede_id")
        # Curso global (sede_id None) es legítimo; cualquier sede específica
        # distinta de la del actor es cross-tenant y se bloquea.
        if target is not None and target != sede_id:
            raise ValueError("El actor no puede crear un curso atribuido a otra sede")
    course = models.Course(**course_data)
    db.add(course)
    _commit_or_raise_conflict(db, detail="course code already exists")
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
    _commit_or_raise_conflict(db, detail="course conflict")
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
    _commit_or_raise_conflict(db, detail="course conflict")
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
    query = (
        db.query(models.Lesson)
        .options(selectinload(models.Lesson.resources))
        .filter(
            models.Lesson.course_id == course_id,
            models.Lesson.deleted_at.is_(None),
        )
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
    query = db.query(models.Lesson).filter(models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None))
    if sede_id is not None:
        # A-06: join con Course para aplicar scope de sede.
        query = query.join(models.Course).filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)),
            models.Course.deleted_at.is_(None),
        )
    return query.first()


def create_lesson(
    db: Session,
    course_id: UUID,
    lesson_data: dict,
    *,
    sede_id: UUID | None = None,
    actor_persona_id: UUID | None = None,
) -> models.Lesson:
    """H-07 (cierre 2026-07-24): defense-in-depth sobre ownership del actor.

    ``sede_id`` opt-in: si se pasa, ``course_id`` debe pertenecer a la sede
    del actor (o ser curso global) para poder añadir una lección. Un caller
    no-API intentando crear una lección en un curso de otra sede recibe
    ``None``-style rejection — aquí delegamos a ``get_course`` y, si no es
    visible, lanzamos ``ValueError`` (handler convierte a 404/403). Sin
    ``sede_id`` se preserva comportamiento previo.

    H-08: commit vía ``_commit_or_raise_conflict`` (aunque ``Lesson`` hoy no
    tiene UNIQUE constraint visible, el patrón defensivo cubre futuras
    constraints — e.g. ``(course_id, order_index)``).
    """
    if sede_id is not None and not get_course(db, course_id, sede_id=sede_id):
        raise ValueError("El curso no es visible para el actor — no se crea la lección")
    lesson = models.Lesson(course_id=course_id, **lesson_data)
    db.add(lesson)
    _commit_or_raise_conflict(db, detail="lesson conflict")
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
    _commit_or_raise_conflict(db, detail="lesson conflict")
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
    _commit_or_raise_conflict(db, detail="lesson conflict")
    return True


def list_enrollments(
    db: Session,
    *,
    persona_id: UUID | None = None,
    course_id: UUID | None = None,
    sede_id: UUID | None = None,
) -> list[models.Enrollment]:
    query = (
        db.query(models.Enrollment)
        .options(joinedload(models.Enrollment.course), joinedload(models.Enrollment.persona))
        .filter(models.Enrollment.deleted_at.is_(None))
    )
    if persona_id:
        query = query.filter(models.Enrollment.persona_id == persona_id)
    if course_id:
        query = query.filter(models.Enrollment.course_id == course_id)
    if sede_id is not None:
        # H-04: filtra por sede del Course del enrollment.
        query = query.join(models.Course).filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
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


def create_enrollment(
    db: Session,
    payload: schemas.EnrollmentCreate,
    *,
    sede_id: UUID | None = None,
) -> models.Enrollment:
    """H-06 (cierre 2026-07-24): reactiva cross-tenant bloqueado.

    Antes, la búsqueda de duplicado por ``(persona_id, course_id)`` no
    validaba ``Course.sede_id``: un actor de sede B podía reactivar un
    enrollment archivado de un curso de sede A. Ahora, si ``sede_id`` se
    pasa y el ``existing`` enrollment pertenece a un curso de otra sede
    específica (no global), NO se reactiva — se inserta un enrollment
    nuevo visible al actor (el course_id pasó la validación de scope en
    el handler API vía ``_get_scoped_course``). Los cursos globales
    (``Course.sede_id IS NULL``) siguen siendo legítimos cross-tenant
    (decisión A-03 lectura/captación) y se reactivan normalmente.

    H-08: commit vía ``_commit_or_raise_conflict`` para distinguir 409
    (enrollment único duplicado concurrente) de 500.
    """
    existing = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.persona_id == payload.persona_id,
            models.Enrollment.course_id == payload.course_id,
        )
        .first()
    )
    if existing and existing.deleted_at is None:
        raise ValueError("La persona ya está inscrita en este curso")
    if existing:
        # H-06: sólo reactivamos si el course es visible al actor (misma
        # sede o global). Un enrollment archivado en un curso de otra sede
        # NO se reactiva — se interpreta como nuevo enrollment legítimo.
        can_reactivate = True
        if sede_id is not None:
            course = db.query(models.Course.sede_id).filter(models.Course.id == existing.course_id).first()
            course_sede = course[0] if course else None
            if course_sede is not None and course_sede != sede_id:
                can_reactivate = False
        if can_reactivate:
            existing.deleted_at = None
            existing.status = "active"
            enrollment = existing
        else:
            # El course_id del existing es de otra sede; el handler ya
            # validó que payload.course_id es visible al actor (debería
            # coincidir con existing.course_id o se rechazaría upstream).
            # Caso teórico: si llegamos aquí, treatamos como conflicto.
            raise ValueError("Enrollment existente pertenece a un curso de otra sede")
    else:
        enrollment = models.Enrollment(
            persona_id=payload.persona_id,
            course_id=payload.course_id,
        )
        db.add(enrollment)
    _commit_or_raise_conflict(db, detail="enrollment already exists")
    db.refresh(enrollment)
    return enrollment


def list_assessments(db: Session, course_id: UUID) -> list[models.Assessment]:
    return (
        db.query(models.Assessment)
        .filter(
            models.Assessment.course_id == course_id,
            models.Assessment.deleted_at.is_(None),
        )
        .all()
    )


def get_assessment(
    db: Session,
    assessment_id: UUID,
    *,
    sede_id: UUID | None = None,
) -> models.Assessment | None:
    query = (
        db.query(models.Assessment)
        .options(selectinload(models.Assessment.questions).selectinload(models.AssessmentQuestion.options))
        .filter(
            models.Assessment.id == assessment_id,
            models.Assessment.deleted_at.is_(None),
        )
    )
    if sede_id is not None:
        # A-06: Assessment carece de sede_id propia; el scope proviene del Course
        # al que está asociado.
        query = query.join(models.Course).filter(
            or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)),
            models.Course.deleted_at.is_(None),
        )
    return query.first()


def get_lesson_progress(db: Session, persona_id: UUID, lesson_id: UUID) -> models.LessonProgress | None:
    return (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.persona_id == persona_id,
            models.LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )


def list_certificates(db: Session, persona_id: UUID) -> list[models.Certificate]:
    return (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(
            models.Enrollment.persona_id == persona_id,
            models.Enrollment.deleted_at.is_(None),
        )
        .all()
    )


def get_certificate_by_code(db: Session, code: str) -> models.Certificate | None:
    return db.query(models.Certificate).filter(models.Certificate.certificate_code == code).first()


def list_forum_threads(
    db: Session,
    *,
    sede_id: UUID | None = None,
    skip: int = 0,
    limit: int | None = 100,
) -> list[models.ForumThread]:
    """M-07 (cierre 2026-07-24): añadidos ``skip``/``limit`` opt-in (limit
    None = sin tope, para callers internos que quieren todo — raro). El
    filtro sede (A-02) ya estaba aplicado vía ``outerjoin`` + filter.

    Nota M-07: ``ForumThread`` NO tiene ``deleted_at`` en el modelo (ver
    ``models_academy_core.py:317``) — el soft-delete de hilos queda como
    debt pendiente (requiere migración DDL añadiendo la columna). Mientras
    tanto no hay rows para filtrar por ``deleted_at``. El endpoint API
    ``forum_threads`` ya tiene paginación (``skip``/``limit`` Query), por
    lo que la paginación real sucede allí; el CRUD expone el kwarg para
    callers directos (tests/seeds) que quieran acotar.
    """
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
    query = query.order_by(models.ForumThread.created_at.desc())
    if skip:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()

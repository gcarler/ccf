"""MCP privado para la operación académica de CCF.

Esta superficie reutiliza los modelos y reglas de scope de la API canónica de
Academia. Los cursos globales pueden leerse para captación, pero las mutaciones
y los datos de estudiantes son estrictamente de la sede del usuario.
"""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from backend import models, schemas
from backend.api.academy import _get_scoped_course, _invalidate_dashboard_for, _serialize_course
from backend.core.cache_v2 import _to_jsonable
from backend.core.database import SessionLocal
from backend.core.tenant import require_user_sede_id
from backend.crud.crm import get_user_sede_id
from backend.mcp_auth import authenticated_mcp_app, get_mcp_current_user, require_mcp_permission
from backend.models_shared import _utcnow

academy_mcp = FastMCP(
    name="CCF Academia",
    instructions=(
        "Opera la Academia de CCF. Respeta el JWT, los permisos academy y la "
        "sede del usuario. Los cursos globales son legibles, pero nunca mutables "
        "desde una sede. No expongas notas pastorales ni datos médicos."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


def _safe_course(row: models.Course) -> dict[str, Any]:
    return _to_jsonable(_serialize_course(row))


def _safe_enrollment(row: models.Enrollment) -> dict[str, Any]:
    return {
        "enrollment_id": str(row.id),
        "persona_id": str(row.persona_id),
        "course_id": str(row.course_id),
        "status": row.status,
        "progress_percent": row.progress_percent,
        "final_grade": row.final_grade,
        "attendance_percent": row.attendance_percent,
        "approved": row.approved,
        "certificate_issued": row.certificate_issued,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _safe_lesson(row: models.Lesson) -> dict[str, Any]:
    return {
        "lesson_id": str(row.id),
        "course_id": str(row.course_id),
        "title": row.title,
        "content": row.content,
        "content_type": row.content_type,
        "media_url": row.media_url,
        "order_index": row.order_index,
        "duration_minutes": row.duration_minutes,
        "is_published": row.is_published,
    }


def _parse_datetime(value: str | None) -> datetime.datetime | None:
    if value is None or not str(value).strip():
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Fecha inválida; use ISO-8601") from exc


@academy_mcp.tool()
def list_academy_courses(
    limit: int = 100,
    offset: int = 0,
    modality: str | None = None,
    published_only: bool = True,
) -> dict[str, Any]:
    """Lista cursos visibles para la sede del usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:read")
        query = db.query(models.Course).filter(models.Course.deleted_at.is_(None))
        sede_id = get_user_sede_id(db, user.id)
        if sede_id:
            query = query.filter((models.Course.sede_id == sede_id) | models.Course.sede_id.is_(None))
        if modality:
            query = query.filter(models.Course.modality == modality)
        if published_only:
            query = query.filter(models.Course.is_published.is_(True))
        rows = query.order_by(models.Course.created_at.desc()).offset(max(0, int(offset))).limit(max(1, min(int(limit), 500))).all()
        return {"items": [_safe_course(row) for row in rows], "count": len(rows)}
    finally:
        db.close()


@academy_mcp.tool()
def get_academy_course(course_id: UUID) -> dict[str, Any]:
    """Obtiene un curso dentro del scope de Academia del usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:read")
        course = _get_scoped_course(db, user, course_id)
        if not course.is_published:
            require_mcp_permission(db, user, "academy:edit")
        return _safe_course(course)
    finally:
        db.close()


@academy_mcp.tool()
def list_academy_lessons(course_id: UUID, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """Lista lecciones de un curso visible para el usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:read")
        course = _get_scoped_course(db, user, course_id)
        query = db.query(models.Lesson).filter(
            models.Lesson.course_id == course.id,
            models.Lesson.deleted_at.is_(None),
        )
        if not course.is_published:
            require_mcp_permission(db, user, "academy:edit")
        else:
            query = query.filter(models.Lesson.is_published.is_(True))
        rows = query.order_by(models.Lesson.order_index).offset(max(0, int(offset))).limit(max(1, min(int(limit), 500))).all()
        return {"items": [_safe_lesson(row) for row in rows], "count": len(rows)}
    finally:
        db.close()


@academy_mcp.tool()
def create_academy_course(
    code: str,
    title: str,
    modality: str = "online",
    description: str | None = None,
    slug: str | None = None,
    is_published: bool = False,
    duration_hours: int = 0,
    access_level: str = "persona",
) -> dict[str, Any]:
    """Crea un curso atribuido automáticamente a la sede del usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:edit")
        sede_id = UUID(str(require_user_sede_id(db, user)))
        payload = schemas.CoursePayload(
            code=code,
            title=title,
            modality=modality,
            description=description,
            slug=slug,
            is_published=is_published,
            duration_hours=max(0, int(duration_hours)),
            access_level=access_level,
        )
        course = models.Course(**payload.model_dump(), sede_id=sede_id)
        db.add(course)
        db.commit()
        db.refresh(course)
        _invalidate_dashboard_for(db, user)
        return _safe_course(course)
    finally:
        db.close()


@academy_mcp.tool()
def update_academy_course(course_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza campos permitidos de un curso de la sede."""
    allowed = {
        "code", "slug", "title", "description", "excerpt", "tag", "cta_text", "syllabus",
        "modality", "is_published", "is_self_paced", "duration_hours", "cohort_name",
        "certificate_type", "instructor_name", "image_url", "access_level",
    }
    clean = {key: value for key, value in changes.items() if key in allowed}
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:edit")
        course = _get_scoped_course(db, user, course_id)
        if course.sede_id is None:
            raise ValueError("Los cursos globales no pueden mutarse desde MCP")
        payload = schemas.CourseUpdate(**clean)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(course, key, value)
        course.updated_at = _utcnow()
        db.commit()
        db.refresh(course)
        _invalidate_dashboard_for(db, user)
        return _safe_course(course)
    finally:
        db.close()


@academy_mcp.tool()
def archive_academy_course(course_id: UUID) -> dict[str, Any]:
    """Archiva un curso de la sede sin borrarlo físicamente."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:manage")
        course = _get_scoped_course(db, user, course_id)
        if course.sede_id is None:
            raise ValueError("Los cursos globales no pueden mutarse desde MCP")
        course.deleted_at = _utcnow()
        db.commit()
        _invalidate_dashboard_for(db, user)
        return {"status": "archived", "course_id": str(course.id)}
    finally:
        db.close()


@academy_mcp.tool()
def create_academy_lesson(
    course_id: UUID,
    title: str,
    content: str = "",
    content_type: str = "video",
    media_url: str | None = None,
    order_index: int = 0,
    duration_minutes: int = 0,
    is_published: bool = False,
) -> dict[str, Any]:
    """Crea una lección dentro de un curso de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:edit")
        course = _get_scoped_course(db, user, course_id)
        if course.sede_id is None:
            raise ValueError("Los cursos globales no pueden mutarse desde MCP")
        payload = schemas.LessonPayload(
            title=title,
            content=content,
            content_type=content_type,
            media_url=media_url,
            order_index=max(0, int(order_index)),
            duration_minutes=max(0, int(duration_minutes)),
            is_published=is_published,
        )
        row = models.Lesson(course_id=course.id, **payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return _safe_lesson(row)
    finally:
        db.close()


@academy_mcp.tool()
def update_academy_lesson(lesson_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza una lección cuyo curso pertenece a la sede."""
    allowed = {"title", "content", "content_type", "media_url", "order_index", "duration_minutes", "is_published"}
    clean = {key: value for key, value in changes.items() if key in allowed}
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:edit")
        row = db.query(models.Lesson).filter(models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)).first()
        if not row:
            raise ValueError("Lección no encontrada")
        course = _get_scoped_course(db, user, row.course_id)
        if course.sede_id is None:
            raise ValueError("Los cursos globales no pueden mutarse desde MCP")
        payload = schemas.LessonUpdate(**clean)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        row.updated_at = _utcnow()
        db.commit()
        db.refresh(row)
        return _safe_lesson(row)
    finally:
        db.close()


@academy_mcp.tool()
def archive_academy_lesson(lesson_id: UUID) -> dict[str, Any]:
    """Archiva una lección sin eliminarla físicamente."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:edit")
        row = db.query(models.Lesson).filter(models.Lesson.id == lesson_id, models.Lesson.deleted_at.is_(None)).first()
        if not row:
            raise ValueError("Lección no encontrada")
        course = _get_scoped_course(db, user, row.course_id)
        if course.sede_id is None:
            raise ValueError("Los cursos globales no pueden mutarse desde MCP")
        row.deleted_at = _utcnow()
        db.commit()
        return {"status": "archived", "lesson_id": str(row.id)}
    finally:
        db.close()


@academy_mcp.tool()
def enroll_current_user(course_id: UUID) -> dict[str, Any]:
    """Inscribe al usuario autenticado en un curso publicado de su scope."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:study")
        course = _get_scoped_course(db, user, course_id)
        if not course.is_published:
            raise ValueError("El curso no está publicado")
        existing = db.query(models.Enrollment).filter(
            models.Enrollment.persona_id == user.id,
            models.Enrollment.course_id == course.id,
        ).first()
        if existing and existing.deleted_at is None:
            return _safe_enrollment(existing)
        if existing:
            existing.deleted_at = None
            existing.status = "active"
            row = existing
        else:
            row = models.Enrollment(persona_id=user.id, course_id=course.id)
            db.add(row)
        db.add(models.AcademyActivityLog(
            event_type="enrollment",
            course_id=course.id,
            persona_id=user.id,
            modality=course.modality,
        ))
        db.commit()
        db.refresh(row)
        _invalidate_dashboard_for(db, user)
        return _safe_enrollment(row)
    finally:
        db.close()


@academy_mcp.tool()
def list_my_academy_enrollments(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """Lista las inscripciones del usuario autenticado."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:study")
        rows = db.query(models.Enrollment).filter(
            models.Enrollment.persona_id == user.id,
            models.Enrollment.deleted_at.is_(None),
        ).order_by(models.Enrollment.created_at.desc()).offset(max(0, int(offset))).limit(max(1, min(int(limit), 500))).all()
        return {"items": [_safe_enrollment(row) for row in rows], "count": len(rows)}
    finally:
        db.close()


@academy_mcp.tool()
def register_academy_attendance(
    enrollment_id: UUID,
    session_date: str,
    status: str = "present",
) -> dict[str, Any]:
    """Registra de forma idempotente la asistencia de una inscripción."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:edit")
        enrollment = db.query(models.Enrollment).filter(
            models.Enrollment.id == enrollment_id,
            models.Enrollment.deleted_at.is_(None),
        ).first()
        if not enrollment:
            raise ValueError("Inscripción no encontrada")
        course = _get_scoped_course(db, user, enrollment.course_id)
        if course.sede_id is None:
            raise ValueError("La asistencia académica requiere un curso de la sede")
        parsed = _parse_datetime(session_date)
        if parsed is None:
            raise ValueError("session_date es obligatorio")
        row = db.query(models.CourseAttendance).filter(
            models.CourseAttendance.enrollment_id == enrollment.id,
            models.CourseAttendance.session_date == parsed,
        ).first()
        if row is None:
            row = models.CourseAttendance(
                enrollment_id=enrollment.id,
                session_date=parsed,
                status=status,
                recorded_by_persona_id=user.id,
            )
            db.add(row)
        else:
            row.status = status
            row.recorded_by_persona_id = user.id
        db.commit()
        db.refresh(row)
        return {
            "attendance_id": str(row.id),
            "enrollment_id": str(row.enrollment_id),
            "session_date": row.session_date.isoformat(),
            "status": row.status,
        }
    finally:
        db.close()


@academy_mcp.tool()
def list_academy_course_students(course_id: UUID, limit: int = 200, offset: int = 0) -> dict[str, Any]:
    """Lista estudiantes de un curso de la sede sin datos pastorales sensibles."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "academy:edit")
        course = _get_scoped_course(db, user, course_id)
        if course.sede_id is None:
            raise ValueError("Los cursos globales no tienen operación administrativa por sede")
        rows = db.query(models.Enrollment).filter(
            models.Enrollment.course_id == course.id,
            models.Enrollment.deleted_at.is_(None),
        ).order_by(models.Enrollment.created_at).offset(max(0, int(offset))).limit(max(1, min(int(limit), 500))).all()
        return {
            "items": [_safe_enrollment(row) for row in rows],
            "count": len(rows),
            "course_id": str(course.id),
        }
    finally:
        db.close()


academy_mcp_app = authenticated_mcp_app(academy_mcp)

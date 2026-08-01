"""Cross-cutting comment endpoints: attachments and personal comment center."""

from __future__ import annotations

import os
import uuid as _uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import String, cast, literal, not_, or_, select
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.database import get_db
from backend.core.permissions import get_current_active_user
from backend.crud.crm import get_user_sede_id
from backend.schemas.projects import CommentAttachment

router = APIRouter()


ALLOWED_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/svg+xml": "image",
    "application/pdf": "pdf",
    "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.ms-excel": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
    "text/plain": "document",
    "text/csv": "document",
    "video/mp4": "video",
    "video/webm": "video",
    "audio/mpeg": "audio",
    "audio/ogg": "audio",
    "audio/wav": "audio",
}


@router.post("/attachments/upload", response_model=CommentAttachment)
async def upload_comment_attachment(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload a file attachment to be referenced from a comment."""
    content_type = file.content_type or "application/octet-stream"
    att_type = ALLOWED_TYPES.get(content_type)
    if not att_type:
        raise HTTPException(status_code=422, detail=f"Tipo de archivo no permitido: {content_type}")

    MAX_SIZE = 25 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 25 MB")

    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "comment_attachments")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    filename = f"{_uuid.uuid4()}{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    return {
        "url": f"/static/comment_attachments/{filename}",
        "type": att_type,
        "name": file.filename or filename,
        "size": len(contents),
    }


def _persona_id(current_user: models.User, db: Session):
    from backend.crud.projects import get_user_persona_id

    return get_user_persona_id(db, current_user.id) or current_user.id


def _mention_filter(column, persona_id: str, dialect_name: str):
    """Filter a JSON ``mentions`` column for a specific persona id.

    Uses the native ``@>`` contains operator on PostgreSQL and falls back
    to a case-insensitive substring match on SQLite so the test suite keeps
    working.
    """
    if dialect_name == "postgresql":
        return column.contains([str(persona_id)])
    # SQLite / other engines: JSON is stored as text.
    return cast(column, String).ilike(f"%{persona_id}%")


def _not_mention_filter(column, persona_id: str, dialect_name: str):
    """Exclude comments where ``persona_id`` appears in the ``mentions`` column.

    NULL-safe counterpart of :func:`_mention_filter`: rows with no mentions
    must be kept, so the negation is guarded with ``column IS NULL``.
    """
    return or_(column.is_(None), not_(_mention_filter(column, persona_id, dialect_name)))


def _base_columns_project(module_type: str):
    return [
        models.ProjectComment.id.label("id"),
        models.ProjectComment.project_id.label("project_id"),
        models.ProjectComment.task_id.label("task_id"),
        models.ProjectComment.content.label("content"),
        models.ProjectComment.author_id.label("author_id"),
        models.ProjectComment.is_resolved.label("is_resolved"),
        models.ProjectComment.created_at.label("created_at"),
        models.ProjectComment.updated_at.label("updated_at"),
        models.ProjectComment.attachments.label("attachments"),
        models.ProjectComment.mentions.label("mentions"),
        literal(module_type).label("module_type"),
        models.Project.title.label("context_title"),
    ]


def _base_columns_agenda():
    return [
        models.AgendaEventComment.id.label("id"),
        models.AgendaEventComment.event_id.label("project_id"),
        literal(None).label("task_id"),
        models.AgendaEventComment.content.label("content"),
        models.AgendaEventComment.author_id.label("author_id"),
        literal(False).label("is_resolved"),
        models.AgendaEventComment.created_at.label("created_at"),
        models.AgendaEventComment.updated_at.label("updated_at"),
        models.AgendaEventComment.attachments.label("attachments"),
        models.AgendaEventComment.mentions.label("mentions"),
        literal("agenda").label("module_type"),
        models.EventoAgenda.titulo.label("context_title"),
    ]


def _build_comment_rows(db: Session, rows: list) -> List[schemas.ProjectCommentItem]:
    """Convert raw rows into Pydantic items with batched author names."""
    author_ids = {row.author_id for row in rows if row.author_id}
    authors_map: dict = {}
    if author_ids:
        from backend.models import Persona

        authors_map = {
            p.id: (getattr(p, "nombre_completo", None) or getattr(p, "full_name", None) or "Usuario")
            for p in db.query(Persona).filter(Persona.id.in_(author_ids)).all()
        }
    result = []
    for row in rows:
        result.append(
            schemas.ProjectCommentItem(
                id=row.id,
                project_id=str(row.project_id) if row.project_id is not None else None,
                task_id=str(row.task_id) if row.task_id is not None else None,
                content=row.content,
                author_id=str(row.author_id) if row.author_id is not None else None,
                author_name=authors_map.get(row.author_id, "Usuario"),
                is_resolved=row.is_resolved,
                created_at=row.created_at,
                updated_at=row.updated_at,
                attachments=row.attachments or [],
                mentions=[str(m) for m in (row.mentions or [])],
                module_type=row.module_type,
                context_title=row.context_title,
            )
        )
    return result


@router.get("/me/created", response_model=List[schemas.ProjectCommentItem])
def list_my_created_comments(
    type_filter: Optional[str] = Query(None, alias="type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return all comments authored by the current user across projects, tasks and agenda."""
    if type_filter and type_filter not in {"project", "activity", "agenda"}:
        raise HTTPException(status_code=422, detail="type must be project, activity or agenda")

    persona = _persona_id(current_user, db)
    user_sede = get_user_sede_id(db, current_user.id)
    dialect = db.bind.dialect.name if db.bind and db.bind.dialect else "sqlite"
    selects = []

    if type_filter in (None, "project"):
        project_s = (
            select(*_base_columns_project("project"))
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .where(
                models.ProjectComment.author_id == persona,
                models.ProjectComment.deleted_at.is_(None),
                models.Project.deleted_at.is_(None),
                models.ProjectComment.task_id.is_(None),
                _not_mention_filter(models.ProjectComment.mentions, str(persona), dialect),
            )
        )
        if user_sede:
            project_s = project_s.where(models.Project.sede_id == user_sede)
        selects.append(project_s)

    if type_filter in (None, "activity"):
        activity_s = (
            select(*_base_columns_project("activity"))
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .where(
                models.ProjectComment.author_id == persona,
                models.ProjectComment.deleted_at.is_(None),
                models.Project.deleted_at.is_(None),
                models.ProjectComment.task_id.isnot(None),
                _not_mention_filter(models.ProjectComment.mentions, str(persona), dialect),
            )
        )
        if user_sede:
            activity_s = activity_s.where(models.Project.sede_id == user_sede)
        selects.append(activity_s)

    if type_filter in (None, "agenda"):
        agenda_s = (
            select(*_base_columns_agenda())
            .join(models.EventoAgenda, models.EventoAgenda.id == models.AgendaEventComment.event_id)
            .where(
                models.AgendaEventComment.author_id == persona,
                models.AgendaEventComment.deleted_at.is_(None),
                models.EventoAgenda.deleted_at.is_(None),
                _not_mention_filter(models.AgendaEventComment.mentions, str(persona), dialect),
            )
        )
        if user_sede:
            agenda_s = agenda_s.where(models.EventoAgenda.sede_id == user_sede)
        selects.append(agenda_s)

    if not selects:
        return []

    sub = selects[0].union_all(*selects[1:]).subquery()
    rows = db.execute(select(sub).order_by(sub.c.created_at.desc()).offset(offset).limit(limit)).all()
    return _build_comment_rows(db, rows)


@router.get("/me/mentions", response_model=List[schemas.ProjectCommentItem])
def list_my_mentions(
    type_filter: Optional[str] = Query(None, alias="type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return comments where the current user was mentioned."""
    if type_filter and type_filter not in {"project", "activity", "agenda"}:
        raise HTTPException(status_code=422, detail="type must be project, activity or agenda")

    persona = _persona_id(current_user, db)
    user_sede = get_user_sede_id(db, current_user.id)
    dialect = db.bind.dialect.name if db.bind and db.bind.dialect else "sqlite"
    selects = []

    if type_filter in (None, "project"):
        project_s = (
            select(*_base_columns_project("project"))
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .where(
                models.ProjectComment.deleted_at.is_(None),
                models.Project.deleted_at.is_(None),
                models.ProjectComment.task_id.is_(None),
                _mention_filter(models.ProjectComment.mentions, str(persona), dialect),
                models.ProjectComment.author_id != persona,
            )
        )
        if user_sede:
            project_s = project_s.where(models.Project.sede_id == user_sede)
        selects.append(project_s)

    if type_filter in (None, "activity"):
        activity_s = (
            select(*_base_columns_project("activity"))
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .where(
                models.ProjectComment.deleted_at.is_(None),
                models.Project.deleted_at.is_(None),
                models.ProjectComment.task_id.isnot(None),
                _mention_filter(models.ProjectComment.mentions, str(persona), dialect),
                models.ProjectComment.author_id != persona,
            )
        )
        if user_sede:
            activity_s = activity_s.where(models.Project.sede_id == user_sede)
        selects.append(activity_s)

    if type_filter in (None, "agenda"):
        agenda_s = (
            select(*_base_columns_agenda())
            .join(models.EventoAgenda, models.EventoAgenda.id == models.AgendaEventComment.event_id)
            .where(
                models.AgendaEventComment.deleted_at.is_(None),
                models.EventoAgenda.deleted_at.is_(None),
                _mention_filter(models.AgendaEventComment.mentions, str(persona), dialect),
                models.AgendaEventComment.author_id != persona,
            )
        )
        if user_sede:
            agenda_s = agenda_s.where(models.EventoAgenda.sede_id == user_sede)
        selects.append(agenda_s)

    if not selects:
        return []

    sub = selects[0].union_all(*selects[1:]).subquery()
    rows = db.execute(select(sub).order_by(sub.c.created_at.desc()).offset(offset).limit(limit)).all()
    return _build_comment_rows(db, rows)

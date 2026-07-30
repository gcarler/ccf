"""Cross-cutting comment endpoints: attachments and personal comment center."""
from __future__ import annotations

import os
import uuid as _uuid
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.schemas.projects import CommentAttachment
from backend.core.database import get_db
from backend.core.permissions import get_current_active_user
from backend.crud.crm import get_user_sede_id

router = APIRouter()


ALLOWED_TYPES = {
    "image/jpeg": "image", "image/png": "image", "image/gif": "image",
    "image/webp": "image", "image/svg+xml": "image",
    "application/pdf": "pdf",
    "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.ms-excel": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
    "text/plain": "document",
    "text/csv": "document",
    "video/mp4": "video", "video/webm": "video",
    "audio/mpeg": "audio", "audio/ogg": "audio", "audio/wav": "audio",
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


@router.get("/me/created", response_model=List[schemas.ProjectCommentItem])
def list_my_created_comments(
    type_filter: Optional[str] = Query(None, alias="type"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return all comments authored by the current user across projects and agenda."""
    persona = _persona_id(current_user, db)
    user_sede = get_user_sede_id(db, current_user.id)
    results = []

    if not type_filter or type_filter == "project":
        q = (
            db.query(models.ProjectComment, models.Project)
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .filter(
                models.ProjectComment.author_id == persona,
                models.ProjectComment.deleted_at.is_(None),
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede:
            q = q.filter(models.Project.sede_id == user_sede)
        for comment, project in q.order_by(models.ProjectComment.created_at.desc()).limit(limit).all():
            results.append(schemas.ProjectCommentItem(
                id=comment.id,
                project_id=str(comment.project_id),
                task_id=str(comment.task_id) if comment.task_id else None,
                content=comment.content,
                author_id=str(comment.author_id) if comment.author_id else None,
                author_name=current_user.username or "Usuario",
                is_resolved=comment.is_resolved,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                attachments=comment.attachments or [],
                mentions=comment.mentions or [],
                module_type="project",
                context_title=project.title if project else None,
            ))

    if not type_filter or type_filter == "agenda":
        q = (
            db.query(models.AgendaEventComment, models.EventoAgenda)
            .join(models.EventoAgenda, models.EventoAgenda.id == models.AgendaEventComment.event_id)
            .filter(
                models.AgendaEventComment.author_id == persona,
                models.AgendaEventComment.deleted_at.is_(None),
                models.EventoAgenda.deleted_at.is_(None),
            )
        )
        if user_sede:
            q = q.filter(models.EventoAgenda.sede_id == user_sede)
        for comment, event in q.order_by(models.AgendaEventComment.created_at.desc()).limit(limit).all():
            results.append(schemas.ProjectCommentItem(
                id=comment.id,
                project_id=str(event.id),
                task_id=None,
                content=comment.content,
                author_id=str(comment.author_id) if comment.author_id else None,
                author_name=current_user.username or "Usuario",
                is_resolved=False,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                attachments=comment.attachments or [],
                mentions=comment.mentions or [],
                module_type="agenda",
                context_title=event.titulo if event else None,
            ))

    results.sort(key=lambda x: x.created_at, reverse=True)
    return results[:limit]


@router.get("/me/mentions", response_model=List[schemas.ProjectCommentItem])
def list_my_mentions(
    type_filter: Optional[str] = Query(None, alias="type"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return comments where the current user was mentioned."""
    persona = _persona_id(current_user, db)
    user_sede = get_user_sede_id(db, current_user.id)
    results = []

    if not type_filter or type_filter == "project":
        q = (
            db.query(models.ProjectComment, models.Project)
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .filter(
                models.ProjectComment.deleted_at.is_(None),
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede:
            q = q.filter(models.Project.sede_id == user_sede)
        rows = q.all()
        for comment, project in rows:
            if str(persona) in [str(m) for m in (comment.mentions or [])]:
                results.append(schemas.ProjectCommentItem(
                    id=comment.id,
                    project_id=str(comment.project_id),
                    task_id=str(comment.task_id) if comment.task_id else None,
                    content=comment.content,
                    author_id=str(comment.author_id) if comment.author_id else None,
                    author_name="",
                    is_resolved=comment.is_resolved,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                    attachments=comment.attachments or [],
                    mentions=comment.mentions or [],
                    module_type="project",
                    context_title=project.title if project else None,
                ))

    if not type_filter or type_filter == "agenda":
        q = (
            db.query(models.AgendaEventComment, models.EventoAgenda)
            .join(models.EventoAgenda, models.EventoAgenda.id == models.AgendaEventComment.event_id)
            .filter(
                models.AgendaEventComment.deleted_at.is_(None),
                models.EventoAgenda.deleted_at.is_(None),
            )
        )
        if user_sede:
            q = q.filter(models.EventoAgenda.sede_id == user_sede)
        rows = q.all()
        for comment, event in rows:
            if str(persona) in [str(m) for m in (comment.mentions or [])]:
                results.append(schemas.ProjectCommentItem(
                    id=comment.id,
                    project_id=str(event.id),
                    task_id=None,
                    content=comment.content,
                    author_id=str(comment.author_id) if comment.author_id else None,
                    author_name="",
                    is_resolved=False,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                    attachments=comment.attachments or [],
                    mentions=comment.mentions or [],
                    module_type="agenda",
                    context_title=event.titulo if event else None,
                ))

    results.sort(key=lambda x: x.created_at, reverse=True)
    return results[:limit]

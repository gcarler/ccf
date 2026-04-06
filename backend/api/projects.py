from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from pydantic import BaseModel as pydantic_BaseModel
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import text, func
import uuid

from backend import models, schemas
from backend.auth import require_active_user, require_staff_or_admin
from backend.core.database import get_db
from backend.core.audit import record_admin_action
from backend.core.uploads import save_upload, sanitize_filename
from backend.core.config import get_settings

settings = get_settings()


router = APIRouter()


@router.get("/tasks", response_model=List[schemas.ProjectTask])
def list_all_my_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    """Obtiene todas las tareas asignadas al usuario actual de todos los proyectos."""
    tasks = db.query(models.ProjectTask).filter(models.ProjectTask.assignee_id == current_user.id).all()
    for t in tasks: _normalize_dates(t)
    return tasks


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_project(db: Session, project_id: int) -> models.Project:
    project = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks),
            selectinload(models.Project.milestones),
            selectinload(models.Project.activity_logs).selectinload(models.ProjectActivityLog.user)
        )
        .filter(models.Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ensure_task(db: Session, task_id: int) -> models.ProjectTask:
    task = (
        db.query(models.ProjectTask)
        .options(
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.attachments)
        )
        .filter(models.ProjectTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _normalize_dates(obj):
    if not obj: return obj
    # Soporte mejorado para múltiples formatos de fecha de SQLite
    for attr in ['created_at', 'target_date', 'due_date', 'start_date', 'updated_at', 'last_edited_at']:
        val = getattr(obj, attr, None)
        if val and isinstance(val, str):
            try:
                # Limpiar milisegundos si es necesario
                clean_val = val.split('.')[0] if '.' in val and 'T' not in val else val
                setattr(obj, attr, datetime.fromisoformat(clean_val.replace(' ', 'T').replace('Z', '+00:00')))
            except Exception as e:
                print(f"Error normalizing {attr}: {e}")
                if attr == 'created_at': setattr(obj, attr, datetime.now())
    return obj

@router.get("/", response_model=List[schemas.Project])
def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Project).options(
        selectinload(models.Project.tasks).selectinload(models.ProjectTask.attachments),
        selectinload(models.Project.milestones),
    )
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    if owner_id:
        query = query.filter(models.Project.owner_id == owner_id)

    projects = query.order_by(models.Project.id.desc()).all()
    for p in projects:
        _normalize_dates(p)
        for m in p.milestones: _normalize_dates(m)
        for t in p.tasks:
            _normalize_dates(t)
            # Normalize attachments from ORM objects to dicts for Pydantic serialization
            if hasattr(t, 'attachments') and t.attachments:
                t.__dict__['attachments'] = [
                    {
                        "id": a.id,
                        "task_id": a.task_id,
                        "filename": a.filename,
                        "file_url": a.file_url,
                        "file_type": a.file_type,
                        "file_size": a.file_size,
                    }
                    for a in t.attachments
                ]
            else:
                t.__dict__.setdefault('attachments', [])
    return projects



@router.post("/", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Auditoría real
    record_admin_action(db, current_user, action="create_project", resource_type="project", resource_id=str(db_project.id))
    
    _normalize_dates(db_project)
    return db_project


@router.post("/{project_id}/tasks", response_model=schemas.ProjectTask, status_code=status.HTTP_201_CREATED)
def create_project_task(
    project_id: int,
    task: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _ensure_project(db, project_id)
    max_order = db.query(func.max(models.ProjectTask.order_index)).filter(models.ProjectTask.project_id == project_id).scalar() or 0
    payload = task.model_dump()
    payload["project_id"] = project_id
    payload["order_index"] = max_order + 1
    db_task = models.ProjectTask(**payload)
    db.add(db_task)
    
    # Bitácora Ministerial
    activity = models.ProjectActivityLog(
        project_id=project_id, user_id=current_user.id, action_type='task_created',
        description=f"Tarea '{db_task.title}' lanzada por {current_user.username}"
    )
    db.add(activity)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.get("/{project_id}", response_model=schemas.Project)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    p = _ensure_project(db, project_id)
    _normalize_dates(p)
    for m in p.milestones: _normalize_dates(m)
    for t in p.tasks: _normalize_dates(t)
    for log in p.activity_logs:
        _normalize_dates(log)
        log.user_name = log.user.username if log.user else "Sistema"
    return p


# --- WIKI & WHITEBOARD CON CALIDAD AUDITADA ---

@router.get("/{project_id}/wiki", response_model=Optional[schemas.ProjectDocument])
def get_project_wiki(project_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == project_id).first()
    return _normalize_dates(doc)

@router.post("/{project_id}/wiki")
def update_project_wiki(
    project_id: int, 
    payload: Dict[str, Any], 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == project_id).first()
    content = payload.get("content", "")
    
    if not doc:
        doc = models.ProjectDocument(project_id=project_id, title="Wiki Ministerial", content=content, author_id=current_user.id)
        db.add(doc)
    else:
        doc.content = content
        doc.author_id = current_user.id
        doc.last_edited_at = datetime.now()
    
    # Registrar cambio en la bitácora
    activity = models.ProjectActivityLog(
        project_id=project_id, user_id=current_user.id, action_type='wiki_updated',
        description=f"Documentación Wiki actualizada."
    )
    db.add(activity)
    db.commit()
    return {"status": "success"}

@router.get("/{project_id}/whiteboard", response_model=Optional[schemas.ProjectWhiteboard])
def get_project_whiteboard(project_id: int, db: Session = Depends(get_db)):
    board = db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == project_id).first()
    return _normalize_dates(board)

@router.post("/{project_id}/whiteboard")
def update_project_whiteboard(
    project_id: int, 
    payload: Dict[str, Any], 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    board = db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == project_id).first()
    elements = payload.get("elements_json", "[]")
    
    if not board:
        board = models.ProjectWhiteboard(project_id=project_id, title="Pizarra Estratégica", elements_json=elements)
        db.add(board)
    else:
        board.elements_json = elements
        board.updated_at = datetime.now()
    
    db.commit()
    return {"status": "success"}

# --- ATTACHMENTS & SUPPLIES ---

@router.post("/{project_id}/tasks/{task_id}/attachments", response_model=schemas.ProjectTask)
async def upload_task_attachment(
    project_id: int,
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    task = _ensure_task(db, task_id)
    filename = sanitize_filename(file.filename or "file")
    unique_name = f"task_{task_id}_{uuid.uuid4().hex[:8]}_{filename}"
    contents = await file.read()
    
    url = save_upload(contents, unique_name, settings.uploads_dir)
    
    attachment = models.ProjectAttachment(
        task_id=task_id,
        filename=filename,
        file_url=f"/api/static/{unique_name}",
        file_type=file.content_type,
        file_size=len(contents),
        uploader_id=current_user.id
    )
    db.add(attachment)
    db.commit()
    db.refresh(task)
    return task

@router.patch("/{project_id}/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_project_task(
    project_id: int,
    task_id: int,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Actualiza una tarea con auditoría ministerial automática."""
    task = _ensure_task(db, task_id)
    update_data = payload.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    return task


# ── COMMENTS ──────────────────────────────────────────────────────────────────

@router.get("/comments", response_model=List[schemas.ProjectCommentItem])
def list_all_comments(
    unresolved_only: bool = False,
    limit: int = Query(120, le=500),
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Lista todos los comentarios de proyectos con filtros opcionales."""
    q = db.query(models.ProjectComment)
    if unresolved_only:
        q = q.filter(models.ProjectComment.is_resolved == False)
    if project_id:
        q = q.filter(models.ProjectComment.project_id == project_id)
    rows = q.order_by(models.ProjectComment.created_at.desc()).limit(limit).all()
    result = []
    for row in rows:
        author = db.query(models.User).filter(models.User.id == row.author_id).first()
        result.append(schemas.ProjectCommentItem(
            id=row.id,
            project_id=row.project_id,
            task_id=row.task_id,
            content=row.content,
            author_id=row.author_id,
            author_name=f"{author.first_name} {author.last_name}" if author else "Usuario",
            is_resolved=row.is_resolved,
            created_at=row.created_at,
            updated_at=row.updated_at,
        ))
    return result


@router.post("/{project_id}/comments", response_model=schemas.ProjectCommentItem)
def create_project_comment(
    project_id: int,
    payload: schemas.ProjectCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Crea un comentario en un proyecto."""
    _ensure_project(db, project_id)
    comment = models.ProjectComment(
        project_id=project_id,
        task_id=payload.task_id,
        author_id=current_user.id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=comment.project_id,
        task_id=comment.task_id,
        content=comment.content,
        author_id=comment.author_id,
        author_name=f"{current_user.first_name} {current_user.last_name}",
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.patch("/comments/{comment_id}", response_model=schemas.ProjectCommentItem)
def update_project_comment(
    comment_id: int,
    payload: schemas.ProjectCommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Actualiza un comentario (contenido o estado de resolución)."""
    comment = db.query(models.ProjectComment).filter(models.ProjectComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if payload.content is not None:
        comment.content = payload.content
    if payload.is_resolved is not None:
        comment.is_resolved = payload.is_resolved
    db.commit()
    db.refresh(comment)
    author = db.query(models.User).filter(models.User.id == comment.author_id).first()
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=comment.project_id,
        task_id=comment.task_id,
        content=comment.content,
        author_id=comment.author_id,
        author_name=f"{author.first_name} {author.last_name}" if author else "Usuario",
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# ── INBOX ──────────────────────────────────────────────────────────────────────

@router.get("/inbox", response_model=List[schemas.ProjectInboxItem])
def list_inbox(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Bandeja de entrada: tareas recién asignadas y comentarios no leídos."""
    inbox_items: list[schemas.ProjectInboxItem] = []

    # Comentarios no leídos en proyectos del usuario
    unread_comments = (
        db.query(models.ProjectComment, models.Project)
        .join(models.Project, models.Project.id == models.ProjectComment.project_id)
        .filter(
            models.ProjectComment.is_resolved == False,
            models.ProjectComment.author_id != current_user.id,
        )
        .order_by(models.ProjectComment.created_at.desc())
        .limit(limit)
        .all()
    )

    for comment, project in unread_comments:
        # Verificar si ya fue leído por el usuario
        state = db.query(models.ProjectInboxState).filter(
            models.ProjectInboxState.user_id == current_user.id,
            models.ProjectInboxState.item_id == f"comment-{comment.id}",
        ).first()
        is_read = state.is_read if state else False

        author = db.query(models.User).filter(models.User.id == comment.author_id).first()
        inbox_items.append(schemas.ProjectInboxItem(
            id=f"comment-{comment.id}",
            type="comment",
            user=f"{author.first_name} {author.last_name}" if author else "Usuario",
            content=comment.content[:120],
            project=project.title,
            project_id=project.id,
            task_id=comment.task_id,
            is_read=is_read,
            created_at=comment.created_at,
        ))

    return inbox_items[:limit]


@router.post("/inbox/{item_id}/read", response_model=dict)
def mark_inbox_read(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Marca un item del inbox como leído."""
    state = db.query(models.ProjectInboxState).filter(
        models.ProjectInboxState.user_id == current_user.id,
        models.ProjectInboxState.item_id == item_id,
    ).first()
    if state:
        state.is_read = True
    else:
        state = models.ProjectInboxState(
            user_id=current_user.id,
            item_id=item_id,
            is_read=True,
        )
        db.add(state)
    db.commit()
    return {"ok": True, "item_id": item_id}

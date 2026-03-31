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
        selectinload(models.Project.tasks),
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
        for t in p.tasks: _normalize_dates(t)
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

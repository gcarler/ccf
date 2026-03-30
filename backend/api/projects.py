from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from pydantic import BaseModel as pydantic_BaseModel
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import text
import uuid

from backend import models, schemas
from backend.auth import require_active_user, require_staff_or_admin
from backend.core.database import get_db
from backend.core.audit import record_admin_action
from backend.core.uploads import save_upload, sanitize_filename
from backend.core.config import get_settings

settings = get_settings()


router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_project(project: models.Project) -> Dict[str, Any]:
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "status": project.status,
        "owner_id": project.owner_id,
        "color": project.color,
        "icon": project.icon,
        "created_at": project.created_at,
        "task_count": len(project.tasks),
        "completed_tasks": len([t for t in project.tasks if t.status == "done"]),
    }


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
        .options(selectinload(models.ProjectTask.supplies))
        .filter(models.ProjectTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _get_inbox_state_map(db: Session, user_id: int) -> Dict[str, bool]:
    states = (
        db.query(models.ProjectInboxState)
        .filter(models.ProjectInboxState.user_id == user_id)
        .all()
    )
    return {s.item_id: s.is_read for s in states}

def _normalize_dates(obj):
    if not obj: return obj
    if hasattr(obj, 'created_at') and isinstance(obj.created_at, str):
        try:
            obj.created_at = datetime.fromisoformat(obj.created_at.replace('Z', '+00:00'))
        except:
            obj.created_at = datetime.now()
    if hasattr(obj, 'target_date') and isinstance(obj.target_date, str):
        try:
            obj.target_date = datetime.fromisoformat(obj.target_date.replace('Z', '+00:00'))
        except:
            obj.target_date = None
    if hasattr(obj, 'due_date') and isinstance(obj.due_date, str):
        try:
            obj.due_date = datetime.fromisoformat(obj.due_date.replace('Z', '+00:00'))
        except:
            obj.due_date = None
    if hasattr(obj, 'start_date') and isinstance(obj.start_date, str):
        try:
            obj.start_date = datetime.fromisoformat(obj.start_date.replace('Z', '+00:00'))
        except:
            obj.start_date = None
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
        selectinload(models.Project.activity_logs)
    )
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    if owner_id:
        query = query.filter(models.Project.owner_id == owner_id)

    projects = query.order_by(models.Project.id.desc()).all()
    
    for p in projects:
        _normalize_dates(p)
        for m in p.milestones:
            _normalize_dates(m)
        for t in p.tasks:
            _normalize_dates(t)
        for log in p.activity_logs:
            _normalize_dates(log)
    
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

    record_admin_action(
        db, current_user,
        action="create_project",
        resource_type="project",
        resource_id=str(db_project.id)
    )
    
    _normalize_dates(db_project)
    return db_project
@router.get("/{project_id}", response_model=schemas.Project)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    project = _ensure_project(db, project_id)
    _normalize_dates(project)
    return project

@router.patch("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    project = _ensure_project(db, project_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    _normalize_dates(project)
    return project


@router.post("/{project_id}/tasks", response_model=schemas.ProjectTask, status_code=status.HTTP_201_CREATED)
def create_project_task(
    project_id: int,
    task: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Crea una tarea con auditoría ministerial y ordenamiento automático."""
    _ensure_project(db, project_id)
    
    # Calcular el siguiente índice de orden
    from sqlalchemy import func
    max_order = db.query(func.max(models.ProjectTask.order_index)).filter(
        models.ProjectTask.project_id == project_id
    ).scalar() or 0

    payload = task.model_dump()
    payload["project_id"] = project_id
    payload["order_index"] = max_order + 1
    
    db_task = models.ProjectTask(**payload)
    db.add(db_task)
    
    # Registrar en la bitácora de actividad
    activity = models.ProjectActivityLog(
        project_id=project_id,
        user_id=current_user.id,
        action_type='task_created',
        description=f"Tarea '{db_task.title}' creada por {current_user.username}"
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
    
    # Enriquecer logs con nombres de usuario
    for log in p.activity_logs:
        _normalize_dates(log)
        log.user_name = log.user.username if log.user else "Sistema"
        
    return p


@router.patch("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    project = _ensure_project(db, project_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    project = _ensure_project(db, project_id)
    db.delete(project)
    db.commit()
    return None


@router.get("/tasks", response_model=List[schemas.ProjectTask])
def list_tasks(
    project_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    query = db.query(models.ProjectTask).options(selectinload(models.ProjectTask.supplies))
    if project_id:
        query = query.filter(models.ProjectTask.project_id == project_id)
    if status_filter:
        query = query.filter(models.ProjectTask.status == status_filter)

    tasks = query.order_by(models.ProjectTask.id.desc()).all()
    for t in tasks: _normalize_dates(t)
    return tasks


@router.get("/{project_id}/tasks", response_model=List[schemas.ProjectTask])
def list_project_tasks_nested(
...
    tasks = query.order_by(models.ProjectTask.id.desc()).limit(limit).all()
    for t in tasks: _normalize_dates(t)
    return tasks


# --- WIKI & WHITEBOARD ENDPOINTS ---

@router.get("/{project_id}/wiki", response_model=Optional[schemas.ProjectDocument])
def get_project_wiki(project_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == project_id).first()
    return doc

@router.post("/{project_id}/wiki")
def update_project_wiki(project_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == project_id).first()
    if not doc:
        doc = models.ProjectDocument(project_id=project_id, title="Wiki Principal", content=payload.get("content", ""))
        db.add(doc)
    else:
        doc.content = payload.get("content", "")
        doc.last_edited_at = datetime.now()
    db.commit()
    return {"status": "success"}

@router.get("/{project_id}/whiteboard", response_model=Optional[schemas.ProjectWhiteboard])
def get_project_whiteboard(project_id: int, db: Session = Depends(get_db)):
    board = db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == project_id).first()
    return board

@router.post("/{project_id}/whiteboard")
def update_project_whiteboard(project_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    board = db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == project_id).first()
    if not board:
        board = models.ProjectWhiteboard(project_id=project_id, title="Pizarra Principal", elements_json=payload.get("elements_json", "[]"))
        db.add(board)
    else:
        board.elements_json = payload.get("elements_json", "[]")
        board.updated_at = datetime.now()
    db.commit()
    return {"status": "success"}

@router.patch("/{project_id}/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_project_task(
    project_id: int,
    task_id: int,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    task = _ensure_task(db, task_id)
    if task.project_id != project_id:
        raise HTTPException(status_code=400, detail="Task does not belong to project")

    update_data = payload.model_dump(exclude_unset=True)
    if "attachments" in update_data:
        # Avoid direct overwrite if needed, or just let pydantic allow setting JSON.
        pass
    
    for key, value in update_data.items():
        setattr(task, key, value)
        
    db.commit()
    db.refresh(task)
    _normalize_dates(task)
    return task

class SupplyPayload(pydantic_BaseModel):
    item_name: str

@router.post("/{project_id}/tasks/{task_id}/supplies", response_model=schemas.ProjectTask)
def add_task_supply(
    project_id: int,
    task_id: int,
    payload: SupplyPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    task = _ensure_task(db, task_id)
    supply = models.TaskSupply(task_id=task_id, item_name=payload.item_name)
    db.add(supply)
    db.commit()
    db.refresh(task)
    _normalize_dates(task)
    return task

class SupplyUpdatePayload(pydantic_BaseModel):
    status: str

@router.patch("/{project_id}/tasks/{task_id}/supplies/{supply_id}", response_model=schemas.ProjectTask)
def update_task_supply(
    project_id: int,
    task_id: int,
    supply_id: int,
    payload: SupplyUpdatePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    task = _ensure_task(db, task_id)
    s = db.query(models.TaskSupply).filter(models.TaskSupply.id == supply_id).first()
    if s and payload.status:
        s.status = payload.status
        db.commit()
    db.refresh(task)
    _normalize_dates(task)
    return task

@router.delete("/{project_id}/tasks/{task_id}/supplies/{supply_id}", response_model=schemas.ProjectTask)
def remove_task_supply(
    project_id: int,
    task_id: int,
    supply_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    task = _ensure_task(db, task_id)
    s = db.query(models.TaskSupply).filter(models.TaskSupply.id == supply_id).first()
    if s:
        db.delete(s)
        db.commit()
    db.refresh(task)
    _normalize_dates(task)
    return task

@router.post("/{project_id}/tasks/{task_id}/attachments", response_model=schemas.ProjectTask)
async def upload_task_attachment(
    project_id: int,
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    task = _ensure_task(db, task_id)
    if task.project_id != project_id:
        raise HTTPException(400, "Validation error")

    filename = sanitize_filename(file.filename or "file")
    ext = filename.split(".")[-1] if "." in filename else "bin"
    unique_name = f"task_{task_id}_{uuid.uuid4().hex[:8]}.{ext}"
    contents = await file.read()
    
    url = save_upload(contents, unique_name, settings.uploads_dir)
    
    obj = {"name": filename, "url": f"/api/static/{unique_name}"}
    
    current_atts = task.attachments or []
    if not isinstance(current_atts, list):
        current_atts = []
    
    task.attachments = current_atts + [obj]
    db.commit()
    db.refresh(task)
    _normalize_dates(task)
    return task

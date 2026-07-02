from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session, selectinload

from backend import crud, models, schemas
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import normalize_role, require_module_access, require_staff_or_admin
from backend.core.storage import storage_service
from backend.core.uploads import sanitize_filename
from backend.crud.crm import get_user_sede_id
from backend.crud.projects import get_user_persona_id
from backend.mesh_websockets import manager
from backend.services.task_notifications import notify_task_assigned

settings = get_settings()


router = APIRouter()
logger = logging.getLogger(__name__)


def _resolve_persona(db: Session, user_id: Any):
    persona_id = get_user_persona_id(db, user_id)
    if not persona_id:
        return None
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()


def _author_name(persona) -> str:
    if not persona:
        return "Usuario"
    return getattr(persona, "nombre_completo", None) or getattr(persona, "full_name", None) or "Usuario"


def _assignment_changed(previous_assignee_id, current_assignee_id) -> bool:
    if previous_assignee_id is None and current_assignee_id is None:
        return False
    return str(previous_assignee_id) != str(current_assignee_id)


@router.get("/tasks", response_model=List[schemas.ProjectTask])
def list_all_my_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene todas las tareas asignadas al usuario actual de todos los proyectos."""
    persona_id = get_user_persona_id(db, current_user.id)
    if not persona_id:
        return []
    tasks = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.assignee_id == persona_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .all()
    )
    for t in tasks:
        _normalize_dates(t)
    return tasks


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _log_project_activity(db: Session, project_id: Any, user_id: Any, action_type: str, description: str):
    persona_id = get_user_persona_id(db, user_id)
    activity = models.ProjectActivityLog(
        project_id=_to_uuid(project_id),
        persona_id=persona_id,
        action_type=action_type,
        description=description,
    )
    db.add(activity)
    return activity


def _to_uuid(val):
    """Convert string UUID to uuid.UUID for SQLAlchemy filters."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return val


def _ensure_project(db: Session, project_id: str, user_sede=None) -> models.Project:
    project = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks),
            selectinload(models.Project.milestones),
            selectinload(models.Project.activity_logs),
        )
        .filter(models.Project.id == _to_uuid(project_id), models.Project.deleted_at.is_(None))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if user_sede and project.sede_id and project.sede_id != user_sede:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ensure_task(db: Session, task_id: str) -> models.ProjectTask:
    task = (
        db.query(models.ProjectTask)
        .options(
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.attachments),
        )
        .filter(models.ProjectTask.id == _to_uuid(task_id), models.ProjectTask.deleted_at.is_(None))
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _ensure_task_in_project(db: Session, project_id: str, task_id: str) -> models.ProjectTask:
    task = _ensure_task(db, task_id)
    if str(task.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Task not found in project")
    return task


def _ensure_supply_in_task(db: Session, project_id: str, task_id: str, supply_id: UUID) -> models.TaskSupply:
    _ensure_task_in_project(db, project_id, task_id)
    supply = (
        db.query(models.TaskSupply)
        .filter(models.TaskSupply.id == supply_id, models.TaskSupply.task_id == _to_uuid(task_id))
        .first()
    )
    if not supply:
        raise HTTPException(status_code=404, detail="Supply not found in task")
    return supply


def _ensure_milestone_in_project(db: Session, project_id: str, milestone_id: str) -> models.ProjectMilestone:
    milestone = (
        db.query(models.ProjectMilestone)
        .filter(
            models.ProjectMilestone.id == _to_uuid(milestone_id),
            models.ProjectMilestone.project_id == _to_uuid(project_id),
        )
        .first()
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found in project")
    return milestone


def _serialize_task_attachments(task: models.ProjectTask) -> models.ProjectTask:
    task.__dict__["attachments"] = [
        {
            "id": attachment.id,
            "task_id": attachment.task_id,
            "filename": attachment.filename,
            "file_url": attachment.file_url,
            "file_type": attachment.file_type,
            "file_size": attachment.file_size,
            "created_at": attachment.created_at,
        }
        for attachment in (task.attachments or [])
    ]
    return task


def _normalize_dates(obj):
    if not obj:
        return obj
    # Soporte mejorado para multiples formatos de fecha de SQLite
    for attr in [
        "created_at",
        "target_date",
        "due_date",
        "start_date",
        "updated_at",
        "last_edited_at",
    ]:
        val = getattr(obj, attr, None)
        if val and isinstance(val, str):
            try:
                # Limpiar milisegundos si es necesario
                clean_val = val.split(".")[0] if "." in val and "T" not in val else val
                setattr(
                    obj,
                    attr,
                    datetime.fromisoformat(clean_val.replace(" ", "T").replace("Z", "+00:00")),
                )
            except MemoryError:
                raise
            except Exception:
                logger.debug(
                    "Failed to normalize project date",
                    extra={"attribute": attr, "value": val},
                )
                if attr == "created_at":
                    setattr(obj, attr, datetime.now())
    return obj


@router.get("", response_model=List[schemas.Project])
def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    query = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.attachments),
            selectinload(models.Project.milestones),
        )
        .filter(models.Project.deleted_at.is_(None))
    )
    if user_sede:
        query = query.filter(models.Project.sede_id == user_sede)
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    if owner_id:
        query = query.filter(models.Project.owner_id == owner_id)

    projects = query.order_by(models.Project.created_at.desc()).all()
    for p in projects:
        _normalize_dates(p)
        for m in p.milestones:
            _normalize_dates(m)
        for t in p.tasks:
            _normalize_dates(t)
            # Normalize attachments from ORM objects to dicts for Pydantic serialization
            if hasattr(t, "attachments") and t.attachments:
                t.__dict__["attachments"] = [
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
                t.__dict__.setdefault("attachments", [])
    return projects


@router.post("", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    owner_persona_id = get_user_persona_id(db, current_user.id)
    user_sede = get_user_sede_id(db, current_user.id)
    db_project = crud.create_project(db, project, owner_persona_id=owner_persona_id, sede_id=user_sede)

    crud.create_default_phases(db, db_project.id)

    if owner_persona_id:
        crud.create_activity_log(
            db, db_project.id, owner_persona_id, "project_created", f"Proyecto '{db_project.title}' creado"
        )

    record_admin_action(
        db, current_user, action="create_project", resource_type="project", resource_id=str(db_project.id)
    )
    _normalize_dates(db_project)
    return db_project


# ── Phases / Kanban Columns ─────────────────────────────


@router.get("/{project_id}/phases", response_model=List[schemas.ProjectPhaseSchema])
def list_project_phases(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista las fases (columnas del kanban) de un proyecto."""
    _ensure_project(db, project_id)
    return crud.get_project_phases(db, project_id)


@router.put("/{project_id}/phases", response_model=List[schemas.ProjectPhaseSchema])
def set_project_phases(
    project_id: str,
    phases: List[schemas.ProjectPhaseInput],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Reemplaza todas las fases del proyecto (reordenar / renombrar / agregar / eliminar).
    El orden en el array define el order_index de cada fase.
    Solo administradores y gestores pueden modificar fases.
    """
    _project = _ensure_project(db, project_id)

    # Check no phase with tasks is being deleted
    existing = {p.slug for p in crud.get_project_phases(db, project_id)}
    incoming = {p.slug for p in phases}
    removed = existing - incoming
    if removed:
        has_tasks = (
            db.query(models.ProjectTask)
            .filter(
                models.ProjectTask.project_id == project_id,
                models.ProjectTask.status.in_(removed),
            )
            .count()
        )
        if has_tasks:
            raise HTTPException(
                status_code=409,
                detail=f"No se puede eliminar la fase '{next(iter(removed))}': tiene {has_tasks} tarea(s) asignada(s). Mueve las tareas primero.",
            )

    phase_dicts = [{"name": p.name, "slug": p.slug, "color": p.color, "order_index": i} for i, p in enumerate(phases)]
    created = crud.set_project_phases(db, project_id, phase_dicts)
    return created


# --- COMMENTS ---


@router.get("/comments", response_model=List[schemas.ProjectCommentItem])
def list_all_comments(
    unresolved_only: bool = False,
    limit: int = Query(120, le=500),
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todos los comentarios de proyectos con filtros opcionales."""
    q = db.query(models.ProjectComment).filter(models.ProjectComment.deleted_at.is_(None))
    if unresolved_only:
        q = q.filter(models.ProjectComment.is_resolved.is_(False))
    if project_id:
        q = q.filter(models.ProjectComment.project_id == _to_uuid(project_id))
    if task_id:
        q = q.filter(models.ProjectComment.task_id == _to_uuid(task_id))
    rows = q.order_by(models.ProjectComment.created_at.desc()).limit(limit).all()
    # Batch-fetch authors to avoid N+1 queries
    author_ids = {row.author_id for row in rows if row.author_id}
    authors_map = {}
    if author_ids:
        authors = db.query(models.Persona).filter(models.Persona.id.in_(author_ids)).all()
        authors_map = {p.id: _author_name(p) for p in authors}
    result = []
    for row in rows:
        result.append(
            schemas.ProjectCommentItem(
                id=row.id,
                project_id=row.project_id,
                task_id=row.task_id,
                content=row.content,
                author_id=row.author_id,
                author_name=authors_map.get(row.author_id, "Usuario"),
                is_resolved=row.is_resolved,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return result


@router.post(
    "/{project_id}/tasks",
    response_model=schemas.ProjectTask,
    status_code=status.HTTP_201_CREATED,
)
def create_project_task(
    project_id: str,
    task: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    _ensure_project(db, project_id)
    project = db.query(models.Project).filter(models.Project.id == _to_uuid(project_id)).first()
    max_order = (
        db.query(func.max(models.ProjectTask.order_index))
        .filter(models.ProjectTask.project_id == _to_uuid(project_id))
        .scalar()
        or 0
    )
    payload = task.model_dump()
    payload["project_id"] = _to_uuid(project_id)
    payload["order_index"] = max_order + 1
    db_task = models.ProjectTask(**payload)
    db.add(db_task)

    # Bitacora Ministerial
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "task_created",
        f"Tarea '{db_task.title}' lanzada por {getattr(current_user, 'username', getattr(current_user, 'email', 'usuario'))}",
    )
    db.commit()
    db.refresh(db_task)
    if getattr(db_task, "assignee_id", None):
        notify_task_assigned(
            db,
            task=db_task,
            project=project,
            assigned_by_user_id=current_user.id,
        )
    return db_task


# ── PORTFOLIO SUMMARY ──────────────────────────────────────────────────────────


@router.get("/summary", response_model=List[schemas.ProjectPortfolioSummaryRow])
def portfolio_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Resumen de portafolio agrupado por estatus de proyecto."""
    done_case = func.coalesce(func.sum(cast(models.ProjectTask.status == "completed", Integer)), 0).label(
        "completed_tasks"
    )

    rows = (
        db.query(
            models.Project.status,
            func.count(models.Project.id).label("total_projects"),
            func.count(models.ProjectTask.id).label("total_tasks"),
            done_case,
        )
        .outerjoin(models.ProjectTask, models.ProjectTask.project_id == models.Project.id)
        .group_by(models.Project.status)
        .all()
    )

    return [
        schemas.ProjectPortfolioSummaryRow(
            project_status=row[0] or "unknown",
            total_projects=row[1],
            total_tasks=row[2] or 0,
            completed_tasks=row[3] or 0,
            completion_ratio=round((row[3] or 0) / max(row[2] or 1, 1), 2),
        )
        for row in rows
    ]


@router.get("/workload", response_model=List[schemas.ProjectWorkloadSummaryRow])
def workload_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Resumen de carga de trabajo por persona."""
    review_case = func.coalesce(func.sum(cast(models.ProjectTask.status == "review", Integer)), 0).label("in_review")

    rows = (
        db.query(
            models.ProjectTask.assignee_id,
            func.count(models.ProjectTask.id).label("open_tasks"),
            review_case,
        )
        .filter(
            models.ProjectTask.status.in_(["todo", "in_progress", "review"]),
            models.ProjectTask.assignee_id.isnot(None),
        )
        .group_by(models.ProjectTask.assignee_id)
        .all()
    )

    result = []
    for row in rows:
        overdue = (
            db.query(func.count(models.ProjectTask.id))
            .filter(
                models.ProjectTask.assignee_id == row[0],
                models.ProjectTask.due_date < func.now(),
                models.ProjectTask.status.in_(["todo", "in_progress", "review"]),
            )
            .scalar()
            or 0
        )
        result.append(
            schemas.ProjectWorkloadSummaryRow(
                assignee_id=str(row[0]) if row[0] else None,
                open_tasks=row[1] or 0,
                in_review=row[2] or 0,
                overdue_tasks=overdue,
            )
        )
    return result


@router.get("/activities", response_model=List[schemas.ProjectActivityItem])
def list_activities(
    limit: int = Query(20, le=200),
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Feed de actividad global de proyectos."""
    q = db.query(models.ProjectActivityLog).order_by(models.ProjectActivityLog.created_at.desc())
    if project_id:
        q = q.filter(models.ProjectActivityLog.project_id == _to_uuid(project_id))
    logs = q.limit(limit).all()

    result = []
    for log in logs:
        _normalize_dates(log)
        project = db.query(models.Project).filter(models.Project.id == log.project_id).first()
        result.append(
            schemas.ProjectActivityItem(
                id=str(log.id),
                kind=log.action_type,
                project_id=log.project_id,
                project_title=project.title if project else "Proyecto",
                description=log.description or "",
                created_at=log.created_at or _utcnow(),
            )
        )
    return result


@router.get("/tasks/{task_id}", response_model=schemas.ProjectTask)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene una tarea por ID."""
    task = _ensure_task(db, task_id)
    _normalize_dates(task)
    return task


@router.patch("/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_task(
    task_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Actualiza una tarea usando ruta plana (sin project_id)."""
    task = _ensure_task(db, task_id)
    previous_assignee_id = getattr(task, "assignee_id", None)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    task.updated_at = _utcnow()
    db.commit()
    db.refresh(task)
    if "assignee_id" in update_data and _assignment_changed(previous_assignee_id, getattr(task, "assignee_id", None)) and task.assignee_id:
        notify_task_assigned(
            db,
            task=task,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    _normalize_dates(task)
    return task


# ── INBOX (must be before /{project_id} routes) ────────────────────────────────


@router.get("/inbox", response_model=List[schemas.ProjectInboxItem])
def list_inbox(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Bandeja de entrada: tareas recién asignadas y comentarios no leídos."""
    inbox_items: list[schemas.ProjectInboxItem] = []

    # Obtener persona_id (UUID) desde current_user.id (Integer)
    persona = _resolve_persona(db, current_user.id)
    persona_id = persona.id if persona else None

    # Comentarios no leídos en proyectos del usuario
    unread_comments = ()
    if persona_id:
        unread_comments = (
            db.query(models.ProjectComment, models.Project)
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .filter(
                ~models.ProjectComment.is_resolved,
                models.ProjectComment.author_id != persona_id,
            )
            .order_by(models.ProjectComment.created_at.desc())
            .limit(limit)
            .all()
        )

    for comment, project in unread_comments:
        state = (
            db.query(models.ProjectInboxState)
            .filter(
                models.ProjectInboxState.persona_id == persona_id,
                models.ProjectInboxState.item_id == f"comment-{comment.id}",
            )
            .first()
        )
        is_read = state.is_read if state else False

        author = db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()
        inbox_items.append(
            schemas.ProjectInboxItem(
                id=f"comment-{comment.id}",
                type="comment",
                user=_author_name(author),
                content=comment.content[:120],
                project=project.title,
                project_id=project.id,
                task_id=comment.task_id,
                is_read=is_read,
                created_at=comment.created_at,
            )
        )

    return inbox_items[:limit]


@router.post("/inbox/{item_id}/read", response_model=dict)
def mark_inbox_read(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Marca un item del inbox como leído."""
    persona = _resolve_persona(db, current_user.id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    state = (
        db.query(models.ProjectInboxState)
        .filter(
            models.ProjectInboxState.persona_id == persona.id,
            models.ProjectInboxState.item_id == item_id,
        )
        .first()
    )
    if state:
        state.is_read = True
    else:
        state = models.ProjectInboxState(persona_id=persona.id, item_id=item_id, is_read=True)
        db.add(state)
    db.commit()
    return {"ok": True, "item_id": item_id}


# ── PROJECT BY ID ─────────────────────────────────────────────────────────────


@router.get("/{project_id}", response_model=schemas.Project)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    p = _ensure_project(db, project_id)
    _normalize_dates(p)
    for m in p.milestones:
        _normalize_dates(m)
    for t in p.tasks:
        _normalize_dates(t)
    for log in p.activity_logs:
        _normalize_dates(log)
        log.user_name = log.persona.nombre_completo if log.persona else "Sistema"
    return p


# --- WIKI & WHITEBOARD CON CALIDAD AUDITADA ---


@router.get("/{project_id}/wiki", response_model=Optional[schemas.ProjectDocument])
def get_project_wiki(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == project_id).first()
    return _normalize_dates(doc)


@router.post("/{project_id}/wiki", response_model=schemas.ProjectDocument)
def update_project_wiki(
    project_id: str,
    payload: schemas.ProjectDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    _ensure_project(db, project_id)  # Validates project exists
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == project_id).first()
    title = payload.title or "Wiki Ministerial"
    content = payload.content or ""
    author_persona_id = get_user_persona_id(db, current_user.id)

    if not doc:
        doc = models.ProjectDocument(
            project_id=project_id,
            title=title,
            content=content,
            author_id=author_persona_id,
        )
        db.add(doc)
    else:
        doc.title = title
        doc.content = content
        doc.author_id = author_persona_id
        doc.last_edited_at = datetime.now(timezone.utc)

    # Registrar cambio en la bitacora
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "wiki_updated",
        "Documentacion Wiki actualizada.",
    )
    db.commit()
    db.refresh(doc)
    return _normalize_dates(doc)


@router.get("/whiteboards", response_model=List[schemas.ProjectWhiteboard])
def list_whiteboards(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todas las pizarras activas ordenadas por fecha de actualización."""
    boards = (
        db.query(models.ProjectWhiteboard)
        .filter(models.ProjectWhiteboard.deleted_at.is_(None))
        .order_by(models.ProjectWhiteboard.updated_at.desc())
        .all()
    )
    return [_normalize_dates(b) for b in boards]


@router.get("/{project_id}/whiteboard", response_model=Optional[schemas.ProjectWhiteboard])
def get_project_whiteboard(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    _ensure_project(db, project_id)
    board = (
        db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == _to_uuid(project_id)).first()
    )
    return _normalize_dates(board)


@router.post("/{project_id}/whiteboard", response_model=schemas.ProjectWhiteboard)
def update_project_whiteboard(
    project_id: str,
    payload: schemas.ProjectWhiteboardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    _ensure_project(db, project_id)
    board = (
        db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == _to_uuid(project_id)).first()
    )
    title = payload.title or "Pizarra Estrategica"
    elements = payload.elements_json or "[]"

    if not board:
        board = models.ProjectWhiteboard(project_id=_to_uuid(project_id), title=title, elements_json=elements)
        db.add(board)
    else:
        board.elements_json = elements
        board.updated_at = datetime.now(timezone.utc)

    board.title = title
    if payload.thumbnail_url is not None:
        board.thumbnail_url = payload.thumbnail_url

    db.commit()
    db.refresh(board)
    return _normalize_dates(board)


@router.delete("/{project_id}/whiteboard", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_whiteboard(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Realiza soft delete de la pizarra asociada a un proyecto."""
    _ensure_project(db, project_id)
    board = (
        db.query(models.ProjectWhiteboard)
        .filter(models.ProjectWhiteboard.project_id == _to_uuid(project_id))
        .first()
    )
    if board:
        board.deleted_at = datetime.now(timezone.utc)
        db.commit()
    return None


# --- ATTACHMENTS & SUPPLIES ---


@router.post("/{project_id}/tasks/{task_id}/attachments", response_model=schemas.ProjectTask)
async def upload_task_attachment(
    project_id: str,
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    task = _ensure_task_in_project(db, project_id, task_id)
    filename = sanitize_filename(file.filename or "file")
    contents = await file.read()

    url = storage_service.save_file(contents, filename, subfolder="projects")

    uploader_persona_id = get_user_persona_id(db, current_user.id)
    attachment = models.ProjectAttachment(
        task_id=_to_uuid(task_id),
        filename=filename,
        file_url=url,
        file_type=file.content_type,
        file_size=len(contents),
        uploader_id=uploader_persona_id,
    )
    db.add(attachment)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "attachment_added",
        f"Archivo '{filename}' adjuntado a '{task.title}'",
    )
    db.commit()
    db.refresh(task)
    return _serialize_task_attachments(task)


@router.patch("/{project_id}/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_project_task(
    project_id: str,
    task_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Actualiza una tarea con auditoría ministerial automática."""
    task = _ensure_task_in_project(db, project_id, task_id)
    previous_assignee_id = getattr(task, "assignee_id", None)
    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    if "assignee_id" in update_data and _assignment_changed(previous_assignee_id, getattr(task, "assignee_id", None)) and task.assignee_id:
        notify_task_assigned(
            db,
            task=task,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    return task


@router.get("/{project_id}/tasks/{task_id}/supplies", response_model=List[schemas.TaskSupply])
def list_task_supplies(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista los insumos de una tarea."""
    _ensure_task_in_project(db, project_id, task_id)
    return (
        db.query(models.TaskSupply)
        .filter(models.TaskSupply.task_id == _to_uuid(task_id))
        .order_by(models.TaskSupply.id.asc())
        .all()
    )


@router.post(
    "/{project_id}/tasks/{task_id}/supplies",
    response_model=schemas.TaskSupply,
    status_code=status.HTTP_201_CREATED,
)
def create_task_supply(
    project_id: str,
    task_id: str,
    payload: schemas.TaskSupplyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Crea un insumo requerido para una tarea."""
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = models.TaskSupply(task_id=_to_uuid(task_id), **payload.model_dump())
    db.add(supply)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_added",
        f"Insumo '{supply.item_name}' agregado a '{task.title}'",
    )
    db.commit()
    db.refresh(supply)
    return supply


@router.patch(
    "/{project_id}/tasks/{task_id}/supplies/{supply_id}",
    response_model=schemas.TaskSupply,
)
def update_task_supply(
    project_id: str,
    task_id: str,
    supply_id: str,
    payload: schemas.TaskSupplyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Actualiza nombre, cantidad o estado de un insumo."""
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = _ensure_supply_in_task(db, project_id, task_id, supply_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supply, key, value)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_updated",
        f"Insumo '{supply.item_name}' actualizado en '{task.title}'",
    )
    db.commit()
    db.refresh(supply)
    return supply


@router.delete("/{project_id}/tasks/{task_id}/supplies/{supply_id}", response_model=dict)
def delete_task_supply(
    project_id: str,
    task_id: str,
    supply_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Elimina un insumo de una tarea."""
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = _ensure_supply_in_task(db, project_id, task_id, supply_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_deleted",
        f"Insumo '{supply.item_name}' eliminado de '{task.title}'",
    )
    supply.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": supply_id}


# ── SUBTASKS ───────────────────────────────────────────────────────────────────


@router.post(
    "/{project_id}/tasks/{task_id}/subtasks",
    response_model=schemas.ProjectTask,
    status_code=status.HTTP_201_CREATED,
)
def create_subtask(
    project_id: str,
    task_id: str,
    subtask: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Crea una subtarea (nivel 2 o 3) bajo una tarea existente."""
    _ensure_project(db, project_id)
    parent_task = _ensure_task_in_project(db, project_id, task_id)
    max_order = (
        db.query(func.max(models.ProjectTask.order_index)).filter(models.ProjectTask.parent_id == task_id).scalar() or 0
    )
    payload = subtask.model_dump()
    payload["project_id"] = project_id
    payload["parent_id"] = task_id
    payload["order_index"] = max_order + 1
    db_subtask = models.ProjectTask(**payload)
    db.add(db_subtask)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "subtask_created",
        f"Sub-actividad '{db_subtask.title}' creada bajo '{parent_task.title}'",
    )
    db.commit()
    db.refresh(db_subtask)
    if getattr(db_subtask, "assignee_id", None):
        notify_task_assigned(
            db,
            task=db_subtask,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=None,
        )
    return db_subtask


@router.patch(
    "/{project_id}/tasks/{task_id}/subtasks/{subtask_id}",
    response_model=schemas.ProjectTask,
)
def update_subtask(
    project_id: str,
    task_id: str,
    subtask_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Actualiza una subtarea."""
    _ensure_project(db, project_id)
    _ensure_task_in_project(db, project_id, task_id)
    subtask = _ensure_task_in_project(db, project_id, subtask_id)
    if str(subtask.parent_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Subtask not found under task")
    previous_assignee_id = getattr(subtask, "assignee_id", None)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(subtask, key, value)
    db.commit()
    db.refresh(subtask)
    if "assignee_id" in update_data and _assignment_changed(previous_assignee_id, getattr(subtask, "assignee_id", None)) and subtask.assignee_id:
        notify_task_assigned(
            db,
            task=subtask,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    return subtask


@router.delete("/{project_id}/tasks/{task_id}/subtasks/{subtask_id}")
def delete_subtask(
    project_id: str,
    task_id: str,
    subtask_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Elimina una subtarea."""
    _ensure_project(db, project_id)
    _ensure_task_in_project(db, project_id, task_id)
    subtask = _ensure_task_in_project(db, project_id, subtask_id)
    if str(subtask.parent_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Subtask not found under task")
    subtask.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": subtask_id}


# ── COMMENTS ──────────────────────────────────────────────────────────────────


@router.post("/comments", response_model=schemas.ProjectCommentItem)
def create_comment(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Crea un comentario usando project_id en el body."""
    project_id = payload.get("project_id")
    content = (payload.get("content") or "").strip()
    if not project_id or not content:
        raise HTTPException(status_code=400, detail="project_id and content are required")
    task_id = payload.get("task_id")
    _ensure_project(db, project_id)
    author_persona_id = get_user_persona_id(db, current_user.id)
    comment = models.ProjectComment(
        project_id=_to_uuid(project_id),
        task_id=_to_uuid(task_id) if task_id else None,
        author_id=author_persona_id,
        content=content,
    )
    db.add(comment)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "comment_added",
        content,
    )
    db.commit()
    db.refresh(comment)
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=comment.project_id,
        task_id=comment.task_id,
        content=comment.content,
        author_id=comment.author_id,
        author_name=_author_name(db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()),
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.post("/{project_id}/comments", response_model=schemas.ProjectCommentItem)
def create_project_comment(
    project_id: str,
    payload: schemas.ProjectCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Crea un comentario en un proyecto."""
    _ensure_project(db, project_id)
    author_persona_id = get_user_persona_id(db, current_user.id)
    comment = models.ProjectComment(
        project_id=project_id,
        task_id=payload.task_id,
        author_id=author_persona_id,
        content=payload.content,
    )
    db.add(comment)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "comment_added",
        payload.content,
    )
    db.commit()
    db.refresh(comment)
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=comment.project_id,
        task_id=comment.task_id,
        content=comment.content,
        author_id=comment.author_id,
        author_name=_author_name(db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()),
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.patch("/comments/{comment_id}", response_model=schemas.ProjectCommentItem)
def update_project_comment(
    comment_id: str,
    payload: schemas.ProjectCommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
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
    author = db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=comment.project_id,
        task_id=comment.task_id,
        content=comment.content,
        author_id=comment.author_id,
        author_name=_author_name(author),
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# ── TASK LIST PER PROJECT ──────────────────────────────────────────────────────


@router.get("/{project_id}/tasks", response_model=List[schemas.ProjectTask])
def list_project_tasks(
    project_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todas las tareas de un proyecto."""
    _ensure_project(db, project_id)
    q = (
        db.query(models.ProjectTask)
        .options(
            selectinload(models.ProjectTask.attachments),
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.subtasks),
        )
        .filter(models.ProjectTask.project_id == _to_uuid(project_id), models.ProjectTask.deleted_at.is_(None))
    )

    if status_filter:
        q = q.filter(models.ProjectTask.status == status_filter)

    tasks = q.order_by(models.ProjectTask.order_index.asc()).all()

    for t in tasks:
        _normalize_dates(t)
        if hasattr(t, "attachments") and t.attachments:
            t.__dict__["attachments"] = [
                {
                    "id": a.id,
                    "task_id": a.task_id,
                    "filename": a.filename,
                    "file_url": a.file_url,
                    "file_type": a.file_type,
                    "file_size": a.file_size,
                }
                for a in t.attachments if a.deleted_at is None
            ]
        else:
            t.__dict__.setdefault("attachments", [])
        if hasattr(t, "supplies") and t.supplies:
            t.supplies = [s for s in t.supplies if s.deleted_at is None]
        if hasattr(t, "subtasks") and t.subtasks:
            t.subtasks = [sub for sub in t.subtasks if sub.deleted_at is None]

    return tasks


# ── PROJECT UPDATE & DELETE ────────────────────────────────────────────────────


@router.patch("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: str,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Actualiza los metadatos de un proyecto."""
    project = _ensure_project(db, project_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    project.updated_at = _utcnow()
    db.commit()
    db.refresh(project)
    _normalize_dates(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    """Elimina un proyecto y todos sus datos relacionados."""
    project = _ensure_project(db, project_id)
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": project_id}


@router.delete("/{project_id}/tasks/{task_id}")
def delete_project_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Elimina una tarea de un proyecto."""
    _ensure_project(db, project_id)
    task = _ensure_task_in_project(db, project_id, task_id)
    task.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": task_id}


@router.delete("/comments/{comment_id}")
def delete_project_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Elimina un comentario."""
    comment = db.query(models.ProjectComment).filter(models.ProjectComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": comment_id}


# ── PROJECT CHAT ─────────────────────────────────────────────────────


@router.get("/{project_id}/messages", response_model=List[schemas.ProjectMessageItem])
def list_project_messages(
    project_id: str,
    limit: int = Query(50, le=200),
    before: Optional[int] = Query(None, alias="before"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """List project chat messages, newest first, with cursor pagination."""
    _ensure_project(db, project_id)
    room = f"project_{project_id}"
    q = db.query(models.ChatMessage).filter(models.ChatMessage.room_id == room)
    if before:
        q = q.filter(models.ChatMessage.id < before)
    rows = q.order_by(models.ChatMessage.created_at.desc()).limit(limit).all()
    sender_ids = {r.sender_id for r in rows}
    users_map = {}
    if sender_ids:
        personas = db.query(models.Persona).filter(models.Persona.id.in_(sender_ids)).all()
        users_map = {p.id: _author_name(p) for p in personas}
    return [
        schemas.ProjectMessageItem(
            id=r.id,
            sender_id=r.sender_id,
            sender_name=users_map.get(r.sender_id, "Usuario"),
            content=r.content,
            created_at=r.created_at,
            is_read=r.is_read,
        )
        for r in rows
    ]


@router.post(
    "/{project_id}/messages",
    response_model=schemas.ProjectMessageItem,
    status_code=status.HTTP_201_CREATED,
)
def send_project_message(
    project_id: str,
    payload: schemas.ProjectMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Send a message to the project chat room."""
    _ensure_project(db, project_id)
    persona = _resolve_persona(db, current_user.id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    msg = models.ChatMessage(
        sender_id=persona.id,
        room_id=f"project_{project_id}",
        content=payload.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    # Broadcast via WebSocket (safe no-op if no event loop available)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                manager.broadcast_event(
                    {
                        "event": "project_message",
                        "project_id": project_id,
                        "message": {
                            "id": msg.id,
                            "sender_id": msg.sender_id,
                            "sender_name": _author_name(persona),
                            "content": msg.content,
                            "created_at": str(msg.created_at),
                        },
                    },
                    room=f"project_{project_id}",
                )
            )
    except RuntimeError:
        pass

    return schemas.ProjectMessageItem(
        id=msg.id,
        sender_id=str(msg.sender_id),
        sender_name=_author_name(persona),
        content=msg.content,
        created_at=msg.created_at,
    )


@router.delete("/{project_id}/messages/{message_id}")
def delete_project_message(
    project_id: str,
    message_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Delete a chat message (own message or admin)."""
    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(404, detail="Message not found")
    if msg.sender_id != current_user.id:
        role = normalize_role(getattr(current_user, "role", ""))
        if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
            role = normalize_role(current_user.rol_plataforma.nombre)
        if role not in ("admin", "pastor", "coordinador"):
            raise HTTPException(403, detail="Cannot delete another user's message")
    msg.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ── MILESTONES ─────────────────────────────────────────────────────────────────


@router.get("/{project_id}/milestones", response_model=List[schemas.ProjectMilestone])
def list_project_milestones(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista los hitos de un proyecto."""
    _ensure_project(db, project_id)
    milestones = (
        db.query(models.ProjectMilestone)
        .filter(
            models.ProjectMilestone.project_id == _to_uuid(project_id),
            models.ProjectMilestone.deleted_at.is_(None),
        )
        .order_by(models.ProjectMilestone.target_date.asc())
        .all()
    )
    for m in milestones:
        _normalize_dates(m)
    return milestones


@router.post(
    "/{project_id}/milestones",
    response_model=schemas.ProjectMilestone,
    status_code=status.HTTP_201_CREATED,
)
def create_project_milestone(
    project_id: str,
    payload: schemas.ProjectMilestoneBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Crea un hito en un proyecto."""
    _ensure_project(db, project_id)
    milestone = models.ProjectMilestone(project_id=_to_uuid(project_id), **payload.model_dump())
    db.add(milestone)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "milestone_created",
        f"Hito '{milestone.title}' creado",
    )
    db.commit()
    db.refresh(milestone)
    _normalize_dates(milestone)
    return milestone


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=schemas.ProjectMilestone)
def update_project_milestone(
    project_id: str,
    milestone_id: str,
    payload: schemas.ProjectMilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Actualiza un hito y registra cambios relevantes en la bitacora."""
    _ensure_project(db, project_id)
    milestone = _ensure_milestone_in_project(db, project_id, milestone_id)
    previous_completed = milestone.is_completed
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(milestone, key, value)

    if "is_completed" in update_data and milestone.is_completed != previous_completed:
        action_type = "milestone_completed" if milestone.is_completed else "milestone_reopened"
        description = (
            f"Hito '{milestone.title}' completado" if milestone.is_completed else f"Hito '{milestone.title}' reabierto"
        )
    else:
        action_type = "milestone_updated"
        description = f"Hito '{milestone.title}' actualizado"

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        action_type,
        description,
    )
    db.commit()
    db.refresh(milestone)
    _normalize_dates(milestone)
    return milestone

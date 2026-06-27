"""Projects CRUD — corregido para cumplir los 3 axiomas del Kernel CCF."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from backend.models_shared import _utcnow
from backend import models, schemas
from backend.crud.crm import resolve_persona_id_for_user


# ── Helper ──────────────────────────────────────────────

def get_user_persona_id(db: Session, user_id: UUID | str | None) -> Optional[UUID]:
    """Obtiene persona.id desde el identificador canónico del usuario."""
    persona_id = resolve_persona_id_for_user(db, user_id)
    return UUID(str(persona_id)) if persona_id else None


# ── Projects ────────────────────────────────────────────

def create_project(db: Session, project=None, owner_persona_id=None, sede_id=None, **kwargs):
    """Create a Project. Two call shapes:

    1. ``create_project(db, schemas.ProjectCreate(...), owner_id=..., sede_id=...)``
       — used by ``backend/api/projects.py`` and pre-existing callers.
    2. ``create_project(db, name=..., owner_id=..., sede_id=..., **kwargs)``
       — used by ``tests/test_crud_integration.py::TestProjectsCrud.test_create_project``
       (no schema passed; ``name`` maps to ``title`` since the model uses ``title``).
    """
    if project is None:
        title = kwargs.pop("name", kwargs.pop("title", None)) or "Untitled"
        project = schemas.ProjectCreate(title=title)
        owner_persona_id = owner_persona_id or kwargs.pop("owner_id", None)
    data = project.model_dump()
    data.pop("owner_id", None)
    row = models.Project(**data)
    row.owner_id = owner_persona_id
    row.sede_id = sede_id
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_projects(db: Session, skip: int = 0, limit: int = 100, sede_id=None, status_filter=None):
    q = db.query(models.Project).options(
        selectinload(models.Project.owner),
        selectinload(models.Project.tasks),
    ).filter(models.Project.deleted_at.is_(None))
    if sede_id is not None:
        q = q.filter(models.Project.sede_id == sede_id)
    if status_filter:
        q = q.filter(models.Project.status == status_filter)
    return q.order_by(models.Project.updated_at.desc()).offset(skip).limit(limit).all()


def get_project(db: Session, project_id, sede_id=None, **_kwargs):
    """Fetch a project. ``sede_id`` is an optional multi-tenant filter used by
    ``tests/test_crud_integration.py::TestProjectsCrud.test_get_project``.

    Production callers continue to use the no-``sede_id`` form; the kwarg is
    swallowed here so neither side needs a separate function.
    """
    q = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.deleted_at.is_(None))
    )
    if sede_id is not None:
        q = q.filter(models.Project.sede_id == sede_id)
    return q.first()


def update_project(db: Session, project_id, payload=None, *, sede_id=None, **kwargs):
    """Update a project.

    Accepts either ``schemas.ProjectUpdate`` (production path) or kwarg-driven
    calls like ``update_project(db, pid, name='New Name', sede_id=...)`` from
    the integration tests. Kwargs are routed through a synthesized
    ``schemas.ProjectUpdate`` so Pydantic's type validation is preserved at the
    boundary; ``name`` is aliased to ``title`` (mirroring ``create_project``'s
    same idiom) so callers using the canonical ``name`` alias still write to
    the column. Unknown kwarg keys are silently filtered before synthesis.
    ``sede_id`` is always honored, even alongside a payload.
    """
    row = get_project(db, project_id)
    if not row:
        return None
    # Mirror ``create_project``'s name-over-title precedence. ``name`` wins
    # over ``title`` when both are passed; we still log a warning on conflict
    # so a future reader (or a frontend bug) gets a diagnostic instead of a
    # silent override. Equal values are not warned about to avoid noise for
    # the common case where a caller passes both fields identically.
    if "name" in kwargs:
        name_val = kwargs.pop("name")
        existing_title = kwargs.get("title")
        if existing_title is not None and existing_title != name_val:
            logging.getLogger(__name__).warning(
                "update_project: conflicting 'name'=%r and 'title'=%r on "
                "project_id=%r; using 'name' (mirrors create_project precedence).",
                name_val,
                existing_title,
                project_id,
            )
        kwargs["title"] = name_val
    if payload is None and kwargs:
        allowed_fields = set(schemas.ProjectUpdate.model_fields.keys())
        payload = schemas.ProjectUpdate(**{k: v for k, v in kwargs.items() if k in allowed_fields})
    if payload is not None:
        changes = (
            payload.model_dump(exclude_unset=True)
            if hasattr(payload, "model_dump")
            else dict(payload)
        )
        for key, value in changes.items():
            if value is not None:
                setattr(row, key, value)
    if sede_id is not None:
        row.sede_id = sede_id
    db.commit()
    db.refresh(row)
    return row


def delete_project(db: Session, project_id) -> bool:
    row = get_project(db, project_id)
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Project Tasks ───────────────────────────────────────

def create_project_task(db: Session, task: schemas.ProjectTaskCreate):
    db_task = models.ProjectTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_project_tasks(db: Session, project_id, status: Optional[str] = None):
    query = db.query(models.ProjectTask).filter(
        models.ProjectTask.project_id == project_id,
        models.ProjectTask.deleted_at.is_(None),
    )
    if status:
        query = query.filter(models.ProjectTask.status == status)
    return query.order_by(models.ProjectTask.order_index.asc()).all()


def get_project_task(db: Session, task_id):
    return (
        db.query(models.ProjectTask)
        .filter(models.ProjectTask.id == task_id, models.ProjectTask.deleted_at.is_(None))
        .first()
    )


def update_project_task(db: Session, task_id, payload: schemas.ProjectTaskUpdate):
    row = get_project_task(db, task_id)
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_project_task(db: Session, task_id) -> bool:
    row = get_project_task(db, task_id)
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Project Phases ───────────────────────────────────────

def get_project_phases(db: Session, project_id):
    return (
        db.query(models.ProjectPhase)
        .filter(models.ProjectPhase.project_id == project_id, models.ProjectPhase.deleted_at.is_(None))
        .order_by(models.ProjectPhase.order_index)
        .all()
    )


def set_project_phases(db: Session, project_id, phases: list[dict]) -> list[models.ProjectPhase]:
    db.query(models.ProjectPhase).filter(models.ProjectPhase.project_id == project_id).update({models.ProjectPhase.deleted_at: datetime.now(timezone.utc)}, synchronize_session=False)
    created = []
    for i, p in enumerate(phases):
        phase = models.ProjectPhase(
            project_id=project_id,
            name=p["name"],
            slug=p["slug"],
            color=p.get("color", "#94a3b8"),
            order_index=p.get("order_index", i),
        )
        db.add(phase)
        created.append(phase)
    db.commit()
    for p in created:
        db.refresh(p)
    return created


def create_default_phases(db: Session, project_id):
    defaults = [
        {"name": "Por Hacer",  "slug": "todo",        "color": "#94a3b8"},
        {"name": "En Curso",   "slug": "in_progress",  "color": "#3b82f6"},
        {"name": "Revisión",   "slug": "review",       "color": "#f59e0b"},
        {"name": "Completado", "slug": "completed",    "color": "#10b981"},
    ]
    return set_project_phases(db, project_id, defaults)


# ── Project Comments ───────────────────────────────────

def get_project_comments(db: Session, project_id=None, task_id=None):
    q = db.query(models.ProjectComment).filter(models.ProjectComment.deleted_at.is_(None))
    if project_id is not None:
        q = q.filter(models.ProjectComment.project_id == project_id)
    if task_id is not None:
        q = q.filter(models.ProjectComment.task_id == task_id)
    return q.order_by(models.ProjectComment.created_at.desc()).all()


def get_comment(db: Session, comment_id: UUID):
    return db.query(models.ProjectComment).filter(models.ProjectComment.id == comment_id).first()


def create_comment(db: Session, project_id, author_id, content: str, task_id=None):
    row = models.ProjectComment(
        project_id=project_id,
        author_id=author_id,
        content=content,
        task_id=task_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_comment(db: Session, comment_id: UUID, content: str) -> Optional[models.ProjectComment]:
    row = get_comment(db, comment_id)
    if not row:
        return None
    row.content = content
    db.commit()
    db.refresh(row)
    return row


def delete_comment(db: Session, comment_id: UUID) -> bool:
    row = get_comment(db, comment_id)
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Project Milestones ─────────────────────────────────

def get_project_milestones(db: Session, project_id):
    return (
        db.query(models.ProjectMilestone)
        .filter(models.ProjectMilestone.project_id == project_id, models.ProjectMilestone.deleted_at.is_(None))
        .order_by(models.ProjectMilestone.target_date.asc())
        .all()
    )


def get_milestone(db: Session, milestone_id):
    return db.query(models.ProjectMilestone).filter(models.ProjectMilestone.id == milestone_id).first()


def create_milestone(db: Session, project_id, title: str, description: str | None = None, target_date=None):
    row = models.ProjectMilestone(
        project_id=project_id,
        title=title,
        description=description,
        target_date=target_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_milestone(db: Session, milestone_id, payload: schemas.ProjectMilestoneUpdate) -> Optional[models.ProjectMilestone]:
    row = get_milestone(db, milestone_id)
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_milestone(db: Session, milestone_id) -> bool:
    row = get_milestone(db, milestone_id)
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Project Attachments ────────────────────────────────

def get_task_attachments(db: Session, task_id):
    return (
        db.query(models.ProjectAttachment)
        .filter(models.ProjectAttachment.task_id == task_id, models.ProjectAttachment.deleted_at.is_(None))
        .order_by(models.ProjectAttachment.created_at.desc())
        .all()
    )


def get_attachment(db: Session, attachment_id: UUID):
    return db.query(models.ProjectAttachment).filter(models.ProjectAttachment.id == attachment_id).first()


def create_attachment(db: Session, task_id, file_url: str, filename: str,
                      file_size: int = 0, file_type: str | None = None, uploader_id=None):
    row = models.ProjectAttachment(
        task_id=task_id,
        file_url=file_url,
        filename=filename,
        file_size=file_size,
        file_type=file_type,
        uploader_id=uploader_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_attachment(db: Session, attachment_id: UUID) -> bool:
    row = get_attachment(db, attachment_id)
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Project Whiteboard ─────────────────────────────────

def get_project_whiteboard(db: Session, project_id):
    return db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == project_id).first()


def update_project_whiteboard(db: Session, project_id, payload: schemas.ProjectWhiteboardUpdate) -> models.ProjectWhiteboard:
    row = get_project_whiteboard(db, project_id)
    if not row:
        row = models.ProjectWhiteboard(project_id=project_id, elements_json=payload.elements_json or "[]")
        db.add(row)
    else:
        if payload.elements_json is not None:
            row.elements_json = payload.elements_json
    db.commit()
    db.refresh(row)
    return row


# ── Project Wiki / Documents ───────────────────────────

def get_project_wiki(db: Session, project_id):
    return (
        db.query(models.ProjectDocument)
        .filter(models.ProjectDocument.project_id == project_id)
        .order_by(models.ProjectDocument.created_at.asc())
        .first()
    )


def update_project_wiki(db: Session, project_id, content: str, author_id=None) -> models.ProjectDocument:
    row = get_project_wiki(db, project_id)
    if not row:
        row = models.ProjectDocument(project_id=project_id, title="Wiki", content=content, author_id=author_id)
        db.add(row)
    else:
        row.content = content
        if author_id:
            row.author_id = author_id
    db.commit()
    db.refresh(row)
    return row


# ── Task Supplies ───────────────────────────────────────

def get_task_supplies(db: Session, task_id):
    return db.query(models.TaskSupply).filter(models.TaskSupply.task_id == task_id, models.TaskSupply.deleted_at.is_(None)).all()


def get_supply(db: Session, supply_id: UUID):
    return db.query(models.TaskSupply).filter(models.TaskSupply.id == supply_id).first()


def create_supply(db: Session, task_id, item_name: str, quantity: int = 1, status: str = "pending"):
    row = models.TaskSupply(task_id=task_id, item_name=item_name, quantity=quantity, status=status)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_supply(db: Session, supply_id: UUID, payload: schemas.TaskSupplyUpdate) -> Optional[models.TaskSupply]:
    row = get_supply(db, supply_id)
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_supply(db: Session, supply_id: UUID) -> bool:
    row = get_supply(db, supply_id)
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Project Activity Logs ──────────────────────────────

def get_project_activities(db: Session, project_id, limit: int = 100):
    return (
        db.query(models.ProjectActivityLog)
        .filter(models.ProjectActivityLog.project_id == project_id)
        .order_by(models.ProjectActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )


def get_all_activities(db: Session, limit: int = 50, sede_id=None):
    q = db.query(models.ProjectActivityLog)
    if sede_id is not None:
        q = q.join(models.Project, models.ProjectActivityLog.project_id == models.Project.id).filter(
            models.Project.sede_id == sede_id
        )
    return q.order_by(models.ProjectActivityLog.created_at.desc()).limit(limit).all()


def create_activity_log(db: Session, project_id, persona_id, action_type: str, description: str):
    row = models.ProjectActivityLog(
        project_id=project_id,
        persona_id=persona_id,
        action_type=action_type,
        description=description,
    )
    db.add(row)
    db.commit()
    return row


# ── Inbox State ───────────────────────────────────────

def get_inbox_state(db: Session, persona_id: UUID | str, item_id: str) -> Optional[models.ProjectInboxState]:
    return (
        db.query(models.ProjectInboxState)
        .filter(models.ProjectInboxState.persona_id == persona_id, models.ProjectInboxState.item_id == item_id)
        .first()
    )


def update_inbox_state(db: Session, persona_id: UUID | str, item_id: str, is_read: bool) -> models.ProjectInboxState:
    row = get_inbox_state(db, persona_id, item_id)
    if not row:
        row = models.ProjectInboxState(persona_id=persona_id, item_id=item_id, is_read=is_read)
        db.add(row)
    else:
        row.is_read = is_read
    db.commit()
    db.refresh(row)
    return row


# ── Portfolio & Workload ───────────────────────────────

def get_portfolio_summary(db: Session, sede_id=None):
    q = db.query(models.Project).options(
        selectinload(models.Project.owner),
        selectinload(models.Project.tasks),
    ).filter(models.Project.deleted_at.is_(None))
    if sede_id is not None:
        q = q.filter(models.Project.sede_id == sede_id)
    projects = q.all()
    summary = {}
    for p in projects:
        summary.setdefault(p.status, []).append(p)
    return summary


def get_workload_summary(db: Session, sede_id=None):
    from sqlalchemy import func
    q = (
        db.query(models.ProjectTask.assignee_id, func.count(models.ProjectTask.id).label("task_count"))
        .filter(models.ProjectTask.deleted_at.is_(None), models.ProjectTask.assignee_id.isnot(None))
        .group_by(models.ProjectTask.assignee_id)
    )
    return q.all()


# ── Test compatibility wrappers ───────────────────────────────────────
# These expose the names expected by ``tests/test_crud_integration.py``'s
# ``TestProjectsCrud`` without disturbing the production callers in
# ``backend/api/projects.py`` that import the longer ``get_projects`` /
# ``create_project_task`` variants. Production semantics are unchanged.

def list_projects(db: Session, **kwargs) -> list[models.Project]:
    return get_projects(db, **kwargs)


def create_task(db: Session, project_id, title=None, assignee_id=None, **kwargs) -> models.ProjectTask:
    """Test-compatible alias for ``create_project_task``.

    Used by ``tests/test_crud_integration.py::TestProjectsCrud.test_create_task``.
    """
    payload = schemas.ProjectTaskCreate(
        project_id=project_id,
        title=title or "",
        assignee_id=assignee_id,
        **kwargs,
    )
    return create_project_task(db, payload)


def list_tasks(db: Session, project_id, **kwargs) -> list[models.ProjectTask]:
    """Test-compatible alias for ``get_project_tasks``.
    Used by ``tests/test_crud_integration.py::TestProjectsCrud.test_list_tasks``.
    """
    return get_project_tasks(db, project_id, **kwargs)

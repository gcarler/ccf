"""Projects CRUD — corregido para cumplir los 3 axiomas del Kernel CCF."""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlsplit
from uuid import UUID
from xml.sax.saxutils import escape as escape_xml_text

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, load_only, selectinload

from backend import models, schemas
from backend.crud.crm import resolve_persona_id_for_user
from backend.models_shared import _utcnow
from backend.schemas.projects import TASK_TITLE_MAX_LENGTH

# ── Helper ──────────────────────────────────────────────


def get_user_persona_id(db: Session, user_id: UUID | str | None) -> Optional[UUID]:
    """Obtiene persona.id desde el identificador canónico del usuario."""
    persona_id = resolve_persona_id_for_user(db, user_id)
    return UUID(str(persona_id)) if persona_id else None


def _to_uuid(val: Any) -> Optional[UUID]:
    """Convierte de forma segura un valor a UUID o devuelve None."""
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return None


def _safe_csv_text(value: Any) -> str:
    """Keep user-controlled CSV text from being evaluated as a spreadsheet formula."""
    text = "" if value is None else str(value)
    first_content = next((char for char in text if char not in " \t\r\n\v\f"), "")
    if first_content in {"=", "+", "-", "@"}:
        return f"'{text}"
    return text


# ── Projects ────────────────────────────────────────────


def create_project(
    db: Session,
    project: schemas.ProjectCreate,
    *,
    owner_persona_id: UUID | str,
    sede_id: UUID | str,
    commit: bool = True,
):
    """Crea un proyecto mediante el contrato Pydantic canónico.

    Axioma 3 — la sede es obligatoria. ``sede_id=None`` se rechaza con
    ``ValueError`` para que la ruta no pueda crear accidentalmente un
    proyecto "huérfano" que luego escaparía al scope multi-tenant
    (``tests/test_projects_multi_tenant.py::TestMultiTenantCRUDDefenseInDepth``).

    El superadmin histórico no envía ``sede_id``; en ese caso la capa de
    ruta debe pasar la sede activa del actor (o cortar antes de llegar
    aquí). Esta función NO cae al modo "global" — protege la base como
    defense-in-depth.
    """
    if sede_id is None:
        raise ValueError("sede_id is required (Axioma 3): cannot create a tenant-less project")
    data = project.model_dump()
    data.pop("owner_id", None)
    row = models.Project(**data)
    row.owner_id = owner_persona_id
    row.sede_id = sede_id
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def get_projects(db: Session, skip: int = 0, limit: int = 100, sede_id=None, status_filter=None):
    q = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.owner),
            selectinload(models.Project.tasks),
        )
        .filter(models.Project.deleted_at.is_(None))
    )
    if sede_id is not None:
        q = q.filter(models.Project.sede_id == sede_id)
    if status_filter:
        q = q.filter(models.Project.status == status_filter)
    return q.order_by(models.Project.updated_at.desc()).offset(skip).limit(limit).all()


def get_projects_page(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    sede_id=None,
    status_filter: Optional[str] = None,
    owner_id=None,
    search: Optional[str] = None,
):
    """Return one bounded, filtered project page and its matching total."""
    query = db.query(models.Project).filter(models.Project.deleted_at.is_(None))
    if sede_id is not None:
        query = query.filter(models.Project.sede_id == sede_id)
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    if owner_id is not None:
        query = query.filter(models.Project.owner_id == owner_id)
    normalized_search = search.strip() if isinstance(search, str) else ""
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.filter(
            models.Project.title.ilike(pattern) | models.Project.description.ilike(pattern)
        )

    total = query.count()
    projects = (
        query.options(
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.attachments),
            selectinload(models.Project.milestones),
        )
        .order_by(models.Project.created_at.desc(), models.Project.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return projects, total


def get_project_summaries_page(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    sede_id=None,
    status_filter: Optional[str] = None,
    owner_id=None,
    search: Optional[str] = None,
):
    """Return a bounded project page with aggregate metrics, not child graphs."""
    query = db.query(models.Project).filter(models.Project.deleted_at.is_(None))
    if sede_id is not None:
        query = query.filter(models.Project.sede_id == sede_id)
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    if owner_id is not None:
        query = query.filter(models.Project.owner_id == owner_id)
    normalized_search = search.strip() if isinstance(search, str) else ""
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.filter(
            models.Project.title.ilike(pattern) | models.Project.description.ilike(pattern)
        )

    total = query.count()
    projects = (
        query.options(load_only(
            models.Project.id,
            models.Project.title,
            models.Project.description,
            models.Project.status,
            models.Project.owner_id,
            models.Project.color,
            models.Project.icon,
            models.Project.start_date,
            models.Project.target_date,
            models.Project.progress_mode,
            models.Project.manual_progress,
            models.Project.budget_allocated,
            models.Project.budget_spent,
            models.Project.health_override,
            models.Project.created_at,
            models.Project.updated_at,
        ))
        .order_by(models.Project.created_at.desc(), models.Project.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    project_ids = [project.id for project in projects]
    task_stats = {}
    milestone_stats = {}
    if project_ids:
        now = datetime.now(timezone.utc)
        task_rows = (
            db.query(
                models.ProjectTask.project_id,
                func.count(models.ProjectTask.id),
                func.sum(case((models.ProjectTask.status == "completed", 1), else_=0)),
                func.sum(case((models.ProjectTask.status == "in_progress", 1), else_=0)),
                func.sum(case((and_(
                    models.ProjectTask.status != "completed",
                    models.ProjectTask.due_date.is_not(None),
                    models.ProjectTask.due_date < now,
                ), 1), else_=0)),
            )
            .filter(
                models.ProjectTask.project_id.in_(project_ids),
                models.ProjectTask.deleted_at.is_(None),
            )
            .group_by(models.ProjectTask.project_id)
            .all()
        )
        task_stats = {
            project_id: {
                "task_count": int(task_count or 0),
                "completed_task_count": int(completed_count or 0),
                "in_progress_task_count": int(in_progress_count or 0),
                "overdue_task_count": int(overdue_count or 0),
            }
            for project_id, task_count, completed_count, in_progress_count, overdue_count in task_rows
        }
        milestone_rows = (
            db.query(
                models.ProjectMilestone.project_id,
                func.count(models.ProjectMilestone.id),
                func.sum(case((models.ProjectMilestone.is_completed.is_(True), 1), else_=0)),
            )
            .filter(
                models.ProjectMilestone.project_id.in_(project_ids),
                models.ProjectMilestone.deleted_at.is_(None),
            )
            .group_by(models.ProjectMilestone.project_id)
            .all()
        )
        milestone_stats = {
            project_id: {
                "milestone_count": int(milestone_count or 0),
                "completed_milestone_count": int(completed_count or 0),
            }
            for project_id, milestone_count, completed_count in milestone_rows
        }

    return [
        {
            "project": project,
            **task_stats.get(project.id, {
                "task_count": 0,
                "completed_task_count": 0,
                "in_progress_task_count": 0,
                "overdue_task_count": 0,
            }),
            **milestone_stats.get(project.id, {
                "milestone_count": 0,
                "completed_milestone_count": 0,
            }),
        }
        for project in projects
    ], total


def get_assigned_project_tasks_page(
    db: Session,
    *,
    persona_id: UUID | str,
    sede_id: UUID | str | None,
    offset: int = 0,
    limit: int = 50,
):
    """Return one bounded page of active tasks assigned to a person in scope."""
    query = (
        db.query(models.ProjectTask)
        .join(models.Project, models.Project.id == models.ProjectTask.project_id)
        .filter(
            models.ProjectTask.assignee_id == _to_uuid(persona_id),
            models.ProjectTask.deleted_at.is_(None),
            models.Project.deleted_at.is_(None),
        )
    )
    if sede_id is not None:
        query = query.filter(models.Project.sede_id == _to_uuid(sede_id))

    total = query.count()
    rows = (
        query.options(
            selectinload(models.ProjectTask.project),
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.attachments),
            selectinload(models.ProjectTask.subtasks),
        )
        .order_by(models.ProjectTask.created_at.desc(), models.ProjectTask.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def get_project(db: Session, project_id, sede_id=None):
    """Obtiene un proyecto y aplica el scope de sede cuando se proporciona."""
    q = db.query(models.Project).filter(models.Project.id == project_id, models.Project.deleted_at.is_(None))
    if sede_id is not None:
        q = q.filter(models.Project.sede_id == sede_id)
    return q.first()


def update_project(
    db: Session,
    project_id,
    payload: schemas.ProjectUpdate,
    *,
    sede_id: UUID | str | None = None,
):
    """Actualiza un proyecto dentro de una sede explícitamente indicada.

    ``sede_id`` es obligatorio en la capa CRUD para que un caller directo no
    pueda mutar un proyecto de otra sede por omisión del scope. La API debe
    resolver la sede efectiva del actor antes de llamar a esta función.
    """
    if sede_id is None:
        raise ValueError("sede_id is required (Axioma 3): cannot update without tenant scope")
    # Apply the tenant scope while locating the row—not only when assigning
    # the new sede—so a direct CRUD caller cannot update another tenant.
    row = get_project(db, project_id, sede_id=sede_id)
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(row, key, value)
    row.sede_id = sede_id
    db.commit()
    db.refresh(row)
    return row


def delete_project(db: Session, project_id, *, sede_id: UUID | str | None = None) -> bool:
    """Soft-delete a project only when it belongs to the supplied sede."""
    if sede_id is None:
        raise ValueError("sede_id is required (Axioma 3): cannot delete without tenant scope")
    row = get_project(db, project_id, sede_id=sede_id)
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


class TaskDateOutOfBoundsError(ValueError):
    """Raised when a task's dates exceed its phase bounds."""
    pass


def validate_task_dates_within_phase(
    db: Session,
    project_id: UUID | str,
    *,
    status_slug: Optional[str] = None,
    node: Optional[str] = None,
    start_date: Optional[datetime] = None,
    due_date: Optional[datetime] = None,
    task_id: Optional[UUID | str] = None,
) -> None:
    """Valida que las fechas de una tarea no violen los límites estrictos de la fase asignada."""
    s_dt = start_date
    if s_dt is not None:
        if isinstance(s_dt, str):
            try:
                s_dt = datetime.fromisoformat(s_dt.replace("Z", "+00:00"))
            except Exception:
                s_dt = None
        if s_dt and getattr(s_dt, "tzinfo", None) is None:
            s_dt = s_dt.replace(tzinfo=timezone.utc)

    d_dt = due_date
    if d_dt is not None:
        if isinstance(d_dt, str):
            try:
                d_dt = datetime.fromisoformat(d_dt.replace("Z", "+00:00"))
            except Exception:
                d_dt = None
        if d_dt and getattr(d_dt, "tzinfo", None) is None:
            d_dt = d_dt.replace(tzinfo=timezone.utc)

    if s_dt and d_dt and s_dt > d_dt:
        raise TaskDateOutOfBoundsError(
            f"La fecha de inicio ({s_dt.isoformat()}) no puede ser posterior a la fecha límite ({d_dt.isoformat()})"
        )

    project_uuid = _to_uuid(project_id)
    phases = (
        db.query(models.ProjectPhase)
        .filter(models.ProjectPhase.project_id == project_uuid, models.ProjectPhase.deleted_at.is_(None))
        .all()
    )
    if not phases:
        return

    matching_phase = None
    if node:
        node_str = str(node).strip()
        for p in phases:
            if str(p.id) == node_str or p.slug == node_str or p.name == node_str:
                matching_phase = p
                break
    if not matching_phase and status_slug:
        slug_str = str(status_slug).strip()
        for p in phases:
            if p.slug == slug_str:
                matching_phase = p
                break

    if not matching_phase:
        return

    p_start = getattr(matching_phase, "start_date", None)
    if p_start and getattr(p_start, "tzinfo", None) is None:
        p_start = p_start.replace(tzinfo=timezone.utc)

    p_end = getattr(matching_phase, "end_date", None)
    if p_end and getattr(p_end, "tzinfo", None) is None:
        p_end = p_end.replace(tzinfo=timezone.utc)

    if p_start:
        if s_dt and s_dt < p_start:
            raise TaskDateOutOfBoundsError(
                f"La fecha de inicio de la tarea ({s_dt.date()}) no puede ser anterior al inicio de la fase '{matching_phase.name}' ({p_start.date()})"
            )
        if d_dt and d_dt < p_start:
            raise TaskDateOutOfBoundsError(
                f"La fecha límite de la tarea ({d_dt.date()}) no puede ser anterior al inicio de la fase '{matching_phase.name}' ({p_start.date()})"
            )

    if p_end:
        if s_dt and s_dt > p_end:
            raise TaskDateOutOfBoundsError(
                f"La fecha de inicio de la tarea ({s_dt.date()}) no puede ser posterior al fin de la fase '{matching_phase.name}' ({p_end.date()})"
            )
        if d_dt and d_dt > p_end:
            raise TaskDateOutOfBoundsError(
                f"La fecha límite de la tarea ({d_dt.date()}) no puede ser posterior al fin de la fase '{matching_phase.name}' ({p_end.date()})"
            )


def create_project_task(db: Session, task: schemas.ProjectTaskCreate):
    task_data = task.model_dump()
    project_id = _to_uuid(task_data.get("project_id"))
    if project_id is None:
        raise ValueError("project_id is required to create a project task")
    parent_id = _to_uuid(task_data.get("parent_id"))
    if parent_id is not None:
        parent = (
            db.query(models.ProjectTask.id)
            .filter(
                models.ProjectTask.id == parent_id,
                models.ProjectTask.project_id == project_id,
                models.ProjectTask.deleted_at.is_(None),
            )
            .first()
        )
        if not parent:
            raise ValueError("parent_id must reference an active task in the same project")

    validate_task_dates_within_phase(
        db,
        project_id,
        status_slug=task_data.get("status"),
        node=task_data.get("node"),
        start_date=task_data.get("start_date"),
        due_date=task_data.get("due_date"),
    )

    task_data["project_id"] = project_id
    task_data["parent_id"] = parent_id
    db_task = models.ProjectTask(**task_data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    if parent_id is not None:
        try:
            from backend.services.project_evm_service import sync_parent_task_rollup
            sync_parent_task_rollup(db, parent_id)
        except Exception:
            pass
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


def trigger_project_automations_safe(
    db: Session,
    project_id: Any,
    trigger_event: str,
    context: Optional[dict] = None,
    *,
    actor_persona_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
) -> list[dict]:
    """Dispara de forma segura las reglas de automatización activas del proyecto."""
    if not project_id or not trigger_event:
        return []
    try:
        effective_sede = user_sede_id
        if effective_sede is None:
            proj = get_project(db, project_id)
            if proj and getattr(proj, "sede_id", None):
                effective_sede = proj.sede_id
        return evaluate_project_automations(
            db,
            project_id,
            trigger_event,
            context or {},
            actor_persona_id=actor_persona_id,
            user_sede_id=effective_sede,
            dry_run=False,
        )
    except Exception:
        return []


def evaluate_task_mutation_automations(
    db: Session,
    task: models.ProjectTask,
    *,
    prev_status: Optional[str] = None,
    prev_progress_pct: float = 0.0,
    requested_status: Optional[str] = None,
    actor_persona_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
) -> None:
    """Evalúa y dispara automatizaciones tras mutar estado o avance de una tarea/subtarea."""
    if not task or not getattr(task, "project_id", None):
        return
    curr_status = getattr(task, "status", None)
    curr_pct = float(getattr(task, "physical_progress_pct", 0.0) or 0.0)
    ctx = {
        "task_id": str(task.id),
        "task_title": getattr(task, "title", ""),
        "status": curr_status,
        "priority": getattr(task, "priority", "medium"),
        "node": getattr(task, "node", None),
        "assignee_id": str(task.assignee_id) if getattr(task, "assignee_id", None) else None,
    }
    was_completed = prev_status in ("completed", "done") or prev_progress_pct >= 100.0
    is_now_completed = curr_status in ("completed", "done") or curr_pct >= 100.0
    if is_now_completed and not was_completed:
        trigger_project_automations_safe(
            db,
            task.project_id,
            "task_completed",
            ctx,
            actor_persona_id=actor_persona_id,
            user_sede_id=user_sede_id,
        )
    elif (requested_status == "blocked" or curr_status == "blocked") and prev_status != "blocked":
        trigger_project_automations_safe(
            db,
            task.project_id,
            "task_blocked",
            ctx,
            actor_persona_id=actor_persona_id,
            user_sede_id=user_sede_id,
        )


def update_project_task(db: Session, task_id, payload: schemas.ProjectTaskUpdate):
    row = get_project_task(db, task_id)
    if not row:
        return None
    prev_status = row.status
    prev_progress = float(getattr(row, "physical_progress_pct", 0.0) or 0.0)
    update_data = payload.model_dump(exclude_unset=True)

    effective_status = update_data.get("status", row.status)
    effective_node = update_data.get("node", row.node)
    effective_start = update_data.get("start_date", row.start_date)
    effective_due = update_data.get("due_date", row.due_date)

    validate_task_dates_within_phase(
        db,
        row.project_id,
        status_slug=effective_status,
        node=effective_node,
        start_date=effective_start,
        due_date=effective_due,
        task_id=row.id,
    )

    for key, value in update_data.items():
        setattr(row, key, value)
    if row.status in ("completed", "done") and float(getattr(row, "physical_progress_pct", 0.0) or 0.0) < 100.0:
        row.physical_progress_pct = 100.0
    db.commit()
    db.refresh(row)
    if row.parent_id:
        try:
            from backend.services.project_evm_service import sync_parent_task_rollup
            sync_parent_task_rollup(db, row.parent_id)
        except Exception:
            pass
    evaluate_task_mutation_automations(
        db,
        row,
        prev_status=prev_status,
        prev_progress_pct=prev_progress,
        requested_status=update_data.get("status"),
    )
    return row


def delete_project_task(db: Session, task_id) -> bool:
    row = get_project_task(db, task_id)
    if not row:
        return False
    parent_id = row.parent_id
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    if parent_id:
        try:
            from backend.services.project_evm_service import sync_parent_task_rollup
            sync_parent_task_rollup(db, parent_id)
        except Exception:
            pass
    return True


# ── Project Phases ───────────────────────────────────────


def get_project_phases(db: Session, project_id):
    return (
        db.query(models.ProjectPhase)
        .filter(models.ProjectPhase.project_id == project_id, models.ProjectPhase.deleted_at.is_(None))
        .order_by(models.ProjectPhase.order_index)
        .all()
    )


def set_project_phases(
    db: Session,
    project_id,
    phases: list[dict],
    *,
    commit: bool = True,
) -> list[models.ProjectPhase]:
    db.query(models.ProjectPhase).filter(models.ProjectPhase.project_id == project_id).update(
        {models.ProjectPhase.deleted_at: datetime.now(timezone.utc)}, synchronize_session=False
    )
    created = []
    for i, p in enumerate(phases):
        phase = models.ProjectPhase(
            project_id=project_id,
            name=p["name"],
            slug=p["slug"],
            color=p.get("color", "#94a3b8"),
            order_index=p.get("order_index", i),
            start_date=p.get("start_date"),
            end_date=p.get("end_date"),
        )
        db.add(phase)
        created.append(phase)
    if commit:
        db.commit()
        for phase in created:
            db.refresh(phase)
    else:
        db.flush()
    return created


def create_default_phases(db: Session, project_id, *, commit: bool = True):
    defaults = [
        {"name": "Por Hacer", "slug": "todo", "color": "#94a3b8"},
        {"name": "En Curso", "slug": "in_progress", "color": "#3b82f6"},
        {"name": "Revisión", "slug": "review", "color": "#f59e0b"},
        {"name": "Completado", "slug": "completed", "color": "#10b981"},
    ]
    return set_project_phases(db, project_id, defaults, commit=commit)


# ── Project Comments ───────────────────────────────────


def get_project_comments(db: Session, project_id=None, task_id=None, sede_id=None):
    if sede_id is not None and project_id is not None:
        project = get_project(db, project_id, sede_id=sede_id)
        if not project:
            raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")
    q = db.query(models.ProjectComment).filter(models.ProjectComment.deleted_at.is_(None))
    if project_id is not None:
        q = q.filter(models.ProjectComment.project_id == project_id)
    if task_id is not None:
        q = q.filter(models.ProjectComment.task_id == task_id)
    return q.order_by(models.ProjectComment.is_pinned.desc(), models.ProjectComment.created_at.desc()).all()


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


def create_milestone(
    db: Session, project_id, title: str, description: str | None = None, target_date=None, is_completed: bool = False
):
    row = models.ProjectMilestone(
        project_id=project_id,
        title=title,
        description=description,
        target_date=target_date,
        is_completed=is_completed,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if row.is_completed:
        trigger_project_automations_safe(
            db,
            row.project_id,
            "milestone_completed",
            {"milestone_id": str(row.id), "milestone_title": row.title},
        )
    return row


def update_milestone(
    db: Session, milestone_id, payload: schemas.ProjectMilestoneUpdate
) -> Optional[models.ProjectMilestone]:
    row = get_milestone(db, milestone_id)
    if not row:
        return None
    was_completed = bool(row.is_completed)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    if row.is_completed and not was_completed:
        trigger_project_automations_safe(
            db,
            row.project_id,
            "milestone_completed",
            {"milestone_id": str(row.id), "milestone_title": row.title},
        )
    return row


def delete_milestone(db: Session, milestone_id) -> bool:
    row = get_milestone(db, milestone_id)
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Project Components (EDT Level 2) ──────────────────


def get_project_components(db: Session, project_id: Any) -> list[models.ProjectComponent]:
    p_uuid = _to_uuid(project_id)
    return (
        db.query(models.ProjectComponent)
        .filter(
            models.ProjectComponent.project_id == p_uuid,
            models.ProjectComponent.deleted_at.is_(None),
        )
        .order_by(models.ProjectComponent.order_index.asc(), models.ProjectComponent.code.asc())
        .all()
    )


def get_project_component(db: Session, project_id: Any, component_id: Any) -> Optional[models.ProjectComponent]:
    p_uuid = _to_uuid(project_id)
    c_uuid = _to_uuid(component_id)
    return (
        db.query(models.ProjectComponent)
        .filter(
            models.ProjectComponent.id == c_uuid,
            models.ProjectComponent.project_id == p_uuid,
            models.ProjectComponent.deleted_at.is_(None),
        )
        .first()
    )


def create_project_component(
    db: Session,
    project_id: Any,
    payload: schemas.ProjectComponentCreate,
) -> models.ProjectComponent:
    p_uuid = _to_uuid(project_id)
    data = payload.model_dump(exclude_unset=True)
    data["project_id"] = p_uuid
    row = models.ProjectComponent(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_project_component(
    db: Session,
    project_id: Any,
    component_id: Any,
    payload: schemas.ProjectComponentUpdate,
) -> Optional[models.ProjectComponent]:
    row = get_project_component(db, project_id, component_id)
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_project_component(db: Session, project_id: Any, component_id: Any) -> bool:
    row = get_project_component(db, project_id, component_id)
    if not row:
        return False
    row.deleted_at = _utcnow()
    # Desvincular de tareas y gastos asociados
    db.query(models.ProjectTask).filter(
        models.ProjectTask.component_id == row.id,
        models.ProjectTask.deleted_at.is_(None),
    ).update({"component_id": None}, synchronize_session=False)
    db.query(models.ProjectExpense).filter(
        models.ProjectExpense.component_id == row.id,
        models.ProjectExpense.deleted_at.is_(None),
    ).update({"component_id": None}, synchronize_session=False)
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


def create_attachment(
    db: Session,
    task_id,
    file_url: str,
    filename: str,
    file_size: int = 0,
    file_type: str | None = None,
    uploader_id=None,
):
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
    return (
        db.query(models.ProjectWhiteboard)
        .filter(
            models.ProjectWhiteboard.project_id == project_id,
            models.ProjectWhiteboard.deleted_at.is_(None),
        )
        .first()
    )


def update_project_whiteboard(
    db: Session, project_id, payload: schemas.ProjectWhiteboardUpdate
) -> models.ProjectWhiteboard:
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


def sync_supply_expense(
    db: Session,
    supply: models.TaskSupply,
    *,
    created_by: Optional[UUID | str] = None,
) -> Optional[models.ProjectExpense]:
    """Sincroniza automáticamente un suministro con costo hacia ProjectExpense (AC de tarea/componente/proyecto)."""
    if not supply or not getattr(supply, "task_id", None):
        return None
    task = (
        db.query(models.ProjectTask)
        .filter(models.ProjectTask.id == _to_uuid(supply.task_id))
        .first()
    )
    if not task or not getattr(task, "project_id", None):
        return None

    tag = f"[supply_id:{supply.id}]"
    linked = (
        db.query(models.ProjectExpense)
        .filter(
            models.ProjectExpense.project_id == task.project_id,
            models.ProjectExpense.description.ilike(f"%{tag}%"),
        )
        .order_by(models.ProjectExpense.created_at.desc())
        .first()
    )

    if supply.deleted_at is not None or supply.status == "unavailable":
        if linked and linked.deleted_at is None:
            linked.deleted_at = datetime.now(timezone.utc)
            db.commit()
            recalculate_project_budget(db, task.project_id)
        return None

    qty = max(1, int(getattr(supply, "quantity", 1) or 1))
    unit_cost = float(getattr(supply, "unit_cost", 0.0) or 0.0)
    total_cost = float(getattr(supply, "total_cost", 0.0) or 0.0)
    if total_cost <= 0.0 and unit_cost > 0.0:
        total_cost = round(unit_cost * qty, 2)
    elif unit_cost <= 0.0 and total_cost > 0.0:
        unit_cost = round(total_cost / qty, 2)

    supply.unit_cost = round(unit_cost, 2)
    supply.total_cost = round(total_cost, 2)

    if total_cost <= 0.0:
        if linked and linked.deleted_at is None:
            linked.deleted_at = datetime.now(timezone.utc)
            db.commit()
            recalculate_project_budget(db, task.project_id)
        return None

    paid_statuses = {"ready", "received", "approved", "purchased", "paid"}
    exp_status = "paid" if str(supply.status or "").lower() in paid_statuses else "planned"
    desc_text = f"{tag} Suministro: {supply.item_name} (x{qty}) [unit_cost={round(unit_cost, 2)}]"

    prev_exp_status = linked.status if linked and linked.deleted_at is None else None
    if linked:
        linked.component_id = task.component_id
        linked.task_id = task.id
        linked.category = "supplies"
        linked.description = desc_text
        linked.amount = round(total_cost, 2)
        linked.status = exp_status
        linked.deleted_at = None
        linked.updated_at = datetime.now(timezone.utc)
    else:
        linked = models.ProjectExpense(
            project_id=task.project_id,
            component_id=task.component_id,
            task_id=task.id,
            category="supplies",
            description=desc_text,
            amount=round(total_cost, 2),
            date=datetime.now(timezone.utc),
            status=exp_status,
            created_by=_to_uuid(created_by) if created_by else None,
            is_auto_generated=True,
        )
        db.add(linked)

    # El gasto de origen quedó marcado como auto-generado desde suministros.
    linked.is_auto_generated = True
    db.commit()
    db.refresh(linked)
    supply.expense_id = str(linked.id)
    recalculate_project_budget(db, task.project_id)

    if exp_status in ("approved", "paid") and prev_exp_status not in ("approved", "paid"):
        trigger_project_automations_safe(
            db,
            task.project_id,
            "expense_approved",
            {
                "expense_id": str(linked.id),
                "amount": float(linked.amount or 0.0),
                "category": linked.category,
                "task_id": str(task.id),
                "supply_id": str(supply.id),
            },
            actor_persona_id=created_by,
        )
    return linked


def get_task_supplies(db: Session, task_id):
    return (
        db.query(models.TaskSupply)
        .filter(models.TaskSupply.task_id == task_id, models.TaskSupply.deleted_at.is_(None))
        .order_by(models.TaskSupply.id.asc())
        .all()
    )


def get_supply(db: Session, supply_id: UUID):
    return db.query(models.TaskSupply).filter(models.TaskSupply.id == supply_id).first()


def create_supply(
    db: Session,
    task_id,
    item_name: str,
    quantity: int = 1,
    status: str = "pending",
    *,
    unit_cost: float = 0.0,
    total_cost: Optional[float] = None,
    created_by: Optional[UUID | str] = None,
):
    row = models.TaskSupply(
        task_id=task_id,
        item_name=item_name,
        quantity=quantity,
        status=status,
        unit_cost=unit_cost,
        total_cost=total_cost,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    sync_supply_expense(db, row, created_by=created_by)
    return row


def update_supply(
    db: Session,
    supply_id: UUID,
    payload: schemas.TaskSupplyUpdate,
    *,
    created_by: Optional[UUID | str] = None,
) -> Optional[models.TaskSupply]:
    row = get_supply(db, supply_id)
    if not row:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    if "unit_cost" in update_data and "total_cost" not in update_data:
        eff_qty = max(1, int(update_data.get("quantity", row.quantity) or 1))
        update_data["total_cost"] = round(float(update_data["unit_cost"] or 0.0) * eff_qty, 2)
    elif "quantity" in update_data and "total_cost" not in update_data and float(getattr(row, "unit_cost", 0.0) or 0.0) > 0:
        eff_qty = max(1, int(update_data["quantity"] or 1))
        update_data["total_cost"] = round(float(row.unit_cost) * eff_qty, 2)
    for key, value in update_data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    sync_supply_expense(db, row, created_by=created_by)
    return row


def delete_supply(db: Session, supply_id: UUID) -> bool:
    row = get_supply(db, supply_id)
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    sync_supply_expense(db, row)
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
    q = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.owner),
            selectinload(models.Project.tasks),
        )
        .filter(models.Project.deleted_at.is_(None))
    )
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


# ── KPIs ──────────────────────────────────────────────


def _prepare_kpi_response(
    db: Session,
    row: models.ProjectKPI,
    project: Optional[models.Project] = None,
    matrix: Optional[dict] = None,
) -> models.ProjectKPI:
    if not row:
        return row
    from backend.models_projects import decode_kpi_meta
    from backend.services.project_evm_service import evaluate_execution_metric

    _, meta = decode_kpi_meta(getattr(row, "description", None))
    src = str(meta.get("source_type") or getattr(row, "source_type", "manual") or "manual").strip()
    comp_id = meta.get("component_id") or getattr(row, "component_id", None)
    row.source_type = src
    row.component_id = str(comp_id) if comp_id else None

    if src != "manual":
        proj = project or get_project(db, row.project_id)
        if proj:
            eval_res = evaluate_execution_metric(
                db,
                proj,
                src,
                component_id=row.component_id,
                target_value=row.target_value,
                matrix=matrix,
            )
            if eval_res.get("current_value") is not None:
                row.current_value = float(eval_res["current_value"])
            row.__dict__["last_spi"] = eval_res.get("spi")
            row.__dict__["frente"] = eval_res.get("frente")
            row.__dict__["component_name"] = eval_res.get("component_name")
            row.__dict__["is_auto_synced"] = True
            return row

    target = float(row.target_value or 0.0)
    curr = float(row.current_value or 0.0)
    row.__dict__["last_spi"] = round(curr / target, 4) if target > 0 else None
    row.__dict__["frente"] = "manual"
    row.__dict__["component_name"] = None
    row.__dict__["is_auto_synced"] = False
    return row


def get_project_kpis(db: Session, project_id: UUID | str) -> list[models.ProjectKPI]:
    rows = (
        db.query(models.ProjectKPI)
        .filter(models.ProjectKPI.project_id == project_id, models.ProjectKPI.deleted_at.is_(None))
        .order_by(models.ProjectKPI.created_at.asc())
        .all()
    )
    if not rows:
        return []
    project = get_project(db, project_id)
    matrix = None
    if project and any(getattr(r, "source_type", "manual") != "manual" for r in rows):
        from backend.services.project_evm_service import build_project_execution_matrix
        matrix = build_project_execution_matrix(db, project)
    return [_prepare_kpi_response(db, r, project=project, matrix=matrix) for r in rows]


def get_project_kpi(db: Session, project_id: UUID | str, kpi_id: UUID | str) -> Optional[models.ProjectKPI]:
    row = (
        db.query(models.ProjectKPI)
        .filter(
            models.ProjectKPI.id == kpi_id,
            models.ProjectKPI.project_id == project_id,
            models.ProjectKPI.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    return _prepare_kpi_response(db, row)


def create_project_kpi(
    db: Session, project_id: UUID | str, kpi_in: schemas.ProjectKPICreate
) -> models.ProjectKPI:
    from backend.models_projects import encode_kpi_meta
    from backend.services.project_evm_service import evaluate_execution_metric

    data = kpi_in.model_dump()
    src = str(data.pop("source_type", "manual") or "manual").strip()
    comp_id = data.pop("component_id", None)
    data["description"] = encode_kpi_meta(data.get("description"), src, comp_id)

    project = get_project(db, project_id)
    if src != "manual" and project:
        eval_res = evaluate_execution_metric(
            db, project, src, component_id=comp_id, target_value=data.get("target_value")
        )
        if eval_res.get("current_value") is not None:
            data["current_value"] = float(eval_res["current_value"])

    row = models.ProjectKPI(project_id=project_id, **data)
    row.source_type = src
    row.component_id = str(comp_id) if comp_id else None
    db.add(row)
    db.commit()
    db.refresh(row)
    return _prepare_kpi_response(db, row, project=project)


def update_project_kpi(
    db: Session, project_id: UUID | str, kpi_id: UUID | str, kpi_in: schemas.ProjectKPIUpdate
) -> Optional[models.ProjectKPI]:
    from backend.models_projects import decode_kpi_meta, encode_kpi_meta
    from backend.services.project_evm_service import evaluate_execution_metric

    row = (
        db.query(models.ProjectKPI)
        .filter(
            models.ProjectKPI.id == kpi_id,
            models.ProjectKPI.project_id == project_id,
            models.ProjectKPI.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None

    clean_desc, existing_meta = decode_kpi_meta(row.description)
    update_data = kpi_in.model_dump(exclude_unset=True)
    src = str(update_data.pop("source_type", existing_meta.get("source_type") or "manual") or "manual").strip()
    if "component_id" in update_data:
        comp_id = update_data.pop("component_id")
    else:
        comp_id = existing_meta.get("component_id")

    new_desc = update_data.pop("description", clean_desc)
    row.description = encode_kpi_meta(new_desc, src, comp_id)

    for k, v in update_data.items():
        if v is not None:
            setattr(row, k, v)

    project = get_project(db, project_id)
    if src != "manual" and project:
        eval_res = evaluate_execution_metric(
            db, project, src, component_id=comp_id, target_value=row.target_value
        )
        if eval_res.get("current_value") is not None:
            row.current_value = float(eval_res["current_value"])

    row.source_type = src
    row.component_id = str(comp_id) if comp_id else None
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _prepare_kpi_response(db, row, project=project)


def delete_project_kpi(db: Session, project_id: UUID | str, kpi_id: UUID | str) -> bool:
    row = (
        db.query(models.ProjectKPI)
        .filter(
            models.ProjectKPI.id == kpi_id,
            models.ProjectKPI.project_id == project_id,
            models.ProjectKPI.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True



# ── Dependencies (Gantt) ──────────────────────────────


class CircularDependencyError(ValueError):
    """Raised when adding a task dependency would create a circular reference."""
    pass


def detect_cycle_in_dependencies(
    edges: list[tuple[Any, Any]],
    new_edge: Optional[tuple[Any, Any]] = None,
) -> tuple[bool, list[str]]:
    """Detects if there is a cycle in a directed graph of task dependencies using DFS.

    Edges are directed (predecessor -> successor).
    Returns (has_cycle, cycle_path_as_strings).
    """
    from collections import defaultdict

    adj: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()

    all_edges = list(edges)
    if new_edge is not None:
        all_edges.append(new_edge)

    for p, s in all_edges:
        p_str = str(p)
        s_str = str(s)
        adj[p_str].append(s_str)
        nodes.add(p_str)
        nodes.add(s_str)

    color: dict[str, int] = {node: 0 for node in nodes}
    parent: dict[str, Optional[str]] = {node: None for node in nodes}
    cycle_path: list[str] = []

    def dfs(u: str) -> bool:
        color[u] = 1  # GRAY (visiting / in recursion stack)
        for v in adj.get(u, []):
            if v == u:
                cycle_path.extend([u, v])
                return True
            if color.get(v, 0) == 1:
                # Cycle found! Reconstruct cycle path from u back to v
                curr = u
                path = [v, curr]
                while curr != v and curr is not None:
                    curr = parent.get(curr)
                    if curr:
                        path.append(curr)
                path.reverse()
                cycle_path.extend(path)
                return True
            elif color.get(v, 0) == 0:
                parent[v] = u
                if dfs(v):
                    return True
        color[u] = 2  # BLACK (visited)
        return False

    for node in sorted(nodes):
        if color[node] == 0:
            if dfs(node):
                return True, cycle_path

    return False, []


def analyze_pdm_network_topology(edges: list[tuple[Any, Any]]) -> dict:
    """Analiza la topología de red PDM (Precedence Diagramming Method, PMI 6.3).

    Calcula grados de entrada/salida, puntos de convergencia de rutas
    (merge, in_degree >= 2) y de divergencia (burst, out_degree >= 2), y
    clasifica la complejidad de la red:
    - 'cyclic_invalid': la dependencia tiene ciclo (grafo inválido).
    - 'high_convergence': max_in_degree >= 3 o ≥ 2 puntos de convergencia.
    - 'moderate': un punto de convergencia o ≥ 1 punto de divergencia.
    - 'linear_or_empty': cadena lineal o grafo vacío.
    """
    from collections import Counter

    normalized = [(str(p), str(s)) for p, s in edges]
    nodes: set[str] = set()
    for predecessor, successor in normalized:
        nodes.add(predecessor)
        nodes.add(successor)

    total_nodes = len(nodes)
    total_edges = len(edges)  # longitud original de la lista (puede traer duplicados)
    has_cycle, _ = detect_cycle_in_dependencies(edges)

    in_degree: Counter[str] = Counter(successor for _, successor in normalized)
    out_degree: Counter[str] = Counter(predecessor for predecessor, _ in normalized)

    max_in_degree = max(in_degree.values(), default=0)
    max_out_degree = max(out_degree.values(), default=0)
    merge_nodes_count = sum(1 for deg in in_degree.values() if deg >= 2)  # PMI Path Convergence
    burst_nodes_count = sum(1 for deg in out_degree.values() if deg >= 2)  # PMI Path Divergence

    if has_cycle:
        network_complexity_level = "cyclic_invalid"
    elif max_in_degree >= 3 or merge_nodes_count >= 2:
        network_complexity_level = "high_convergence"
    elif merge_nodes_count == 1 or burst_nodes_count >= 1:
        network_complexity_level = "moderate"
    else:
        network_complexity_level = "linear_or_empty"

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "has_cycle": has_cycle,
        "max_in_degree": max_in_degree,
        "max_out_degree": max_out_degree,
        "merge_nodes_count": merge_nodes_count,
        "burst_nodes_count": burst_nodes_count,
        "network_complexity_level": network_complexity_level,
    }


def get_task_dependencies(db: Session, project_id: UUID | str) -> list[models.ProjectTaskDependency]:
    return (
        db.query(models.ProjectTaskDependency)
        .filter(
            models.ProjectTaskDependency.project_id == project_id,
            models.ProjectTaskDependency.deleted_at.is_(None),
        )
        .all()
    )


def create_task_dependency(
    db: Session, project_id: UUID | str, dep_in: schemas.ProjectTaskDependencyCreate
) -> models.ProjectTaskDependency:
    project_uuid = _to_uuid(project_id)
    pred_uuid = _to_uuid(dep_in.predecessor_id)
    succ_uuid = _to_uuid(dep_in.successor_id)

    if pred_uuid == succ_uuid:
        raise CircularDependencyError(
            f"Dependencia circular detectada: una tarea ({pred_uuid}) no puede depender de sí misma"
        )

    task_ids = {pred_uuid, succ_uuid}
    task_ids.discard(None)
    project_task_ids = {
        row[0]
        for row in db.query(models.ProjectTask.id)
        .filter(
            models.ProjectTask.project_id == project_uuid,
            models.ProjectTask.deleted_at.is_(None),
            models.ProjectTask.id.in_(task_ids),
        )
        .all()
    }
    if len(task_ids) != 2 or project_task_ids != task_ids:
        raise ValueError("Both dependency tasks must be active and belong to the project")

    # Topological DFS Cycle Detection
    active_deps = (
        db.query(models.ProjectTaskDependency.predecessor_id, models.ProjectTaskDependency.successor_id)
        .filter(
            models.ProjectTaskDependency.project_id == project_uuid,
            models.ProjectTaskDependency.deleted_at.is_(None),
        )
        .all()
    )
    edges = [(row[0], row[1]) for row in active_deps]
    has_cycle, cycle_path = detect_cycle_in_dependencies(edges, new_edge=(pred_uuid, succ_uuid))
    if has_cycle:
        path_str = " -> ".join(cycle_path) if cycle_path else f"{pred_uuid} -> {succ_uuid}"
        raise CircularDependencyError(
            f"Dependencia circular detectada: la relación {pred_uuid} -> {succ_uuid} crearía un ciclo en el grafo ({path_str}). "
            "No se permiten dependencias circulares para evitar bloqueos en Gantt."
        )

    existing = (
        db.query(models.ProjectTaskDependency)
        .filter(
            models.ProjectTaskDependency.project_id == project_uuid,
            models.ProjectTaskDependency.predecessor_id == dep_in.predecessor_id,
            models.ProjectTaskDependency.successor_id == dep_in.successor_id,
        )
        .first()
    )
    if existing:
        if existing.deleted_at is not None:
            # The DB's unique pair constraint intentionally includes soft-
            # deleted rows. Restore that row instead of INSERTing a duplicate.
            existing.deleted_at = None
            existing.dependency_type = dep_in.dependency_type
            existing.lag_days = dep_in.lag_days
            db.commit()
            db.refresh(existing)
        return existing
    row = models.ProjectTaskDependency(
        project_id=project_uuid,
        predecessor_id=dep_in.predecessor_id,
        successor_id=dep_in.successor_id,
        dependency_type=dep_in.dependency_type,
        lag_days=dep_in.lag_days,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_task_dependency(db: Session, project_id: UUID | str, dep_id: UUID | str) -> bool:
    row = (
        db.query(models.ProjectTaskDependency)
        .filter(
            models.ProjectTaskDependency.id == dep_id,
            models.ProjectTaskDependency.project_id == project_id,
            models.ProjectTaskDependency.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Expenses & Budget (Super-PRO) ──────────────────────


def recalculate_project_budget(db: Session, project_id: UUID | str) -> Optional[models.Project]:
    project = get_project(db, project_id)
    if not project:
        return None
    expenses = (
        db.query(models.ProjectExpense)
        .filter(
            models.ProjectExpense.project_id == project_id,
            models.ProjectExpense.deleted_at.is_(None),
        )
        .all()
    )
    paid_sum = sum(e.amount for e in expenses if e.status in ("paid", "approved"))
    project.budget_spent = round(float(paid_sum), 2)
    db.commit()
    db.refresh(project)
    return project


def get_project_expenses(
    db: Session,
    project_id: UUID | str,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> list[models.ProjectExpense]:
    q = db.query(models.ProjectExpense).filter(
        models.ProjectExpense.project_id == project_id,
        models.ProjectExpense.deleted_at.is_(None),
    )
    if status:
        q = q.filter(models.ProjectExpense.status == status)
    if category:
        q = q.filter(models.ProjectExpense.category == category)
    rows = q.order_by(models.ProjectExpense.date.desc(), models.ProjectExpense.created_at.desc()).all()
    for r in rows:
        if r.creator:
            r.creator_name = r.creator.nombre_completo
        if getattr(r, "task", None):
            r.task_title = r.task.title
    return rows


def get_project_expense(
    db: Session, project_id: UUID | str, expense_id: UUID | str
) -> Optional[models.ProjectExpense]:
    row = (
        db.query(models.ProjectExpense)
        .filter(
            models.ProjectExpense.id == expense_id,
            models.ProjectExpense.project_id == project_id,
            models.ProjectExpense.deleted_at.is_(None),
        )
        .first()
    )
    if row:
        if row.creator:
            row.creator_name = row.creator.nombre_completo
        if getattr(row, "task", None):
            row.task_title = row.task.title
    return row


def create_project_expense(
    db: Session,
    project_id: UUID | str,
    expense_in: schemas.ProjectExpenseCreate,
    created_by: Optional[UUID | str] = None,
) -> models.ProjectExpense:
    exp_date = expense_in.date or datetime.now(timezone.utc)
    row = models.ProjectExpense(
        project_id=project_id,
        component_id=_to_uuid(expense_in.component_id) if expense_in.component_id else None,
        task_id=_to_uuid(expense_in.task_id) if getattr(expense_in, "task_id", None) else None,
        category=expense_in.category or "general",
        description=expense_in.description,
        amount=round(float(expense_in.amount), 2),
        date=exp_date,
        receipt_url=expense_in.receipt_url,
        status=expense_in.status or "planned",
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    recalculate_project_budget(db, project_id)
    if row.status in ("approved", "paid"):
        trigger_project_automations_safe(
            db,
            project_id,
            "expense_approved",
            {
                "expense_id": str(row.id),
                "amount": float(row.amount or 0.0),
                "category": row.category,
                "task_id": str(row.task_id) if row.task_id else None,
            },
            actor_persona_id=created_by,
        )
    if row.creator:
        row.creator_name = row.creator.nombre_completo
    if getattr(row, "task", None):
        row.task_title = row.task.title
    return row


def update_project_expense(
    db: Session,
    project_id: UUID | str,
    expense_id: UUID | str,
    expense_in: schemas.ProjectExpenseUpdate,
) -> Optional[models.ProjectExpense]:
    row = get_project_expense(db, project_id, expense_id)
    if not row:
        return None
    prev_status = row.status
    nullable_fields = {"description", "receipt_url", "component_id", "task_id"}
    for k, v in expense_in.model_dump(exclude_unset=True).items():
        if v is not None or k in nullable_fields:
            if k == "amount":
                setattr(row, k, round(float(v), 2))
            elif k in ("component_id", "task_id"):
                setattr(row, k, _to_uuid(v) if v else None)
            else:
                setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    recalculate_project_budget(db, project_id)
    if row.status in ("approved", "paid") and prev_status not in ("approved", "paid"):
        trigger_project_automations_safe(
            db,
            project_id,
            "expense_approved",
            {
                "expense_id": str(row.id),
                "amount": float(row.amount or 0.0),
                "category": row.category,
                "task_id": str(row.task_id) if row.task_id else None,
            },
            actor_persona_id=row.created_by,
        )
    if row.creator:
        row.creator_name = row.creator.nombre_completo
    if getattr(row, "task", None):
        row.task_title = row.task.title
    return row


def delete_project_expense(db: Session, project_id: UUID | str, expense_id: UUID | str) -> bool:
    row = get_project_expense(db, project_id, expense_id)
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    recalculate_project_budget(db, project_id)
    return True


def get_project_budget_summary(db: Session, project_id: UUID | str) -> Optional[dict]:
    project = get_project(db, project_id)
    if not project:
        return None
    expenses = (
        db.query(models.ProjectExpense)
        .filter(
            models.ProjectExpense.project_id == project_id,
            models.ProjectExpense.deleted_at.is_(None),
        )
        .all()
    )
    allocated = float(project.budget_allocated or 0.0)
    planned = sum(e.amount for e in expenses if e.status == "planned")
    committed = sum(e.amount for e in expenses if e.status == "committed")
    paid = sum(e.amount for e in expenses if e.status in ("paid", "approved"))

    # This helper is called by GET endpoints and must remain read-only. Expense
    # create/update/delete mutations persist the derived field via
    # recalculate_project_budget().
    remaining = max(0.0, allocated - paid)
    burn_rate = round((paid / allocated * 100), 2) if allocated > 0 else 0.0

    by_category: dict[str, float] = {}
    for e in expenses:
        cat = e.category or "general"
        by_category[cat] = round(by_category.get(cat, 0.0) + float(e.amount), 2)

    from backend.services.project_evm_service import (
        calculate_project_evm,
        compute_project_reserves_breakdown,
    )

    reserves_info = compute_project_reserves_breakdown(db, project, bac=allocated)
    evm_metrics = calculate_project_evm(db, project)

    return {
        "project_id": str(project.id),
        "budget_allocated": allocated,
        "budget_spent": round(paid, 2),
        "remaining_budget": round(remaining, 2),
        "burn_rate_percent": burn_rate,
        "total_expenses_count": len(expenses),
        "planned_amount": round(planned, 2),
        "committed_amount": round(committed, 2),
        "paid_amount": round(paid, 2),
        "work_packages_budget": reserves_info["work_packages_budget"],
        "contingency_reserve": reserves_info["contingency_reserve"],
        "management_reserve": reserves_info["management_reserve"],
        "management_reserve_pct": reserves_info["management_reserve_pct"],
        "total_project_budget": reserves_info["total_project_budget"],
        "threats_emv": reserves_info["threats_emv"],
        "opportunities_emv": reserves_info["opportunities_emv"],
        "net_emv": reserves_info["net_emv"],
        "cpi_stability_rule": evm_metrics.get("cpi_stability_rule"),
        "early_warning_sentinel": evm_metrics.get("early_warning_sentinel"),
        "by_category": by_category,
    }


# ── Risks (RAID Matrix) ──────────────────────────────────


def get_project_risks(
    db: Session,
    project_id: UUID | str,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> list[models.ProjectRisk]:
    q = (
        db.query(models.ProjectRisk)
        .options(selectinload(models.ProjectRisk.owner))
        .filter(
            models.ProjectRisk.project_id == project_id,
            models.ProjectRisk.deleted_at.is_(None),
        )
    )
    if status:
        q = q.filter(models.ProjectRisk.status == status)
    if category:
        q = q.filter(models.ProjectRisk.category == category)
    rows = q.order_by(models.ProjectRisk.severity_score.desc(), models.ProjectRisk.created_at.desc()).all()
    return rows


def get_project_risk(
    db: Session, project_id: UUID | str, risk_id: UUID | str
) -> Optional[models.ProjectRisk]:
    return (
        db.query(models.ProjectRisk)
        .options(selectinload(models.ProjectRisk.owner))
        .filter(
            models.ProjectRisk.id == risk_id,
            models.ProjectRisk.project_id == project_id,
            models.ProjectRisk.deleted_at.is_(None),
        )
        .first()
    )


def _assert_risk_owner_in_project_sede(
    db: Session, project_id: UUID | str, owner_id: UUID | str | None
) -> None:
    """Keep a risk owner in the same tenant as its project, including direct CRUD callers."""
    if owner_id is None:
        return
    project = get_project(db, project_id)
    owner = db.query(models.Persona).filter(models.Persona.id == _to_uuid(owner_id)).first()
    if not project or not owner or str(owner.sede_id) != str(project.sede_id):
        raise ValueError("Risk owner not found in project sede")


def create_project_risk(
    db: Session,
    project_id: UUID | str,
    risk_in: schemas.ProjectRiskCreate,
) -> models.ProjectRisk:
    _assert_risk_owner_in_project_sede(db, project_id, risk_in.owner_id)
    prob = risk_in.probability or 3
    imp = risk_in.impact or 3
    sev = prob * imp
    row = models.ProjectRisk(
        project_id=project_id,
        title=risk_in.title,
        category=risk_in.category or "tecnico",
        risk_type=getattr(risk_in, "risk_type", "threat") or "threat",
        probability=prob,
        probability_pct=getattr(risk_in, "probability_pct", None),
        impact=imp,
        financial_impact=float(getattr(risk_in, "financial_impact", 0.0) or 0.0),
        severity_score=sev,
        mitigation_plan=risk_in.mitigation_plan,
        contingency_plan=risk_in.contingency_plan,
        owner_id=risk_in.owner_id,
        status=risk_in.status or "active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if row.owner_id:
        row = get_project_risk(db, project_id, row.id)
    return row


def update_project_risk(
    db: Session,
    project_id: UUID | str,
    risk_id: UUID | str,
    risk_in: schemas.ProjectRiskUpdate,
) -> Optional[models.ProjectRisk]:
    from backend.models_projects import decode_risk_meta, encode_risk_meta

    row = get_project_risk(db, project_id, risk_id)
    if not row:
        return None
    data = risk_in.model_dump(exclude_unset=True)
    if "owner_id" in data:
        _assert_risk_owner_in_project_sede(db, project_id, data["owner_id"])

    clean_plan, existing_meta = decode_risk_meta(row.contingency_plan)
    if "contingency_plan" in data:
        new_clean_plan, _ = decode_risk_meta(data.pop("contingency_plan"))
    else:
        new_clean_plan = clean_plan

    r_type = data.pop("risk_type", None) or existing_meta.get("risk_type") or row.risk_type or "threat"
    if "probability_pct" in data:
        p_pct = data.pop("probability_pct")
    elif "probability" in data and existing_meta.get("probability_pct") is None:
        p_pct = None
    else:
        p_pct = existing_meta.get("probability_pct")

    f_imp = data.pop("financial_impact", None)
    if f_imp is None:
        f_imp = existing_meta.get("financial_impact", row.financial_impact)

    nullable_risk_fields = {"mitigation_plan", "owner_id"}
    for k, v in data.items():
        if v is not None or k in nullable_risk_fields:
            setattr(row, k, v)

    row.contingency_plan = encode_risk_meta(
        new_clean_plan,
        risk_type=str(r_type),
        probability_pct=float(p_pct) if p_pct is not None else None,
        financial_impact=float(f_imp or 0.0),
    )
    row.__dict__["_risk_type"] = "opportunity" if str(r_type).lower() == "opportunity" else "threat"
    row.__dict__["_probability_pct"] = float(p_pct) if p_pct is not None else None
    row.__dict__["_financial_impact"] = float(f_imp or 0.0)

    # Recalcular severity_score
    prob = row.probability or 1
    imp = row.impact or 1
    row.severity_score = prob * imp
    row.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return row


def delete_project_risk(db: Session, project_id: UUID | str, risk_id: UUID | str) -> bool:
    row = get_project_risk(db, project_id, risk_id)
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def convert_risk_to_task(
    db: Session,
    project_id: UUID | str,
    risk_id: UUID | str,
    actor_id: Optional[UUID | str] = None,
) -> Optional[models.ProjectTask]:
    from backend.models_projects import decode_risk_meta

    risk = get_project_risk(db, project_id, risk_id)
    if not risk:
        return None

    # Marcar el riesgo como ocurrido
    risk.status = "occurred"
    risk.updated_at = datetime.now(timezone.utc)

    sev = (risk.probability or 1) * (risk.impact or 1)
    priority = "urgent" if sev >= 15 else ("high" if sev >= 10 else "medium")
    clean_contingency, _ = decode_risk_meta(risk.contingency_plan)

    desc_lines = [
        "**[INCIDENCIA RAID MATERIALIZADA]**",
        f"- **Categoría:** {risk.category}",
        f"- **Probabilidad:** {risk.probability}/5 | **Impacto:** {risk.impact}/5 (Severidad: {sev}/25)",
        "",
        "**Plan de Contingencia Activado:**",
        f"{clean_contingency or 'No especificado'}",
        "",
        "**Plan de Mitigación Previsto:**",
        f"{risk.mitigation_plan or 'No especificado'}",
    ]

    task = models.ProjectTask(
        project_id=project_id,
        title=f"[RAID] {risk.title}",
        description="\n".join(desc_lines),
        status="todo",
        priority=priority,
        assignee_id=risk.owner_id,
        start_date=datetime.now(timezone.utc),
    )
    db.add(task)

    # Registrar en el log de actividades
    activity = models.ProjectActivityLog(
        project_id=project_id,
        persona_id=actor_id or risk.owner_id,
        action_type="risk_converted",
        description=f"Riesgo '{risk.title}' convertido en tarea con severidad {sev}/25 ({priority}).",
    )
    db.add(activity)

    db.commit()
    db.refresh(task)
    return task


def get_project_risks_summary(db: Session, project_id: UUID | str) -> Optional[dict]:
    project = get_project(db, project_id)
    if not project:
        return None

    risks = (
        db.query(models.ProjectRisk)
        .filter(
            models.ProjectRisk.project_id == project_id,
            models.ProjectRisk.deleted_at.is_(None),
        )
        .all()
    )

    total = len(risks)
    active = sum(1 for r in risks if r.status == "active")
    mitigated = sum(1 for r in risks if r.status == "mitigated")
    occurred = sum(1 for r in risks if r.status == "occurred")

    critical = sum(1 for r in risks if (r.probability or 1) * (r.impact or 1) >= 15)
    high = sum(1 for r in risks if 10 <= (r.probability or 1) * (r.impact or 1) < 15)
    medium = sum(1 for r in risks if 5 <= (r.probability or 1) * (r.impact or 1) < 10)
    low = sum(1 for r in risks if (r.probability or 1) * (r.impact or 1) < 5)

    threats_count = sum(1 for r in risks if getattr(r, "risk_type", "threat") != "opportunity")
    opportunities_count = sum(1 for r in risks if getattr(r, "risk_type", "threat") == "opportunity")

    threats_emv = round(
        sum(
            max(0.0, float(getattr(r, "emv", 0.0) or 0.0))
            for r in risks
            if r.status == "active" and getattr(r, "risk_type", "threat") != "opportunity"
        ),
        2,
    )
    opportunities_emv = round(
        sum(
            min(0.0, float(getattr(r, "emv", 0.0) or 0.0))
            for r in risks
            if r.status == "active" and getattr(r, "risk_type", "threat") == "opportunity"
        ),
        2,
    )
    total_emv = round(threats_emv + opportunities_emv, 2)
    required_contingency_reserve = round(max(0.0, threats_emv), 2)

    by_category: dict[str, int] = {}
    for r in risks:
        cat = r.category or "tecnico"
        by_category[cat] = by_category.get(cat, 0) + 1

    # Construcción de la matriz 5x5
    matrix_5x5 = []
    for p in range(1, 6):
        for i in range(1, 6):
            cell_risks = [r for r in risks if r.probability == p and r.impact == i]
            matrix_5x5.append({
                "probability": p,
                "impact": i,
                "severity_score": p * i,
                "count": len(cell_risks),
                "risk_ids": [str(r.id) for r in cell_risks],
                "active_count": sum(1 for r in cell_risks if r.status == "active"),
            })

    return {
        "project_id": str(project.id),
        "total_risks": total,
        "active_risks": active,
        "mitigated_risks": mitigated,
        "occurred_risks": occurred,
        "critical_count": critical,
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "threats_count": threats_count,
        "opportunities_count": opportunities_count,
        "threats_emv": threats_emv,
        "opportunities_emv": opportunities_emv,
        "total_emv": total_emv,
        "required_contingency_reserve": required_contingency_reserve,
        "matrix_5x5": matrix_5x5,
        "by_category": by_category,
    }


# ── Workload Planning (Super-PRO Fase 3) ─────────────────


def get_project_workload(db: Session, project_id: UUID | str) -> Optional[dict]:
    project = get_project(db, project_id)
    if not project:
        return None

    now_utc = datetime.now(timezone.utc)

    # 1. Obtener todas las tareas no eliminadas del proyecto
    tasks = (
        db.query(models.ProjectTask)
        .options(selectinload(models.ProjectTask.assignee))
        .filter(
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .order_by(models.ProjectTask.due_date.asc(), models.ProjectTask.order_index.asc())
        .all()
    )

    all_task_ids = {str(t.id) for t in tasks}
    parent_ids_with_children = {
        str(t.parent_id)
        for t in tasks
        if t.parent_id and str(t.parent_id) in all_task_ids and str(t.parent_id) != str(t.id)
    }

    # Obtener registros de tiempo reales (ProjectTimeLog)
    time_logs = (
        db.query(models.ProjectTimeLog)
        .filter(
            models.ProjectTimeLog.project_id == project_id,
            models.ProjectTimeLog.deleted_at.is_(None),
        )
        .all()
    )
    hours_by_task: dict[str, float] = {}
    hours_by_persona: dict[str, float] = {}
    for tl in time_logs:
        h = float(tl.hours or 0.0)
        if tl.task_id:
            tid_s = str(tl.task_id)
            hours_by_task[tid_s] = round(hours_by_task.get(tid_s, 0.0) + h, 2)
        if tl.persona_id:
            pid_s = str(tl.persona_id)
            hours_by_persona[pid_s] = round(hours_by_persona.get(pid_s, 0.0) + h, 2)

    # 2. Obtener miembros explícitos del proyecto
    members_rows = (
        db.query(models.ProjectMember)
        .options(selectinload(models.ProjectMember.persona))
        .filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.deleted_at.is_(None),
        )
        .all()
    )

    # Conjunto de personas conocidas
    personas_map: dict[str, models.Persona] = {}
    for m in members_rows:
        if m.persona:
            personas_map[str(m.persona.id)] = m.persona

    # Añadir al owner si existe
    if project.owner_id:
        owner_p = db.query(models.Persona).filter(models.Persona.id == project.owner_id).first()
        if owner_p:
            personas_map[str(owner_p.id)] = owner_p

    # Añadir personas asignadas a tareas que no estén en la lista de miembros
    for t in tasks:
        if t.assignee_id:
            pid_str = str(t.assignee_id)
            if pid_str not in personas_map:
                if t.assignee:
                    personas_map[pid_str] = t.assignee
                else:
                    p = db.query(models.Persona).filter(models.Persona.id == t.assignee_id).first()
                    if p:
                        personas_map[pid_str] = p

    # 3. Agrupar tareas por responsable
    tasks_by_assignee: dict[Optional[str], list[models.ProjectTask]] = {}
    for t in tasks:
        key = str(t.assignee_id) if t.assignee_id else None
        tasks_by_assignee.setdefault(key, []).append(t)

    member_workloads = []
    total_active_tasks = 0
    total_completed_tasks = 0
    total_overdue_tasks = 0
    total_estimated_hours = 0.0
    total_actual_hours = 0.0

    overloaded_count = 0
    balanced_count = 0
    available_count = 0

    # Procesar miembros conocidos
    for pid_str, persona in personas_map.items():
        assigned = tasks_by_assignee.get(pid_str, [])
        active_t = [t for t in assigned if t.status != "completed"]
        completed_t = [t for t in assigned if t.status == "completed"]

        overdue_t = []
        for t in active_t:
            if t.due_date:
                t_due = t.due_date if getattr(t.due_date, "tzinfo", None) else t.due_date.replace(tzinfo=timezone.utc)
                if t_due < now_utc:
                    overdue_t.append(t)

        urgent_count = sum(1 for t in active_t if t.priority == "urgent")
        high_count = sum(1 for t in active_t if t.priority == "high")
        medium_count = sum(1 for t in active_t if t.priority in ("medium", "normal"))
        low_count = sum(1 for t in active_t if t.priority == "low")

        active_count = len(active_t)
        total_active_tasks += active_count
        total_completed_tasks += len(completed_t)
        total_overdue_tasks += len(overdue_t)

        # Esfuerzo en horas (ponderando tareas hoja para evitar doble conteo padre+subtarea)
        leaf_assigned = [t for t in assigned if str(t.id) not in parent_ids_with_children]
        est_hours_member = round(
            sum(float(getattr(t, "estimated_hours", 0.0) or 0.0) for t in (leaf_assigned or assigned)),
            2,
        )
        task_logged_member = sum(hours_by_task.get(str(t.id), 0.0) for t in assigned)
        act_hours_member = round(max(hours_by_persona.get(pid_str, 0.0), task_logged_member), 2)
        hours_util_pct = (
            round((act_hours_member / est_hours_member) * 100.0, 1)
            if est_hours_member > 0.0
            else (100.0 if act_hours_member > 0.0 else 0.0)
        )
        total_estimated_hours = round(total_estimated_hours + est_hours_member, 2)
        total_actual_hours = round(total_actual_hours + act_hours_member, 2)

        active_est_hours = sum(
            float(getattr(t, "estimated_hours", 0.0) or 0.0)
            for t in (leaf_assigned or assigned)
            if t.status != "completed"
        )

        # Regla de capacidad:
        # - Overloaded: 5 o más activas, o 2 o más vencidas, o 2 o más urgentes, o >= 40h activas estimadas
        # - Balanced: 2 a 4 activas (o >= 16h activas estimadas)
        # - Available: 0 a 1 activas
        if active_count >= 5 or len(overdue_t) >= 2 or urgent_count >= 2 or active_est_hours >= 40.0:
            status = "overloaded"
            overloaded_count += 1
        elif active_count >= 2 or active_est_hours >= 16.0:
            status = "balanced"
            balanced_count += 1
        else:
            status = "available"
            available_count += 1

        task_pct = round((active_count / 5.0) * 100)
        hours_pct = round((active_est_hours / 40.0) * 100) if active_est_hours > 0 else 0
        workload_pct = min(100, max(task_pct, hours_pct))

        # Tareas serializadas para UI
        task_items = []
        for t in assigned:
            is_od = False
            if t.status != "completed" and t.due_date:
                t_due = t.due_date if getattr(t.due_date, "tzinfo", None) else t.due_date.replace(tzinfo=timezone.utc)
                is_od = bool(t_due < now_utc)
            t_est = round(float(getattr(t, "estimated_hours", 0.0) or 0.0), 2)
            t_act = round(hours_by_task.get(str(t.id), 0.0), 2)
            task_items.append({
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
                "is_overdue": is_od,
                "estimated_hours": t_est,
                "actual_hours": t_act,
            })

        name = getattr(persona, "nombre_completo", None) or f"{getattr(persona, 'nombres', '')} {getattr(persona, 'apellidos', '')}".strip() or "Miembro"
        member_workloads.append({
            "persona_id": pid_str,
            "name": name,
            "email": getattr(persona, "email", None),
            "avatar_url": getattr(persona, "foto_url", None),
            "total_tasks": len(assigned),
            "active_tasks": active_count,
            "completed_tasks": len(completed_t),
            "overdue_tasks": len(overdue_t),
            "urgent_tasks": urgent_count,
            "high_tasks": high_count,
            "medium_tasks": medium_count,
            "low_tasks": low_count,
            "estimated_hours_total": est_hours_member,
            "actual_hours_logged": act_hours_member,
            "hours_utilization_pct": hours_util_pct,
            "capacity_status": status,
            "workload_percent": workload_pct,
            "tasks": task_items,
        })

    # Tareas sin asignar
    unassigned = tasks_by_assignee.get(None, [])
    unassigned_active = [t for t in unassigned if t.status != "completed"]
    unassigned_count = len(unassigned_active)
    total_active_tasks += unassigned_count
    total_completed_tasks += sum(1 for t in unassigned if t.status == "completed")

    if unassigned:
        unassigned_leaf = [t for t in unassigned if str(t.id) not in parent_ids_with_children]
        unassigned_est = round(
            sum(float(getattr(t, "estimated_hours", 0.0) or 0.0) for t in (unassigned_leaf or unassigned)),
            2,
        )
        unassigned_act = round(sum(hours_by_task.get(str(t.id), 0.0) for t in unassigned), 2)
        total_estimated_hours = round(total_estimated_hours + unassigned_est, 2)
        total_actual_hours = round(total_actual_hours + unassigned_act, 2)
        unassigned_util = round((unassigned_act / unassigned_est) * 100.0, 1) if unassigned_est > 0 else 0.0

        unassigned_task_items = []
        for t in unassigned:
            is_od = False
            if t.status != "completed" and t.due_date:
                t_due = t.due_date if getattr(t.due_date, "tzinfo", None) else t.due_date.replace(tzinfo=timezone.utc)
                is_od = bool(t_due < now_utc)
            unassigned_task_items.append({
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
                "is_overdue": is_od,
                "estimated_hours": round(float(getattr(t, "estimated_hours", 0.0) or 0.0), 2),
                "actual_hours": round(hours_by_task.get(str(t.id), 0.0), 2),
            })

        member_workloads.append({
            "persona_id": None,
            "name": "Sin Asignar",
            "email": None,
            "avatar_url": None,
            "total_tasks": len(unassigned),
            "active_tasks": unassigned_count,
            "completed_tasks": len(unassigned) - unassigned_count,
            "overdue_tasks": sum(1 for t in unassigned_task_items if t["is_overdue"]),
            "urgent_tasks": sum(1 for t in unassigned_active if t.priority == "urgent"),
            "high_tasks": sum(1 for t in unassigned_active if t.priority == "high"),
            "medium_tasks": sum(1 for t in unassigned_active if t.priority in ("medium", "normal")),
            "low_tasks": sum(1 for t in unassigned_active if t.priority == "low"),
            "estimated_hours_total": unassigned_est,
            "actual_hours_logged": unassigned_act,
            "hours_utilization_pct": unassigned_util,
            "capacity_status": "available",
            "workload_percent": 0,
            "tasks": unassigned_task_items,
        })

    # Ordenar miembros: primero overloaded, luego balanced, luego available, y Sin Asignar al final
    status_order = {"overloaded": 0, "balanced": 1, "available": 2}
    member_workloads.sort(
        key=lambda m: (1 if m["persona_id"] is None else 0, status_order.get(m["capacity_status"], 3), -m["active_tasks"])
    )

    return {
        "project_id": str(project.id),
        "total_members": len(personas_map),
        "total_active_tasks": total_active_tasks,
        "total_completed_tasks": total_completed_tasks,
        "total_overdue_tasks": total_overdue_tasks,
        "total_estimated_hours": total_estimated_hours,
        "total_actual_hours": total_actual_hours,
        "overloaded_members_count": overloaded_count,
        "balanced_members_count": balanced_count,
        "available_members_count": available_count,
        "unassigned_tasks_count": unassigned_count,
        "members": member_workloads,
    }


def reassign_project_task(
    db: Session,
    project_id: UUID | str,
    task_id: UUID | str,
    new_assignee_id: Optional[UUID | str],
) -> Optional[models.ProjectTask]:
    task = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.id == task_id,
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    if not task:
        return None

    task.assignee_id = new_assignee_id
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


# ── Critical Path Method (CPM) & Project Baselines (Super-PRO Fase 4) ──


def calculate_critical_path(db: Session, project_id: UUID | str) -> Optional[dict]:
    project = get_project(db, project_id)
    if not project:
        return None

    all_tasks = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .order_by(models.ProjectTask.order_index.asc())
        .all()
    )

    if not all_tasks:
        return {
            "project_id": str(project.id),
            "total_duration_days": 0,
            "critical_tasks_count": 0,
            "excluded_parent_tasks_count": 0,
            "total_lag_days": 0,
            "critical_path_task_ids": [],
            "tasks": [],
            "has_cycles": False,
        }

    # Filtrar actividades contenedoras padre que tienen subtareas activas para evitar caminos duplicados en CPM
    all_ids_set = {str(t.id) for t in all_tasks}
    parent_ids_with_active_subtasks = {
        str(t.parent_id)
        for t in all_tasks
        if t.parent_id and str(t.parent_id) in all_ids_set and str(t.parent_id) != str(t.id)
    }
    tasks = [t for t in all_tasks if str(t.id) not in parent_ids_with_active_subtasks]
    if not tasks:
        tasks = list(all_tasks)
    excluded_parent_tasks_count = len(all_tasks) - len(tasks)

    task_map = {str(t.id): t for t in tasks}
    task_ids = list(task_map.keys())

    # Duración de cada tarea (mínimo 1 día)
    durations = {}
    for t_id, t in task_map.items():
        if t.start_date and t.due_date:
            try:
                s_dt = t.start_date.date() if hasattr(t.start_date, "date") else t.start_date
                d_dt = t.due_date.date() if hasattr(t.due_date, "date") else t.due_date
                dur = max(1, (d_dt - s_dt).days + 1)
            except Exception:
                dur = 1
        else:
            dur = 1
        durations[t_id] = dur

    # Obtener dependencias activas del proyecto
    deps = (
        db.query(models.ProjectTaskDependency)
        .filter(
            models.ProjectTaskDependency.project_id == project_id,
            models.ProjectTaskDependency.deleted_at.is_(None),
        )
        .all()
    )

    # Grafo
    succs = {t_id: [] for t_id in task_ids}
    preds = {t_id: [] for t_id in task_ids}
    in_degree = {t_id: 0 for t_id in task_ids}
    max_incoming_lag = {t_id: 0 for t_id in task_ids}
    total_lag_days = 0

    for dep in deps:
        p_id = str(dep.predecessor_id)
        s_id = str(dep.successor_id)
        if p_id in task_map and s_id in task_map and p_id != s_id:
            lag = int(dep.lag_days or 0)
            total_lag_days += lag
            succs[p_id].append((s_id, lag))
            preds[s_id].append((p_id, lag))
            in_degree[s_id] += 1
            if lag > max_incoming_lag[s_id]:
                max_incoming_lag[s_id] = lag

    # Orden topológico (Algoritmo de Kahn)
    queue = [t_id for t_id in task_ids if in_degree[t_id] == 0]
    topo_order = []
    temp_in_degree = in_degree.copy()

    while queue:
        curr = queue.pop(0)
        topo_order.append(curr)
        for s_id, _ in succs[curr]:
            temp_in_degree[s_id] -= 1
            if temp_in_degree[s_id] == 0:
                queue.append(s_id)

    has_cycles = len(topo_order) < len(task_ids)
    if has_cycles:
        for t_id in task_ids:
            if t_id not in topo_order:
                topo_order.append(t_id)

    # 1. Forward Pass (Early Start y Early Finish)
    ES = {t_id: 0 for t_id in task_ids}
    EF = {t_id: durations[t_id] for t_id in task_ids}

    for u in topo_order:
        for v, lag in succs[u]:
            new_es = EF[u] + lag
            if new_es > ES[v]:
                ES[v] = new_es
                EF[v] = ES[v] + durations[v]

    total_project_duration = max(EF.values()) if EF else 0

    # 2. Backward Pass (Late Start y Late Finish)
    LF = {t_id: total_project_duration for t_id in task_ids}
    LS = {t_id: total_project_duration - durations[t_id] for t_id in task_ids}

    for u in reversed(topo_order):
        if succs[u]:
            min_lf = min(LS[v] - lag for v, lag in succs[u])
            LF[u] = min_lf
            LS[u] = LF[u] - durations[u]
        else:
            LF[u] = total_project_duration
            LS[u] = LF[u] - durations[u]

    # 3. Slack y Tareas Críticas
    slack = {t_id: max(0, LS[t_id] - ES[t_id]) for t_id in task_ids}
    is_crit = {t_id: (slack[t_id] == 0) for t_id in task_ids}

    critical_path_ids = [t_id for t_id in topo_order if is_crit[t_id]]

    now_utc = datetime.now(timezone.utc)
    base_date = project.start_date or now_utc
    if not hasattr(base_date, "tzinfo") or not base_date.tzinfo:
        base_date = base_date.replace(tzinfo=timezone.utc)

    task_items = []
    for t_id in task_ids:
        t = task_map[t_id]
        dur = durations[t_id]
        es = ES[t_id]
        ef = EF[t_id]
        ls = LS[t_id]
        lf = LF[t_id]
        sl = slack[t_id]
        crit = is_crit[t_id]

        es_date = base_date + timedelta(days=es)
        ef_date = base_date + timedelta(days=ef)
        ls_date = base_date + timedelta(days=ls)
        lf_date = base_date + timedelta(days=lf)

        task_items.append({
            "task_id": t_id,
            "title": t.title,
            "duration_days": dur,
            "lag_days": max_incoming_lag[t_id],
            "early_start": es,
            "early_finish": ef,
            "late_start": ls,
            "late_finish": lf,
            "slack_days": sl,
            "is_critical": crit,
            "early_start_date": es_date,
            "early_finish_date": ef_date,
            "late_start_date": ls_date,
            "late_finish_date": lf_date,
        })

    return {
        "project_id": str(project.id),
        "total_duration_days": total_project_duration,
        "critical_tasks_count": len(critical_path_ids),
        "excluded_parent_tasks_count": excluded_parent_tasks_count,
        "total_lag_days": total_lag_days,
        "critical_path_task_ids": critical_path_ids,
        "tasks": task_items,
        "has_cycles": has_cycles,
    }


def create_project_baseline(
    db: Session,
    project_id: UUID | str,
    baseline_in: schemas.ProjectBaselineCreate,
    user_id: Optional[UUID | str] = None,
) -> models.ProjectBaseline:
    project = get_project(db, project_id)
    if not project:
        raise ValueError("Proyecto no encontrado")

    tasks = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .order_by(models.ProjectTask.order_index.asc())
        .all()
    )

    evm_snapshot: dict[str, Any] = {}
    try:
        from backend.services.project_evm_service import calculate_project_evm
        evm_now = calculate_project_evm(db, project)
        evm_snapshot = {
            "bac": evm_now.get("bac", float(project.budget_allocated or 0.0)),
            "ac": evm_now.get("ac", float(project.budget_spent or 0.0)),
            "ev": evm_now.get("ev", 0.0),
            "pv": evm_now.get("pv", 0.0),
            "progress_percentage": evm_now.get("progress_percentage", 0.0),
            "cpi": evm_now.get("cpi", 1.0),
            "spi": evm_now.get("spi", 1.0),
        }
    except Exception:
        evm_snapshot = {
            "bac": float(project.budget_allocated or 0.0),
            "ac": float(project.budget_spent or 0.0),
            "ev": 0.0,
            "pv": 0.0,
            "progress_percentage": 0.0,
            "cpi": 1.0,
            "spi": 1.0,
        }

    snapshot_data = {
        "project_id": str(project.id),
        "project_title": project.title,
        "bac": float(project.budget_allocated or 0.0),
        "budget_allocated": float(project.budget_allocated or 0.0),
        "budget_spent": float(project.budget_spent or 0.0),
        "progress_percentage": evm_snapshot.get("progress_percentage", 0.0),
        "evm": evm_snapshot,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "target_date": project.target_date.isoformat() if project.target_date else None,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "total_tasks": len(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "estimated_hours": float(getattr(t, "estimated_hours", 0.0) or 0.0),
                "physical_progress_pct": float(getattr(t, "physical_progress_pct", 0.0) or 0.0),
                "start_date": t.start_date.isoformat() if t.start_date else None,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "order_index": t.order_index,
            }
            for t in tasks
        ],
    }

    baseline = models.ProjectBaseline(
        project_id=project.id,
        name=baseline_in.name,
        description=baseline_in.description,
        snapshot_data=snapshot_data,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def get_project_latest_baseline(db: Session, project_id: UUID | str) -> Optional[dict]:
    baseline = (
        db.query(models.ProjectBaseline)
        .filter(
            models.ProjectBaseline.project_id == project_id,
            models.ProjectBaseline.deleted_at.is_(None),
        )
        .order_by(models.ProjectBaseline.created_at.desc())
        .first()
    )
    if not baseline:
        return None

    current_tasks = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .all()
    )
    current_map = {str(t.id): t for t in current_tasks}

    snapshot = baseline.snapshot_data or {}
    snap_tasks = snapshot.get("tasks", [])

    comparisons = []
    total_pos_variance = 0

    for st in snap_tasks:
        t_id = st.get("id")
        cur_t = current_map.get(t_id)

        b_start = datetime.fromisoformat(st["start_date"]) if st.get("start_date") else None
        b_due = datetime.fromisoformat(st["due_date"]) if st.get("due_date") else None
        b_dur = max(1, (b_due.date() - b_start.date()).days + 1) if (b_start and b_due) else 1

        c_start = cur_t.start_date if cur_t else None
        c_due = cur_t.due_date if cur_t else None
        c_dur = max(1, (c_due.date() - c_start.date()).days + 1) if (c_start and c_due) else 1

        if b_due and c_due:
            b_d = b_due.date() if hasattr(b_due, "date") else b_due
            c_d = c_due.date() if hasattr(c_due, "date") else c_due
            var_days = (c_d - b_d).days
        else:
            var_days = 0

        if var_days > 0:
            total_pos_variance += var_days

        comparisons.append({
            "task_id": t_id,
            "title": cur_t.title if cur_t else st.get("title", ""),
            "baseline_start": b_start,
            "baseline_due": b_due,
            "baseline_duration": b_dur,
            "current_start": c_start,
            "current_due": c_due,
            "current_duration": c_dur,
            "variance_days": var_days,
            "status": cur_t.status if cur_t else st.get("status", "todo"),
        })

    return {
        "id": str(baseline.id),
        "project_id": str(baseline.project_id),
        "name": baseline.name,
        "description": baseline.description,
        "created_by": str(baseline.created_by) if baseline.created_by else None,
        "created_at": baseline.created_at,
        "snapshot_data": snapshot,
        "comparisons": comparisons,
        "total_variance_days": total_pos_variance,
    }


def list_project_baselines(db: Session, project_id: UUID | str) -> list[models.ProjectBaseline]:
    return (
        db.query(models.ProjectBaseline)
        .filter(
            models.ProjectBaseline.project_id == project_id,
            models.ProjectBaseline.deleted_at.is_(None),
        )
        .order_by(models.ProjectBaseline.created_at.desc())
        .all()
    )


# ── Time Tracking & Sheets (Super-PRO Fase 5) ───────────────────────────────


def sync_task_time_logs(db: Session, task_id: Any) -> None:
    """Sincroniza las horas registradas en ProjectTimeLog con la tarea (actual_hours, avance y roll-up EDT)."""
    if not task_id:
        return
    task = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.id == _to_uuid(task_id),
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    if not task:
        return

    from sqlalchemy import func
    logged_sum = (
        db.query(func.coalesce(func.sum(models.ProjectTimeLog.hours), 0.0))
        .filter(
            models.ProjectTimeLog.task_id == task.id,
            models.ProjectTimeLog.deleted_at.is_(None),
        )
        .scalar()
    )
    actual_h = round(float(logged_sum or 0.0), 2)
    task.actual_hours = actual_h

    has_subtasks = (
        db.query(models.ProjectTask.id)
        .filter(
            models.ProjectTask.parent_id == task.id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
        is not None
    )
    est_h = float(getattr(task, "estimated_hours", 0.0) or 0.0)
    if not has_subtasks and est_h > 0.0 and task.status not in ("completed", "done"):
        derived_pct = round(min(100.0, (actual_h / est_h) * 100.0), 1)
        task.physical_progress_pct = derived_pct
        if actual_h > 0.0 and task.status == "todo":
            task.status = "in_progress"
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)

    try:
        from backend.services.project_evm_service import sync_parent_task_rollup
        if task.parent_id:
            sync_parent_task_rollup(db, task.parent_id)
        elif has_subtasks:
            sync_parent_task_rollup(db, task.id)
    except Exception:
        pass


def _prepare_time_log_response(log: models.ProjectTimeLog) -> models.ProjectTimeLog:
    if log and hasattr(log, "persona") and log.persona:
        p = log.persona
        log.persona_name = getattr(p, "nombre_completo", None) or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip() or "Miembro"
    elif log:
        log.persona_name = "Miembro"

    if log and hasattr(log, "task") and log.task:
        log.task_title = log.task.title
    elif log:
        log.task_title = "General del Proyecto"

    return log


def create_project_time_log(
    db: Session,
    project_id: UUID | str,
    log_in: schemas.ProjectTimeLogCreate,
    persona_id: UUID | str,
    created_by: Optional[UUID | str] = None,
) -> models.ProjectTimeLog:
    project = get_project(db, project_id)
    if not project:
        raise ValueError("Proyecto no encontrado")

    if log_in.task_id:
        task = (
            db.query(models.ProjectTask)
            .filter(
                models.ProjectTask.id == log_in.task_id,
                models.ProjectTask.project_id == project_id,
                models.ProjectTask.deleted_at.is_(None),
            )
            .first()
        )
        if not task:
            raise ValueError("Tarea no encontrada en este proyecto")

    log_date = log_in.date or datetime.now(timezone.utc)
    if not hasattr(log_date, "tzinfo") or not log_date.tzinfo:
        log_date = log_date.replace(tzinfo=timezone.utc)

    time_log = models.ProjectTimeLog(
        project_id=project.id,
        task_id=log_in.task_id,
        persona_id=persona_id,
        hours=round(float(log_in.hours), 2),
        date=log_date,
        description=log_in.description,
        is_billable=log_in.is_billable,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(time_log)
    db.commit()
    db.refresh(time_log)

    if time_log.task_id:
        sync_task_time_logs(db, time_log.task_id)

    # Cargar relaciones
    db.query(models.ProjectTimeLog).options(
        selectinload(models.ProjectTimeLog.persona),
        selectinload(models.ProjectTimeLog.task),
    ).filter(models.ProjectTimeLog.id == time_log.id).first()

    return _prepare_time_log_response(time_log)


def get_project_time_logs(
    db: Session,
    project_id: UUID | str,
    task_id: Optional[UUID | str] = None,
    persona_id: Optional[UUID | str] = None,
) -> list[models.ProjectTimeLog]:
    q = (
        db.query(models.ProjectTimeLog)
        .options(
            selectinload(models.ProjectTimeLog.persona),
            selectinload(models.ProjectTimeLog.task),
        )
        .filter(
            models.ProjectTimeLog.project_id == project_id,
            models.ProjectTimeLog.deleted_at.is_(None),
        )
    )
    if task_id:
        q = q.filter(models.ProjectTimeLog.task_id == task_id)
    if persona_id:
        q = q.filter(models.ProjectTimeLog.persona_id == persona_id)

    logs = q.order_by(models.ProjectTimeLog.date.desc(), models.ProjectTimeLog.created_at.desc()).all()
    for time_log in logs:
        _prepare_time_log_response(time_log)
    return logs


def delete_project_time_log(
    db: Session,
    project_id: UUID | str,
    log_id: UUID | str,
) -> bool:
    log = (
        db.query(models.ProjectTimeLog)
        .filter(
            models.ProjectTimeLog.id == log_id,
            models.ProjectTimeLog.project_id == project_id,
            models.ProjectTimeLog.deleted_at.is_(None),
        )
        .first()
    )
    if not log:
        return False

    affected_task_id = log.task_id
    log.deleted_at = datetime.now(timezone.utc)
    db.commit()
    if affected_task_id:
        sync_task_time_logs(db, affected_task_id)
    return True


def get_project_time_tracking_summary(db: Session, project_id: UUID | str) -> dict:
    logs = (
        db.query(models.ProjectTimeLog)
        .options(
            selectinload(models.ProjectTimeLog.persona),
            selectinload(models.ProjectTimeLog.task),
        )
        .filter(
            models.ProjectTimeLog.project_id == project_id,
            models.ProjectTimeLog.deleted_at.is_(None),
        )
        .all()
    )

    total_hours = 0.0
    billable_hours = 0.0

    task_map: dict[str, dict] = {}
    member_map: dict[str, dict] = {}

    for time_log in logs:
        h = float(time_log.hours or 0.0)
        total_hours += h
        if time_log.is_billable:
            billable_hours += h

        # Tarea
        t_id = str(time_log.task_id) if time_log.task_id else "general"
        t_title = time_log.task.title if time_log.task else "General del Proyecto"
        if t_id not in task_map:
            task_map[t_id] = {
                "task_id": t_id,
                "task_title": t_title,
                "total_hours": 0.0,
                "billable_hours": 0.0,
                "logs_count": 0,
            }
        task_map[t_id]["total_hours"] = round(task_map[t_id]["total_hours"] + h, 2)
        if time_log.is_billable:
            task_map[t_id]["billable_hours"] = round(task_map[t_id]["billable_hours"] + h, 2)
        task_map[t_id]["logs_count"] += 1

        # Miembro
        p_id = str(time_log.persona_id)
        p_name = "Miembro"
        p_avatar = None
        if time_log.persona:
            p = time_log.persona
            p_name = getattr(p, "nombre_completo", None) or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip() or "Miembro"
            p_avatar = getattr(p, "foto_url", None)

        if p_id not in member_map:
            member_map[p_id] = {
                "persona_id": p_id,
                "persona_name": p_name,
                "avatar_url": p_avatar,
                "total_hours": 0.0,
                "billable_hours": 0.0,
                "logs_count": 0,
            }
        member_map[p_id]["total_hours"] = round(member_map[p_id]["total_hours"] + h, 2)
        if time_log.is_billable:
            member_map[p_id]["billable_hours"] = round(member_map[p_id]["billable_hours"] + h, 2)
        member_map[p_id]["logs_count"] += 1

    by_task = sorted(task_map.values(), key=lambda t: t["total_hours"], reverse=True)
    by_member = sorted(member_map.values(), key=lambda m: m["total_hours"], reverse=True)

    return {
        "project_id": str(project_id),
        "total_hours": round(total_hours, 2),
        "billable_hours": round(billable_hours, 2),
        "non_billable_hours": round(total_hours - billable_hours, 2),
        "total_logs": len(logs),
        "by_task": by_task,
        "by_member": by_member,
    }


# ---------------------------------------------------------------------------
# PROJECT TEMPLATES & INSTANTIATION (Super-PRO Fase 6)
# ---------------------------------------------------------------------------

def _prepare_template_response(template: models.ProjectTemplate) -> models.ProjectTemplate:
    if not template:
        return template
    if hasattr(template, "creator") and template.creator:
        p = template.creator
        template.creator_name = (
            getattr(p, "nombre_completo", None)
            or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip()
            or "Creador"
        )
    else:
        template.creator_name = "Sistema"
    return template


def get_project_templates(
    db: Session,
    *,
    sede_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> list[models.ProjectTemplate]:
    effective_sede = sede_id if sede_id is not None else user_sede_id
    q = (
        db.query(models.ProjectTemplate)
        .options(selectinload(models.ProjectTemplate.creator))
        .filter(models.ProjectTemplate.deleted_at.is_(None))
    )

    # Axioma 3: Scope multi-tenant para plantillas
    if effective_sede is not None:
        q = q.filter(
            (models.ProjectTemplate.sede_id.is_(None))
            | (models.ProjectTemplate.sede_id == effective_sede)
            | (models.ProjectTemplate.is_public.is_(True))
        )
    else:
        q = q.filter(
            models.ProjectTemplate.sede_id.is_(None)
            | models.ProjectTemplate.is_public.is_(True)
        )

    if category and category != "all":
        q = q.filter(models.ProjectTemplate.category == category)

    if is_public is not None:
        q = q.filter(models.ProjectTemplate.is_public == is_public)

    if search:
        search_term = f"%{search}%"
        q = q.filter(
            models.ProjectTemplate.name.ilike(search_term)
            | models.ProjectTemplate.description.ilike(search_term)
        )

    templates = q.order_by(models.ProjectTemplate.created_at.desc()).all()
    for t in templates:
        _prepare_template_response(t)
    return templates


def get_project_template(
    db: Session,
    template_id: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
) -> Optional[models.ProjectTemplate]:
    effective_sede = sede_id if sede_id is not None else user_sede_id
    q = (
        db.query(models.ProjectTemplate)
        .options(selectinload(models.ProjectTemplate.creator))
        .filter(
            models.ProjectTemplate.id == template_id,
            models.ProjectTemplate.deleted_at.is_(None),
        )
    )
    if effective_sede is not None:
        q = q.filter(
            (models.ProjectTemplate.sede_id.is_(None))
            | (models.ProjectTemplate.sede_id == effective_sede)
            | (models.ProjectTemplate.is_public.is_(True))
        )
    else:
        q = q.filter(
            models.ProjectTemplate.sede_id.is_(None)
            | models.ProjectTemplate.is_public.is_(True)
        )
    template = q.first()
    if template:
        _prepare_template_response(template)
    return template


def create_project_template(
    db: Session,
    template_in: schemas.ProjectTemplateCreate,
    creator_persona_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    *,
    created_by: Optional[UUID | str] = None,
    can_manage_global: bool = False,
) -> models.ProjectTemplate:
    effective_creator = creator_persona_id or created_by
    if sede_id is None and not can_manage_global:
        raise ValueError("projects:manage es obligatorio para crear plantillas globales")
    structure_dict = (
        template_in.structure.model_dump()
        if hasattr(template_in.structure, "model_dump")
        else (template_in.structure or {})
    )

    template = models.ProjectTemplate(
        name=template_in.name,
        description=template_in.description,
        category=template_in.category or "general",
        default_budget=float(template_in.default_budget or 0.0),
        structure=structure_dict,
        created_by=effective_creator,
        is_public=template_in.is_public if template_in.is_public is not None else True,
        # Tenant ownership comes from the authenticated actor, never from the request body.
        sede_id=sede_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    if template.created_by:
        db.query(models.ProjectTemplate).options(
            selectinload(models.ProjectTemplate.creator)
        ).filter(models.ProjectTemplate.id == template.id).first()

    return _prepare_template_response(template)


def update_project_template(
    db: Session,
    template_id: UUID | str,
    template_in: schemas.ProjectTemplateUpdate,
    sede_id: Optional[UUID | str] = None,
    *,
    can_manage_global: bool = False,
) -> Optional[models.ProjectTemplate]:
    template = _get_project_template_for_mutation(db, template_id, sede_id)
    if not template:
        return None
    if template.sede_id is None and not can_manage_global:
        return None

    if template_in.name is not None:
        template.name = template_in.name
    if template_in.description is not None:
        template.description = template_in.description
    if template_in.category is not None:
        template.category = template_in.category
    if template_in.default_budget is not None:
        template.default_budget = float(template_in.default_budget)
    if template_in.structure is not None:
        template.structure = (
            template_in.structure.model_dump()
            if hasattr(template_in.structure, "model_dump")
            else template_in.structure
        )
    if template_in.is_public is not None:
        template.is_public = template_in.is_public

    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)
    return _prepare_template_response(template)


def delete_project_template(
    db: Session,
    template_id: UUID | str,
    sede_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
    *,
    can_manage_global: bool = False,
) -> bool:
    effective_sede = sede_id if sede_id is not None else user_sede_id
    template = _get_project_template_for_mutation(db, template_id, effective_sede)
    if not template:
        return False
    if template.sede_id is None and not can_manage_global:
        return False

    template.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def _get_project_template_for_mutation(
    db: Session,
    template_id: UUID | str,
    sede_id: Optional[UUID | str],
) -> Optional[models.ProjectTemplate]:
    """Resolve templates writable in the actor's tenant; public is read-only cross-tenant."""
    q = db.query(models.ProjectTemplate).filter(
        models.ProjectTemplate.id == template_id,
        models.ProjectTemplate.deleted_at.is_(None),
    )
    if sede_id is not None:
        q = q.filter(
            models.ProjectTemplate.sede_id.is_(None)
            | (models.ProjectTemplate.sede_id == sede_id)
        )
    else:
        q = q.filter(models.ProjectTemplate.sede_id.is_(None))
    return q.first()


def create_project_from_template(
    db: Session,
    template_id: UUID | str,
    payload: schemas.InstantiateProjectFromTemplate,
    *,
    creator_persona_id: Optional[UUID | str] = None,
    created_by: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
) -> models.Project:
    effective_creator = creator_persona_id or created_by
    effective_sede = sede_id or user_sede_id
    template = get_project_template(db, template_id, sede_id=effective_sede)
    if not template:
        raise ValueError("Plantilla no encontrada o sin permisos de acceso")

    if not effective_sede:
        raise ValueError("sede_id es obligatorio para instanciar proyectos (Axioma 3)")

    structure = template.structure or {}
    tasks_data = structure.get("tasks", [])
    phases_data = structure.get("phases", [])

    start_date = payload.start_date or datetime.now(timezone.utc)
    if not hasattr(start_date, "tzinfo") or not start_date.tzinfo:
        start_date = start_date.replace(tzinfo=timezone.utc)

    # Calcular target_date basado en duración máxima de tareas o 30 días
    max_offset = 30
    if tasks_data:
        task_ends = [
            int(t.get("day_offset", 0)) + int(t.get("duration_days", 1))
            for t in tasks_data
        ]
        if task_ends:
            max_offset = max(max_offset, max(task_ends))

    target_date = start_date + timedelta(days=max_offset)

    budget = (
        float(payload.budget_allocated)
        if payload.budget_allocated is not None
        else float(template.default_budget or 0.0)
    )

    project = models.Project(
        title=payload.title,
        description=payload.description or template.description,
        status="planning",
        owner_id=payload.owner_id or effective_creator,
        sede_id=effective_sede,
        budget_allocated=budget,
        budget_spent=0.0,
        start_date=start_date,
        target_date=target_date,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(project)
    db.flush()

    # 1. Crear fases
    phase_order_map: dict[int, models.ProjectPhase] = {}
    phase_name_map: dict[str, models.ProjectPhase] = {}

    if phases_data:
        for idx, p_info in enumerate(phases_data):
            p_order = p_info.get("order_index", p_info.get("order", idx))
            p_title = p_info.get("title") or p_info.get("name") or f"Fase {idx + 1}"
            p_color = p_info.get("color") or "#94a3b8"
            import re
            p_slug = p_info.get("slug") or re.sub(r"[^a-zA-Z0-9_]", "_", p_title.lower())[:20]
            phase = models.ProjectPhase(
                project_id=project.id,
                name=p_title[:50],
                slug=p_slug,
                color=p_color[:20],
                order_index=p_order,
            )
            db.add(phase)
            db.flush()
            phase_order_map[idx] = phase
            phase_name_map[p_title.lower().strip()] = phase
    else:
        # Fases estándar por defecto
        created_phases = create_default_phases(db, project.id)
        for idx, ph in enumerate(created_phases):
            phase_order_map[idx] = ph
            phase_name_map[ph.name.lower().strip()] = ph

    # 2. Crear tareas con cálculo relativo de fechas
    for t_idx, t_info in enumerate(tasks_data):
        offset = int(t_info.get("day_offset", 0))
        duration = max(1, int(t_info.get("duration_days", 1)))
        task_start = start_date + timedelta(days=offset)
        task_due = task_start + timedelta(days=duration)

        # Resolver fase / nodo
        target_phase_name = None
        if t_info.get("phase_name"):
            match = phase_name_map.get(t_info["phase_name"].lower().strip())
            if match:
                target_phase_name = match.name
        elif t_info.get("phase_index") is not None:
            match = phase_order_map.get(t_info["phase_index"])
            if match:
                target_phase_name = match.name
        elif phase_order_map:
            target_phase_name = phase_order_map[0].name

        task = models.ProjectTask(
            project_id=project.id,
            node=target_phase_name,
            title=t_info.get("title") or "Tarea de Plantilla",
            description=t_info.get("description"),
            priority=t_info.get("priority", "medium"),
            status="todo",
            order_index=t_idx,
            start_date=task_start,
            due_date=task_due,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(task)
        db.flush()

        if bool(t_info.get("is_milestone", False)):
            milestone = models.ProjectMilestone(
                project_id=project.id,
                title=task.title,
                target_date=task_due.date(),
                created_at=datetime.now(timezone.utc),
            )
            db.add(milestone)

    # 3. Registrar actividad en bitácora
    activity = models.ProjectActivityLog(
        project_id=project.id,
        persona_id=creator_persona_id,
        action_type="project_created_from_template",
        description=f"Proyecto instanciado desde la plantilla '{template.name}' con {len(tasks_data)} tareas",
        created_at=datetime.now(timezone.utc),
    )
    db.add(activity)

    db.commit()
    db.refresh(project)
    return project


def save_project_as_template(
    db: Session,
    project_id: UUID | str,
    payload: schemas.SaveProjectAsTemplate,
    *,
    creator_persona_id: Optional[UUID | str] = None,
    created_by: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
) -> models.ProjectTemplate:
    effective_creator = creator_persona_id or created_by
    effective_sede = sede_id or user_sede_id
    project = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks),
        )
        .filter(models.Project.id == project_id, models.Project.deleted_at.is_(None))
        .first()
    )
    if not project:
        raise ValueError("Proyecto no encontrado")

    # Axioma 3: Scope check si sede_id proporcionada
    if effective_sede is not None and project.sede_id is not None and str(project.sede_id) != str(effective_sede):
        raise ValueError("Proyecto no encontrado o en sede distinta")

    # Extraer fases
    db_phases = db.query(models.ProjectPhase).filter(
        models.ProjectPhase.project_id == project_id,
        models.ProjectPhase.deleted_at.is_(None)
    ).order_by(models.ProjectPhase.order_index.asc()).all()

    phases_data = [
        {
            "title": p.name,
            "name": p.name,
            "slug": p.slug,
            "color": p.color,
            "order": p.order_index,
            "order_index": p.order_index
        }
        for p in db_phases
    ]

    # Extraer tareas
    active_tasks = [t for t in (project.tasks or []) if not t.deleted_at]
    proj_start = project.start_date or (
        min([t.start_date for t in active_tasks if t.start_date] or [datetime.now(timezone.utc)])
    )
    if not hasattr(proj_start, "tzinfo") or not proj_start.tzinfo:
        proj_start = proj_start.replace(tzinfo=timezone.utc)

    tasks_data = []
    for t in active_tasks:
        day_offset = 0
        if t.start_date:
            t_st = t.start_date if getattr(t.start_date, "tzinfo", None) else t.start_date.replace(tzinfo=timezone.utc)
            day_offset = max(0, (t_st - proj_start).days)

        duration_days = 1
        if t.due_date:
            t_due = t.due_date if getattr(t.due_date, "tzinfo", None) else t.due_date.replace(tzinfo=timezone.utc)
            t_st = (t.start_date if getattr(t.start_date, "tzinfo", None) else t.start_date.replace(tzinfo=timezone.utc)) if t.start_date else proj_start
            duration_days = max(1, (t_due - t_st).days)

        phase_name = t.node

        tasks_data.append({
            "title": t.title,
            "description": t.description,
            "priority": t.priority or "medium",
            "phase_name": phase_name,
            "day_offset": day_offset,
            "duration_days": duration_days,
            "is_milestone": False,
        })

    structure = {
        "phases": phases_data,
        "tasks": tasks_data,
        "default_view": "kanban",
        "tags": [],
    }

    template = models.ProjectTemplate(
        name=payload.name,
        description=payload.description or project.description,
        category=payload.category or "general",
        default_budget=float(project.budget_allocated or 0.0),
        structure=structure,
        created_by=effective_creator,
        is_public=payload.is_public if payload.is_public is not None else True,
        sede_id=project.sede_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    if template.created_by:
        db.query(models.ProjectTemplate).options(
            selectinload(models.ProjectTemplate.creator)
        ).filter(models.ProjectTemplate.id == template.id).first()

    return _prepare_template_response(template)


# ── Project Automations & Triggers (Super-PRO Fase 7) ───────────────────────

def _prepare_automation_response(rule: models.ProjectAutomationRule) -> models.ProjectAutomationRule:
    if getattr(rule, "creator", None):
        c = rule.creator
        rule.creator_name = (
            getattr(c, "nombre_completo", None)
            or f"{getattr(c, 'first_name', '')} {getattr(c, 'last_name', '')}".strip()
            or getattr(c, "email", "Usuario")
        )
    else:
        rule.creator_name = "Sistema"
    return rule


def get_project_automation_rules(
    db: Session,
    project_id: Optional[UUID | str] = None,
    *,
    user_sede_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    is_active: Optional[bool] = None,
    trigger_event: Optional[str] = None,
) -> list[models.ProjectAutomationRule]:
    effective_sede = sede_id if sede_id is not None else user_sede_id
    q = (
        db.query(models.ProjectAutomationRule)
        .options(selectinload(models.ProjectAutomationRule.creator))
        .filter(models.ProjectAutomationRule.deleted_at.is_(None))
    )

    if project_id is not None:
        q = q.filter(
            (models.ProjectAutomationRule.project_id == _to_uuid(project_id))
            | (models.ProjectAutomationRule.project_id.is_(None))
        )

    if effective_sede is not None:
        q = q.filter(
            (models.ProjectAutomationRule.sede_id.is_(None))
            | (models.ProjectAutomationRule.sede_id == _to_uuid(effective_sede))
        )

    if is_active is not None:
        q = q.filter(models.ProjectAutomationRule.is_active.is_(is_active))

    if trigger_event:
        q = q.filter(models.ProjectAutomationRule.trigger_event == trigger_event)

    rules = q.order_by(models.ProjectAutomationRule.created_at.desc()).all()
    for r in rules:
        _prepare_automation_response(r)
    return rules


def get_project_automation_rule(
    db: Session,
    project_id_or_rule_id: Any,
    rule_id: Optional[Any] = None,
    *,
    user_sede_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
) -> Optional[models.ProjectAutomationRule]:
    actual_rule_id = rule_id if rule_id is not None else project_id_or_rule_id
    effective_sede = sede_id if sede_id is not None else user_sede_id
    q = (
        db.query(models.ProjectAutomationRule)
        .options(selectinload(models.ProjectAutomationRule.creator))
        .filter(
            models.ProjectAutomationRule.id == _to_uuid(actual_rule_id),
            models.ProjectAutomationRule.deleted_at.is_(None),
        )
    )
    if effective_sede is not None:
        q = q.filter(
            (models.ProjectAutomationRule.sede_id.is_(None))
            | (models.ProjectAutomationRule.sede_id == _to_uuid(effective_sede))
        )
    rule = q.first()
    if rule:
        _prepare_automation_response(rule)
    return rule


def create_project_automation_rule(
    db: Session,
    project_id_or_rule_in: Any,
    rule_in: Optional[schemas.ProjectAutomationRuleCreate] = None,
    *,
    creator_persona_id: Optional[UUID | str] = None,
    created_by: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
) -> models.ProjectAutomationRule:
    if rule_in is None and hasattr(project_id_or_rule_in, "trigger_event"):
        actual_rule_in = project_id_or_rule_in
    else:
        actual_rule_in = rule_in
        if actual_rule_in and not getattr(actual_rule_in, "project_id", None):
            actual_rule_in.project_id = _to_uuid(project_id_or_rule_in)

    effective_creator = creator_persona_id or created_by
    effective_sede = getattr(actual_rule_in, "sede_id", None) or sede_id or user_sede_id

    # Validar que si tiene project_id, pertenezca a la misma sede
    if actual_rule_in.project_id:
        proj = (
            db.query(models.Project)
            .filter(models.Project.id == _to_uuid(actual_rule_in.project_id), models.Project.deleted_at.is_(None))
            .first()
        )
        if not proj:
            raise ValueError("Proyecto no encontrado")
        if effective_sede is not None and proj.sede_id is not None and str(proj.sede_id) != str(effective_sede):
            raise ValueError("Proyecto no pertenece a la sede especificada (Axioma 3)")

    rule = models.ProjectAutomationRule(
        project_id=_to_uuid(actual_rule_in.project_id) if actual_rule_in.project_id else None,
        name=actual_rule_in.name,
        description=actual_rule_in.description,
        trigger_event=actual_rule_in.trigger_event,
        condition_data=actual_rule_in.condition_data or {},
        action_type=actual_rule_in.action_type,
        action_data=actual_rule_in.action_data or {},
        is_active=actual_rule_in.is_active,
        execution_count=0,
        last_triggered_at=None,
        created_by=_to_uuid(effective_creator) if effective_creator else None,
        sede_id=_to_uuid(effective_sede) if effective_sede else None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    if rule.created_by:
        db.query(models.ProjectAutomationRule).options(
            selectinload(models.ProjectAutomationRule.creator)
        ).filter(models.ProjectAutomationRule.id == rule.id).first()

    return _prepare_automation_response(rule)


def update_project_automation_rule(
    db: Session,
    project_id_or_rule_id: Any,
    rule_id_or_update: Any = None,
    rule_in: Optional[schemas.ProjectAutomationRuleUpdate] = None,
    *,
    user_sede_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    can_manage_global: bool = False,
) -> Optional[models.ProjectAutomationRule]:
    if rule_in is not None:
        actual_rule_id = rule_id_or_update
        actual_rule_in = rule_in
    else:
        actual_rule_id = project_id_or_rule_id
        actual_rule_in = rule_id_or_update

    rule = get_project_automation_rule(db, actual_rule_id, user_sede_id=user_sede_id, sede_id=sede_id)
    if not rule or (rule.project_id is None and not can_manage_global):
        return None

    if actual_rule_in.name is not None:
        rule.name = actual_rule_in.name
    if actual_rule_in.description is not None:
        rule.description = actual_rule_in.description
    if actual_rule_in.trigger_event is not None:
        rule.trigger_event = actual_rule_in.trigger_event
    if actual_rule_in.condition_data is not None:
        rule.condition_data = actual_rule_in.condition_data
    if actual_rule_in.action_type is not None:
        rule.action_type = actual_rule_in.action_type
    if actual_rule_in.action_data is not None:
        rule.action_data = actual_rule_in.action_data
    if actual_rule_in.is_active is not None:
        rule.is_active = actual_rule_in.is_active

    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    return _prepare_automation_response(rule)


def delete_project_automation_rule(
    db: Session,
    project_id_or_rule_id: Any,
    rule_id: Optional[Any] = None,
    *,
    user_sede_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    can_manage_global: bool = False,
) -> bool:
    actual_rule_id = rule_id if rule_id is not None else project_id_or_rule_id
    rule = get_project_automation_rule(db, actual_rule_id, user_sede_id=user_sede_id, sede_id=sede_id)
    if not rule or (rule.project_id is None and not can_manage_global):
        return False

    rule.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def _assert_automation_assignee_in_sede(
    db: Session,
    assignee_id: UUID | str,
    user_sede_id: Optional[UUID | str],
) -> None:
    """Prevent automation rules from creating cross-sede task assignments."""
    if user_sede_id is None:
        return
    persona = (
        db.query(models.Persona)
        .filter(
            models.Persona.id == _to_uuid(assignee_id),
            models.Persona.sede_id == _to_uuid(user_sede_id),
        )
        .first()
    )
    if not persona:
        raise ValueError("Automation assignee not found in actor sede")


def evaluate_project_automations(
    db: Session,
    project_id: UUID | str,
    trigger_event_or_payload: Any = None,
    context: Optional[dict] = None,
    *,
    trigger_event: Optional[str] = None,
    actor_persona_id: Optional[UUID | str] = None,
    user_sede_id: Optional[UUID | str] = None,
    dry_run: bool = True,
) -> list[dict]:
    effective_context = {}
    if hasattr(trigger_event_or_payload, "trigger_event"):
        effective_trigger = trigger_event_or_payload.trigger_event
        if hasattr(trigger_event_or_payload, "context_data") and getattr(trigger_event_or_payload, "context_data", None):
            effective_context.update(trigger_event_or_payload.context_data)
        if hasattr(trigger_event_or_payload, "context") and getattr(trigger_event_or_payload, "context", None):
            effective_context.update(trigger_event_or_payload.context)
        if getattr(trigger_event_or_payload, "task_id", None):
            effective_context["task_id"] = str(trigger_event_or_payload.task_id)
    elif isinstance(trigger_event_or_payload, str):
        effective_trigger = trigger_event_or_payload
        effective_context = dict(context or {})
    else:
        effective_trigger = trigger_event or ""
        effective_context = dict(context or {})

    if effective_trigger == "task_completed":
        effective_context.setdefault("status", "completed")

    rules = get_project_automation_rules(
        db,
        project_id=project_id,
        user_sede_id=user_sede_id,
        is_active=True,
        trigger_event=effective_trigger,
    )

    results = []
    task_id = effective_context.get("task_id")
    task = None
    if task_id:
        task = (
            db.query(models.ProjectTask)
            .filter(
                models.ProjectTask.id == _to_uuid(task_id),
                models.ProjectTask.project_id == _to_uuid(project_id),
                models.ProjectTask.deleted_at.is_(None),
            )
            .first()
        )

    supported_actions = {
        "notify_assignee",
        "reassign_task",
        "change_phase",
        "create_followup_task",
        "set_priority",
    }
    supported_priorities = {"low", "medium", "high", "urgent"}
    task_required_actions = {"reassign_task", "change_phase", "set_priority"}
    for rule in rules:
        action = rule.action_type
        validation_data = rule.action_data or {}
        configuration_error = None
        if not isinstance(validation_data, dict):
            configuration_error = "Los datos de configuración de la acción no son válidos."
        elif action not in supported_actions:
            configuration_error = f"Acción no soportada: {action}"
        elif action == "reassign_task" and not validation_data.get("assignee_id"):
            configuration_error = "La acción requiere assignee_id."
        elif action == "change_phase" and not any(
            isinstance(target, str) and target.strip()
            for target in (validation_data.get("phase_name"), validation_data.get("node"))
        ):
            configuration_error = "La acción requiere phase_name o node."
        elif action == "set_priority" and (
            not isinstance(validation_data.get("priority", "high"), str)
            or validation_data.get("priority", "high") not in supported_priorities
        ):
            configuration_error = "La prioridad de destino no es válida."
        elif action == "create_followup_task" and (
            not isinstance(validation_data.get("priority", "medium"), str)
            or validation_data.get("priority", "medium") not in supported_priorities
        ):
            configuration_error = "La prioridad de la tarea de seguimiento no es válida."

        if configuration_error:
            results.append({
                "rule_id": str(rule.id),
                "rule_name": rule.name,
                "action_type": action,
                "status": "failed",
                "details": configuration_error,
            })
            continue

        if action in task_required_actions and task is None:
            results.append({
                "rule_id": str(rule.id),
                "rule_name": rule.name,
                "action_type": action,
                "status": "failed",
                "details": "Esta acción requiere una tarea activa del proyecto.",
            })
            continue

        cond = rule.condition_data or {}
        # 1. Comprobar condiciones
        matches = True
        if "priority" in cond and cond["priority"]:
            task_priority = getattr(task, "priority", None) if task else effective_context.get("priority")
            if task_priority != cond["priority"]:
                matches = False

        if matches and "status" in cond and cond["status"]:
            task_status = getattr(task, "status", None) if task else effective_context.get("status")
            if task_status != cond["status"]:
                matches = False

        if matches and ("phase_name" in cond or "node" in cond):
            required_node = cond.get("phase_name") or cond.get("node")
            task_node = getattr(task, "node", None) if task else (effective_context.get("phase_name") or effective_context.get("node"))
            if task_node != required_node:
                matches = False

        if not matches:
            results.append({
                "rule_id": str(rule.id),
                "rule_name": rule.name,
                "action_type": rule.action_type,
                "status": "skipped_condition",
                "details": "Condición no satisfecha por el contexto actual",
            })
            continue

        # 2. Ejecutar acción
        action_details = ""
        act_data = rule.action_data or {}
        try:
            if action == "notify_assignee":
                recipient = getattr(task, "assignee_id", None) or effective_context.get("assignee_id") or actor_persona_id
                if recipient:
                    _assert_automation_assignee_in_sede(db, recipient, user_sede_id)
                activity = models.ProjectActivityLog(
                    project_id=_to_uuid(project_id),
                    persona_id=_to_uuid(recipient) if recipient else None,
                    action_type="automation_triggered",
                    description=f"[Automatización] {rule.name}: Notificación emitida para '{getattr(task, 'title', effective_context.get('task_title', 'tarea'))}'",
                    created_at=datetime.now(timezone.utc),
                )
                if not dry_run:
                    db.add(activity)
                action_details = (
                    f"Se generaría una notificación para responsable {recipient}"
                    if dry_run else f"Notificación generada para responsable {recipient}"
                )

            elif action == "reassign_task" and task:
                new_assignee = act_data.get("assignee_id")
                if new_assignee:
                    _assert_automation_assignee_in_sede(db, new_assignee, user_sede_id)
                    if dry_run:
                        action_details = f"Se reasignaría la tarea a {new_assignee}"
                    else:
                        task.assignee_id = _to_uuid(new_assignee)
                        task.updated_at = datetime.now(timezone.utc)
                        activity = models.ProjectActivityLog(
                            project_id=_to_uuid(project_id),
                            persona_id=_to_uuid(actor_persona_id) if actor_persona_id else None,
                            action_type="automation_task_reassigned",
                            description=f"[Automatización] Tarea '{task.title}' reasignada a {new_assignee}",
                            created_at=datetime.now(timezone.utc),
                        )
                        db.add(activity)
                        action_details = f"Tarea reasignada a {new_assignee}"

            elif action == "change_phase" and task:
                target_node = act_data.get("phase_name") or act_data.get("node")
                if target_node:
                    old_node = task.node
                    if dry_run:
                        action_details = f"La tarea se movería de '{old_node}' a '{target_node}'"
                    else:
                        task.node = target_node
                        task.updated_at = datetime.now(timezone.utc)
                        activity = models.ProjectActivityLog(
                            project_id=_to_uuid(project_id),
                            persona_id=_to_uuid(actor_persona_id) if actor_persona_id else None,
                            action_type="automation_phase_changed",
                            description=f"[Automatización] Tarea '{task.title}' movida de '{old_node}' a '{target_node}'",
                            created_at=datetime.now(timezone.utc),
                        )
                        db.add(activity)
                        action_details = f"Tarea movida a fase '{target_node}'"

            elif action == "create_followup_task":
                title = (act_data.get("title") or f"Seguimiento: {rule.name}").strip()
                if len(title) > TASK_TITLE_MAX_LENGTH:
                    raise ValueError(
                        f"El título de la tarea de seguimiento no puede superar "
                        f"{TASK_TITLE_MAX_LENGTH} caracteres"
                    )
                priority = act_data.get("priority", "medium")
                offset_days = int(act_data.get("duration_days", 3))
                start_d = datetime.now(timezone.utc)
                due_d = start_d + timedelta(days=offset_days)
                followup_assignee_id = act_data.get("assignee_id")
                if followup_assignee_id:
                    _assert_automation_assignee_in_sede(db, followup_assignee_id, user_sede_id)
                if dry_run:
                    action_details = f"Se crearía la tarea de seguimiento '{title}' con vencimiento {due_d.date().isoformat()}"
                else:
                    new_task = models.ProjectTask(
                        project_id=_to_uuid(project_id),
                        title=title,
                        description=act_data.get("description", f"Generada automáticamente por regla '{rule.name}'"),
                        status="todo",
                        priority=priority,
                        start_date=start_d,
                        due_date=due_d,
                        node=act_data.get("phase_name") or act_data.get("node"),
                        assignee_id=_to_uuid(followup_assignee_id) if followup_assignee_id else None,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db.add(new_task)
                    db.flush()
                    activity = models.ProjectActivityLog(
                        project_id=_to_uuid(project_id),
                        persona_id=_to_uuid(actor_persona_id) if actor_persona_id else None,
                        action_type="automation_followup_created",
                        description=f"[Automatización] Tarea de seguimiento creada: '{new_task.title}' (id={new_task.id})",
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(activity)
                    action_details = f"Tarea de seguimiento '{new_task.title}' creada con éxito"

            elif action == "set_priority" and task:
                new_prio = act_data.get("priority", "high")
                if dry_run:
                    action_details = f"La prioridad de la tarea cambiaría a {new_prio}"
                else:
                    task.priority = new_prio
                    task.updated_at = datetime.now(timezone.utc)
                    action_details = f"Prioridad de tarea cambiada a {new_prio}"

            else:
                action_details = f"Acción '{action}' completada sin efectos secundarios"

            # 3. Registrar ejecución exitosa
            if not dry_run:
                rule.execution_count = (rule.execution_count or 0) + 1
                rule.last_triggered_at = datetime.now(timezone.utc)

            results.append({
                "rule_id": str(rule.id),
                "rule_name": rule.name,
                "action_type": rule.action_type,
                "status": "would_execute" if dry_run else "executed",
                "details": action_details,
            })
        except Exception as e:
            results.append({
                "rule_id": str(rule.id),
                "rule_name": rule.name,
                "action_type": rule.action_type,
                "status": "failed",
                "details": str(e),
            })

    if not dry_run:
        db.commit()
    return results


# ---------------------------------------------------------------------------
# EXECUTIVE REPORTS & CSV/EXCEL EXPORTS (Super-PRO Fase 8 - FINAL)
# ---------------------------------------------------------------------------

def get_project_executive_report_data(
    db: Session,
    project_id: UUID | str,
    *,
    user_sede_id: Optional[UUID | str] = None,
) -> Optional[dict]:
    """Recopila de manera coherente y centralizada todos los datos para el reporte ejecutivo."""
    project = get_project(db, project_id, sede_id=user_sede_id)
    if not project:
        return None

    # Tareas
    tasks = (
        db.query(models.ProjectTask)
        .options(selectinload(models.ProjectTask.assignee))
        .filter(
            models.ProjectTask.project_id == project.id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .order_by(models.ProjectTask.created_at.asc())
        .all()
    )

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "completed")
    in_progress_tasks = sum(1 for t in tasks if t.status == "in_progress")
    todo_tasks = sum(1 for t in tasks if t.status == "todo")
    blocked_tasks = sum(1 for t in tasks if t.status in ("blocked", "review"))
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    # Resumen financiero
    budget_summary = get_project_budget_summary(db, project.id) or {
        "budget_allocated": float(project.budget_allocated or 0.0),
        "budget_spent": float(project.budget_spent or 0.0),
        "remaining_budget": float(project.budget_allocated or 0.0) - float(project.budget_spent or 0.0),
        "burn_rate_percent": 0.0,
        "total_expenses_count": 0,
        "by_category": {},
    }

    # Resumen RAID
    risks_summary = get_project_risks_summary(db, project.id) or {
        "total_risks": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "risks": [],
    }
    risk_rows = get_project_risks(db, project.id)
    executive_risks = {
        **risks_summary,
        "project_id": str(project.id),
        "risks": [
            {
                "id": str(risk.id),
                "title": risk.title,
                "category": risk.category or "tecnico",
                "probability": risk.probability,
                "impact": risk.impact,
                "severity": (risk.probability or 1) * (risk.impact or 1),
                "status": risk.status,
                "mitigation_plan": risk.mitigation_plan,
            }
            for risk in risk_rows
        ],
    }

    # Ruta Crítica CPM
    cpm_summary = calculate_critical_path(db, project.id) or {
        "total_duration_days": 0,
        "critical_tasks_count": 0,
        "critical_path_task_ids": [],
        "tasks": [],
    }

    # Tiempos
    time_summary = get_project_time_tracking_summary(db, project.id) or {
        "total_hours": 0.0,
        "billable_hours": 0.0,
        "non_billable_hours": 0.0,
        "total_logs": 0,
        "by_task": [],
        "by_member": [],
    }

    # Fases
    phases = (
        db.query(models.ProjectPhase)
        .filter(
            models.ProjectPhase.project_id == project.id,
            models.ProjectPhase.deleted_at.is_(None),
        )
        .order_by(models.ProjectPhase.order_index.asc())
        .all()
    )
    phase_data = []
    for ph in phases:
        ph_tasks = [t for t in tasks if t.node == ph.name or t.node == str(ph.id)]
        ph_comp = sum(1 for t in ph_tasks if t.status == "completed")
        phase_data.append({
            "id": str(ph.id),
            "name": ph.name,
            "order_index": ph.order_index,
            "total_tasks": len(ph_tasks),
            "completed_tasks": ph_comp,
            "progress_percent": round((ph_comp / len(ph_tasks) * 100), 1) if ph_tasks else 0.0,
        })

    # Creador / Propietario
    owner_name = "Sin asignar"
    if project.owner:
        p = project.owner
        owner_name = getattr(p, "nombre_completo", None) or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip() or "Líder"

    from backend.services.project_evm_service import build_project_execution_matrix, calculate_project_evm

    execution_matrix = build_project_execution_matrix(db, project)
    rolled_progress_pct = float(
        execution_matrix.get("rollup_hierarchy", {}).get("overall_progress_pct", completion_rate)
    )
    eff_progress_pct = (
        float(getattr(project, "manual_progress", 0.0) or 0.0)
        if project.progress_mode == "manual"
        else rolled_progress_pct
    )

    kpis_list = get_project_kpis(db, project.id)
    indicators_list = get_project_indicators(db, project.id, sede_id=user_sede_id)

    # Resumen 360° de los 6 Submódulos de Control Operativo
    evm_summary = calculate_project_evm(db, project) or {}
    baselines_rows = (
        db.query(models.ProjectBaseline)
        .filter(
            models.ProjectBaseline.project_id == project.id,
            models.ProjectBaseline.deleted_at.is_(None),
        )
        .order_by(models.ProjectBaseline.created_at.desc())
        .all()
    )
    baseline_block = {
        "has_active_baseline": bool(evm_summary.get("has_baseline", False)),
        "baseline_id": evm_summary.get("baseline_id"),
        "baseline_name": evm_summary.get("baseline_name"),
        "baseline_bac": (
            round(float(evm_summary["baseline_bac"]), 2)
            if evm_summary.get("baseline_bac") is not None
            else None
        ),
        "baseline_variance_cost": round(float(evm_summary.get("baseline_variance_cost") or 0.0), 2),
        "baseline_variance_schedule": round(float(evm_summary.get("baseline_variance_schedule") or 0.0), 1),
        "snapshots_count": len(baselines_rows),
    }

    task_ids = [t.id for t in tasks if getattr(t, "id", None) is not None]
    supplies_rows = (
        db.query(models.TaskSupply)
        .filter(
            models.TaskSupply.task_id.in_(task_ids),
            models.TaskSupply.deleted_at.is_(None),
        )
        .all()
        if task_ids
        else []
    )
    delivered_statuses = {"ready", "received", "delivered", "approved", "purchased", "paid", "completed"}
    delivered_supplies_count = sum(
        1 for s in supplies_rows if str(getattr(s, "status", "") or "").lower() in delivered_statuses
    )
    total_supplies_cost = round(
        sum(float(getattr(s, "total_cost", 0.0) or 0.0) for s in supplies_rows), 2
    )
    project_expenses_rows = (
        db.query(models.ProjectExpense)
        .filter(
            models.ProjectExpense.project_id == project.id,
            models.ProjectExpense.deleted_at.is_(None),
        )
        .all()
    )
    auto_expenses = [
        e
        for e in project_expenses_rows
        if bool(getattr(e, "is_auto_generated", False) or (e.description and "[supply_id:" in str(e.description)))
    ]
    supplies_block = {
        "total_supplies_count": len(supplies_rows),
        "delivered_supplies_count": delivered_supplies_count,
        "total_supplies_cost": total_supplies_cost,
        "auto_generated_expenses_count": len(auto_expenses),
        "auto_generated_expenses_total": round(sum(float(e.amount or 0.0) for e in auto_expenses), 2),
    }

    all_t_ids = {str(t.id) for t in tasks if getattr(t, "id", None) is not None}
    parent_t_ids = {
        str(t.parent_id)
        for t in tasks
        if getattr(t, "parent_id", None)
        and str(t.parent_id) in all_t_ids
        and str(t.parent_id) != str(t.id)
    }
    leaf_tasks = [t for t in tasks if str(t.id) not in parent_t_ids] or list(tasks)
    estimated_hours_total = round(
        sum(float(getattr(t, "estimated_hours", 0.0) or 0.0) for t in leaf_tasks), 2
    )
    total_logged_hours = round(float(time_summary.get("total_hours", 0.0) or 0.0), 2)
    hours_utilization_pct = (
        round((total_logged_hours / estimated_hours_total) * 100.0, 1)
        if estimated_hours_total > 0.0
        else (100.0 if total_logged_hours > 0.0 else 0.0)
    )
    time_tracking_block = {
        "logs_count": int(time_summary.get("total_logs", 0) or 0),
        "billable_hours": round(float(time_summary.get("billable_hours", 0.0) or 0.0), 2),
        "non_billable_hours": round(float(time_summary.get("non_billable_hours", 0.0) or 0.0), 2),
        "total_logged_hours": total_logged_hours,
        "estimated_hours_total": estimated_hours_total,
        "hours_utilization_pct": hours_utilization_pct,
    }

    workload_data = get_project_workload(db, project.id) or {}
    wl_members = [
        m
        for m in (workload_data.get("members") or [])
        if m.get("persona_id") is not None and int(m.get("total_tasks", 0) or 0) > 0
    ]
    if wl_members:
        m_hours_utils = [float(m.get("hours_utilization_pct", 0.0) or 0.0) for m in wl_members]
        m_wl_pcts = [float(m.get("workload_percent", 0.0) or 0.0) for m in wl_members]
        avg_utilization_pct = (
            round(sum(m_hours_utils) / len(wl_members), 1)
            if any(u > 0.0 for u in m_hours_utils)
            else round(sum(m_wl_pcts) / len(wl_members), 1)
        )
    else:
        avg_utilization_pct = 0.0
    workload_block = {
        "members_with_tasks_count": len(wl_members),
        "overloaded_members_count": int(workload_data.get("overloaded_members_count", 0) or 0),
        "avg_utilization_pct": avg_utilization_pct,
    }

    crit_ids = {str(cid) for cid in (cpm_summary.get("critical_path_task_ids") or [])}
    critical_tasks_count = int(cpm_summary.get("critical_tasks_count", len(crit_ids)) or 0)
    critical_completed_count = sum(
        1
        for t in tasks
        if (str(t.id) in crit_ids or bool(getattr(t, "is_critical", False)))
        and getattr(t, "status", None) in ("completed", "done")
    )
    dependencies_count = (
        db.query(models.ProjectTaskDependency)
        .filter(
            models.ProjectTaskDependency.project_id == project.id,
            models.ProjectTaskDependency.deleted_at.is_(None),
        )
        .count()
    )
    cpm_block = {
        "critical_tasks_count": critical_tasks_count,
        "critical_completed_count": critical_completed_count,
        "dependencies_count": dependencies_count,
    }

    automation_rules = (
        db.query(models.ProjectAutomationRule)
        .filter(
            models.ProjectAutomationRule.project_id == project.id,
            models.ProjectAutomationRule.deleted_at.is_(None),
        )
        .all()
    )
    automations_block = {
        "total_rules_count": len(automation_rules),
        "active_rules_count": sum(1 for r in automation_rules if bool(r.is_active)),
        "total_executions_count": sum(int(r.execution_count or 0) for r in automation_rules),
    }

    submodules_summary = {
        "baseline": baseline_block,
        "supplies": supplies_block,
        "time_tracking": time_tracking_block,
        "workload": workload_block,
        "cpm": cpm_block,
        "automations": automations_block,
    }

    from backend.services.project_lifecycle_pmi_service import build_governance_summary

    governance_summary = build_governance_summary(db, project.id)

    from backend.services.project_ccb_service import get_project_ccb_and_quality_summary

    ccb_quality_summary = get_project_ccb_and_quality_summary(db, project.id)

    return {
        "project": {
            "id": str(project.id),
            "title": project.title,
            "description": project.description or "Sin descripción detallada",
            "status": project.status,
            "priority": getattr(project, "priority", None) or "medium",
            "health_override": project.health_override,
            "progress_mode": project.progress_mode,
            "progress_percentage": eff_progress_pct,
            "budget_allocated": float(project.budget_allocated or 0.0),
            "budget_spent": float(project.budget_spent or 0.0),
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "target_date": project.target_date.isoformat() if project.target_date else None,
            "owner_name": owner_name,
            "sede_id": str(project.sede_id) if project.sede_id else None,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        },
        "tasks_metrics": {
            "total": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_progress_tasks,
            "todo": todo_tasks,
            "blocked": blocked_tasks,
            "completion_rate": completion_rate,
        },
        "financial_kpis": budget_summary,
        "cpi_stability_rule": budget_summary.get("cpi_stability_rule"),
        "early_warning_sentinel": budget_summary.get("early_warning_sentinel"),
        "raid_kpis": executive_risks,
        "cpm_metrics": cpm_summary,
        "time_metrics": time_summary,
        "phases": phase_data,
        "execution_matrix": execution_matrix,
        "submodules_summary": submodules_summary,
        "governance_summary": governance_summary,
        "kpis": kpis_list,
        "indicators": indicators_list,
        "ccb_and_quality_summary": ccb_quality_summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organization": "Comunidad Cristiana El Faro - Dirección de Proyectos",
    }


def generate_project_summary_pdf(
    report_data: dict | Session,
    project_id: Optional[UUID | str] = None,
    *,
    user_sede_id: Optional[UUID | str] = None,
) -> bytes:
    """Genera un informe ejecutivo PDF profesional con membrete CCF y ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    if not isinstance(report_data, dict):
        if project_id is None:
            raise ValueError("project_id es obligatorio cuando se invoca con sesión de base de datos")
        report_data = (
            get_project_executive_report_data(report_data, project_id, user_sede_id=user_sede_id)
            or {}
        )

    def safe_text(value: Any) -> str:
        """Render project-controlled fields as text, never as ReportLab markup."""
        return escape_xml_text(str(value if value is not None else ""))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        pageCompression=0,
    )

    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'CCFHeader',
        parent=styles['Normal'],
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#1E3A8A'),
        fontName='Helvetica-Bold',
        alignment=1,
    )
    sub_header_style = ParagraphStyle(
        'CCFSubHeader',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#4B5563'),
        fontName='Helvetica',
        alignment=1,
    )
    section_title_style = ParagraphStyle(
        'CCFSectionTitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1E3A8A'),
        fontName='Helvetica-Bold',
        spaceBefore=7,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        'CCFBody',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1F2937'),
        fontName='Helvetica',
    )
    body_bold = ParagraphStyle(
        'CCFBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold',
    )
    cell_style = ParagraphStyle(
        'CCFCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1F2937'),
    )
    cell_header = ParagraphStyle(
        'CCFCellHeader',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=1,
    )

    story = []

    # 1. Membrete
    story.append(Paragraph("COMUNIDAD CRISTIANA EL FARO", header_style))
    story.append(Paragraph("DIRECCIÓN DE PROYECTOS Y GESTIÓN MINISTERIAL • INFORME EJECUTIVO", sub_header_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceBefore=2, spaceAfter=8))

    proj = report_data.get("project", {})
    t_met = report_data.get("tasks_metrics", {})
    f_kpi = report_data.get("financial_kpis", {})
    r_kpi = report_data.get("raid_kpis", {})
    cpm = report_data.get("cpm_metrics", {})
    time_met = report_data.get("time_metrics", {})
    exec_mat = report_data.get("execution_matrix") or {}

    # 2. Ficha Técnica del Proyecto
    meta_table_data = [
        [
            Paragraph("<b>Proyecto:</b>", body_bold),
            Paragraph(f"<b>{safe_text(proj.get('title', 'Sin Título'))}</b>", body_bold),
            Paragraph("<b>Estado:</b>", body_bold),
            Paragraph(safe_text(proj.get('status', 'N/A')).upper(), body_style),
        ],
        [
            Paragraph("<b>Líder / Propietario:</b>", body_style),
            Paragraph(safe_text(proj.get('owner_name', 'No asignado')), body_style),
            Paragraph("<b>Salud:</b>", body_style),
            Paragraph(safe_text(proj.get('health_override', 'Normal')).capitalize(), body_style),
        ],
        [
            Paragraph("<b>Fecha Inicio:</b>", body_style),
            Paragraph(str(proj.get('start_date') or 'No definida')[:10], body_style),
            Paragraph("<b>Fecha Objetivo:</b>", body_style),
            Paragraph(str(proj.get('target_date') or 'No definida')[:10], body_style),
        ],
        [
            Paragraph("<b>Avance General:</b>", body_style),
            Paragraph(f"<b>{proj.get('progress_percentage', 0.0)}%</b>", body_bold),
            Paragraph("<b>Fecha Emisión:</b>", body_style),
            Paragraph(safe_text(report_data.get('generated_at', ''))[:19].replace('T', ' ') + " UTC", body_style),
        ],
    ]
    meta_table = Table(meta_table_data, colWidths=[100, 170, 90, 180])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # 3. Tarjetas KPI de Resumen Ejecutivo
    story.append(Paragraph("RESUMEN DE INDICADORES CLAVE (KPIS)", section_title_style))
    kpi_table_data = [
        [
            Paragraph("<b>AVANCE PONDERADO</b>", cell_header),
            Paragraph("<b>PRESUPUESTO EJECUTADO</b>", cell_header),
            Paragraph("<b>RIESGOS CRÍTICOS</b>", cell_header),
            Paragraph("<b>DURACIÓN CRÍTICA</b>", cell_header),
            Paragraph("<b>HORAS TOTALES</b>", cell_header),
        ],
        [
            Paragraph(f"<font size=11><b>{proj.get('progress_percentage', t_met.get('completion_rate', 0.0))}%</b></font><br/>{t_met.get('completed', 0)}/{t_met.get('total', 0)} Tareas", cell_style),
            Paragraph(f"<font size=11><b>${f_kpi.get('budget_spent', 0.0):,.2f}</b></font><br/>de ${f_kpi.get('budget_allocated', 0.0):,.2f}", cell_style),
            Paragraph(f"<font size=11 color='#DC2626'><b>{r_kpi.get('critical_count', 0)}</b></font><br/>de {r_kpi.get('total_risks', 0)} Riesgos", cell_style),
            Paragraph(f"<font size=11><b>{cpm.get('total_duration_days', 0)}d</b></font><br/>{cpm.get('critical_tasks_count', 0)} Tareas Ruta", cell_style),
            Paragraph(f"<font size=11><b>{time_met.get('total_hours', 0.0)}h</b></font><br/>{time_met.get('billable_hours', 0.0)}h Facturable", cell_style),
        ]
    ]
    kpi_table = Table(kpi_table_data, colWidths=[108, 108, 108, 108, 108])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 8))

    # 3b. Balance de los 3 Frentes de Ejecución y Tributación EDT (si está disponible)
    frentes = exec_mat.get("frentes") or {}
    ft = frentes.get("tiempo") or exec_mat.get("frente_tiempo") or {}
    ff = frentes.get("financiero") or exec_mat.get("frente_financiero") or {}
    fc = frentes.get("cruce_evm") or exec_mat.get("frente_cruce_evm") or {}

    if ft or ff or fc:
        story.append(Paragraph("BALANCE INTEGRAL DE LOS 3 FRENTES DE EJECUCIÓN (PMI / EVM)", section_title_style))
        frentes_table_data = [
            [
                Paragraph("<b>FRENTE TIEMPO (CRONOGRAMA)</b>", cell_header),
                Paragraph("<b>FRENTE FINANCIERO (PRESUPUESTO)</b>", cell_header),
                Paragraph("<b>FRENTE CRUCE EVM (TIEMPO × COSTO)</b>", cell_header),
            ],
            [
                Paragraph(
                    f"<b>Avance Físico:</b> {ft.get('progress_pct', ft.get('time_progress_pct', 0.0))}%<br/>"
                    f"<b>SPI / SPI(t):</b> {ft.get('spi', 1.0)} / {ft.get('spi_t', 1.0)}<br/>"
                    f"<b>Tiempo Ganado (ES):</b> {ft.get('earned_schedule_days', 0.0)}d de {ft.get('planned_duration_days', 0.0)}d<br/>"
                    f"<b>Eficiencia Horas:</b> {ft.get('hours_efficiency_pct', 100.0)}% ({ft.get('actual_hours', 0.0)}h / {ft.get('estimated_hours', ft.get('total_estimated_hours', 0.0))}h)",
                    cell_style,
                ),
                Paragraph(
                    f"<b>Presupuesto (BAC):</b> ${ff.get('bac', 0.0):,.2f}<br/>"
                    f"<b>Costo Real (AC):</b> ${ff.get('ac', 0.0):,.2f} ({ff.get('burn_rate_pct', ff.get('financial_execution_pct', 0.0))}%)<br/>"
                    f"<b>Remanente:</b> ${ff.get('remaining_budget', ff.get('available_budget', 0.0)):,.2f}<br/>"
                    f"<b>Regla 100% EDT:</b> {ff.get('budget_100_rule', {}).get('allocation_percentage', 0.0)}%",
                    cell_style,
                ),
                Paragraph(
                    f"<b>Valor Ganado (EV):</b> ${fc.get('ev', 0.0):,.2f} (PV: ${fc.get('pv', 0.0):,.2f})<br/>"
                    f"<b>CPI (Costo) / CR:</b> {fc.get('cpi', 1.0)} / {fc.get('cr', 1.0)}<br/>"
                    f"<b>Brecha Físico-Financiera:</b> {fc.get('balance_gap_pct', 0.0)}%<br/>"
                    f"<b>Salud EVM:</b> {safe_text(fc.get('health_status', 'OPTIMO'))}",
                    cell_style,
                ),
            ],
        ]
        frentes_table = Table(frentes_table_data, colWidths=[180, 180, 180])
        frentes_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(frentes_table)
        story.append(Spacer(1, 6))

    edt_comps = exec_mat.get("rollup_hierarchy", {}).get("components") or []
    if edt_comps:
        story.append(Paragraph("TRIBUTACIÓN JERÁRQUICA EDT (SUBTAREAS → ACTIVIDADES → COMPONENTES → PROYECTO)", section_title_style))
        edt_rows = [
            [
                Paragraph("<b>Componente EDT</b>", cell_header),
                Paragraph("<b>Presupuesto / Peso</b>", cell_header),
                Paragraph("<b>Avance Físico</b>", cell_header),
                Paragraph("<b>Ejec. Financiera</b>", cell_header),
                Paragraph("<b>CPI / SPI</b>", cell_header),
            ]
        ]
        for comp in edt_comps[:8]:
            c_code = safe_text(comp.get("code") or "EDT")
            c_name = safe_text(comp.get("name") or "Componente")
            c_bac = float(comp.get("budget_allocated") or 0.0)
            c_weight = float(comp.get("budget_weight_pct", comp.get("weight_pct", 0.0)))
            c_phys = float(comp.get("physical_progress_pct") or 0.0)
            c_fin = float(comp.get("financial_progress_pct") or 0.0)
            c_cpi = float(comp.get("cpi") or 1.0)
            c_spi = float(comp.get("spi") or 1.0)
            edt_rows.append([
                Paragraph(f"<b>[{c_code}]</b> {c_name}", cell_style),
                Paragraph(f"${c_bac:,.2f} ({c_weight}%)", cell_style),
                Paragraph(f"<b>{c_phys}%</b> ({comp.get('activities_count', 0)} act.)", cell_style),
                Paragraph(f"{c_fin}% (${float(comp.get('ac') or 0.0):,.2f})", cell_style),
                Paragraph(f"CPI {c_cpi} • SPI {c_spi}", cell_style),
            ])
        edt_table = Table(edt_rows, colWidths=[170, 110, 90, 90, 80])
        edt_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(edt_table)
        story.append(Spacer(1, 6))

    pro_fams = exec_mat.get("pro_families") or list((exec_mat.get("familias_pro") or {}).values())
    if pro_fams:
        story.append(Paragraph("MATRIZ DE LAS 6 FAMILIAS DE INDICADORES PRO", section_title_style))
        fam_rows = [
            [
                Paragraph("<b>Código / Familia Pro</b>", cell_header),
                Paragraph("<b>Frente</b>", cell_header),
                Paragraph("<b>Actual / Meta</b>", cell_header),
                Paragraph("<b>SPI</b>", cell_header),
            ]
        ]
        for fam in pro_fams[:6]:
            f_code = safe_text(fam.get("code") or "PRO")
            f_title = safe_text(fam.get("title") or fam.get("name") or "Indicador")
            f_frente = safe_text(fam.get("frente") or "tiempo").upper()
            f_curr = fam.get("current_value", 0.0)
            f_targ = fam.get("target_value", 100.0)
            f_unit = safe_text(fam.get("unit") or "%")
            f_spi = fam.get("spi", 1.0)
            fam_rows.append([
                Paragraph(f"<b>{f_code}</b> — {f_title}", cell_style),
                Paragraph(f_frente, cell_style),
                Paragraph(f"<b>{f_curr}</b> / {f_targ} {f_unit}", cell_style),
                Paragraph(f"<b>{f_spi}</b>", cell_style),
            ])
        fam_table = Table(fam_rows, colWidths=[240, 80, 130, 90])
        fam_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(fam_table)
        story.append(Spacer(1, 6))

    # 3c. Control Integrado de Cambios (CCB), Aceptación DoD y Costo de Calidad (CoQ) — PMI Vol. 6 §4-§5
    ccb = report_data.get("ccb_and_quality_summary") or {}
    if ccb:
        story.append(Paragraph("CONTROL INTEGRADO DE CAMBIOS (CCB), ACEPTACIÓN DO D Y COSTO DE CALIDAD (COQ)", section_title_style))
        cr_by_cat = ccb.get("coq_by_category") or {}
        ccb_text = (
            f"<b>Solicitudes de Cambio:</b> {ccb.get('total_change_requests', 0)} totales — "
            f"Pendientes CCB: {ccb.get('pending_ccb_count', 0)} | Aprobadas: {ccb.get('approved_count', 0)} | Rechazadas: {ccb.get('rejected_count', 0)}<br/>"
            f"<b>Impacto Neto Aprobado:</b> ${ccb.get('net_approved_cost_delta', 0.0):,.2f} (BAC) y "
            f"{ccb.get('net_approved_schedule_days', 0)} días (cronograma) — Re-baseline automático con acta del Comité.<br/>"
            f"<b>Entregables Aceptados (DoD 4/4):</b> {ccb.get('tasks_dod_accepted_count', 0)}<br/>"
            f"<b>Costo de Calidad (CoQ) Total:</b> ${ccb.get('total_coq_cost', 0.0):,.2f} — "
            f"Prevención: ${cr_by_cat.get('prevention', 0.0):,.2f} | Evaluación: ${cr_by_cat.get('appraisal', 0.0):,.2f} | "
            f"Falla Interna: ${cr_by_cat.get('internal_failure', 0.0):,.2f} | Falla Externa: ${cr_by_cat.get('external_failure', 0.0):,.2f}"
        )
        story.append(Paragraph(ccb_text, body_style))
        story.append(Spacer(1, 6))

    # 4. Control Presupuestario y Estructura Canónica de Reservas (EMV / PMI Vol. 5 y 6)
    story.append(Paragraph("CONTROL PRESUPUESTARIO, RESERVAS EMV Y EARLY WARNING SENTINEL", section_title_style))
    by_cat = f_kpi.get("by_category", {})
    cat_text = ", ".join([f"{safe_text(k).capitalize()}: ${v:,.2f}" for k, v in by_cat.items()]) or "Sin partidas registradas"
    rem_budget = f_kpi.get('remaining_budget', 0.0)
    burn_pct = f_kpi.get('burn_rate_percent', 0.0)
    wp_budget = float(f_kpi.get('work_packages_budget') or ff.get('work_packages_budget') or f_kpi.get('budget_allocated', 0.0))
    cont_res = float(f_kpi.get('contingency_reserve') or ff.get('contingency_reserve') or 0.0)
    mgmt_res = float(f_kpi.get('management_reserve') or ff.get('management_reserve') or 0.0)
    tot_proj_budget = float(f_kpi.get('total_project_budget') or ff.get('total_project_budget') or (float(f_kpi.get('budget_allocated', 0.0)) + mgmt_res))
    cpi_rule = f_kpi.get('cpi_stability_rule') or report_data.get('cpi_stability_rule') or fc.get('cpi_stability_rule') or {}
    sentinel = f_kpi.get('early_warning_sentinel') or report_data.get('early_warning_sentinel') or fc.get('early_warning_sentinel') or {}
    fin_text = (
        f"<b>Asignado (BAC):</b> ${f_kpi.get('budget_allocated', 0.0):,.2f} | "
        f"<b>Gastado:</b> ${f_kpi.get('budget_spent', 0.0):,.2f} ({burn_pct}%) | "
        f"<b>Disponible:</b> ${rem_budget:,.2f}<br/>"
        f"<b>Estructura de Reservas (PMI Vol. 6):</b> Paquetes de Trabajo: ${wp_budget:,.2f} • "
        f"Reserva Contingencia (EMV): ${cont_res:,.2f} • "
        f"Reserva Gestión: ${mgmt_res:,.2f} • "
        f"<b>Presupuesto Total:</b> ${tot_proj_budget:,.2f}<br/>"
        f"<b>Regla 15% Estabilidad CPI:</b> {'Bloqueada (≥15%)' if cpi_rule.get('is_locked') else 'En calibración (<15%)'} "
        f"(Rango EAC: ${float(cpi_rule.get('eac_floor') or 0.0):,.2f} – ${float(cpi_rule.get('eac_ceiling') or 0.0):,.2f})<br/>"
        f"<b>Early Warning Sentinel:</b> [{safe_text(sentinel.get('level', 'OPTIMO'))}] "
        f"{safe_text(sentinel.get('label', 'Ejecución dentro de parámetros'))}<br/>"
        f"<b>Desglose por Categoría:</b> {cat_text}"
    )
    story.append(Paragraph(fin_text, body_style))
    story.append(Spacer(1, 6))

    # 5. Matriz RAID (Riesgos y Supuestos)
    story.append(Paragraph("MATRIZ RAID — RIESGOS E INCIDENCIAS CLAVE", section_title_style))
    risks = r_kpi.get("risks", [])
    if risks:
        top_risks = sorted(risks, key=lambda r: (r.get("probability", 1) * r.get("impact", 1)), reverse=True)[:4]
        risk_table_data = [
            [
                Paragraph("<b>Riesgo / Título</b>", cell_header),
                Paragraph("<b>Cat.</b>", cell_header),
                Paragraph("<b>Severidad</b>", cell_header),
                Paragraph("<b>Plan de Mitigación</b>", cell_header),
            ]
        ]
        for r in top_risks:
            sev = (r.get("probability") or 1) * (r.get("impact") or 1)
            sev_color = "#DC2626" if sev >= 15 else ("#D97706" if sev >= 10 else "#16A34A")
            risk_table_data.append([
                Paragraph(safe_text(r.get("title", "")), cell_style),
                Paragraph(safe_text(r.get("category", "tech")), cell_style),
                Paragraph(f"<font color='{sev_color}'><b>{sev}/25</b></font>", cell_style),
                Paragraph(safe_text(r.get("mitigation_plan") or "En evaluación"), cell_style),
            ])
        risk_table = Table(risk_table_data, colWidths=[180, 60, 60, 240])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(risk_table)
    else:
        story.append(Paragraph("<i>No se han registrado riesgos para este proyecto.</i>", body_style))
    story.append(Spacer(1, 6))

    # 6. Cronograma y Ruta Crítica CPM
    story.append(Paragraph("CRONOGRAMA Y RUTA CRÍTICA (CPM)", section_title_style))
    cpm_tasks = cpm.get("tasks", [])
    crit_tasks = [t for t in cpm_tasks if t.get("is_critical")]
    crit_names = ", ".join([safe_text(t.get("title", "")) for t in crit_tasks]) or "Ninguna tarea crítica calculada"
    cpm_text = (
        f"<b>Duración Total Estimada:</b> {cpm.get('total_duration_days', 0)} días calendario.<br/>"
        f"<b>Tareas en Ruta Crítica (Holgura Cero):</b> {crit_names}"
    )
    story.append(Paragraph(cpm_text, body_style))
    story.append(Spacer(1, 6))

    # 7. Tiempos y Hojas de Horas
    story.append(Paragraph("REGISTRO DE HORAS Y ESFUERZO", section_title_style))
    by_mem = time_met.get("by_member", [])
    if by_mem:
        mem_str = ", ".join([f"{safe_text(m.get('persona_name'))}: {m.get('total_hours')}h ({m.get('billable_hours')}h fact.)" for m in by_mem[:5]])
    else:
        mem_str = "Sin horas registradas en hoja de tiempos"
    time_text = (
        f"<b>Total Horas Invertidas:</b> {time_met.get('total_hours', 0.0)} horas "
        f"({time_met.get('billable_hours', 0.0)}h facturables, {time_met.get('non_billable_hours', 0.0)}h internas).<br/>"
        f"<b>Participación de Equipo:</b> {mem_str}"
    )
    story.append(Paragraph(time_text, body_style))
    story.append(Spacer(1, 6))

    # 7b. Estado de Submódulos de Control Operativo (360°)
    sub_sum = report_data.get("submodules_summary") or {}
    sub_base = sub_sum.get("baseline") or {}
    sub_sup = sub_sum.get("supplies") or {}
    sub_time = sub_sum.get("time_tracking") or {}
    sub_wl = sub_sum.get("workload") or {}
    sub_cpm = sub_sum.get("cpm") or {}
    sub_auto = sub_sum.get("automations") or {}

    story.append(
        Paragraph(
            "Estado de Submódulos de Control Operativo (Línea Base, Insumos, Horas, Carga, Ruta Crítica y Automatizaciones)",
            section_title_style,
        )
    )
    base_status_txt = (
        f"Activa: {safe_text(sub_base.get('baseline_name') or 'Línea Base')} "
        f"(BAC: ${float(sub_base.get('baseline_bac') or 0.0):,.2f} | "
        f"Var Costo: ${float(sub_base.get('baseline_variance_cost') or 0.0):,.2f} | "
        f"Var Cronog.: {float(sub_base.get('baseline_variance_schedule') or 0.0)}%)"
        if sub_base.get("has_active_baseline")
        else f"Sin línea base activa ({int(sub_base.get('snapshots_count') or 0)} snapshots)"
    )
    submodules_table_data = [
        [
            Paragraph("<b>Submódulo Operativo</b>", cell_header),
            Paragraph("<b>Indicadores de Ejecución Real</b>", cell_header),
        ],
        [
            Paragraph("<b>1. Línea Base EVM</b>", cell_style),
            Paragraph(
                f"{base_status_txt} • Snapshots: {int(sub_base.get('snapshots_count') or 0)}",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>2. Suministros e Insumos</b>", cell_style),
            Paragraph(
                f"Insumos: {int(sub_sup.get('delivered_supplies_count') or 0)}/{int(sub_sup.get('total_supplies_count') or 0)} entregados • "
                f"Costo Insumos: ${float(sub_sup.get('total_supplies_cost') or 0.0):,.2f} • "
                f"Gastos Auto-generados (AC): {int(sub_sup.get('auto_generated_expenses_count') or 0)} "
                f"(${float(sub_sup.get('auto_generated_expenses_total') or 0.0):,.2f})",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>3. Hojas de Tiempo (TimeTracking)</b>", cell_style),
            Paragraph(
                f"Registros: {int(sub_time.get('logs_count') or 0)} • "
                f"Horas Registradas: {float(sub_time.get('total_logged_hours') or 0.0)}h "
                f"({float(sub_time.get('billable_hours') or 0.0)}h fact. / {float(sub_time.get('non_billable_hours') or 0.0)}h no fact.) • "
                f"Estimadas: {float(sub_time.get('estimated_hours_total') or 0.0)}h "
                f"({float(sub_time.get('hours_utilization_pct') or 0.0)}%)",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>4. Carga de Equipo (Workload)</b>", cell_style),
            Paragraph(
                f"Miembros con tareas: {int(sub_wl.get('members_with_tasks_count') or 0)} • "
                f"Sobrecargados: {int(sub_wl.get('overloaded_members_count') or 0)} • "
                f"Utilización Promedio: {float(sub_wl.get('avg_utilization_pct') or 0.0)}%",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>5. Ruta Crítica (CPM / EDT)</b>", cell_style),
            Paragraph(
                f"Tareas Críticas: {int(sub_cpm.get('critical_completed_count') or 0)}/{int(sub_cpm.get('critical_tasks_count') or 0)} completadas • "
                f"Dependencias Activas: {int(sub_cpm.get('dependencies_count') or 0)}",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>6. Automatizaciones</b>", cell_style),
            Paragraph(
                f"Reglas Activas: {int(sub_auto.get('active_rules_count') or 0)}/{int(sub_auto.get('total_rules_count') or 0)} • "
                f"Ejecuciones Disparadas: {int(sub_auto.get('total_executions_count') or 0)}",
                cell_style,
            ),
        ],
    ]
    submodules_table = Table(submodules_table_data, colWidths=[160, 380])
    submodules_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(submodules_table)
    story.append(Spacer(1, 10))

    # 7c. Gobernanza del ciclo de vida PMI
    governance = report_data.get("governance_summary")
    if governance:
        quadrants = governance.get("stakeholders_by_quadrant") or {}
        story.append(Paragraph("GOBERNANZA DEL CICLO DE VIDA PMI", section_title_style))
        charter_status = str(governance.get("charter_status") or "draft").replace("_", " ").capitalize()
        sponsor_id = governance.get("sponsor_id") or "Sin asignar"
        authorized_at = governance.get("authorized_at") or "Sin autorizar"
        story.append(Paragraph(
            f"<b>Project Charter:</b> {safe_text(charter_status)} • "
            f"<b>Sponsor (Persona):</b> {safe_text(sponsor_id)} • "
            f"<b>Autorización:</b> {safe_text(authorized_at)} • "
            f"<b>Objetivos medibles:</b> {int(governance.get('measurable_objectives_count') or 0)}",
            body_style,
        ))
        stakeholder_total = int(governance.get("stakeholders_total") or 0)
        quadrant_table_data = [
            [Paragraph("<b>Matriz Poder × Interés</b>", cell_header), Paragraph("<b>Interesados</b>", cell_header)],
            [Paragraph("Gestionar de cerca", cell_style), int(quadrants.get("manage_closely") or 0)],
            [Paragraph("Mantener satisfechos", cell_style), int(quadrants.get("keep_satisfied") or 0)],
            [Paragraph("Mantener informados", cell_style), int(quadrants.get("keep_informed") or 0)],
            [Paragraph("Monitorear", cell_style), int(quadrants.get("monitor") or 0)],
            [Paragraph("<b>Total</b>", cell_style), stakeholder_total],
        ]
        quadrant_table = Table(quadrant_table_data, colWidths=[390, 150])
        quadrant_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(quadrant_table)
        closure_status = str(governance.get("closure_status") or "open").replace("_", " ").capitalize()
        deliverables_status = "Sí" if governance.get("deliverables_accepted_verified") else "Pendiente"
        reconciliation_status = "Sí" if governance.get("financial_reconciliation_completed") else "Pendiente"
        lessons_count = int(governance.get("lessons_learned_count") or 0)
        story.append(Paragraph(
            f"<b>Cierre formal:</b> {safe_text(closure_status)} • "
            f"<b>Entregables aceptados y verificados:</b> {deliverables_status} • "
            f"<b>Conciliación financiera:</b> {reconciliation_status} • "
            f"<b>Lecciones aprendidas:</b> {lessons_count}",
            body_style,
        ))
        story.append(Spacer(1, 8))

    # 8. Pie de página
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceBefore=2, spaceAfter=4))
    footer_text = (
        f"<b>Comunidad Cristiana El Faro</b> • Plataforma CCF Super-PRO Proyectos • "
        f"Documento emitido el {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC • Confidencialidad Ministerial."
    )
    story.append(Paragraph(footer_text, ParagraphStyle('CCFFooter', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.HexColor('#64748B'), alignment=1)))

    doc.build(story)
    return buf.getvalue()


def generate_project_tasks_csv(
    db: Session,
    project_id: UUID | str,
    *,
    user_sede_id: Optional[UUID | str] = None,
) -> str:
    """Genera CSV con BOM UTF-8 de tareas y cronograma del proyecto."""
    project = get_project(db, project_id, sede_id=user_sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    tasks = (
        db.query(models.ProjectTask)
        .options(selectinload(models.ProjectTask.assignee))
        .filter(
            models.ProjectTask.project_id == project.id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .order_by(models.ProjectTask.created_at.asc())
        .all()
    )

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "ID",
        "Título",
        "Descripción",
        "Estado",
        "Prioridad",
        "Fase/Nodo",
        "Responsable",
        "Fecha Inicio",
        "Fecha Fin",
        "Fecha Creación",
    ])

    for t in tasks:
        assignee_name = ""
        if t.assignee:
            p = t.assignee
            assignee_name = getattr(p, "nombre_completo", None) or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip() or "Miembro"

        start_str = t.start_date.isoformat()[:10] if t.start_date else ""
        due_str = t.due_date.isoformat()[:10] if t.due_date else ""
        created_str = t.created_at.isoformat()[:19].replace("T", " ") if t.created_at else ""

        writer.writerow([
            str(t.id),
            _safe_csv_text(t.title),
            _safe_csv_text((t.description or "").replace("\n", " ").strip()),
            _safe_csv_text(t.status or "todo"),
            _safe_csv_text(t.priority or "medium"),
            _safe_csv_text(t.node),
            _safe_csv_text(assignee_name),
            start_str,
            due_str,
            created_str,
        ])

    return output.getvalue()


def generate_project_expenses_csv(
    db: Session,
    project_id: UUID | str,
    *,
    user_sede_id: Optional[UUID | str] = None,
) -> str:
    """Genera CSV con BOM UTF-8 del libro mayor de gastos del proyecto."""
    project = get_project(db, project_id, sede_id=user_sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    expenses = (
        db.query(models.ProjectExpense)
        .options(selectinload(models.ProjectExpense.creator))
        .filter(
            models.ProjectExpense.project_id == project.id,
            models.ProjectExpense.deleted_at.is_(None),
        )
        .order_by(models.ProjectExpense.date.asc(), models.ProjectExpense.created_at.asc())
        .all()
    )

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "ID",
        "Fecha",
        "Categoría",
        "Descripción",
        "Monto",
        "Estado",
        "Comprobante URL",
        "Registrado Por",
        "Fecha Registro",
    ])

    for e in expenses:
        creator_name = ""
        if e.creator:
            p = e.creator
            creator_name = getattr(p, "nombre_completo", None) or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip() or "Usuario"

        date_str = e.date.isoformat()[:10] if e.date else ""
        created_str = e.created_at.isoformat()[:19].replace("T", " ") if e.created_at else ""

        writer.writerow([
            str(e.id),
            date_str,
            _safe_csv_text(e.category or "general"),
            _safe_csv_text((e.description or "").replace("\n", " ").strip()),
            f"{float(e.amount or 0.0):.2f}",
            _safe_csv_text(e.status or "planned"),
            _safe_csv_text(e.receipt_url),
            _safe_csv_text(creator_name),
            created_str,
        ])

    return output.getvalue()


# ── Project Indicators MGA / CREMA & SPI (Super-PRO CREMA Fase 1) ───────────

def validate_crema_indicator(payload: schemas.ValidateCremaPayload | dict) -> dict:
    """Microservicio validador inteligente de criterios C, R, E, M, A (Metodología MGA/BID)."""
    if isinstance(payload, dict):
        name = str(payload.get("name") or "").strip()
        description = str(payload.get("description") or "").strip()
        level = str(payload.get("level") or "PRODUCTO_PRINCIPAL").strip()
        calculation_type = str(payload.get("calculation_type") or "ABSOLUTO_ACUMULADO").strip()
        unit_of_measure = str(payload.get("unit_of_measure") or "").strip()
        target_value = payload.get("target_value")
        frequency = str(payload.get("frequency") or "mensual").strip()
    else:
        name = str(payload.name or "").strip()
        description = str(payload.description or "").strip()
        level = str(payload.level or "PRODUCTO_PRINCIPAL").strip()
        calculation_type = str(payload.calculation_type or "ABSOLUTO_ACUMULADO").strip()
        unit_of_measure = str(payload.unit_of_measure or "").strip()
        target_value = payload.target_value
        frequency = str(payload.frequency or "mensual").strip()

    criteria = {}

    # C - Claro (Clear): Precisión semántica, sin ambigüedades
    c_score = 0.0
    c_recs = []
    if len(name) >= 8:
        c_score += 12.0
    elif len(name) >= 4:
        c_score += 6.0
        c_recs.append("El nombre del indicador es muy breve. Detalle con mayor precisión el objeto de medición.")
    else:
        c_score += 3.0
        c_recs.append("El nombre debe tener al menos 4 caracteres representativos.")

    keywords = ["tasa", "porcentaje", "número", "numero", "cantidad", "índice", "indice", "volumen", "proporción", "proporcion", "tiempo", "costo", "total", "grado", "nivel", "cobertura", "avance", "spi", "horas", "monto"]
    has_keyword = any(k in name.lower() or k in description.lower() for k in keywords)
    if has_keyword or len(name) >= 15:
        c_score += 8.0
    else:
        c_score += 4.0
        c_recs.append("Recomendado: Incluya un sustantivo o métrica clara (ej: Porcentaje, Número, Tasa, Índice).")

    criteria["C"] = {
        "name": "Claro (Clear)",
        "score": round(min(20.0, c_score), 1),
        "passed": c_score >= 14.0,
        "recommendations": c_recs,
    }

    # R - Relevante (Relevant): Coherencia con nivel MGA
    r_score = 0.0
    r_recs = []
    valid_levels = {
        "RESULTADO_EFICACIA",
        "PRODUCTO_PRINCIPAL",
        "PRODUCTO_SECUNDARIO",
        "GESTION_PROCESO",
        "EFICIENCIA",
        "CALIDAD",
        "COMPONENTE_EDT",
        "IMPACTO_MINISTERIAL",
        "ACTIVIDAD_CRITICA",
        "FINANCIERO_EVM",
    }
    if level in valid_levels:
        r_score = 20.0
    else:
        r_score = 10.0
        r_recs.append(f"Nivel '{level}' no es un nivel estándar MGA. Seleccione uno de: {', '.join(sorted(valid_levels))}.")

    criteria["R"] = {
        "name": "Relevante (Relevant)",
        "score": round(r_score, 1),
        "passed": r_score >= 15.0,
        "recommendations": r_recs,
    }

    # E - Económico (Economic): Factibilidad y costo razonable de captura
    e_score = 0.0
    e_recs = []
    freq_lower = frequency.lower()
    if freq_lower in ["mensual", "trimestral", "semestral"]:
        e_score = 20.0
    elif freq_lower in ["semanal", "quincenal", "por_hito"]:
        e_score = 16.0
        e_recs.append("Frecuencias muy continuas pueden elevar el costo operativo de recolección de evidencias.")
    elif freq_lower in ["anual"]:
        e_score = 15.0
        e_recs.append("Frecuencia anual reduce la oportunidad de control temprano frente a desviaciones.")
    else:
        e_score = 12.0
        e_recs.append("Especifique una periodicidad estándar de medición (mensual, trimestral).")

    criteria["E"] = {
        "name": "Económico (Economic)",
        "score": round(e_score, 1),
        "passed": e_score >= 15.0,
        "recommendations": e_recs,
    }

    # M - Medible (Measurable): Unidad de medida y meta cuantitativa
    m_score = 0.0
    m_recs = []
    if unit_of_measure:
        m_score += 10.0
    else:
        m_recs.append("Defina una unidad de medida formal (ej: %, personas, horas, unidades, USD).")

    try:
        t_val = float(target_value) if target_value is not None else None
    except (ValueError, TypeError):
        t_val = None

    if t_val is not None and t_val > 0:
        m_score += 10.0
    elif t_val is not None and t_val == 0:
        m_score += 5.0
        m_recs.append("Meta proyectada igual a 0. Indique un objetivo cuantitativo superior.")
    else:
        m_recs.append("Establezca una meta cuantitativa numérica verificable.")

    criteria["M"] = {
        "name": "Medible (Measurable)",
        "score": round(min(20.0, m_score), 1),
        "passed": m_score >= 15.0,
        "recommendations": m_recs,
    }

    # A - Adecuado (Adequate): Coherencia entre nivel y tipo de cálculo
    a_score = 0.0
    a_recs = []
    valid_calcs = {
        "ABSOLUTO_ACUMULADO",
        "PORCENTAJE_PROPORCION",
        "TASA_VARIACION",
        "COSTO_EFICIENCIA",
    }
    if calculation_type in valid_calcs:
        a_score += 15.0
        if level in ["EFICIENCIA", "CALIDAD", "FINANCIERO_EVM"] and calculation_type in ["COSTO_EFICIENCIA", "PORCENTAJE_PROPORCION"]:
            a_score += 5.0
        elif level in ["RESULTADO_EFICACIA", "IMPACTO_MINISTERIAL"] and calculation_type in ["PORCENTAJE_PROPORCION", "TASA_VARIACION", "COSTO_EFICIENCIA"]:
            a_score += 5.0
        elif level in ["PRODUCTO_PRINCIPAL", "PRODUCTO_SECUNDARIO", "GESTION_PROCESO", "COMPONENTE_EDT", "ACTIVIDAD_CRITICA"]:
            a_score += 5.0
        else:
            a_score += 3.0
    else:
        a_score = 8.0
        a_recs.append(f"Tipo de cálculo '{calculation_type}' no canónico. Use uno de: {', '.join(sorted(valid_calcs))}.")

    criteria["A"] = {
        "name": "Adecuado (Adequate)",
        "score": round(min(20.0, a_score), 1),
        "passed": a_score >= 15.0,
        "recommendations": a_recs,
    }

    total_score = sum(c["score"] for c in criteria.values())
    total_score = round(total_score, 1)

    if total_score >= 85.0:
        status = "EXCELENTE"
        summary = "El indicador cumple con alta rigurosidad metodológica MGA/CREMA y está listo para monitoreo formal."
    elif total_score >= 70.0:
        status = "BUENO"
        summary = "El indicador es metodológicamente sólido con pequeñas oportunidades de optimización en unidad o periodicidad."
    elif total_score >= 50.0:
        status = "REGULAR"
        summary = "El indicador requiere calibración en sus atributos de claridad o metas antes de fijar línea base."
    else:
        status = "DEFICIENTE"
        summary = "El indicador no satisface los criterios CREMA mínimos. Requiere revisión estructural."

    return {
        "score": total_score,
        "status": status,
        "criteria": criteria,
        "summary": summary,
    }


def _prepare_indicator_response(
    ind: models.ProjectIndicator,
    db: Optional[Session] = None,
    project: Optional[models.Project] = None,
    matrix: Optional[dict] = None,
) -> models.ProjectIndicator:
    if ind:
        if hasattr(ind, "creator") and ind.creator:
            p = ind.creator
            ind.creator_name = getattr(p, "nombre_completo", None) or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip() or "Usuario"
        else:
            ind.creator_name = "Usuario"

        records = [r for r in getattr(ind, "records", []) if r.deleted_at is None]
        ind.records_count = len(records)
        for r in records:
            _prepare_record_response(r)

        src = getattr(ind, "source_type", "manual") or "manual"
        comp_id = getattr(ind, "component_id", None)

        if src != "manual" and db is not None and project is not None:
            from backend.services.project_evm_service import evaluate_execution_metric
            eval_res = evaluate_execution_metric(
                db,
                project,
                src,
                component_id=comp_id,
                target_value=ind.target_value,
                matrix=matrix,
            )
            if eval_res.get("current_value") is not None:
                ind.current_value = float(eval_res["current_value"])
            ind.last_spi = eval_res.get("spi")
            ind.__dict__["component_name"] = eval_res.get("component_name")
            ind.__dict__["frente"] = eval_res.get("frente")
            ind.__dict__["is_auto_synced"] = True
        else:
            if records:
                sorted_recs = sorted(records, key=lambda x: x.reported_at or x.created_at)
                ind.last_spi = sorted_recs[-1].spi
            elif ind.target_value and float(ind.target_value) > 0 and float(ind.current_value or 0.0) > 0:
                ind.last_spi = round(float(ind.current_value) / float(ind.target_value), 4)
            else:
                ind.last_spi = None
            ind.__dict__["component_name"] = None
            ind.__dict__["frente"] = "manual"
            ind.__dict__["is_auto_synced"] = False
    return ind


def _prepare_record_response(rec: models.ProjectIndicatorRecord) -> models.ProjectIndicatorRecord:
    if rec:
        if hasattr(rec, "reporter") and rec.reporter:
            p = rec.reporter
            rec.reporter_name = getattr(p, "nombre_completo", None) or f"{getattr(p, 'nombres', '')} {getattr(p, 'apellidos', '')}".strip() or "Usuario"
        else:
            rec.reporter_name = "Usuario"
    return rec


def get_project_indicators(
    db: Session,
    project_id: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
) -> list[models.ProjectIndicator]:
    """Lista todos los indicadores activos de un proyecto con sus métricas y registros."""
    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    indicators = (
        db.query(models.ProjectIndicator)
        .options(
            selectinload(models.ProjectIndicator.creator),
            selectinload(models.ProjectIndicator.records).selectinload(models.ProjectIndicatorRecord.reporter),
        )
        .filter(
            models.ProjectIndicator.project_id == project.id,
            models.ProjectIndicator.deleted_at.is_(None),
        )
        .order_by(models.ProjectIndicator.created_at.asc())
        .all()
    )

    matrix = None
    if indicators and any(getattr(ind, "source_type", "manual") != "manual" for ind in indicators):
        from backend.services.project_evm_service import build_project_execution_matrix
        matrix = build_project_execution_matrix(db, project)

    return [_prepare_indicator_response(ind, db=db, project=project, matrix=matrix) for ind in indicators]


def get_project_indicator(
    db: Session,
    indicator_id: UUID | str,
    *,
    project_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
) -> Optional[models.ProjectIndicator]:
    """Obtiene un indicador específico con control de tenant."""
    q = (
        db.query(models.ProjectIndicator)
        .options(
            selectinload(models.ProjectIndicator.creator),
            selectinload(models.ProjectIndicator.records).selectinload(models.ProjectIndicatorRecord.reporter),
        )
        .filter(
            models.ProjectIndicator.id == indicator_id,
            models.ProjectIndicator.deleted_at.is_(None),
        )
    )
    if project_id is not None:
        q = q.filter(models.ProjectIndicator.project_id == project_id)

    ind = q.first()
    if not ind:
        return None

    project = get_project(db, ind.project_id, sede_id=sede_id) if sede_id is not None else get_project(db, ind.project_id)
    if sede_id is not None and not project:
        return None

    return _prepare_indicator_response(ind, db=db, project=project)


def create_project_indicator(
    db: Session,
    project_id: UUID | str,
    indicator_in: schemas.ProjectIndicatorCreate,
    created_by: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
) -> models.ProjectIndicator:
    """Crea un indicador con evaluación CREMA automática, enlace de ejecución y trazabilidad UTC."""
    from backend.services.project_evm_service import evaluate_execution_metric

    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    effective_sede_id = sede_id or project.sede_id
    src = str(getattr(indicator_in, "source_type", "manual") or "manual").strip()
    comp_id = getattr(indicator_in, "component_id", None)

    target_val = float(indicator_in.target_value or 0.0)
    current_val = float(indicator_in.current_value or indicator_in.baseline_value or 0.0)
    unit_val = indicator_in.unit_of_measure

    if src != "manual":
        eval_res = evaluate_execution_metric(
            db, project, src, component_id=comp_id, target_value=target_val if target_val > 0 else None
        )
        if eval_res.get("current_value") is not None:
            current_val = float(eval_res["current_value"])
        if target_val <= 0 and eval_res.get("suggested_target"):
            target_val = float(eval_res["suggested_target"])
        if not unit_val and eval_res.get("unit"):
            unit_val = str(eval_res["unit"])

    # Auto-evaluación CREMA si no viene provista
    crema_eval = dict(indicator_in.crema_evaluation or {})
    crema_score = indicator_in.crema_score
    if not crema_eval.get("criteria") or crema_score is None:
        validation = validate_crema_indicator({
            "name": indicator_in.name,
            "description": indicator_in.description,
            "level": indicator_in.level,
            "calculation_type": indicator_in.calculation_type,
            "unit_of_measure": unit_val,
            "target_value": target_val,
            "frequency": indicator_in.frequency,
        })
        crema_eval = dict(validation)
        crema_score = validation["score"]

    crema_eval["execution_link"] = {
        "source_type": src,
        "component_id": str(comp_id) if comp_id else None,
    }

    # Generar código correlativo si no viene provisto
    code = indicator_in.code
    if not code:
        count = (
            db.query(func.count(models.ProjectIndicator.id))
            .filter(models.ProjectIndicator.project_id == project.id)
            .scalar()
            or 0
        )
        code = f"IND-{count + 1:03d}"

    indicator = models.ProjectIndicator(
        project_id=project.id,
        code=code,
        name=indicator_in.name,
        description=indicator_in.description,
        level=indicator_in.level or "PRODUCTO_PRINCIPAL",
        calculation_type=indicator_in.calculation_type or "ABSOLUTO_ACUMULADO",
        unit_of_measure=unit_val,
        baseline_value=indicator_in.baseline_value or 0.0,
        target_value=target_val,
        current_value=current_val,
        frequency=indicator_in.frequency or "mensual",
        period_targets=indicator_in.period_targets or {},
        crema_score=crema_score,
        crema_evaluation=crema_eval,
        created_by=created_by,
        sede_id=effective_sede_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(indicator)
    db.commit()
    db.refresh(indicator)
    return _prepare_indicator_response(indicator, db=db, project=project)


def update_project_indicator(
    db: Session,
    indicator_id: UUID | str,
    indicator_in: schemas.ProjectIndicatorUpdate,
    user_id: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
    project_id: Optional[UUID | str] = None,
) -> Optional[models.ProjectIndicator]:
    """Actualiza un indicador recalculando CREMA y sincronizando su enlace de ejecución."""
    from backend.services.project_evm_service import evaluate_execution_metric

    indicator = get_project_indicator(db, indicator_id, project_id=project_id, sede_id=sede_id)
    if not indicator:
        return None

    update_data = indicator_in.model_dump(exclude_unset=True)
    src = str(update_data.pop("source_type", indicator.source_type) or "manual").strip()
    if "component_id" in update_data:
        comp_id = update_data.pop("component_id")
    else:
        comp_id = indicator.component_id

    for field, val in update_data.items():
        setattr(indicator, field, val)

    project = get_project(db, indicator.project_id, sede_id=sede_id)
    if src != "manual" and project:
        eval_res = evaluate_execution_metric(
            db, project, src, component_id=comp_id, target_value=indicator.target_value
        )
        if eval_res.get("current_value") is not None:
            indicator.current_value = float(eval_res["current_value"])

    # Si se alteraron atributos clave y no se pasó crema_score explícito, recalcular CREMA
    recalc_keys = {"name", "description", "level", "calculation_type", "unit_of_measure", "target_value", "frequency"}
    if any(k in update_data for k in recalc_keys) and "crema_score" not in update_data:
        val_res = validate_crema_indicator({
            "name": indicator.name,
            "description": indicator.description,
            "level": indicator.level,
            "calculation_type": indicator.calculation_type,
            "unit_of_measure": indicator.unit_of_measure,
            "target_value": indicator.target_value,
            "frequency": indicator.frequency,
        })
        new_eval = dict(val_res)
        new_eval["execution_link"] = {
            "source_type": src,
            "component_id": str(comp_id) if comp_id else None,
        }
        indicator.crema_evaluation = new_eval
        indicator.crema_score = val_res["score"]
    else:
        existing_eval = dict(indicator.crema_evaluation) if isinstance(indicator.crema_evaluation, dict) else {}
        existing_eval["execution_link"] = {
            "source_type": src,
            "component_id": str(comp_id) if comp_id else None,
        }
        indicator.crema_evaluation = existing_eval

    indicator.source_type = src
    indicator.component_id = str(comp_id) if comp_id else None
    indicator.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(indicator)
    return _prepare_indicator_response(indicator, db=db, project=project)


def delete_project_indicator(
    db: Session,
    indicator_id: UUID | str,
    user_id: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
    project_id: Optional[UUID | str] = None,
) -> bool:
    """Soft-delete de indicador garantizando UTC (Axioma 2)."""
    indicator = get_project_indicator(db, indicator_id, project_id=project_id, sede_id=sede_id)
    if not indicator:
        return False

    indicator.deleted_at = datetime.now(timezone.utc)
    indicator.updated_at = datetime.now(timezone.utc)
    db.commit()
    return True


def create_project_indicator_record(
    db: Session,
    indicator_id: UUID | str,
    record_in: schemas.ProjectIndicatorRecordCreate,
    reported_by: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
    project_id: Optional[UUID | str] = None,
) -> models.ProjectIndicatorRecord:
    """Registra avance periódico calculando SPI y actualizando el valor actual del indicador."""
    indicator = get_project_indicator(db, indicator_id, project_id=project_id, sede_id=sede_id)
    if not indicator:
        raise ValueError("Indicador no encontrado o no pertenece a la sede (Axioma 3)")

    target = float(record_in.target_value or 0.0)
    actual = float(record_in.actual_value or 0.0)

    # SPI is derived from the persisted measurement; never trust a client-supplied score.
    if target > 0:
        spi = round(actual / target, 2)
    else:
        spi = 1.0 if actual >= 0 else 0.0

    rep_at = record_in.reported_at or datetime.now(timezone.utc)
    if not hasattr(rep_at, "tzinfo") or not rep_at.tzinfo:
        rep_at = rep_at.replace(tzinfo=timezone.utc)

    record = models.ProjectIndicatorRecord(
        indicator_id=indicator.id,
        period=record_in.period,
        target_value=target,
        actual_value=actual,
        spi=spi,
        notes=record_in.notes,
        evidence_url=record_in.evidence_url,
        reported_by=reported_by,
        reported_at=rep_at,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Actualizar current_value del indicador con el último valor actual reportado
    indicator.current_value = actual
    indicator.updated_at = datetime.now(timezone.utc)

    db.add(record)
    db.commit()
    db.refresh(record)
    return _prepare_record_response(record)


def get_project_indicator_records(
    db: Session,
    indicator_id: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
    project_id: Optional[UUID | str] = None,
) -> list[models.ProjectIndicatorRecord]:
    """Lista historial de mediciones de un indicador."""
    indicator = get_project_indicator(db, indicator_id, project_id=project_id, sede_id=sede_id)
    if not indicator:
        raise ValueError("Indicador no encontrado o no pertenece a la sede (Axioma 3)")

    records = (
        db.query(models.ProjectIndicatorRecord)
        .options(selectinload(models.ProjectIndicatorRecord.reporter))
        .filter(
            models.ProjectIndicatorRecord.indicator_id == indicator.id,
            models.ProjectIndicatorRecord.deleted_at.is_(None),
        )
        .order_by(models.ProjectIndicatorRecord.reported_at.asc(), models.ProjectIndicatorRecord.created_at.asc())
        .all()
    )

    return [_prepare_record_response(r) for r in records]


def sync_project_indicators_and_kpis(
    db: Session,
    project_id: UUID | str,
    actor_id: Optional[UUID | str] = None,
    *,
    user_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
    seed_pro_families: Optional[bool] = None,
    seed_pro_indicators: Optional[bool] = None,
    seed_kpis: Optional[bool] = None,
    seed_pro_kpis: Optional[bool] = None,
    period_label: Optional[str] = None,
    record_period: Optional[str] = None,
) -> dict:
    """Sincroniza en tiempo real la Matriz de Indicadores y KPIs con los 3 Frentes de Ejecución.

    - Si seed_pro_families/seed_pro_indicators=True, autogenera las 6 Familias de Indicadores Pro del proyecto
      y el indicador de avance físico de cada Componente EDT activo si aún no existen.
    - Si seed_kpis/seed_pro_kpis=True, autogenera los 6 KPIs ejecutivos Pro vinculados a los 3 Frentes si no existen.
    - Recalcula current_value y SPI para todos los indicadores y KPIs vinculados a fuentes automáticas.
    """
    from backend.models_projects import encode_kpi_meta
    from backend.services.project_evm_service import (
        build_project_execution_matrix,
        evaluate_execution_metric,
    )

    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    eff_actor = actor_id or user_id
    eff_seed_indicators = (
        seed_pro_indicators
        if seed_pro_indicators is not None
        else (seed_pro_families if seed_pro_families is not None else True)
    )
    eff_seed_kpis = (
        seed_pro_kpis
        if seed_pro_kpis is not None
        else (seed_kpis if seed_kpis is not None else False)
    )

    now = datetime.now(timezone.utc)
    eff_period = (record_period or period_label or now.strftime("%Y-%m")).strip()
    matrix = build_project_execution_matrix(db, project)

    existing_indicators = (
        db.query(models.ProjectIndicator)
        .filter(
            models.ProjectIndicator.project_id == project.id,
            models.ProjectIndicator.deleted_at.is_(None),
        )
        .all()
    )

    seeded_indicators_count = 0
    synced_indicators_count = 0

    if eff_seed_indicators:
        existing_links = {
            (getattr(ind, "source_type", "manual"), getattr(ind, "component_id", None))
            for ind in existing_indicators
        }
        pro_blueprints = [
            {
                "code": "PRO-01",
                "name": "Porcentaje de Avance Físico Ponderado (Tributación EDT -> Proyecto)",
                "description": "Mide el avance continuo ponderando Subtareas -> Actividades -> Componentes EDT -> Proyecto.",
                "level": "COMPONENTE_EDT",
                "calculation_type": "PORCENTAJE_PROPORCION",
                "unit_of_measure": "%",
                "target_value": 100.0,
                "source_type": "pro_edt_progress",
                "component_id": None,
            },
            {
                "code": "PRO-02",
                "name": "Índice de Eficiencia de Esfuerzo y Horas Trabajadas",
                "description": "Relación porcentual entre las horas ganadas por avance físico y las horas reales registradas.",
                "level": "ACTIVIDAD_CRITICA",
                "calculation_type": "PORCENTAJE_PROPORCION",
                "unit_of_measure": "%",
                "target_value": 100.0,
                "source_type": "pro_hours_efficiency",
                "component_id": None,
            },
            {
                "code": "PRO-03",
                "name": "Índice de Costo-Eficiencia Presupuestal (CPI = EV / AC)",
                "description": "Cruce físico-financiero entre el Valor Ganado (EV) y el Costo Real ejecutado (AC).",
                "level": "FINANCIERO_EVM",
                "calculation_type": "COSTO_EFICIENCIA",
                "unit_of_measure": "índice",
                "target_value": 1.0,
                "source_type": "pro_cost_efficiency",
                "component_id": None,
            },
            {
                "code": "PRO-04",
                "name": "Porcentaje de Cumplimiento de Hitos en Cronograma",
                "description": "Proporción de hitos del proyecto completados dentro de la fecha objetivo comprometida.",
                "level": "PRODUCTO_PRINCIPAL",
                "calculation_type": "PORCENTAJE_PROPORCION",
                "unit_of_measure": "%",
                "target_value": 100.0,
                "source_type": "pro_milestones_ontime",
                "component_id": None,
            },
            {
                "code": "PRO-05",
                "name": "Tasa de Mitigación y Control de Riesgos RAID",
                "description": "Porcentaje de riesgos identificados con estado mitigado o plan de mitigación activo.",
                "level": "IMPACTO_MINISTERIAL",
                "calculation_type": "PORCENTAJE_PROPORCION",
                "unit_of_measure": "%",
                "target_value": 100.0,
                "source_type": "pro_raid_mitigated",
                "component_id": None,
            },
            {
                "code": "PRO-06",
                "name": "Índice Compuesto de Salud Global del Proyecto (CR = CPI × SPI)",
                "description": "Razón Crítica PMI que combina el desempeño del cronograma (SPI) y la eficiencia del gasto (CPI).",
                "level": "IMPACTO_MINISTERIAL",
                "calculation_type": "COSTO_EFICIENCIA",
                "unit_of_measure": "índice",
                "target_value": 1.0,
                "source_type": "pro_global_health",
                "component_id": None,
            },
        ]

        # También incluir un indicador de avance por cada Componente EDT activo
        for idx, comp_info in enumerate(matrix.get("rollup_hierarchy", {}).get("components", []), start=1):
            c_id = str(comp_info["component_id"])
            c_code = comp_info.get("code") or f"EDT-{idx:02d}"
            c_name = comp_info.get("name") or f"Componente {idx}"
            pro_blueprints.append(
                {
                    "code": f"EDT-{idx:02d}",
                    "name": f"Avance Físico Componente [{c_code}] {c_name}",
                    "description": f"Tributación directa de actividades y subtareas del componente {c_name} (Peso presupuestal: {comp_info.get('weight_pct', 0)}%).",
                    "level": "COMPONENTE_EDT",
                    "calculation_type": "PORCENTAJE_PROPORCION",
                    "unit_of_measure": "%",
                    "target_value": 100.0,
                    "source_type": "pro_edt_progress",
                    "component_id": c_id,
                }
            )

        for bp in pro_blueprints:
            key = (bp["source_type"], bp["component_id"])
            if key in existing_links:
                continue
            created_ind = create_project_indicator(
                db,
                project.id,
                schemas.ProjectIndicatorCreate(**bp),
                created_by=eff_actor,
                sede_id=sede_id or project.sede_id,
            )
            existing_indicators.append(created_ind)
            existing_links.add(key)
            seeded_indicators_count += 1

    # Sincronizar todos los indicadores conectados a fuentes automáticas
    for ind in existing_indicators:
        src = getattr(ind, "source_type", "manual") or "manual"
        if src == "manual":
            continue
        eval_res = evaluate_execution_metric(
            db,
            project,
            src,
            component_id=getattr(ind, "component_id", None),
            target_value=ind.target_value,
            matrix=matrix,
        )
        if eval_res.get("current_value") is not None:
            ind.current_value = float(eval_res["current_value"])
            ind.updated_at = now
            synced_indicators_count += 1

            # Registrar o actualizar medición automática del período actual
            existing_rec = (
                db.query(models.ProjectIndicatorRecord)
                .filter(
                    models.ProjectIndicatorRecord.indicator_id == ind.id,
                    models.ProjectIndicatorRecord.period == eff_period,
                    models.ProjectIndicatorRecord.deleted_at.is_(None),
                )
                .first()
            )
            spi_val = round(float(eval_res.get("spi") or 0.0), 2)
            if existing_rec:
                existing_rec.actual_value = float(eval_res["current_value"])
                existing_rec.target_value = float(ind.target_value or eval_res.get("suggested_target") or 100.0)
                existing_rec.spi = spi_val
                existing_rec.updated_at = now
            else:
                db.add(
                    models.ProjectIndicatorRecord(
                        indicator_id=ind.id,
                        period=eff_period,
                        target_value=float(ind.target_value or eval_res.get("suggested_target") or 100.0),
                        actual_value=float(eval_res["current_value"]),
                        spi=spi_val,
                        notes=f"Sincronización automática desde ejecución real ({src}).",
                        reported_by=eff_actor,
                        reported_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )

    # KPIs ejecutivos (6 Familias Pro)
    existing_kpis = (
        db.query(models.ProjectKPI)
        .filter(
            models.ProjectKPI.project_id == project.id,
            models.ProjectKPI.deleted_at.is_(None),
        )
        .all()
    )
    seeded_kpis_count = 0
    synced_kpis_count = 0

    if eff_seed_kpis:
        existing_kpi_sources = {
            (getattr(k, "source_type", "manual"), getattr(k, "component_id", None))
            for k in existing_kpis
        }
        kpi_blueprints = [
            {
                "title": "Avance Físico Ponderado (Tributación EDT)",
                "description": "Roll-up continuo Subtareas -> Actividades -> Componentes EDT -> Proyecto.",
                "target_value": 100.0,
                "unit": "%",
                "category": "operational",
                "source_type": "pro_edt_progress",
            },
            {
                "title": "Eficiencia de Esfuerzo y Horas Trabajadas",
                "description": "Relación porcentual entre horas ganadas por avance y horas reales.",
                "target_value": 100.0,
                "unit": "%",
                "category": "operational",
                "source_type": "pro_hours_efficiency",
            },
            {
                "title": "Eficiencia Presupuestal Valor Ganado (CPI)",
                "description": "Cruce Tiempo × Financiero (EV / AC).",
                "target_value": 1.0,
                "unit": "índice",
                "category": "financial",
                "source_type": "pro_cost_efficiency",
            },
            {
                "title": "Cumplimiento de Hitos en Cronograma",
                "description": "Porcentaje de hitos completados en fecha objetivo.",
                "target_value": 100.0,
                "unit": "%",
                "category": "quality",
                "source_type": "pro_milestones_ontime",
            },
            {
                "title": "Mitigación de Riesgos RAID",
                "description": "Porcentaje de riesgos mitigados o con plan activo.",
                "target_value": 100.0,
                "unit": "%",
                "category": "quality",
                "source_type": "pro_raid_mitigated",
            },
            {
                "title": "Salud Global del Proyecto (Razón Crítica CR)",
                "description": "Índice compuesto CPI × SPI de desempeño integral.",
                "target_value": 1.0,
                "unit": "índice",
                "category": "impact",
                "source_type": "pro_global_health",
            },
        ]
        for kbp in kpi_blueprints:
            k_key = (kbp["source_type"], None)
            if k_key in existing_kpi_sources:
                continue
            eval_res = evaluate_execution_metric(
                db, project, kbp["source_type"], target_value=kbp["target_value"], matrix=matrix
            )
            new_kpi = models.ProjectKPI(
                project_id=project.id,
                title=kbp["title"],
                description=encode_kpi_meta(kbp["description"], kbp["source_type"], None),
                target_value=kbp["target_value"],
                current_value=float(eval_res.get("current_value") or 0.0),
                unit=kbp["unit"],
                category=kbp["category"],
                created_at=now,
                updated_at=now,
            )
            new_kpi.source_type = kbp["source_type"]
            db.add(new_kpi)
            existing_kpis.append(new_kpi)
            existing_kpi_sources.add(k_key)
            seeded_kpis_count += 1

    for k in existing_kpis:
        k_src = getattr(k, "source_type", "manual") or "manual"
        if k_src == "manual":
            continue
        eval_res = evaluate_execution_metric(
            db,
            project,
            k_src,
            component_id=getattr(k, "component_id", None),
            target_value=k.target_value,
            matrix=matrix,
        )
        if eval_res.get("current_value") is not None:
            k.current_value = float(eval_res["current_value"])
            k.updated_at = now
            synced_kpis_count += 1

    db.commit()

    final_indicators = get_project_indicators(db, project.id, sede_id=sede_id)
    final_kpis = get_project_kpis(db, project.id)

    return {
        "project_id": str(project.id),
        "synced_indicators": synced_indicators_count,
        "seeded_indicators": seeded_indicators_count,
        "synced_kpis": synced_kpis_count,
        "seeded_kpis": seeded_kpis_count,
        "synced_indicators_count": synced_indicators_count,
        "seeded_indicators_count": seeded_indicators_count,
        "synced_kpis_count": synced_kpis_count,
        "seeded_kpis_count": seeded_kpis_count,
        "execution_matrix": matrix,
        "indicators": final_indicators,
        "kpis": final_kpis,
    }



# ── Project User Favorites and Pinning (Super-PRO Files Fase 1) ───────────

def toggle_task_favorite(
    db: Session,
    project_id: UUID | str,
    task_id: UUID | str,
    persona_id: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
) -> dict:
    """Alterna el estado favorito de una tarea para una persona respetando el tenant scope (Axioma 3)."""
    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    task = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.id == task_id,
            models.ProjectTask.project_id == project.id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    if not task:
        raise ValueError("Tarea no encontrada en este proyecto")

    fav = (
        db.query(models.ProjectUserFavorite)
        .filter(
            models.ProjectUserFavorite.project_id == project.id,
            models.ProjectUserFavorite.persona_id == persona_id,
            models.ProjectUserFavorite.entity_type == "task",
            models.ProjectUserFavorite.entity_id == task.id,
        )
        .first()
    )

    if fav:
        db.delete(fav)
        db.commit()
        return {
            "is_favorite": False,
            "entity_type": "task",
            "entity_id": str(task.id),
            "message": "Tarea removida de favoritos",
        }
    else:
        new_fav = models.ProjectUserFavorite(
            project_id=project.id,
            persona_id=persona_id,
            entity_type="task",
            entity_id=task.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_fav)
        db.commit()
        db.refresh(new_fav)
        return {
            "is_favorite": True,
            "entity_type": "task",
            "entity_id": str(task.id),
            "message": "Tarea agregada a favoritos",
        }


def get_project_user_favorites(
    db: Session,
    project_id: UUID | str,
    persona_id: UUID | str,
    *,
    entity_type: str = "task",
    sede_id: Optional[UUID | str] = None,
) -> list[str]:
    """Obtiene la lista de UUIDs de entidades favoritas para el usuario en el proyecto."""
    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    favs = (
        db.query(models.ProjectUserFavorite)
        .filter(
            models.ProjectUserFavorite.project_id == project.id,
            models.ProjectUserFavorite.persona_id == persona_id,
            models.ProjectUserFavorite.entity_type == entity_type,
        )
        .all()
    )
    return [str(f.entity_id) for f in favs]


def pin_project_comment(
    db: Session,
    project_id: UUID | str,
    comment_id: UUID | str,
    persona_id: UUID | str,
    *,
    task_id: Optional[UUID | str] = None,
    is_pinned: Optional[bool] = None,
    sede_id: Optional[UUID | str] = None,
) -> models.ProjectComment:
    """Fija o desfija un comentario en la cabecera del hilo con trazabilidad UTC."""
    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    q = (
        db.query(models.ProjectComment)
        .filter(
            models.ProjectComment.id == comment_id,
            models.ProjectComment.project_id == project.id,
            models.ProjectComment.deleted_at.is_(None),
        )
    )
    if task_id:
        q = q.filter(models.ProjectComment.task_id == task_id)

    comment = q.first()
    if not comment:
        raise ValueError("Comentario no encontrado en este proyecto")

    target_state = not comment.is_pinned if is_pinned is None else bool(is_pinned)
    comment.is_pinned = target_state
    if target_state:
        comment.pinned_at = datetime.now(timezone.utc)
        comment.pinned_by = persona_id
    else:
        comment.pinned_at = None
        comment.pinned_by = None

    comment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    return comment


# ── Bóveda Documental y Visor Universal Embebido (Super-PRO Files Fase 2) ──

import re

DRIVE_FILE_ID_PATTERNS = [
    r"/file/d/([a-zA-Z0-9_-]+)",           # https://drive.google.com/file/d/ID/...
    r"/document/d/([a-zA-Z0-9_-]+)",       # https://docs.google.com/document/d/ID/...
    r"/spreadsheets/d/([a-zA-Z0-9_-]+)",   # https://docs.google.com/spreadsheets/d/ID/...
    r"/presentation/d/([a-zA-Z0-9_-]+)",   # https://docs.google.com/presentation/d/ID/...
    r"/forms/d/([a-zA-Z0-9_-]+)",          # https://docs.google.com/forms/d/ID/...
    r"[?&]id=([a-zA-Z0-9_-]+)",            # https://drive.google.com/open?id=ID
    r"^([a-zA-Z0-9_-]{8,})$",              # Bare ID
]

def extract_drive_file_id(url_or_id: str) -> Optional[str]:
    """Extrae el ID de Google Drive a partir de una URL compartida o ID crudo."""
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    if "://" in url_or_id:
        try:
            parsed_url = urlsplit(url_or_id)
            if (
                parsed_url.scheme.lower() != "https"
                or parsed_url.hostname not in {"drive.google.com", "docs.google.com"}
                or parsed_url.username is not None
                or parsed_url.password is not None
                or parsed_url.port is not None
            ):
                return None
        except ValueError:
            return None
    elif "/" in url_or_id or "?" in url_or_id or "#" in url_or_id:
        # Only raw file IDs are accepted without an absolute Google URL.
        return None
    for pattern in DRIVE_FILE_ID_PATTERNS:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None

def normalize_drive_embed_url(url_or_id: str) -> tuple[Optional[str], Optional[str], str]:
    """Normaliza un enlace de Google Drive a formato embebido /preview.
    
    Retorna (drive_file_id, embed_url, inferred_type).
    """
    file_id = extract_drive_file_id(url_or_id)
    if not file_id:
        return None, None, "unknown"
    
    url_str = url_or_id.lower()
    if "document/d/" in url_str:
        embed_url = f"https://docs.google.com/document/d/{file_id}/preview"
        inferred_type = "google_doc"
    elif "spreadsheets/d/" in url_str:
        embed_url = f"https://docs.google.com/spreadsheets/d/{file_id}/preview"
        inferred_type = "google_sheet"
    elif "presentation/d/" in url_str:
        embed_url = f"https://docs.google.com/presentation/d/{file_id}/preview"
        inferred_type = "google_slide"
    elif "forms/d/" in url_str:
        embed_url = f"https://docs.google.com/forms/d/{file_id}/viewform?embedded=true"
        inferred_type = "google_form"
    else:
        embed_url = f"https://drive.google.com/file/d/{file_id}/preview"
        inferred_type = "google_drive_file"
        
    return file_id, embed_url, inferred_type


def create_project_file(
    db: Session,
    project_id: UUID | str,
    *,
    file_in: Optional[Any] = None,
    name: Optional[str] = None,
    file_url: Optional[str] = None,
    file_source: str = "local",
    category: str = "general",
    description: Optional[str] = None,
    file_type: Optional[str] = None,
    file_size: Optional[int] = None,
    drive_file_id: Optional[str] = None,
    task_id: Optional[UUID | str] = None,
    phase_id: Optional[UUID | str] = None,
    uploaded_by: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
) -> models.ProjectFile:
    """Crea un registro documental en la bóveda de project_files."""
    if file_in is not None:
        data = file_in.model_dump() if hasattr(file_in, "model_dump") else (file_in.dict() if hasattr(file_in, "dict") else dict(file_in))
        name = data.get("name", name)
        file_url = data.get("file_url", file_url)
        file_source = data.get("file_source", file_source)
        category = data.get("category", category)
        description = data.get("description", description)
        file_type = data.get("file_type", file_type)
        file_size = data.get("file_size", file_size)
        drive_file_id = data.get("drive_file_id", drive_file_id)
        task_id = data.get("task_id", task_id)
        phase_id = data.get("phase_id", phase_id)

    if not name or not file_url:
        raise ValueError("name y file_url son campos obligatorios")

    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    if task_id is not None:
        task = db.query(models.ProjectTask).filter(
            models.ProjectTask.id == _to_uuid(task_id),
            models.ProjectTask.project_id == project.id,
            models.ProjectTask.deleted_at.is_(None),
        ).first()
        if not task:
            raise ValueError("La tarea asociada no pertenece a este proyecto")
    if phase_id is not None:
        phase = db.query(models.ProjectPhase).filter(
            models.ProjectPhase.id == _to_uuid(phase_id),
            models.ProjectPhase.project_id == project.id,
            models.ProjectPhase.deleted_at.is_(None),
        ).first()
        if not phase:
            raise ValueError("La fase asociada no pertenece a este proyecto")

    # Si es drive y no tiene drive_file_id, intentar extraerlo y normalizar
    if file_source == "drive" or "drive.google.com" in file_url or "docs.google.com" in file_url:
        d_id, _, inf_type = normalize_drive_embed_url(file_url)
        if d_id:
            drive_file_id = d_id
            file_source = "drive"
            if not file_type:
                file_type = inf_type

    now_utc = datetime.now(timezone.utc)
    new_file = models.ProjectFile(
        project_id=project.id,
        name=name,
        description=description,
        category=category or "general",
        file_source=file_source,
        file_url=file_url,
        file_type=file_type,
        file_size=file_size,
        drive_file_id=drive_file_id,
        task_id=task_id,
        phase_id=phase_id,
        uploaded_by=uploaded_by,
        sede_id=project.sede_id,
        created_at=now_utc,
        updated_at=now_utc,
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file


def link_drive_file(
    db: Session,
    project_id: UUID | str,
    *,
    payload: Optional[Any] = None,
    drive_url: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    task_id: Optional[UUID | str] = None,
    phase_id: Optional[UUID | str] = None,
    uploaded_by: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
) -> models.ProjectFile:
    """Vincula un documento o carpeta de Google Drive a la bóveda del proyecto."""
    if payload is not None:
        data = payload.model_dump() if hasattr(payload, "model_dump") else (payload.dict() if hasattr(payload, "dict") else dict(payload))
        drive_url = data.get("drive_url", drive_url)
        name = data.get("name", name)
        description = data.get("description", description)
        category = data.get("category", category)
        task_id = data.get("task_id", task_id)
        phase_id = data.get("phase_id", phase_id)

    if not drive_url:
        raise ValueError("drive_url es obligatorio")

    drive_file_id, embed_url, inferred_type = normalize_drive_embed_url(drive_url)
    if not drive_file_id:
        raise ValueError("La URL proporcionada no es un enlace válido de Google Drive o Google Docs.")

    doc_name = name.strip() if name and name.strip() else f"Documento Drive ({drive_file_id[:8]})"

    return create_project_file(
        db,
        project_id=project_id,
        name=doc_name,
        description=description,
        category=category or "general",
        file_source="drive",
        file_url=drive_url,
        file_type=inferred_type,
        drive_file_id=drive_file_id,
        task_id=task_id,
        phase_id=phase_id,
        uploaded_by=uploaded_by,
        sede_id=sede_id,
    )


def get_project_files(
    db: Session,
    project_id: UUID | str,
    *,
    category: Optional[str] = None,
    file_source: Optional[str] = None,
    task_id: Optional[UUID | str] = None,
    phase_id: Optional[UUID | str] = None,
    search: Optional[str] = None,
    sede_id: Optional[UUID | str] = None,
) -> list[models.ProjectFile]:
    """Obtiene los archivos activos de la bóveda documental del proyecto."""
    project = get_project(db, project_id, sede_id=sede_id)
    if not project:
        raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    if task_id is not None:
        task = db.query(models.ProjectTask).filter(
            models.ProjectTask.id == _to_uuid(task_id),
            models.ProjectTask.project_id == project.id,
            models.ProjectTask.deleted_at.is_(None),
        ).first()
        if not task:
            raise ValueError("La tarea asociada no pertenece a este proyecto")
    if phase_id is not None:
        phase = db.query(models.ProjectPhase).filter(
            models.ProjectPhase.id == _to_uuid(phase_id),
            models.ProjectPhase.project_id == project.id,
            models.ProjectPhase.deleted_at.is_(None),
        ).first()
        if not phase:
            raise ValueError("La fase asociada no pertenece a este proyecto")

    q = db.query(models.ProjectFile).filter(
        models.ProjectFile.project_id == project.id,
        models.ProjectFile.deleted_at.is_(None),
    )
    if category:
        q = q.filter(models.ProjectFile.category == category)
    if file_source:
        q = q.filter(models.ProjectFile.file_source == file_source)
    if task_id:
        q = q.filter(models.ProjectFile.task_id == _to_uuid(task_id))
    if phase_id:
        q = q.filter(models.ProjectFile.phase_id == _to_uuid(phase_id))
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(models.ProjectFile.name.ilike(term) | models.ProjectFile.description.ilike(term))

    return q.order_by(models.ProjectFile.created_at.desc()).all()


def get_project_file(
    db: Session,
    file_id: UUID | str,
    *,
    project_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
) -> Optional[models.ProjectFile]:
    """Obtiene un archivo individual por ID con validación de proyecto y sede."""
    q = db.query(models.ProjectFile).filter(
        models.ProjectFile.id == file_id,
        models.ProjectFile.deleted_at.is_(None),
    )
    if project_id:
        q = q.filter(models.ProjectFile.project_id == project_id)

    f = q.first()
    if not f:
        return None

    if sede_id is not None:
        project = get_project(db, f.project_id, sede_id=sede_id)
        if not project:
            raise ValueError("Proyecto no encontrado o no pertenece a la sede (Axioma 3)")

    return f


def delete_project_file(
    db: Session,
    file_id: UUID | str,
    *,
    project_id: Optional[UUID | str] = None,
    user_id: Optional[UUID | str] = None,
    sede_id: Optional[UUID | str] = None,
) -> bool:
    """Soft-delete de archivo de la bóveda documental (Axioma 2)."""
    f = get_project_file(db, file_id, project_id=project_id, sede_id=sede_id)
    if not f:
        return False

    f.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def get_project_files_summary(
    db: Session,
    project_id: UUID | str,
    *,
    sede_id: Optional[UUID | str] = None,
) -> dict:
    """Consolida el resumen métrico de la bóveda documental."""
    files = get_project_files(db, project_id, sede_id=sede_id)
    total_files = len(files)
    total_size = sum(f.file_size or 0 for f in files)

    by_source: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for item in files:
        src = item.file_source or "local"
        by_source[src] = by_source.get(src, 0) + 1
        cat = item.category or "general"
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "project_id": str(project_id),
        "total_files": total_files,
        "total_size_bytes": total_size,
        "by_source": by_source,
        "by_category": by_category,
        "files": files,
    }


def summarize_whiteboard_canvas_elements(
    elements_json: str | list[Any] | None,
) -> dict[str, Any]:
    """Audita la composición de artefactos visuales de una pizarra colaborativa de planificación PMI."""
    import json as _json

    invalid_result: dict[str, Any] = {
        "is_valid_canvas": False,
        "element_count": 0,
        "type_distribution": {},
        "connector_count": 0,
        "text_bearing_count": 0,
        "canvas_complexity": "invalid",
    }

    if elements_json is None:
        elements: list[Any] = []
    elif isinstance(elements_json, str):
        try:
            parsed = _json.loads(elements_json)
        except Exception:
            return invalid_result
        if not isinstance(parsed, list):
            return invalid_result
        elements = parsed
    elif isinstance(elements_json, list):
        elements = elements_json
    else:
        return invalid_result

    if any(not isinstance(el, dict) for el in elements):
        return invalid_result

    connector_types = {"line", "arrow", "connector", "path"}
    text_types = {"text", "i-text", "textbox", "sticky", "note"}

    raw_counts: dict[str, int] = {}
    connector_count = 0
    text_bearing_count = 0

    for el in elements:
        norm_type = str(el.get("type") or "unknown").strip().lower() or "unknown"
        raw_counts[norm_type] = raw_counts.get(norm_type, 0) + 1
        if norm_type in connector_types:
            connector_count += 1
        has_non_empty_text = (
            isinstance(el.get("text"), str) and el.get("text").strip() != ""
        )
        if norm_type in text_types or has_non_empty_text:
            text_bearing_count += 1

    element_count = len(elements)
    type_distribution = {k: raw_counts[k] for k in sorted(raw_counts.keys())}

    if element_count == 0:
        canvas_complexity = "empty"
    elif element_count >= 5 and connector_count >= 1 and text_bearing_count >= 1:
        canvas_complexity = "rich_diagram"
    else:
        canvas_complexity = "basic_board"

    return {
        "is_valid_canvas": True,
        "element_count": element_count,
        "type_distribution": type_distribution,
        "connector_count": connector_count,
        "text_bearing_count": text_bearing_count,
        "canvas_complexity": canvas_complexity,
    }


def classify_cpm_float_risk_profile(
    cpm_metrics: dict[str, Any] | None,
    near_critical_threshold_days: int = 2,
) -> dict[str, Any]:
    """Evalúa la rigidez de holgura del cronograma CPM (PMBOK §6.5.2.2).

    Extrae `tasks` de `cpm_metrics` (acepta `dict {task_id: task}` vía
    .values() o `list[dict]`) y retorna:
    - `total_scheduled_tasks`: nº de tareas del grafo CPM.
    - `critical_tasks_count`: is_critical True o total_float <= 0.
    - `near_critical_tasks_count`: no críticas con 0 < total_float <=
      threshold (threshold = max(1, near_critical_threshold_days or 2)).
    - `buffered_tasks_count`: total - críticas - near_critical.
    - `critical_density_pct`: % de críticas (2 decimales; 0.0 sin tareas).
    - `schedule_rigidity_status`: 'empty_schedule' (sin tareas),
      'hyper_rigid' ((críticas + near) / total >= 0.75), 'moderate_float'
      (critical_density_pct <= 50 y no hyper_rigid) o 'tight_schedule'.
    """
    raw_tasks = (cpm_metrics or {}).get("tasks")
    if isinstance(raw_tasks, dict):
        task_rows = list(raw_tasks.values())
    elif isinstance(raw_tasks, list):
        task_rows = list(raw_tasks)
    else:
        task_rows = []

    total = len(task_rows)
    threshold = max(1, int(near_critical_threshold_days or 2))

    critical_tasks_count = 0
    near_critical_tasks_count = 0
    for row in task_rows:
        if not isinstance(row, dict):
            continue
        try:
            total_float = int(row.get("total_float", 0) or 0)
        except (TypeError, ValueError):
            total_float = 0
        is_critical = bool(row.get("is_critical")) or total_float <= 0
        if is_critical:
            critical_tasks_count += 1
        elif 0 < total_float <= threshold:
            near_critical_tasks_count += 1

    buffered_tasks_count = max(
        0, total - critical_tasks_count - near_critical_tasks_count
    )
    critical_density_pct = (
        round((critical_tasks_count / total) * 100.0, 2) if total > 0 else 0.0
    )

    if total == 0:
        schedule_rigidity_status = "empty_schedule"
    elif ((critical_tasks_count + near_critical_tasks_count) / total) >= 0.75:
        schedule_rigidity_status = "hyper_rigid"
    elif critical_density_pct <= 50.0:
        schedule_rigidity_status = "moderate_float"
    else:
        schedule_rigidity_status = "tight_schedule"

    return {
        "total_scheduled_tasks": total,
        "critical_tasks_count": critical_tasks_count,
        "near_critical_tasks_count": near_critical_tasks_count,
        "buffered_tasks_count": buffered_tasks_count,
        "critical_density_pct": critical_density_pct,
        "schedule_rigidity_status": schedule_rigidity_status,
    }


def evaluate_dependency_network_bottlenecks(
    edges: Optional[list[tuple[Any, Any]]] = None,
    high_degree_threshold: int = 3,
) -> dict:
    """Analiza la topología de dependencias de actividades (PMBOK §6.3 Sequence Activities).

    Detección de cuellos de botella Merge/Burst sobre las aristas de
    dependencia (predecesora → sucesora), normalizando cada par a strings
    stripped, ignorando pares con extremos vacíos, self-loops
    (u == v) y duplicados. `threshold = max(2, high_degree_threshold or 3)`
    define cuándo un nodo es hub de congestión (in + out >= threshold):
    - `total_nodes` / `total_unique_edges`: población única del grafo.
    - `max_in_degree` / `max_out_degree`: grados extremos.
    - `merge_point_nodes`: convergencia (in_degree >= 2), ordenados.
    - `burst_point_nodes`: divergencia (out_degree >= 2), ordenados.
    - `bottleneck_nodes`: hubs de alta congestión (in+out >= threshold).
    - `network_complexity_status`: 'disconnected' (0 aristas únicas),
      'high_congestion_hubs' (≥ 1 bottleneck), 'convergent_divergent'
      (merge o burst) o 'linear_chain'.
    """
    from collections import defaultdict

    unique_edges: set[tuple[str, str]] = set()
    if edges:
        for u, v in edges:
            u_str = str(u).strip()
            v_str = str(v).strip()
            if not u_str or not v_str or u_str == v_str:
                continue
            unique_edges.add((u_str, v_str))

    nodes: set[str] = set()
    in_degree: dict[str, int] = defaultdict(int)
    out_degree: dict[str, int] = defaultdict(int)
    for u_str, v_str in unique_edges:
        nodes.add(u_str)
        nodes.add(v_str)
        in_degree[v_str] += 1
        out_degree[u_str] += 1

    total_nodes = len(nodes)
    total_unique_edges = len(unique_edges)
    max_in_degree = max(in_degree.values(), default=0)
    max_out_degree = max(out_degree.values(), default=0)
    merge_point_nodes = sorted([n for n in nodes if in_degree[n] >= 2])
    burst_point_nodes = sorted([n for n in nodes if out_degree[n] >= 2])

    threshold = max(2, int(high_degree_threshold or 3))
    bottleneck_nodes = sorted(
        [n for n in nodes if (in_degree[n] + out_degree[n]) >= threshold]
    )

    if total_unique_edges == 0:
        network_complexity_status = "disconnected"
    elif len(bottleneck_nodes) > 0:
        network_complexity_status = "high_congestion_hubs"
    elif len(merge_point_nodes) > 0 or len(burst_point_nodes) > 0:
        network_complexity_status = "convergent_divergent"
    else:
        network_complexity_status = "linear_chain"

    return {
        "total_nodes": total_nodes,
        "total_unique_edges": total_unique_edges,
        "max_in_degree": max_in_degree,
        "max_out_degree": max_out_degree,
        "merge_point_nodes": merge_point_nodes,
        "burst_point_nodes": burst_point_nodes,
        "bottleneck_nodes": bottleneck_nodes,
        "network_complexity_status": network_complexity_status,
    }

"""Projects CRUD — corregido para cumplir los 3 axiomas del Kernel CCF."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from backend import models, schemas
from backend.crud.crm import resolve_persona_id_for_user
from backend.models_shared import _utcnow

# ── Helper ──────────────────────────────────────────────


def get_user_persona_id(db: Session, user_id: UUID | str | None) -> Optional[UUID]:
    """Obtiene persona.id desde el identificador canónico del usuario."""
    persona_id = resolve_persona_id_for_user(db, user_id)
    return UUID(str(persona_id)) if persona_id else None


# ── Projects ────────────────────────────────────────────


def create_project(
    db: Session,
    project: schemas.ProjectCreate,
    *,
    owner_persona_id: UUID | str,
    sede_id: UUID | str,
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
    db.commit()
    db.refresh(row)
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
        )
        db.add(phase)
        created.append(phase)
    db.commit()
    for p in created:
        db.refresh(p)
    return created


def create_default_phases(db: Session, project_id):
    defaults = [
        {"name": "Por Hacer", "slug": "todo", "color": "#94a3b8"},
        {"name": "En Curso", "slug": "in_progress", "color": "#3b82f6"},
        {"name": "Revisión", "slug": "review", "color": "#f59e0b"},
        {"name": "Completado", "slug": "completed", "color": "#10b981"},
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
    return row


def update_milestone(
    db: Session, milestone_id, payload: schemas.ProjectMilestoneUpdate
) -> Optional[models.ProjectMilestone]:
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


def get_task_supplies(db: Session, task_id):
    return (
        db.query(models.TaskSupply)
        .filter(models.TaskSupply.task_id == task_id, models.TaskSupply.deleted_at.is_(None))
        .order_by(models.TaskSupply.id.asc())
        .all()
    )


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


def get_project_kpis(db: Session, project_id: UUID | str) -> list[models.ProjectKPI]:
    return (
        db.query(models.ProjectKPI)
        .filter(models.ProjectKPI.project_id == project_id, models.ProjectKPI.deleted_at.is_(None))
        .order_by(models.ProjectKPI.created_at.asc())
        .all()
    )


def get_project_kpi(db: Session, project_id: UUID | str, kpi_id: UUID | str) -> Optional[models.ProjectKPI]:
    return (
        db.query(models.ProjectKPI)
        .filter(
            models.ProjectKPI.id == kpi_id,
            models.ProjectKPI.project_id == project_id,
            models.ProjectKPI.deleted_at.is_(None),
        )
        .first()
    )


def create_project_kpi(
    db: Session, project_id: UUID | str, kpi_in: schemas.ProjectKPICreate
) -> models.ProjectKPI:
    data = kpi_in.model_dump()
    row = models.ProjectKPI(project_id=project_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_project_kpi(
    db: Session, project_id: UUID | str, kpi_id: UUID | str, kpi_in: schemas.ProjectKPIUpdate
) -> Optional[models.ProjectKPI]:
    row = get_project_kpi(db, project_id, kpi_id)
    if not row:
        return None
    for k, v in kpi_in.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def delete_project_kpi(db: Session, project_id: UUID | str, kpi_id: UUID | str) -> bool:
    row = get_project_kpi(db, project_id, kpi_id)
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Dependencies (Gantt) ──────────────────────────────


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
    existing = (
        db.query(models.ProjectTaskDependency)
        .filter(
            models.ProjectTaskDependency.predecessor_id == dep_in.predecessor_id,
            models.ProjectTaskDependency.successor_id == dep_in.successor_id,
            models.ProjectTaskDependency.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        return existing
    row = models.ProjectTaskDependency(
        project_id=project_id,
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
    paid_sum = sum(e.amount for e in expenses if e.status == "paid")
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
    if row and row.creator:
        row.creator_name = row.creator.nombre_completo
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
    if row.creator:
        row.creator_name = row.creator.nombre_completo
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
    for k, v in expense_in.model_dump(exclude_unset=True).items():
        if v is not None:
            if k == "amount":
                setattr(row, k, round(float(v), 2))
            else:
                setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    recalculate_project_budget(db, project_id)
    if row.creator:
        row.creator_name = row.creator.nombre_completo
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
    paid = sum(e.amount for e in expenses if e.status == "paid")

    # Actualizar budget_spent si difiere
    if project.budget_spent != round(paid, 2):
        project.budget_spent = round(paid, 2)
        db.commit()
        db.refresh(project)

    remaining = max(0.0, allocated - paid)
    burn_rate = round((paid / allocated * 100), 2) if allocated > 0 else 0.0

    by_category: dict[str, float] = {}
    for e in expenses:
        cat = e.category or "general"
        by_category[cat] = round(by_category.get(cat, 0.0) + float(e.amount), 2)

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
        "by_category": by_category,
    }


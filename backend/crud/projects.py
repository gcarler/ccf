"""Projects CRUD — corregido para cumplir los 3 axiomas del Kernel CCF."""

from datetime import datetime, timezone, timedelta
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


def create_project_risk(
    db: Session,
    project_id: UUID | str,
    risk_in: schemas.ProjectRiskCreate,
) -> models.ProjectRisk:
    prob = risk_in.probability or 3
    imp = risk_in.impact or 3
    sev = prob * imp
    row = models.ProjectRisk(
        project_id=project_id,
        title=risk_in.title,
        category=risk_in.category or "tecnico",
        probability=prob,
        impact=imp,
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
    row = get_project_risk(db, project_id, risk_id)
    if not row:
        return None
    data = risk_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)

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
    risk = get_project_risk(db, project_id, risk_id)
    if not risk:
        return None

    # Marcar el riesgo como ocurrido
    risk.status = "occurred"
    risk.updated_at = datetime.now(timezone.utc)

    sev = (risk.probability or 1) * (risk.impact or 1)
    priority = "urgent" if sev >= 15 else ("high" if sev >= 10 else "medium")

    desc_lines = [
        f"**[INCIDENCIA RAID MATERIALIZADA]**",
        f"- **Categoría:** {risk.category}",
        f"- **Probabilidad:** {risk.probability}/5 | **Impacto:** {risk.impact}/5 (Severidad: {sev}/25)",
        "",
        "**Plan de Contingencia Activado:**",
        f"{risk.contingency_plan or 'No especificado'}",
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

        # Regla de capacidad:
        # - Overloaded: 5 o más activas, o 2 o más vencidas, o 2 o más urgentes
        # - Balanced: 2 a 4 activas
        # - Available: 0 a 1 activas
        if active_count >= 5 or len(overdue_t) >= 2 or urgent_count >= 2:
            status = "overloaded"
            overloaded_count += 1
        elif active_count >= 2:
            status = "balanced"
            balanced_count += 1
        else:
            status = "available"
            available_count += 1

        workload_pct = min(100, round((active_count / 5.0) * 100))

        # Tareas serializadas para UI
        task_items = []
        for t in assigned:
            is_od = False
            if t.status != "completed" and t.due_date:
                t_due = t.due_date if getattr(t.due_date, "tzinfo", None) else t.due_date.replace(tzinfo=timezone.utc)
                is_od = bool(t_due < now_utc)
            task_items.append({
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
                "is_overdue": is_od,
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

    tasks = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .order_by(models.ProjectTask.order_index.asc())
        .all()
    )

    if not tasks:
        return {
            "project_id": str(project.id),
            "total_duration_days": 0,
            "critical_tasks_count": 0,
            "critical_path_task_ids": [],
            "tasks": [],
            "has_cycles": False,
        }

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

    for dep in deps:
        p_id = str(dep.predecessor_id)
        s_id = str(dep.successor_id)
        if p_id in task_map and s_id in task_map and p_id != s_id:
            lag = dep.lag_days or 0
            succs[p_id].append((s_id, lag))
            preds[s_id].append((p_id, lag))
            in_degree[s_id] += 1

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

    snapshot_data = {
        "project_id": str(project.id),
        "project_title": project.title,
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
    for l in logs:
        _prepare_time_log_response(l)
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

    log.deleted_at = datetime.now(timezone.utc)
    db.commit()
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

    for l in logs:
        h = float(l.hours or 0.0)
        total_hours += h
        if l.is_billable:
            billable_hours += h

        # Tarea
        t_id = str(l.task_id) if l.task_id else "general"
        t_title = l.task.title if l.task else "General del Proyecto"
        if t_id not in task_map:
            task_map[t_id] = {
                "task_id": t_id,
                "task_title": t_title,
                "total_hours": 0.0,
                "billable_hours": 0.0,
                "logs_count": 0,
            }
        task_map[t_id]["total_hours"] = round(task_map[t_id]["total_hours"] + h, 2)
        if l.is_billable:
            task_map[t_id]["billable_hours"] = round(task_map[t_id]["billable_hours"] + h, 2)
        task_map[t_id]["logs_count"] += 1

        # Miembro
        p_id = str(l.persona_id)
        p_name = "Miembro"
        p_avatar = None
        if l.persona:
            p = l.persona
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
        if l.is_billable:
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
) -> models.ProjectTemplate:
    effective_creator = creator_persona_id or created_by
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
        sede_id=template_in.sede_id or sede_id,
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
) -> Optional[models.ProjectTemplate]:
    template = get_project_template(db, template_id, sede_id=sede_id)
    if not template:
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
) -> bool:
    effective_sede = sede_id if sede_id is not None else user_sede_id
    template = get_project_template(db, template_id, sede_id=effective_sede)
    if not template:
        return False

    template.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


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






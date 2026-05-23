"""Projects and project tasks CRUD."""

from typing import Optional

from sqlalchemy.orm import Session

from backend import models, schemas

# ── Projects ────────────────────────────────────────────


def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Project)
        .order_by(models.Project.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def update_project(db: Session, project_id: int, payload: schemas.ProjectUpdate):
    row = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_project(db: Session, project_id: int) -> bool:
    row = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Project Tasks ───────────────────────────────────────


def create_project_task(db: Session, task: schemas.ProjectTaskCreate):
    db_task = models.ProjectTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_project_tasks(db: Session, project_id: int, status: Optional[str] = None):
    query = db.query(models.ProjectTask).filter(
        models.ProjectTask.project_id == project_id
    )
    if status:
        query = query.filter(models.ProjectTask.status == status)
    return query.order_by(models.ProjectTask.order_index.asc()).all()


def get_project_task(db: Session, task_id: int):
    return db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()


def update_project_task(db: Session, task_id: int, payload: schemas.ProjectTaskUpdate):
    row = db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_project_task(db: Session, task_id: int) -> bool:
    row = db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Project Phases ───────────────────────────────────────


def get_project_phases(db: Session, project_id: int):
    return (
        db.query(models.ProjectPhase)
        .filter(models.ProjectPhase.project_id == project_id)
        .order_by(models.ProjectPhase.order_index)
        .all()
    )


def set_project_phases(
    db: Session, project_id: int, phases: list[dict]
) -> list[models.ProjectPhase]:
    """Replace all phases for a project. `phases` is a list of {name, slug, color, order_index}."""
    db.query(models.ProjectPhase).filter(
        models.ProjectPhase.project_id == project_id
    ).delete()
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


def create_default_phases(db: Session, project_id: int):
    """Create default phases for a new project."""
    defaults = [
        {"name": "Por Hacer", "slug": "todo", "color": "#94a3b8"},
        {"name": "En Curso", "slug": "in_progress", "color": "#3b82f6"},
        {"name": "Revisión", "slug": "review", "color": "#f59e0b"},
        {"name": "Completado", "slug": "done", "color": "#10b981"},
    ]
    return set_project_phases(db, project_id, defaults)


# ── Project Comments ───────────────────────────────────


def get_project_comments(
    db: Session, project_id: int | None = None, task_id: int | None = None
):
    query = db.query(models.ProjectComment)
    if project_id is not None:
        query = query.filter(models.ProjectComment.project_id == project_id)
    if task_id is not None:
        query = query.filter(models.ProjectComment.task_id == task_id)
    return query.order_by(models.ProjectComment.created_at.desc()).all()


def get_comment(db: Session, comment_id: int):
    return (
        db.query(models.ProjectComment)
        .filter(models.ProjectComment.id == comment_id)
        .first()
    )


def create_comment(
    db: Session,
    project_id: int,
    author_id: int,
    content: str,
    task_id: int | None = None,
):
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


def update_comment(
    db: Session, comment_id: int, content: str
) -> Optional[models.ProjectComment]:
    row = (
        db.query(models.ProjectComment)
        .filter(models.ProjectComment.id == comment_id)
        .first()
    )
    if not row:
        return None
    row.content = content
    db.commit()
    db.refresh(row)
    return row


def delete_comment(db: Session, comment_id: int) -> bool:
    row = (
        db.query(models.ProjectComment)
        .filter(models.ProjectComment.id == comment_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Project Milestones ─────────────────────────────────


def get_project_milestones(db: Session, project_id: int):
    return (
        db.query(models.ProjectMilestone)
        .filter(models.ProjectMilestone.project_id == project_id)
        .order_by(models.ProjectMilestone.due_date.asc())
        .all()
    )


def get_milestone(db: Session, milestone_id: int):
    return (
        db.query(models.ProjectMilestone)
        .filter(models.ProjectMilestone.id == milestone_id)
        .first()
    )


def create_milestone(
    db: Session,
    project_id: int,
    title: str,
    description: str | None = None,
    due_date=None,
    status: str = "pending",
):
    row = models.ProjectMilestone(
        project_id=project_id,
        title=title,
        description=description,
        due_date=due_date,
        status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_milestone(
    db: Session, milestone_id: int, payload: schemas.ProjectMilestoneUpdate
) -> Optional[models.ProjectMilestone]:
    row = (
        db.query(models.ProjectMilestone)
        .filter(models.ProjectMilestone.id == milestone_id)
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_milestone(db: Session, milestone_id: int) -> bool:
    row = (
        db.query(models.ProjectMilestone)
        .filter(models.ProjectMilestone.id == milestone_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Project Attachments ────────────────────────────────


def get_task_attachments(db: Session, task_id: int):
    return (
        db.query(models.ProjectAttachment)
        .filter(models.ProjectAttachment.task_id == task_id)
        .order_by(models.ProjectAttachment.created_at.desc())
        .all()
    )


def get_attachment(db: Session, attachment_id: int):
    return (
        db.query(models.ProjectAttachment)
        .filter(models.ProjectAttachment.id == attachment_id)
        .first()
    )


def create_attachment(
    db: Session,
    task_id: int,
    file_url: str,
    file_name: str,
    file_size: int = 0,
    mime_type: str | None = None,
    uploader_id: int | None = None,
):
    row = models.ProjectAttachment(
        task_id=task_id,
        file_url=file_url,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type,
        uploader_id=uploader_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_attachment(db: Session, attachment_id: int) -> bool:
    row = (
        db.query(models.ProjectAttachment)
        .filter(models.ProjectAttachment.id == attachment_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Project Whiteboard ─────────────────────────────────


def get_project_whiteboard(db: Session, project_id: int):
    return (
        db.query(models.ProjectWhiteboard)
        .filter(models.ProjectWhiteboard.project_id == project_id)
        .first()
    )


def update_project_whiteboard(
    db: Session, project_id: int, payload: schemas.ProjectWhiteboardUpdate
) -> models.ProjectWhiteboard:
    row = (
        db.query(models.ProjectWhiteboard)
        .filter(models.ProjectWhiteboard.project_id == project_id)
        .first()
    )
    if not row:
        row = models.ProjectWhiteboard(
            project_id=project_id, canvas_data=payload.canvas_data or {}
        )
        db.add(row)
    else:
        row.canvas_data = payload.canvas_data or row.canvas_data
    db.commit()
    db.refresh(row)
    return row


# ── Project Wiki / Documents ───────────────────────────


def get_project_wiki(db: Session, project_id: int):
    return (
        db.query(models.ProjectDocument)
        .filter(
            models.ProjectDocument.project_id == project_id,
            models.ProjectDocument.doc_type == "wiki",
        )
        .first()
    )


def update_project_wiki(
    db: Session, project_id: int, content: str, updated_by: int | None = None
) -> models.ProjectDocument:
    row = (
        db.query(models.ProjectDocument)
        .filter(
            models.ProjectDocument.project_id == project_id,
            models.ProjectDocument.doc_type == "wiki",
        )
        .first()
    )
    if not row:
        row = models.ProjectDocument(
            project_id=project_id,
            doc_type="wiki",
            content=content,
            created_by=updated_by,
        )
        db.add(row)
    else:
        row.content = content
        row.updated_by = updated_by
    db.commit()
    db.refresh(row)
    return row


# ── Project Supplies (TaskSupply) ───────────────────────


def get_task_supplies(db: Session, task_id: int):
    return (
        db.query(models.TaskSupply)
        .filter(models.TaskSupply.task_id == task_id)
        .order_by(models.TaskSupply.created_at.asc())
        .all()
    )


def get_supply(db: Session, supply_id: int):
    return db.query(models.TaskSupply).filter(models.TaskSupply.id == supply_id).first()


def create_supply(
    db: Session,
    task_id: int,
    name: str,
    quantity: int = 1,
    estimated_cost: float = 0.0,
    status: str = "pending",
    requested_by: int | None = None,
):
    row = models.TaskSupply(
        task_id=task_id,
        name=name,
        quantity=quantity,
        estimated_cost=estimated_cost,
        status=status,
        requested_by=requested_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_supply(
    db: Session, supply_id: int, payload: schemas.TaskSupplyUpdate
) -> Optional[models.TaskSupply]:
    row = db.query(models.TaskSupply).filter(models.TaskSupply.id == supply_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_supply(db: Session, supply_id: int) -> bool:
    row = db.query(models.TaskSupply).filter(models.TaskSupply.id == supply_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Project Activity Logs ──────────────────────────────


def get_project_activities(db: Session, project_id: int, limit: int = 100):
    return (
        db.query(models.ProjectActivityLog)
        .filter(models.ProjectActivityLog.project_id == project_id)
        .order_by(models.ProjectActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )


def create_activity_log(
    db: Session,
    project_id: int,
    action: str,
    user_id: int | None = None,
    detail: str | None = None,
):
    row = models.ProjectActivityLog(
        project_id=project_id,
        action=action,
        user_id=user_id,
        detail=detail,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Project Inbox State ────────────────────────────────


def get_inbox_state(db: Session, user_id: int, project_id: int | None = None):
    query = db.query(models.ProjectInboxState).filter(
        models.ProjectInboxState.user_id == user_id
    )
    if project_id is not None:
        query = query.filter(models.ProjectInboxState.project_id == project_id)
    return query.all()


def update_inbox_state(db: Session, user_id: int, item_id: int, is_read: bool = True):
    row = (
        db.query(models.ProjectInboxState)
        .filter(
            models.ProjectInboxState.user_id == user_id,
            models.ProjectInboxState.item_id == item_id,
        )
        .first()
    )
    if not row:
        row = models.ProjectInboxState(
            user_id=user_id, item_id=item_id, is_read=is_read
        )
        db.add(row)
    else:
        row.is_read = is_read
    db.commit()
    db.refresh(row)
    return row


# ── Portfolio / Summary Queries ────────────────────────


def get_portfolio_summary(db: Session):
    """Return count of projects by status with total tasks."""
    from sqlalchemy import func as sa_func

    rows = (
        db.query(
            models.Project.status,
            sa_func.count(models.Project.id),
            sa_func.count(models.ProjectTask.id),
        )
        .outerjoin(models.ProjectTask)
        .group_by(models.Project.status)
        .all()
    )
    return [{"status": r[0], "projects": r[1], "tasks": r[2]} for r in rows]


def get_workload_summary(db: Session):
    """Return task counts per assignee."""
    from sqlalchemy import func as sa_func

    rows = (
        db.query(
            models.ProjectTask.assignee_id,
            sa_func.count(models.ProjectTask.id),
            sa_func.sum(
                sa_func.case((models.ProjectTask.status == "done", 1), else_=0)
            ),
        )
        .filter(models.ProjectTask.assignee_id.isnot(None))
        .group_by(models.ProjectTask.assignee_id)
        .all()
    )
    return [{"assignee_id": r[0], "total": r[1], "completed": r[2] or 0} for r in rows]

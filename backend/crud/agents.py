"""Agent tasks and insights CRUD."""

from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.models_shared import _utcnow


def create_agent_task(db: Session, payload: schemas.AgentTaskCreate):
    row = models.AgentTask(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        source=payload.source,
        status="pending",
        assigned_to=payload.assigned_to,
        agent_type=payload.agent_type,
        task_data=payload.metadata,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_tasks(db: Session, status: str | None = None):
    query = db.query(models.AgentTask).filter(models.AgentTask.deleted_at.is_(None))
    if status:
        query = query.filter(models.AgentTask.status == status)
    return query.order_by(models.AgentTask.created_at.desc()).all()


def update_agent_task(db: Session, task_id: UUID, payload: schemas.AgentTaskUpdate):
    row = db.query(models.AgentTask).filter(
        models.AgentTask.id == task_id, models.AgentTask.deleted_at.is_(None)
    ).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "metadata":
            setattr(row, "task_data", value)
        else:
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def create_agent_insight(db: Session, payload: schemas.AgentInsightCreate):
    row = models.AgentInsight(
        title=payload.title,
        insight_type=payload.insight_type,
        description=payload.description,
        confidence=int(payload.confidence * 100),
        source_agent=payload.source_agent,
        insight_payload=payload.payload,
        insight_data=payload.metadata,
        acknowledged=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_insights(db: Session, acknowledged: bool | None = None):
    query = db.query(models.AgentInsight).filter(models.AgentInsight.deleted_at.is_(None))
    if acknowledged is not None:
        query = query.filter(models.AgentInsight.acknowledged == acknowledged)
    return query.order_by(models.AgentInsight.created_at.desc()).all()


def acknowledge_insight(db: Session, insight_id: UUID):
    row = (
        db.query(models.AgentInsight)
        .filter(models.AgentInsight.id == insight_id, models.AgentInsight.deleted_at.is_(None))
        .first()
    )
    if not row:
        return None
    row.acknowledged = True
    db.commit()
    db.refresh(row)
    return row


def delete_agent_task(db: Session, task_id: UUID) -> bool:
    row = db.query(models.AgentTask).filter(
        models.AgentTask.id == task_id, models.AgentTask.deleted_at.is_(None)
    ).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def delete_agent_insight(db: Session, insight_id: UUID) -> bool:
    row = (
        db.query(models.AgentInsight)
        .filter(models.AgentInsight.id == insight_id, models.AgentInsight.deleted_at.is_(None))
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True

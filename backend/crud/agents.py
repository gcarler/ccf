"""Agent tasks and insights CRUD."""
from sqlalchemy.orm import Session

from backend import models, schemas


def create_agent_task(db: Session, payload: schemas.AgentTaskCreate):
    row = models.AgentTask(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        source=payload.source,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_tasks(db: Session, status: str | None = None):
    query = db.query(models.AgentTask)
    if status:
        query = query.filter(models.AgentTask.status == status)
    return query.order_by(models.AgentTask.created_at.desc()).all()


def update_agent_task(db: Session, task_id: int, payload: schemas.AgentTaskUpdate):
    row = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def create_agent_insight(db: Session, payload: schemas.AgentInsightCreate):
    row = models.AgentInsight(
        title=payload.title,
        insight_type=payload.insight_type,
        payload=payload.payload,
        acknowledged=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_insights(db: Session, acknowledged: bool | None = None):
    query = db.query(models.AgentInsight)
    if acknowledged is not None:
        query = query.filter(models.AgentInsight.acknowledged == acknowledged)
    return query.order_by(models.AgentInsight.created_at.desc()).all()


def acknowledge_insight(db: Session, insight_id: int):
    row = db.query(models.AgentInsight).filter(models.AgentInsight.id == insight_id).first()
    if not row:
        return None
    row.acknowledged = True
    db.commit()
    db.refresh(row)
    return row


def delete_agent_task(db: Session, task_id: int) -> bool:
    row = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def delete_agent_insight(db: Session, insight_id: int) -> bool:
    row = db.query(models.AgentInsight).filter(models.AgentInsight.id == insight_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True

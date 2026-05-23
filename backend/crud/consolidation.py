"""Consolidation CRUD: assignments, interactions, follow-up tasks.

Cases already exist in crud/crm.py.
"""
from typing import Optional, List

from sqlalchemy.orm import Session

from backend import models
from backend.schemas.crm import (
    ConsolidationAssignmentCreate,
    ConsolidationAssignmentUpdate,
    ConsolidationInteractionCreate,
    ConsolidationInteractionUpdate,
    ConsolidationFollowUpTaskCreate,
    ConsolidationFollowUpTaskUpdate,
)


# ── Consolidation Assignments ────────────────────────────────────────────

def get_consolidation_assignments(
    db: Session,
    case_id: Optional[int] = None,
    assigned_to_member_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[models.ConsolidationAssignment]:
    query = db.query(models.ConsolidationAssignment)
    if case_id is not None:
        query = query.filter(models.ConsolidationAssignment.case_id == case_id)
    if assigned_to_member_id is not None:
        query = query.filter(models.ConsolidationAssignment.assigned_to_member_id == assigned_to_member_id)
    if status is not None:
        query = query.filter(models.ConsolidationAssignment.status == status)
    return query.order_by(models.ConsolidationAssignment.created_at.desc()).all()


def get_consolidation_assignment(db: Session, assignment_id: int) -> Optional[models.ConsolidationAssignment]:
    return db.query(models.ConsolidationAssignment).filter(
        models.ConsolidationAssignment.id == assignment_id
    ).first()


def create_consolidation_assignment(
    db: Session, payload: ConsolidationAssignmentCreate
) -> models.ConsolidationAssignment:
    row = models.ConsolidationAssignment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_consolidation_assignment(
    db: Session, assignment_id: int, payload: ConsolidationAssignmentUpdate
) -> Optional[models.ConsolidationAssignment]:
    row = db.query(models.ConsolidationAssignment).filter(
        models.ConsolidationAssignment.id == assignment_id
    ).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_consolidation_assignment(db: Session, assignment_id: int) -> bool:
    row = db.query(models.ConsolidationAssignment).filter(
        models.ConsolidationAssignment.id == assignment_id
    ).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Consolidation Interactions ───────────────────────────────────────────

def get_consolidation_interactions(
    db: Session,
    case_id: Optional[int] = None,
    performed_by_member_id: Optional[int] = None,
    interaction_type: Optional[str] = None,
) -> List[models.ConsolidationInteraction]:
    query = db.query(models.ConsolidationInteraction)
    if case_id is not None:
        query = query.filter(models.ConsolidationInteraction.case_id == case_id)
    if performed_by_member_id is not None:
        query = query.filter(models.ConsolidationInteraction.performed_by_member_id == performed_by_member_id)
    if interaction_type is not None:
        query = query.filter(models.ConsolidationInteraction.interaction_type == interaction_type)
    return query.order_by(models.ConsolidationInteraction.interaction_date.desc()).all()


def get_consolidation_interaction(db: Session, interaction_id: int) -> Optional[models.ConsolidationInteraction]:
    return db.query(models.ConsolidationInteraction).filter(
        models.ConsolidationInteraction.id == interaction_id
    ).first()


def create_consolidation_interaction(
    db: Session, payload: ConsolidationInteractionCreate
) -> models.ConsolidationInteraction:
    row = models.ConsolidationInteraction(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_consolidation_interaction(
    db: Session, interaction_id: int, payload: ConsolidationInteractionUpdate
) -> Optional[models.ConsolidationInteraction]:
    row = db.query(models.ConsolidationInteraction).filter(
        models.ConsolidationInteraction.id == interaction_id
    ).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_consolidation_interaction(db: Session, interaction_id: int) -> bool:
    row = db.query(models.ConsolidationInteraction).filter(
        models.ConsolidationInteraction.id == interaction_id
    ).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Consolidation Follow-Up Tasks ────────────────────────────────────────

def get_consolidation_follow_up_tasks(
    db: Session,
    case_id: Optional[int] = None,
    assignment_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[models.ConsolidationFollowUpTask]:
    query = db.query(models.ConsolidationFollowUpTask)
    if case_id is not None:
        query = query.filter(models.ConsolidationFollowUpTask.case_id == case_id)
    if assignment_id is not None:
        query = query.filter(models.ConsolidationFollowUpTask.assignment_id == assignment_id)
    if status is not None:
        query = query.filter(models.ConsolidationFollowUpTask.status == status)
    return query.order_by(models.ConsolidationFollowUpTask.due_date.asc()).all()


def get_consolidation_follow_up_task(db: Session, task_id: int) -> Optional[models.ConsolidationFollowUpTask]:
    return db.query(models.ConsolidationFollowUpTask).filter(
        models.ConsolidationFollowUpTask.id == task_id
    ).first()


def create_consolidation_follow_up_task(
    db: Session, payload: ConsolidationFollowUpTaskCreate
) -> models.ConsolidationFollowUpTask:
    row = models.ConsolidationFollowUpTask(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_consolidation_follow_up_task(
    db: Session, task_id: int, payload: ConsolidationFollowUpTaskUpdate
) -> Optional[models.ConsolidationFollowUpTask]:
    row = db.query(models.ConsolidationFollowUpTask).filter(
        models.ConsolidationFollowUpTask.id == task_id
    ).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_consolidation_follow_up_task(db: Session, task_id: int) -> bool:
    row = db.query(models.ConsolidationFollowUpTask).filter(
        models.ConsolidationFollowUpTask.id == task_id
    ).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True

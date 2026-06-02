"""Consolidation CRUD: assignments, interactions, follow-up tasks.

Cases already exist in crud/crm.py.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models_shared import _utcnow
from backend import models
from backend.schemas.crm import (ConsolidationAssignmentCreate,
                                 ConsolidationAssignmentUpdate,
                                 ConsolidationTaskCreate,
                                 ConsolidationTaskUpdate,
                                 ConsolidationInteractionCreate,
                                 ConsolidationInteractionUpdate)

# ── Consolidation Assignments ────────────────────────────────────────────


def get_consolidation_assignments(
    db: Session,
    case_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[models.ConsolidationAssignment]:
    query = db.query(models.ConsolidationAssignment)
    if case_id is not None:
        query = query.filter(models.ConsolidationAssignment.case_id == case_id)
    if assigned_to_id is not None:
        query = query.filter(
            models.ConsolidationAssignment.assigned_to_id
            == assigned_to_id
        )
    if status is not None:
        query = query.filter(models.ConsolidationAssignment.status == status)
    return query.order_by(models.ConsolidationAssignment.created_at.desc()).all()


def get_consolidation_assignment(
    db: Session, assignment_id: int
) -> Optional[models.ConsolidationAssignment]:
    return (
        db.query(models.ConsolidationAssignment)
        .filter(models.ConsolidationAssignment.id == assignment_id)
        .first()
    )


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
    row = (
        db.query(models.ConsolidationAssignment)
        .filter(models.ConsolidationAssignment.id == assignment_id)
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_consolidation_assignment(db: Session, assignment_id: int) -> bool:
    row = (
        db.query(models.ConsolidationAssignment)
        .filter(models.ConsolidationAssignment.id == assignment_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Consolidation Interactions ───────────────────────────────────────────


def get_consolidation_interactions(
    db: Session,
    case_id: Optional[int] = None,
    performed_by_id: Optional[int] = None,
    interaction_type: Optional[str] = None,
) -> List[models.ConsolidationInteraction]:
    query = db.query(models.ConsolidationInteraction)
    if case_id is not None:
        query = query.filter(models.ConsolidationInteraction.case_id == case_id)
    if performed_by_id is not None:
        query = query.filter(
            models.ConsolidationInteraction.performed_by_id
            == performed_by_id
        )
    if interaction_type is not None:
        query = query.filter(
            models.ConsolidationInteraction.interaction_type == interaction_type
        )
    return query.order_by(models.ConsolidationInteraction.interaction_date.desc()).all()


def get_consolidation_interaction(
    db: Session, interaction_id: int
) -> Optional[models.ConsolidationInteraction]:
    return (
        db.query(models.ConsolidationInteraction)
        .filter(models.ConsolidationInteraction.id == interaction_id)
        .first()
    )


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
    row = (
        db.query(models.ConsolidationInteraction)
        .filter(models.ConsolidationInteraction.id == interaction_id)
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_consolidation_interaction(db: Session, interaction_id: int) -> bool:
    row = (
        db.query(models.ConsolidationInteraction)
        .filter(models.ConsolidationInteraction.id == interaction_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Consolidation Follow-Up Tasks ────────────────────────────────────────


def get_consolidation_tasks(
    db: Session,
    case_id: Optional[int] = None,
    assignment_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[models.ConsolidationTask]:
    query = db.query(models.ConsolidationTask)
    if case_id is not None:
        query = query.filter(models.ConsolidationTask.case_id == case_id)
    if assignment_id is not None:
        query = query.filter(
            models.ConsolidationTask.assignment_id == assignment_id
        )
    if status is not None:
        query = query.filter(models.ConsolidationTask.status == status)
    return query.order_by(models.ConsolidationTask.due_date.asc()).all()


def get_consolidation_task(
    db: Session, task_id: int
) -> Optional[models.ConsolidationTask]:
    return (
        db.query(models.ConsolidationTask)
        .filter(models.ConsolidationTask.id == task_id)
        .first()
    )


def create_consolidation_task(
    db: Session, payload: ConsolidationTaskCreate
) -> models.ConsolidationTask:
    row = models.ConsolidationTask(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_consolidation_task(
    db: Session, task_id: int, payload: ConsolidationTaskUpdate
) -> Optional[models.ConsolidationTask]:
    row = (
        db.query(models.ConsolidationTask)
        .filter(models.ConsolidationTask.id == task_id)
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_consolidation_task(db: Session, task_id: int) -> bool:
    row = (
        db.query(models.ConsolidationTask)
        .filter(models.ConsolidationTask.id == task_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True

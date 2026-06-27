"""Governance CRUD: automation_rules (admin_audit_logs already in audit.py)."""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from backend.models_shared import _utcnow

from backend import models
from backend.schemas.governance import (AutomationRuleCreate,
                                        AutomationRuleUpdate)


def get_automation_rules(db: Session, only_active: bool = False):
    query = db.query(models.AutomationRule)
    if only_active:
        query = query.filter(models.AutomationRule.is_active)
    return query.order_by(models.AutomationRule.name).all()


def get_automation_rule(db: Session, rule_id: UUID) -> Optional[models.AutomationRule]:
    return (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )


def create_automation_rule(
    db: Session, payload: AutomationRuleCreate
) -> models.AutomationRule:
    row = models.AutomationRule(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_automation_rule(
    db: Session, rule_id: UUID, payload: AutomationRuleUpdate
) -> Optional[models.AutomationRule]:
    row = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_automation_rule(db: Session, rule_id: UUID) -> bool:
    row = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def record_automation_run(db: Session, rule_id: UUID):
    """Update last_run timestamp for an automation rule."""
    row = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )
    if not row:
        return None
    row.last_run = _utcnow()
    db.commit()
    db.refresh(row)
    return row

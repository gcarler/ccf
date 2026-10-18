"""PMI project initiation, stakeholder engagement, and closure operations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models


def build_governance_summary(db: Session, project_id: UUID) -> dict:
    """Return compact charter, stakeholder matrix, and closure metrics for reports."""
    lifecycle = (
        db.query(models.ProjectLifecycle)
        .filter(models.ProjectLifecycle.project_id == project_id)
        .first()
    )
    quadrant_counts = {
        "manage_closely": 0,
        "keep_satisfied": 0,
        "keep_informed": 0,
        "monitor": 0,
    }
    grouped_counts = (
        db.query(models.ProjectStakeholder.quadrant, func.count(models.ProjectStakeholder.id))
        .filter(
            models.ProjectStakeholder.project_id == project_id,
            models.ProjectStakeholder.deleted_at.is_(None),
        )
        .group_by(models.ProjectStakeholder.quadrant)
        .all()
    )
    stakeholders_total = 0
    for quadrant, count in grouped_counts:
        stakeholders_total += int(count)
        if quadrant in quadrant_counts:
            quadrant_counts[quadrant] = int(count)

    authorized_at = lifecycle.authorized_at if lifecycle else None
    if authorized_at is not None and authorized_at.tzinfo is None:
        authorized_at = authorized_at.replace(tzinfo=timezone.utc)

    return {
        "charter_status": lifecycle.charter_status if lifecycle else "draft",
        "sponsor_id": str(lifecycle.sponsor_id) if lifecycle and lifecycle.sponsor_id else None,
        "authorized_at": authorized_at.isoformat() if authorized_at else None,
        "measurable_objectives_count": len(lifecycle.measurable_objectives or []) if lifecycle else 0,
        "stakeholders_total": stakeholders_total,
        "stakeholders_by_quadrant": quadrant_counts,
        "closure_status": lifecycle.closure_status if lifecycle else "open",
        "deliverables_accepted_verified": bool(lifecycle.deliverables_accepted_verified) if lifecycle else False,
        "financial_reconciliation_completed": bool(lifecycle.financial_reconciliation_completed) if lifecycle else False,
        "lessons_learned_count": len(lifecycle.lessons_learned or []) if lifecycle else 0,
    }


def get_lifecycle(db: Session, project_id: UUID) -> models.ProjectLifecycle:
    row = db.query(models.ProjectLifecycle).filter(models.ProjectLifecycle.project_id == project_id).first()
    return row or models.ProjectLifecycle(
        project_id=project_id,
        measurable_objectives=[],
        key_assumptions=[],
        key_constraints=[],
        high_level_risks=[],
        lessons_learned=[],
        charter_status="draft",
        closure_status="open",
        deliverables_accepted_verified=False,
        financial_reconciliation_completed=False,
        wiki_synced=False,
    )


def save_charter(db: Session, project_id: UUID, data: dict, actor_persona_id: UUID) -> models.ProjectLifecycle:
    row = get_lifecycle(db, project_id)
    if row.closure_status == "closed":
        raise HTTPException(status_code=409, detail="El ciclo de vida del proyecto está cerrado")
    was_authorized = row.charter_status == "authorized"
    requested_status = data.pop("charter_status", None)
    for field, value in data.items():
        setattr(row, field, value)
    if requested_status == "authorized":
        if not row.business_case or not row.strategic_justification:
            raise HTTPException(status_code=422, detail="El acta requiere caso de negocio y justificación estratégica")
        row.charter_status = "authorized"
        if not was_authorized:
            row.authorized_by = actor_persona_id
            row.authorized_at = datetime.now(timezone.utc)
    elif requested_status == "draft":
        if was_authorized:
            raise HTTPException(status_code=409, detail="El acta autorizada no puede volver a borrador")
        row.charter_status = "draft"
        row.authorized_by = None
        row.authorized_at = None
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_stakeholders(db: Session, project_id: UUID) -> list[models.ProjectStakeholder]:
    return (
        db.query(models.ProjectStakeholder)
        .filter(
            models.ProjectStakeholder.project_id == project_id,
            models.ProjectStakeholder.deleted_at.is_(None),
        )
        .order_by(models.ProjectStakeholder.created_at, models.ProjectStakeholder.id)
        .all()
    )


def _quadrant(power: int, interest: int) -> str:
    if power >= 3 and interest >= 3:
        return "manage_closely"
    if power >= 3:
        return "keep_satisfied"
    if interest >= 3:
        return "keep_informed"
    return "monitor"


def create_stakeholder(db: Session, project_id: UUID, data: dict) -> models.ProjectStakeholder:
    data["quadrant"] = _quadrant(data["power_level"], data["interest_level"])
    row = models.ProjectStakeholder(project_id=project_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_stakeholder(
    db: Session, project_id: UUID, stakeholder_id: UUID, data: dict
) -> models.ProjectStakeholder:
    row = (
        db.query(models.ProjectStakeholder)
        .filter(
            models.ProjectStakeholder.id == stakeholder_id,
            models.ProjectStakeholder.project_id == project_id,
            models.ProjectStakeholder.deleted_at.is_(None),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Interesado no encontrado")
    for field, value in data.items():
        setattr(row, field, value)
    if row.persona_id is None and not (row.display_name or "").strip() and not (row.role_title or "").strip():
        raise HTTPException(status_code=422, detail="El interesado requiere Persona, nombre o cargo")
    row.quadrant = _quadrant(row.power_level, row.interest_level)
    db.commit()
    db.refresh(row)
    return row


def soft_delete_stakeholder(db: Session, project_id: UUID, stakeholder_id: UUID) -> None:
    row = (
        db.query(models.ProjectStakeholder)
        .filter(
            models.ProjectStakeholder.id == stakeholder_id,
            models.ProjectStakeholder.project_id == project_id,
            models.ProjectStakeholder.deleted_at.is_(None),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Interesado no encontrado")
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()


def finalize_closure(
    db: Session, project_id: UUID, data: dict, actor_persona_id: UUID
) -> models.ProjectLifecycle:
    row = get_lifecycle(db, project_id)
    if row.closure_status == "closed":
        raise HTTPException(status_code=409, detail="El proyecto ya está cerrado")
    if not data.get("deliverables_accepted_verified"):
        raise HTTPException(status_code=422, detail="Debe confirmar la aceptación y verificación de entregables")
    if not data.get("financial_reconciliation_completed"):
        raise HTTPException(status_code=422, detail="Debe completar la conciliación financiera")
    lessons = data.pop("lessons_learned", [])
    for field, value in data.items():
        setattr(row, field, value)
    row.lessons_learned = [lesson.model_dump() if hasattr(lesson, "model_dump") else lesson for lesson in lessons]
    row.final_variance = (
        round(float(row.final_bac) - float(row.final_ac), 2)
        if row.final_bac is not None and row.final_ac is not None
        else None
    )
    row.closure_status = "closed"
    row.closed_by = actor_persona_id
    row.closed_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

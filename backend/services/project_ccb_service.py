"""Servicio de Control Integrado de Cambios (CCB) — PMI Vol. 6 §5 —
y Criterios de Aceptación (DoD / Validate Scope) — PMI Vol. 6 §4.

Reglas doctrinales implementadas:
1. Trazabilidad inmutable: cada CR registra autor, fecha, impacto ($ y días) y
   justificación; los campos de impacto no se mutan tras la creación.
2. Dictamen del Comité (CCB): 'approved' o 'rejected' con acta (review_notes).
3. Re-baseline automático: al aprobarse, el cambio se aplica al BAC
   (budget_allocated) y al cronograma (target_date), y se congela un nuevo
   snapshot de ProjectBaseline vinculado en resulting_baseline_id.
4. Aislamiento multi-sede (Axioma 3): toda operación exige sede del actor y la
   pertenencia del proyecto a esa sede.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import timedelta, timezone
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas


def _utcnow():
    from datetime import datetime

    return datetime.now(timezone.utc)


def list_change_requests(
    db: Session, project: models.Project
) -> schemas.ProjectChangeRequestListResponse:
    """Lista las CRs del proyecto con el resumen de impacto acumulado."""
    rows = (
        db.query(models.ProjectChangeRequest)
        .filter(
            models.ProjectChangeRequest.project_id == project.id,
            models.ProjectChangeRequest.sede_id == project.sede_id,
        )
        .order_by(models.ProjectChangeRequest.created_at.desc())
        .all()
    )

    summary = schemas.ProjectChangeRequestSummary()
    for row in rows:
        if row.status == "pending_ccb":
            summary.pending_ccb += 1
            summary.pending_cost_impact_total = round(summary.pending_cost_impact_total + float(row.cost_impact_delta or 0.0), 2)
            summary.pending_schedule_impact_days_total += int(row.schedule_impact_days or 0)
        elif row.status == "approved":
            summary.approved += 1
            summary.approved_cost_impact_total = round(summary.approved_cost_impact_total + float(row.cost_impact_delta or 0.0), 2)
            summary.approved_schedule_impact_days_total += int(row.schedule_impact_days or 0)
        elif row.status == "rejected":
            summary.rejected += 1

    return schemas.ProjectChangeRequestListResponse(
        project_id=project.id,
        items=row_list_adapter(db, rows),
        summary=summary,
    )


def row_list_adapter(db: Session, rows) -> list[schemas.ProjectChangeRequest]:
    return [schemas.ProjectChangeRequest.model_validate(r) for r in rows]


def create_change_request(
    db: Session,
    project: models.Project,
    cr_in: schemas.ProjectChangeRequestCreate,
    actor_persona_id: UUID,
) -> models.ProjectChangeRequest:
    """Registra una Solicitud de Cambio Formal en estado 'pending_ccb' (trazabilidad inmutable)."""
    cr = models.ProjectChangeRequest(
        project_id=project.id,
        title=cr_in.title,
        justification=cr_in.justification,
        change_type=cr_in.change_type,
        cost_impact_delta=float(cr_in.cost_impact_delta or 0.0),
        schedule_impact_days=int(cr_in.schedule_impact_days or 0),
        scope_impact_summary=cr_in.scope_impact_summary,
        status="pending_ccb",
        requested_by=actor_persona_id,
        sede_id=project.sede_id,
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)
    return cr


def decide_change_request(
    db: Session,
    project: models.Project,
    cr: models.ProjectChangeRequest,
    decision_in: schemas.ProjectChangeRequestDecide,
    actor_persona_id: UUID,
) -> models.ProjectChangeRequest:
    """Emite el dictamen del Comité de Control de Cambios.

    - 'approved': aplica cost_impact_delta al budget_allocated del proyecto,
      ajusta target_date si schedule_impact_days != 0 y congela un ProjectBaseline
      de Re-baseline vinculado en resulting_baseline_id (actualización sincronizada).
    - 'rejected': no altera la línea base; queda el acta con la justificación.
    """
    if cr.status != "pending_ccb":
        raise ValueError("La solicitud de cambio ya fue dictaminada por el Comité (trazabilidad inmutable)")

    cr.status = decision_in.decision
    cr.reviewed_by = actor_persona_id
    cr.review_notes = decision_in.review_notes
    cr.reviewed_at = _utcnow()

    if decision_in.decision == "approved":
        project.budget_allocated = round(
            float(project.budget_allocated or 0.0) + float(cr.cost_impact_delta or 0.0), 2
        )
        if cr.schedule_impact_days:
            if project.target_date:
                base_target = project.target_date
            else:
                base_target = _utcnow()
            project.target_date = base_target + timedelta(days=int(cr.schedule_impact_days))

        # Re-baseline automático (actualización sincronizada de la línea base)
        baseline_in = schemas.ProjectBaselineCreate(
            name=f"Re-baseline: {cr.title}"[:100],
            description=(
                f"Re-baseline automático tras aprobar CR '{cr.title}' "
                f"(Δ$={cr.cost_impact_delta}, Δdías={cr.schedule_impact_days}). Acta: {cr.id}"
            ),
        )
        from backend.crud.projects import create_project_baseline

        baseline = create_project_baseline(db, project.id, baseline_in, user_id=actor_persona_id)
        cr.resulting_baseline_id = baseline.id

    db.commit()
    db.refresh(cr)
    db.refresh(project)
    return cr


def get_dod_acceptance(
    db: Session, project: models.Project, task_id: UUID
) -> Optional[models.ProjectDodAcceptance]:
    """Retorna el estado de aceptación DoD de un paquete de trabajo (o None)."""
    return (
        db.query(models.ProjectDodAcceptance)
        .filter(
            models.ProjectDodAcceptance.task_id == task_id,
            models.ProjectDodAcceptance.project_id == project.id,
        )
        .first()
    )


def upsert_dod_acceptance(
    db: Session,
    project: models.Project,
    task: models.ProjectTask,
    payload: schemas.ProjectDodAcceptanceUpdate,
    actor_persona_id: UUID,
) -> models.ProjectDodAcceptance:
    """Registra/actualiza la verificación DoD de una tarea (Validate Scope).

    Si los 4 criterios canónicos del Vol. 6 §4 se cumplen, el entregable queda
    'accepted' con firma del supervisor (accepted_by UUID + accepted_at UTC).
    """
    dod = get_dod_acceptance(db, project, task.id)
    if dod is None:
        dod = models.ProjectDodAcceptance(
            project_id=project.id,
            task_id=task.id,
            sede_id=project.sede_id,
        )
        db.add(dod)

    dod.specification_met = bool(payload.specification_met)
    dod.tests_no_critical_failures = bool(payload.tests_no_critical_failures)
    dod.evidence_archived = bool(payload.evidence_archived)
    dod.supervisor_sign_off = bool(payload.supervisor_sign_off)
    dod.coq_classification = payload.coq_classification
    dod.coq_amount = float(payload.coq_amount) if payload.coq_amount is not None else None

    if (
        dod.specification_met
        and dod.tests_no_critical_failures
        and dod.evidence_archived
        and dod.supervisor_sign_off
    ):
        dod.status = "accepted"
        dod.accepted_by = actor_persona_id
        dod.accepted_at = _utcnow()
    else:
        dod.status = "pending"

    db.commit()
    db.refresh(dod)
    return dod


def get_project_ccb_and_quality_summary(db: Session, project_id: UUID) -> dict:
    """Resumen ejecutivo del Control de Cambios (CCB, Vol. 6 §5) y de la
    calidad de entregables (DoD / Costo de Calidad CoQ, Vol. 6 §4).

    Claves de retorno (todas calculadas con agregación en SQL):
    - total_change_requests, pending_ccb_count, approved_count, rejected_count
    - net_approved_cost_delta (Δ$ BAC neto de CRs aprobadas)
    - net_approved_schedule_days (Δdías neto de CRs aprobadas)
    - tasks_dod_accepted_count (entregables DoD aceptados)
    - total_coq_cost ($ CoQ acumulado) y coq_by_category por clasificación
    """
    coq_by_category = {
        "prevention": 0.0,
        "appraisal": 0.0,
        "internal_failure": 0.0,
        "external_failure": 0.0,
    }

    cr_counts = (
        db.query(
            models.ProjectChangeRequest.status,
            func.count().label("cnt"),
        )
        .filter(models.ProjectChangeRequest.project_id == project_id)
        .group_by(models.ProjectChangeRequest.status)
        .all()
    )
    status_counts = {status: int(cnt or 0) for status, cnt in cr_counts}

    approved_totals = (
        db.query(
            func.coalesce(func.sum(models.ProjectChangeRequest.cost_impact_delta), 0.0),
            func.coalesce(func.sum(models.ProjectChangeRequest.schedule_impact_days), 0),
        )
        .filter(
            models.ProjectChangeRequest.project_id == project_id,
            models.ProjectChangeRequest.status == "approved",
        )
        .first()
    )

    tasks_dod_accepted_count = int(
        db.query(func.count())
        .filter(
            models.ProjectDodAcceptance.project_id == project_id,
            models.ProjectDodAcceptance.status == "accepted",
        )
        .scalar() or 0
    )

    total_coq_cost = 0.0
    coq_rows = (
        db.query(
            models.ProjectDodAcceptance.coq_classification,
            func.coalesce(func.sum(models.ProjectDodAcceptance.coq_amount), 0.0),
        )
        .filter(
            models.ProjectDodAcceptance.project_id == project_id,
            models.ProjectDodAcceptance.coq_amount.isnot(None),
        )
        .group_by(models.ProjectDodAcceptance.coq_classification)
        .all()
    )
    for classification, amount in coq_rows:
        value = float(amount or 0.0)
        total_coq_cost += value
        if classification in coq_by_category:
            coq_by_category[classification] = value

    return {
        "total_change_requests": sum(status_counts.values()),
        "pending_ccb_count": status_counts.get("pending_ccb", 0),
        "approved_count": status_counts.get("approved", 0),
        "rejected_count": status_counts.get("rejected", 0),
        "net_approved_cost_delta": float(approved_totals[0] or 0.0),
        "net_approved_schedule_days": int(approved_totals[1] or 0),
        "tasks_dod_accepted_count": tasks_dod_accepted_count,
        "total_coq_cost": total_coq_cost,
        "coq_by_category": coq_by_category,
    }

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
from collections.abc import Mapping, Sequence
from datetime import timedelta, timezone
from typing import Any, Optional, Union
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

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

    # ── Auditoría de Calidad: paquetes de trabajo (tareas hoja) y DoD ──
    # Tarea hoja = paquete de trabajo activo (sin subtareas hijas no eliminadas).
    task_child = aliased(models.ProjectTask)
    child_count_subquery = (
        db.query(func.count(task_child.id))
        .filter(
            task_child.parent_id == models.ProjectTask.id,
            task_child.deleted_at.is_(None),
        )
        .correlate(models.ProjectTask)
        .scalar_subquery()
    )
    total_leaf_tasks = int(
        db.query(func.count())
        .filter(
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.deleted_at.is_(None),
            child_count_subquery == 0,
        )
        .scalar() or 0
    )

    dod_rows = (
        db.query(
            func.count().filter(models.ProjectDodAcceptance.supervisor_sign_off.is_(True)),
            func.count().filter(
                models.ProjectDodAcceptance.specification_met.is_(True),
                models.ProjectDodAcceptance.tests_no_critical_failures.is_(True),
                models.ProjectDodAcceptance.evidence_archived.is_(True),
                models.ProjectDodAcceptance.supervisor_sign_off.is_(True),
            ),
        )
        .filter(models.ProjectDodAcceptance.project_id == project_id)
        .first()
    )
    dod_signed_off_count = int(dod_rows[0] or 0)
    dod_all_four_met_count = int(dod_rows[1] or 0)
    dod_completion_rate_pct = (
        round((dod_signed_off_count / total_leaf_tasks * 100), 1) if total_leaf_tasks > 0 else 0.0
    )

    # ── Conformidad (Prevención + Evaluación) vs No Conformidad (Fallas) ──
    total_cost_of_conformance = (
        float(coq_by_category["prevention"]) + float(coq_by_category["appraisal"])
    )
    total_cost_of_non_conformance = (
        float(coq_by_category["internal_failure"]) + float(coq_by_category["external_failure"])
    )
    coq_conformance_ratio_pct = (
        round((total_cost_of_conformance / total_coq_cost * 100), 1) if total_coq_cost > 0 else 0.0
    )

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
        "total_leaf_tasks": total_leaf_tasks,
        "dod_signed_off_count": dod_signed_off_count,
        "dod_all_four_met_count": dod_all_four_met_count,
        "dod_completion_rate_pct": dod_completion_rate_pct,
        "total_cost_of_conformance": total_cost_of_conformance,
        "coq_conformance_ratio_pct": coq_conformance_ratio_pct,
        "total_cost_of_non_conformance": total_cost_of_non_conformance,
    }


def compute_ccb_approval_rate_pct(approved_count: int, rejected_count: int) -> float:
    """Tasa de aprobación del Comité de Control de Cambios (Vol. 6 §5).

    Devuelve el porcentaje (1 decimal) de CRs aprobadas sobre el total
    dictaminado (aprobadas + rechazadas); 0.0 si no hay dictámenes.
    Entradas negativas se clampan a 0.
    """
    approved = max(int(approved_count or 0), 0)
    rejected = max(int(rejected_count or 0), 0)
    decided = approved + rejected
    if decided <= 0:
        return 0.0
    return round((approved / decided * 100.0), 1)


def evaluate_coq_balance_status(
    coq_conformance_ratio_pct: float, total_coq_cost: float
) -> str:
    """Clasifica el balance del Costo de la Calidad (CoQ, regla Juran/Crosby).

    - 'unmeasured': sin CoQ registrado (total_coq_cost <= 0).
    - 'optimal_prevention': conformidad ≥ 70% del CoQ total.
    - 'balanced': conformidad ≥ 50% del CoQ total.
    - 'high_failure_risk': conformidad < 50% (riesgo alto de fallas).
    """
    if float(total_coq_cost or 0.0) <= 0.0:
        return "unmeasured"
    ratio = float(coq_conformance_ratio_pct or 0.0)
    if ratio >= 70.0:
        return "optimal_prevention"
    if ratio >= 50.0:
        return "balanced"
    return "high_failure_risk"


def build_ccb_coq_diagnostic(summary: dict) -> dict:
    """Diagnóstico ejecutivo CCB + CoQ a partir de un resumen (Vol. 6 §4/§5).

    Acepta un dict（p. ej. el retorno de get_project_ccb_and_quality_summary) y
    devuelve la tasa de aprobación del Comité, el estado de balance CoQ y si el
    proyecto exige intervención de calidad (riesgo alto de fallas o ≥3 CRs
    pendientes de dictamen).
    """
    approved_count = int(summary.get("approved_count", 0) or 0)
    rejected_count = int(summary.get("rejected_count", 0) or 0)
    coq_ratio = float(summary.get("coq_conformance_ratio_pct", 0.0) or 0.0)
    total_coq = float(summary.get("total_coq_cost", 0.0) or 0.0)
    coq_status = evaluate_coq_balance_status(coq_ratio, total_coq)
    return {
        "ccb_approval_rate_pct": compute_ccb_approval_rate_pct(approved_count, rejected_count),
        "coq_balance_status": coq_status,
        "requires_quality_intervention": bool(
            coq_status == "high_failure_risk"
            or int(summary.get("pending_ccb_count", 0) or 0) >= 3
        ),
    }


def evaluate_dod_gate_compliance(summary: dict) -> dict:
    """Audita la disciplina de Control de Calidad y Validación del Alcance (PMI Vol. 6 §4.2 Definition of Done)."""
    data = summary if isinstance(summary, dict) else {}
    total_leaf_tasks = max(0, int(data.get("total_leaf_tasks") or 0))
    dod_signed_off_count = max(0, int(data.get("dod_signed_off_count") or 0))
    dod_all_four_met_count = max(0, int(data.get("dod_all_four_met_count") or 0))

    unsigned_leaf_tasks = max(0, total_leaf_tasks - dod_signed_off_count)
    premature_sign_off_count = max(0, dod_signed_off_count - dod_all_four_met_count)
    strict_dod_compliance_pct = (
        round((dod_all_four_met_count / total_leaf_tasks) * 100.0, 1)
        if total_leaf_tasks > 0
        else 0.0
    )
    sign_off_integrity_pct = (
        round((dod_all_four_met_count / dod_signed_off_count) * 100.0, 1)
        if dod_signed_off_count > 0
        else 100.0
    )

    if total_leaf_tasks == 0:
        dod_gate_status = "no_leaf_tasks"
    elif premature_sign_off_count > 0:
        dod_gate_status = "integrity_breach"
    elif strict_dod_compliance_pct >= 80.0:
        dod_gate_status = "certified"
    elif strict_dod_compliance_pct >= 40.0:
        dod_gate_status = "in_progress"
    else:
        dod_gate_status = "at_risk"

    return {
        "total_leaf_tasks": total_leaf_tasks,
        "dod_signed_off_count": dod_signed_off_count,
        "dod_all_four_met_count": dod_all_four_met_count,
        "unsigned_leaf_tasks": unsigned_leaf_tasks,
        "premature_sign_off_count": premature_sign_off_count,
        "strict_dod_compliance_pct": strict_dod_compliance_pct,
        "sign_off_integrity_pct": sign_off_integrity_pct,
        "dod_gate_status": dod_gate_status,
    }


def evaluate_project_communications_complexity(
    participant_count: int, message_count: int = 0
) -> dict:
    """Calcula la complejidad de canales de comunicación N(N-1)/2 (PMBOK §10.1.2.2) y participación en sala de proyecto."""
    n = max(0, int(participant_count or 0))
    msgs = max(0, int(message_count or 0))

    communication_channels = (n * (n - 1)) // 2 if n >= 2 else 0
    avg_messages_per_participant = round(msgs / n, 2) if n > 0 else 0.0

    if n < 2:
        network_topology_tier = "solo_or_empty"
    elif n <= 5:
        network_topology_tier = "small_team"
    elif n <= 12:
        network_topology_tier = "medium_project"
    else:
        network_topology_tier = "high_complexity_network"

    requires_formal_comms_plan = bool(communication_channels > 45)

    return {
        "participant_count": n,
        "communication_channels": communication_channels,
        "message_count": msgs,
        "avg_messages_per_participant": avg_messages_per_participant,
        "network_topology_tier": network_topology_tier,
        "requires_formal_comms_plan": requires_formal_comms_plan,
    }


def evaluate_ccb_baseline_creep_impact(
    net_approved_cost_delta: float,
    bac: float,
    net_approved_schedule_days: int,
    planned_duration_days: int = 0,
) -> dict:
    """Evalúa la expansión acumulada de líneas base por CRs aprobadas (PMBOK §4.6).

    Compara el Δ$ neto y Δdías netos de las CRs aprobadas contra el BAC
    vigente y la duración planificada, y determina si exigió re-basado:
    - `cost_creep_pct` = Δ$ / BAC (2 decimales; 0.0 si BAC <= 0).
    - `schedule_creep_pct` = Δdías / duración planificada (2 decimales;
      0.0 si duración <= 0).
    - `requires_rebaselining`: True si |creep%| >= 15 en costo o cronograma.
    - `baseline_stability_status`: 'rebaseline_required' si requiere,
      'stable' si ambos |creep%| < 5.0, o 'moderate_expansion'.
    """
    cost_delta = round(float(net_approved_cost_delta or 0.0), 2)
    bac_val = max(0.0, float(bac or 0.0))
    schedule_delta = int(net_approved_schedule_days or 0)
    pd_val = max(0, int(planned_duration_days or 0))

    cost_creep_pct = round((cost_delta / bac_val) * 100.0, 2) if bac_val > 0 else 0.0
    schedule_creep_pct = (
        round((schedule_delta / pd_val) * 100.0, 2) if pd_val > 0 else 0.0
    )

    requires_rebaselining = bool(
        abs(cost_creep_pct) >= 15.0 or abs(schedule_creep_pct) >= 15.0
    )

    if requires_rebaselining:
        baseline_stability_status = "rebaseline_required"
    elif abs(cost_creep_pct) < 5.0 and abs(schedule_creep_pct) < 5.0:
        baseline_stability_status = "stable"
    else:
        baseline_stability_status = "moderate_expansion"

    return {
        "net_approved_cost_delta": cost_delta,
        "cost_creep_pct": cost_creep_pct,
        "net_approved_schedule_days": schedule_delta,
        "schedule_creep_pct": schedule_creep_pct,
        "requires_rebaselining": requires_rebaselining,
        "baseline_stability_status": baseline_stability_status,
    }


def evaluate_cost_of_quality_balance(
    prevention_cost: float = 0.0,
    appraisal_cost: float = 0.0,
    internal_failure_cost: float = 0.0,
    external_failure_cost: float = 0.0,
) -> dict:
    """Evalúa el equilibrio de Costo de la Calidad (CoQ: Conformidad vs No Conformidad) según PMI PMBOK §8.1.2.3."""
    prevention = round(max(0.0, float(prevention_cost or 0.0)), 2)
    appraisal = round(max(0.0, float(appraisal_cost or 0.0)), 2)
    internal_failure = round(max(0.0, float(internal_failure_cost or 0.0)), 2)
    external_failure = round(max(0.0, float(external_failure_cost or 0.0)), 2)

    cost_of_conformance = round(prevention + appraisal, 2)
    cost_of_nonconformance = round(internal_failure + external_failure, 2)
    total_coq = round(cost_of_conformance + cost_of_nonconformance, 2)

    conformance_ratio_pct = (
        round((cost_of_conformance / total_coq) * 100.0, 2) if total_coq > 0 else 0.0
    )
    nonconformance_ratio_pct = (
        round((cost_of_nonconformance / total_coq) * 100.0, 2)
        if total_coq > 0
        else 0.0
    )

    if total_coq == 0.0:
        coq_maturity_status = "untracked"
    elif external_failure > 0.0 and (external_failure / total_coq) >= 0.25:
        coq_maturity_status = "external_failure_critical"
    elif cost_of_nonconformance > cost_of_conformance:
        coq_maturity_status = "reactive_rework_heavy"
    elif prevention >= appraisal:
        coq_maturity_status = "proactive_conformance"
    else:
        coq_maturity_status = "inspection_dependent"

    return {
        "prevention_cost": prevention,
        "appraisal_cost": appraisal,
        "internal_failure_cost": internal_failure,
        "external_failure_cost": external_failure,
        "cost_of_conformance": cost_of_conformance,
        "cost_of_nonconformance": cost_of_nonconformance,
        "total_coq": total_coq,
        "conformance_ratio_pct": conformance_ratio_pct,
        "nonconformance_ratio_pct": nonconformance_ratio_pct,
        "coq_maturity_status": coq_maturity_status,
    }


def evaluate_ccb_backlog_velocity(
    change_requests: list[dict[str, Any]] | None,
    sla_days: float = 7.0,
) -> dict[str, Any]:
    """Audita la velocidad de decisión del Comité de Control de Cambios (CCB) y el envejecimiento del backlog de CRs (PMI PMBOK §4.6)."""
    valid_crs = [cr for cr in (change_requests or []) if isinstance(cr, dict)]
    sla_threshold = max(1.0, float(sla_days or 7.0))

    decided_count = 0
    pending_count = 0
    overdue_pending_count = 0
    sum_decided_days = 0.0
    max_pending_age_days = 0.0

    decided_statuses = {
        "approved",
        "rejected",
        "aprobado",
        "rechazado",
        "closed",
        "decided",
    }

    for cr in valid_crs:
        status_norm = (
            str(cr.get("status") or cr.get("estado") or "pending").strip().lower()
        )
        age_days = max(
            0.0, float(cr.get("age_days") or cr.get("resolution_days") or 0.0)
        )
        if status_norm in decided_statuses:
            decided_count += 1
            sum_decided_days += age_days
        else:
            pending_count += 1
            max_pending_age_days = max(max_pending_age_days, age_days)
            if age_days > sla_threshold:
                overdue_pending_count += 1

    total_requests = decided_count + pending_count
    avg_resolution_days = (
        round(sum_decided_days / decided_count, 2) if decided_count > 0 else 0.0
    )
    max_pending_age_days = round(max_pending_age_days, 2)
    backlog_pressure_pct = (
        round((pending_count / total_requests) * 100.0, 2)
        if total_requests > 0
        else 0.0
    )

    if total_requests == 0:
        ccb_velocity_status = "no_requests"
    elif overdue_pending_count >= 1:
        ccb_velocity_status = "sla_breach_bottleneck"
    elif pending_count > decided_count:
        ccb_velocity_status = "backlog_accumulating"
    else:
        ccb_velocity_status = "responsive_governance"

    return {
        "total_requests": total_requests,
        "decided_count": decided_count,
        "pending_count": pending_count,
        "overdue_pending_count": overdue_pending_count,
        "avg_resolution_days": avg_resolution_days,
        "max_pending_age_days": max_pending_age_days,
        "backlog_pressure_pct": backlog_pressure_pct,
        "ccb_velocity_status": ccb_velocity_status,
    }


def evaluate_defect_containment_efficiency(
    pre_delivery_defects: int,
    post_delivery_defects: int,
    reworked_verified_count: int = 0,
) -> dict[str, Any]:
    """Evalúa la Eficiencia de Contención de Defectos (DRE) y tasa de escape según PMI PMBOK §8.3."""
    pre_defects = max(0, int(pre_delivery_defects or 0))
    post_defects = max(0, int(post_delivery_defects or 0))
    total_defects = pre_defects + post_defects
    verified_rework = min(total_defects, max(0, int(reworked_verified_count or 0)))

    containment_efficiency_pct = (
        round((pre_defects / total_defects) * 100.0, 2)
        if total_defects > 0
        else 100.0
    )
    defect_escape_rate_pct = (
        round((post_defects / total_defects) * 100.0, 2)
        if total_defects > 0
        else 0.0
    )
    rework_verification_pct = (
        round((verified_rework / total_defects) * 100.0, 2)
        if total_defects > 0
        else 100.0
    )
    unverified_defects_count = total_defects - verified_rework

    if total_defects == 0:
        quality_containment_status = "zero_defects_recorded"
    elif defect_escape_rate_pct > 15.0:
        quality_containment_status = "high_escape_breach"
    elif unverified_defects_count > 0:
        quality_containment_status = "pending_defect_rework"
    elif containment_efficiency_pct >= 95.0 and unverified_defects_count == 0:
        quality_containment_status = "world_class_containment"
    else:
        quality_containment_status = "acceptable_containment"

    return {
        "pre_delivery_defects": pre_defects,
        "post_delivery_defects": post_defects,
        "total_defects": total_defects,
        "reworked_verified_count": verified_rework,
        "unverified_defects_count": unverified_defects_count,
        "containment_efficiency_pct": containment_efficiency_pct,
        "defect_escape_rate_pct": defect_escape_rate_pct,
        "rework_verification_pct": rework_verification_pct,
        "quality_containment_status": quality_containment_status,
    }


def evaluate_dod_checklist_verification_depth(
    checklist_items: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Evalúa la profundidad de verificación y evidencia de una lista de criterios DoD según PMI PMBOK §8.2 (Manage Quality)."""
    valid_items = [
        item for item in (checklist_items or []) if isinstance(item, dict)
    ]
    total_items = len(valid_items)
    completed_items = 0
    verified_with_evidence_items = 0

    for item in valid_items:
        is_completed = bool(
            item.get("completed") or item.get("checked") or item.get("done")
        )
        if is_completed:
            completed_items += 1
            evidence_val = str(
                item.get("evidence")
                or item.get("verified_by")
                or item.get("artifact_url")
                or ""
            ).strip()
            if evidence_val:
                verified_with_evidence_items += 1

    completion_pct = (
        round((completed_items / total_items) * 100.0, 2)
        if total_items > 0
        else 0.0
    )
    evidence_coverage_pct = (
        round((verified_with_evidence_items / completed_items) * 100.0, 2)
        if completed_items > 0
        else 0.0
    )

    if total_items == 0:
        posture = "NO_DOD_CHECKLIST"
    elif completion_pct == 100.0 and evidence_coverage_pct >= 80.0:
        posture = "AUDIT_READY_DOD"
    elif completion_pct == 100.0 and evidence_coverage_pct < 80.0:
        posture = "COMPLETED_WITHOUT_EVIDENCE"
    else:
        posture = "INCOMPLETE_DOD"

    return {
        "total_items": total_items,
        "completed_items": completed_items,
        "verified_with_evidence_items": verified_with_evidence_items,
        "completion_pct": completion_pct,
        "evidence_coverage_pct": evidence_coverage_pct,
        "posture": posture,
    }


def evaluate_scope_creep_baseline_drift(
    baseline_tasks_count: int | None,
    current_tasks_count: int | None,
    approved_change_requests_tasks_delta: int | None = 0,
) -> dict[str, Any]:
    """Audita la pérdida de control del alcance (scope creep / baseline drift — PMBOK §5.6, §4.6).

    - `safe_baseline`/`safe_current`: conteos clampados a >= 0; el delta de CRs
      aprobadas puede ser negativo (ej. reducción de alcance aprobado).
    - `authorized_scope_count`: baseline + CRs aprobadas (>= 0).
    - `unapproved_tasks_delta`: tareas actuales por encima del alcance autorizado.
    - `scope_creep_pct`: drift % sobre el alcance autorizado (2 decimales);
      con autorizado 0: 100.0 si hay tareas no autorizadas, 0.0 en otro caso.
    - `posture`: 'NO_BASELINE_SCOPE' sin baseline ni tareas actuales;
      'CONTROLLED_BASELINE' sin drift; 'MODERATE_SCOPE_DRIFT' con drift <= 15.0;
      'CRITICAL_SCOPE_CREEP' con drift > 15.0.
    """
    safe_baseline = max(0, int(baseline_tasks_count or 0))
    safe_current = max(0, int(current_tasks_count or 0))
    safe_approved_delta = int(approved_change_requests_tasks_delta or 0)

    authorized_scope_count = max(0, safe_baseline + safe_approved_delta)
    unapproved_tasks_delta = max(0, safe_current - authorized_scope_count)

    if authorized_scope_count > 0:
        scope_creep_pct = round(
            (unapproved_tasks_delta / authorized_scope_count) * 100.0, 2
        )
    else:
        scope_creep_pct = 100.0 if unapproved_tasks_delta > 0 else 0.0

    if safe_baseline == 0 and safe_current == 0:
        posture = "NO_BASELINE_SCOPE"
    elif unapproved_tasks_delta == 0:
        posture = "CONTROLLED_BASELINE"
    elif scope_creep_pct <= 15.0:
        posture = "MODERATE_SCOPE_DRIFT"
    else:
        posture = "CRITICAL_SCOPE_CREEP"

    return {
        "baseline_tasks_count": safe_baseline,
        "current_tasks_count": safe_current,
        "approved_change_requests_tasks_delta": safe_approved_delta,
        "authorized_scope_count": authorized_scope_count,
        "unapproved_tasks_delta": unapproved_tasks_delta,
        "scope_creep_pct": scope_creep_pct,
        "posture": posture,
    }


def evaluate_ccb_voting_consensus(
    votes: list[dict[str, Any]] | None,
    required_quorum: int | None = 3,
) -> dict[str, Any]:
    """Evalúa el quórum y consenso de votación del Comité de Control de Cambios (CCB) según PMI PMBOK §4.6."""
    valid_votes = [item for item in (votes or []) if isinstance(item, dict)]
    safe_quorum = max(1, int(required_quorum or 3))
    total_votes = len(valid_votes)

    approve_tokens = ("approve", "approved", "aprobar", "aprobado", "yes", "si")
    reject_tokens = ("reject", "rejected", "rechazar", "rechazado", "no", "veto")

    approve_votes = 0
    reject_votes = 0
    veto_cast = False

    for item in valid_votes:
        val = str(item.get("vote") or item.get("decision") or "").strip().lower()
        if val in approve_tokens:
            approve_votes += 1
        elif val in reject_tokens:
            reject_votes += 1

        if bool(item.get("is_veto")) or val == "veto":
            veto_cast = True

    quorum_met = bool(total_votes >= safe_quorum)
    approval_ratio = (
        round((approve_votes / total_votes) * 100.0, 2)
        if total_votes > 0
        else 0.0
    )

    if veto_cast:
        posture = "VETOED_BY_AUTHORITY"
    elif not quorum_met:
        posture = "INSUFFICIENT_QUORUM"
    elif approve_votes == total_votes:
        posture = "UNANIMOUS_CCB_APPROVAL"
    elif (
        approve_votes < total_votes
        and approve_votes > reject_votes
        and approval_ratio >= 60.0
    ):
        posture = "MAJORITY_CCB_APPROVAL"
    else:
        posture = "CCB_REJECTED_OR_DEADLOCKED"

    return {
        "safe_quorum": safe_quorum,
        "total_votes": total_votes,
        "approve_votes": approve_votes,
        "reject_votes": reject_votes,
        "veto_cast": veto_cast,
        "quorum_met": quorum_met,
        "approval_ratio": approval_ratio,
        "posture": posture,
    }


def audit_ccb_decision_sla_breaches(
    requests: list[dict[str, Any]] | None,
    sla_hours: float | int | None = 72.0,
) -> dict[str, Any]:
    """Audita incumplimientos de SLA en resoluciones CCB (PMBOK §4.6 Control Changes).

    Ignora entradas que no sean dict. El SLA mínimo es 1.0h. Para cada
    solicitud, horas transcurridas = `elapsed_hours` o `age_hours` (0.0 por
    defecto): incumple si supera el SLA, no si es exactamente el límite.
    - `total_requests`: solicitudes válidas evaluadas.
    - `breached_count` / `within_sla_count`: resolución fuera/dentro del SLA.
    - `sla_compliance_rate`: % dentro del SLA (2 decimales; 100.0 sin solicitudes).
    - `posture`: 'NO_CCB_REQUESTS' sin solicitudes;
      'SLA_GOVERNANCE_COMPLIANT' sin incumplimientos;
      'MODERATE_SLA_DELAY' con compliance >= 70.0; y
      'CRITICAL_SLA_BOTTLENECK' en otro caso.
    """
    items = [item for item in (requests or []) if isinstance(item, dict)]
    safe_sla = max(1.0, round(float(sla_hours or 72.0), 2))
    total_requests = len(items)

    breached_count = 0
    for item in items:
        elapsed_hours = float(item.get("elapsed_hours") or item.get("age_hours") or 0.0)
        if elapsed_hours > safe_sla:
            breached_count += 1

    within_sla_count = total_requests - breached_count
    sla_compliance_rate = (
        round((within_sla_count / total_requests) * 100.0, 2)
        if total_requests > 0
        else 100.0
    )

    if total_requests == 0:
        posture = "NO_CCB_REQUESTS"
    elif breached_count == 0:
        posture = "SLA_GOVERNANCE_COMPLIANT"
    elif sla_compliance_rate >= 70.0:
        posture = "MODERATE_SLA_DELAY"
    else:
        posture = "CRITICAL_SLA_BOTTLENECK"

    return {
        "sla_hours": safe_sla,
        "total_requests": total_requests,
        "breached_count": breached_count,
        "within_sla_count": within_sla_count,
        "sla_compliance_rate": sla_compliance_rate,
        "posture": posture,
    }


def evaluate_deliverable_first_time_right_yield(
    deliverables: Optional[list[dict[str, Any]]],
    target_ftr_pct: float = 85.0,
) -> dict[str, Any]:
    """Evalúa el rendimiento First-Time-Right (FTR Yield) y retrabajo de entregables (PMBOK §8.3 / §5.5).

    Analiza entregables sometidos a Control de Calidad (§8.3) y Validación del
    Alcance (§5.5):
    - `total_inspected`: entregables válidos analizados.
    - `first_time_right_count`: entregables con `accepted is True` y `rejection_cycles == 0`.
    - `reworked_deliverable_ids`: IDs de entregables con `rejection_cycles > 0`.
    - `chronic_rework_ids`: IDs de entregables con `rejection_cycles >= 2`.
    - `total_rework_hours`: suma de horas de retrabajo redondeada a 2 decimales.
    - `ftr_yield_pct`: porcentaje FTR (`0.0` a `100.0`, o `0.0` si `total_inspected == 0`).
    - `quality_yield_posture`:
      - `'NO_DELIVERABLES_INSPECTED'` si `total_inspected == 0`
      - `'CHRONIC_REWORK_BOTTLENECK'` si `len(chronic_rework_ids) > 0`
      - `'HIGH_FIRST_TIME_RIGHT_YIELD'` si `ftr_yield_pct >= target_ftr_pct` y `len(chronic_rework_ids) == 0`
      - `'BELOW_TARGET_FTR_YIELD'` en cualquier otro caso (`ftr_yield_pct < target_ftr_pct`)
    - `recommendations`: recomendaciones accionables PMI PMBOK §8.3 / §5.5.
    """
    items = [item for item in (deliverables or []) if isinstance(item, dict)]
    try:
        raw_target = float(85.0 if target_ftr_pct is None else target_ftr_pct)
    except (TypeError, ValueError):
        raw_target = 85.0
    safe_target_ftr_pct = max(0.0, min(100.0, round(raw_target, 2)))

    total_inspected = len(items)
    first_time_right_count = 0
    reworked_deliverable_ids: list[str] = []
    chronic_rework_ids: list[str] = []
    total_rework_hours = 0.0

    for idx, item in enumerate(items, start=1):
        raw_id = item.get("id") if item.get("id") is not None else item.get("task_id")
        deliverable_id = str(raw_id).strip() if raw_id is not None and str(raw_id).strip() else f"DELIV-{idx}"

        accepted = bool(item.get("accepted", False))

        raw_cycles = (
            item.get("rejection_cycles")
            if item.get("rejection_cycles") is not None
            else item.get("rework_count", 0)
        )
        try:
            rejection_cycles = max(0, int(raw_cycles or 0))
        except (TypeError, ValueError):
            rejection_cycles = 0

        raw_hours = item.get("rework_hours", 0.0)
        try:
            rework_hours = max(0.0, float(raw_hours or 0.0))
        except (TypeError, ValueError):
            rework_hours = 0.0

        total_rework_hours += rework_hours

        if accepted and rejection_cycles == 0:
            first_time_right_count += 1

        if rejection_cycles > 0:
            reworked_deliverable_ids.append(deliverable_id)

        if rejection_cycles >= 2:
            chronic_rework_ids.append(deliverable_id)

    rounded_rework_hours = round(total_rework_hours, 2)
    ftr_yield_pct = (
        round((first_time_right_count / total_inspected) * 100.0, 2)
        if total_inspected > 0
        else 0.0
    )

    recommendations: list[str] = []
    if total_inspected == 0:
        quality_yield_posture = "NO_DELIVERABLES_INSPECTED"
        recommendations.append(
            "Registrar inspecciones de Control de Calidad (PMBOK §8.3) y actas DoD antes de ejecutar la Validación del Alcance (§5.5)."
        )
    elif len(chronic_rework_ids) > 0:
        quality_yield_posture = "CHRONIC_REWORK_BOTTLENECK"
        recommendations.append(
            f"Ejecutar análisis de causa raíz (Ishikawa/5-Porqués) sobre entregables con retrabajo crónico ({', '.join(chronic_rework_ids)}) que acumulan {rounded_rework_hours}h de retrabajo (PMBOK §8.3)."
        )
        recommendations.append(
            "Reforzar listas de verificación DoD previas a la inspección para eliminar ciclos repetitivos de rechazo en Validación del Alcance (§5.5)."
        )
    elif ftr_yield_pct >= safe_target_ftr_pct:
        quality_yield_posture = "HIGH_FIRST_TIME_RIGHT_YIELD"
        recommendations.append(
            f"Rendimiento First-Time-Right ({ftr_yield_pct}%) cumple la meta de calidad ({safe_target_ftr_pct}%). Mantener prevención e inspección temprana PMBOK §8.3."
        )
    else:
        quality_yield_posture = "BELOW_TARGET_FTR_YIELD"
        recommendations.append(
            f"Rendimiento First-Time-Right ({ftr_yield_pct}%) inferior al umbral objetivo ({safe_target_ftr_pct}%). Fortalecer revisiones de pares y criterios de aceptación DoD antes de entregar a validación (§5.5)."
        )
        if reworked_deliverable_ids:
            recommendations.append(
                f"Revisar defectos detectados en {', '.join(reworked_deliverable_ids)} ({rounded_rework_hours}h de retrabajo) para contener costos de falla interna (PMBOK §8.3)."
            )

    return {
        "total_inspected": total_inspected,
        "first_time_right_count": first_time_right_count,
        "reworked_deliverable_ids": reworked_deliverable_ids,
        "chronic_rework_ids": chronic_rework_ids,
        "total_rework_hours": rounded_rework_hours,
        "ftr_yield_pct": ftr_yield_pct,
        "quality_yield_posture": quality_yield_posture,
        "recommendations": recommendations,
    }


def audit_emergency_change_retroactive_ratification(
    change_requests: Optional[list[dict]],
    total_requests_window: Optional[int] = None,
    max_emergency_share_pct: float = 20.0,
) -> dict:
    """Audita la ratificación retroactiva de cambios de emergencia (PMBOK §4.6).

    Los cambios fast-track de emergencia deben ratificarse luego ante el CCB
    y completar una revisión post-implementación (PIR):
    - `total_evaluated`: máximo entre los dicts válidos y la ventana declarada.
    - `emergency_count`: cambios con `is_emergency`/`fast_track` verdadero.
    - `unratified_emergency_ids`: ids/code de emergencias sin ratificación CCB
      (`retroactively_ratified`/`ccb_ratified`).
    - `missing_pir_emergency_ids`: emergencias sin PIR (`post_implementation_review_done`/
      `pir_completed`).
    - `emergency_share_pct`: % de emergencias sobre lo evaluado (2 decimales;
      0.0 sin nada).
    - `emergency_governance_posture`: 'NO_EMERGENCY_CHANGES' sin emergencias;
      'UNRATIFIED_EMERGENCY_BYPASS' con emergencias sin ratificar;
      'EXCESSIVE_FAST_TRACK_ABUSE' con share > max_emergency_share_pct;
      'PENDING_POST_IMPLEMENTATION_REVIEW' con PIRs faltantes; y
      'GOVERNED_EMERGENCY_PROTOCOL' en el protocolo completo.
    - `recommendations`: acciones correctivas según el hallazgo.
    """
    items = [item for item in (change_requests or []) if isinstance(item, dict)]
    total_evaluated = max(len(items), int(total_requests_window or 0))

    emergency_count = 0
    unratified_emergency_ids: list[str] = []
    missing_pir_emergency_ids: list[str] = []

    for item in items:
        is_emergency = bool(item.get("is_emergency") or item.get("fast_track"))
        if not is_emergency:
            continue
        emergency_count += 1
        change_id = str(item.get("id") or item.get("code") or "").strip()
        if not bool(item.get("retroactively_ratified") or item.get("ccb_ratified")):
            unratified_emergency_ids.append(change_id)
        if not bool(
            item.get("post_implementation_review_done") or item.get("pir_completed")
        ):
            missing_pir_emergency_ids.append(change_id)

    emergency_share_pct = (
        round((emergency_count / total_evaluated) * 100.0, 2)
        if total_evaluated > 0
        else 0.0
    )

    if emergency_count == 0:
        emergency_governance_posture = "NO_EMERGENCY_CHANGES"
    elif unratified_emergency_ids:
        emergency_governance_posture = "UNRATIFIED_EMERGENCY_BYPASS"
    elif emergency_share_pct > max_emergency_share_pct:
        emergency_governance_posture = "EXCESSIVE_FAST_TRACK_ABUSE"
    elif missing_pir_emergency_ids:
        emergency_governance_posture = "PENDING_POST_IMPLEMENTATION_REVIEW"
    else:
        emergency_governance_posture = "GOVERNED_EMERGENCY_PROTOCOL"

    recommendations: list[str] = []
    if emergency_governance_posture == "UNRATIFIED_EMERGENCY_BYPASS":
        recommendations.append(
            "Ratificar retroactivamente ante el CCB los cambios de emergencia pendientes"
        )
    if emergency_governance_posture == "EXCESSIVE_FAST_TRACK_ABUSE":
        recommendations.append(
            "Revisar el umbral de uso del fast-track y reforzar el control de cambios de rutina"
        )
    if emergency_governance_posture in (
        "PENDING_POST_IMPLEMENTATION_REVIEW",
        "UNRATIFIED_EMERGENCY_BYPASS",
    ) and missing_pir_emergency_ids:
        recommendations.append(
            "Programar la revisión post-implementación (PIR) de los cambios de emergencia"
        )
    if emergency_governance_posture == "NO_EMERGENCY_CHANGES":
        recommendations.append(
            "Mantener el protocolo de emergencia documentado y el CCB en alerta"
        )
    if emergency_governance_posture == "GOVERNED_EMERGENCY_PROTOCOL":
        recommendations.append(
            "Registrar la ratificación y el PIR en el backlog de gobernanza CCB"
        )

    return {
        "total_evaluated": total_evaluated,
        "emergency_count": emergency_count,
        "unratified_emergency_ids": unratified_emergency_ids,
        "missing_pir_emergency_ids": missing_pir_emergency_ids,
        "emergency_share_pct": emergency_share_pct,
        "emergency_governance_posture": emergency_governance_posture,
        "recommendations": recommendations,
    }


def audit_configuration_baseline_integrity(
    configuration_items: Optional[list[dict]],
) -> dict[str, Any]:
    """Audita la integridad de la línea base de configuración y deriva de versiones de CIs según PMI PMBOK §4.6."""
    items = [item for item in (configuration_items or []) if isinstance(item, dict)]
    total_items = len(items)

    unauthorized_drift_ids: list[str] = []
    unverified_checksum_ids: list[str] = []
    compliant_count = 0

    for idx, item in enumerate(items, start=1):
        raw_id = (
            item.get("id")
            if item.get("id") is not None
            else item.get("ci_id")
            if item.get("ci_id") is not None
            else item.get("artifact_id")
            if item.get("artifact_id") is not None
            else item.get("code")
            if item.get("code") is not None
            else item.get("name")
        )
        ci_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"CI-{idx}"
        )

        raw_approved = (
            item.get("approved_version")
            if item.get("approved_version") is not None
            else item.get("baseline_version")
        )
        approved_ver = str(raw_approved or "").strip()
        raw_deployed = (
            item.get("deployed_version")
            if item.get("deployed_version") is not None
            else item.get("current_version")
        )
        deployed_ver = str(raw_deployed or "").strip()

        cr_ref = str(
            item.get("authorized_by_cr")
            or item.get("cr_id")
            or item.get("ccb_approved_change_id")
            or item.get("approved_cr_id")
            or ""
        ).strip()

        has_drift = (not approved_ver or not deployed_ver) or (deployed_ver != approved_ver)
        is_unauthorized_drift = (not approved_ver or not deployed_ver) or (
            has_drift and not bool(cr_ref)
        )
        if is_unauthorized_drift:
            unauthorized_drift_ids.append(ci_id)

        raw_has_checksum = (
            item.get("has_checksum")
            if item.get("has_checksum") is not None
            else item.get("checksum_verified")
            if item.get("checksum_verified") is not None
            else item.get("integrity_verified")
        )
        raw_verified_hash = (
            item.get("verified_hash")
            if item.get("verified_hash") is not None
            else item.get("hash_match")
        )
        has_valid_checksum = bool(
            (isinstance(raw_has_checksum, bool) and raw_has_checksum)
            or (
                isinstance(raw_has_checksum, str)
                and raw_has_checksum.strip().lower() not in ("", "false", "0", "none")
            )
            or (isinstance(raw_verified_hash, bool) and raw_verified_hash)
            or (
                isinstance(raw_verified_hash, str)
                and raw_verified_hash.strip().lower() not in ("", "false", "0", "none")
            )
        )
        if not has_valid_checksum:
            unverified_checksum_ids.append(ci_id)

        if not is_unauthorized_drift and has_valid_checksum:
            compliant_count += 1

    integrity_rate_pct = (
        round((compliant_count / total_items) * 100.0, 2)
        if total_items > 0
        else 0.0
    )

    recommendations: list[str] = []
    if total_items == 0:
        configuration_posture = "NO_CONFIGURATION_ITEMS"
        recommendations.append(
            "Registrar los elementos de configuración (CIs) y sus versiones de línea base aprobadas en el sistema de gestión de configuración (PMBOK §4.6)."
        )
    elif len(unauthorized_drift_ids) > 0:
        configuration_posture = "UNAUTHORIZED_VERSION_DRIFT"
        recommendations.append(
            f"Revertir o someter a ratificación del CCB los elementos con deriva de versión no autorizada ({', '.join(unauthorized_drift_ids)}) conforme a PMBOK §4.6."
        )
    elif len(unverified_checksum_ids) > 0:
        configuration_posture = "UNVERIFIED_ARTIFACT_CHECKSUMS"
        recommendations.append(
            f"Generar y verificar hashes/checksums criptográficos para los artefactos sin verificación de integridad ({', '.join(unverified_checksum_ids)}) según auditoría de configuración PMBOK §4.6."
        )
    else:
        configuration_posture = "VERIFIED_CONFIGURATION_BASELINE"
        recommendations.append(
            "Línea base de configuración íntegra y verificada con trazabilidad CCB y hashes validados (PMBOK §4.6)."
        )

    return {
        "total_items": total_items,
        "unauthorized_drift_ids": unauthorized_drift_ids,
        "unverified_checksum_ids": unverified_checksum_ids,
        "compliant_count": compliant_count,
        "integrity_rate_pct": integrity_rate_pct,
        "configuration_posture": configuration_posture,
        "recommendations": recommendations,
    }


def audit_pareto_defect_root_causes(
    defects: Optional[list[dict]],
    vital_few_threshold_pct: float = 80.0,
) -> dict:
    """Audita la concentración de causas raíz de defectos (Pareto 80-20 — PMBOK §8.3).

    Cada defecto declara `root_cause`/`category` (vacío o "UNKNOWN"/"TBD"/
    "N/A"/"SIN CATEGORIA"/"SIN CATEGORÍA" -> 'UNCATEGORIZED') y
    `count`/`occurrences` (default 1, clamp >= 1). Agrupa por causa en
    mayúsculas, ordenado de mayor a menor (desempate por acumulación):
    - `total_defect_occurrences` / `unique_causes_count` / `uncategorized_occurrences`.
    - `top_cause` (None sin defectos) y `top_cause_share_pct` (2 dec; 0.0 vacío).
    - `vital_few_causes`: primeras causas acumulando hasta >= threshold %.
    - `pareto_posture`: 'NO_DEFECTS_RECORDED' sin.defectos;
      'UNCATEGORIZED_ROOT_CAUSE_BLINDSPOT' con >= 30% de sin categorizar;
      'CONCENTRATED_PARETO_BOTTLENECK' con top >= 50% o vital few <= 2
      causas >= 3; y 'DIFFUSE_DEFECT_DISTRIBUTION' difuso.
    - `recommendations`: acciones correctivas por hallazgo.
    """
    UNKNOWN_TOKENS = {"unknown", "tbd", "n/a", "sin categoria", "sin categoría"}
    items = [item for item in (defects or []) if isinstance(item, dict)]

    grouped: dict[str, int] = {}
    uncategorized_occurrences = 0
    for item in items:
        raw_cause = str(item.get("root_cause") or item.get("category") or "").strip()
        normalized = raw_cause.lower() or "uncategorized"
        if normalized in UNKNOWN_TOKENS or not raw_cause:
            normalized = "uncategorized"
        try:
            occurrences = max(1, int(float(item.get("count") or item.get("occurrences") or 1)))
        except (TypeError, ValueError):
            occurrences = 1
        grouped[normalized.upper()] = grouped.get(normalized.upper(), 0) + occurrences
        if normalized == "uncategorized":
            uncategorized_occurrences += occurrences

    if "UNCATEGORIZED" in grouped:
        uncat_total = grouped["UNCATEGORIZED"]
        uncategorized_occurrences = uncat_total

    ordered_causes = sorted(
        grouped.items(), key=lambda pair: (-pair[1], pair[0])
    )
    total_defect_occurrences = sum(grouped.values())

    safe_threshold = float(vital_few_threshold_pct if vital_few_threshold_pct is not None else 80.0)
    vital_few_causes: list[str] = []
    cumulative = 0
    top_cause = ordered_causes[0][0] if ordered_causes else None
    top_cause_share_pct = (
        round((ordered_causes[0][1] / total_defect_occurrences) * 100.0, 2)
        if ordered_causes
        else 0.0
    )
    if ordered_causes:
        for cause, occurrences in ordered_causes:
            vital_few_causes.append(cause)
            cumulative += occurrences
            if (cumulative / total_defect_occurrences) * 100.0 >= safe_threshold:
                break

    uncategorized_pct = (
        (uncategorized_occurrences / total_defect_occurrences) * 100.0
        if total_defect_occurrences > 0
        else 0.0
    )

    if total_defect_occurrences == 0:
        pareto_posture = "NO_DEFECTS_RECORDED"
    elif uncategorized_pct >= 30.0:
        pareto_posture = "UNCATEGORIZED_ROOT_CAUSE_BLINDSPOT"
    elif (
        top_cause_share_pct >= 50.0
        or (len(grouped) >= 3 and len(vital_few_causes) <= 2)
    ):
        pareto_posture = "CONCENTRATED_PARETO_BOTTLENECK"
    else:
        pareto_posture = "DIFFUSE_DEFECT_DISTRIBUTION"

    recommendations: list[str] = []
    if pareto_posture == "NO_DEFECTS_RECORDED":
        recommendations.append(
            "Registrar los defectos con su causa raíz para habilitar el analisis Pareto (PMBOK §8.3)."
        )
    elif pareto_posture == "UNCATEGORIZED_ROOT_CAUSE_BLINDSPOT":
        recommendations.append(
            "Exigir causa raíz obligatoria en el registro de defectos: el punto ciego impide el Pareto."
        )
    elif pareto_posture == "CONCENTRATED_PARETO_BOTTLENECK":
        recommendations.append(
            "Atacar el few vital con acciones correctivas dirigidas antes de ampliar el colegio de causas."
        )
    else:
        recommendations.append(
            "Distribución difusa: aplicar la herramienta 5 Whys para consolidar causas reales dispersas."
        )

    return {
        "total_defect_occurrences": total_defect_occurrences,
        "unique_causes_count": len(grouped),
        "uncategorized_occurrences": uncategorized_occurrences,
        "top_cause": top_cause,
        "top_cause_share_pct": top_cause_share_pct,
        "vital_few_causes": vital_few_causes,
        "pareto_posture": pareto_posture,
        "recommendations": recommendations,
    }


def audit_unapproved_scope_creep_exposure(
    work_packages: Optional[List[Dict[str, Any]]] = None,
    tolerance_hours_pct: float = 10.0,
) -> Dict[str, Any]:
    """Audita trabajo fuera de line base y gold-plating sin CR (PMBOK §5.6 y §4.6).

    Cada paquete compara `actual_hours` frente a `baseline_hours` y su CR
    aprobada (`approved_cr_id`/`change_request_id` o `has_approved_cr`):
    - Trabajo con esfuerzo real sin line base y sin CR -> 'unbaselined_package_ids'
      aportando sus horas a `unapproved_effort_hours`.
    - Paquete con line base sin CR cuyo overrun_pct supera la tolerancia ->
      'scope_creep_package_ids' aportando el exceso a `unapproved_effort_hours`.
    - `scope_posture`: 'NO_WORK_PACKAGES_EVALUATED' vacío;
      'UNAUTHORIZED_UNBASELINED_WORK' con trabajo sin linea base;
      'UNAPPROVED_SCOPE_CREEP_DETECTED' con creep > tolerancia;
      'CONTROLLED_SCOPE_BASELINE' en caso contrario.
    """
    packages = [item for item in (work_packages or []) if isinstance(item, dict)]
    if not packages:
        return {
            "total_packages": 0,
            "unbaselined_package_ids": [],
            "scope_creep_package_ids": [],
            "unapproved_effort_hours": 0.0,
            "is_scope_controlled": True,
            "scope_posture": "NO_WORK_PACKAGES_EVALUATED",
        }

    unbaselined_package_ids: List[str] = []
    scope_creep_package_ids: List[str] = []
    unapproved_effort = 0.0
    for idx, item in enumerate(packages, start=1):
        pkg_id = (
            str(item.get("id") or item.get("package_id") or item.get("wbs_code") or "").strip()
            or f"WP-{idx}"
        )
        try:
            base_h = max(0.0, float(item.get("baseline_hours") if item.get("baseline_hours") is not None else (item.get("planned_hours") or 0.0)))
        except (TypeError, ValueError):
            base_h = 0.0
        try:
            act_h = max(0.0, float(item.get("actual_hours") if item.get("actual_hours") is not None else (item.get("effort_hours") or 0.0)))
        except (TypeError, ValueError):
            act_h = 0.0
        cr_ref = str(item.get("approved_cr_id") or item.get("change_request_id") or "").strip()
        has_cr = bool(cr_ref or item.get("has_approved_cr") is True)

        if base_h <= 0.0 and act_h > 0.0 and not has_cr:
            unbaselined_package_ids.append(pkg_id)
            unapproved_effort += act_h
        elif base_h > 0.0 and not has_cr:
            overrun_pct = ((act_h - base_h) / base_h) * 100.0
            if overrun_pct > float(tolerance_hours_pct) + 1e-9:
                scope_creep_package_ids.append(pkg_id)
                unapproved_effort += act_h - base_h

    total_packages = len(packages)
    is_scope_controlled = bool(len(unbaselined_package_ids) == 0 and len(scope_creep_package_ids) == 0)
    if total_packages == 0:
        scope_posture = "NO_WORK_PACKAGES_EVALUATED"
    elif unbaselined_package_ids:
        scope_posture = "UNAUTHORIZED_UNBASELINED_WORK"
    elif scope_creep_package_ids:
        scope_posture = "UNAPPROVED_SCOPE_CREEP_DETECTED"
    else:
        scope_posture = "CONTROLLED_SCOPE_BASELINE"

    return {
        "total_packages": total_packages,
        "unbaselined_package_ids": unbaselined_package_ids,
        "scope_creep_package_ids": scope_creep_package_ids,
        "unapproved_effort_hours": round(unapproved_effort, 2),
        "is_scope_controlled": is_scope_controlled,
        "scope_posture": scope_posture,
    }


def evaluate_cost_of_quality_prevention_balance(
    coq_entries: Optional[List[Dict[str, Any]]] = None,
    max_failure_cost_share_pct: float = 35.0,
) -> Dict[str, Any]:
    """Evalúa el balance CoQ entre Conformidad y No Conformidad (PMBOK §8.1.2.3).

    Cada entrada declara `id`/`entry_id` (fallback 'COQ-{idx}'), categoría
    (`category`/`coq_category`/`type`) y monto (`amount`/`cost`):
    - prevention: 'prevention', 'prevencion'. appraisal: 'appraisal',
      'evaluacion', 'inspeccion'. fallas: 'internal_failure',
      'external_failure', 'falla_interna', 'falla_externa', 'rework', 'warranty'.
    - Montos <= 0.0 o categoría fuera de los conjuntos -> 'unclassified_entry_ids'.
    - `failure_cost_share_pct` = nonconformance / total (2 decimales; 0.0 vacío).
    - `is_balanced`: total > 0, sin entradas no clasificadas, share dentro de la
      tolerancia y con inversión en prevention.
    - `coq_posture`: 'NO_COQ_ENTRIES_RECORDED' vacío;
      'INVALID_OR_UNCLASSIFIED_COQ_ENTRIES'; 'HIGH_NONCONFORMANCE_FAILURE_BURDEN';
      'MISSING_PREVENTION_INVESTMENT'; 'OPTIMAL_CONFORMANCE_COQ_BALANCE'.
    """
    entries = [e for e in (coq_entries or []) if isinstance(e, dict)]
    if not entries:
        return {
            "total_coq_amount": 0.0,
            "conformance_cost": 0.0,
            "nonconformance_cost": 0.0,
            "failure_cost_share_pct": 0.0,
            "unclassified_entry_ids": [],
            "is_balanced": False,
            "coq_posture": "NO_COQ_ENTRIES_RECORDED",
        }

    prevention_set = {"prevention", "prevencion", "prevención"}
    appraisal_set = {"appraisal", "evaluacion", "evaluación", "inspeccion", "inspección"}
    failure_set = {
        "internal_failure", "external_failure",
        "falla_interna", "falla_externa", "rework", "warranty",
    }

    unclassified_entry_ids: List[str] = []
    prevention_cost = 0.0
    conformance_cost = 0.0
    nonconformance_cost = 0.0

    for idx, item in enumerate(entries, start=1):
        entry_id = str(item.get("id") or item.get("entry_id") or "").strip() or f"COQ-{idx}"
        raw_cat = str(item.get("category") or item.get("coq_category") or item.get("type") or "").strip().lower()
        try:
            amount = float(item.get("amount") if item.get("amount") is not None else (item.get("cost") or 0.0))
        except (TypeError, ValueError):
            amount = 0.0

        if amount <= 0.0 or (
            raw_cat not in prevention_set
            and raw_cat not in appraisal_set
            and raw_cat not in failure_set
        ):
            unclassified_entry_ids.append(entry_id)
            continue

        if raw_cat in prevention_set:
            prevention_cost += amount
            conformance_cost += amount
        elif raw_cat in appraisal_set:
            conformance_cost += amount
        else:
            nonconformance_cost += amount

    conformance_cost = round(conformance_cost, 2)
    nonconformance_cost = round(nonconformance_cost, 2)
    total_coq_amount = round(conformance_cost + nonconformance_cost, 2)
    failure_cost_share_pct = (
        round((nonconformance_cost / total_coq_amount) * 100.0, 2)
        if total_coq_amount > 0.0
        else 0.0
    )
    is_balanced = bool(
        total_coq_amount > 0.0
        and len(unclassified_entry_ids) == 0
        and failure_cost_share_pct <= float(max_failure_cost_share_pct) + 1e-9
        and prevention_cost > 0.0
    )

    if len(unclassified_entry_ids) > 0:
        coq_posture = "INVALID_OR_UNCLASSIFIED_COQ_ENTRIES"
    elif failure_cost_share_pct > float(max_failure_cost_share_pct) + 1e-9:
        coq_posture = "HIGH_NONCONFORMANCE_FAILURE_BURDEN"
    elif prevention_cost <= 0.0:
        coq_posture = "MISSING_PREVENTION_INVESTMENT"
    else:
        coq_posture = "OPTIMAL_CONFORMANCE_COQ_BALANCE"

    return {
        "total_coq_amount": total_coq_amount,
        "conformance_cost": conformance_cost,
        "nonconformance_cost": nonconformance_cost,
        "failure_cost_share_pct": failure_cost_share_pct,
        "unclassified_entry_ids": unclassified_entry_ids,
        "is_balanced": is_balanced,
        "coq_posture": coq_posture,
    }


def evaluate_defect_containment_and_escape_rate(
    defects: Optional[List[Dict[str, Any]]] = None,
    min_containment_effectiveness_pct: float = 85.0,
) -> Dict[str, Any]:
    """Evalúa la contención de defectos pre-release y su escape a producción (PMBOK §8.3).

    Cada defecto declara `id`/`defect_id` (fallback 'DEF-{idx}'), etapa de
    detección (`detected_in`/`phase`/`stage`) y gravedad (`severity`/`priority`);
    se considera escapado a producción si la etapa pertenece a
    {production, prod, post_release, customer, field, produccion, cliente} o
    `escaped_to_production` es True:
    - `critical_escaped_defect_ids`: escapados con severity crítica
      ({critical, blocker, high, sev1, p0, p1, critico, alta}).
    - `containment_effectiveness_pct` / `escape_rate_pct` (2 decimales).
    - `is_contained`: sin críticos escapados y DCE >= minimo tolerado.
    - `containment_posture`: 'NO_DEFECTS_EVALUATED' vacío;
      'CRITICAL_PRODUCTION_DEFECT_ESCAPE'; 'LOW_DEFECT_CONTAINMENT_EFFECTIVENESS';
      'EFFECTIVE_QA_DEFECT_CONTAINMENT'.
    """
    records = [d for d in (defects or []) if isinstance(d, dict)]
    if not records:
        return {
            "total_defects": 0,
            "pre_release_defects_count": 0,
            "escaped_production_defects_count": 0,
            "critical_escaped_defect_ids": [],
            "containment_effectiveness_pct": 100.0,
            "escape_rate_pct": 0.0,
            "is_contained": True,
            "containment_posture": "NO_DEFECTS_EVALUATED",
        }

    ESCAPED_STAGES = {
        "production", "prod", "post_release", "customer", "field",
        "produccion", "producción", "cliente",
    }
    CRITICAL_SEVERITIES = {
        "critical", "blocker", "high", "sev1", "p0", "p1",
        "critico", "crítico", "alta",
    }

    total_defects = len(records)
    pre_release_defects_count = 0
    escaped_production_defects_count = 0
    critical_escaped_defect_ids: List[str] = []

    for idx, item in enumerate(records, start=1):
        def_id = str(item.get("id") or item.get("defect_id") or "").strip() or f"DEF-{idx}"
        stage = str(item.get("detected_in") or item.get("phase") or item.get("stage") or "").strip().lower()
        severity = str(item.get("severity") or item.get("priority") or "").strip().lower()
        is_escaped = stage in ESCAPED_STAGES or item.get("escaped_to_production") is True

        if is_escaped:
            escaped_production_defects_count += 1
            if severity in CRITICAL_SEVERITIES:
                critical_escaped_defect_ids.append(def_id)
        else:
            pre_release_defects_count += 1

    containment_effectiveness_pct = round(
        (pre_release_defects_count / total_defects) * 100.0, 2
    )
    escape_rate_pct = round(
        (escaped_production_defects_count / total_defects) * 100.0, 2
    )
    is_contained = bool(
        len(critical_escaped_defect_ids) == 0
        and containment_effectiveness_pct + 1e-9 >= float(min_containment_effectiveness_pct)
    )

    if len(critical_escaped_defect_ids) > 0:
        containment_posture = "CRITICAL_PRODUCTION_DEFECT_ESCAPE"
    elif containment_effectiveness_pct + 1e-9 < float(min_containment_effectiveness_pct):
        containment_posture = "LOW_DEFECT_CONTAINMENT_EFFECTIVENESS"
    else:
        containment_posture = "EFFECTIVE_QA_DEFECT_CONTAINMENT"

    return {
        "total_defects": total_defects,
        "pre_release_defects_count": pre_release_defects_count,
        "escaped_production_defects_count": escaped_production_defects_count,
        "critical_escaped_defect_ids": critical_escaped_defect_ids,
        "containment_effectiveness_pct": containment_effectiveness_pct,
        "escape_rate_pct": escape_rate_pct,
        "is_contained": is_contained,
        "containment_posture": containment_posture,
    }


def audit_configuration_items_baseline_integrity_v1(
    configuration_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verifica la integridad de la linea base de IC y las auditorías PCA/FCA (PMBOK §4.6).

    Contrato v1 conservado para compatibilidad; la variante canónica vigente
    es ``audit_configuration_items_baseline_integrity`` (basada en
    ``checksum_verified`` y reporte explícito de ``version_drift_ci_ids``).

    Cada IC declara `id`/`ci_id`/`code` (fallback 'CI-{idx}'), version de
    base (`baseline_version`/`approved_version`), version desplegada
    (`deployed_version`/`actual_version`/`current_version`), CR aprobado
    (`approved_cr_id`/`change_request_id`) y estado de verificacion
    (`verification_status`/`pca_fca_status`):
    - `unbaselined_ci_ids`: sin version base o sin version desplegada.
    - `unauthorized_drift_ci_ids`: despliegue distinto a la base sin CR aprobado.
    - `unverified_audit_ci_ids`: verificacion fuera del set
      {verified, verificado, passed, approved, aprobado, compliant}.
    - `integrity_rate_pct` (2 decimales; 100.0 sin IC).
    - `is_configuration_compliant`: sin hallazgos en las 3 listas.
    - `configuration_posture`: 'NO_CONFIGURATION_ITEMS' vacío;
      'UNAUTHORIZED_CONFIGURATION_DRIFT'; 'UNBASELINED_CONFIGURATION_ITEM';
      'PENDING_PCA_FCA_VERIFICATION'; 'VERIFIED_CONFIGURATION_BASELINE'.
    """
    items = [ci for ci in (configuration_items or []) if isinstance(ci, dict)]
    if not items:
        return {
            "total_items": 0,
            "verified_items_count": 0,
            "unauthorized_drift_ci_ids": [],
            "unbaselined_ci_ids": [],
            "unverified_audit_ci_ids": [],
            "integrity_rate_pct": 100.0,
            "is_configuration_compliant": True,
            "configuration_posture": "NO_CONFIGURATION_ITEMS",
        }

    VERIFIED_STATUSES = {
        "verified", "verificado", "passed", "approved", "aprobado", "compliant",
    }

    total_items = len(items)
    verified_items_count = 0
    unauthorized_drift_ci_ids: list[str] = []
    unbaselined_ci_ids: list[str] = []
    unverified_audit_ci_ids: list[str] = []

    for idx, item in enumerate(items, start=1):
        ci_id = str(
            item.get("id") or item.get("ci_id") or item.get("code") or f"CI-{idx}"
        ).strip()
        baseline_version = str(
            item.get("baseline_version") or item.get("approved_version") or ""
        ).strip()
        deployed_version = str(
            item.get("deployed_version")
            or item.get("actual_version")
            or item.get("current_version")
            or ""
        ).strip()
        approved_cr_id = str(
            item.get("approved_cr_id") or item.get("change_request_id") or ""
        ).strip()
        verification_status = str(
            item.get("verification_status") or item.get("pca_fca_status") or ""
        ).strip().lower()

        is_unbaselined = not baseline_version or not deployed_version
        is_unauthorized_drift = bool(
            baseline_version
            and deployed_version
            and baseline_version != deployed_version
            and not approved_cr_id
        )
        is_unverified_audit = verification_status not in VERIFIED_STATUSES

        if is_unbaselined:
            unbaselined_ci_ids.append(ci_id)
        if is_unauthorized_drift:
            unauthorized_drift_ci_ids.append(ci_id)
        if is_unverified_audit:
            unverified_audit_ci_ids.append(ci_id)
        if not (is_unbaselined or is_unauthorized_drift or is_unverified_audit):
            verified_items_count += 1

    integrity_rate_pct = (
        round((verified_items_count / total_items) * 100.0, 2)
        if total_items > 0
        else 100.0
    )
    is_configuration_compliant = bool(
        len(unauthorized_drift_ci_ids) == 0
        and len(unbaselined_ci_ids) == 0
        and len(unverified_audit_ci_ids) == 0
    )

    if total_items == 0:
        configuration_posture = "NO_CONFIGURATION_ITEMS"
    elif len(unauthorized_drift_ci_ids) > 0:
        configuration_posture = "UNAUTHORIZED_CONFIGURATION_DRIFT"
    elif len(unbaselined_ci_ids) > 0:
        configuration_posture = "UNBASELINED_CONFIGURATION_ITEM"
    elif len(unverified_audit_ci_ids) > 0:
        configuration_posture = "PENDING_PCA_FCA_VERIFICATION"
    else:
        configuration_posture = "VERIFIED_CONFIGURATION_BASELINE"

    return {
        "total_items": total_items,
        "verified_items_count": verified_items_count,
        "unauthorized_drift_ci_ids": unauthorized_drift_ci_ids,
        "unbaselined_ci_ids": unbaselined_ci_ids,
        "unverified_audit_ci_ids": unverified_audit_ci_ids,
        "integrity_rate_pct": integrity_rate_pct,
        "is_configuration_compliant": is_configuration_compliant,
        "configuration_posture": configuration_posture,
    }


def evaluate_spc_process_stability(
    measurements: list[float] | None = None,
    center_line: float | None = None,
    ucl: float | None = None,
    lcl: float | None = None,
    usl: float | None = None,
    lsl: float | None = None,
) -> dict[str, Any]:
    """Evalúa estabilidad estadística del proceso (SPC Control Chart & Rule of Seven, PMI PMBOK §8.3.2.5)."""
    values: list[float] = []
    if isinstance(measurements, list):
        for raw_val in measurements:
            if isinstance(raw_val, bool) or raw_val is None:
                continue
            try:
                values.append(float(raw_val))
            except (TypeError, ValueError):
                continue

    if len(values) == 0:
        return {
            "sample_size": 0,
            "process_mean": round(float(center_line), 4) if center_line is not None else 0.0,
            "beyond_control_limit_indices": [],
            "beyond_spec_limit_indices": [],
            "max_same_side_run": 0,
            "has_rule_of_seven_run": False,
            "is_in_statistical_control": True,
            "spc_posture": "NO_MEASUREMENTS_PROVIDED",
        }

    mean_val = float(center_line) if center_line is not None else sum(values) / len(values)
    beyond_control_limit_indices: list[int] = []
    beyond_spec_limit_indices: list[int] = []
    above_run = 0
    below_run = 0
    max_same_side_run = 0

    for idx, val in enumerate(values):
        if (ucl is not None and val > float(ucl) + 1e-9) or (
            lcl is not None and val < float(lcl) - 1e-9
        ):
            beyond_control_limit_indices.append(idx)
        if (usl is not None and val > float(usl) + 1e-9) or (
            lsl is not None and val < float(lsl) - 1e-9
        ):
            beyond_spec_limit_indices.append(idx)

        if val > mean_val + 1e-9:
            above_run += 1
            below_run = 0
        elif val < mean_val - 1e-9:
            below_run += 1
            above_run = 0
        else:
            above_run = 0
            below_run = 0

        current_run = max(above_run, below_run)
        if current_run > max_same_side_run:
            max_same_side_run = current_run

    has_rule_of_seven_run = bool(max_same_side_run >= 7)
    is_in_statistical_control = bool(
        len(beyond_control_limit_indices) == 0
        and len(beyond_spec_limit_indices) == 0
        and not has_rule_of_seven_run
    )

    if len(beyond_spec_limit_indices) > 0:
        spc_posture = "SPECIFICATION_LIMIT_BREACH"
    elif len(beyond_control_limit_indices) > 0:
        spc_posture = "CONTROL_LIMIT_OUTLIER"
    elif has_rule_of_seven_run:
        spc_posture = "RULE_OF_SEVEN_NON_RANDOM_RUN"
    else:
        spc_posture = "IN_STATISTICAL_CONTROL"

    return {
        "sample_size": len(values),
        "process_mean": round(mean_val, 4),
        "beyond_control_limit_indices": beyond_control_limit_indices,
        "beyond_spec_limit_indices": beyond_spec_limit_indices,
        "max_same_side_run": max_same_side_run,
        "has_rule_of_seven_run": has_rule_of_seven_run,
        "is_in_statistical_control": is_in_statistical_control,
        "spc_posture": spc_posture,
    }


def _parse_fmea_rating(raw_val: Any) -> int:
    if raw_val is None or isinstance(raw_val, bool):
        return 1
    try:
        return max(1, min(10, int(float(raw_val))))
    except (TypeError, ValueError):
        return 1


def evaluate_fmea_rpn_criticality(
    failure_modes: list[dict[str, Any]] | None = None,
    rpn_threshold: int = 125,
    high_severity_threshold: int = 9,
) -> dict[str, Any]:
    """Evalúa modos y efectos de falla (FMEA RPN = S x O x D) y cobertura CAPA según PMI PMBOK §8.1.2.3 & §11.2."""
    items = [item for item in (failure_modes or []) if isinstance(item, dict)]
    total_failure_modes = len(items)
    if total_failure_modes == 0:
        return {
            "total_failure_modes": 0,
            "max_rpn": 0,
            "critical_modes_count": 0,
            "unmitigated_critical_mode_ids": [],
            "is_fmea_controlled": True,
            "fmea_posture": "NO_FAILURE_MODES_EVALUATED",
        }

    try:
        rpn_limit = int(rpn_threshold)
    except (TypeError, ValueError):
        rpn_limit = 125
    try:
        sev_limit = int(high_severity_threshold)
    except (TypeError, ValueError):
        sev_limit = 9

    max_rpn = 0
    critical_modes_count = 0
    unmitigated_critical_mode_ids: list[str] = []

    for idx, item in enumerate(items, start=1):
        fm_id = (
            str(
                item.get("id")
                or item.get("failure_mode_id")
                or item.get("code")
                or f"FM-{idx}"
            ).strip()
            or f"FM-{idx}"
        )
        severity = _parse_fmea_rating(
            item.get("severity") if item.get("severity") is not None else item.get("s")
        )
        occurrence = _parse_fmea_rating(
            item.get("occurrence")
            if item.get("occurrence") is not None
            else item.get("o")
        )
        detection = _parse_fmea_rating(
            item.get("detection")
            if item.get("detection") is not None
            else item.get("d")
        )
        rpn = severity * occurrence * detection
        if rpn > max_rpn:
            max_rpn = rpn

        action = str(
            item.get("recommended_action")
            or item.get("mitigation_action")
            or item.get("capa_action")
            or ""
        ).strip()
        owner = str(
            item.get("action_owner")
            or item.get("owner")
            or item.get("responsable")
            or ""
        ).strip()

        is_critical = (rpn >= rpn_limit) or (severity >= sev_limit)
        if is_critical:
            critical_modes_count += 1
            if len(action) < 5 or not owner:
                unmitigated_critical_mode_ids.append(fm_id)

    is_fmea_controlled = bool(len(unmitigated_critical_mode_ids) == 0)
    if len(unmitigated_critical_mode_ids) > 0:
        fmea_posture = "UNMITIGATED_CRITICAL_FAILURE_MODE"
    elif critical_modes_count > 0:
        fmea_posture = "MITIGATED_HIGH_RPN_EXPOSURE"
    else:
        fmea_posture = "LOW_RPN_BASELINE_RISK"

    return {
        "total_failure_modes": total_failure_modes,
        "max_rpn": max_rpn,
        "critical_modes_count": critical_modes_count,
        "unmitigated_critical_mode_ids": unmitigated_critical_mode_ids,
        "is_fmea_controlled": is_fmea_controlled,
        "fmea_posture": fmea_posture,
    }


def audit_emergency_change_ccb_ratification_governance(
    change_requests: list[dict[str, Any]] | None = None,
    max_ratification_days: int = 5,
    max_emergency_share_pct: float = 20.0,
) -> dict[str, Any]:
    """Audita ratificación retroactiva CCB de cambios de emergencia (PMBOK §4.6).

    Evalúa CRs válidos (con `id`/`cr_id` no vacío). Para cada CR de
    emergencia (`is_emergency` True) exige referencia de incidente y
    justificación, ratificación CCB tempestiva o confirmación con responsable
    al cerrar, y un ratio de emergencias dentro del límite:
    - `unjustified_emergency_cr_ids`: sin `incident_reference` o `justification`.
    - `overdue_ratification_cr_ids`: status fuera de {RATIFIED, CCB_APPROVED,
      CLOSED} con days_since_implementation > max(1, max_ratification_days).
    - `unratified_closed_emergency_cr_ids`: status ratificado/cerrado sin `ratified_by`.
    - `emergency_share_pct` (2 decimales; 0.0 sin CRs).
    - `is_emergency_governance_valid`: con emergencias, 3 listas vacías y share <= límite.
    - `emergency_posture`: 'NO_EMERGENCY_CHANGES' sin emergencias;
      'UNRATIFIED_EMERGENCY_CLOSURE'; 'OVERDUE_RETROACTIVE_CCB_RATIFICATION';
      'UNJUSTIFIED_EMERGENCY_BYPASS'; 'EXCESSIVE_EMERGENCY_CHANGE_RATIO';
      'GOVERNED_EMERGENCY_CHANGE_PROTOCOL'.
    """
    RATIFIED_STATUSES = {"RATIFIED", "CCB_APPROVED", "CLOSED"}
    valid_crs = [
        cr
        for cr in (change_requests or [])
        if isinstance(cr, dict) and str(cr.get("id") or cr.get("cr_id") or "").strip()
    ]
    total_change_requests = len(valid_crs)

    emergency_changes_count = 0
    unjustified_emergency_cr_ids: list[str] = []
    overdue_ratification_cr_ids: list[str] = []
    unratified_closed_emergency_cr_ids: list[str] = []

    for cr in valid_crs:
        cr_id = str(cr.get("id") or cr.get("cr_id") or "").strip()
        if not bool(cr.get("is_emergency", False)):
            continue
        emergency_changes_count += 1

        incident_reference = str(cr.get("incident_reference") or "").strip()
        justification = str(cr.get("justification") or "").strip()
        status = str(cr.get("status") or "IMPLEMENTED").strip().upper()
        try:
            days_since_implementation = int(cr.get("days_since_implementation") or 0)
        except (TypeError, ValueError):
            days_since_implementation = 0
        ratified_by = str(cr.get("ratified_by") or "").strip()

        if not incident_reference or not justification:
            unjustified_emergency_cr_ids.append(cr_id)
        if (
            status not in RATIFIED_STATUSES
            and days_since_implementation > max(1, int(max_ratification_days))
        ):
            overdue_ratification_cr_ids.append(cr_id)
        if status in RATIFIED_STATUSES and not ratified_by:
            unratified_closed_emergency_cr_ids.append(cr_id)

    emergency_share_pct = (
        round((emergency_changes_count / total_change_requests) * 100.0, 2)
        if total_change_requests > 0
        else 0.0
    )
    is_emergency_governance_valid = bool(
        emergency_changes_count > 0
        and len(unjustified_emergency_cr_ids) == 0
        and len(overdue_ratification_cr_ids) == 0
        and len(unratified_closed_emergency_cr_ids) == 0
        and emergency_share_pct <= float(max_emergency_share_pct)
    )

    if emergency_changes_count == 0:
        emergency_posture = "NO_EMERGENCY_CHANGES"
    elif len(unratified_closed_emergency_cr_ids) > 0:
        emergency_posture = "UNRATIFIED_EMERGENCY_CLOSURE"
    elif len(overdue_ratification_cr_ids) > 0:
        emergency_posture = "OVERDUE_RETROACTIVE_CCB_RATIFICATION"
    elif len(unjustified_emergency_cr_ids) > 0:
        emergency_posture = "UNJUSTIFIED_EMERGENCY_BYPASS"
    elif emergency_share_pct > float(max_emergency_share_pct):
        emergency_posture = "EXCESSIVE_EMERGENCY_CHANGE_RATIO"
    else:
        emergency_posture = "GOVERNED_EMERGENCY_CHANGE_PROTOCOL"

    return {
        "total_change_requests": total_change_requests,
        "emergency_changes_count": emergency_changes_count,
        "emergency_share_pct": emergency_share_pct,
        "unjustified_emergency_cr_ids": unjustified_emergency_cr_ids,
        "overdue_ratification_cr_ids": overdue_ratification_cr_ids,
        "unratified_closed_emergency_cr_ids": unratified_closed_emergency_cr_ids,
        "is_emergency_governance_valid": is_emergency_governance_valid,
        "emergency_posture": emergency_posture,
    }


class ProjectCCBService:
    """Fachada canónica de Control Integrado de Cambios (CCB) y Calidad DoD PMI."""

    @staticmethod
    def list_change_requests(
        db: Session, project: models.Project
    ) -> schemas.ProjectChangeRequestListResponse:
        return list_change_requests(db, project)

    @staticmethod
    def create_change_request(
        db: Session,
        project: models.Project,
        cr_in: schemas.ProjectChangeRequestCreate,
        actor_persona_id: UUID,
    ) -> models.ProjectChangeRequest:
        return create_change_request(db, project, cr_in, actor_persona_id)

    @staticmethod
    def decide_change_request(
        db: Session,
        project: models.Project,
        cr: models.ProjectChangeRequest,
        decision_in: schemas.ProjectChangeRequestDecide,
        actor_persona_id: UUID,
    ) -> models.ProjectChangeRequest:
        return decide_change_request(db, project, cr, decision_in, actor_persona_id)

    @staticmethod
    def get_dod_acceptance(
        db: Session, project: models.Project, task_id: UUID
    ) -> Optional[models.ProjectDodAcceptance]:
        return get_dod_acceptance(db, project, task_id)

    @staticmethod
    def upsert_dod_acceptance(
        db: Session,
        project: models.Project,
        task: models.ProjectTask,
        payload: schemas.ProjectDodAcceptanceUpdate,
        actor_persona_id: UUID,
    ) -> models.ProjectDodAcceptance:
        return upsert_dod_acceptance(db, project, task, payload, actor_persona_id)

    @staticmethod
    def get_project_ccb_and_quality_summary(db: Session, project_id: UUID) -> dict:
        return get_project_ccb_and_quality_summary(db, project_id)

    @staticmethod
    def compute_ccb_approval_rate_pct(
        approved_count: int, rejected_count: int
    ) -> float:
        return compute_ccb_approval_rate_pct(approved_count, rejected_count)

    @staticmethod
    def evaluate_coq_balance_status(
        coq_conformance_ratio_pct: float, total_coq_cost: float
    ) -> str:
        return evaluate_coq_balance_status(coq_conformance_ratio_pct, total_coq_cost)

    @staticmethod
    def build_ccb_coq_diagnostic(summary: dict) -> dict:
        return build_ccb_coq_diagnostic(summary)

    @staticmethod
    def evaluate_dod_gate_compliance(summary: dict) -> dict:
        return evaluate_dod_gate_compliance(summary)

    @staticmethod
    def evaluate_project_communications_complexity(
        participant_count: int, message_count: int = 0
    ) -> dict:
        return evaluate_project_communications_complexity(
            participant_count, message_count=message_count
        )

    @staticmethod
    def evaluate_ccb_baseline_creep_impact(
        net_approved_cost_delta: float,
        bac: float,
        net_approved_schedule_days: int,
        planned_duration_days: int = 0,
    ) -> dict:
        return evaluate_ccb_baseline_creep_impact(
            net_approved_cost_delta,
            bac,
            net_approved_schedule_days,
            planned_duration_days=planned_duration_days,
        )

    @staticmethod
    def evaluate_cost_of_quality_balance(
        prevention_cost: float = 0.0,
        appraisal_cost: float = 0.0,
        internal_failure_cost: float = 0.0,
        external_failure_cost: float = 0.0,
    ) -> dict:
        return evaluate_cost_of_quality_balance(
            prevention_cost=prevention_cost,
            appraisal_cost=appraisal_cost,
            internal_failure_cost=internal_failure_cost,
            external_failure_cost=external_failure_cost,
        )

    @staticmethod
    def evaluate_ccb_backlog_velocity(
        change_requests: list[dict[str, Any]] | None,
        sla_days: float = 7.0,
    ) -> dict[str, Any]:
        return evaluate_ccb_backlog_velocity(change_requests, sla_days=sla_days)

    @staticmethod
    def evaluate_defect_containment_efficiency(
        pre_delivery_defects: int,
        post_delivery_defects: int,
        reworked_verified_count: int = 0,
    ) -> dict[str, Any]:
        return evaluate_defect_containment_efficiency(
            pre_delivery_defects,
            post_delivery_defects,
            reworked_verified_count=reworked_verified_count,
        )

    @staticmethod
    def evaluate_dod_checklist_verification_depth(
        checklist_items: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return evaluate_dod_checklist_verification_depth(checklist_items)

    @staticmethod
    def evaluate_scope_creep_baseline_drift(
        baseline_tasks_count: int | None,
        current_tasks_count: int | None,
        approved_change_requests_tasks_delta: int | None = 0,
    ) -> dict[str, Any]:
        return evaluate_scope_creep_baseline_drift(
            baseline_tasks_count,
            current_tasks_count,
            approved_change_requests_tasks_delta=approved_change_requests_tasks_delta,
        )

    @staticmethod
    def evaluate_ccb_voting_consensus(
        votes: list[dict[str, Any]] | None,
        required_quorum: int | None = 3,
    ) -> dict[str, Any]:
        return evaluate_ccb_voting_consensus(votes, required_quorum=required_quorum)

    @staticmethod
    def audit_ccb_decision_sla_breaches(
        requests: list[dict[str, Any]] | None,
        sla_hours: float | int | None = 72.0,
    ) -> dict[str, Any]:
        return audit_ccb_decision_sla_breaches(requests, sla_hours=sla_hours)

    @staticmethod
    def audit_emergency_change_retroactive_ratification(
        change_requests: Optional[list[dict]],
        total_requests_window: Optional[int] = None,
        max_emergency_share_pct: float = 20.0,
    ) -> dict:
        return audit_emergency_change_retroactive_ratification(
            change_requests,
            total_requests_window=total_requests_window,
            max_emergency_share_pct=max_emergency_share_pct,
        )

    @staticmethod
    def audit_emergency_change_ccb_ratification_governance(
        change_requests: list[dict[str, Any]] | None = None,
        max_ratification_days: int = 5,
        max_emergency_share_pct: float = 20.0,
    ) -> dict[str, Any]:
        return audit_emergency_change_ccb_ratification_governance(
            change_requests,
            max_ratification_days=max_ratification_days,
            max_emergency_share_pct=max_emergency_share_pct,
        )

    @staticmethod
    def audit_pareto_defect_root_causes(
        defects: Optional[list[dict]],
        vital_few_threshold_pct: float = 80.0,
    ) -> dict:
        return audit_pareto_defect_root_causes(
            defects, vital_few_threshold_pct=vital_few_threshold_pct
        )

    @staticmethod
    def evaluate_deliverable_first_time_right_yield(
        deliverables: Optional[list[dict[str, Any]]],
        target_ftr_pct: float = 85.0,
    ) -> dict[str, Any]:
        return evaluate_deliverable_first_time_right_yield(
            deliverables, target_ftr_pct=target_ftr_pct
        )

    @staticmethod
    def audit_configuration_baseline_integrity(
        configuration_items: Optional[list[dict]],
    ) -> dict[str, Any]:
        return audit_configuration_baseline_integrity(configuration_items)

    @staticmethod
    def audit_configuration_items_baseline_integrity(
        configuration_items: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return audit_configuration_items_baseline_integrity(configuration_items)

    @staticmethod
    def evaluate_spc_process_stability(
        measurements: list[float] | None = None,
        center_line: float | None = None,
        ucl: float | None = None,
        lcl: float | None = None,
        usl: float | None = None,
        lsl: float | None = None,
    ) -> dict[str, Any]:
        return evaluate_spc_process_stability(
            measurements,
            center_line=center_line,
            ucl=ucl,
            lcl=lcl,
            usl=usl,
            lsl=lsl,
        )

    @staticmethod
    def evaluate_fmea_rpn_criticality(
        failure_modes: list[dict[str, Any]] | None = None,
        rpn_threshold: int = 125,
        high_severity_threshold: int = 9,
    ) -> dict[str, Any]:
        return evaluate_fmea_rpn_criticality(
            failure_modes,
            rpn_threshold=rpn_threshold,
            high_severity_threshold=high_severity_threshold,
        )

    @staticmethod
    def audit_unapproved_scope_creep_exposure(
        work_packages: Optional[list[dict[str, Any]]],
        tolerance_hours_pct: float = 10.0,
    ) -> dict[str, Any]:
        return audit_unapproved_scope_creep_exposure(
            work_packages, tolerance_hours_pct=tolerance_hours_pct
        )

    @staticmethod
    def evaluate_cost_of_quality_prevention_balance(
        coq_entries: Optional[List[Dict[str, Any]]] = None,
        max_failure_cost_share_pct: float = 35.0,
    ) -> Dict[str, Any]:
        return evaluate_cost_of_quality_prevention_balance(
            coq_entries,
            max_failure_cost_share_pct=max_failure_cost_share_pct,
        )

    @staticmethod
    def evaluate_defect_containment_and_escape_rate(
        defects: Optional[List[Dict[str, Any]]] = None,
        min_containment_effectiveness_pct: float = 85.0,
    ) -> Dict[str, Any]:
        return evaluate_defect_containment_and_escape_rate(
            defects,
            min_containment_effectiveness_pct=min_containment_effectiveness_pct,
        )

    @staticmethod
    def evaluate_quality_ncr_sla_compliance(
        ncrs: list[dict[str, Any]] | None = None,
        major_sla_days: int = 7,
        minor_sla_days: int = 14,
    ) -> dict[str, Any]:
        return evaluate_quality_ncr_sla_compliance(
            ncrs,
            major_sla_days=major_sla_days,
            minor_sla_days=minor_sla_days,
        )

    @staticmethod
    def evaluate_pareto_vital_few_defect_causes(
        defect_categories: list[dict[str, Any]] | None = None,
        pareto_cutoff_pct: float = 80.0,
    ) -> dict[str, Any]:
        return evaluate_pareto_vital_few_defect_causes(
            defect_categories,
            pareto_cutoff_pct=pareto_cutoff_pct,
        )

    @staticmethod
    def evaluate_deliverable_acceptance_traceability(
        deliverables: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return evaluate_deliverable_acceptance_traceability(deliverables)

    @staticmethod
    def evaluate_cost_of_quality_conformance_balance(
        coq_entries: Sequence[Mapping[str, Any]] | None = None,
        *,
        min_conformance_share_pct: float = 50.0,
        max_external_failure_share_pct: float = 15.0,
    ) -> dict[str, Any]:
        return evaluate_cost_of_quality_conformance_balance(
            coq_entries,
            min_conformance_share_pct=min_conformance_share_pct,
            max_external_failure_share_pct=max_external_failure_share_pct,
        )

    @staticmethod
    def evaluate_spc_control_chart_stability(
        measurements: Sequence[float] | None,
        *,
        center_line: float,
        upper_control_limit: float,
        lower_control_limit: float,
        upper_spec_limit: float | None = None,
        lower_spec_limit: float | None = None,
    ) -> dict[str, Any]:
        return evaluate_spc_control_chart_stability(
            measurements,
            center_line=center_line,
            upper_control_limit=upper_control_limit,
            lower_control_limit=lower_control_limit,
            upper_spec_limit=upper_spec_limit,
            lower_spec_limit=lower_spec_limit,
        )


def evaluate_quality_ncr_sla_compliance(
    ncrs: list[dict[str, Any]] | None = None,
    major_sla_days: int = 7,
    minor_sla_days: int = 14,
) -> dict[str, Any]:
    """Evalúa reportes de No Conformidad de Calidad (NCR), cumplimiento de SLA por severidad, RCA y evidencia de cierre según PMI PMBOK §8.2 y §8.3."""
    items = [item for item in (ncrs or []) if isinstance(item, dict)]
    try:
        major_limit = max(1, int(major_sla_days))
    except (TypeError, ValueError):
        major_limit = 7
    try:
        minor_limit = max(1, int(minor_sla_days))
    except (TypeError, ValueError):
        minor_limit = 14
    critical_limit = max(1, major_limit // 2)

    total_ncrs = 0
    open_ncrs_count = 0
    sla_breached_ncr_ids: list[str] = []
    missing_rca_ncr_ids: list[str] = []
    unverified_closed_ncr_ids: list[str] = []

    for item in items:
        ncr_id = str(item.get("id") or item.get("ncr_id") or "").strip()
        if not ncr_id:
            continue
        total_ncrs += 1
        severity = str(item.get("severity") or "MINOR").strip().upper()
        status = str(item.get("status") or "OPEN").strip().upper()
        try:
            age_days = max(0, int(item.get("age_days") or 0))
        except (TypeError, ValueError):
            age_days = 0
        root_cause = str(item.get("root_cause") or "").strip()
        verification_evidence = str(
            item.get("verification_evidence") or ""
        ).strip()

        if status != "CLOSED":
            open_ncrs_count += 1
            if severity == "CRITICAL":
                sla_limit = critical_limit
            elif severity == "MAJOR":
                sla_limit = major_limit
            else:
                sla_limit = minor_limit

            if age_days > sla_limit:
                sla_breached_ncr_ids.append(ncr_id)
            if severity in {"CRITICAL", "MAJOR"} and not root_cause:
                missing_rca_ncr_ids.append(ncr_id)
        else:
            if not verification_evidence:
                unverified_closed_ncr_ids.append(ncr_id)

    is_ncr_governance_compliant = bool(
        total_ncrs > 0
        and len(sla_breached_ncr_ids) == 0
        and len(missing_rca_ncr_ids) == 0
        and len(unverified_closed_ncr_ids) == 0
    )

    if total_ncrs == 0:
        ncr_posture = "NO_NCRS_RECORDED"
    elif len(unverified_closed_ncr_ids) > 0:
        ncr_posture = "UNVERIFIED_NCR_CLOSURE"
    elif len(sla_breached_ncr_ids) > 0:
        ncr_posture = "NCR_SLA_BREACH"
    elif len(missing_rca_ncr_ids) > 0:
        ncr_posture = "MISSING_MAJOR_NCR_ROOT_CAUSE"
    else:
        ncr_posture = "COMPLIANT_NCR_GOVERNANCE"

    return {
        "total_ncrs": total_ncrs,
        "open_ncrs_count": open_ncrs_count,
        "sla_breached_ncr_ids": sla_breached_ncr_ids,
        "missing_rca_ncr_ids": missing_rca_ncr_ids,
        "unverified_closed_ncr_ids": unverified_closed_ncr_ids,
        "is_ncr_governance_compliant": is_ncr_governance_compliant,
        "ncr_posture": ncr_posture,
    }


def evaluate_pareto_vital_few_defect_causes(
    defect_categories: list[dict[str, Any]] | None = None,
    pareto_cutoff_pct: float = 80.0,
) -> dict[str, Any]:
    """Evalúa la concentración Pareto 80/20 de causas raíz de defectos y cobertura CAPA en causas vitales (PMBOK §8.3.2.5)."""
    valid_categories: list[dict[str, Any]] = []
    for item in defect_categories or []:
        if not isinstance(item, dict):
            continue
        category_id = str(item.get("category_id") or item.get("id") or "").strip()
        if not category_id:
            continue
        try:
            defect_count = max(0, int(item.get("defect_count") or 0))
        except (TypeError, ValueError):
            defect_count = 0
        if defect_count > 0:
            valid_categories.append(
                {
                    "category_id": category_id,
                    "defect_count": defect_count,
                    "has_capa_plan": bool(item.get("has_capa_plan", False)),
                }
            )

    if not valid_categories:
        return {
            "total_defects": 0,
            "total_categories": 0,
            "vital_few_category_ids": [],
            "vital_few_share_pct": 0.0,
            "unmitigated_vital_category_ids": [],
            "is_pareto_actionable": False,
            "pareto_posture": "NO_DEFECT_DATA",
        }

    sorted_cats = sorted(
        valid_categories, key=lambda c: (-c["defect_count"], c["category_id"])
    )
    total_defects = sum(c["defect_count"] for c in sorted_cats)
    cutoff = float(pareto_cutoff_pct)

    vital_few_category_ids: list[str] = []
    unmitigated_vital_category_ids: list[str] = []
    vital_defects_sum = 0

    for c in sorted_cats:
        prev_pct = (vital_defects_sum / total_defects) * 100.0
        if prev_pct < cutoff - 1e-9 or len(vital_few_category_ids) == 0:
            cid = c["category_id"]
            vital_few_category_ids.append(cid)
            vital_defects_sum += c["defect_count"]
            if not c["has_capa_plan"]:
                unmitigated_vital_category_ids.append(cid)
        else:
            break

    vital_few_share_pct = round((vital_defects_sum / total_defects) * 100.0, 2)
    concentration_ratio = len(vital_few_category_ids) / len(sorted_cats)
    is_pareto_actionable = len(unmitigated_vital_category_ids) == 0

    if len(unmitigated_vital_category_ids) > 0:
        pareto_posture = "UNMITIGATED_VITAL_FEW_CAUSES"
    elif concentration_ratio <= 0.5:
        pareto_posture = "HIGH_PARETO_CONCENTRATION_GOVERNED"
    else:
        pareto_posture = "DISPERSED_DEFECT_DISTRIBUTION"

    return {
        "total_defects": total_defects,
        "total_categories": len(sorted_cats),
        "vital_few_category_ids": vital_few_category_ids,
        "vital_few_share_pct": vital_few_share_pct,
        "unmitigated_vital_category_ids": unmitigated_vital_category_ids,
        "is_pareto_actionable": is_pareto_actionable,
        "pareto_posture": pareto_posture,
    }


def evaluate_deliverable_acceptance_traceability(
    deliverables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evalúa trazabilidad de verificación QC (Control Quality) previa a aceptación formal de entregables (Validate Scope) según PMI PMBOK §8.3 y §5.5."""
    total_deliverables = 0
    accepted_deliverables_count = 0
    accepted_without_qc_ids: list[str] = []
    missing_signoff_deliverable_ids: list[str] = []
    unlinked_requirement_deliverable_ids: list[str] = []

    for item in deliverables or []:
        if not isinstance(item, dict):
            continue
        deliv_id = str(item.get("id") or item.get("deliverable_id") or "").strip()
        if not deliv_id:
            continue

        qc_verified = bool(item.get("qc_verified", False))
        scope_accepted = bool(item.get("scope_accepted", False))
        try:
            open_critical_defects = max(
                0, int(item.get("open_critical_defects") or 0)
            )
        except (TypeError, ValueError):
            open_critical_defects = 0
        acceptance_signoff_by = str(item.get("acceptance_signoff_by") or "").strip()
        requirement_id = str(item.get("requirement_id") or "").strip()

        total_deliverables += 1
        if scope_accepted:
            accepted_deliverables_count += 1
            if not qc_verified or open_critical_defects > 0:
                accepted_without_qc_ids.append(deliv_id)
            if not acceptance_signoff_by:
                missing_signoff_deliverable_ids.append(deliv_id)
        if not requirement_id:
            unlinked_requirement_deliverable_ids.append(deliv_id)

    is_acceptance_chain_valid = bool(
        total_deliverables > 0
        and len(accepted_without_qc_ids) == 0
        and len(missing_signoff_deliverable_ids) == 0
        and len(unlinked_requirement_deliverable_ids) == 0
    )

    if total_deliverables == 0:
        acceptance_posture = "NO_DELIVERABLES_REGISTERED"
    elif len(accepted_without_qc_ids) > 0:
        acceptance_posture = "SCOPE_ACCEPTED_WITHOUT_QC_VERIFICATION"
    elif len(missing_signoff_deliverable_ids) > 0:
        acceptance_posture = "MISSING_FORMAL_ACCEPTANCE_SIGNOFF"
    elif len(unlinked_requirement_deliverable_ids) > 0:
        acceptance_posture = "UNLINKED_REQUIREMENT_TRACEABILITY"
    else:
        acceptance_posture = "VERIFIED_AND_VALIDATED_DELIVERABLES"

    return {
        "total_deliverables": total_deliverables,
        "accepted_deliverables_count": accepted_deliverables_count,
        "accepted_without_qc_ids": accepted_without_qc_ids,
        "missing_signoff_deliverable_ids": missing_signoff_deliverable_ids,
        "unlinked_requirement_deliverable_ids": unlinked_requirement_deliverable_ids,
        "is_acceptance_chain_valid": is_acceptance_chain_valid,
        "acceptance_posture": acceptance_posture,
    }


def evaluate_cost_of_quality_conformance_balance(
    coq_entries: Sequence[Mapping[str, Any]] | None = None,
    *,
    min_conformance_share_pct: float = 50.0,
    max_external_failure_share_pct: float = 15.0,
) -> dict[str, Any]:
    """Evalúa el equilibrio de Costo de la Calidad (CoQ: Conformidad vs No Conformidad) según PMI PMBOK §8.1.2.3."""
    valid_categories = {
        "prevention",
        "appraisal",
        "internal_failure",
        "external_failure",
    }
    evaluated_entry_count = 0
    prevention_cost = 0.0
    appraisal_cost = 0.0
    internal_failure_cost = 0.0
    external_failure_cost = 0.0
    invalid_entry_ids: list[str] = []

    for item in coq_entries or []:
        if not isinstance(item, Mapping):
            continue
        entry_id = str(item.get("entry_id") or "").strip()
        if not entry_id:
            continue

        evaluated_entry_count += 1
        category = str(item.get("category") or "").strip().lower()
        raw_amount = item.get("amount", 0.0)
        try:
            amount = float(0.0 if raw_amount is None else raw_amount)
        except (TypeError, ValueError):
            invalid_entry_ids.append(entry_id)
            continue

        if category not in valid_categories or amount < 0.0:
            invalid_entry_ids.append(entry_id)
            continue

        if category == "prevention":
            prevention_cost += amount
        elif category == "appraisal":
            appraisal_cost += amount
        elif category == "internal_failure":
            internal_failure_cost += amount
        elif category == "external_failure":
            external_failure_cost += amount

    prevention_cost = round(prevention_cost, 2)
    appraisal_cost = round(appraisal_cost, 2)
    internal_failure_cost = round(internal_failure_cost, 2)
    external_failure_cost = round(external_failure_cost, 2)

    conformance_cost = round(prevention_cost + appraisal_cost, 2)
    nonconformance_cost = round(internal_failure_cost + external_failure_cost, 2)
    total_coq = round(conformance_cost + nonconformance_cost, 2)

    if total_coq > 0.0:
        conformance_share_pct = round((conformance_cost / total_coq) * 100.0, 2)
        nonconformance_share_pct = round((nonconformance_cost / total_coq) * 100.0, 2)
        external_failure_share_pct = round(
            (external_failure_cost / total_coq) * 100.0, 2
        )
    else:
        conformance_share_pct = 100.0
        nonconformance_share_pct = 0.0
        external_failure_share_pct = 0.0

    if nonconformance_cost > 0.0:
        prevention_to_failure_ratio = round(prevention_cost / nonconformance_cost, 2)
    else:
        prevention_to_failure_ratio = round(prevention_cost, 2)

    is_conformance_balanced = bool(
        evaluated_entry_count > 0
        and len(invalid_entry_ids) == 0
        and conformance_share_pct >= float(min_conformance_share_pct)
        and external_failure_share_pct <= float(max_external_failure_share_pct)
    )

    return {
        "evaluated_entry_count": evaluated_entry_count,
        "prevention_cost": prevention_cost,
        "appraisal_cost": appraisal_cost,
        "internal_failure_cost": internal_failure_cost,
        "external_failure_cost": external_failure_cost,
        "conformance_cost": conformance_cost,
        "nonconformance_cost": nonconformance_cost,
        "total_coq": total_coq,
        "conformance_share_pct": conformance_share_pct,
        "nonconformance_share_pct": nonconformance_share_pct,
        "external_failure_share_pct": external_failure_share_pct,
        "prevention_to_failure_ratio": prevention_to_failure_ratio,
        "invalid_entry_ids": invalid_entry_ids,
        "is_conformance_balanced": is_conformance_balanced,
    }


def evaluate_spc_control_chart_stability(
    measurements: Sequence[float] | None,
    *,
    center_line: float,
    upper_control_limit: float,
    lower_control_limit: float,
    upper_spec_limit: float | None = None,
    lower_spec_limit: float | None = None,
) -> dict[str, Any]:
    """Evalúa la estabilidad de un proceso mediante Diagramas de Control Estadístico (SPC Control Charts y Regla de Siete) según PMI PMBOK §8.3.2.4."""
    cl = float(center_line)
    ucl = float(upper_control_limit)
    lcl = float(lower_control_limit)
    usl = float(upper_spec_limit) if upper_spec_limit is not None else None
    lsl = float(lower_spec_limit) if lower_spec_limit is not None else None

    has_invalid_limits = bool(ucl <= lcl or not (lcl <= cl <= ucl))

    samples = list(measurements or [])
    sample_count = len(samples)
    out_of_control_indices: list[int] = []
    out_of_spec_indices: list[int] = []
    rule_of_seven_violation_indices: list[int] = []

    above_streak = 0
    below_streak = 0

    for idx, raw_val in enumerate(samples):
        val = float(raw_val)
        if val > ucl or val < lcl:
            out_of_control_indices.append(idx)
        if (usl is not None and val > usl) or (lsl is not None and val < lsl):
            out_of_spec_indices.append(idx)

        if val > cl:
            above_streak += 1
            below_streak = 0
        elif val < cl:
            below_streak += 1
            above_streak = 0
        else:
            above_streak = 0
            below_streak = 0

        if above_streak >= 7 or below_streak >= 7:
            rule_of_seven_violation_indices.append(idx)

    is_in_statistical_control = bool(
        sample_count > 0
        and not has_invalid_limits
        and len(out_of_control_indices) == 0
        and len(out_of_spec_indices) == 0
        and len(rule_of_seven_violation_indices) == 0
    )

    return {
        "sample_count": sample_count,
        "has_invalid_limits": has_invalid_limits,
        "out_of_control_indices": out_of_control_indices,
        "out_of_spec_indices": out_of_spec_indices,
        "rule_of_seven_violation_indices": rule_of_seven_violation_indices,
        "is_in_statistical_control": is_in_statistical_control,
    }


__all__ = [
    "list_change_requests",
    "row_list_adapter",
    "create_change_request",
    "decide_change_request",
    "get_dod_acceptance",
    "upsert_dod_acceptance",
    "get_project_ccb_and_quality_summary",
    "compute_ccb_approval_rate_pct",
    "evaluate_coq_balance_status",
    "build_ccb_coq_diagnostic",
    "evaluate_dod_gate_compliance",
    "evaluate_project_communications_complexity",
    "evaluate_ccb_baseline_creep_impact",
    "evaluate_cost_of_quality_balance",
    "evaluate_ccb_backlog_velocity",
    "evaluate_defect_containment_efficiency",
    "evaluate_dod_checklist_verification_depth",
    "evaluate_scope_creep_baseline_drift",
    "evaluate_ccb_voting_consensus",
    "audit_ccb_decision_sla_breaches",
    "audit_emergency_change_retroactive_ratification",
    "audit_emergency_change_ccb_ratification_governance",
    "audit_pareto_defect_root_causes",
    "audit_unapproved_scope_creep_exposure",
    "evaluate_cost_of_quality_prevention_balance",
    "evaluate_defect_containment_and_escape_rate",
    "evaluate_deliverable_first_time_right_yield",
    "audit_configuration_baseline_integrity",
    "audit_configuration_items_baseline_integrity",
    "evaluate_spc_process_stability",
    "evaluate_fmea_rpn_criticality",
    "evaluate_quality_ncr_sla_compliance",
    "evaluate_pareto_vital_few_defect_causes",
    "evaluate_deliverable_acceptance_traceability",
    "evaluate_cost_of_quality_conformance_balance",
    "evaluate_spc_control_chart_stability",
    "evaluate_quality_capa_root_cause_effectiveness",
    "evaluate_ccb_emergency_change_retrospective_compliance",
    "evaluate_quality_aql_lot_sampling_acceptance",
    "evaluate_copq_rework_and_scrap_ratio",
    "audit_ccb_change_request_sla_and_aging_backlog",
    "ProjectCCBService",
]



def audit_configuration_items_baseline_integrity(
    configuration_items: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """PMBOK §4.6.2.2 — integridad de Elementos de Configuración (CIs) frente a la línea base aprobada.

    Para cada CI con ``ci_id`` válido:
    - sin ``baseline_version`` o sin ``deployed_version`` -> ``unbaselined_ci_ids``.
    - ``deployed_version`` != ``baseline_version`` -> ``version_drift_ci_ids``;
      si además no hay ``approved_change_request_id`` -> ``unauthorized_drift_ci_ids``.
    - ``checksum_verified`` falso -> ``unverified_checksum_ci_ids``.
    """
    if not isinstance(configuration_items, (list, tuple)):
        configuration_items = []

    evaluated_ci_count = 0
    unbaselined_ci_ids: list[str] = []
    version_drift_ci_ids: list[str] = []
    unauthorized_drift_ci_ids: list[str] = []
    unverified_checksum_ci_ids: list[str] = []

    for item in configuration_items:
        if not isinstance(item, Mapping):
            continue
        ci_id = str(item.get("ci_id") or "").strip()
        if not ci_id:
            continue
        evaluated_ci_count += 1

        baseline_version = str(item.get("baseline_version") or "").strip()
        deployed_version = str(item.get("deployed_version") or "").strip()
        approved_change_request_id = str(
            item.get("approved_change_request_id") or ""
        ).strip()
        checksum_verified = bool(item.get("checksum_verified", False))

        if not baseline_version or not deployed_version:
            unbaselined_ci_ids.append(ci_id)
            continue

        if deployed_version != baseline_version:
            version_drift_ci_ids.append(ci_id)
            if not approved_change_request_id:
                unauthorized_drift_ci_ids.append(ci_id)

        if not checksum_verified:
            unverified_checksum_ci_ids.append(ci_id)

    is_integrity_verified = bool(
        evaluated_ci_count > 0
        and len(unbaselined_ci_ids) == 0
        and len(unauthorized_drift_ci_ids) == 0
        and len(unverified_checksum_ci_ids) == 0
    )

    return {
        "evaluated_ci_count": evaluated_ci_count,
        "unbaselined_ci_ids": unbaselined_ci_ids,
        "version_drift_ci_ids": version_drift_ci_ids,
        "unauthorized_drift_ci_ids": unauthorized_drift_ci_ids,
        "unverified_checksum_ci_ids": unverified_checksum_ci_ids,
        "is_integrity_verified": is_integrity_verified,
    }


def evaluate_quality_capa_root_cause_effectiveness(
    capa_records: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Evalúa la efectividad de acciones correctivas y preventivas (CAPA) mediante análisis de causa raíz (RCA), verificación de cierre y no recurrencia según PMI PMBOK §8.2 y §8.3."""
    if (
        capa_records is None
        or isinstance(capa_records, (str, bytes, Mapping))
        or not isinstance(capa_records, Sequence)
    ):
        items: Sequence[Any] = []
    else:
        items = capa_records

    valid_rca_methods = {"5_whys", "ishikawa", "fmea", "fault_tree", "pareto"}
    total_capas = 0
    effective_count = 0
    missing_rca_method_capa_ids: list[str] = []
    unverified_closure_capa_ids: list[str] = []
    recurring_defect_capa_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        capa_id = str(item.get("capa_id") or "").strip()
        if not capa_id:
            continue

        total_capas += 1
        root_cause_method = str(item.get("root_cause_method") or "").strip().lower()
        verification_passed = bool(item.get("verification_passed", False))
        try:
            recurrence_count = max(0, int(item.get("recurrence_count", 0) or 0))
        except (TypeError, ValueError):
            recurrence_count = 0
        status = str(item.get("status") or "").strip().lower()

        has_valid_rca = root_cause_method in valid_rca_methods
        if not has_valid_rca:
            missing_rca_method_capa_ids.append(capa_id)

        if status in {"closed", "verified", "effective"} and not verification_passed:
            unverified_closure_capa_ids.append(capa_id)

        if recurrence_count > 0:
            recurring_defect_capa_ids.append(capa_id)

        if has_valid_rca and verification_passed and recurrence_count == 0:
            effective_count += 1

    effectiveness_rate_pct = (
        round((effective_count / total_capas) * 100.0, 2)
        if total_capas > 0
        else 0.0
    )
    is_capa_system_healthy = bool(
        total_capas > 0
        and not missing_rca_method_capa_ids
        and not unverified_closure_capa_ids
        and not recurring_defect_capa_ids
    )

    return {
        "total_capas": total_capas,
        "missing_rca_method_capa_ids": missing_rca_method_capa_ids,
        "unverified_closure_capa_ids": unverified_closure_capa_ids,
        "recurring_defect_capa_ids": recurring_defect_capa_ids,
        "effectiveness_rate_pct": effectiveness_rate_pct,
        "is_capa_system_healthy": is_capa_system_healthy,
    }


ProjectCCBService.evaluate_quality_capa_root_cause_effectiveness = staticmethod(
    evaluate_quality_capa_root_cause_effectiveness
)


def evaluate_ccb_emergency_change_retrospective_compliance(
    change_requests: Sequence[Mapping[str, Any]] | None,
    *,
    max_retrospective_sla_hours: float = 48.0,
) -> dict[str, Any]:
    """Evalúa el cumplimiento retrospectivo de cambios de emergencia (fast-track) ante el CCB verificando plan de reversión, ratificación formal y revisión post-implementación (PIR) dentro del SLA según PMI PMBOK §4.6."""
    if (
        change_requests is None
        or isinstance(change_requests, (str, bytes, Mapping))
        or not isinstance(change_requests, Sequence)
    ):
        items: Sequence[Any] = []
    else:
        items = change_requests

    total_emergency_changes = 0
    missing_rollback_plan_cr_ids: list[str] = []
    unratified_emergency_cr_ids: list[str] = []
    sla_breached_pir_cr_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        if not bool(item.get("is_emergency", False)):
            continue
        cr_id = str(item.get("cr_id") or "").strip()
        if not cr_id:
            continue

        total_emergency_changes += 1
        raw_pir = item.get("post_implementation_review_hours")
        try:
            pir_hours = (
                float(raw_pir)
                if raw_pir is not None and not isinstance(raw_pir, bool)
                else -1.0
            )
        except (TypeError, ValueError):
            pir_hours = -1.0

        rollback_plan_documented = bool(
            item.get("rollback_plan_documented", False)
        )
        ccb_ratified = bool(item.get("ccb_ratified", False))

        if not rollback_plan_documented:
            missing_rollback_plan_cr_ids.append(cr_id)
        if not ccb_ratified:
            unratified_emergency_cr_ids.append(cr_id)
        if pir_hours < 0.0 or pir_hours > float(max_retrospective_sla_hours):
            sla_breached_pir_cr_ids.append(cr_id)

    is_emergency_governance_compliant = bool(
        total_emergency_changes > 0
        and not missing_rollback_plan_cr_ids
        and not unratified_emergency_cr_ids
        and not sla_breached_pir_cr_ids
    )

    return {
        "total_emergency_changes": total_emergency_changes,
        "missing_rollback_plan_cr_ids": missing_rollback_plan_cr_ids,
        "unratified_emergency_cr_ids": unratified_emergency_cr_ids,
        "sla_breached_pir_cr_ids": sla_breached_pir_cr_ids,
        "is_emergency_governance_compliant": is_emergency_governance_compliant,
    }


ProjectCCBService.evaluate_ccb_emergency_change_retrospective_compliance = staticmethod(
    evaluate_ccb_emergency_change_retrospective_compliance
)


def evaluate_quality_aql_lot_sampling_acceptance(
    inspection_lots: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Evalúa lotes de muestreo estadístico de calidad (AQL Lot Acceptance Inspection) según PMI PMBOK §8.3 y §5.5."""
    if (
        inspection_lots is None
        or isinstance(inspection_lots, (str, bytes, Mapping))
        or not isinstance(inspection_lots, Sequence)
    ):
        items: Sequence[Any] = []
    else:
        items = inspection_lots

    total_lots = 0
    accepted_lot_ids: list[str] = []
    rejected_lot_ids: list[str] = []
    invalid_sample_size_lot_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        lot_id = str(item.get("lot_id") or "").strip()
        if not lot_id:
            continue

        total_lots += 1
        try:
            lot_size = int(item.get("lot_size", 0) or 0)
        except (TypeError, ValueError):
            lot_size = 0

        try:
            sample_size = int(item.get("sample_size", 0) or 0)
        except (TypeError, ValueError):
            sample_size = 0

        try:
            defects_found = max(0, int(item.get("defects_found", 0) or 0))
        except (TypeError, ValueError):
            defects_found = 0

        try:
            acceptance_number = max(0, int(item.get("acceptance_number", 0) or 0))
        except (TypeError, ValueError):
            acceptance_number = 0

        if lot_size <= 0 or sample_size <= 0 or sample_size > lot_size:
            invalid_sample_size_lot_ids.append(lot_id)
        else:
            if defects_found > acceptance_number:
                rejected_lot_ids.append(lot_id)
            else:
                accepted_lot_ids.append(lot_id)

    lot_acceptance_rate_pct = (
        round((len(accepted_lot_ids) / total_lots) * 100.0, 2)
        if total_lots > 0
        else 0.0
    )
    is_sampling_quality_compliant = bool(
        total_lots > 0
        and not invalid_sample_size_lot_ids
        and not rejected_lot_ids
    )

    return {
        "total_lots": total_lots,
        "accepted_lot_ids": accepted_lot_ids,
        "rejected_lot_ids": rejected_lot_ids,
        "invalid_sample_size_lot_ids": invalid_sample_size_lot_ids,
        "lot_acceptance_rate_pct": lot_acceptance_rate_pct,
        "is_sampling_quality_compliant": is_sampling_quality_compliant,
    }


ProjectCCBService.evaluate_quality_aql_lot_sampling_acceptance = staticmethod(
    evaluate_quality_aql_lot_sampling_acceptance
)


def evaluate_copq_rework_and_scrap_ratio(
    metrics: Mapping[str, Any] | None,
    *,
    max_copq_pct_of_actual: float = 10.0,
) -> dict[str, Any]:
    """Evalúa el Costo de la Mala Calidad (COPQ: retrabajo, desecho, garantías y penalizaciones SLA) frente al costo real del proyecto según PMI PMBOK §8.2 y §8.3."""
    invalid_result: dict[str, Any] = {
        "internal_failure_cost": 0.0,
        "external_failure_cost": 0.0,
        "total_copq": 0.0,
        "copq_pct_of_actual_cost": 0.0,
        "external_failure_share_pct": 0.0,
        "copq_posture": "invalid_inputs",
        "is_copq_controlled": False,
    }
    if not isinstance(metrics, Mapping):
        return invalid_result

    try:
        rework_cost = max(0.0, float(metrics.get("rework_cost", 0.0) or 0.0))
        scrap_cost = max(0.0, float(metrics.get("scrap_cost", 0.0) or 0.0))
        warranty_cost = max(0.0, float(metrics.get("warranty_cost", 0.0) or 0.0))
        sla_penalty_cost = max(
            0.0, float(metrics.get("sla_penalty_cost", 0.0) or 0.0)
        )
        actual_project_cost = float(
            metrics.get("actual_project_cost", 0.0) or 0.0
        )
    except (TypeError, ValueError):
        return invalid_result

    if actual_project_cost <= 0.0:
        return invalid_result

    internal_failure_cost = round(rework_cost + scrap_cost, 2)
    external_failure_cost = round(warranty_cost + sla_penalty_cost, 2)
    total_copq = round(internal_failure_cost + external_failure_cost, 2)
    copq_pct_of_actual_cost = round((total_copq / actual_project_cost) * 100.0, 2)
    external_failure_share_pct = (
        round((external_failure_cost / total_copq) * 100.0, 2)
        if total_copq > 0.0
        else 0.0
    )

    if copq_pct_of_actual_cost > float(max_copq_pct_of_actual):
        copq_posture = "excessive_copq_bleed"
    elif total_copq > 0.0 and external_failure_share_pct > 40.0:
        copq_posture = "external_escape_dominant"
    else:
        copq_posture = "controlled"

    is_copq_controlled = bool(copq_posture == "controlled")

    return {
        "internal_failure_cost": internal_failure_cost,
        "external_failure_cost": external_failure_cost,
        "total_copq": total_copq,
        "copq_pct_of_actual_cost": copq_pct_of_actual_cost,
        "external_failure_share_pct": external_failure_share_pct,
        "copq_posture": copq_posture,
        "is_copq_controlled": is_copq_controlled,
    }


ProjectCCBService.evaluate_copq_rework_and_scrap_ratio = staticmethod(
    evaluate_copq_rework_and_scrap_ratio
)


def audit_ccb_change_request_sla_and_aging_backlog(
    change_requests: Sequence[Mapping[str, Any]] | None,
    *,
    normal_sla_days: float = 14.0,
    urgent_sla_days: float = 3.0,
    max_deferred_ratio_pct: float = 25.0,
) -> dict[str, Any]:
    """PMBOK §4.6 — envejecimiento SLA y backlog diferido de solicitudes del CCB.

    - Abiertas {pending, under_review, submitted, in_review} con edad mayor al
      SLA aplicable (urgent: urgent_sla_days; resto: normal_sla_days) ->
      ``sla_breached_cr_ids``; sin ``impact_assessment_owner`` ->
      ``unassigned_impact_owner_cr_ids``.
    - Diferidas {deferred, on_hold} sin ``re_evaluation_date`` ->
      ``deferred_without_review_date_cr_ids``.
    - ``deferred_ratio_pct`` sobre ``total_evaluated`` con umbral
      ``max_deferred_ratio_pct`` -> ``deferred_backlog_excess``.
    """
    if not isinstance(change_requests, (list, tuple)):
        change_requests = []

    total_evaluated = 0
    open_pending_count = 0
    deferred_count = 0
    sla_breached_cr_ids: list[str] = []
    unassigned_impact_owner_cr_ids: list[str] = []
    deferred_without_review_date_cr_ids: list[str] = []

    OPEN_STATUSES = {"pending", "under_review", "submitted", "in_review"}
    DEFERRED_STATUSES = {"deferred", "on_hold"}
    URGENT_PRIORITIES = {"urgent", "critical", "high", "emergency"}

    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    for item in change_requests:
        if not isinstance(item, Mapping):
            continue
        cr_id = str(item.get("cr_id") or item.get("id") or "").strip()
        if not cr_id:
            continue
        total_evaluated += 1

        status = str(item.get("status") or "pending").strip().lower()
        priority = str(item.get("priority") or "normal").strip().lower()

        if status in OPEN_STATUSES:
            open_pending_count += 1

            sla_days = urgent_sla_days if priority in URGENT_PRIORITIES else normal_sla_days
            age_days = _safe_float(item.get("age_days") or 0.0)
            if age_days > sla_days:
                sla_breached_cr_ids.append(cr_id)

            if not str(item.get("impact_assessment_owner") or "").strip():
                unassigned_impact_owner_cr_ids.append(cr_id)

        elif status in DEFERRED_STATUSES:
            deferred_count += 1

            if not str(item.get("re_evaluation_date") or "").strip():
                deferred_without_review_date_cr_ids.append(cr_id)

    deferred_ratio_pct = (
        round((deferred_count / total_evaluated) * 100.0, 2)
        if total_evaluated > 0
        else 0.0
    )
    deferred_backlog_excess = bool(deferred_ratio_pct > max_deferred_ratio_pct)
    is_ccb_sla_compliant = bool(
        len(sla_breached_cr_ids) == 0
        and len(unassigned_impact_owner_cr_ids) == 0
        and len(deferred_without_review_date_cr_ids) == 0
        and not deferred_backlog_excess
    )

    return {
        "total_evaluated": total_evaluated,
        "open_pending_count": open_pending_count,
        "deferred_count": deferred_count,
        "deferred_ratio_pct": deferred_ratio_pct,
        "sla_breached_cr_ids": sla_breached_cr_ids,
        "unassigned_impact_owner_cr_ids": unassigned_impact_owner_cr_ids,
        "deferred_without_review_date_cr_ids": deferred_without_review_date_cr_ids,
        "deferred_backlog_excess": deferred_backlog_excess,
        "is_ccb_sla_compliant": is_ccb_sla_compliant,
    }


ProjectCCBService.audit_ccb_change_request_sla_and_aging_backlog = staticmethod(
    audit_ccb_change_request_sla_and_aging_backlog
)

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


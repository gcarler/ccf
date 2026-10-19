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
    "evaluate_supplier_ncr_disposition_governance",
    "audit_scope_creep_and_gold_plating_drift",
    "audit_configuration_fca_pca_baseline_verification",
    "audit_dod_defect_escape_and_first_time_right_rate",
    "audit_requirements_traceability_matrix_coverage",
    "audit_emergency_change_fast_track_ratification",
    "audit_contract_change_order_cumulative_escalation",
    "audit_ncr_capa_effectiveness_and_recurrence",
    "audit_configuration_baseline_drift_and_hotfix_governance",
    "audit_quality_gate_peer_review_and_defect_density",
    "audit_retrospective_action_item_closure_and_process_improvement",
    "audit_procurement_warranty_claims_and_holdback_release",
    "audit_change_request_reserve_drawdown_authorization",
    "audit_deliverable_formal_acceptance_and_waiver_expiration",
    "audit_quality_copq_and_rework_scrap_threshold",
    "audit_emergency_change_ratification_and_bypass_governance",
    "audit_quality_capa_root_cause_and_recurrence",
    "audit_configuration_baseline_integrity_and_version_drift",
    "audit_scope_creep_and_gold_plating_effort",
    "audit_quality_spc_control_chart_stability",
    "audit_defect_removal_efficiency_and_uat_readiness",
    "audit_cost_of_quality_conformance_and_failure_ratio",
    "audit_technical_debt_interest_and_remediation_quota",
    "audit_canary_rollout_blast_radius_and_rollback_readiness",
    "audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene",
    "audit_requirements_volatility_churn_and_scope_freeze_breaches",
    "audit_architectural_fitness_functions_and_coupling_drift",
    "audit_api_backward_compatibility_and_contract_versioning",
    "audit_test_pyramid_balance_and_mutation_coverage_gate",
    "audit_supply_chain_slsa_provenance_and_artifact_signing",
    "audit_ecab_emergency_change_retroactive_ratification_and_abuse",
    "audit_release_freeze_blackout_window_and_change_collisions",
    "audit_query_performance_n_plus_one_and_full_scan_gate",
    "audit_feature_flag_stale_toggle_debt_and_kill_switch",
    "audit_canary_rollout_traffic_shift_and_auto_rollback_gate",
    "audit_secret_scanning_pre_receive_and_leak_revocation",
    "audit_iac_terraform_drift_and_state_lock_hygiene",
    "audit_container_image_vulnerability_and_non_root_runtime_gate",
    "audit_dark_launch_shadow_traffic_parity_and_isolation",
    "audit_db_connection_pool_saturation_and_idle_tx_timeout",
    "audit_message_broker_consumer_lag_and_dlq_poison_pill_gate",
    "audit_distributed_cache_stampede_and_hotkey_skew_gate",
    "audit_service_mesh_mtls_strict_and_outlier_ejection_gate",
    "audit_graphql_query_depth_and_n_plus_one_batching_gate",
    "audit_blue_green_cutover_drain_and_db_backward_compatibility",
    "audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate",
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


def evaluate_supplier_ncr_disposition_governance(
    ncr_items: Sequence[Mapping[str, Any]] | None,
    max_concession_ratio_pct: float = 15.0,
) -> dict[str, Any]:
    """Evalúa reportes de no conformidad de proveedores (Supplier NCR), cuarentena y disposición técnica según PMI PMBOK §8.3 y §12.3."""
    if (
        ncr_items is None
        or isinstance(ncr_items, (str, bytes, Mapping))
        or not isinstance(ncr_items, Sequence)
    ):
        items: Sequence[Any] = []
    else:
        items = ncr_items

    total_evaluated = 0
    concession_count = 0
    unquarantined_open_ncr_ids: list[str] = []
    unauthorized_concession_ncr_ids: list[str] = []
    unclaimed_vendor_recovery_ncr_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        ncr_id = str(item.get("ncr_id") or item.get("id") or "").strip()
        if not ncr_id:
            continue

        total_evaluated += 1
        disposition = str(item.get("disposition") or "pending").strip().lower()
        severity = str(item.get("severity") or "minor").strip().lower()

        if disposition == "pending" and item.get("quarantine_isolated") is not True:
            unquarantined_open_ncr_ids.append(ncr_id)

        if disposition in {"use_as_is", "concession"}:
            concession_count += 1
            if (
                severity == "critical"
                or item.get("engineering_authority_approved") is not True
            ):
                unauthorized_concession_ncr_ids.append(ncr_id)

        if (
            disposition in {"scrap", "return_to_vendor"}
            and item.get("cost_recovery_claimed") is not True
        ):
            unclaimed_vendor_recovery_ncr_ids.append(ncr_id)

    concession_ratio_pct = (
        round((concession_count / total_evaluated) * 100.0, 2)
        if total_evaluated > 0
        else 0.0
    )
    excessive_concession_rate = bool(
        concession_ratio_pct > float(max_concession_ratio_pct)
    )
    is_ncr_governance_compliant = bool(
        len(unquarantined_open_ncr_ids) == 0
        and len(unauthorized_concession_ncr_ids) == 0
        and len(unclaimed_vendor_recovery_ncr_ids) == 0
        and not excessive_concession_rate
    )

    recommendations: list[str] = []
    if unquarantined_open_ncr_ids:
        recommendations.append(
            "Aislar inmediatamente en cuarentena los lotes con NCR abiertas: "
            + ", ".join(unquarantined_open_ncr_ids)
            + "."
        )
    if unauthorized_concession_ncr_ids:
        recommendations.append(
            "Rechazar concesiones sobre NCR críticas o sin aprobación de autoridad de ingeniería: "
            + ", ".join(unauthorized_concession_ncr_ids)
            + "."
        )
    if unclaimed_vendor_recovery_ncr_ids:
        recommendations.append(
            "Gestionar el reclamo de recuperación de costos o nota de crédito ante el proveedor: "
            + ", ".join(unclaimed_vendor_recovery_ncr_ids)
            + "."
        )
    if excessive_concession_rate:
        recommendations.append(
            f"Reducir la tasa de aceptación por concesión ({concession_ratio_pct}%) por debajo del umbral permitido ({max_concession_ratio_pct}%)."
        )

    if unquarantined_open_ncr_ids or unauthorized_concession_ncr_ids:
        status = "critical"
    elif unclaimed_vendor_recovery_ncr_ids or excessive_concession_rate:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_evaluated": total_evaluated,
        "concession_count": concession_count,
        "concession_ratio_pct": concession_ratio_pct,
        "unquarantined_open_ncr_ids": unquarantined_open_ncr_ids,
        "unauthorized_concession_ncr_ids": unauthorized_concession_ncr_ids,
        "unclaimed_vendor_recovery_ncr_ids": unclaimed_vendor_recovery_ncr_ids,
        "excessive_concession_rate": excessive_concession_rate,
        "is_ncr_governance_compliant": is_ncr_governance_compliant,
        "status": status,
        "recommendations": recommendations,
    }


ProjectCCBService.evaluate_supplier_ncr_disposition_governance = staticmethod(
    evaluate_supplier_ncr_disposition_governance
)



def audit_scope_creep_and_gold_plating_drift(
    work_packages: Sequence[Mapping[str, Any]] | None,
    *,
    max_unapproved_effort_drift_pct: float = 5.0,
) -> dict[str, Any]:
    """Audita corrupción del alcance (Scope Creep), adición no autorizada de funcionalidades (Gold-Plating) y expansión silenciosa de esfuerzo sin CR en paquetes de trabajo WBS según PMI PMBOK §5.6 y §4.6."""
    total_evaluated = 0
    unapproved_scope_addition_wp_ids: list[str] = []
    gold_plating_wp_ids: list[str] = []
    silent_effort_expansion_wp_ids: list[str] = []

    max_drift = float(max_unapproved_effort_drift_pct)
    packages: Sequence[Any] = work_packages or []
    if not isinstance(packages, Sequence) or isinstance(
        packages, (str, bytes, Mapping)
    ):
        packages = []

    for item in packages:
        if not isinstance(item, Mapping):
            continue
        wp_id = str(item.get("wp_id") or item.get("id") or "").strip()
        if not wp_id:
            continue

        total_evaluated += 1
        has_approved_cr = bool(str(item.get("approved_cr_id") or "").strip())
        in_approved_baseline = bool(item.get("in_approved_wbs_baseline") is True)
        extra_features_count = int(item.get("extra_features_added_count") or 0)

        if not in_approved_baseline and not has_approved_cr:
            unapproved_scope_addition_wp_ids.append(wp_id)

        if extra_features_count > 0 and not has_approved_cr:
            gold_plating_wp_ids.append(wp_id)

        if not has_approved_cr:
            try:
                baseline_hours = float(item.get("baseline_hours") or 0.0)
            except (TypeError, ValueError):
                baseline_hours = 0.0
            if baseline_hours > 0.0:
                try:
                    actual_or_forecast = float(
                        item.get("actual_or_forecast_hours") or 0.0
                    )
                except (TypeError, ValueError):
                    actual_or_forecast = 0.0
                drift_pct = (
                    (actual_or_forecast - baseline_hours) / baseline_hours
                ) * 100.0
                if drift_pct > max_drift:
                    silent_effort_expansion_wp_ids.append(wp_id)

    is_scope_baseline_controlled = bool(
        len(unapproved_scope_addition_wp_ids) == 0
        and len(gold_plating_wp_ids) == 0
        and len(silent_effort_expansion_wp_ids) == 0
    )

    return {
        "total_evaluated": total_evaluated,
        "unapproved_scope_addition_wp_ids": unapproved_scope_addition_wp_ids,
        "gold_plating_wp_ids": gold_plating_wp_ids,
        "silent_effort_expansion_wp_ids": silent_effort_expansion_wp_ids,
        "is_scope_baseline_controlled": is_scope_baseline_controlled,
    }


ProjectCCBService.audit_scope_creep_and_gold_plating_drift = staticmethod(
    audit_scope_creep_and_gold_plating_drift
)


def audit_requirements_traceability_matrix_coverage(
    rtm_entries: object,
) -> dict[str, object]:
    """Audita cobertura bidireccional de la Matriz de Trazabilidad de Requisitos (RTM: objetivo de negocio -> entregable WBS -> casos de prueba y automatización de regresión) según PMI PMBOK §5.2 y §8.2."""
    total_evaluated = 0
    orphan_forward_traceability_req_ids: list[str] = []
    untested_backward_traceability_req_ids: list[str] = []
    unautomated_critical_req_ids: list[str] = []

    critical_tiers = {"critical", "high", "must", "p0"}

    if isinstance(rtm_entries, Sequence) and not isinstance(
        rtm_entries, (str, bytes, bytearray)
    ):
        for item in rtm_entries:
            if not isinstance(item, Mapping):
                continue
            req_id = str(
                item.get("requirement_id") or item.get("id") or ""
            ).strip()
            if not req_id:
                continue

            total_evaluated += 1
            business_objective_ref = str(
                item.get("business_objective_ref") or ""
            ).strip()
            wbs_deliverable_ref = str(
                item.get("wbs_deliverable_ref") or ""
            ).strip()

            raw_tests = item.get("verification_test_case_ids")
            if isinstance(raw_tests, Sequence) and not isinstance(
                raw_tests, (str, bytes, bytearray)
            ):
                valid_test_count = sum(
                    1
                    for tc in raw_tests
                    if isinstance(tc, str) and bool(tc.strip())
                )
            else:
                valid_test_count = 0

            priority_tier = (
                str(item.get("priority_tier") or "medium").strip().lower()
            )
            regression_suite_automated = bool(
                item.get("regression_suite_automated", False)
            )

            if not business_objective_ref or not wbs_deliverable_ref:
                orphan_forward_traceability_req_ids.append(req_id)

            if valid_test_count == 0:
                untested_backward_traceability_req_ids.append(req_id)

            if (
                priority_tier in critical_tiers
                and not regression_suite_automated
            ):
                unautomated_critical_req_ids.append(req_id)

    return {
        "total_evaluated": total_evaluated,
        "orphan_forward_traceability_req_ids": orphan_forward_traceability_req_ids,
        "untested_backward_traceability_req_ids": untested_backward_traceability_req_ids,
        "unautomated_critical_req_ids": unautomated_critical_req_ids,
        "is_rtm_bidirectional_complete": (
            len(orphan_forward_traceability_req_ids) == 0
            and len(untested_backward_traceability_req_ids) == 0
            and len(unautomated_critical_req_ids) == 0
        ),
    }


ProjectCCBService.audit_requirements_traceability_matrix_coverage = staticmethod(
    audit_requirements_traceability_matrix_coverage
)


def audit_configuration_fca_pca_baseline_verification(
    configuration_audits: object,
) -> dict[str, object]:
    """Audita verificación de líneas base funcional (FCA) y física (PCA) de Configuration Items según PMI PMBOK §4.6 y §8.3."""
    total_evaluated = 0
    fca_failed_ci_ids: list[str] = []
    pca_discrepancy_ci_ids: list[str] = []
    mutable_version_tag_ci_ids: list[str] = []

    audits: Sequence[Any] = (
        configuration_audits
        if isinstance(configuration_audits, Sequence)
        and not isinstance(configuration_audits, (str, bytes, bytearray))
        else []
    )

    for item in audits:
        if not isinstance(item, Mapping):
            continue
        ci_id = str(item.get("ci_id") or item.get("id") or "").strip()
        if not ci_id:
            continue

        total_evaluated += 1

        fca_functional_test_passed = bool(
            item.get("fca_functional_test_passed", False)
        )
        pca_as_built_matches_as_designed = bool(
            item.get("pca_as_built_matches_as_designed", False)
        )
        try:
            unapproved_baseline_deviations_count = int(
                item.get("unapproved_baseline_deviations_count", 0) or 0
            )
        except (TypeError, ValueError):
            unapproved_baseline_deviations_count = 0
        version_tag_immutable = bool(item.get("version_tag_immutable", False))

        if not fca_functional_test_passed:
            fca_failed_ci_ids.append(ci_id)

        if (
            not pca_as_built_matches_as_designed
            or unapproved_baseline_deviations_count > 0
        ):
            pca_discrepancy_ci_ids.append(ci_id)

        if not version_tag_immutable:
            mutable_version_tag_ci_ids.append(ci_id)

    is_fca_pca_audit_compliant = bool(
        len(fca_failed_ci_ids) == 0
        and len(pca_discrepancy_ci_ids) == 0
        and len(mutable_version_tag_ci_ids) == 0
    )

    return {
        "total_evaluated": total_evaluated,
        "fca_failed_ci_ids": fca_failed_ci_ids,
        "pca_discrepancy_ci_ids": pca_discrepancy_ci_ids,
        "mutable_version_tag_ci_ids": mutable_version_tag_ci_ids,
        "is_fca_pca_audit_compliant": is_fca_pca_audit_compliant,
    }


ProjectCCBService.audit_configuration_fca_pca_baseline_verification = staticmethod(
    audit_configuration_fca_pca_baseline_verification
)


def audit_emergency_change_fast_track_ratification(
    change_requests: object,
    *,
    max_emergency_ratio_pct: float = 15.0,
    ratification_sla_hours: float = 48.0,
) -> dict[str, object]:
    """Audita solicitudes de cambio de emergencia (Fast-Track), severidad de incidente (Sev1/Sev2), aprobador delegado, plan de rollback y SLA de ratificación post-facto CCB según PMI PMBOK §4.6 y §8.3."""
    total_change_requests = 0
    emergency_change_count = 0
    unjustified_emergency_severity_cr_ids: list[str] = []
    missing_safeguard_or_approver_cr_ids: list[str] = []
    overdue_post_facto_ratification_cr_ids: list[str] = []

    sla_hours = float(ratification_sla_hours)

    if isinstance(change_requests, Sequence) and not isinstance(
        change_requests, (str, bytes, bytearray)
    ):
        for item in change_requests:
            if not isinstance(item, Mapping):
                continue
            cr_id = str(item.get("cr_id") or item.get("id") or "").strip()
            if not cr_id:
                continue

            total_change_requests += 1
            if not bool(item.get("is_emergency", False)):
                continue

            emergency_change_count += 1
            incident_severity = (
                str(item.get("incident_severity") or "").strip().lower()
            )
            delegated_approver_id = str(
                item.get("delegated_approver_id") or ""
            ).strip()
            rollback_plan_documented = bool(
                item.get("rollback_plan_documented", False)
            )
            try:
                hours_since_execution = float(
                    item.get("hours_since_execution", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                hours_since_execution = 0.0
            post_facto_ccb_ratified = bool(
                item.get("post_facto_ccb_ratified", False)
            )

            if incident_severity not in {"sev1", "sev2"}:
                unjustified_emergency_severity_cr_ids.append(cr_id)

            if not delegated_approver_id or not rollback_plan_documented:
                missing_safeguard_or_approver_cr_ids.append(cr_id)

            if (
                not post_facto_ccb_ratified
                and hours_since_execution > sla_hours
            ):
                overdue_post_facto_ratification_cr_ids.append(cr_id)

    emergency_ratio_pct = (
        round((emergency_change_count / total_change_requests) * 100.0, 2)
        if total_change_requests > 0
        else 0.0
    )
    exceeds_emergency_ratio_cap = bool(
        emergency_ratio_pct > float(max_emergency_ratio_pct)
    )

    return {
        "total_change_requests": total_change_requests,
        "emergency_change_count": emergency_change_count,
        "emergency_ratio_pct": emergency_ratio_pct,
        "exceeds_emergency_ratio_cap": exceeds_emergency_ratio_cap,
        "unjustified_emergency_severity_cr_ids": unjustified_emergency_severity_cr_ids,
        "missing_safeguard_or_approver_cr_ids": missing_safeguard_or_approver_cr_ids,
        "overdue_post_facto_ratification_cr_ids": overdue_post_facto_ratification_cr_ids,
        "is_emergency_governance_compliant": (
            len(unjustified_emergency_severity_cr_ids) == 0
            and len(missing_safeguard_or_approver_cr_ids) == 0
            and len(overdue_post_facto_ratification_cr_ids) == 0
            and not exceeds_emergency_ratio_cap
        ),
    }


ProjectCCBService.audit_emergency_change_fast_track_ratification = staticmethod(
    audit_emergency_change_fast_track_ratification
)



def audit_dod_defect_escape_and_first_time_right_rate(
    deliverable_inspections: list[dict[str, object]],
    *,
    max_defect_escape_ratio_pct: float = 10.0,
    min_first_time_right_pct: float = 80.0,
) -> dict[str, object]:
    """Audita Defect Escape Ratio y First-Time-Right pass rate del Control de Calidad (DoD) según PMI PMBOK §8.3."""
    total_deliverables = 0
    first_time_right_count = 0
    invalid_metric_deliverable_ids: list[str] = []
    high_defect_escape_deliverable_ids: list[str] = []
    unlinked_capa_escaped_deliverable_ids: list[str] = []
    regression_gap_deliverable_ids: list[str] = []

    max_escape = float(max_defect_escape_ratio_pct)
    min_ftr = float(min_first_time_right_pct)
    items: Sequence[Any] = (
        deliverable_inspections
        if isinstance(deliverable_inspections, Sequence)
        and not isinstance(deliverable_inspections, (str, bytes, bytearray, Mapping))
        else []
    )

    def _coerce(value: Any, default: float = 0.0) -> float:
        try:
            return float(value if value is not None else default)
        except (TypeError, ValueError):
            return default

    for item in items:
        if not isinstance(item, Mapping):
            continue
        deliverable_id = str(item.get("deliverable_id") or item.get("id") or "").strip()
        if not deliverable_id:
            continue

        try:
            pre_release_defects_found = int(item.get("pre_release_defects_found", 0) or 0)
        except (TypeError, ValueError):
            pre_release_defects_found = 0
        try:
            post_release_escaped_defects = int(
                item.get("post_release_escaped_defects", 0) or 0
            )
        except (TypeError, ValueError):
            post_release_escaped_defects = 0
        raw_cycles = item.get("inspection_cycles_count", 1)
        try:
            inspection_cycles_count = int(raw_cycles)
        except (TypeError, ValueError):
            inspection_cycles_count = 1
        automated_regression_coverage_pct = _coerce(
            item.get("automated_regression_coverage_pct"), 0.0
        )
        root_cause_capa_linked = bool(item.get("root_cause_capa_linked", False))

        if (
            pre_release_defects_found < 0
            or post_release_escaped_defects < 0
            or inspection_cycles_count < 1
        ):
            invalid_metric_deliverable_ids.append(deliverable_id)
            continue

        total_deliverables += 1

        total_defects = pre_release_defects_found + post_release_escaped_defects
        escape_ratio_pct = (
            round((post_release_escaped_defects / total_defects) * 100.0, 2)
            if total_defects > 0
            else 0.0
        )
        if escape_ratio_pct > max_escape:
            high_defect_escape_deliverable_ids.append(deliverable_id)

        if post_release_escaped_defects > 0 and not root_cause_capa_linked:
            unlinked_capa_escaped_deliverable_ids.append(deliverable_id)

        if (
            post_release_escaped_defects > 0
            and automated_regression_coverage_pct < 70.0
        ):
            regression_gap_deliverable_ids.append(deliverable_id)

        if inspection_cycles_count == 1 and post_release_escaped_defects == 0:
            first_time_right_count += 1

    first_time_right_pct = (
        round((first_time_right_count / total_deliverables) * 100.0, 2)
        if total_deliverables > 0
        else 100.0
    )
    below_first_time_right_threshold = bool(
        total_deliverables > 0 and first_time_right_pct < min_ftr
    )

    is_dod_quality_gate_compliant = bool(
        len(invalid_metric_deliverable_ids) == 0
        and len(high_defect_escape_deliverable_ids) == 0
        and len(unlinked_capa_escaped_deliverable_ids) == 0
        and len(regression_gap_deliverable_ids) == 0
        and not below_first_time_right_threshold
    )

    return {
        "total_deliverables": total_deliverables,
        "first_time_right_count": first_time_right_count,
        "first_time_right_pct": first_time_right_pct,
        "below_first_time_right_threshold": below_first_time_right_threshold,
        "invalid_metric_deliverable_ids": invalid_metric_deliverable_ids,
        "high_defect_escape_deliverable_ids": high_defect_escape_deliverable_ids,
        "unlinked_capa_escaped_deliverable_ids": unlinked_capa_escaped_deliverable_ids,
        "regression_gap_deliverable_ids": regression_gap_deliverable_ids,
        "is_dod_quality_gate_compliant": is_dod_quality_gate_compliant,
    }


ProjectCCBService.audit_dod_defect_escape_and_first_time_right_rate = staticmethod(
    audit_dod_defect_escape_and_first_time_right_rate
)


def audit_contract_change_order_cumulative_escalation(
    contract_change_ledgers: list[dict[str, object]],
    *,
    max_cumulative_variation_pct: float = 20.0,
    max_single_order_variation_pct: float = 10.0,
) -> dict[str, object]:
    """Audita el escalamiento acumulado y el fraccionamiento de órdenes de cambio contractuales (order-splitting) frente a umbrales individuales y acumulados, exigiendo adenda legal firmada y ratificación ejecutiva según PMI PMBOK §4.6 y §12.2."""
    try:
        max_cum_pct = float(max_cumulative_variation_pct)
    except (TypeError, ValueError):
        max_cum_pct = 20.0

    try:
        max_single_pct = float(max_single_order_variation_pct)
    except (TypeError, ValueError):
        max_single_pct = 10.0

    total_contracts = 0
    invalid_base_contract_ids: list[str] = []
    unsigned_legal_amendment_contract_ids: list[str] = []
    unratified_threshold_breach_contract_ids: list[str] = []

    if isinstance(contract_change_ledgers, Sequence) and not isinstance(
        contract_change_ledgers, (str, bytes, bytearray)
    ):
        for item in contract_change_ledgers:
            if not isinstance(item, Mapping):
                continue
            contract_id = str(
                item.get("contract_id") or item.get("id") or ""
            ).strip()
            if not contract_id:
                continue

            total_contracts += 1
            raw_base = item.get("original_contract_value")
            if raw_base is None or isinstance(raw_base, bool):
                base_val = -1.0
            else:
                try:
                    base_val = float(raw_base)
                except (TypeError, ValueError):
                    base_val = -1.0

            if base_val <= 0.0:
                invalid_base_contract_ids.append(contract_id)
                continue

            raw_orders = item.get("change_orders")
            orders = (
                [co for co in raw_orders if isinstance(co, Mapping)]
                if isinstance(raw_orders, Sequence)
                and not isinstance(raw_orders, (str, bytes, bytearray))
                else []
            )

            deltas: list[float] = []
            has_unsigned_legal = False
            has_unratified_order = False

            for co in orders:
                raw_delta = co.get("cost_delta", 0.0)
                if raw_delta is None or isinstance(raw_delta, bool):
                    delta = 0.0
                else:
                    try:
                        delta = float(raw_delta)
                    except (TypeError, ValueError):
                        delta = 0.0
                deltas.append(delta)

                if delta != 0.0 and not bool(
                    co.get("legal_amendment_signed", False)
                ):
                    has_unsigned_legal = True

                if not bool(co.get("executive_board_ratified", False)):
                    has_unratified_order = True

            net_cost_delta = sum(deltas)
            abs_cost_delta_max = max((abs(d) for d in deltas), default=0.0)
            cumulative_variation_pct = round(
                (abs(net_cost_delta) / base_val) * 100.0, 2
            )
            max_single_variation_pct = round(
                (abs_cost_delta_max / base_val) * 100.0, 2
            )

            if has_unsigned_legal:
                unsigned_legal_amendment_contract_ids.append(contract_id)

            if (
                cumulative_variation_pct > max_cum_pct
                or max_single_variation_pct > max_single_pct
            ) and has_unratified_order:
                unratified_threshold_breach_contract_ids.append(contract_id)

    return {
        "total_contracts": total_contracts,
        "invalid_base_contract_ids": invalid_base_contract_ids,
        "unsigned_legal_amendment_contract_ids": unsigned_legal_amendment_contract_ids,
        "unratified_threshold_breach_contract_ids": unratified_threshold_breach_contract_ids,
        "is_change_order_escalation_compliant": (
            len(invalid_base_contract_ids) == 0
            and len(unsigned_legal_amendment_contract_ids) == 0
            and len(unratified_threshold_breach_contract_ids) == 0
        ),
    }


ProjectCCBService.audit_contract_change_order_cumulative_escalation = staticmethod(
    audit_contract_change_order_cumulative_escalation
)


def audit_ncr_capa_effectiveness_and_recurrence(
    ncr_records: list[dict[str, object]],
    *,
    max_verification_lag_days: int = 14,
) -> dict[str, object]:
    """PMBOK §8.2 / §8.3 — auditoría de efectividad CAPA, verificación QA y recurrencia en NCRs."""
    if not isinstance(ncr_records, Sequence) or isinstance(ncr_records, (str, bytes)):
        return {
            "total_ncrs": 0,
            "invalid_ncr_metadata_ids": [],
            "missing_rca_major_ncr_ids": [],
            "overdue_capa_verification_ncr_ids": [],
            "unverified_closure_ncr_ids": [],
            "ineffective_capa_recurrent_ncr_ids": [],
            "is_ncr_capa_governance_compliant": True,
        }

    try:
        max_lag = float(max_verification_lag_days)
    except (TypeError, ValueError):
        max_lag = 14.0

    valid_severities = {"critical", "major", "minor"}
    valid_statuses = {
        "open",
        "capa_in_progress",
        "pending_verification",
        "verified_closed",
    }

    total_ncrs = 0
    invalid_ncr_metadata_ids: list[str] = []
    missing_rca_major_ncr_ids: list[str] = []
    overdue_capa_verification_ncr_ids: list[str] = []
    unverified_closure_ncr_ids: list[str] = []
    ineffective_capa_recurrent_ncr_ids: list[str] = []

    for item in ncr_records:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("ncr_id")
        if raw_id is None:
            continue
        ncr_id = str(raw_id).strip()
        if not ncr_id:
            continue

        total_ncrs += 1

        sev = str(item.get("severity") or "").strip().lower()
        status = str(item.get("status") or "").strip().lower()

        try:
            days_pending = float(item.get("days_in_pending_verification", 0.0))
            recurrence = int(item.get("recurrence_count_after_closure", 0))
        except (TypeError, ValueError):
            invalid_ncr_metadata_ids.append(ncr_id)
            continue

        if (
            sev not in valid_severities
            or status not in valid_statuses
            or days_pending < 0.0
            or recurrence < 0
        ):
            invalid_ncr_metadata_ids.append(ncr_id)
            continue

        rca_documented = bool(item.get("root_cause_method_documented", False))
        raw_verifier = item.get("independent_qa_verifier_id")
        verifier_id = str(raw_verifier).strip() if raw_verifier is not None else ""

        if sev in {"critical", "major"} and status != "open" and not rca_documented:
            missing_rca_major_ncr_ids.append(ncr_id)

        if status == "pending_verification" and days_pending > max_lag:
            overdue_capa_verification_ncr_ids.append(ncr_id)

        if status == "verified_closed" and not verifier_id:
            unverified_closure_ncr_ids.append(ncr_id)

        if recurrence > 0:
            ineffective_capa_recurrent_ncr_ids.append(ncr_id)

    return {
        "total_ncrs": total_ncrs,
        "invalid_ncr_metadata_ids": invalid_ncr_metadata_ids,
        "missing_rca_major_ncr_ids": missing_rca_major_ncr_ids,
        "overdue_capa_verification_ncr_ids": overdue_capa_verification_ncr_ids,
        "unverified_closure_ncr_ids": unverified_closure_ncr_ids,
        "ineffective_capa_recurrent_ncr_ids": ineffective_capa_recurrent_ncr_ids,
        "is_ncr_capa_governance_compliant": (
            len(invalid_ncr_metadata_ids) == 0
            and len(missing_rca_major_ncr_ids) == 0
            and len(overdue_capa_verification_ncr_ids) == 0
            and len(unverified_closure_ncr_ids) == 0
            and len(ineffective_capa_recurrent_ncr_ids) == 0
        ),
    }


ProjectCCBService.audit_ncr_capa_effectiveness_and_recurrence = staticmethod(
    audit_ncr_capa_effectiveness_and_recurrence
)


def audit_configuration_baseline_drift_and_hotfix_governance(
    configuration_items: list[dict[str, Any]],
    *,
    max_unverified_audit_age_days: int = 30,
) -> dict[str, Any]:
    """PMBOK §4.6 / §5.6 — auditoría de deriva de línea base de configuración y hotfixes no autorizados."""
    if not isinstance(configuration_items, Sequence) or isinstance(
        configuration_items, (str, bytes)
    ):
        return {
            "total_configuration_items": 0,
            "compliant_ci_count": 0,
            "unauthorized_version_drift_count": 0,
            "unauthorized_hotfix_count": 0,
            "failed_fca_pca_count": 0,
            "stale_audit_ci_count": 0,
            "configuration_integrity_pct": 100.0,
            "configuration_governance_status": "HEALTHY",
            "discrepancies": [],
        }

    try:
        max_age = int(max_unverified_audit_age_days)
    except (TypeError, ValueError):
        max_age = 30

    total_configuration_items = 0
    compliant_ci_count = 0
    unauthorized_version_drift_count = 0
    unauthorized_hotfix_count = 0
    failed_fca_pca_count = 0
    stale_audit_ci_count = 0
    discrepancies: list[dict[str, Any]] = []

    for item in configuration_items:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("ci_id")
        if raw_id is None:
            continue
        ci_id = str(raw_id).strip()
        if not ci_id:
            continue

        total_configuration_items += 1

        baseline_ver = str(item.get("baseline_version") or "").strip()
        deployed_ver = str(item.get("deployed_version") or "").strip()
        auth_cr = str(item.get("authorized_change_request_id") or "").strip()
        is_hotfix = bool(item.get("is_production_hotfix", False))
        pca_passed = bool(item.get("physical_configuration_audit_passed", False))
        fca_passed = bool(item.get("functional_configuration_audit_passed", False))
        days_since_audit = int(
            item.get("days_since_last_configuration_audit", 0) or 0
        )

        unauthorized_version_drift = (baseline_ver != deployed_ver) and not auth_cr
        unauthorized_hotfix = is_hotfix and not auth_cr
        failed_fca_pca = (not pca_passed) or (not fca_passed)
        stale_audit = days_since_audit > max_age

        issues: list[str] = []
        if unauthorized_version_drift:
            unauthorized_version_drift_count += 1
            issues.append("unauthorized_version_drift")
        if unauthorized_hotfix:
            unauthorized_hotfix_count += 1
            issues.append("unauthorized_production_hotfix")
        if failed_fca_pca:
            failed_fca_pca_count += 1
            issues.append("failed_fca_or_pca_audit")
        if stale_audit:
            stale_audit_ci_count += 1
            issues.append("stale_configuration_audit")

        if not issues:
            compliant_ci_count += 1
        else:
            discrepancies.append({"ci_id": ci_id, "issues": issues})

    if total_configuration_items == 0:
        configuration_integrity_pct = 100.0
    else:
        configuration_integrity_pct = round(
            (compliant_ci_count / total_configuration_items) * 100.0, 2
        )

    if (
        unauthorized_version_drift_count == 0
        and unauthorized_hotfix_count == 0
        and failed_fca_pca_count == 0
        and stale_audit_ci_count == 0
    ):
        status = "HEALTHY"
    elif (
        unauthorized_version_drift_count > 0
        or unauthorized_hotfix_count > 0
        or failed_fca_pca_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_configuration_items": total_configuration_items,
        "compliant_ci_count": compliant_ci_count,
        "unauthorized_version_drift_count": unauthorized_version_drift_count,
        "unauthorized_hotfix_count": unauthorized_hotfix_count,
        "failed_fca_pca_count": failed_fca_pca_count,
        "stale_audit_ci_count": stale_audit_ci_count,
        "configuration_integrity_pct": configuration_integrity_pct,
        "configuration_governance_status": status,
        "discrepancies": discrepancies,
    }


ProjectCCBService.audit_configuration_baseline_drift_and_hotfix_governance = staticmethod(
    audit_configuration_baseline_drift_and_hotfix_governance
)


def audit_quality_gate_peer_review_and_defect_density(
    deliverable_reviews: list[dict[str, Any]],
    *,
    min_review_coverage_pct: float = 100.0,
    max_defect_density_per_kloc: float = 2.5,
) -> dict[str, Any]:
    """PMBOK §8.2 / §8.3 — auditoría de revisión por pares en compuertas de calidad y densidad de defectos."""
    if not isinstance(deliverable_reviews, Sequence) or isinstance(
        deliverable_reviews, (str, bytes)
    ):
        return {
            "total_deliverables": 0,
            "compliant_deliverables_count": 0,
            "insufficient_review_coverage_count": 0,
            "open_critical_or_unverified_rework_count": 0,
            "excessive_defect_density_count": 0,
            "peer_review_governance_status": "HEALTHY",
            "violations": [],
        }

    try:
        min_cov = float(min_review_coverage_pct)
    except (TypeError, ValueError):
        min_cov = 100.0

    try:
        max_density = float(max_defect_density_per_kloc)
    except (TypeError, ValueError):
        max_density = 2.5

    total_deliverables = 0
    compliant_deliverables_count = 0
    insufficient_review_coverage_count = 0
    open_critical_or_unverified_rework_count = 0
    excessive_defect_density_count = 0
    violations: list[dict[str, Any]] = []

    for item in deliverable_reviews:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("deliverable_id")
        if raw_id is None:
            continue
        deliverable_id = str(raw_id).strip()
        if not deliverable_id:
            continue

        total_deliverables += 1

        size_units = float(item.get("size_kloc_or_units", 0.0) or 0.0)
        review_cov = float(item.get("review_coverage_pct", 0.0) or 0.0)
        indep_reviewer = bool(item.get("independent_reviewer_assigned", False))
        crit_major_open = int(item.get("critical_major_defects_open", 0) or 0)
        total_defects = int(item.get("total_defects_found", 0) or 0)
        rework_verified = bool(item.get("rework_verified", False))

        insufficient_review = (review_cov < min_cov) or (not indep_reviewer)
        open_critical_or_unverified = (crit_major_open > 0) or (
            total_defects > 0 and not rework_verified
        )

        if size_units > 0.0:
            defect_density = round(float(total_defects) / size_units, 2)
        else:
            defect_density = 0.0

        excessive_defect_density = defect_density > max_density

        reasons: list[str] = []
        if insufficient_review:
            insufficient_review_coverage_count += 1
            reasons.append("insufficient_peer_review_or_missing_independent_reviewer")
        if open_critical_or_unverified:
            open_critical_or_unverified_rework_count += 1
            reasons.append("open_critical_defects_or_unverified_rework")
        if excessive_defect_density:
            excessive_defect_density_count += 1
            reasons.append("excessive_defect_density")

        if not reasons:
            compliant_deliverables_count += 1
        else:
            violations.append(
                {
                    "deliverable_id": deliverable_id,
                    "defect_density": defect_density,
                    "reasons": reasons,
                }
            )

    if (
        insufficient_review_coverage_count == 0
        and open_critical_or_unverified_rework_count == 0
        and excessive_defect_density_count == 0
    ):
        status = "HEALTHY"
    elif (
        open_critical_or_unverified_rework_count > 0
        or insufficient_review_coverage_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_deliverables": total_deliverables,
        "compliant_deliverables_count": compliant_deliverables_count,
        "insufficient_review_coverage_count": insufficient_review_coverage_count,
        "open_critical_or_unverified_rework_count": open_critical_or_unverified_rework_count,
        "excessive_defect_density_count": excessive_defect_density_count,
        "peer_review_governance_status": status,
        "violations": violations,
    }


ProjectCCBService.audit_quality_gate_peer_review_and_defect_density = staticmethod(
    audit_quality_gate_peer_review_and_defect_density
)





def audit_retrospective_action_item_closure_and_process_improvement(
    retrospective_actions: list[dict],
    *,
    max_action_carryover_sprints: int = 2,
    min_measurable_outcome_pct: float = 80.0,
) -> dict:
    """Audita cierre de acciones de retrospectiva y mejora continua (PMBOK §8.2 y Agile Practice Guide).

    Cada acción aporta action_id, status, sprints_carried_over,
    owner_assigned, measurable_success_criterion_defined y
    verified_effectiveness:
    - stalled_carryover: acción no CLOSED arrastrada por más sprints
      que el umbral.
    - unowned_or_unmeasurable: sin responsable o sin criterio medible
      de éxito.
    - unverified_closed: acción CLOSED sin verificación empírica de
      efectividad.
    - measurable_outcome_coverage_pct: % de acciones con criterio
      medible (2 dec, 100.0 si vacío).
    - continuous_improvement_status: 'HEALTHY' sin hallazgos y
      cobertura >= min; 'CRITICAL' con stalled carry-over o cierres sin
      verificación; 'AT_RISK' en otro caso; violations con
      {action_id, reasons}.
    """
    if not isinstance(retrospective_actions, list):
        retrospective_actions = []
    actions = [a for a in retrospective_actions if isinstance(a, dict)]

    total_actions = len(actions)
    count_measureable = sum(
        1 for a in actions if bool(a.get("measurable_success_criterion_defined", False))
    )
    measurable_outcome_coverage_pct = (
        round(count_measureable / total_actions * 100.0, 2) if total_actions > 0 else 100.0
    )

    compliant_actions_count = 0
    stalled_carryover_actions_count = 0
    unowned_or_unmeasurable_actions_count = 0
    unverified_closed_actions_count = 0
    violations: list[dict] = []

    for idx, action in enumerate(actions, start=1):
        action_id = str(action.get("action_id", f"ACTION-{idx}"))
        reasons: list[str] = []
        has_stalled = False
        has_unowned = False
        has_unverified = False

        status = str(action.get("status") or "").strip().upper()
        raw_sprints = action.get("sprints_carried_over")
        try:
            sprints = int(raw_sprints if raw_sprints is not None else 0)
        except (TypeError, ValueError):
            sprints = 0
        owner_assigned = bool(action.get("owner_assigned", False))
        measurable = bool(action.get("measurable_success_criterion_defined", False))
        verified = bool(action.get("verified_effectiveness", False))

        if status != "CLOSED" and sprints > int(max_action_carryover_sprints):
            has_stalled = True
            reasons.append(f"STALLED_CARRYOVER ({sprints}>{max_action_carryover_sprints}, status {status or 'UNKNOWN'})")
        if (not owner_assigned) or (not measurable):
            has_unowned = True
            if not owner_assigned:
                reasons.append("OWNER_UNASSIGNED")
            if not measurable:
                reasons.append("SUCCESS_CRITERION_NOT_MEASURABLE")
        if status == "CLOSED" and not verified:
            has_unverified = True
            reasons.append("CLOSED_WITHOUT_VERIFIED_EFFECTIVENESS")

        if has_stalled:
            stalled_carryover_actions_count += 1
        if has_unowned:
            unowned_or_unmeasurable_actions_count += 1
        if has_unverified:
            unverified_closed_actions_count += 1
        if not (has_stalled or has_unowned or has_unverified):
            compliant_actions_count += 1
        if reasons:
            violations.append({"action_id": action_id, "reasons": reasons})

    continuous_improvement_status = (
        "CRITICAL"
        if stalled_carryover_actions_count > 0 or unverified_closed_actions_count > 0
        else (
            "AT_RISK"
            if unowned_or_unmeasurable_actions_count > 0
            or measurable_outcome_coverage_pct < float(min_measurable_outcome_pct)
            else "HEALTHY"
        )
    )

    return {
        "total_actions": total_actions,
        "compliant_actions_count": compliant_actions_count,
        "stalled_carryover_actions_count": stalled_carryover_actions_count,
        "unowned_or_unmeasurable_actions_count": unowned_or_unmeasurable_actions_count,
        "unverified_closed_actions_count": unverified_closed_actions_count,
        "measurable_outcome_coverage_pct": measurable_outcome_coverage_pct,
        "continuous_improvement_status": continuous_improvement_status,
        "violations": violations,
    }


ProjectCCBService.audit_retrospective_action_item_closure_and_process_improvement = staticmethod(
    audit_retrospective_action_item_closure_and_process_improvement
)


def audit_procurement_warranty_claims_and_holdback_release(
    contracts_warranty: list[dict[str, Any]],
    *,
    max_warranty_response_days: int = 5,
) -> dict[str, Any]:
    """Audita SLA de atencion de reclamos de garantia y liberacion de retenciones (holdback) segun PMI PMBOK §12.3 y §4.7."""
    if not isinstance(contracts_warranty, list):
        contracts_warranty = []

    max_resp_days = int(max_warranty_response_days)
    total_contracts_evaluated = 0
    compliant_contracts_count = 0
    premature_holdback_releases_count = 0
    warranty_sla_breached_contracts_count = 0
    unsecured_warranty_contracts_count = 0
    violations: list[dict[str, Any]] = []

    for raw in contracts_warranty:
        if not isinstance(raw, dict):
            continue
        total_contracts_evaluated += 1
        contract_id = (
            str(raw.get("contract_id") or "").strip()
            or f"CNT-{total_contracts_evaluated}"
        )
        open_latent_defects_count = int(raw.get("open_latent_defects_count", 0) or 0)
        max_claim_response_days = int(raw.get("max_claim_response_days", 0) or 0)
        holdback_released = bool(raw.get("holdback_released", False))
        warranty_bond_active = bool(raw.get("warranty_bond_active", False))
        final_lien_waiver_signed = bool(raw.get("final_lien_waiver_signed", False))

        premature_holdback_release = holdback_released and (
            open_latent_defects_count > 0
            or (not final_lien_waiver_signed)
            or (not warranty_bond_active)
        )
        warranty_sla_breach = (
            open_latent_defects_count > 0 and max_claim_response_days > max_resp_days
        )
        unsecured_warranty = (not warranty_bond_active) and holdback_released

        reasons: list[str] = []
        if premature_holdback_release:
            premature_holdback_releases_count += 1
            reasons.append("premature_holdback_release")
        if warranty_sla_breach:
            warranty_sla_breached_contracts_count += 1
            reasons.append("warranty_claim_sla_breach")
        if unsecured_warranty:
            unsecured_warranty_contracts_count += 1
            reasons.append("unsecured_warranty_period")

        if not reasons:
            compliant_contracts_count += 1
        else:
            violations.append(
                {
                    "contract_id": contract_id,
                    "reasons": reasons,
                }
            )

    if (
        premature_holdback_releases_count == 0
        and warranty_sla_breached_contracts_count == 0
        and unsecured_warranty_contracts_count == 0
    ):
        status = "HEALTHY"
    elif (
        premature_holdback_releases_count > 0
        or warranty_sla_breached_contracts_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_contracts_evaluated": total_contracts_evaluated,
        "compliant_contracts_count": compliant_contracts_count,
        "premature_holdback_releases_count": premature_holdback_releases_count,
        "warranty_sla_breached_contracts_count": warranty_sla_breached_contracts_count,
        "unsecured_warranty_contracts_count": unsecured_warranty_contracts_count,
        "warranty_governance_status": status,
        "violations": violations,
    }


ProjectCCBService.audit_procurement_warranty_claims_and_holdback_release = staticmethod(
    audit_procurement_warranty_claims_and_holdback_release
)


def audit_change_request_reserve_drawdown_authorization(
    drawdown_requests: Sequence[Mapping[str, Any]] | None,
    *,
    contingency_reserve_available: float = 0.0,
    management_reserve_available: float = 0.0,
    require_sponsor_for_management_reserve: bool = True,
    require_risk_id_for_contingency: bool = True,
) -> dict[str, Any]:
    """Audita autorización de disposiciones de reserva de contingencia vs. reserva de gestión (PMI PMBOK §11.6 y §4.6).

    Verifica que riesgos conocidos-desconocidos consuman reserva de contingencia con
    trazabilidad al registro de riesgos, y que riesgos desconocidos-desconocidos
    consuman reserva de gestión con autorización ejecutiva/sponsor y actualización
    formal de línea base de costos, sin exceder los techos disponibles.
    """
    if (
        drawdown_requests is None
        or isinstance(drawdown_requests, (str, bytes))
        or not isinstance(drawdown_requests, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = drawdown_requests

    try:
        contingency_cap = max(0.0, float(contingency_reserve_available or 0.0))
    except (TypeError, ValueError):
        contingency_cap = 0.0

    try:
        management_cap = max(0.0, float(management_reserve_available or 0.0))
    except (TypeError, ValueError):
        management_cap = 0.0

    allowed_exec_roles = {
        "sponsor",
        "ccb_chair",
        "steering_committee",
        "executive_sponsor",
    }

    total_requests = 0
    compliant_requests = 0
    total_contingency_requested = 0.0
    total_management_requested = 0.0

    pool_mismatch_ids: list[str] = []
    missing_risk_traceability_ids: list[str] = []
    unauthorized_management_drawdown_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_requests += 1

        req_id = (
            str(
                raw.get("id")
                or raw.get("request_id")
                or raw.get("cr_id")
                or ""
            ).strip()
            or "CR-UNKNOWN"
        )
        uncertainty_type = str(raw.get("uncertainty_type") or "").strip().lower()
        reserve_pool = str(raw.get("reserve_pool") or "").strip().lower()

        try:
            amount = max(0.0, float(raw.get("amount") or 0.0))
        except (TypeError, ValueError):
            amount = 0.0

        linked_risk_id = str(raw.get("linked_risk_id") or "").strip()
        approved_by_role = str(raw.get("approved_by_role") or "").strip().lower()
        baseline_updated = bool(raw.get("baseline_updated"))

        if reserve_pool == "contingency":
            total_contingency_requested += amount
        elif reserve_pool == "management":
            total_management_requested += amount

        pool_mismatch = (
            reserve_pool not in {"contingency", "management"}
            or uncertainty_type not in {"known_unknown", "unknown_unknown"}
            or (uncertainty_type == "known_unknown" and reserve_pool != "contingency")
            or (uncertainty_type == "unknown_unknown" and reserve_pool != "management")
        )
        missing_risk_traceability = (
            reserve_pool == "contingency"
            and bool(require_risk_id_for_contingency)
            and not linked_risk_id
        )
        unauthorized_management_drawdown = reserve_pool == "management" and (
            (
                bool(require_sponsor_for_management_reserve)
                and approved_by_role not in allowed_exec_roles
            )
            or (not baseline_updated)
        )

        if pool_mismatch:
            pool_mismatch_ids.append(req_id)
        if missing_risk_traceability:
            missing_risk_traceability_ids.append(req_id)
        if unauthorized_management_drawdown:
            unauthorized_management_drawdown_ids.append(req_id)

        if (
            not pool_mismatch
            and not missing_risk_traceability
            and not unauthorized_management_drawdown
        ):
            compliant_requests += 1

    contingency_overrun_amount = round(
        max(0.0, total_contingency_requested - contingency_cap), 2
    )
    management_overrun_amount = round(
        max(0.0, total_management_requested - management_cap), 2
    )
    total_contingency_requested = round(total_contingency_requested, 2)
    total_management_requested = round(total_management_requested, 2)

    is_compliant = (
        len(pool_mismatch_ids) == 0
        and len(missing_risk_traceability_ids) == 0
        and len(unauthorized_management_drawdown_ids) == 0
        and contingency_overrun_amount == 0.0
        and management_overrun_amount == 0.0
    )

    if is_compliant:
        governance_health = "healthy"
    elif (
        contingency_overrun_amount > 0.0
        or management_overrun_amount > 0.0
        or len(unauthorized_management_drawdown_ids) > 0
        or len(pool_mismatch_ids) > 0
    ):
        governance_health = "critical"
    else:
        governance_health = "at_risk"

    recommendations: list[str] = []
    if pool_mismatch_ids:
        recommendations.append(
            f"Reclasificar solicitudes {pool_mismatch_ids}: 'known_unknown' debe usar 'contingency' y 'unknown_unknown' debe usar 'management'."
        )
    if missing_risk_traceability_ids:
        recommendations.append(
            f"Vincular un identificador de riesgo activo (linked_risk_id) para disposiciones de contingencia en {missing_risk_traceability_ids}."
        )
    if unauthorized_management_drawdown_ids:
        recommendations.append(
            f"Exigir aprobación de Sponsor/CCB Chair y actualización formal de línea base (baseline_updated=True) para reserva de gestión en {unauthorized_management_drawdown_ids}."
        )
    if contingency_overrun_amount > 0.0:
        recommendations.append(
            f"El consumo de reserva de contingencia excede el techo disponible en {contingency_overrun_amount}; tramitar solicitud de cambio al presupuesto base."
        )
    if management_overrun_amount > 0.0:
        recommendations.append(
            f"El consumo de reserva de gestión excede el techo disponible en {management_overrun_amount}; escalar al patrocinador ejecutivo."
        )

    return {
        "total_requests": total_requests,
        "compliant_requests": compliant_requests,
        "total_contingency_requested": total_contingency_requested,
        "total_management_requested": total_management_requested,
        "contingency_overrun_amount": contingency_overrun_amount,
        "management_overrun_amount": management_overrun_amount,
        "pool_mismatch_ids": pool_mismatch_ids,
        "missing_risk_traceability_ids": missing_risk_traceability_ids,
        "unauthorized_management_drawdown_ids": unauthorized_management_drawdown_ids,
        "governance_health": governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectCCBService.audit_change_request_reserve_drawdown_authorization = staticmethod(
    audit_change_request_reserve_drawdown_authorization
)


def audit_deliverable_formal_acceptance_and_waiver_expiration(
    deliverable_acceptances: Sequence[Mapping[str, Any]] | None,
    *,
    max_conditional_waiver_days: int = 30,
    require_customer_or_sponsor_signoff: bool = True,
    forbid_open_critical_defects: bool = True,
) -> dict[str, Any]:
    """Audita firma de aceptación formal de entregables, verificación previa de calidad (QC) y vigencia de dispensas condicionales (PMI PMBOK §8.3 y §5.5)."""
    if (
        deliverable_acceptances is None
        or isinstance(deliverable_acceptances, (str, bytes))
        or not isinstance(deliverable_acceptances, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = deliverable_acceptances

    try:
        max_waiver_days = int(max_conditional_waiver_days)
    except (TypeError, ValueError):
        max_waiver_days = 30

    allowed_signoff_roles = {
        "customer",
        "sponsor",
        "product_owner",
        "client_representative",
    }

    total_deliverables = 0
    compliant_deliverables = 0

    unverified_scope_acceptance_ids: list[str] = []
    unauthorized_signoff_or_critical_defect_ids: list[str] = []
    expired_or_unplanned_waiver_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_deliverables += 1

        deliverable_id = (
            str(raw.get("id") or raw.get("deliverable_id") or "").strip()
            or "DEL-UNKNOWN"
        )
        acceptance_status = (
            str(raw.get("acceptance_status") or "pending").strip().lower()
        )
        qc_verified = bool(raw.get("qc_verified"))
        signed_off_by_role = (
            str(raw.get("signed_off_by_role") or "").strip().lower()
        )

        try:
            open_critical_defects = max(
                0, int(raw.get("open_critical_defects") or 0)
            )
        except (TypeError, ValueError):
            open_critical_defects = 0

        try:
            waiver_days_elapsed = max(
                0, int(raw.get("waiver_days_elapsed") or 0)
            )
        except (TypeError, ValueError):
            waiver_days_elapsed = 0

        waiver_remediation_plan_linked = bool(
            raw.get("waiver_remediation_plan_linked")
        )

        is_accepted_or_conditional = acceptance_status in {
            "accepted",
            "conditionally_accepted",
        }

        is_unverified_scope = is_accepted_or_conditional and (not qc_verified)
        is_unauthorized_or_crit_defect = is_accepted_or_conditional and (
            (
                bool(require_customer_or_sponsor_signoff)
                and signed_off_by_role not in allowed_signoff_roles
            )
            or (
                bool(forbid_open_critical_defects)
                and open_critical_defects > 0
            )
        )
        is_expired_or_unplanned_waiver = (
            acceptance_status == "conditionally_accepted"
            and (
                waiver_days_elapsed > max_waiver_days
                or not waiver_remediation_plan_linked
            )
        )

        if is_unverified_scope:
            unverified_scope_acceptance_ids.append(deliverable_id)
        if is_unauthorized_or_crit_defect:
            unauthorized_signoff_or_critical_defect_ids.append(deliverable_id)
        if is_expired_or_unplanned_waiver:
            expired_or_unplanned_waiver_ids.append(deliverable_id)

        if (
            not is_unverified_scope
            and not is_unauthorized_or_crit_defect
            and not is_expired_or_unplanned_waiver
        ):
            compliant_deliverables += 1

    acceptance_integrity_score = (
        100.0
        if total_deliverables == 0
        else round((compliant_deliverables / total_deliverables) * 100.0, 2)
    )

    is_compliant = (
        len(unverified_scope_acceptance_ids) == 0
        and len(unauthorized_signoff_or_critical_defect_ids) == 0
        and len(expired_or_unplanned_waiver_ids) == 0
    )

    if is_compliant:
        acceptance_governance_health = "healthy"
    elif (
        len(unverified_scope_acceptance_ids) > 0
        or len(unauthorized_signoff_or_critical_defect_ids) > 0
    ):
        acceptance_governance_health = "critical"
    else:
        acceptance_governance_health = "at_risk"

    recommendations: list[str] = []
    if unverified_scope_acceptance_ids:
        recommendations.append(
            f"Completar verificación técnica de Control Quality (qc_verified=True) antes de aceptar alcance en {unverified_scope_acceptance_ids}."
        )
    if unauthorized_signoff_or_critical_defect_ids:
        recommendations.append(
            f"Exigir firma de cliente/sponsor/PO y cero defectos críticos abiertos antes de aceptar entregables en {unauthorized_signoff_or_critical_defect_ids}."
        )
    if expired_or_unplanned_waiver_ids:
        recommendations.append(
            f"Vincular plan de remediación y regularizar dispensas condicionales vencidas (> {max_waiver_days}d) en {expired_or_unplanned_waiver_ids}."
        )

    return {
        "total_deliverables": total_deliverables,
        "compliant_deliverables": compliant_deliverables,
        "unverified_scope_acceptance_ids": unverified_scope_acceptance_ids,
        "unauthorized_signoff_or_critical_defect_ids": unauthorized_signoff_or_critical_defect_ids,
        "expired_or_unplanned_waiver_ids": expired_or_unplanned_waiver_ids,
        "acceptance_integrity_score": acceptance_integrity_score,
        "acceptance_governance_health": acceptance_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectCCBService.audit_deliverable_formal_acceptance_and_waiver_expiration = staticmethod(
    audit_deliverable_formal_acceptance_and_waiver_expiration
)


def audit_quality_copq_and_rework_scrap_threshold(
    quality_cost_records: Sequence[Mapping[str, Any]] | None,
    *,
    min_conformance_investment_pct: float = 50.0,
    max_external_failure_to_copq_pct: float = 35.0,
    max_copq_to_bac_pct: float = 10.0,
) -> dict[str, Any]:
    """Audita el Costo de la Calidad (CoQ): equilibrio entre inversión de conformidad (prevención/evaluación) y costo de mala calidad (COPQ, retrabajo interno y fallos externos frente al BAC) (PMI PMBOK §8.1.2.3 y §8.3)."""
    if (
        quality_cost_records is None
        or isinstance(quality_cost_records, (str, bytes))
        or not isinstance(quality_cost_records, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = quality_cost_records

    try:
        min_conf_pct = float(min_conformance_investment_pct)
    except (TypeError, ValueError):
        min_conf_pct = 50.0

    try:
        max_ext_pct = float(max_external_failure_to_copq_pct)
    except (TypeError, ValueError):
        max_ext_pct = 35.0

    try:
        max_copq_bac_pct = float(max_copq_to_bac_pct)
    except (TypeError, ValueError):
        max_copq_bac_pct = 10.0

    def _pos_float(val: Any) -> float:
        try:
            return max(0.0, float(val or 0.0))
        except (TypeError, ValueError):
            return 0.0

    total_records = 0
    compliant_records = 0
    total_conformance_cost_accum = 0.0
    total_copq_accum = 0.0

    underinvested_conformance_ids: list[str] = []
    excessive_external_failure_leakage_ids: list[str] = []
    copq_budget_erosion_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_records += 1

        record_id = (
            str(raw.get("id") or raw.get("record_id") or "").strip()
            or "COQ-UNKNOWN"
        )

        prevention_cost = _pos_float(raw.get("prevention_cost"))
        appraisal_cost = _pos_float(raw.get("appraisal_cost"))
        internal_failure_cost = _pos_float(raw.get("internal_failure_cost"))
        external_failure_cost = _pos_float(raw.get("external_failure_cost"))
        bac = _pos_float(raw.get("bac"))

        conformance_cost = prevention_cost + appraisal_cost
        copq = internal_failure_cost + external_failure_cost
        total_coq = conformance_cost + copq

        total_conformance_cost_accum += conformance_cost
        total_copq_accum += copq

        is_underinvested = (
            total_coq > 0.0
            and (conformance_cost / total_coq) * 100.0 < min_conf_pct
        )
        is_excessive_ext = (
            copq > 0.0
            and (external_failure_cost / copq) * 100.0 > max_ext_pct
        )
        is_budget_erosion = (
            bac > 0.0
            and (copq / bac) * 100.0 > max_copq_bac_pct
        )

        if is_underinvested:
            underinvested_conformance_ids.append(record_id)
        if is_excessive_ext:
            excessive_external_failure_leakage_ids.append(record_id)
        if is_budget_erosion:
            copq_budget_erosion_ids.append(record_id)

        if (
            not is_underinvested
            and not is_excessive_ext
            and not is_budget_erosion
        ):
            compliant_records += 1

    is_compliant = (
        len(underinvested_conformance_ids) == 0
        and len(excessive_external_failure_leakage_ids) == 0
        and len(copq_budget_erosion_ids) == 0
    )

    if is_compliant:
        coq_governance_health = "healthy"
    elif (
        len(excessive_external_failure_leakage_ids) > 0
        or len(copq_budget_erosion_ids) > 0
    ):
        coq_governance_health = "critical"
    else:
        coq_governance_health = "at_risk"

    recommendations: list[str] = []
    if underinvested_conformance_ids:
        recommendations.append(
            f"Incrementar la inversión en prevención y evaluación (>= {min_conf_pct}% del CoQ total) en {underinvested_conformance_ids}."
        )
    if excessive_external_failure_leakage_ids:
        recommendations.append(
            f"Reforzar el control de calidad interno (QC) para contener fugas de fallos externos (> {max_ext_pct}% del COPQ) en {excessive_external_failure_leakage_ids}."
        )
    if copq_budget_erosion_ids:
        recommendations.append(
            f"Ejecutar análisis de causa raíz (CAPA) para reducir la erosión presupuestaria por COPQ (> {max_copq_bac_pct}% del BAC) en {copq_budget_erosion_ids}."
        )

    return {
        "total_records": total_records,
        "compliant_records": compliant_records,
        "total_conformance_cost": round(total_conformance_cost_accum, 2),
        "total_copq": round(total_copq_accum, 2),
        "underinvested_conformance_ids": underinvested_conformance_ids,
        "excessive_external_failure_leakage_ids": excessive_external_failure_leakage_ids,
        "copq_budget_erosion_ids": copq_budget_erosion_ids,
        "coq_governance_health": coq_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectCCBService.audit_quality_copq_and_rework_scrap_threshold = staticmethod(
    audit_quality_copq_and_rework_scrap_threshold
)



def audit_emergency_change_ratification_and_bypass_governance(
    change_requests: Sequence[Mapping[str, Any]] | None,
    *,
    max_ratification_hours: float = 48.0,
    max_emergency_share_pct: float = 20.0,
) -> dict[str, Any]:
    """PMBOK 4.6 — Perform Integrated Change Control: canal de emergencia.

    Auditoría pura sobre ``change_requests``. Entradas no-lista/None se
    tratan como lista vacía y elementos no-dict se ignoran. Reglas
    evaluadas sobre items con ``is_emergency`` True:

    1. ``unratified_overdue_or_unjustified_emergency``: ``severity_incident_linked`` falsy
       OR (``post_facto_ratified`` falsy AND ``hours_since_execution > max_ratification_hours``).
    2. ``emergency_without_rollback_safety``: ``rollback_tested`` falsy.

    Agregados: ``emergency_share_pct`` (emergency / total * 100, 0.0 sin
    cambios) y ``emergency_bypass_ratio_exceeded`` (total > 0 AND share >
    max_emergency_share_pct). ``emergency_governance_status``: HEALTHY si
    sin violaciones y ratio OK; CRITICAL si unratified > 0; AT_RISK en otro
    caso.
    """
    raw_items = change_requests if isinstance(change_requests, list) else []
    items = [entry for entry in raw_items if isinstance(entry, Mapping)]

    total = len(items)
    emergency_count = sum(1 for entry in items if entry.get("is_emergency") is True)

    unratified_count = 0
    rollback_count = 0
    compliant_count = 0
    violations: list[dict[str, Any]] = []

    for entry in items:
        cr_id = entry.get("cr_id")

        # Las reglas solo se evalúan sobre cambios de emergencia; el resto
        # ejecutó el control integrado normal y es trivialmente conforme.
        if entry.get("is_emergency") is not True:
            compliant_count += 1
            continue

        severity_incident_linked = entry.get("severity_incident_linked")
        post_facto_ratified = entry.get("post_facto_ratified")
        hours_since_execution = entry.get("hours_since_execution")
        rollback_tested = entry.get("rollback_tested")

        reasons: list[str] = []

        unjustified = severity_incident_linked is not True
        overdue = (
            post_facto_ratified is not True
            and isinstance(hours_since_execution, (int, float))
            and hours_since_execution > max_ratification_hours
        )
        if unjustified or overdue:
            reasons.append("unratified_overdue_or_unjustified_emergency")

        if rollback_tested is not True:
            reasons.append("emergency_without_rollback_safety")

        ordered_reasons = list(dict.fromkeys(reasons))
        if not ordered_reasons:
            compliant_count += 1
            continue

        if "unratified_overdue_or_unjustified_emergency" in ordered_reasons:
            unratified_count += 1
        if "emergency_without_rollback_safety" in ordered_reasons:
            rollback_count += 1

        violations.append(
            {
                "cr_id": cr_id,
                "reasons": ordered_reasons,
            }
        )

    emergency_share_pct = round((emergency_count / total) * 100.0, 2) if total > 0 else 0.0
    bypass_exceeded = total > 0 and emergency_share_pct > max_emergency_share_pct

    if unratified_count > 0:
        status = "CRITICAL"
    elif rollback_count > 0 or bypass_exceeded:
        status = "AT_RISK"
    else:
        status = "HEALTHY"

    return {
        "total_changes": total,
        "emergency_changes_count": emergency_count,
        "compliant_changes_count": compliant_count,
        "unratified_overdue_or_unjustified_emergency_count": unratified_count,
        "emergency_without_rollback_safety_count": rollback_count,
        "emergency_share_pct": emergency_share_pct,
        "emergency_bypass_ratio_exceeded": bypass_exceeded,
        "emergency_governance_status": status,
        "violations": violations,
    }


ProjectCCBService.audit_emergency_change_ratification_and_bypass_governance = staticmethod(
    audit_emergency_change_ratification_and_bypass_governance
)


def audit_quality_capa_root_cause_and_recurrence(
    capa_items: Sequence[Mapping[str, Any]] | None,
    *,
    max_verification_lag_days: int = 30,
    require_rca_method: bool = True,
) -> dict[str, Any]:
    """Audita acciones correctivas y preventivas (CAPA): documentación de método RCA (5 Whys, Ishikawa, etc.), verificación oportuna de efectividad y ausencia de recurrencia de defectos (PMI PMBOK §8.2 y §4.6)."""
    if (
        capa_items is None
        or isinstance(capa_items, (str, bytes))
        or not isinstance(capa_items, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = capa_items

    try:
        max_lag_days = int(max_verification_lag_days)
    except (TypeError, ValueError):
        max_lag_days = 30

    req_rca = bool(require_rca_method)

    total_capas = 0
    compliant_capas = 0

    missing_rca_or_premature_closure_ids: list[str] = []
    overdue_effectiveness_verification_ids: list[str] = []
    recurring_failure_capa_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_capas += 1

        capa_id = (
            str(raw.get("id") or raw.get("capa_id") or "").strip()
            or "CAPA-UNKNOWN"
        )
        status = str(raw.get("status") or "").strip().lower()
        rca_method = str(raw.get("rca_method") or "").strip().lower()
        effectiveness_verified = bool(raw.get("effectiveness_verified"))

        try:
            days_since_implementation = max(
                0, int(raw.get("days_since_implementation") or 0)
            )
        except (TypeError, ValueError):
            days_since_implementation = 0

        try:
            recurrence_count = max(0, int(raw.get("recurrence_count") or 0))
        except (TypeError, ValueError):
            recurrence_count = 0

        is_missing_rca_or_premature = (req_rca and not rca_method) or (
            status == "verified_closed" and not effectiveness_verified
        )
        is_overdue_verification = (
            status == "implemented"
            and not effectiveness_verified
            and days_since_implementation > max_lag_days
        )
        is_recurring = recurrence_count > 0

        if is_missing_rca_or_premature:
            missing_rca_or_premature_closure_ids.append(capa_id)
        if is_overdue_verification:
            overdue_effectiveness_verification_ids.append(capa_id)
        if is_recurring:
            recurring_failure_capa_ids.append(capa_id)

        if (
            not is_missing_rca_or_premature
            and not is_overdue_verification
            and not is_recurring
        ):
            compliant_capas += 1

    is_compliant = (
        len(missing_rca_or_premature_closure_ids) == 0
        and len(overdue_effectiveness_verification_ids) == 0
        and len(recurring_failure_capa_ids) == 0
    )

    if is_compliant:
        capa_governance_health = "healthy"
    elif (
        len(missing_rca_or_premature_closure_ids) > 0
        or len(recurring_failure_capa_ids) > 0
    ):
        capa_governance_health = "critical"
    else:
        capa_governance_health = "at_risk"

    recommendations: list[str] = []
    if missing_rca_or_premature_closure_ids:
        recommendations.append(
            f"Documentar método formal de Análisis de Causa Raíz (RCA) y verificar efectividad antes de cerrar CAPA en {missing_rca_or_premature_closure_ids}."
        )
    if overdue_effectiveness_verification_ids:
        recommendations.append(
            f"Ejecutar verificación de efectividad post-implementación (<= {max_lag_days} días) en {overdue_effectiveness_verification_ids}."
        )
    if recurring_failure_capa_ids:
        recommendations.append(
            f"Reabrir el análisis de causa raíz por recurrencia del defecto tras la acción CAPA en {recurring_failure_capa_ids}."
        )

    return {
        "total_capas": total_capas,
        "compliant_capas": compliant_capas,
        "missing_rca_or_premature_closure_ids": missing_rca_or_premature_closure_ids,
        "overdue_effectiveness_verification_ids": overdue_effectiveness_verification_ids,
        "recurring_failure_capa_ids": recurring_failure_capa_ids,
        "capa_governance_health": capa_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectCCBService.audit_quality_capa_root_cause_and_recurrence = staticmethod(
    audit_quality_capa_root_cause_and_recurrence
)



def audit_configuration_baseline_integrity_and_version_drift(
    configuration_items: Sequence[Mapping[str, Any]] | None,
    *,
    require_checksum_verification: bool = True,
    max_allowed_drift_items: int = 0,
) -> dict[str, Any]:
    """PMBOK 4.6 — Configuration Verification & Audit de la línea base.

    Auditoría pura sobre ``configuration_items``. Entradas no-lista/None se
    tratan como lista vacía y elementos no-dict se ignoran. Cada elemento:
    ``ci_id``, ``approved_baseline_version``, ``deployed_version``,
    ``approved_cr_id``, ``checksum_matches_artifact``,
    ``is_locked_in_cm_repo``. Reglas:

    1. ``unauthorized_drift_ci_ids``: ``deployed_version !=
       approved_baseline_version`` sin ``approved_cr_id``.
    2. ``pending_baseline_sync_ci_ids``: versiones difieren pero con CR
       aprobado pendiente de sincronizar.
    3. ``checksum_mismatch_ci_ids``: ``require_checksum_verification`` AND
       ``checksum_matches_artifact`` falsy.
    4. ``unlocked_baseline_ci_ids``: ``is_locked_in_cm_repo`` falsy.

    Enumeraciones: las comparaciones de versión se realizan como cadenas
    strip()-cadas para tolerar espacios; vacío/None cuenta como diferencia.
    ``cm_audit_status``: COMPROMISED si ``len(unauthorized_drift) >
    max_allowed_drift_items`` o hay checksum mismatch; DRIFT_DETECTED si no
    es COMPROMISED pero hay al menos una lista no vacia; VERIFIED en caso
    contrario. ``is_baseline_intact`` = status == 'VERIFIED'.
    """
    raw_items = configuration_items if isinstance(configuration_items, list) else []
    items = [entry for entry in raw_items if isinstance(entry, Mapping)]

    def _norm(value: Any) -> str | None:
        if not isinstance(value, str):
            return value if isinstance(value, str) else None
        stripped = value.strip()
        return stripped if stripped else None

    unauthorized_drift_ci_ids: list[str] = []
    pending_baseline_sync_ci_ids: list[str] = []
    checksum_mismatch_ci_ids: list[str] = []
    unlocked_baseline_ci_ids: list[str] = []

    for entry in items:
        ci_id = entry.get("ci_id")
        approved_version = _norm(entry.get("approved_baseline_version"))
        deployed_version = _norm(entry.get("deployed_version"))
        approved_cr_id = _norm(entry.get("approved_cr_id"))
        has_approved_cr = isinstance(approved_cr_id, str) and bool(approved_cr_id)

        versions_differ = bool(approved_version or deployed_version) and (
            approved_version != deployed_version
        )
        if versions_differ:
            if has_approved_cr:
                pending_baseline_sync_ci_ids.append(ci_id)
            else:
                unauthorized_drift_ci_ids.append(ci_id)

        if require_checksum_verification and entry.get("checksum_matches_artifact") is not True:
            checksum_mismatch_ci_ids.append(ci_id)

        if entry.get("is_locked_in_cm_repo") is not True:
            unlocked_baseline_ci_ids.append(ci_id)

    compromised = (
        len(unauthorized_drift_ci_ids) > max_allowed_drift_items
        or len(checksum_mismatch_ci_ids) > 0
    )
    if compromised:
        cm_audit_status = "COMPROMISED"
    elif unauthorized_drift_ci_ids or pending_baseline_sync_ci_ids or unlocked_baseline_ci_ids:
        cm_audit_status = "DRIFT_DETECTED"
    else:
        cm_audit_status = "VERIFIED"

    return {
        "total_configuration_items": len(items),
        "unauthorized_drift_ci_ids": unauthorized_drift_ci_ids,
        "pending_baseline_sync_ci_ids": pending_baseline_sync_ci_ids,
        "checksum_mismatch_ci_ids": checksum_mismatch_ci_ids,
        "unlocked_baseline_ci_ids": unlocked_baseline_ci_ids,
        "cm_audit_status": cm_audit_status,
        "is_baseline_intact": cm_audit_status == "VERIFIED",
    }


ProjectCCBService.audit_configuration_baseline_integrity_and_version_drift = staticmethod(
    audit_configuration_baseline_integrity_and_version_drift
)


def audit_scope_creep_and_gold_plating_effort(
    work_items: list[dict[str, Any]],
    *,
    max_unbaselined_effort_ratio_pct: float = 5.0,
) -> dict[str, Any]:
    """Audita desviaciones de alcance no autorizadas (Scope Creep) y funcionalidades extra no solicitadas (Gold-Plating) frente a la línea base WBS y órdenes de cambio CCB (PMI PMBOK §5.6)."""
    if (
        work_items is None
        or isinstance(work_items, (str, bytes))
        or not isinstance(work_items, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = work_items

    try:
        max_ratio_pct = float(max_unbaselined_effort_ratio_pct)
    except (TypeError, ValueError):
        max_ratio_pct = 5.0

    total_work_items = 0
    unapproved_scope_creep_ids: list[str] = []
    gold_plating_item_ids: list[str] = []
    unbaselined_accum = 0.0
    total_effort_accum = 0.0
    issues: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_work_items += 1

        item_id = (
            str(raw.get("item_id") or raw.get("id") or "").strip()
            or f"WRK-{total_work_items}"
        )

        raw_hrs = raw.get("logged_hours")
        if raw_hrs is None or isinstance(raw_hrs, bool):
            logged_hours = 0.0
        else:
            try:
                logged_hours = max(0.0, float(raw_hrs))
            except (TypeError, ValueError):
                logged_hours = 0.0

        in_approved_wbs_baseline = bool(raw.get("in_approved_wbs_baseline"))
        linked_approved_cr_id = str(
            raw.get("linked_approved_cr_id") or ""
        ).strip()
        is_gold_plating = bool(raw.get("is_gold_plating_extra_feature"))

        total_effort_accum += logged_hours

        is_creep = (
            not in_approved_wbs_baseline
            and not linked_approved_cr_id
            and logged_hours > 0.0
        )
        is_gp = is_gold_plating and logged_hours > 0.0

        if is_creep:
            unapproved_scope_creep_ids.append(item_id)
            issues.append(
                f"Ítem '{item_id}' registra esfuerzo ({logged_hours:.2f}h) fuera de la línea base WBS sin solicitud de cambio (CR) aprobada."
            )
        if is_gp:
            gold_plating_item_ids.append(item_id)
            issues.append(
                f"Ítem '{item_id}' constituye Gold-Plating no solicitado con {logged_hours:.2f}h imputadas."
            )

        if is_creep or is_gp:
            unbaselined_accum += logged_hours

    unbaselined_effort_hours = round(unbaselined_accum, 2)
    total_effort_hours = round(total_effort_accum, 2)
    unbaselined_effort_ratio_pct = (
        round((unbaselined_effort_hours / total_effort_hours) * 100.0, 2)
        if total_effort_hours > 0.0
        else 0.0
    )

    if unbaselined_effort_ratio_pct > max_ratio_pct:
        issues.append(
            f"El porcentaje de esfuerzo fuera de línea base ({unbaselined_effort_ratio_pct:.2f}%) supera el umbral permitido ({max_ratio_pct:.2f}%)."
        )

    if (
        unbaselined_effort_ratio_pct > max_ratio_pct
        or len(gold_plating_item_ids) > 0
    ):
        scope_control_status = "SCOPE_BREACH"
    elif len(unapproved_scope_creep_ids) > 0:
        scope_control_status = "MINOR_DRIFT"
    else:
        scope_control_status = "DISCIPLINED"

    return {
        "total_work_items": total_work_items,
        "unapproved_scope_creep_ids": unapproved_scope_creep_ids,
        "gold_plating_item_ids": gold_plating_item_ids,
        "unbaselined_effort_hours": unbaselined_effort_hours,
        "total_effort_hours": total_effort_hours,
        "unbaselined_effort_ratio_pct": unbaselined_effort_ratio_pct,
        "scope_control_status": scope_control_status,
        "is_scope_disciplined": scope_control_status == "DISCIPLINED",
        "issues": issues,
    }


ProjectCCBService.audit_scope_creep_and_gold_plating_effort = staticmethod(
    audit_scope_creep_and_gold_plating_effort
)


def audit_quality_spc_control_chart_stability(
    sample_points: list[dict[str, Any]],
    *,
    center_line_mean: float = 0.0,
    one_sigma_std_dev: float = 1.0,
    upper_spec_limit_usl: float | None = None,
    lower_spec_limit_lsl: float | None = None,
) -> dict[str, Any]:
    """Audita estabilidad estadística de gráficos de control SPC y Regla de Siete (PMI PMBOK §8.3)."""
    mean = float(center_line_mean if center_line_mean is not None else 0.0)
    sigma = max(0.0, float(one_sigma_std_dev if one_sigma_std_dev is not None else 1.0))
    usl = float(upper_spec_limit_usl) if upper_spec_limit_usl is not None else None
    lsl = float(lower_spec_limit_lsl) if lower_spec_limit_lsl is not None else None

    ucl_3sigma = round(mean + 3.0 * sigma, 4)
    lcl_3sigma = round(mean - 3.0 * sigma, 4)

    if not isinstance(sample_points, list):
        return {
            "total_samples": 0,
            "ucl_3sigma": ucl_3sigma,
            "lcl_3sigma": lcl_3sigma,
            "beyond_3sigma_sample_ids": [],
            "beyond_spec_limit_sample_ids": [],
            "rule_of_seven_run_detected": False,
            "process_stability_status": "IN_STATISTICAL_CONTROL",
            "is_process_stable": True,
            "issues": [],
        }

    total_samples = 0
    beyond_3sigma_sample_ids: list[str] = []
    beyond_spec_limit_sample_ids: list[str] = []
    issues: list[str] = []

    above_run = 0
    below_run = 0
    rule_of_seven_run_detected = False

    for idx, item in enumerate(sample_points):
        if not isinstance(item, dict):
            continue
        total_samples += 1
        sample_id = str(item.get("sample_id") or f"SAMPLE-{idx + 1}").strip()
        measured_value = float(item.get("measured_value") or 0.0)

        if measured_value > ucl_3sigma or measured_value < lcl_3sigma:
            beyond_3sigma_sample_ids.append(sample_id)
            issues.append(
                f"Muestra '{sample_id}' ({measured_value:.4f}) fuera de límites de control ±3σ [{lcl_3sigma:.4f}, {ucl_3sigma:.4f}]."
            )

        if (usl is not None and measured_value > usl) or (
            lsl is not None and measured_value < lsl
        ):
            beyond_spec_limit_sample_ids.append(sample_id)
            issues.append(
                f"Muestra '{sample_id}' ({measured_value:.4f}) fuera de límites de especificación USL/LSL."
            )

        if measured_value > mean:
            above_run += 1
            below_run = 0
        elif measured_value < mean:
            below_run += 1
            above_run = 0
        else:
            above_run = 0
            below_run = 0

        if above_run >= 7 or below_run >= 7:
            rule_of_seven_run_detected = True

    if rule_of_seven_run_detected:
        issues.append(
            "Se detectó corrida no aleatoria de >= 7 puntos consecutivos del mismo lado de la línea central (Rule of Seven)."
        )

    if len(beyond_spec_limit_sample_ids) > 0:
        process_stability_status = "OUT_OF_SPEC"
    elif len(beyond_3sigma_sample_ids) > 0 or rule_of_seven_run_detected:
        process_stability_status = "OUT_OF_CONTROL"
    else:
        process_stability_status = "IN_STATISTICAL_CONTROL"

    return {
        "total_samples": total_samples,
        "ucl_3sigma": ucl_3sigma,
        "lcl_3sigma": lcl_3sigma,
        "beyond_3sigma_sample_ids": beyond_3sigma_sample_ids,
        "beyond_spec_limit_sample_ids": beyond_spec_limit_sample_ids,
        "rule_of_seven_run_detected": rule_of_seven_run_detected,
        "process_stability_status": process_stability_status,
        "is_process_stable": process_stability_status == "IN_STATISTICAL_CONTROL",
        "issues": issues,
    }


ProjectCCBService.audit_quality_spc_control_chart_stability = staticmethod(
    audit_quality_spc_control_chart_stability
)


def audit_defect_removal_efficiency_and_uat_readiness(
    *,
    pre_release_defects_found: int = 0,
    post_release_escaped_defects: int = 0,
    open_sev1_blocker_defects: int = 0,
    open_sev2_critical_defects: int = 0,
    uat_test_cases_total: int = 0,
    uat_test_cases_passed: int = 0,
    min_required_dre_pct: float = 90.0,
    min_uat_pass_rate_pct: float = 95.0,
) -> Dict[str, object]:
    """Auditoría PMBOK 8.3 Control Quality y 5.5 Validate Scope.

    Calcula defect_removal_efficiency_dre_pct y defect_escape_ratio_pct,
    el UAT pass rate y determina si el flujo de release está listo para
    formal sign-off (is_uat_sign_off_ready).
    """
    safe_pre_release = max(0, pre_release_defects_found)
    safe_post_release = max(0, post_release_escaped_defects)
    total_defects = safe_pre_release + safe_post_release

    if total_defects > 0:
        defect_removal_efficiency_dre_pct = round(
            (safe_pre_release / total_defects) * 100.0, 2
        )
    else:
        defect_removal_efficiency_dre_pct = 100.0

    defect_escape_ratio_pct = round(
        100.0 - defect_removal_efficiency_dre_pct, 2
    )

    safe_uat_passed = max(0, uat_test_cases_passed)
    if uat_test_cases_total > 0:
        uat_pass_rate_pct = round((safe_uat_passed / uat_test_cases_total) * 100.0, 2)
    else:
        uat_pass_rate_pct = 0.0

    blocking_conditions: List[str] = []
    if open_sev1_blocker_defects > 0:
        blocking_conditions.append("open_sev1_blockers")
    if open_sev2_critical_defects > 0:
        blocking_conditions.append("open_sev2_criticals")
    if uat_pass_rate_pct < min_uat_pass_rate_pct:
        blocking_conditions.append("uat_pass_rate_below_threshold")
    if defect_removal_efficiency_dre_pct < min_required_dre_pct:
        blocking_conditions.append("dre_below_threshold")

    if open_sev1_blocker_defects > 0 or uat_pass_rate_pct < min_uat_pass_rate_pct:
        release_gate_status = "RELEASE_BLOCKED"
    elif (
        open_sev2_critical_defects > 0
        or defect_removal_efficiency_dre_pct < min_required_dre_pct
    ):
        release_gate_status = "CONDITIONAL_WAIVER_REQUIRED"
    else:
        release_gate_status = "READY_FOR_SIGN_OFF"

    is_uat_sign_off_ready = release_gate_status == "READY_FOR_SIGN_OFF"

    return {
        "total_defects": total_defects,
        "defect_removal_efficiency_dre_pct": defect_removal_efficiency_dre_pct,
        "defect_escape_ratio_pct": defect_escape_ratio_pct,
        "uat_pass_rate_pct": uat_pass_rate_pct,
        "blocking_conditions": blocking_conditions,
        "release_gate_status": release_gate_status,
        "is_uat_sign_off_ready": is_uat_sign_off_ready,
    }


ProjectCCBService.audit_defect_removal_efficiency_and_uat_readiness = staticmethod(
    audit_defect_removal_efficiency_and_uat_readiness
)


def audit_cost_of_quality_conformance_and_failure_ratio(
    coq_entries: list[dict[str, Any]],
    *,
    total_project_budget: float,
    min_conformance_share_pct: float = 60.0,
    max_coq_budget_share_pct: float = 15.0,
) -> dict[str, Any]:
    """Audita Costo de la Calidad (CoQ: Prevención/Evaluación vs Fallas Internas/Externas) y proporción óptima de conformidad (PMI PMBOK §8.2 / §8.3)."""
    budget = max(0.0, float(total_project_budget or 0.0))
    min_conf_pct = float(
        min_conformance_share_pct if min_conformance_share_pct is not None else 60.0
    )
    max_coq_pct = float(
        max_coq_budget_share_pct if max_coq_budget_share_pct is not None else 15.0
    )

    if not isinstance(coq_entries, list):
        return {
            "prevention_cost": 0.0,
            "appraisal_cost": 0.0,
            "internal_failure_cost": 0.0,
            "external_failure_cost": 0.0,
            "cost_of_conformance": 0.0,
            "cost_of_non_conformance": 0.0,
            "total_coq": 0.0,
            "conformance_share_pct": 100.0,
            "external_failure_share_pct": 0.0,
            "coq_budget_share_pct": 0.0,
            "prevention_starvation": False,
            "coq_health_status": "OPTIMAL",
            "recommendations": [],
        }

    prev_raw = 0.0
    appr_raw = 0.0
    int_fail_raw = 0.0
    ext_fail_raw = 0.0

    for item in coq_entries:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "").strip().upper()
        amount = max(0.0, float(item.get("amount") or 0.0))
        if category == "PREVENTION":
            prev_raw += amount
        elif category == "APPRAISAL":
            appr_raw += amount
        elif category == "INTERNAL_FAILURE":
            int_fail_raw += amount
        elif category == "EXTERNAL_FAILURE":
            ext_fail_raw += amount

    prevention_cost = round(prev_raw, 2)
    appraisal_cost = round(appr_raw, 2)
    internal_failure_cost = round(int_fail_raw, 2)
    external_failure_cost = round(ext_fail_raw, 2)

    cost_of_conformance = round(prevention_cost + appraisal_cost, 2)
    cost_of_non_conformance = round(
        internal_failure_cost + external_failure_cost, 2
    )
    total_coq = round(cost_of_conformance + cost_of_non_conformance, 2)

    conformance_share_pct = (
        round((cost_of_conformance / total_coq) * 100.0, 2)
        if total_coq > 0.0
        else 100.0
    )
    external_failure_share_pct = (
        round((external_failure_cost / total_coq) * 100.0, 2)
        if total_coq > 0.0
        else 0.0
    )
    coq_budget_share_pct = (
        round((total_coq / budget) * 100.0, 2) if budget > 0.0 else 0.0
    )
    prevention_starvation = bool(
        prevention_cost < appraisal_cost * 0.25 and cost_of_non_conformance > 0.0
    )

    recommendations: list[str] = []
    if cost_of_non_conformance > cost_of_conformance:
        recommendations.append(
            "El costo de no-conformidad supera la inversión en conformidad; incrementar prevención y aseguramiento."
        )
    if external_failure_share_pct > 25.0:
        recommendations.append(
            f"La proporción de fallas externas ({external_failure_share_pct:.2f}%) supera el 25% del CoQ total."
        )
    if conformance_share_pct < min_conf_pct:
        recommendations.append(
            f"La proporción de conformidad ({conformance_share_pct:.2f}%) es inferior al mínimo objetivo ({min_conf_pct:.2f}%)."
        )
    if coq_budget_share_pct > max_coq_pct:
        recommendations.append(
            f"El CoQ total ({coq_budget_share_pct:.2f}% del presupuesto) excede el umbral máximo ({max_coq_pct:.2f}%)."
        )
    if prevention_starvation:
        recommendations.append(
            "Inversión en prevención insuficiente (< 25% del gasto en evaluación con fallas activas); reasignar hacia ingeniería preventiva."
        )

    if (
        cost_of_non_conformance > cost_of_conformance
        or external_failure_share_pct > 25.0
    ):
        coq_health_status = "CRITICAL"
    elif (
        conformance_share_pct < min_conf_pct
        or coq_budget_share_pct > max_coq_pct
        or prevention_starvation
    ):
        coq_health_status = "WARNING"
    else:
        coq_health_status = "OPTIMAL"

    return {
        "prevention_cost": prevention_cost,
        "appraisal_cost": appraisal_cost,
        "internal_failure_cost": internal_failure_cost,
        "external_failure_cost": external_failure_cost,
        "cost_of_conformance": cost_of_conformance,
        "cost_of_non_conformance": cost_of_non_conformance,
        "total_coq": total_coq,
        "conformance_share_pct": conformance_share_pct,
        "external_failure_share_pct": external_failure_share_pct,
        "coq_budget_share_pct": coq_budget_share_pct,
        "prevention_starvation": prevention_starvation,
        "coq_health_status": coq_health_status,
        "recommendations": recommendations,
    }


ProjectCCBService.audit_cost_of_quality_conformance_and_failure_ratio = staticmethod(
    audit_cost_of_quality_conformance_and_failure_ratio
)


def audit_technical_debt_interest_and_remediation_quota(
    debt_items: Any,
    *,
    total_iteration_capacity_hours: float,
    allocated_remediation_hours: float,
    min_remediation_quota_pct: float = 15.0,
    max_debt_drag_pct: float = 20.0,
) -> Dict[str, object]:
    """Auditoría PMBOK 8.2 y Agile Practice Guide: deuda técnica.

    Calcula el principal acumulado y el interés compuesto por iteración
    (debt_drag_pct), compar los quotas de remediación presupuestados y
    detecta deuda HIGH sin ticket de remediación y deuda con insolvencia
    por compound (interest * age > principal).
    """
    entries = debt_items if isinstance(debt_items, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    total_principal_hours: float = 0.0
    total_interest_hours_per_iteration: float = 0.0
    untracked_high_debt_ids: List[str] = []
    compounding_insolvency_ids: List[str] = []

    for item in rows:
        principal = item.get("principal_remediation_hours")
        interest = item.get("recurring_interest_hours_per_iteration")
        age = item.get("age_iterations")
        principal_val = principal if isinstance(principal, (int, float)) else 0.0
        interest_val = interest if isinstance(interest, (int, float)) else 0.0
        age_val = age if isinstance(age, (int, float)) else 0

        total_principal_hours += max(0.0, float(principal_val))
        total_interest_hours_per_iteration += max(0.0, float(interest_val))

        if item.get("severity") == "HIGH" and item.get("has_remediation_ticket", True) is False:
            untracked_high_debt_ids.append(item.get("debt_id"))

        if (
            principal_val > 0
            and interest_val * age_val > principal_val
        ):
            compounding_insolvency_ids.append(item.get("debt_id"))

    total_principal_hours = round(total_principal_hours, 2)
    total_interest_hours_per_iteration = round(total_interest_hours_per_iteration, 2)

    if total_iteration_capacity_hours > 0:
        debt_drag_pct = round(
            (total_interest_hours_per_iteration / total_iteration_capacity_hours) * 100.0,
            2,
        )
        actual_remediation_quota_pct = round(
            (allocated_remediation_hours / total_iteration_capacity_hours) * 100.0,
            2,
        )
    else:
        debt_drag_pct = 0.0
        actual_remediation_quota_pct = 0.0

    if debt_drag_pct > max_debt_drag_pct or untracked_high_debt_ids:
        debt_governance_status = "BANKRUPTCY_RISK"
    elif (
        total_principal_hours > 0 and actual_remediation_quota_pct < min_remediation_quota_pct
    ) or compounding_insolvency_ids:
        debt_governance_status = "WARNING"
    else:
        debt_governance_status = "SUSTAINABLE"

    recommendations: List[str] = []
    if debt_drag_pct > max_debt_drag_pct:
        recommendations.append(
            f"Reduce per-iteration debt drag: {debt_drag_pct}% exceeds max {max_debt_drag_pct}%"
        )
    if untracked_high_debt_ids:
        recommendations.append(
            "Create remediation tickets for untracked HIGH severity debts: "
            + ", ".join(str(d) for d in untracked_high_debt_ids)
        )
    if total_principal_hours > 0 and actual_remediation_quota_pct < min_remediation_quota_pct:
        recommendations.append(
            f"Increase remediation quota: {actual_remediation_quota_pct}% is below min {min_remediation_quota_pct}%"
        )
    if compounding_insolvency_ids:
        recommendations.append(
            "Pay down debts whose compounded interest exceeds principal (interest * age > principal): "
            + ", ".join(str(d) for d in compounding_insolvency_ids)
        )

    return {
        "total_debt_items": len(rows),
        "total_principal_hours": total_principal_hours,
        "total_interest_hours_per_iteration": total_interest_hours_per_iteration,
        "debt_drag_pct": debt_drag_pct,
        "actual_remediation_quota_pct": actual_remediation_quota_pct,
        "untracked_high_debt_ids": untracked_high_debt_ids,
        "compounding_insolvency_ids": compounding_insolvency_ids,
        "debt_governance_status": debt_governance_status,
        "is_debt_sustainable": debt_governance_status == "SUSTAINABLE",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_technical_debt_interest_and_remediation_quota = staticmethod(
    audit_technical_debt_interest_and_remediation_quota
)


def audit_canary_rollout_blast_radius_and_rollback_readiness(
    releases: list[dict[str, Any]],
    *,
    max_initial_canary_traffic_pct: float = 10.0,
    min_bake_time_minutes: int = 60,
) -> dict[str, Any]:
    """Audit PMI PMBOK §8.3 & §4.6 CCB canary rollout blast-radius, bake time, and automated rollback readiness."""
    excessive_blast_radius_release_ids: list[str] = []
    insufficient_bake_time_release_ids: list[str] = []
    unverified_rollback_release_ids: list[str] = []
    breaking_db_migration_release_ids: list[str] = []
    recommendations: list[str] = []

    valid_releases = (
        [
            r
            for r in releases
            if isinstance(r, dict) and str(r.get("release_id", "")).strip()
        ]
        if isinstance(releases, list)
        else []
    )

    for rel in valid_releases:
        release_id = str(rel.get("release_id", "")).strip()
        initial_canary_traffic_pct = float(
            rel.get("initial_canary_traffic_pct", 0.0) or 0.0
        )
        bake_time_minutes = int(rel.get("bake_time_minutes", 0) or 0)
        has_automated_rollback_trigger = bool(
            rel.get("has_automated_rollback_trigger", False)
        )
        rollback_tested_in_staging = bool(
            rel.get("rollback_tested_in_staging", False)
        )
        has_backward_compatible_db_migration = (
            bool(rel.get("has_backward_compatible_db_migration", True))
            if rel.get("has_backward_compatible_db_migration") is not None
            else True
        )

        if initial_canary_traffic_pct > max_initial_canary_traffic_pct:
            excessive_blast_radius_release_ids.append(release_id)

        if bake_time_minutes < min_bake_time_minutes:
            insufficient_bake_time_release_ids.append(release_id)

        if not has_automated_rollback_trigger or not rollback_tested_in_staging:
            unverified_rollback_release_ids.append(release_id)

        if not has_backward_compatible_db_migration:
            breaking_db_migration_release_ids.append(release_id)

    if unverified_rollback_release_ids:
        recommendations.append(
            f"Configure automated rollback triggers and verify staging rollback before deploying: {', '.join(unverified_rollback_release_ids)}."
        )
    if breaking_db_migration_release_ids:
        recommendations.append(
            f"Refactor breaking schema changes into expand-contract backward-compatible migrations for: {', '.join(breaking_db_migration_release_ids)}."
        )
    if excessive_blast_radius_release_ids:
        recommendations.append(
            f"Cap initial canary traffic exposure at <={max_initial_canary_traffic_pct:.1f}% for releases: {', '.join(excessive_blast_radius_release_ids)}."
        )
    if insufficient_bake_time_release_ids:
        recommendations.append(
            f"Enforce a minimum canary bake window of {min_bake_time_minutes} minutes for releases: {', '.join(insufficient_bake_time_release_ids)}."
        )

    if unverified_rollback_release_ids or breaking_db_migration_release_ids:
        rollout_governance_status = "BLOCKED"
    elif excessive_blast_radius_release_ids or insufficient_bake_time_release_ids:
        rollout_governance_status = "WARNING"
    else:
        rollout_governance_status = "SAFE_TO_DEPLOY"

    return {
        "total_releases": len(valid_releases),
        "excessive_blast_radius_release_ids": excessive_blast_radius_release_ids,
        "insufficient_bake_time_release_ids": insufficient_bake_time_release_ids,
        "unverified_rollback_release_ids": unverified_rollback_release_ids,
        "breaking_db_migration_release_ids": breaking_db_migration_release_ids,
        "rollout_governance_status": rollout_governance_status,
        "is_rollout_ready": rollout_governance_status == "SAFE_TO_DEPLOY",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_canary_rollout_blast_radius_and_rollback_readiness = staticmethod(
    audit_canary_rollout_blast_radius_and_rollback_readiness
)


def audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene(
    feature_flags: list[dict[str, Any]],
    *,
    max_rollout_flag_ttl_days: int = 30,
    max_active_release_flags: int = 10,
) -> dict[str, Any]:
    """Audit PMI PMBOK §8.3 & §4.6 CCB feature flag lifecycle debt, kill-switch ownership, and CI branch coverage."""
    zombie_flag_ids: list[str] = []
    unowned_flag_ids: list[str] = []
    untested_branch_flag_ids: list[str] = []
    missing_cleanup_ticket_flag_ids: list[str] = []
    recommendations: list[str] = []

    valid_flags = (
        [
            f
            for f in feature_flags
            if isinstance(f, dict) and str(f.get("flag_id", "")).strip()
        ]
        if isinstance(feature_flags, list)
        else []
    )

    active_release_flags_count = 0

    for flag in valid_flags:
        flag_id = str(flag.get("flag_id", "")).strip()
        flag_type = str(flag.get("flag_type", "RELEASE")).strip().upper()
        age_days = int(flag.get("age_days", 0) or 0)
        rollout_pct = float(flag.get("rollout_pct", 0.0) or 0.0)
        owner_raw = flag.get("owner_id")
        owner_id = str(owner_raw).strip() if owner_raw is not None else ""
        has_cleanup_ticket = bool(flag.get("has_cleanup_ticket", False))
        both_paths_tested_in_ci = (
            bool(flag.get("both_paths_tested_in_ci", True))
            if flag.get("both_paths_tested_in_ci") is not None
            else True
        )

        if flag_type in ("RELEASE", "EXPERIMENT"):
            active_release_flags_count += 1
            if (
                rollout_pct == 100.0 and age_days > max_rollout_flag_ttl_days
            ) or age_days > max_rollout_flag_ttl_days * 2:
                zombie_flag_ids.append(flag_id)
                if not has_cleanup_ticket:
                    missing_cleanup_ticket_flag_ids.append(flag_id)

        if not owner_id:
            unowned_flag_ids.append(flag_id)

        if not both_paths_tested_in_ci:
            untested_branch_flag_ids.append(flag_id)

    combinatorial_explosion_risk = bool(
        active_release_flags_count > max_active_release_flags
    )

    if untested_branch_flag_ids:
        recommendations.append(
            f"Add dual-path (ON/OFF) CI automated tests for feature flags: {', '.join(untested_branch_flag_ids)}."
        )
    if unowned_flag_ids:
        recommendations.append(
            f"Assign explicit engineering owners to orphaned feature flags: {', '.join(unowned_flag_ids)}."
        )
    if zombie_flag_ids:
        recommendations.append(
            f"Retire stale/100%-rolled-out zombie feature flags from codebase: {', '.join(zombie_flag_ids)}."
        )
    if missing_cleanup_ticket_flag_ids:
        recommendations.append(
            f"Create backlog cleanup tickets for zombie feature flags: {', '.join(missing_cleanup_ticket_flag_ids)}."
        )
    if combinatorial_explosion_risk:
        recommendations.append(
            f"Reduce active release/experiment feature flags ({active_release_flags_count} > {max_active_release_flags}) to limit combinatorial test matrix explosion."
        )

    if (
        untested_branch_flag_ids
        or unowned_flag_ids
        or len(zombie_flag_ids) >= 2
    ):
        flag_governance_status = "CRITICAL"
    elif zombie_flag_ids or combinatorial_explosion_risk:
        flag_governance_status = "WARNING"
    else:
        flag_governance_status = "CLEAN"

    return {
        "total_flags": len(valid_flags),
        "active_release_flags_count": active_release_flags_count,
        "combinatorial_explosion_risk": combinatorial_explosion_risk,
        "zombie_flag_ids": zombie_flag_ids,
        "unowned_flag_ids": unowned_flag_ids,
        "untested_branch_flag_ids": untested_branch_flag_ids,
        "missing_cleanup_ticket_flag_ids": missing_cleanup_ticket_flag_ids,
        "flag_governance_status": flag_governance_status,
        "is_flag_hygiene_compliant": flag_governance_status == "CLEAN",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene = staticmethod(
    audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene
)


def audit_requirements_volatility_churn_and_scope_freeze_breaches(
    requirements: Any,
    *,
    baseline_locked_count: int,
    max_churn_rate_pct: float = 15.0,
) -> Dict[str, object]:
    """Auditoría PMBOK 5.6 (Control Scope) y 4.6: churn de requerimientos.

    Mide la tasa de churn frente a la línea base bloqueada, separa los
    cambios posteriores al scope freeze con y sin aprobación de CCB, y
    determina el estado de volatilidad del baseline.
    """
    entries = requirements if isinstance(requirements, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    churn_actions = {"ADDED", "MODIFIED", "DELETED"}
    unapproved_post_freeze_req_ids: List[str] = []
    approved_post_freeze_req_ids: List[str] = []
    churned_requirements_count = 0
    net_story_points_delta = 0.0

    for item in rows:
        req_id = item.get("req_id")
        change_action = item.get("change_action", "UNCHANGED")
        story_delta = item.get("story_points_delta", 0.0)

        if story_delta is not None and isinstance(story_delta, (int, float)):
            net_story_points_delta += story_delta

        if change_action in churn_actions:
            churned_requirements_count += 1

            if item.get("modified_after_scope_freeze", False) is True:
                if item.get("has_ccb_approval_cr_id", True) is True:
                    approved_post_freeze_req_ids.append(req_id)
                else:
                    unapproved_post_freeze_req_ids.append(req_id)

    net_story_points_delta = round(net_story_points_delta, 2)

    if baseline_locked_count > 0:
        requirements_churn_rate_pct = round(
            (churned_requirements_count / baseline_locked_count) * 100.0, 2
        )
    else:
        requirements_churn_rate_pct = 0.0

    if (
        unapproved_post_freeze_req_ids
        or requirements_churn_rate_pct > max_churn_rate_pct * 2
    ):
        volatility_governance_status = "SCOPE_FREEZE_VIOLATION"
    elif (
        requirements_churn_rate_pct > max_churn_rate_pct
        or approved_post_freeze_req_ids
    ):
        volatility_governance_status = "WARNING"
    else:
        volatility_governance_status = "STABLE_BASELINE"

    recommendations: List[str] = []
    if unapproved_post_freeze_req_ids:
        recommendations.append(
            "Ratify with the CCB or revert post-freeze changes without approved CR: "
            + ", ".join(str(r) for r in unapproved_post_freeze_req_ids)
        )
    if approved_post_freeze_req_ids:
        recommendations.append(
            "Track post-freeze changes with approved CRs under control scope: "
            + ", ".join(str(r) for r in approved_post_freeze_req_ids)
        )
    if requirements_churn_rate_pct > max_churn_rate_pct:
        recommendations.append(
            f"Stabilize requirements baseline: churn rate {requirements_churn_rate_pct}% exceeds max {max_churn_rate_pct}%"
        )
    if net_story_points_delta > 0:
        recommendations.append(
            f"Verify CCB capacity impact for +{net_story_points_delta} net story points"
        )
    elif net_story_points_delta < 0:
        recommendations.append(
            f"Verify CCB capacity impact for {-net_story_points_delta} removed story points"
        )

    return {
        "total_requirements": len(rows),
        "churned_requirements_count": churned_requirements_count,
        "requirements_churn_rate_pct": requirements_churn_rate_pct,
        "net_story_points_delta": net_story_points_delta,
        "unapproved_post_freeze_req_ids": unapproved_post_freeze_req_ids,
        "approved_post_freeze_req_ids": approved_post_freeze_req_ids,
        "volatility_governance_status": volatility_governance_status,
        "is_baseline_stable": volatility_governance_status == "STABLE_BASELINE",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_requirements_volatility_churn_and_scope_freeze_breaches = staticmethod(
    audit_requirements_volatility_churn_and_scope_freeze_breaches
)


def audit_architectural_fitness_functions_and_coupling_drift(
    components: Any,
    *,
    max_instability_index: float = 0.8,
    max_distance_from_main_sequence: float = 0.35,
) -> Dict[str, object]:
    """Auditoría PMBOK 8.2 y 4.6: fitness functions arquitectónicas.

    Calcula por componente el índice de inestabilidad
    (ce / (ca + ce)) y la distancia a la secuencia principal
    (abs(abstractness + inestabilidad - 1)), detectando ciclos,
    fitness fallidas, core inestable y zonas de dolor/inutilidad.
    """
    entries = components if isinstance(components, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    cyclic_dependency_component_ids: List[str] = []
    failed_fitness_component_ids: List[str] = []
    unstable_core_component_ids: List[str] = []
    zone_of_pain_or_uselessness_ids: List[str] = []
    observed_instabilities: List[float] = []

    for item in rows:
        component_id = item.get("component_id")
        ca = item.get("afferent_coupling_ca", 0)
        ce = item.get("efferent_coupling_ce", 0)
        abstractness = item.get("abstractness_ratio", 0.0)

        ca_val = ca if isinstance(ca, (int, float)) and ca >= 0 else 0
        ce_val = ce if isinstance(ce, (int, float)) and ce >= 0 else 0
        abstractness_val = (
            abstractness if isinstance(abstractness, (int, float)) else 0.0
        )

        if ca_val + ce_val > 0:
            instability_index = round(ce_val / (ca_val + ce_val), 2)
        else:
            instability_index = 0.0
        observed_instabilities.append(instability_index)

        distance_from_main_sequence = round(
            abs(abstractness_val + instability_index - 1.0), 2
        )

        if item.get("has_cyclic_dependency", False) is True:
            cyclic_dependency_component_ids.append(component_id)

        if item.get("fitness_function_passed", True) is not True:
            failed_fitness_component_ids.append(component_id)

        if (
            item.get("is_core_domain", False) is True
            and instability_index > max_instability_index
        ):
            unstable_core_component_ids.append(component_id)

        if distance_from_main_sequence > max_distance_from_main_sequence:
            zone_of_pain_or_uselessness_ids.append(component_id)

    max_instability_observed = max(observed_instabilities) if observed_instabilities else 0.0

    if (
        cyclic_dependency_component_ids
        or failed_fitness_component_ids
        or unstable_core_component_ids
    ):
        architecture_governance_status = "EROSION_BLOCKED"
    elif zone_of_pain_or_uselessness_ids:
        architecture_governance_status = "DRIFT_WARNING"
    else:
        architecture_governance_status = "FITNESS_HEALTHY"

    return {
        "total_components_evaluated": len(rows),
        "cyclic_dependency_component_ids": cyclic_dependency_component_ids,
        "failed_fitness_component_ids": failed_fitness_component_ids,
        "unstable_core_component_ids": unstable_core_component_ids,
        "zone_of_pain_or_uselessness_ids": zone_of_pain_or_uselessness_ids,
        "max_instability_observed": max_instability_observed,
        "architecture_governance_status": architecture_governance_status,
        "is_architecture_compliant": architecture_governance_status == "FITNESS_HEALTHY",
    }


ProjectCCBService.audit_architectural_fitness_functions_and_coupling_drift = staticmethod(
    audit_architectural_fitness_functions_and_coupling_drift
)


def audit_api_backward_compatibility_and_contract_versioning(
    api_changes: list[dict[str, Any]],
    *,
    min_deprecation_notice_days: int = 30,
) -> dict[str, Any]:
    """PMI PMBOK §8.3 & §11.6 — CCB API Backward-Compatibility Contract, Breaking Schema Change & Consumer Versioning Gate Auditor."""
    valid_endpoints: list[dict[str, Any]] = []
    if isinstance(api_changes, (list, tuple)):
        for item in api_changes:
            if not isinstance(item, dict):
                continue
            eid = str(item.get("endpoint_id") or "").strip()
            if not eid:
                continue
            valid_endpoints.append({**item, "_eid": eid})

    if not valid_endpoints:
        return {
            "total_endpoints_evaluated": 0,
            "breaking_change_count": 0,
            "unversioned_breaking_change_ids": [],
            "failed_contract_test_ids": [],
            "insufficient_deprecation_window_ids": [],
            "contract_governance_status": "BACKWARD_COMPATIBLE_SAFE",
            "is_contract_gate_compliant": True,
            "recommendations": [],
        }

    breaking_change_count = 0
    unversioned_breaking_change_ids: list[str] = []
    failed_contract_test_ids: list[str] = []
    insufficient_deprecation_window_ids: list[str] = []

    for ep in valid_endpoints:
        eid = ep["_eid"]
        removes_field = bool(ep.get("removes_required_response_field", False))
        adds_param = bool(
            ep.get("adds_mandatory_request_parameter_without_default", False)
        )
        bumps_major = bool(ep.get("bumps_major_api_version", False))
        contract_passed = bool(ep.get("consumer_contract_tests_passed", True))
        notice_days = int(
            ep.get("deprecation_notice_days_provided", min_deprecation_notice_days)
            if ep.get("deprecation_notice_days_provided") is not None
            else min_deprecation_notice_days
        )

        is_breaking = removes_field or adds_param
        if is_breaking:
            breaking_change_count += 1
            if not bumps_major:
                unversioned_breaking_change_ids.append(eid)
            if notice_days < min_deprecation_notice_days:
                insufficient_deprecation_window_ids.append(eid)

        if not contract_passed:
            failed_contract_test_ids.append(eid)

    recommendations: list[str] = []
    if unversioned_breaking_change_ids:
        recommendations.append(
            f"Bump major API version or restore backward compatibility for breaking endpoint(s): {', '.join(unversioned_breaking_change_ids)}."
        )
    if failed_contract_test_ids:
        recommendations.append(
            f"Resolve failing consumer-driven contract tests before CCB sign-off on endpoint(s): {', '.join(failed_contract_test_ids)}."
        )
    if insufficient_deprecation_window_ids:
        recommendations.append(
            f"Extend consumer deprecation notice window to at least {min_deprecation_notice_days} days for breaking endpoint(s): {', '.join(insufficient_deprecation_window_ids)}."
        )

    if unversioned_breaking_change_ids or failed_contract_test_ids:
        contract_governance_status = "BREAKING_BLOCKED"
    elif insufficient_deprecation_window_ids:
        contract_governance_status = "DEPRECATION_WINDOW_WARNING"
    else:
        contract_governance_status = "BACKWARD_COMPATIBLE_SAFE"

    return {
        "total_endpoints_evaluated": len(valid_endpoints),
        "breaking_change_count": breaking_change_count,
        "unversioned_breaking_change_ids": unversioned_breaking_change_ids,
        "failed_contract_test_ids": failed_contract_test_ids,
        "insufficient_deprecation_window_ids": insufficient_deprecation_window_ids,
        "contract_governance_status": contract_governance_status,
        "is_contract_gate_compliant": contract_governance_status
        == "BACKWARD_COMPATIBLE_SAFE",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_api_backward_compatibility_and_contract_versioning = staticmethod(
    audit_api_backward_compatibility_and_contract_versioning
)


def audit_test_pyramid_balance_and_mutation_coverage_gate(
    suites: list[dict[str, Any]],
    *,
    min_unit_test_share_pct: float = 60.0,
    max_e2e_test_share_pct: float = 20.0,
    min_mutation_score_pct: float = 75.0,
    max_flaky_rate_pct: float = 2.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.2 & §8.3 — CCB Test Pyramid Balance, Flaky Test Quarantine & Mutation Coverage Gate Auditor."""
    valid_suites: list[dict[str, Any]] = []
    if isinstance(suites, (list, tuple)):
        for item in suites:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("suite_id") or "").strip()
            if not sid:
                continue
            valid_suites.append({**item, "_sid": sid})

    if not valid_suites:
        return {
            "total_suites_evaluated": 0,
            "ice_cream_cone_antipattern_suite_ids": [],
            "weak_mutation_coverage_suite_ids": [],
            "flaky_instability_suite_ids": [],
            "quality_pyramid_status": "PYRAMID_OPTIMAL",
            "is_test_pyramid_compliant": True,
            "recommendations": [],
        }

    ice_cream_cone_antipattern_suite_ids: list[str] = []
    weak_mutation_coverage_suite_ids: list[str] = []
    flaky_instability_suite_ids: list[str] = []

    for st in valid_suites:
        sid = st["_sid"]
        unit_cnt = max(0, int(st.get("unit_tests_count", 0) or 0))
        integ_cnt = max(0, int(st.get("integration_tests_count", 0) or 0))
        e2e_cnt = max(0, int(st.get("e2e_tests_count", 0) or 0))
        mut_score = float(
            st.get("mutation_kill_score_pct", 80.0)
            if st.get("mutation_kill_score_pct") is not None
            else 80.0
        )
        flaky_rate = max(0.0, float(st.get("flaky_tests_rate_pct", 0.0) or 0.0))

        total_tests = unit_cnt + integ_cnt + e2e_cnt
        if total_tests > 0:
            unit_share_pct = round((unit_cnt / total_tests) * 100.0, 2)
            e2e_share_pct = round((e2e_cnt / total_tests) * 100.0, 2)
        else:
            unit_share_pct = 0.0
            e2e_share_pct = 0.0

        if (
            total_tests == 0
            or unit_share_pct < min_unit_test_share_pct
            or e2e_share_pct > max_e2e_test_share_pct
        ):
            ice_cream_cone_antipattern_suite_ids.append(sid)

        if mut_score < min_mutation_score_pct:
            weak_mutation_coverage_suite_ids.append(sid)

        if flaky_rate > max_flaky_rate_pct:
            flaky_instability_suite_ids.append(sid)

    recommendations: list[str] = []
    if weak_mutation_coverage_suite_ids:
        recommendations.append(
            f"Strengthen assertion quality to reach >= {min_mutation_score_pct}% mutation kill score in suite(s): {', '.join(weak_mutation_coverage_suite_ids)}."
        )
    if flaky_instability_suite_ids:
        recommendations.append(
            f"Quarantine and deterministic-refactor flaky tests exceeding {max_flaky_rate_pct}% threshold in suite(s): {', '.join(flaky_instability_suite_ids)}."
        )
    if ice_cream_cone_antipattern_suite_ids:
        recommendations.append(
            f"Rebalance test pyramid (>= {min_unit_test_share_pct}% unit, <= {max_e2e_test_share_pct}% E2E) in suite(s): {', '.join(ice_cream_cone_antipattern_suite_ids)}."
        )

    if weak_mutation_coverage_suite_ids or flaky_instability_suite_ids:
        quality_pyramid_status = "QUALITY_GATE_BLOCKED"
    elif ice_cream_cone_antipattern_suite_ids:
        quality_pyramid_status = "PYRAMID_IMBALANCE_WARNING"
    else:
        quality_pyramid_status = "PYRAMID_OPTIMAL"

    return {
        "total_suites_evaluated": len(valid_suites),
        "ice_cream_cone_antipattern_suite_ids": ice_cream_cone_antipattern_suite_ids,
        "weak_mutation_coverage_suite_ids": weak_mutation_coverage_suite_ids,
        "flaky_instability_suite_ids": flaky_instability_suite_ids,
        "quality_pyramid_status": quality_pyramid_status,
        "is_test_pyramid_compliant": quality_pyramid_status == "PYRAMID_OPTIMAL",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_test_pyramid_balance_and_mutation_coverage_gate = staticmethod(
    audit_test_pyramid_balance_and_mutation_coverage_gate
)


def audit_supply_chain_slsa_provenance_and_artifact_signing(
    artifacts: list[dict[str, Any]],
    *,
    min_slsa_level: int = 3,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §12.3 — CCB Supply Chain SLSA Provenance Level, Artifact Cryptographic Signature & Hermetic Build Isolation Auditor."""
    valid_artifacts: list[dict[str, Any]] = []
    if isinstance(artifacts, (list, tuple)):
        for item in artifacts:
            if not isinstance(item, dict):
                continue
            aid = str(item.get("artifact_id") or "").strip()
            if not aid:
                continue
            valid_artifacts.append({**item, "_aid": aid})

    if not valid_artifacts:
        return {
            "total_artifacts_evaluated": 0,
            "unsigned_artifact_ids": [],
            "insufficient_slsa_artifact_ids": [],
            "unpinned_digest_artifact_ids": [],
            "supply_chain_status": "SLSA_VERIFIED_SECURE",
            "is_slsa_supply_chain_compliant": True,
            "recommendations": [],
        }

    unsigned_artifact_ids: list[str] = []
    insufficient_slsa_artifact_ids: list[str] = []
    unpinned_digest_artifact_ids: list[str] = []

    for art in valid_artifacts:
        aid = art["_aid"]
        slsa_lvl = max(0, int(art.get("slsa_provenance_level", 0) or 0))
        is_signed = bool(art.get("is_cryptographically_signed_cosign", False))
        is_hermetic = bool(art.get("built_in_ephemeral_hermetic_runner", False))
        has_pinned = bool(art.get("has_pinned_dependency_digests", True))

        if not is_signed:
            unsigned_artifact_ids.append(aid)
        if slsa_lvl < min_slsa_level or not is_hermetic:
            insufficient_slsa_artifact_ids.append(aid)
        if not has_pinned:
            unpinned_digest_artifact_ids.append(aid)

    recommendations: list[str] = []
    if unsigned_artifact_ids:
        recommendations.append(
            f"Sign build artifacts cryptographically with Cosign/Sigstore transparency log for artifact(s): {', '.join(unsigned_artifact_ids)}."
        )
    if insufficient_slsa_artifact_ids:
        recommendations.append(
            f"Enforce ephemeral hermetic runners and SLSA Provenance Level >= {min_slsa_level} for artifact(s): {', '.join(insufficient_slsa_artifact_ids)}."
        )
    if unpinned_digest_artifact_ids:
        recommendations.append(
            f"Pin base images and dependencies by immutable SHA-256 digests for artifact(s): {', '.join(unpinned_digest_artifact_ids)}."
        )

    if unsigned_artifact_ids or insufficient_slsa_artifact_ids:
        supply_chain_status = "PROVENANCE_TAMPER_RISK"
    elif unpinned_digest_artifact_ids:
        supply_chain_status = "DIGEST_PINNING_WARNING"
    else:
        supply_chain_status = "SLSA_VERIFIED_SECURE"

    return {
        "total_artifacts_evaluated": len(valid_artifacts),
        "unsigned_artifact_ids": unsigned_artifact_ids,
        "insufficient_slsa_artifact_ids": insufficient_slsa_artifact_ids,
        "unpinned_digest_artifact_ids": unpinned_digest_artifact_ids,
        "supply_chain_status": supply_chain_status,
        "is_slsa_supply_chain_compliant": supply_chain_status
        == "SLSA_VERIFIED_SECURE",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_supply_chain_slsa_provenance_and_artifact_signing = staticmethod(
    audit_supply_chain_slsa_provenance_and_artifact_signing
)


def audit_ecab_emergency_change_retroactive_ratification_and_abuse(
    changes: list[dict[str, Any]],
    *,
    max_retroactive_ratification_hours: float = 48.0,
    max_emergency_change_ratio_pct: float = 15.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.6 — CCB Emergency Change Advisory Board (ECAB) Retroactive Ratification SLA, Break-Glass Abuse & Post-Implementation Review Auditor."""
    valid_changes: list[dict[str, Any]] = []
    if isinstance(changes, (list, tuple)):
        for item in changes:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("change_id") or "").strip()
            if not cid:
                continue
            valid_changes.append({**item, "_cid": cid})

    if not valid_changes:
        return {
            "total_changes_evaluated": 0,
            "emergency_changes_count": 0,
            "emergency_change_ratio_pct": 0.0,
            "unratified_or_late_ecab_ids": [],
            "unjustified_break_glass_ids": [],
            "missing_pir_emergency_ids": [],
            "ecab_governance_status": "ECAB_GOVERNED",
            "is_ecab_compliant": True,
            "recommendations": [],
        }

    unratified_or_late_ecab_ids: list[str] = []
    unjustified_break_glass_ids: list[str] = []
    missing_pir_emergency_ids: list[str] = []
    emergency_changes_count = 0

    for chg in valid_changes:
        cid = chg["_cid"]
        is_emerg = bool(chg.get("is_emergency_break_glass", False))
        if not is_emerg:
            continue
        emergency_changes_count += 1
        hours_to_rat = max(
            0.0, float(chg.get("hours_to_ecab_ratification", 0.0) or 0.0)
        )
        has_signoff = bool(chg.get("has_ecab_retroactive_signoff", True))
        has_sev1 = bool(chg.get("has_linked_sev1_incident_id", True))
        has_pir = bool(
            chg.get("has_post_implementation_review_completed", True)
        )

        if (
            not has_signoff
            or hours_to_rat > max_retroactive_ratification_hours
        ):
            unratified_or_late_ecab_ids.append(cid)
        if not has_sev1:
            unjustified_break_glass_ids.append(cid)
        if not has_pir:
            missing_pir_emergency_ids.append(cid)

    total_changes = len(valid_changes)
    emergency_change_ratio_pct = (
        round((emergency_changes_count / total_changes) * 100.0, 2)
        if total_changes > 0
        else 0.0
    )

    recommendations: list[str] = []
    if unratified_or_late_ecab_ids:
        recommendations.append(
            f"Convene ECAB for retroactive sign-off within <= {max_retroactive_ratification_hours}h SLA for emergency change(s): {', '.join(unratified_or_late_ecab_ids)}."
        )
    if unjustified_break_glass_ids:
        recommendations.append(
            f"Enforce linked SEV-1 incident justification to prevent break-glass CCB bypass abuse on change(s): {', '.join(unjustified_break_glass_ids)}."
        )
    if missing_pir_emergency_ids:
        recommendations.append(
            f"Complete mandatory Post-Implementation Review (PIR) for emergency change(s): {', '.join(missing_pir_emergency_ids)}."
        )
    if emergency_change_ratio_pct > max_emergency_change_ratio_pct:
        recommendations.append(
            f"Reduce emergency change ratio ({emergency_change_ratio_pct}% > {max_emergency_change_ratio_pct}% max) by tightening standard CCB planning cadence."
        )

    if unratified_or_late_ecab_ids or unjustified_break_glass_ids:
        ecab_governance_status = "ECAB_BYPASS_ABUSE_DETECTED"
    elif (
        missing_pir_emergency_ids
        or emergency_change_ratio_pct > max_emergency_change_ratio_pct
    ):
        ecab_governance_status = "EMERGENCY_RATIO_OR_PIR_WARNING"
    else:
        ecab_governance_status = "ECAB_GOVERNED"

    return {
        "total_changes_evaluated": total_changes,
        "emergency_changes_count": emergency_changes_count,
        "emergency_change_ratio_pct": emergency_change_ratio_pct,
        "unratified_or_late_ecab_ids": unratified_or_late_ecab_ids,
        "unjustified_break_glass_ids": unjustified_break_glass_ids,
        "missing_pir_emergency_ids": missing_pir_emergency_ids,
        "ecab_governance_status": ecab_governance_status,
        "is_ecab_compliant": ecab_governance_status == "ECAB_GOVERNED",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_ecab_emergency_change_retroactive_ratification_and_abuse = staticmethod(
    audit_ecab_emergency_change_retroactive_ratification_and_abuse
)


def audit_release_freeze_blackout_window_and_change_collisions(
    deployments: list[dict[str, Any]],
    *,
    max_concurrent_shared_infra_changes: int = 1,
) -> dict[str, Any]:
    """PMI PMBOK §8.3 & §4.6 — CCB Release Freeze Window, Blackout Period Exception Approval & Change Collision Auditor."""
    valid_deployments: list[dict[str, Any]] = []
    if isinstance(deployments, (list, tuple)):
        for item in deployments:
            if not isinstance(item, dict):
                continue
            did = str(item.get("deployment_id") or "").strip()
            if not did:
                continue
            valid_deployments.append({**item, "_did": did})

    if not valid_deployments:
        return {
            "total_deployments_evaluated": 0,
            "unauthorized_blackout_deployment_ids": [],
            "collision_hazard_deployment_ids": [],
            "unattended_rollback_deployment_ids": [],
            "release_window_status": "RELEASE_WINDOW_SAFE",
            "is_release_window_compliant": True,
            "recommendations": [],
        }

    unauthorized_blackout_deployment_ids: list[str] = []
    collision_hazard_deployment_ids: list[str] = []
    unattended_rollback_deployment_ids: list[str] = []

    for dep in valid_deployments:
        did = dep["_did"]
        is_blackout = bool(dep.get("is_during_blackout_freeze_window", False))
        has_waiver = bool(dep.get("has_vp_exception_waiver_signed", False))
        concurrent_cnt = int(
            dep.get("concurrent_shared_infra_changes_count", 1)
            if dep.get("concurrent_shared_infra_changes_count") is not None
            else 1
        )
        has_commander = bool(
            dep.get("has_dedicated_rollback_commander_on_duty", True)
        )

        if is_blackout and not has_waiver:
            unauthorized_blackout_deployment_ids.append(did)
        if concurrent_cnt > max_concurrent_shared_infra_changes:
            collision_hazard_deployment_ids.append(did)
        if not has_commander:
            unattended_rollback_deployment_ids.append(did)

    recommendations: list[str] = []
    if unauthorized_blackout_deployment_ids:
        recommendations.append(
            f"Block deployments during release freeze blackout window or obtain signed VP exception waiver for deployment(s): {', '.join(unauthorized_blackout_deployment_ids)}."
        )
    if unattended_rollback_deployment_ids:
        recommendations.append(
            f"Assign dedicated on-duty rollback commander prior to executing deployment(s): {', '.join(unattended_rollback_deployment_ids)}."
        )
    if collision_hazard_deployment_ids:
        recommendations.append(
            f"Serialize concurrent shared-infrastructure changes (<= {max_concurrent_shared_infra_changes} at a time) for deployment(s): {', '.join(collision_hazard_deployment_ids)}."
        )

    if (
        unauthorized_blackout_deployment_ids
        or unattended_rollback_deployment_ids
    ):
        release_window_status = "FREEZE_OR_COMMAND_BREACH"
    elif collision_hazard_deployment_ids:
        release_window_status = "CHANGE_COLLISION_WARNING"
    else:
        release_window_status = "RELEASE_WINDOW_SAFE"

    return {
        "total_deployments_evaluated": len(valid_deployments),
        "unauthorized_blackout_deployment_ids": unauthorized_blackout_deployment_ids,
        "collision_hazard_deployment_ids": collision_hazard_deployment_ids,
        "unattended_rollback_deployment_ids": unattended_rollback_deployment_ids,
        "release_window_status": release_window_status,
        "is_release_window_compliant": release_window_status
        == "RELEASE_WINDOW_SAFE",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_release_freeze_blackout_window_and_change_collisions = staticmethod(
    audit_release_freeze_blackout_window_and_change_collisions
)


def audit_query_performance_n_plus_one_and_full_scan_gate(
    queries: list[dict[str, Any]],
    *,
    max_p99_latency_ms: float = 200.0,
    max_rows_scanned_to_returned_ratio: float = 50.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.2 & §8.3 — CCB Database Query N+1 Regression, Missing Index Full-Scan & Latency P99 Gate Auditor."""
    valid_queries: list[dict[str, Any]] = []
    if isinstance(queries, (list, tuple)):
        for item in queries:
            if not isinstance(item, dict):
                continue
            qid = str(item.get("query_id") or "").strip()
            if not qid:
                continue
            valid_queries.append({**item, "_qid": qid})

    if not valid_queries:
        return {
            "total_queries_evaluated": 0,
            "n_plus_one_or_full_scan_query_ids": [],
            "p99_latency_breach_query_ids": [],
            "inefficient_selectivity_query_ids": [],
            "query_gate_status": "QUERY_PLAN_OPTIMAL",
            "is_query_performance_compliant": True,
            "recommendations": [],
        }

    n_plus_one_or_full_scan_query_ids: list[str] = []
    p99_latency_breach_query_ids: list[str] = []
    inefficient_selectivity_query_ids: list[str] = []

    for qry in valid_queries:
        qid = qry["_qid"]
        n_plus_one = bool(qry.get("triggers_n_plus_one_loop", False))
        full_scan = bool(
            qry.get("uses_full_table_seq_scan_on_large_table", False)
        )
        p99_ms = float(
            qry.get("p99_execution_ms", 25.0)
            if qry.get("p99_execution_ms") is not None
            else 25.0
        )
        scan_ratio = float(
            qry.get("rows_scanned_to_returned_ratio", 1.0)
            if qry.get("rows_scanned_to_returned_ratio") is not None
            else 1.0
        )

        if n_plus_one or full_scan:
            n_plus_one_or_full_scan_query_ids.append(qid)
        if p99_ms > max_p99_latency_ms:
            p99_latency_breach_query_ids.append(qid)
        if scan_ratio > max_rows_scanned_to_returned_ratio:
            inefficient_selectivity_query_ids.append(qid)

    recommendations: list[str] = []
    if n_plus_one_or_full_scan_query_ids:
        recommendations.append(
            f"Eliminate ORM N+1 lazy-loading loops (use `joinedload`/`selectinload`) and add covering B-Tree indexes for query(ies): {', '.join(n_plus_one_or_full_scan_query_ids)}."
        )
    if p99_latency_breach_query_ids:
        recommendations.append(
            f"Optimize execution plans to bring P99 latency within <= {max_p99_latency_ms} ms for query(ies): {', '.join(p99_latency_breach_query_ids)}."
        )
    if inefficient_selectivity_query_ids:
        recommendations.append(
            f"Refine composite index selectivity to reduce rows-scanned-to-returned ratio (<= {max_rows_scanned_to_returned_ratio}) for query(ies): {', '.join(inefficient_selectivity_query_ids)}."
        )

    if n_plus_one_or_full_scan_query_ids or p99_latency_breach_query_ids:
        query_gate_status = "PERFORMANCE_REGRESSION_BLOCKED"
    elif inefficient_selectivity_query_ids:
        query_gate_status = "SELECTIVITY_INDEX_WARNING"
    else:
        query_gate_status = "QUERY_PLAN_OPTIMAL"

    return {
        "total_queries_evaluated": len(valid_queries),
        "n_plus_one_or_full_scan_query_ids": n_plus_one_or_full_scan_query_ids,
        "p99_latency_breach_query_ids": p99_latency_breach_query_ids,
        "inefficient_selectivity_query_ids": inefficient_selectivity_query_ids,
        "query_gate_status": query_gate_status,
        "is_query_performance_compliant": query_gate_status
        == "QUERY_PLAN_OPTIMAL",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_query_performance_n_plus_one_and_full_scan_gate = staticmethod(
    audit_query_performance_n_plus_one_and_full_scan_gate
)


def audit_feature_flag_stale_toggle_debt_and_kill_switch(
    feature_flags: list[dict[str, Any]],
    *,
    max_toggle_age_days: int | float = 45,
    max_kill_switch_propagation_seconds: float = 30.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.3 & §11.6 — CCB Feature Flag Stale Toggle Technical Debt, Blast-Radius Ownership & Kill-Switch Latency Auditor."""
    valid_flags: list[dict[str, Any]] = []
    if isinstance(feature_flags, (list, tuple)):
        for item in feature_flags:
            if not isinstance(item, dict):
                continue
            fkey = str(item.get("flag_key") or "").strip()
            if not fkey:
                continue
            valid_flags.append({**item, "_fkey": fkey})

    if not valid_flags:
        return {
            "evaluated_flags_count": 0,
            "broken_kill_switch_or_unowned_flag_keys": [],
            "stale_or_entangled_flag_keys": [],
            "feature_flag_governance_status": "FLAG_HYGIENE_OPTIMAL",
            "is_feature_flag_compliant": True,
            "recommendations": [],
        }

    broken_kill_switch_or_unowned_flag_keys: list[str] = []
    stale_or_entangled_flag_keys: list[str] = []

    for flg in valid_flags:
        fkey = flg["_fkey"]
        raw_age = flg.get("age_days_since_100pct_rollout")
        age_days = float(raw_age if raw_age is not None else 0.0)
        is_kill_switch = bool(flg.get("is_permanent_ops_kill_switch", False))
        raw_prop = flg.get("kill_switch_propagation_seconds")
        prop_sec = float(raw_prop if raw_prop is not None else 5.0)
        has_owner_and_ticket = bool(
            flg.get("has_assigned_owner_and_cleanup_ticket", True)
        )
        raw_nested = flg.get("nested_flag_dependencies_count")
        nested_cnt = int(raw_nested if raw_nested is not None else 0)

        if (
            is_kill_switch
            and prop_sec > max_kill_switch_propagation_seconds
        ) or not has_owner_and_ticket:
            broken_kill_switch_or_unowned_flag_keys.append(fkey)

        if (
            not is_kill_switch and age_days > max_toggle_age_days
        ) or nested_cnt > 1:
            stale_or_entangled_flag_keys.append(fkey)

    recommendations: list[str] = []
    if broken_kill_switch_or_unowned_flag_keys:
        recommendations.append(
            f"Assign explicit owner/cleanup ticket and ensure ops kill-switch propagation <= {max_kill_switch_propagation_seconds}s for flag(s): {', '.join(broken_kill_switch_or_unowned_flag_keys)}."
        )
    if stale_or_entangled_flag_keys:
        recommendations.append(
            f"Retire stale release toggles (> {max_toggle_age_days} days post-100% rollout) and decouple nested flag dependencies (> 1) for flag(s): {', '.join(stale_or_entangled_flag_keys)}."
        )

    if broken_kill_switch_or_unowned_flag_keys:
        feature_flag_governance_status = "FLAG_KILL_SWITCH_OR_OWNERSHIP_BREACH"
    elif stale_or_entangled_flag_keys:
        feature_flag_governance_status = "FLAG_STALE_TOGGLE_DEBT_WARNING"
    else:
        feature_flag_governance_status = "FLAG_HYGIENE_OPTIMAL"

    return {
        "evaluated_flags_count": len(valid_flags),
        "broken_kill_switch_or_unowned_flag_keys": broken_kill_switch_or_unowned_flag_keys,
        "stale_or_entangled_flag_keys": stale_or_entangled_flag_keys,
        "feature_flag_governance_status": feature_flag_governance_status,
        "is_feature_flag_compliant": feature_flag_governance_status
        == "FLAG_HYGIENE_OPTIMAL",
        "recommendations": recommendations,
    }


ProjectCCBService.audit_feature_flag_stale_toggle_debt_and_kill_switch = staticmethod(
    audit_feature_flag_stale_toggle_debt_and_kill_switch
)


def audit_canary_rollout_traffic_shift_and_auto_rollback_gate(
    canary_deployments: Sequence[Mapping[str, Any]] | None,
    *,
    min_bake_time_minutes_per_stage: int | float = 30,
    max_canary_5xx_error_rate_pct: float = 0.5,
) -> dict[str, Any]:
    """PMI PMBOK §8.3 & §11.6 — CCB Canary Rollout Progressive Traffic Shifting, Error-Budget Burn Alert & Auto-Rollback Gate Auditor."""
    valid_deployments = [
        dep
        for dep in (canary_deployments or [])
        if isinstance(dep, Mapping) and str(dep.get("deployment_id") or "").strip()
    ]

    unarmed_rollback_or_error_spike_deployment_ids: list[str] = []
    rushed_bake_or_aggressive_step_deployment_ids: list[str] = []

    for dep in valid_deployments:
        did = str(dep.get("deployment_id")).strip()
        initial_step_pct = float(
            dep.get("initial_traffic_step_pct", 5.0)
            if dep.get("initial_traffic_step_pct") is not None
            else 5.0
        )
        bake_minutes = float(
            dep.get("bake_time_minutes_observed", 30)
            if dep.get("bake_time_minutes_observed") is not None
            else 30
        )
        error_rate_pct = float(
            dep.get("observed_5xx_error_rate_pct", 0.05)
            if dep.get("observed_5xx_error_rate_pct") is not None
            else 0.05
        )
        rollback_armed = bool(
            dep.get("automated_rollback_hook_armed", True)
            if dep.get("automated_rollback_hook_armed") is not None
            else True
        )
        signals_compared = bool(
            dep.get("baseline_golden_signals_compared", True)
            if dep.get("baseline_golden_signals_compared") is not None
            else True
        )

        if (
            not rollback_armed
            or error_rate_pct > max_canary_5xx_error_rate_pct
        ):
            unarmed_rollback_or_error_spike_deployment_ids.append(did)

        if (
            bake_minutes < min_bake_time_minutes_per_stage
            or initial_step_pct > 25.0
            or not signals_compared
        ):
            rushed_bake_or_aggressive_step_deployment_ids.append(did)

    if unarmed_rollback_or_error_spike_deployment_ids:
        canary_governance_status = "CANARY_ROLLBACK_OR_ERROR_SPIKE_BREACH"
    elif rushed_bake_or_aggressive_step_deployment_ids:
        canary_governance_status = "CANARY_BAKE_TIME_OR_STEP_WARNING"
    else:
        canary_governance_status = "CANARY_PROGRESSIVE_DELIVERY_OPTIMAL"

    return {
        "evaluated_deployments_count": len(valid_deployments),
        "unarmed_rollback_or_error_spike_deployment_ids": unarmed_rollback_or_error_spike_deployment_ids,
        "rushed_bake_or_aggressive_step_deployment_ids": rushed_bake_or_aggressive_step_deployment_ids,
        "canary_governance_status": canary_governance_status,
        "is_canary_rollout_compliant": canary_governance_status
        == "CANARY_PROGRESSIVE_DELIVERY_OPTIMAL",
    }


ProjectCCBService.audit_canary_rollout_traffic_shift_and_auto_rollback_gate = staticmethod(
    audit_canary_rollout_traffic_shift_and_auto_rollback_gate
)


def audit_secret_scanning_pre_receive_and_leak_revocation(
    repositories: Sequence[Mapping[str, Any]] | None,
    *,
    max_revocation_minutes_sla: float = 15.0,
    max_false_positive_bypass_rate_pct: float = 5.0,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §8.3 — CCB Secret Scanning Pre-Receive Gate, High-Entropy Token Leak & Git History Revocation SLA Auditor."""
    valid_repositories = [
        repo
        for repo in (repositories or [])
        if isinstance(repo, Mapping) and str(repo.get("repo_id") or "").strip()
    ]

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _num(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    active_leak_or_unprotected_repo_ids: list[str] = []
    slow_revocation_or_high_bypass_repo_ids: list[str] = []

    for repo in valid_repositories:
        rid = str(repo.get("repo_id")).strip()
        hook_enforced = _bool(
            repo.get("pre_receive_secret_hook_enforced"), True
        )
        unrevoked_leaks = _num(
            repo.get("unrevoked_leaked_secrets_count"), 0.0
        )
        revocation_minutes = _num(
            repo.get("max_observed_revocation_minutes"), 5.0
        )
        bypass_rate_pct = _num(
            repo.get("push_bypass_rate_pct"), 1.0
        )
        history_purged = _bool(
            repo.get("git_history_purged_on_leak"), True
        )

        if (
            not hook_enforced
            or unrevoked_leaks > 0
            or not history_purged
        ):
            active_leak_or_unprotected_repo_ids.append(rid)

        if (
            revocation_minutes > max_revocation_minutes_sla
            or bypass_rate_pct > max_false_positive_bypass_rate_pct
        ):
            slow_revocation_or_high_bypass_repo_ids.append(rid)

    if active_leak_or_unprotected_repo_ids:
        secret_scanning_governance_status = "SECRET_LEAK_OR_HOOK_BYPASS_BREACH"
    elif slow_revocation_or_high_bypass_repo_ids:
        secret_scanning_governance_status = (
            "SECRET_REVOCATION_SLA_OR_BYPASS_WARNING"
        )
    else:
        secret_scanning_governance_status = "SECRET_HYGIENE_ZERO_LEAK_OPTIMAL"

    return {
        "evaluated_repos_count": len(valid_repositories),
        "active_leak_or_unprotected_repo_ids": active_leak_or_unprotected_repo_ids,
        "slow_revocation_or_high_bypass_repo_ids": slow_revocation_or_high_bypass_repo_ids,
        "secret_scanning_governance_status": secret_scanning_governance_status,
        "is_secret_scanning_compliant": secret_scanning_governance_status
        == "SECRET_HYGIENE_ZERO_LEAK_OPTIMAL",
    }


ProjectCCBService.audit_secret_scanning_pre_receive_and_leak_revocation = staticmethod(
    audit_secret_scanning_pre_receive_and_leak_revocation
)


def audit_iac_terraform_drift_and_state_lock_hygiene(
    iac_workspaces: Sequence[Mapping[str, Any]] | None,
    *,
    max_drift_reconciliation_hours: float = 24.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.3 & §11.6 — CCB Infrastructure-as-Code (IaC) Terraform Plan Drift, Unmanaged Manual Mutation & State Lock Hygiene Auditor."""
    valid_workspaces = [
        ws
        for ws in (iac_workspaces or [])
        if isinstance(ws, Mapping) and str(ws.get("workspace_id") or "").strip()
    ]

    unlocked_state_or_console_mutation_workspace_ids: list[str] = []
    unreconciled_drift_workspace_ids: list[str] = []

    for ws in valid_workspaces:
        wid = str(ws.get("workspace_id")).strip()
        console_mutations = int(
            ws.get("unmanaged_console_mutations_count", 0)
            if ws.get("unmanaged_console_mutations_count") is not None
            else 0
        )
        drifted_resources = int(
            ws.get("drifted_resources_count", 0)
            if ws.get("drifted_resources_count") is not None
            else 0
        )
        hours_since_drift = float(
            ws.get("hours_since_drift_detected", 0.0)
            if ws.get("hours_since_drift_detected") is not None
            else 0.0
        )
        state_locked_encrypted = bool(
            ws.get("remote_state_locking_and_encryption_enabled", True)
            if ws.get("remote_state_locking_and_encryption_enabled") is not None
            else True
        )
        destructive_requires_ccb = bool(
            ws.get("destructive_plan_requires_ccb_approval", True)
            if ws.get("destructive_plan_requires_ccb_approval") is not None
            else True
        )

        if (
            not state_locked_encrypted
            or not destructive_requires_ccb
            or console_mutations > 0
        ):
            unlocked_state_or_console_mutation_workspace_ids.append(wid)

        if (
            drifted_resources > 0
            and hours_since_drift > max_drift_reconciliation_hours
        ):
            unreconciled_drift_workspace_ids.append(wid)

    if unlocked_state_or_console_mutation_workspace_ids:
        iac_governance_status = "IAC_STATE_LOCK_OR_CONSOLE_MUTATION_BREACH"
    elif unreconciled_drift_workspace_ids:
        iac_governance_status = "IAC_DRIFT_RECONCILIATION_SLA_WARNING"
    else:
        iac_governance_status = "IAC_GITOPS_PARITY_OPTIMAL"

    return {
        "evaluated_workspaces_count": len(valid_workspaces),
        "unlocked_state_or_console_mutation_workspace_ids": unlocked_state_or_console_mutation_workspace_ids,
        "unreconciled_drift_workspace_ids": unreconciled_drift_workspace_ids,
        "iac_governance_status": iac_governance_status,
        "is_iac_gitops_compliant": iac_governance_status
        == "IAC_GITOPS_PARITY_OPTIMAL",
    }


ProjectCCBService.audit_iac_terraform_drift_and_state_lock_hygiene = staticmethod(
    audit_iac_terraform_drift_and_state_lock_hygiene
)


def audit_container_image_vulnerability_and_non_root_runtime_gate(
    container_images: Sequence[Mapping[str, Any]] | None,
    *,
    max_high_cves_allowed: int = 0,
    max_image_size_mb: float = 500.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.3 & §11.6 — CCB Container Image Vulnerability Gate, Distroless Base Hygiene & Non-Root Runtime Enforcement Auditor."""
    valid_images = [
        img
        for img in (container_images or [])
        if isinstance(img, Mapping) and str(img.get("image_id") or "").strip()
    ]

    vulnerable_or_root_runtime_image_ids: list[str] = []
    bloated_or_writable_rootfs_image_ids: list[str] = []

    for img in valid_images:
        iid = str(img.get("image_id")).strip()
        critical_or_high_cves_count = int(
            img.get("critical_or_high_cves_count", 0)
            if img.get("critical_or_high_cves_count") is not None
            else 0
        )
        runs_as_non_root_uid = bool(
            img.get("runs_as_non_root_uid", True)
            if img.get("runs_as_non_root_uid") is not None
            else True
        )
        pinned_by_sha256_digest = bool(
            img.get("pinned_by_sha256_digest", True)
            if img.get("pinned_by_sha256_digest") is not None
            else True
        )
        image_size_mb = float(
            img.get("image_size_mb", 180.0)
            if img.get("image_size_mb") is not None
            else 180.0
        )
        read_only_root_filesystem_enabled = bool(
            img.get("read_only_root_filesystem_enabled", True)
            if img.get("read_only_root_filesystem_enabled") is not None
            else True
        )

        if (
            critical_or_high_cves_count > max_high_cves_allowed
            or not runs_as_non_root_uid
            or not pinned_by_sha256_digest
        ):
            vulnerable_or_root_runtime_image_ids.append(iid)

        if (
            image_size_mb > max_image_size_mb
            or not read_only_root_filesystem_enabled
        ):
            bloated_or_writable_rootfs_image_ids.append(iid)

    if vulnerable_or_root_runtime_image_ids:
        container_security_status = "CONTAINER_CVE_OR_ROOT_RUNTIME_BREACH"
    elif bloated_or_writable_rootfs_image_ids:
        container_security_status = "CONTAINER_BLOAT_OR_WRITABLE_ROOTFS_WARNING"
    else:
        container_security_status = "CONTAINER_RUNTIME_HARDENED_OPTIMAL"

    return {
        "evaluated_images_count": len(valid_images),
        "vulnerable_or_root_runtime_image_ids": vulnerable_or_root_runtime_image_ids,
        "bloated_or_writable_rootfs_image_ids": bloated_or_writable_rootfs_image_ids,
        "container_security_status": container_security_status,
        "is_container_security_compliant": container_security_status
        == "CONTAINER_RUNTIME_HARDENED_OPTIMAL",
    }


ProjectCCBService.audit_container_image_vulnerability_and_non_root_runtime_gate = staticmethod(
    audit_container_image_vulnerability_and_non_root_runtime_gate
)


def audit_dark_launch_shadow_traffic_parity_and_isolation(
    shadow_campaigns: Sequence[Mapping[str, Any]] | None,
    *,
    min_payload_parity_pct: float = 99.5,
    max_primary_latency_overhead_ms: float = 10.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.2 & §8.3 — CCB Dark-Launch Shadow Traffic Mirroring Payload Parity, Side-Effect Isolation & Latency Amplification Auditor."""
    valid_campaigns = [
        campaign
        for campaign in (shadow_campaigns or [])
        if isinstance(campaign, Mapping)
        and str(campaign.get("campaign_id") or "").strip()
    ]

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _num(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    side_effect_leak_or_sync_blocking_campaign_ids: list[str] = []
    parity_mismatch_or_latency_drag_campaign_ids: list[str] = []

    for campaign in valid_campaigns:
        campaign_id = str(campaign.get("campaign_id")).strip()
        payload_parity_pct = _num(
            campaign.get("payload_response_parity_pct"), 99.9
        )
        side_effects_muted = _bool(
            campaign.get("shadow_write_side_effects_muted"), True
        )
        async_fire_forget = _bool(
            campaign.get("async_fire_and_forget_enforced"), True
        )
        latency_overhead_ms = _num(
            campaign.get("primary_path_latency_overhead_ms"), 2.0
        )
        pii_masked = _bool(
            campaign.get("pii_masked_in_shadow_diff_logs"), True
        )

        if (
            not side_effects_muted
            or not async_fire_forget
            or not pii_masked
        ):
            side_effect_leak_or_sync_blocking_campaign_ids.append(campaign_id)

        if (
            payload_parity_pct < min_payload_parity_pct
            or latency_overhead_ms > max_primary_latency_overhead_ms
        ):
            parity_mismatch_or_latency_drag_campaign_ids.append(campaign_id)

    if side_effect_leak_or_sync_blocking_campaign_ids:
        dark_launch_governance_status = "DARK_LAUNCH_SIDE_EFFECT_OR_PII_BREACH"
    elif parity_mismatch_or_latency_drag_campaign_ids:
        dark_launch_governance_status = (
            "DARK_LAUNCH_PARITY_OR_LATENCY_WARNING"
        )
    else:
        dark_launch_governance_status = "DARK_LAUNCH_SHADOW_PARITY_OPTIMAL"

    return {
        "evaluated_campaigns_count": len(valid_campaigns),
        "side_effect_leak_or_sync_blocking_campaign_ids": side_effect_leak_or_sync_blocking_campaign_ids,
        "parity_mismatch_or_latency_drag_campaign_ids": parity_mismatch_or_latency_drag_campaign_ids,
        "dark_launch_governance_status": dark_launch_governance_status,
        "is_dark_launch_compliant": dark_launch_governance_status
        == "DARK_LAUNCH_SHADOW_PARITY_OPTIMAL",
    }


ProjectCCBService.audit_dark_launch_shadow_traffic_parity_and_isolation = staticmethod(
    audit_dark_launch_shadow_traffic_parity_and_isolation
)


def audit_db_connection_pool_saturation_and_idle_tx_timeout(
    db_pools: Sequence[Mapping[str, Any]] | None,
    *,
    max_pool_utilization_pct: float = 80.0,
    max_idle_in_tx_timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.3 & §11.6 — CCB Database Connection Pool Saturation, PgBouncer Transaction-Mode Multiplexing & Idle-in-Transaction Timeout Auditor."""
    valid_pools = [
        pl
        for pl in (db_pools or [])
        if isinstance(pl, Mapping) and str(pl.get("pool_id") or "").strip()
    ]

    leaking_or_unbounded_idle_tx_pool_ids: list[str] = []
    high_utilization_or_unpooled_pool_ids: list[str] = []

    for pl in valid_pools:
        pid = str(pl.get("pool_id")).strip()
        peak_active_connections_pct = float(
            pl.get("peak_active_connections_pct", 55.0)
            if pl.get("peak_active_connections_pct") is not None
            else 55.0
        )
        idle_in_transaction_timeout_seconds = float(
            pl.get("idle_in_transaction_timeout_seconds", 15.0)
            if pl.get("idle_in_transaction_timeout_seconds") is not None
            else 15.0
        )
        connection_leaks_detected_count = int(
            pl.get("connection_leaks_detected_count", 0)
            if pl.get("connection_leaks_detected_count") is not None
            else 0
        )
        pgbouncer_transaction_pooling_enabled = bool(
            pl.get("pgbouncer_transaction_pooling_enabled", True)
            if pl.get("pgbouncer_transaction_pooling_enabled") is not None
            else True
        )

        if (
            connection_leaks_detected_count > 0
            or idle_in_transaction_timeout_seconds <= 0
            or idle_in_transaction_timeout_seconds
            > max_idle_in_tx_timeout_seconds
        ):
            leaking_or_unbounded_idle_tx_pool_ids.append(pid)

        if (
            peak_active_connections_pct > max_pool_utilization_pct
            or not pgbouncer_transaction_pooling_enabled
        ):
            high_utilization_or_unpooled_pool_ids.append(pid)

    if leaking_or_unbounded_idle_tx_pool_ids:
        db_pool_governance_status = "DB_POOL_LEAK_OR_UNBOUNDED_IDLE_TX_BREACH"
    elif high_utilization_or_unpooled_pool_ids:
        db_pool_governance_status = (
            "DB_POOL_SATURATION_OR_MULTIPLEXING_WARNING"
        )
    else:
        db_pool_governance_status = "DB_POOL_CAPACITY_OPTIMAL"

    return {
        "evaluated_pools_count": len(valid_pools),
        "leaking_or_unbounded_idle_tx_pool_ids": leaking_or_unbounded_idle_tx_pool_ids,
        "high_utilization_or_unpooled_pool_ids": high_utilization_or_unpooled_pool_ids,
        "db_pool_governance_status": db_pool_governance_status,
        "is_db_pool_compliant": db_pool_governance_status
        == "DB_POOL_CAPACITY_OPTIMAL",
    }


ProjectCCBService.audit_db_connection_pool_saturation_and_idle_tx_timeout = staticmethod(
    audit_db_connection_pool_saturation_and_idle_tx_timeout
)


def audit_message_broker_consumer_lag_and_dlq_poison_pill_gate(
    topics: list[dict] | None,
    *,
    max_consumer_lag_messages: int = 5000,
    max_poison_pill_retries: int = 5,
) -> dict:
    """PMBOK §8.3 & §11.6 — Audita lag de consumidores de broker de mensajería, cuarentena DLQ de poison-pills y compatibilidad de Schema Registry."""
    raw_items = topics if isinstance(topics, list) else []
    valid_topics: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("topic_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_topics.append(item)

    schema_break_or_missing_dlq_topic_ids: list[str] = []
    high_lag_or_retry_storm_topic_ids: list[str] = []

    for t in valid_topics:
        topic_id = t["topic_id"].strip()
        raw_lag = t.get("consumer_lag_messages", 0)
        consumer_lag_messages = int(0 if raw_lag is None else raw_lag)

        raw_dlq = t.get("dlq_poison_pill_quarantine_enabled", True)
        dlq_poison_pill_quarantine_enabled = bool(
            True if raw_dlq is None else raw_dlq
        )

        raw_schema = t.get("schema_backward_compatible", True)
        schema_backward_compatible = bool(
            True if raw_schema is None else raw_schema
        )

        raw_retries = t.get("configured_max_retries", 3)
        configured_max_retries = int(3 if raw_retries is None else raw_retries)

        if (
            not schema_backward_compatible
            or not dlq_poison_pill_quarantine_enabled
        ):
            schema_break_or_missing_dlq_topic_ids.append(topic_id)

        if (
            consumer_lag_messages > max_consumer_lag_messages
            or configured_max_retries > max_poison_pill_retries
        ):
            high_lag_or_retry_storm_topic_ids.append(topic_id)

    if schema_break_or_missing_dlq_topic_ids:
        message_broker_gate_status = "BROKER_SCHEMA_OR_DLQ_QUARANTINE_BREACH"
    elif high_lag_or_retry_storm_topic_ids:
        message_broker_gate_status = "BROKER_CONSUMER_LAG_OR_RETRY_WARNING"
    else:
        message_broker_gate_status = "BROKER_STREAMING_GATE_OPTIMAL"

    return {
        "evaluated_topics_count": len(valid_topics),
        "schema_break_or_missing_dlq_topic_ids": schema_break_or_missing_dlq_topic_ids,
        "high_lag_or_retry_storm_topic_ids": high_lag_or_retry_storm_topic_ids,
        "message_broker_gate_status": message_broker_gate_status,
        "is_message_broker_gate_compliant": message_broker_gate_status
        == "BROKER_STREAMING_GATE_OPTIMAL",
    }


ProjectCCBService.audit_message_broker_consumer_lag_and_dlq_poison_pill_gate = staticmethod(
    audit_message_broker_consumer_lag_and_dlq_poison_pill_gate
)


def audit_distributed_cache_stampede_and_hotkey_skew_gate(
    caches: list[dict] | None,
    *,
    min_cache_hit_ratio_pct: float = 85.0,
    max_hotkey_traffic_share_pct: float = 25.0,
) -> dict:
    """PMBOK §8.3 & §11.6 — Audita protección contra thundering-herd (singleflight + TTL jitter), ratio de aciertos y asimetría de hot-keys en cachés distribuidos."""
    raw_items = caches if isinstance(caches, list) else []
    valid_caches: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("cache_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_caches.append(item)

    stampede_unprotected_cache_ids: list[str] = []
    low_hit_ratio_or_hotkey_skew_cache_ids: list[str] = []

    for c in valid_caches:
        cid = c["cache_id"].strip()
        raw_lock = c.get("singleflight_stampede_lock_enabled", True)
        singleflight_stampede_lock_enabled = bool(
            True if raw_lock is None else raw_lock
        )

        raw_jitter = c.get("ttl_jitter_configured", True)
        ttl_jitter_configured = bool(
            True if raw_jitter is None else raw_jitter
        )

        raw_hit = c.get("cache_hit_ratio_pct", 94.0)
        cache_hit_ratio_pct = float(94.0 if raw_hit is None else raw_hit)

        raw_hotkey = c.get("max_single_key_traffic_share_pct", 8.0)
        max_single_key_traffic_share_pct = float(
            8.0 if raw_hotkey is None else raw_hotkey
        )

        if not singleflight_stampede_lock_enabled or not ttl_jitter_configured:
            stampede_unprotected_cache_ids.append(cid)

        if (
            cache_hit_ratio_pct < min_cache_hit_ratio_pct
            or max_single_key_traffic_share_pct > max_hotkey_traffic_share_pct
        ):
            low_hit_ratio_or_hotkey_skew_cache_ids.append(cid)

    if stampede_unprotected_cache_ids:
        cache_resilience_status = "CACHE_STAMPEDE_LOCK_OR_JITTER_BREACH"
    elif low_hit_ratio_or_hotkey_skew_cache_ids:
        cache_resilience_status = "CACHE_HIT_RATIO_OR_HOTKEY_SKEW_WARNING"
    else:
        cache_resilience_status = "CACHE_TIER_RESILIENCE_OPTIMAL"

    return {
        "evaluated_caches_count": len(valid_caches),
        "stampede_unprotected_cache_ids": stampede_unprotected_cache_ids,
        "low_hit_ratio_or_hotkey_skew_cache_ids": low_hit_ratio_or_hotkey_skew_cache_ids,
        "cache_resilience_status": cache_resilience_status,
        "is_cache_resilience_compliant": cache_resilience_status
        == "CACHE_TIER_RESILIENCE_OPTIMAL",
    }


ProjectCCBService.audit_distributed_cache_stampede_and_hotkey_skew_gate = staticmethod(
    audit_distributed_cache_stampede_and_hotkey_skew_gate
)


def audit_service_mesh_mtls_strict_and_outlier_ejection_gate(
    meshes: list[dict] | None,
    *,
    max_sidecar_cpu_overhead_pct: float = 12.0,
    max_ejected_endpoints_share_pct: float = 30.0,
) -> dict:
    """PMBOK §8.3 & §11.6 — Audita aplicación estricta de mTLS en Service Mesh, sobrecarga de CPU de sidecar proxy y eyección de outliers de circuit-breaker."""
    raw_items = meshes if isinstance(meshes, list) else []
    valid_meshes: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("mesh_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_meshes.append(item)

    permissive_mtls_or_missing_outlier_mesh_ids: list[str] = []
    high_sidecar_overhead_or_cascading_ejection_mesh_ids: list[str] = []

    for m in valid_meshes:
        mid = m["mesh_id"].strip()
        raw_mtls = m.get("mtls_strict_mode_enforced", True)
        mtls_strict_mode_enforced = bool(True if raw_mtls is None else raw_mtls)

        raw_outlier = m.get("outlier_detection_configured", True)
        outlier_detection_configured = bool(
            True if raw_outlier is None else raw_outlier
        )

        raw_cpu = m.get("sidecar_cpu_overhead_pct", 4.5)
        sidecar_cpu_overhead_pct = float(4.5 if raw_cpu is None else raw_cpu)

        raw_eject = m.get("max_ejection_percent", 20.0)
        max_ejection_percent = float(20.0 if raw_eject is None else raw_eject)

        if not mtls_strict_mode_enforced or not outlier_detection_configured:
            permissive_mtls_or_missing_outlier_mesh_ids.append(mid)

        if (
            sidecar_cpu_overhead_pct > max_sidecar_cpu_overhead_pct
            or max_ejection_percent > max_ejected_endpoints_share_pct
        ):
            high_sidecar_overhead_or_cascading_ejection_mesh_ids.append(mid)

    if permissive_mtls_or_missing_outlier_mesh_ids:
        service_mesh_gate_status = "MESH_PERMISSIVE_MTLS_OR_OUTLIER_BREACH"
    elif high_sidecar_overhead_or_cascading_ejection_mesh_ids:
        service_mesh_gate_status = "MESH_SIDECAR_OVERHEAD_OR_EJECTION_WARNING"
    else:
        service_mesh_gate_status = "MESH_ZERO_TRUST_RESILIENCE_OPTIMAL"

    return {
        "evaluated_meshes_count": len(valid_meshes),
        "permissive_mtls_or_missing_outlier_mesh_ids": permissive_mtls_or_missing_outlier_mesh_ids,
        "high_sidecar_overhead_or_cascading_ejection_mesh_ids": high_sidecar_overhead_or_cascading_ejection_mesh_ids,
        "service_mesh_gate_status": service_mesh_gate_status,
        "is_service_mesh_gate_compliant": service_mesh_gate_status
        == "MESH_ZERO_TRUST_RESILIENCE_OPTIMAL",
    }


ProjectCCBService.audit_service_mesh_mtls_strict_and_outlier_ejection_gate = staticmethod(
    audit_service_mesh_mtls_strict_and_outlier_ejection_gate
)


def audit_graphql_query_depth_and_n_plus_one_batching_gate(
    operations: list[dict] | None,
    *,
    max_query_depth: int = 8,
    max_complexity_cost_score: int = 500,
) -> dict:
    """PMBOK §8.3 & §11.6 — Audita límites de profundidad y amplificación de alias en consultas GraphQL, presupuesto de complejidad y batching DataLoader contra N+1."""
    raw_items = operations if isinstance(operations, list) else []
    valid_operations: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("operation_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_operations.append(item)

    unbounded_depth_or_n_plus_one_operation_ids: list[str] = []
    deep_query_or_high_complexity_operation_ids: list[str] = []

    for o in valid_operations:
        oid = o["operation_id"].strip()
        raw_limit = o.get("depth_and_alias_limit_enforced", True)
        depth_and_alias_limit_enforced = bool(
            True if raw_limit is None else raw_limit
        )

        raw_dl = o.get("dataloader_batching_verified", True)
        dataloader_batching_verified = bool(True if raw_dl is None else raw_dl)

        raw_depth = o.get("observed_query_depth", 4)
        observed_query_depth = int(4 if raw_depth is None else raw_depth)

        raw_score = o.get("complexity_cost_score", 180)
        complexity_cost_score = int(180 if raw_score is None else raw_score)

        if (
            not depth_and_alias_limit_enforced
            or not dataloader_batching_verified
        ):
            unbounded_depth_or_n_plus_one_operation_ids.append(oid)

        if (
            observed_query_depth > max_query_depth
            or complexity_cost_score > max_complexity_cost_score
        ):
            deep_query_or_high_complexity_operation_ids.append(oid)

    if unbounded_depth_or_n_plus_one_operation_ids:
        graphql_gate_status = "GRAPHQL_UNBOUNDED_DEPTH_OR_N_PLUS_ONE_BREACH"
    elif deep_query_or_high_complexity_operation_ids:
        graphql_gate_status = "GRAPHQL_COMPLEXITY_OR_DEPTH_WARNING"
    else:
        graphql_gate_status = "GRAPHQL_QUERY_GOVERNANCE_OPTIMAL"

    return {
        "evaluated_operations_count": len(valid_operations),
        "unbounded_depth_or_n_plus_one_operation_ids": unbounded_depth_or_n_plus_one_operation_ids,
        "deep_query_or_high_complexity_operation_ids": deep_query_or_high_complexity_operation_ids,
        "graphql_gate_status": graphql_gate_status,
        "is_graphql_gate_compliant": graphql_gate_status
        == "GRAPHQL_QUERY_GOVERNANCE_OPTIMAL",
    }


ProjectCCBService.audit_graphql_query_depth_and_n_plus_one_batching_gate = staticmethod(
    audit_graphql_query_depth_and_n_plus_one_batching_gate
)


def audit_blue_green_cutover_drain_and_db_backward_compatibility(
    cutovers: list[dict] | None,
    *,
    min_standby_warm_retention_minutes: int = 60,
    max_inflight_dropped_requests: int = 0,
) -> dict:
    """PMBOK §8.3 & §11.6 — Audita cutover blue-green, drain de conexiones en vuelo, smoke test green y compatibilidad expand-contract de esquema DB."""
    raw_items = cutovers if isinstance(cutovers, list) else []
    valid_cutovers: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("cutover_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_cutovers.append(item)

    def _num(value, default):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _bool(value, default):
        return value if isinstance(value, bool) else default

    incompatible_db_or_failed_smoke_cutover_ids: list[str] = []
    dropped_requests_or_cold_standby_cutover_ids: list[str] = []

    for cutover in valid_cutovers:
        cutover_id = str(cutover.get("cutover_id")).strip()
        db_compatible = _bool(
            cutover.get("expand_contract_db_schema_compatible"), True
        )
        smoke_passed = _bool(
            cutover.get("synthetic_smoke_test_green_passed"), True
        )
        dropped_requests = _num(
            cutover.get("inflight_dropped_requests_count"), 0.0
        )
        warm_retention = _num(
            cutover.get("blue_standby_warm_retention_minutes"), 120.0
        )

        if not db_compatible or not smoke_passed:
            incompatible_db_or_failed_smoke_cutover_ids.append(cutover_id)

        if (
            dropped_requests > max_inflight_dropped_requests
            or warm_retention < min_standby_warm_retention_minutes
        ):
            dropped_requests_or_cold_standby_cutover_ids.append(cutover_id)

    if incompatible_db_or_failed_smoke_cutover_ids:
        blue_green_cutover_status = "BLUE_GREEN_DB_COMPAT_OR_SMOKE_BREACH"
    elif dropped_requests_or_cold_standby_cutover_ids:
        blue_green_cutover_status = (
            "BLUE_GREEN_DRAIN_DROP_OR_WARM_STANDBY_WARNING"
        )
    else:
        blue_green_cutover_status = "BLUE_GREEN_ZERO_DOWNTIME_OPTIMAL"

    return {
        "evaluated_cutovers_count": len(valid_cutovers),
        "incompatible_db_or_failed_smoke_cutover_ids": incompatible_db_or_failed_smoke_cutover_ids,
        "dropped_requests_or_cold_standby_cutover_ids": dropped_requests_or_cold_standby_cutover_ids,
        "blue_green_cutover_status": blue_green_cutover_status,
        "is_blue_green_cutover_compliant": blue_green_cutover_status
        == "BLUE_GREEN_ZERO_DOWNTIME_OPTIMAL",
    }


ProjectCCBService.audit_blue_green_cutover_drain_and_db_backward_compatibility = staticmethod(
    audit_blue_green_cutover_drain_and_db_backward_compatibility
)


def audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate(
    pool_samples: list[dict[str, Any]],
    *,
    max_pool_utilization_pct: float = 85.0,
    max_client_wait_ms: float = 50.0,
    max_idle_in_tx_seconds: float = 15.0,
    require_transaction_pooling_mode: bool = True,
) -> dict[str, Any]:
    """PMBOK §8.3 & §11.6 — Audita saturación de pool de conexiones PgBouncer, timeout de transacciones idle-in-transaction y modo de pooling transaccional en gates CCB."""
    raw_samples = pool_samples if isinstance(pool_samples, (list, tuple)) else []
    valid_samples = [item for item in raw_samples if isinstance(item, dict)]

    if not valid_samples:
        return {
            "status": "healthy",
            "gate_passed": True,
            "pools_evaluated": 0,
            "saturated_pool_ids": [],
            "idle_in_tx_leak_pool_ids": [],
            "records": [],
            "violations": [],
        }

    saturated_pool_ids: list[str] = []
    idle_in_tx_leak_pool_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_breach = False
    has_critical = False

    for idx, item in enumerate(valid_samples):
        pool_id = (
            str(item.get("pool_id") or item.get("id") or f"pool-{idx + 1}").strip()
            or f"pool-{idx + 1}"
        )
        active_server_connections = max(
            0, int(item.get("active_server_connections") or 0)
        )
        max_pool_size = max(0, int(item.get("max_pool_size") or 0))
        waiting_clients_count = max(
            0, int(item.get("waiting_clients_count") or 0)
        )
        max_wait_time_ms = max(0.0, float(item.get("max_wait_time_ms") or 0.0))
        longest_idle_in_tx_seconds = max(
            0.0, float(item.get("longest_idle_in_tx_seconds") or 0.0)
        )
        pooling_mode = (
            str(item.get("pooling_mode") or "transaction").strip().lower()
            or "transaction"
        )
        reserve_pool_exhausted = bool(item.get("reserve_pool_exhausted", False))

        if max_pool_size > 0:
            utilization_pct = round(
                (active_server_connections / max_pool_size) * 100.0, 2
            )
        elif active_server_connections > 0:
            utilization_pct = 100.0
        else:
            utilization_pct = 0.0

        pool_utilization_exceeded = utilization_pct > max_pool_utilization_pct
        client_wait_sla_breach = max_wait_time_ms > max_client_wait_ms
        idle_in_transaction_leak = (
            longest_idle_in_tx_seconds > max_idle_in_tx_seconds
        )
        invalid_pooling_mode = bool(
            require_transaction_pooling_mode and pooling_mode != "transaction"
        )

        if (
            pool_utilization_exceeded
            or client_wait_sla_breach
            or reserve_pool_exhausted
        ):
            saturated_pool_ids.append(pool_id)

        if idle_in_transaction_leak:
            idle_in_tx_leak_pool_ids.append(pool_id)

        sample_breach = (
            pool_utilization_exceeded
            or client_wait_sla_breach
            or idle_in_transaction_leak
            or invalid_pooling_mode
            or reserve_pool_exhausted
        )
        if sample_breach:
            has_breach = True
            violations.append(f"Pool '{pool_id}' breached PgBouncer gate SLA.")

        if (
            reserve_pool_exhausted
            or idle_in_transaction_leak
            or utilization_pct > 95.0
        ):
            has_critical = True

        records.append(
            {
                "pool_id": pool_id,
                "active_server_connections": active_server_connections,
                "max_pool_size": max_pool_size,
                "waiting_clients_count": waiting_clients_count,
                "max_wait_time_ms": max_wait_time_ms,
                "longest_idle_in_tx_seconds": longest_idle_in_tx_seconds,
                "pooling_mode": pooling_mode,
                "utilization_pct": utilization_pct,
                "pool_utilization_exceeded": pool_utilization_exceeded,
                "client_wait_sla_breach": client_wait_sla_breach,
                "idle_in_transaction_leak": idle_in_transaction_leak,
                "invalid_pooling_mode": invalid_pooling_mode,
                "reserve_pool_exhausted": reserve_pool_exhausted,
            }
        )

    if not has_breach:
        status = "healthy"
        gate_passed = True
    elif has_critical:
        status = "critical"
        gate_passed = False
    else:
        status = "warning"
        gate_passed = False

    return {
        "status": status,
        "gate_passed": gate_passed,
        "pools_evaluated": len(valid_samples),
        "saturated_pool_ids": saturated_pool_ids,
        "idle_in_tx_leak_pool_ids": idle_in_tx_leak_pool_ids,
        "records": records,
        "violations": violations,
    }


ProjectCCBService.audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate = staticmethod(
    audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate
)



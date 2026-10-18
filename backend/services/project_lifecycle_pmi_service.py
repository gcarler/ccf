"""PMI project initiation, stakeholder engagement, and closure operations."""

from __future__ import annotations

import re

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from backend import models


def build_pmo_portfolio_matrix(db: Session, sede_id: UUID | None) -> dict:
    """Aggregate active project EVM metrics within the authenticated sede scope."""
    query = (
        db.query(models.Project)
        .options(selectinload(models.Project.lifecycle))
        .filter(
            models.Project.deleted_at.is_(None),
            models.Project.status.in_(("planning", "active", "on_hold")),
        )
    )
    if sede_id is not None:
        query = query.filter(or_(models.Project.sede_id.is_(None), models.Project.sede_id == sede_id))

    projects = query.order_by(models.Project.title, models.Project.id).all()
    from backend.services.project_evm_service import calculate_project_evm

    quadrants = {
        "q1_optimal": 0,
        "q2_cost_acceleration": 0,
        "q3_underutilized_capacity": 0,
        "q4_critical_emergency": 0,
    }
    projects_matrix = []
    total_bac = 0.0
    total_ev = 0.0
    total_ac = 0.0
    total_pv = 0.0

    for project in projects:
        evm = calculate_project_evm(db, project)
        bac = float(evm.get("bac") or 0.0)
        ev = float(evm.get("ev") or 0.0)
        ac = float(evm.get("ac") or 0.0)
        pv = float(evm.get("pv") or 0.0)
        cpi = float(evm.get("cpi") or 0.0)
        spi = float(evm.get("spi") or 0.0)
        if cpi >= 1.0 and spi >= 1.0:
            quadrant = "q1_optimal"
        elif cpi < 1.0 and spi >= 1.0:
            quadrant = "q2_cost_acceleration"
        elif cpi >= 1.0 and spi < 1.0:
            quadrant = "q3_underutilized_capacity"
        else:
            quadrant = "q4_critical_emergency"
        quadrants[quadrant] += 1
        total_bac += bac
        total_ev += ev
        total_ac += ac
        total_pv += pv

        lifecycle = project.lifecycle
        projects_matrix.append({
            "project_id": str(project.id),
            "title": project.title,
            "status": project.status,
            "development_approach": lifecycle.development_approach if lifecycle else "hybrid",
            "pmo_type": lifecycle.pmo_type if lifecycle else "controlling",
            "bac": round(bac, 2),
            "ev": round(ev, 2),
            "ac": round(ac, 2),
            "cpi": round(cpi, 2),
            "spi": round(spi, 2),
            "csi": round(cpi * spi, 2),
            "quadrant": quadrant,
            "progress_pct": round(float(evm.get("progress_percentage") or 0.0), 1),
            "charter_status": lifecycle.charter_status if lifecycle else "draft",
        })

    portfolio_cpi = round(total_ev / total_ac, 2) if total_ac > 0 else (1.0 if total_ev == 0 else 2.0)
    portfolio_spi = round(total_ev / total_pv, 2) if total_pv > 0 else (1.0 if total_ev == 0 else 2.0)
    portfolio_totals = {
        "total_projects": len(projects),
        "total_bac": round(total_bac, 2),
        "total_ev": round(total_ev, 2),
        "total_ac": round(total_ac, 2),
        "portfolio_cpi": portfolio_cpi,
        "portfolio_spi": portfolio_spi,
        "portfolio_csi": round(portfolio_cpi * portfolio_spi, 2),
    }
    return {
        "portfolio_totals": portfolio_totals,
        "quadrants_distribution": quadrants,
        "projects_matrix": projects_matrix,
    }


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


def compute_closure_readiness_pct(
    deliverables_accepted_verified: bool,
    financial_reconciliation_completed: bool,
    lessons_learned_count: int,
    closure_status: str,
) -> float:
    """Compute PMI §4.7 administrative closure readiness percentage (0.0 to 100.0)."""
    if closure_status == "closed":
        return 100.0
    score = 0.0
    if deliverables_accepted_verified:
        score += 40.0
    if financial_reconciliation_completed:
        score += 40.0
    if int(lessons_learned_count or 0) > 0:
        score += 20.0
    return round(score, 1)


def compute_governance_maturity_pct(
    charter_status: str,
    measurable_objectives_count: int,
    stakeholders_total: int,
    closure_readiness_pct: float,
) -> float:
    """Compute PMI §2.4 project governance maturity percentage (0.0 to 100.0)."""
    score = 0.0
    if charter_status == "authorized":
        score += 35.0
    if int(measurable_objectives_count or 0) > 0:
        score += 25.0
    if int(stakeholders_total or 0) > 0:
        score += 20.0
    clamped_closure = max(0.0, min(100.0, float(closure_readiness_pct or 0.0)))
    score += 20.0 * (clamped_closure / 100.0)
    return round(score, 1)


def evaluate_governance_health(summary: dict) -> dict:
    """Evaluate PMI governance maturity and closure readiness from a governance summary dict."""
    closure_readiness_pct = compute_closure_readiness_pct(
        deliverables_accepted_verified=bool(summary.get("deliverables_accepted_verified")),
        financial_reconciliation_completed=bool(summary.get("financial_reconciliation_completed")),
        lessons_learned_count=int(summary.get("lessons_learned_count") or 0),
        closure_status=str(summary.get("closure_status") or "open"),
    )
    governance_maturity_pct = compute_governance_maturity_pct(
        charter_status=str(summary.get("charter_status") or "draft"),
        measurable_objectives_count=int(summary.get("measurable_objectives_count") or 0),
        stakeholders_total=int(summary.get("stakeholders_total") or 0),
        closure_readiness_pct=closure_readiness_pct,
    )
    if governance_maturity_pct >= 85.0:
        maturity_tier = "optimized"
    elif governance_maturity_pct >= 60.0:
        maturity_tier = "managed"
    elif governance_maturity_pct >= 35.0:
        maturity_tier = "developing"
    else:
        maturity_tier = "initial"
    return {
        "closure_readiness_pct": closure_readiness_pct,
        "governance_maturity_pct": governance_maturity_pct,
        "maturity_tier": maturity_tier,
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
        development_approach="hybrid",
        pmo_type="controlling",
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


def evaluate_automation_governance_readiness(
    rules: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audit project automation rules configuration readiness under PMI workflow governance standards."""
    supported_actions = {
        "notify_assignee",
        "notify_channel",
        "reassign_task",
        "change_phase",
        "create_followup_task",
        "set_priority",
    }
    supported_priorities = {"low", "medium", "high", "urgent", "critical"}

    total_rules = 0
    active_rules = 0
    valid_active_rules = 0
    misconfigured_active_rules = 0
    total_executions = 0

    for rule in rules or []:
        if not isinstance(rule, dict):
            continue
        total_rules += 1
        try:
            exec_count = max(0, int(rule.get("execution_count") or 0))
        except (TypeError, ValueError):
            exec_count = 0
        total_executions += exec_count

        is_active = bool(rule.get("is_active", True))
        if not is_active:
            continue

        active_rules += 1
        action = rule.get("action_type")
        raw_action_data = rule.get("action_data")
        action_data = {} if raw_action_data is None else raw_action_data

        is_valid = True
        if not isinstance(action_data, dict):
            is_valid = False
        elif not isinstance(action, str) or action not in supported_actions:
            is_valid = False
        elif action == "reassign_task":
            assignee_id = action_data.get("assignee_id")
            if not (
                isinstance(assignee_id, UUID)
                or (isinstance(assignee_id, str) and assignee_id.strip() != "")
            ):
                is_valid = False
        elif action == "change_phase":
            if not any(
                isinstance(target, str) and target.strip() != ""
                for target in (action_data.get("phase_name"), action_data.get("node"))
            ):
                is_valid = False
        elif action == "set_priority":
            priority_val = action_data.get("priority")
            if not isinstance(priority_val, str) or priority_val not in supported_priorities:
                is_valid = False
        elif action == "create_followup_task":
            if "priority" in action_data:
                priority_val = action_data.get("priority")
                if not isinstance(priority_val, str) or priority_val not in supported_priorities:
                    is_valid = False

        if is_valid:
            valid_active_rules += 1
        else:
            misconfigured_active_rules += 1

    readiness_pct = (
        100.0
        if active_rules == 0
        else round((valid_active_rules / active_rules) * 100.0, 2)
    )

    if active_rules == 0:
        governance_status = "idle"
    elif misconfigured_active_rules == 0:
        governance_status = "optimal"
    elif readiness_pct >= 50.0:
        governance_status = "warning"
    else:
        governance_status = "critical"

    return {
        "total_rules": total_rules,
        "active_rules": active_rules,
        "valid_active_rules": valid_active_rules,
        "misconfigured_active_rules": misconfigured_active_rules,
        "total_executions": total_executions,
        "readiness_pct": readiness_pct,
        "governance_status": governance_status,
    }


ENGAGEMENT_RANKS = {
    "unaware": 0,
    "resistant": 1,
    "neutral": 2,
    "supportive": 3,
    "leading": 4,
}


def evaluate_stakeholder_engagement_gaps(
    stakeholders: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Matriz de Evaluación de Involucramiento de Interesados (PMBOK §13.2.2.5).

    Compara el nivel actual de engagement (current_engagement /
    engagement_level, default 'neutral') contra el nivel deseado
    (desired_engagement / target_engagement, default 'supportive') sobre la
    escala unaware=0 → leading=4, y evalúa el poder del interesado
    (power_level/influence == 'high' o power/influence_score >= 4).
    Retorna:
    - `total_stakeholders`: interesados evaluados.
    - `high_power_count`: interesados de alto poder.
    - `engagement_gap_count`: interesados con nivel deseado > actual.
    - `critical_resistant_count`: alto poder en unaware/resistant.
    - `alignment_pct`: % alineados (2 decimales; 100.0 si no hay interesados).
    - `engagement_health`: 'unmapped' (sin interesados), 'critical_resistance'
      (alto poder desinformado/resistente), 'aligned' (>= 80%) o
      'needs_outreach'.
    """
    rows = list(stakeholders or [])
    total_stakeholders = len(rows)

    high_power_count = 0
    engagement_gap_count = 0
    critical_resistant_count = 0
    for s in rows:
        current = str(s.get("current_engagement") or s.get("engagement_level") or "neutral").lower().strip()
        desired = str(s.get("desired_engagement") or s.get("target_engagement") or "supportive").lower().strip()
        current_rank = ENGAGEMENT_RANKS.get(current, 2)
        desired_rank = ENGAGEMENT_RANKS.get(desired, 3)

        power_text = str(s.get("power_level") or s.get("influence") or "").lower()
        try:
            power_num = int(s.get("power") or s.get("influence_score") or 0)
        except (TypeError, ValueError):
            power_num = 0
        is_high_power = power_text == "high" or power_num >= 4
        if is_high_power:
            high_power_count += 1
        if desired_rank > current_rank:
            engagement_gap_count += 1
        if is_high_power and current_rank <= 1:
            critical_resistant_count += 1

    alignment_pct = (
        100.0
        if total_stakeholders == 0
        else round(((total_stakeholders - engagement_gap_count) / total_stakeholders) * 100.0, 2)
    )

    if total_stakeholders == 0:
        engagement_health = "unmapped"
    elif critical_resistant_count > 0:
        engagement_health = "critical_resistance"
    elif alignment_pct >= 80.0:
        engagement_health = "aligned"
    else:
        engagement_health = "needs_outreach"

    return {
        "total_stakeholders": total_stakeholders,
        "high_power_count": high_power_count,
        "engagement_gap_count": engagement_gap_count,
        "critical_resistant_count": critical_resistant_count,
        "alignment_pct": alignment_pct,
        "engagement_health": engagement_health,
    }


def evaluate_charter_authorization_readiness(
    charter_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita los 5 pilares canónicos del Acta de Constitución del Proyecto (PMBOK §4.1 Project Charter)."""
    data = charter_data if isinstance(charter_data, dict) else {}

    has_business_case = bool(str(data.get("business_case") or "").strip())
    has_measurable_objectives = bool(
        isinstance(data.get("measurable_objectives"), list)
        and len([o for o in data.get("measurable_objectives", []) if o]) >= 1
    )

    raw_risks = data.get("high_level_risks")
    if isinstance(raw_risks, list):
        has_high_level_risks_or_assumptions = bool(
            len([r for r in raw_risks if r]) > 0
            or str(data.get("assumptions_and_constraints") or "").strip()
        )
    else:
        has_high_level_risks_or_assumptions = bool(
            str(raw_risks or data.get("assumptions_and_constraints") or "").strip()
        )

    has_assigned_sponsor = bool(
        str(data.get("sponsor_id") or data.get("sponsor_name") or "").strip()
    )
    is_formally_authorized = bool(
        str(data.get("charter_status") or data.get("status") or "").strip().lower()
        in {"authorized", "approved", "signed"}
    )

    pillars = (
        has_business_case,
        has_measurable_objectives,
        has_high_level_risks_or_assumptions,
        has_assigned_sponsor,
        is_formally_authorized,
    )
    pillars_satisfied_count = int(sum(1 for flag in pillars if flag))
    readiness_score_pct = round((pillars_satisfied_count / 5) * 100.0, 2)

    if is_formally_authorized and pillars_satisfied_count == 5:
        charter_gate_verdict = "authorized_complete"
    elif is_formally_authorized and pillars_satisfied_count < 5:
        charter_gate_verdict = "premature_authorization"
    elif not is_formally_authorized and pillars_satisfied_count == 4:
        charter_gate_verdict = "ready_for_signoff"
    else:
        charter_gate_verdict = "draft_incomplete"

    return {
        "has_business_case": has_business_case,
        "has_measurable_objectives": has_measurable_objectives,
        "has_high_level_risks_or_assumptions": has_high_level_risks_or_assumptions,
        "has_assigned_sponsor": has_assigned_sponsor,
        "is_formally_authorized": is_formally_authorized,
        "pillars_satisfied_count": pillars_satisfied_count,
        "readiness_score_pct": readiness_score_pct,
        "charter_gate_verdict": charter_gate_verdict,
    }


def evaluate_administrative_closure_audit(
    closure_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita la completitud formal del cierre del proyecto o fase según PMI PMBOK §4.7."""
    data = closure_data if isinstance(closure_data, dict) else {}

    deliverables_accepted = bool(data.get("deliverables_accepted_verified"))
    financial_closed = bool(data.get("financial_reconciliation_completed"))
    contracts_closed = bool(data.get("procurement_contracts_closed", True))
    resources_released = bool(data.get("team_resources_released", False))

    raw_lessons = data.get("lessons_learned")
    if isinstance(raw_lessons, list):
        lessons_count = len(
            [
                item
                for item in raw_lessons
                if (
                    isinstance(item, dict)
                    and str(item.get("summary") or item.get("lesson") or "").strip()
                )
                or (isinstance(item, str) and item.strip())
            ]
        )
    else:
        lessons_count = max(0, int(data.get("lessons_learned_count") or 0))

    final_report_summary = str(data.get("final_report_summary") or "").strip()

    missing_pillars: list[str] = []
    if not deliverables_accepted:
        missing_pillars.append("deliverables_acceptance")
    if not financial_closed:
        missing_pillars.append("financial_reconciliation")
    if not contracts_closed:
        missing_pillars.append("contractual_closure")
    if not resources_released:
        missing_pillars.append("resource_release")
    if lessons_count < 1 or len(final_report_summary) < 15:
        missing_pillars.append("lessons_learned_repository")

    completed_pillars_count = 5 - len(missing_pillars)
    closure_index_pct = round((completed_pillars_count / 5) * 100.0, 2)
    can_archive_project = len(missing_pillars) == 0

    if can_archive_project:
        closure_verdict = "ready_for_archive"
    elif deliverables_accepted and financial_closed:
        closure_verdict = "pending_SignOff"
    else:
        closure_verdict = "blocked_open_obligations"

    return {
        "completed_pillars_count": completed_pillars_count,
        "closure_index_pct": closure_index_pct,
        "lessons_learned_count": lessons_count,
        "missing_pillars": missing_pillars,
        "can_archive_project": can_archive_project,
        "closure_verdict": closure_verdict,
    }


def evaluate_pmo_portfolio_health_balance(
    projects: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audita el equilibrio de salud del portafolio PMO y la concentración presupuestaria en riesgo según PMI PMBOK §1.2.3.3."""
    valid_projects = [
        p for p in (projects or []) if isinstance(p, dict)
    ]

    total_projects = len(valid_projects)
    healthy_projects_count = 0
    watchlist_projects_count = 0
    critical_projects_count = 0
    total_portfolio_bac = 0.0
    budget_at_risk_bac = 0.0

    for p in valid_projects:
        bac = round(max(0.0, float(p.get("bac") or p.get("budget") or 0.0)), 2)
        cpi = float(p.get("cpi")) if p.get("cpi") is not None else 1.0
        spi = float(p.get("spi")) if p.get("spi") is not None else 1.0
        health_override = str(p.get("health_status") or "").strip().lower()

        total_portfolio_bac += bac

        is_critical = (
            health_override in {"red", "critical", "at_risk"}
            or cpi < 0.85
            or spi < 0.85
        )
        is_watchlist = not is_critical and (
            health_override in {"yellow", "warning", "amber"}
            or cpi < 0.95
            or spi < 0.95
        )

        if is_critical:
            critical_projects_count += 1
            budget_at_risk_bac += bac
        elif is_watchlist:
            watchlist_projects_count += 1
        else:
            healthy_projects_count += 1

    total_portfolio_bac = round(total_portfolio_bac, 2)
    budget_at_risk_bac = round(budget_at_risk_bac, 2)
    budget_at_risk_pct = (
        round((budget_at_risk_bac / total_portfolio_bac) * 100.0, 2)
        if total_portfolio_bac > 0
        else 0.0
    )

    if total_projects == 0:
        portfolio_status = "empty_portfolio"
    elif budget_at_risk_pct >= 30.0 or (critical_projects_count / total_projects) >= 0.4:
        portfolio_status = "systemic_distress"
    elif critical_projects_count >= 1 or watchlist_projects_count > healthy_projects_count:
        portfolio_status = "elevated_exposure"
    else:
        portfolio_status = "balanced_healthy"

    return {
        "total_projects": total_projects,
        "healthy_projects_count": healthy_projects_count,
        "watchlist_projects_count": watchlist_projects_count,
        "critical_projects_count": critical_projects_count,
        "total_portfolio_bac": total_portfolio_bac,
        "budget_at_risk_bac": budget_at_risk_bac,
        "budget_at_risk_pct": budget_at_risk_pct,
        "portfolio_status": portfolio_status,
    }


def evaluate_phase_gate_transition_readiness(
    phase_tasks_total: int,
    phase_tasks_completed: int,
    open_critical_risks: int = 0,
    pending_ccb_changes: int = 0,
    exit_criteria_verified: bool = False,
) -> dict[str, Any]:
    """Audita la decisión de revisión de puerta de fase (Stage-Gate / Phase Gate Review — PMBOK §2.4.2.3)."""
    total = max(0, int(phase_tasks_total or 0))
    completed = min(total, max(0, int(phase_tasks_completed or 0)))
    crit_risks = max(0, int(open_critical_risks or 0))
    ccb_pending = max(0, int(pending_ccb_changes or 0))
    verified = bool(exit_criteria_verified)

    completion_pct = round((completed / total) * 100.0, 2) if total > 0 else 0.0

    gate_blockers: list[str] = []
    if total == 0:
        gate_blockers.append("empty_phase_scope")
    if total > 0 and completion_pct < 100.0:
        gate_blockers.append("incomplete_work_packages")
    if crit_risks > 0:
        gate_blockers.append("open_critical_risks")
    if ccb_pending > 0:
        gate_blockers.append("pending_ccb_decisions")
    if not verified:
        gate_blockers.append("unverified_exit_criteria")

    if len(gate_blockers) == 0:
        gate_decision = "proceed_to_next_phase"
    elif (
        total > 0
        and completion_pct >= 90.0
        and crit_risks == 0
        and ccb_pending <= 1
    ):
        gate_decision = "conditional_proceed_with_action_plan"
    else:
        gate_decision = "hold_at_current_phase"

    return {
        "phase_tasks_total": total,
        "phase_tasks_completed": completed,
        "completion_pct": completion_pct,
        "open_critical_risks": crit_risks,
        "pending_ccb_changes": ccb_pending,
        "exit_criteria_verified": verified,
        "gate_blockers": gate_blockers,
        "can_transition_cleanly": len(gate_blockers) == 0,
        "gate_decision": gate_decision,
    }


def evaluate_lessons_learned_institutional_reuse(
    lessons: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audita el aprendizaje institucional de Lessons Learned (PMBOK §4.4 / §4.7).

    Evalúa si las lecciones registradas son accionables, categorizadas y
    reutilizadas hacia los activos de proceso organizacional (OPA):
    - `total_lessons`: lecciones registradas (ítems dict).
    - `actionable_count`: items con `action_item`/`recommendation` >= 10 chars.
    - `categorized_count`: items con `category`/`knowledge_area` no vacío.
    - `reused_or_applied_count`: items con `reused` o `applied_to_opa` truthy.
    - `actionability_rate`: % accionables (2 decimales; 0.0 sin lecciones).
    - `opa_reuse_rate`: % reutilizadas en OPA (2 decimales; 0.0 sin lecciones).
    - `posture`: 'NO_LESSONS_RECORDED' sin lecciones;
      'INSTITUTIONALIZED_OPA_LEARNING' con accionables >= 75% y reuso >= 50%;
      'PASSIVE_ARCHIVE' con accionables >= 50% pero reuso < 50%;
      'LOW_QUALITY_RETROSPECTIVE' en otro caso.
    """
    items = [item for item in (lessons or []) if isinstance(item, dict)]
    total_lessons = len(items)

    actionable_count = 0
    categorized_count = 0
    reused_or_applied_count = 0
    for item in items:
        actionable_text = str(item.get("action_item") or item.get("recommendation") or "").strip()
        if len(actionable_text) >= 10:
            actionable_count += 1
        categorized_text = str(item.get("category") or item.get("knowledge_area") or "").strip()
        if categorized_text:
            categorized_count += 1
        if bool(item.get("reused") or item.get("applied_to_opa")):
            reused_or_applied_count += 1

    actionability_rate = (
        round((actionable_count / total_lessons) * 100.0, 2)
        if total_lessons > 0
        else 0.0
    )
    opa_reuse_rate = (
        round((reused_or_applied_count / total_lessons) * 100.0, 2)
        if total_lessons > 0
        else 0.0
    )

    if total_lessons == 0:
        posture = "NO_LESSONS_RECORDED"
    elif actionability_rate >= 75.0 and opa_reuse_rate >= 50.0:
        posture = "INSTITUTIONALIZED_OPA_LEARNING"
    elif actionability_rate >= 50.0 and opa_reuse_rate < 50.0:
        posture = "PASSIVE_ARCHIVE"
    else:
        posture = "LOW_QUALITY_RETROSPECTIVE"

    return {
        "total_lessons": total_lessons,
        "actionable_count": actionable_count,
        "categorized_count": categorized_count,
        "reused_or_applied_count": reused_or_applied_count,
        "actionability_rate": actionability_rate,
        "opa_reuse_rate": opa_reuse_rate,
        "posture": posture,
    }


def audit_lessons_learned_actionable_followup(
    lessons: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita el seguimiento accionable e integración OPA/CAPA de lecciones (PMBOK §4.4 y §4.7).

    Cada registro válido (dict con `id`/`lesson_id` no vacío) declara nivel de
    impacto (`impact_level`, default 'MEDIUM'), recomendación, responsable
    (`action_owner_id`), integración OPA (`opa_updated`) y estado
    (`status`, default 'OPEN'):
    - `missing_recommendation_ids`: sin recomendación accionable.
    - `unassigned_high_impact_ids`: HIGH/CRITICAL sin responsable de acción.
    - `uninstitutionalized_closed_ids`: ARCHIVED/CLOSED/INSTITUTIONALIZED sin OPA actualizada.
    - `is_lessons_followup_governed`: con lecciones y las 3 listas vacías.
    - `lessons_followup_posture`: 'NO_LESSONS_RECORDED' sin registros;
      'UNINSTITUTIONALIZED_OPA_CLOSURE'; 'UNASSIGNED_HIGH_IMPACT_LESSON';
      'MISSING_ACTIONABLE_RECOMMENDATION'; 'GOVERNED_LESSONS_FOLLOWUP'.
    """
    valid_lessons = [
        lesson
        for lesson in (lessons or [])
        if isinstance(lesson, dict) and str(lesson.get("id") or lesson.get("lesson_id") or "").strip()
    ]
    total_lessons = len(valid_lessons)
    if total_lessons == 0:
        return {
            "total_lessons": 0,
            "missing_recommendation_ids": [],
            "unassigned_high_impact_ids": [],
            "uninstitutionalized_closed_ids": [],
            "is_lessons_followup_governed": False,
            "lessons_followup_posture": "NO_LESSONS_RECORDED",
        }

    missing_recommendation_ids: list[str] = []
    unassigned_high_impact_ids: list[str] = []
    uninstitutionalized_closed_ids: list[str] = []

    for lesson in valid_lessons:
        lesson_id = str(lesson.get("id") or lesson.get("lesson_id") or "").strip()
        impact_level = str(lesson.get("impact_level") or "MEDIUM").strip().upper()
        recommendation = str(lesson.get("recommendation") or "").strip()
        action_owner_id = str(lesson.get("action_owner_id") or "").strip()
        opa_updated = bool(lesson.get("opa_updated", False))
        status = str(lesson.get("status") or "OPEN").strip().upper()

        if not recommendation:
            missing_recommendation_ids.append(lesson_id)
        if impact_level in {"HIGH", "CRITICAL"} and not action_owner_id:
            unassigned_high_impact_ids.append(lesson_id)
        if status in {"ARCHIVED", "CLOSED", "INSTITUTIONALIZED"} and not opa_updated:
            uninstitutionalized_closed_ids.append(lesson_id)

    is_lessons_followup_governed = bool(
        len(missing_recommendation_ids) == 0
        and len(unassigned_high_impact_ids) == 0
        and len(uninstitutionalized_closed_ids) == 0
    )

    if total_lessons == 0:
        lessons_followup_posture = "NO_LESSONS_RECORDED"
    elif len(uninstitutionalized_closed_ids) > 0:
        lessons_followup_posture = "UNINSTITUTIONALIZED_OPA_CLOSURE"
    elif len(unassigned_high_impact_ids) > 0:
        lessons_followup_posture = "UNASSIGNED_HIGH_IMPACT_LESSON"
    elif len(missing_recommendation_ids) > 0:
        lessons_followup_posture = "MISSING_ACTIONABLE_RECOMMENDATION"
    else:
        lessons_followup_posture = "GOVERNED_LESSONS_FOLLOWUP"

    return {
        "total_lessons": total_lessons,
        "missing_recommendation_ids": missing_recommendation_ids,
        "unassigned_high_impact_ids": unassigned_high_impact_ids,
        "uninstitutionalized_closed_ids": uninstitutionalized_closed_ids,
        "is_lessons_followup_governed": is_lessons_followup_governed,
        "lessons_followup_posture": lessons_followup_posture,
    }


class ProjectLifecyclePMIService:
    """Canonical facade for PMI project lifecycle, governance maturity, and automation readiness."""

    @staticmethod
    def evaluate_lessons_learned_institutional_reuse(
        lessons: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return evaluate_lessons_learned_institutional_reuse(lessons)

    @staticmethod
    def audit_lessons_learned_actionable_followup(
        lessons: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return audit_lessons_learned_actionable_followup(lessons)

    @staticmethod
    def audit_charter_measurable_objectives(
        objectives: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return audit_charter_measurable_objectives(objectives)

    @staticmethod
    def compute_closure_readiness_pct(
        deliverables_accepted_verified: bool,
        financial_reconciliation_completed: bool,
        lessons_learned_count: int,
        closure_status: str,
    ) -> float:
        return compute_closure_readiness_pct(
            deliverables_accepted_verified=deliverables_accepted_verified,
            financial_reconciliation_completed=financial_reconciliation_completed,
            lessons_learned_count=lessons_learned_count,
            closure_status=closure_status,
        )

    @staticmethod
    def compute_governance_maturity_pct(
        charter_status: str,
        measurable_objectives_count: int,
        stakeholders_total: int,
        closure_readiness_pct: float,
    ) -> float:
        return compute_governance_maturity_pct(
            charter_status=charter_status,
            measurable_objectives_count=measurable_objectives_count,
            stakeholders_total=stakeholders_total,
            closure_readiness_pct=closure_readiness_pct,
        )

    @staticmethod
    def evaluate_governance_health(summary: dict) -> dict:
        return evaluate_governance_health(summary)

    @staticmethod
    def evaluate_automation_governance_readiness(
        rules: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return evaluate_automation_governance_readiness(rules)

    @staticmethod
    def evaluate_stakeholder_engagement_gaps(
        stakeholders: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return evaluate_stakeholder_engagement_gaps(stakeholders)

    @staticmethod
    def evaluate_charter_authorization_readiness(
        charter_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return evaluate_charter_authorization_readiness(charter_data)

    @staticmethod
    def evaluate_administrative_closure_audit(
        closure_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return evaluate_administrative_closure_audit(closure_data)

    @staticmethod
    def evaluate_pmo_portfolio_health_balance(
        projects: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return evaluate_pmo_portfolio_health_balance(projects)

    @staticmethod
    def evaluate_phase_gate_transition_readiness(
        phase_tasks_total: int,
        phase_tasks_completed: int,
        open_critical_risks: int = 0,
        pending_ccb_changes: int = 0,
        exit_criteria_verified: bool = False,
    ) -> dict[str, Any]:
        return evaluate_phase_gate_transition_readiness(
            phase_tasks_total=phase_tasks_total,
            phase_tasks_completed=phase_tasks_completed,
            open_critical_risks=open_critical_risks,
            pending_ccb_changes=pending_ccb_changes,
            exit_criteria_verified=exit_criteria_verified,
        )

    @staticmethod
    def evaluate_benefits_realization_posture(
        benefits: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return evaluate_benefits_realization_posture(benefits)

    @staticmethod
    def audit_assumption_and_constraint_log_governance(
        entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return audit_assumption_and_constraint_log_governance(entries)

    @staticmethod
    def audit_stakeholder_communication_cadence(
        stakeholders: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return audit_stakeholder_communication_cadence(stakeholders)

    @staticmethod
    def audit_assumption_and_constraint_log(
        entries: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return audit_assumption_and_constraint_log(entries)

    @staticmethod
    def audit_project_procurement_and_handover_closeout(
        contracts: list[dict[str, Any]] | None = None,
        handover_items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return audit_project_procurement_and_handover_closeout(
            contracts=contracts, handover_items=handover_items
        )

    @staticmethod
    def audit_stakeholder_engagement_transition_gaps(
        stakeholders: Optional[list[dict]],
    ) -> dict:
        return audit_stakeholder_engagement_transition_gaps(stakeholders)

    @staticmethod
    def audit_project_tailoring_and_opa_compliance(
        tailoring_decisions: Optional[list[dict]],
        mandatory_opa_templates: Optional[list[str]] = None,
    ) -> dict:
        return audit_project_tailoring_and_opa_compliance(
            tailoring_decisions,
            mandatory_opa_templates=mandatory_opa_templates,
        )

    @staticmethod
    def audit_benefits_realization_sustainability(
        benefits: Optional[list[dict[str, Any]]],
        min_realization_ratio_pct: float = 80.0,
    ) -> dict[str, Any]:
        return audit_benefits_realization_sustainability(
            benefits, min_realization_ratio_pct=min_realization_ratio_pct
        )

    @staticmethod
    def audit_team_charter_and_tuckman_governance(
        team_charter: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        return audit_team_charter_and_tuckman_governance(team_charter)

    @staticmethod
    def audit_phase_gate_transition_readiness(
        phase_gates: Optional[list[dict[str, Any]]] = None,
        min_exit_criteria_pass_pct: float = 100.0,
    ) -> dict[str, Any]:
        return audit_phase_gate_transition_readiness(
            phase_gates,
            min_exit_criteria_pass_pct=min_exit_criteria_pass_pct,
        )


def audit_charter_measurable_objectives(
    objectives: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audita objetivos medibles del Project Charter (PMBOK §4.1 — SMART).

    Ignora entradas que no sean dict y calcula:
    - `total_objectives`: objetivos válidos.
    - `quantified_target_count`: items con `target_value` distinto de None o
      texto de `metric`/`target` con dígito, '%' o '$'.
    - `time_bound_count`: items con `deadline`/`due_date`/`timeframe` no vacío.
    - `smart_compliant_count`: meta cuantificada Y plazo temporal Y
      descripción/título con >= 10 caracteres.
    - `smart_compliance_rate`: % SMART (2 decimales; 0.0 sin objetivos).
    - `posture`: 'NO_CHARTER_OBJECTIVES' sin objetivos;
      'SMART_GOVERNANCE_ALIGNED' con rate >= 80.0; 'PARTIALLY_MEASURABLE'
      con rate >= 40.0; 'VAGUE_UNMEASURABLE_OBJECTIVES' en otro caso.
    """
    items = [item for item in (objectives or []) if isinstance(item, dict)]
    total_objectives = len(items)

    quantified_target_count = 0
    time_bound_count = 0
    smart_compliant_count = 0
    for item in items:
        quantitative_text = str(item.get("metric") or item.get("target") or "").strip()
        is_quantified = item.get("target_value") is not None or re.search(
            r"[\d%$]", quantitative_text
        ) is not None
        time_bound_text = str(
            item.get("deadline") or item.get("due_date") or item.get("timeframe") or ""
        ).strip()
        is_time_bound = bool(time_bound_text)
        description_text = str(item.get("description") or item.get("title") or "").strip()

        if is_quantified:
            quantified_target_count += 1
        if is_time_bound:
            time_bound_count += 1
        if is_quantified and is_time_bound and len(description_text) >= 10:
            smart_compliant_count += 1

    smart_compliance_rate = (
        round((smart_compliant_count / total_objectives) * 100.0, 2)
        if total_objectives > 0
        else 0.0
    )

    if total_objectives == 0:
        posture = "NO_CHARTER_OBJECTIVES"
    elif smart_compliance_rate >= 80.0:
        posture = "SMART_GOVERNANCE_ALIGNED"
    elif smart_compliance_rate >= 40.0:
        posture = "PARTIALLY_MEASURABLE"
    else:
        posture = "VAGUE_UNMEASURABLE_OBJECTIVES"

    return {
        "total_objectives": total_objectives,
        "quantified_target_count": quantified_target_count,
        "time_bound_count": time_bound_count,
        "smart_compliant_count": smart_compliant_count,
        "smart_compliance_rate": smart_compliance_rate,
        "posture": posture,
    }


def audit_stakeholder_communication_cadence(
    stakeholders: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audita el plan de comunicaciones de interesados (PMBOK §10.1 / §13.2).

    Ignora entradas que no sean dict y calcula:
    - `total_stakeholders`: interesados validos.
    - `channel_defined_count`: items con `channel`/`preferred_channel`/
      `canal` no vacío.
    - `cadence_defined_count`: items con `cadence`/`frequency`/`frecuencia`
      dentro de la gramatica valida (daily/diaria, weekly/semanal,
      biweekly/quincenal, monthly/mensual, milestone/por_hito).
    - `fully_planned_count`: canal definido Y cadencia valida.
    - `coverage_rate`: % de interesados con plan completo (2 decimales;
      0.0 sin interesados).
    - `posture`: 'NO_STAKEHOLDERS_REGISTERED' sin interesados;
      'GOVERNED_COMMUNICATION_PLAN' con coverage >= 80.0;
      'PARTIAL_COMMUNICATION_PLAN' con coverage >= 40.0; y
      'UNPLANNED_STAKEHOLDER_OUTREACH' en otro caso.
    """
    VALID_CADENCES = {
        "daily", "diaria", "weekly", "semanal", "biweekly", "quincenal",
        "monthly", "mensual", "milestone", "por_hito",
    }

    items = [item for item in (stakeholders or []) if isinstance(item, dict)]
    total_stakeholders = len(items)

    channel_defined_count = 0
    cadence_defined_count = 0
    fully_planned_count = 0
    for item in items:
        channel_text = str(
            item.get("channel")
            or item.get("preferred_channel")
            or item.get("canal")
            or ""
        ).strip()
        cadence_text = str(
            item.get("cadence")
            or item.get("frequency")
            or item.get("frecuencia")
            or ""
        ).strip().lower()

        has_channel = bool(channel_text)
        has_cadence = cadence_text in VALID_CADENCES
        if has_channel:
            channel_defined_count += 1
        if has_cadence:
            cadence_defined_count += 1
        if has_channel and has_cadence:
            fully_planned_count += 1

    coverage_rate = (
        round((fully_planned_count / total_stakeholders) * 100.0, 2)
        if total_stakeholders > 0
        else 0.0
    )

    if total_stakeholders == 0:
        posture = "NO_STAKEHOLDERS_REGISTERED"
    elif coverage_rate >= 80.0:
        posture = "GOVERNED_COMMUNICATION_PLAN"
    elif coverage_rate >= 40.0:
        posture = "PARTIAL_COMMUNICATION_PLAN"
    else:
        posture = "UNPLANNED_STAKEHOLDER_OUTREACH"

    return {
        "total_stakeholders": total_stakeholders,
        "channel_defined_count": channel_defined_count,
        "cadence_defined_count": cadence_defined_count,
        "fully_planned_count": fully_planned_count,
        "coverage_rate": coverage_rate,
        "posture": posture,
    }


def evaluate_benefits_realization_posture(
    benefits: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Evalúa el Plan de Gestión de Beneficios (BRM) según PMI PMBOK §1.2.6 y §4.7."""
    items = [item for item in (benefits or []) if isinstance(item, dict)]
    total_benefits = len(items)

    owner_assigned_count = 0
    realized_count = 0
    at_risk_count = 0

    for item in items:
        owner_str = str(
            item.get("benefit_owner")
            or item.get("owner")
            or item.get("responsable")
            or ""
        ).strip()
        if owner_str:
            owner_assigned_count += 1

        target_val = float(item.get("target_value") or 0.0)
        actual_val = float(item.get("actual_value") or 0.0)
        status_str = str(item.get("status") or "").strip().lower()

        if (target_val > 0.0 and actual_val >= target_val) or status_str in (
            "realized",
            "achieved",
            "cumplido",
            "logrado",
        ):
            realized_count += 1

        if status_str in (
            "at_risk",
            "en_riesgo",
            "delayed",
            "retrasado",
            "off_track",
        ):
            at_risk_count += 1

    realization_rate = (
        round((realized_count / total_benefits) * 100.0, 2)
        if total_benefits > 0
        else 0.0
    )

    if total_benefits == 0:
        posture = "NO_BENEFITS_DEFINED"
    elif at_risk_count > 0 or owner_assigned_count < total_benefits:
        posture = "BENEFITS_REALIZATION_AT_RISK"
    elif (
        at_risk_count == 0
        and owner_assigned_count == total_benefits
        and realization_rate >= 75.0
    ):
        posture = "SUSTAINED_VALUE_REALIZATION"
    else:
        posture = "BENEFITS_TRACKING_IN_PROGRESS"

    return {
        "total_benefits": total_benefits,
        "owner_assigned_count": owner_assigned_count,
        "realized_count": realized_count,
        "at_risk_count": at_risk_count,
        "realization_rate": realization_rate,
        "posture": posture,
    }


def audit_assumption_and_constraint_log_governance(
    entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita el Registro de Supuestos y Restricciones (PMBOK §4.1.3.2).

    Cada entrada declara `id`/`entry_id`/`code` (fallback 'ASM-{idx}'),
    responsable (`owner`/`validation_owner`/`responsable`), criterio de
    validacion (`validation_method`/`verification_criteria`/
    `next_review_date`), estado (`status`/`state`) y el vínculo a riesgo/CR
    (`linked_risk_id`/`linked_cr_id`/`impact_reference`):
    - `unowned_entry_ids`: sin responsable.
    - `unverifiable_entry_ids`: sin criterio o fecha de validacion.
    - `unlinked_invalidated_ids`: entradas invalidadas
      ({invalidated, invalid, false, broken, violated, invalido, incumplido})
      sin vinculo a riesgo o CR.
    - `is_assumption_log_governed`: las 3 listas vacias.
    - `assumption_log_posture`: 'NO_ASSUMPTIONS_LOGGED' vacio;
      'UNLINKED_INVALIDATED_ASSUMPTION'; 'UNOWNED_ASSUMPTION_ENTRY';
      'MISSING_VALIDATION_CRITERIA'; 'GOVERNED_ASSUMPTION_LOG'.
    """
    INVALIDATED_STATUSES = {
        "invalidated", "invalid", "false", "broken", "violated", "invalido", "incumplido",
    }
    records = [e for e in (entries or []) if isinstance(e, dict)]
    if not records:
        return {
            "total_entries": 0,
            "invalidated_count": 0,
            "unowned_entry_ids": [],
            "unverifiable_entry_ids": [],
            "unlinked_invalidated_ids": [],
            "is_assumption_log_governed": True,
            "assumption_log_posture": "NO_ASSUMPTIONS_LOGGED",
        }

    total_entries = len(records)
    invalidated_count = 0
    unowned_entry_ids: list[str] = []
    unverifiable_entry_ids: list[str] = []
    unlinked_invalidated_ids: list[str] = []

    for idx, item in enumerate(records, start=1):
        entry_id = str(
            item.get("id") or item.get("entry_id") or item.get("code") or f"ASM-{idx}"
        ).strip()
        owner = str(
            item.get("owner") or item.get("validation_owner") or item.get("responsable") or ""
        ).strip()
        validation_method = str(
            item.get("validation_method")
            or item.get("verification_criteria")
            or item.get("next_review_date")
            or ""
        ).strip()
        status = str(item.get("status") or item.get("state") or "valid").strip().lower()
        linked_ref = str(
            item.get("linked_risk_id")
            or item.get("linked_cr_id")
            or item.get("impact_reference")
            or ""
        ).strip()

        if not owner:
            unowned_entry_ids.append(entry_id)
        if not validation_method:
            unverifiable_entry_ids.append(entry_id)
        if status in INVALIDATED_STATUSES:
            invalidated_count += 1
            if not linked_ref:
                unlinked_invalidated_ids.append(entry_id)

    is_assumption_log_governed = bool(
        len(unowned_entry_ids) == 0
        and len(unverifiable_entry_ids) == 0
        and len(unlinked_invalidated_ids) == 0
    )

    if total_entries == 0:
        assumption_log_posture = "NO_ASSUMPTIONS_LOGGED"
    elif len(unlinked_invalidated_ids) > 0:
        assumption_log_posture = "UNLINKED_INVALIDATED_ASSUMPTION"
    elif len(unowned_entry_ids) > 0:
        assumption_log_posture = "UNOWNED_ASSUMPTION_ENTRY"
    elif len(unverifiable_entry_ids) > 0:
        assumption_log_posture = "MISSING_VALIDATION_CRITERIA"
    else:
        assumption_log_posture = "GOVERNED_ASSUMPTION_LOG"

    return {
        "total_entries": total_entries,
        "invalidated_count": invalidated_count,
        "unowned_entry_ids": unowned_entry_ids,
        "unverifiable_entry_ids": unverifiable_entry_ids,
        "unlinked_invalidated_ids": unlinked_invalidated_ids,
        "is_assumption_log_governed": is_assumption_log_governed,
        "assumption_log_posture": assumption_log_posture,
    }


def audit_assumption_and_constraint_log(
    entries: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audita el Registro de Supuestos y Restricciones (PMBOK §4.1 / §11.2).

    Ignora entradas que no sean dict y clasifica cada registro por su campo
    `type`/`kind` (default 'assumption'):
    - `assumptions_count`: supuestos ('assumption', 'supuesto',
      'hipotesis'/'hipótesis').
    - `constraints_count`: restricciones ('constraint', 'restriccion'/'restricción',
      'limitacion'/'limitación').
    - `validated_or_active_count`: status en ('validated', 'validado', 'active',
      'activo', 'confirmed', 'confirmado') Y con `owner`/`responsable`.
    - `invalidated_count`: status en ('invalidated', 'invalidado', 'false',
      'broken', 'escalated_to_risk') que exige conversión a riesgo.
    - `governance_coverage_rate`: % de entradas validadas/activas con dueño
      (2 decimales; 0.0 sin entradas).
    - `posture`: 'EMPTY_ASSUMPTION_LOG' sin entradas;
      'UNCONVERTED_INVALIDATED_ASSUMPTIONS' con invalidados;
      'GOVERNED_ASSUMPTION_LOG' con coverage >= 80.0; y
      'UNVALIDATED_ASSUMPTION_EXPOSURE' en otro caso.
    """
    ASSUMPTION_TYPES = {"assumption", "supuesto", "hipotesis", "hipótesis"}
    CONSTRAINT_TYPES = {
        "constraint", "restriccion", "restricción", "limitacion", "limitación"
    }
    VALIDATED_STATUSES = {
        "validated", "validado", "active", "activo", "confirmed", "confirmado"
    }
    INVALIDATED_STATUSES = {
        "invalidated", "invalidado", "false", "broken", "escalated_to_risk"
    }

    items = [item for item in (entries or []) if isinstance(item, dict)]
    total_entries = len(items)

    assumptions_count = 0
    constraints_count = 0
    validated_or_active_count = 0
    invalidated_count = 0

    for item in items:
        type_text = str(item.get("type") or item.get("kind") or "assumption").strip().lower()
        status_text = str(item.get("status") or "").strip().lower()
        owner_text = str(item.get("owner") or item.get("responsable") or "").strip()

        if type_text in ASSUMPTION_TYPES:
            assumptions_count += 1
        elif type_text in CONSTRAINT_TYPES:
            constraints_count += 1

        if status_text in INVALIDATED_STATUSES:
            invalidated_count += 1
        elif status_text in VALIDATED_STATUSES and owner_text:
            validated_or_active_count += 1

    governance_coverage_rate = (
        round((validated_or_active_count / total_entries) * 100.0, 2)
        if total_entries > 0
        else 0.0
    )

    if total_entries == 0:
        posture = "EMPTY_ASSUMPTION_LOG"
    elif invalidated_count > 0:
        posture = "UNCONVERTED_INVALIDATED_ASSUMPTIONS"
    elif governance_coverage_rate >= 80.0:
        posture = "GOVERNED_ASSUMPTION_LOG"
    else:
        posture = "UNVALIDATED_ASSUMPTION_EXPOSURE"

    return {
        "total_entries": total_entries,
        "assumptions_count": assumptions_count,
        "constraints_count": constraints_count,
        "validated_or_active_count": validated_or_active_count,
        "invalidated_count": invalidated_count,
        "governance_coverage_rate": governance_coverage_rate,
        "posture": posture,
    }


def audit_project_procurement_and_handover_closeout(
    contracts: list[dict[str, Any]] | None = None,
    handover_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita el cierre administrativo, liquidación de adquisiciones y traspaso a operaciones (PMBOK §4.7 y §12.3)."""
    contract_items = [item for item in (contracts or []) if isinstance(item, dict)]
    handover_list = [item for item in (handover_items or []) if isinstance(item, dict)]

    total_contracts = len(contract_items)
    open_contract_ids: list[str] = []
    disputed_contract_ids: list[str] = []

    for idx, item in enumerate(contract_items, start=1):
        raw_id = item.get("id") if item.get("id") is not None else item.get("contract_id")
        contract_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"CTR-{idx}"
        )

        status_upper = str(item.get("status") or "").strip().upper()
        raw_claims = item.get("open_claims", 0)
        if isinstance(raw_claims, bool):
            has_open_claims = raw_claims
        elif isinstance(raw_claims, (int, float)):
            has_open_claims = raw_claims > 0
        else:
            has_open_claims = str(raw_claims or "").strip().lower() not in (
                "",
                "0",
                "false",
                "no",
                "none",
            )

        final_invoice_paid = item.get("final_invoice_paid") is True

        if status_upper not in ("CLOSED", "SETTLED") or not final_invoice_paid:
            open_contract_ids.append(contract_id)

        if status_upper == "DISPUTED" or has_open_claims:
            disputed_contract_ids.append(contract_id)

    total_handover_items = len(handover_list)
    pending_handover_ids: list[str] = []
    invalid_owner_tokens = {"TBD", "N/A", "SIN ASIGNAR", "NONE", "NULL", "-"}

    for idx, item in enumerate(handover_list, start=1):
        raw_id = (
            item.get("id")
            if item.get("id") is not None
            else item.get("deliverable_id")
        )
        item_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"HND-{idx}"
        )

        transferred = item.get("transferred_to_operations") is True
        owner_str = str(item.get("operations_owner") or "").strip()
        has_valid_owner = (
            bool(owner_str)
            and owner_str.upper().rstrip(".") not in invalid_owner_tokens
        )

        if not transferred or not has_valid_owner:
            pending_handover_ids.append(item_id)

    ready_for_administrative_closure = bool(
        (total_contracts + total_handover_items) > 0
        and len(open_contract_ids) == 0
        and len(disputed_contract_ids) == 0
        and len(pending_handover_ids) == 0
    )

    recommendations: list[str] = []
    if total_contracts == 0 and total_handover_items == 0:
        closeout_posture = "NO_CLOSEOUT_ARTIFACTS"
        recommendations.append(
            "Registrar el inventario de contratos de adquisición (PMBOK §12.3) y entregables de transferencia a operaciones (§4.7) antes de iniciar el cierre."
        )
    elif len(disputed_contract_ids) > 0:
        closeout_posture = "PROCUREMENT_CLAIMS_BLOCKED"
        recommendations.append(
            f"Resolver reclamos o disputas contractuales abiertas en {', '.join(disputed_contract_ids)} mediante negociación directa o ADR (PMBOK §12.3) antes del cierre administrativo."
        )
        if pending_handover_ids:
            recommendations.append(
                f"Completar transferencia formal a operaciones y asignación de dueño en {', '.join(pending_handover_ids)} (PMBOK §4.7)."
            )
    elif len(open_contract_ids) > 0 or len(pending_handover_ids) > 0:
        closeout_posture = "PENDING_CONTRACT_OR_HANDOVER_CLOSEOUT"
        if open_contract_ids:
            recommendations.append(
                f"Liquidar facturas finales y emitir finiquito formal en contratos abiertos: {', '.join(open_contract_ids)} (PMBOK §12.3)."
            )
        if pending_handover_ids:
            recommendations.append(
                f"Formalizar acta de recepción operativa y responsable de sostenimiento para: {', '.join(pending_handover_ids)} (PMBOK §4.7)."
            )
    else:
        closeout_posture = "ADMINISTRATIVE_CLOSURE_READY"
        recommendations.append(
            "Todos los contratos están liquidados sin reclamos y los entregables fueron transferidos a operaciones. Proceder con el cierre administrativo final (PMBOK §4.7)."
        )

    return {
        "total_contracts": total_contracts,
        "open_contract_ids": open_contract_ids,
        "disputed_contract_ids": disputed_contract_ids,
        "total_handover_items": total_handover_items,
        "pending_handover_ids": pending_handover_ids,
        "ready_for_administrative_closure": ready_for_administrative_closure,
        "closeout_posture": closeout_posture,
        "recommendations": recommendations,
    }


def audit_stakeholder_engagement_transition_gaps(
    stakeholders: Optional[list[dict]],
) -> dict:
    """Audita la matriz de evaluación de engagement de interesados (PMBOK §13.2 / §13.4).

    Escala SEAM: UNAWARE/DESCONOCEDOR=1, RESISTANT/RESISTENTE=2, NEUTRAL=3,
    SUPPORTIVE/PARTIDARIO/APOYO=4, LEADING/LIDER/LÍDER=5 (defaults: current
    NEUTRAL, desired SUPPORTIVE).
    - `gap_count`: interesados con `current_rank` < `desired_rank`.
    - `high_power_resistant_ids`: ids con current_rank <= 2 y alto poder
      (`influence`/`power` en ('HIGH','ALTA','CRITICAL') o int >= 4).
    - `unaddressed_gap_ids`: gaps sin plan de acción (`action_plan` < 8 chars).
    - `alignment_rate_pct`: % de interesados en o sobre su nivel deseado
      (2 decimales; 0.0 sin interesados).
    - `seam_posture`: 'EMPTY_STAKEHOLDER_MATRIX' sin interesados;
      'CRITICAL_HIGH_POWER_RESISTANCE' con resistencia de alto poder;
      'UNADDRESSED_ENGAGEMENT_GAPS' con gaps sin plan; y
      'ALIGNED_ENGAGEMENT_MATRIX' en el caso alineado.
    - `recommendations`: acciones correctivas según el hallazgo.
    """
    SEAM_RANKS = {
        "unaware": 1, "desconocedor": 1,
        "resistant": 2, "resistente": 2,
        "neutral": 3,
        "supportive": 4, "partidario": 4, "apoyo": 4,
        "leading": 5, "lider": 5, "líder": 5,
    }
    HIGH_POWER_TEXTS = {"high", "alta", "high_power", "critico", "crítico", "critical"}

    items = [item for item in (stakeholders or []) if isinstance(item, dict)]
    total_stakeholders = len(items)

    def _rank(value: Any, fallback: int) -> int:
        text = str(value or "").strip().lower()
        if text in SEAM_RANKS:
            return SEAM_RANKS[text]
        try:
            numeric = int(float(text))
        except (TypeError, ValueError):
            return fallback
        return min(5, max(1, numeric))

    gap_count = 0
    high_power_resistant_ids: list[str] = []
    unaddressed_gap_ids: list[str] = []

    for item in items:
        stakeholder_id = str(item.get("id") or item.get("name") or "").strip()
        current_rank = _rank(
            item.get("current_engagement") or item.get("current_level") or "NEUTRAL",
            3,
        )
        desired_rank = _rank(
            item.get("desired_engagement") or item.get("desired_level") or "SUPPORTIVE",
            4,
        )

        power_raw = item.get("influence") or item.get("power") or ""
        power_text = str(power_raw).strip().lower()
        try:
            power_numeric = int(float(power_text))
        except (TypeError, ValueError):
            power_numeric = None
        is_high_power = power_text in HIGH_POWER_TEXTS or (
            power_numeric is not None and power_numeric >= 4
        )

        has_gap = current_rank < desired_rank
        if has_gap:
            gap_count += 1

        if current_rank <= 2 and is_high_power:
            high_power_resistant_ids.append(stakeholder_id)

        action_plan_text = str(item.get("action_plan") or "").strip()
        if has_gap and len(action_plan_text) < 8:
            unaddressed_gap_ids.append(stakeholder_id)

    alignment_rate_pct = (
        round(((total_stakeholders - gap_count) / total_stakeholders) * 100.0, 2)
        if total_stakeholders > 0
        else 0.0
    )

    if total_stakeholders == 0:
        seam_posture = "EMPTY_STAKEHOLDER_MATRIX"
    elif high_power_resistant_ids:
        seam_posture = "CRITICAL_HIGH_POWER_RESISTANCE"
    elif unaddressed_gap_ids:
        seam_posture = "UNADDRESSED_ENGAGEMENT_GAPS"
    else:
        seam_posture = "ALIGNED_ENGAGEMENT_MATRIX"

    recommendations: list[str] = []
    if seam_posture == "CRITICAL_HIGH_POWER_RESISTANCE":
        recommendations.append(
            "Escalar inmediatamente la resistencia de interesados de alto poder con patrocinio ejecutivo (PMBOK §13.4)."
        )
    if seam_posture == "UNADDRESSED_ENGAGEMENT_GAPS":
        recommendations.append(
            "Elaborar planes de acción específicos para los gaps de engagement sin tratamiento."
        )
    if seam_posture == "ALIGNED_ENGAGEMENT_MATRIX":
        recommendations.append(
            "Reevaluar la matriz SEAM en cada milestone para sostener el alineamiento (PMBOK §13.2)."
        )
    if seam_posture == "EMPTY_STAKEHOLDER_MATRIX":
        recommendations.append(
            "Registrar los interesados con niveles actual y deseado para iniciar la matriz SEAM."
        )

    return {
        "total_stakeholders": total_stakeholders,
        "gap_count": gap_count,
        "high_power_resistant_ids": high_power_resistant_ids,
        "unaddressed_gap_ids": unaddressed_gap_ids,
        "alignment_rate_pct": alignment_rate_pct,
        "seam_posture": seam_posture,
        "recommendations": recommendations,
    }


def audit_project_tailoring_and_opa_compliance(
    tailoring_decisions: Optional[list[dict]],
    mandatory_opa_templates: Optional[list[str]] = None,
) -> dict:
    """Audita las decisiones de adaptación metodológica (Tailoring) y adopción de OPAs según PMI PMBOK §2.2 / §4.1."""
    items = [item for item in (tailoring_decisions or []) if isinstance(item, dict)]
    total_tailoring_decisions = len(items)

    unjustified_or_unapproved_areas: list[str] = []
    adopted_opas_lower: set[str] = set()

    for idx, item in enumerate(items, start=1):
        raw_area = (
            item.get("process_area")
            if item.get("process_area") is not None
            else item.get("knowledge_area")
        )
        area_name = (
            str(raw_area).strip()
            if raw_area is not None and str(raw_area).strip()
            else f"AREA-{idx}"
        )

        justification_clean = str(item.get("justification") or "").strip()
        pmo_approved = bool(item.get("pmo_approved", False))

        if not pmo_approved or len(justification_clean) < 10:
            unjustified_or_unapproved_areas.append(area_name)

        opa_ref = str(item.get("opa_template_ref") or "").strip()
        if opa_ref:
            adopted_opas_lower.add(opa_ref.lower())

    missing_mandatory_opas: list[str] = []
    for raw_tpl in mandatory_opa_templates or []:
        if not isinstance(raw_tpl, str):
            continue
        tpl_clean = raw_tpl.strip()
        if not tpl_clean:
            continue
        if tpl_clean.lower() not in adopted_opas_lower:
            missing_mandatory_opas.append(tpl_clean)

    compliance_rate_pct = (
        round(
            (
                (total_tailoring_decisions - len(unjustified_or_unapproved_areas))
                / total_tailoring_decisions
            )
            * 100.0,
            2,
        )
        if total_tailoring_decisions > 0
        else 0.0
    )

    recommendations: list[str] = []
    if total_tailoring_decisions == 0 and len(missing_mandatory_opas) == 0:
        tailoring_posture = "NO_TAILORING_RECORDED"
        recommendations.append(
            "Documentar las decisiones de adaptación metodológica (Tailoring) y plantillas OPA requeridas según el ciclo de vida del proyecto (PMBOK §2.2 / §4.1)."
        )
    elif len(missing_mandatory_opas) > 0:
        tailoring_posture = "MISSING_MANDATORY_OPA_TEMPLATES"
        recommendations.append(
            f"Vincular e incorporar las plantillas OPA obligatorias faltantes ({', '.join(missing_mandatory_opas)}) en el plan de dirección del proyecto (PMBOK §2.2)."
        )
    elif len(unjustified_or_unapproved_areas) > 0:
        tailoring_posture = "UNAPPROVED_TAILORING_DEVIATIONS"
        recommendations.append(
            f"Formalizar la justificación técnica (>=10 caracteres) y obtener aprobación de la PMO para las áreas adaptadas ({', '.join(unjustified_or_unapproved_areas)}) conforme a PMBOK §4.1."
        )
    else:
        tailoring_posture = "GOVERNED_METHODOLOGY_TAILORING"
        recommendations.append(
            "Adaptación metodológica gobernada y alineada con los Activos de los Procesos de la Organización (OPAs) y directrices PMO (PMBOK §2.2 / §4.1)."
        )

    return {
        "total_tailoring_decisions": total_tailoring_decisions,
        "unjustified_or_unapproved_areas": unjustified_or_unapproved_areas,
        "missing_mandatory_opas": missing_mandatory_opas,
        "compliance_rate_pct": compliance_rate_pct,
        "tailoring_posture": tailoring_posture,
        "recommendations": recommendations,
    }


def audit_benefits_realization_sustainability(
    benefits: Optional[list[dict[str, Any]]],
    min_realization_ratio_pct: float = 80.0,
) -> dict[str, Any]:
    """Audita la realización y sostenibilidad post-implementación de beneficios del proyecto según PMI PMBOK §1.2.6.4."""
    items = [item for item in (benefits or []) if isinstance(item, dict)]
    total_benefits = len(items)

    if total_benefits == 0:
        return {
            "total_benefits": 0,
            "overall_realization_pct": 0.0,
            "unowned_or_unscheduled_benefit_ids": [],
            "unquantified_benefit_ids": [],
            "underperforming_benefit_ids": [],
            "is_sustainable": False,
            "benefits_posture": "NO_BENEFITS_REGISTERED",
        }

    unowned_or_unscheduled_benefit_ids: list[str] = []
    unquantified_benefit_ids: list[str] = []
    underperforming_benefit_ids: list[str] = []
    sum_target = 0.0
    sum_realized = 0.0

    try:
        min_ratio = float(min_realization_ratio_pct)
    except (TypeError, ValueError):
        min_ratio = 80.0

    for idx, item in enumerate(items, start=1):
        benefit_id = (
            str(item.get("id") or item.get("benefit_id") or "").strip()
            or f"BEN-{idx}"
        )
        owner = str(item.get("benefit_owner") or item.get("owner") or "").strip()
        cadence = str(
            item.get("measurement_cadence") or item.get("review_horizon") or ""
        ).strip()

        raw_target = (
            item.get("target_value")
            if item.get("target_value") is not None
            else item.get("target")
        )
        try:
            target_value = max(0.0, float(raw_target or 0.0))
        except (TypeError, ValueError):
            target_value = 0.0

        raw_realized = (
            item.get("realized_value")
            if item.get("realized_value") is not None
            else item.get("actual_value")
        )
        try:
            realized_value = max(0.0, float(raw_realized or 0.0))
        except (TypeError, ValueError):
            realized_value = 0.0

        if not owner or not cadence:
            unowned_or_unscheduled_benefit_ids.append(benefit_id)

        if target_value <= 0.0:
            unquantified_benefit_ids.append(benefit_id)
        else:
            sum_target += target_value
            sum_realized += realized_value
            ratio_pct = (realized_value / target_value) * 100.0
            if ratio_pct < min_ratio:
                underperforming_benefit_ids.append(benefit_id)

    overall_realization_pct = (
        round((sum_realized / sum_target) * 100.0, 2) if sum_target > 0.0 else 0.0
    )

    is_sustainable = bool(
        total_benefits > 0
        and len(unowned_or_unscheduled_benefit_ids) == 0
        and len(unquantified_benefit_ids) == 0
        and len(underperforming_benefit_ids) == 0
    )

    if len(unowned_or_unscheduled_benefit_ids) > 0:
        benefits_posture = "MISSING_BENEFIT_OWNERSHIP_OR_CADENCE"
    elif len(unquantified_benefit_ids) > 0:
        benefits_posture = "UNQUANTIFIED_BENEFIT_TARGETS"
    elif len(underperforming_benefit_ids) > 0:
        benefits_posture = "BENEFITS_REALIZATION_SHORTFALL"
    else:
        benefits_posture = "SUSTAINABLE_BENEFITS_REALIZATION"

    return {
        "total_benefits": total_benefits,
        "overall_realization_pct": overall_realization_pct,
        "unowned_or_unscheduled_benefit_ids": unowned_or_unscheduled_benefit_ids,
        "unquantified_benefit_ids": unquantified_benefit_ids,
        "underperforming_benefit_ids": underperforming_benefit_ids,
        "is_sustainable": is_sustainable,
        "benefits_posture": benefits_posture,
    }


def audit_team_charter_and_tuckman_governance(
    team_charter: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Audita el Acta de Constitución del Equipo (Team Charter) y madurez de Tuckman según PMI PMBOK §9.1.3.2 y §9.4."""
    canonical_pillars = [
        ("core_values", ("core_values", "valores")),
        ("communication_guidelines", ("communication_guidelines", "pautas_comunicacion")),
        ("decision_making_criteria", ("decision_making_criteria", "criterios_decision")),
        ("conflict_resolution_process", ("conflict_resolution_process", "resolucion_conflictos")),
    ]

    if not isinstance(team_charter, dict) or len(team_charter) == 0:
        return {
            "charter_completeness_pct": 0.0,
            "missing_charter_pillars": [p[0] for p in canonical_pillars],
            "tuckman_stage": "UNSPECIFIED",
            "unresolved_conflicts_count": 0,
            "is_healthy": False,
            "team_posture": "MISSING_TEAM_CHARTER",
        }

    def _has_pillar_content(val: Any) -> bool:
        if val is None or isinstance(val, bool):
            return False
        if isinstance(val, str):
            return len(val.strip()) > 0
        if isinstance(val, (list, tuple, set, dict)):
            return len(val) > 0
        return len(str(val).strip()) > 0

    missing_charter_pillars: list[str] = []
    for pillar_name, keys in canonical_pillars:
        if not any(_has_pillar_content(team_charter.get(k)) for k in keys):
            missing_charter_pillars.append(pillar_name)

    present_count = 4 - len(missing_charter_pillars)
    charter_completeness_pct = round((present_count / 4.0) * 100.0, 2)

    raw_stage = str(
        team_charter.get("tuckman_stage") or team_charter.get("maturity_stage") or ""
    ).strip().lower()
    valid_stages = {"forming", "storming", "norming", "performing", "adjourning"}
    tuckman_stage = raw_stage.upper() if raw_stage in valid_stages else "UNSPECIFIED"

    raw_conflicts = (
        team_charter.get("unresolved_conflicts_count")
        if team_charter.get("unresolved_conflicts_count") is not None
        else (team_charter.get("open_conflicts") or 0)
    )
    try:
        unresolved_conflicts_count = max(0, int(raw_conflicts))
    except (TypeError, ValueError):
        unresolved_conflicts_count = 0

    is_healthy = bool(
        len(missing_charter_pillars) == 0
        and tuckman_stage in {"NORMING", "PERFORMING", "ADJOURNING"}
        and unresolved_conflicts_count == 0
    )

    if present_count == 0:
        team_posture = "MISSING_TEAM_CHARTER"
    elif len(missing_charter_pillars) > 0:
        team_posture = "INCOMPLETE_TEAM_CHARTER_AGREEMENTS"
    elif tuckman_stage == "STORMING" or unresolved_conflicts_count > 0:
        team_posture = "STORMING_OR_CONFLICT_FRICTION"
    elif tuckman_stage in {"FORMING", "UNSPECIFIED"}:
        team_posture = "EARLY_FORMING_ALIGNMENT"
    else:
        team_posture = "HIGH_PERFORMING_TEAM_GOVERNANCE"

    return {
        "charter_completeness_pct": charter_completeness_pct,
        "missing_charter_pillars": missing_charter_pillars,
        "tuckman_stage": tuckman_stage,
        "unresolved_conflicts_count": unresolved_conflicts_count,
        "is_healthy": is_healthy,
        "team_posture": team_posture,
    }


def audit_phase_gate_transition_readiness(
    phase_gates: Optional[list[dict[str, Any]]] = None,
    min_exit_criteria_pass_pct: float = 100.0,
) -> dict[str, Any]:
    """Audita las revisiones de transición de fase (Stage-Gates) y criterios de salida según PMI PMBOK §2.4.2 y §4.7."""
    items = [item for item in (phase_gates or []) if isinstance(item, dict)]
    total_gates = len(items)
    if total_gates == 0:
        return {
            "total_gates": 0,
            "approved_gates_count": 0,
            "bypassed_exit_criteria_gate_ids": [],
            "unapproved_governance_gate_ids": [],
            "blocked_transition_gate_ids": [],
            "is_gate_compliant": True,
            "gate_posture": "NO_PHASE_GATES_EVALUATED",
        }

    try:
        min_pass_pct = float(min_exit_criteria_pass_pct)
    except (TypeError, ValueError):
        min_pass_pct = 100.0

    approved_gates_count = 0
    bypassed_exit_criteria_gate_ids: list[str] = []
    unapproved_governance_gate_ids: list[str] = []
    blocked_transition_gate_ids: list[str] = []
    approved_decisions = {
        "approved",
        "go",
        "passed",
        "completed",
        "aprobado",
        "cerrado",
    }

    for idx, item in enumerate(items, start=1):
        gate_id = (
            str(
                item.get("id")
                or item.get("gate_id")
                or item.get("phase_name")
                or ""
            ).strip()
            or f"GATE-{idx}"
        )
        decision = (
            str(item.get("gate_decision") or item.get("status") or "")
            .strip()
            .lower()
        )
        if decision not in approved_decisions:
            continue

        approved_gates_count += 1
        approver = str(item.get("approver") or item.get("decided_by") or "").strip()

        raw_total = (
            item.get("criteria_total")
            if item.get("criteria_total") is not None
            else (item.get("total_criteria") or 0)
        )
        try:
            c_total = max(0, int(raw_total))
        except (TypeError, ValueError):
            c_total = 0

        raw_met = (
            item.get("criteria_met")
            if item.get("criteria_met") is not None
            else (item.get("passed_criteria") or 0)
        )
        try:
            c_met = max(0, int(raw_met))
        except (TypeError, ValueError):
            c_met = 0

        raw_blockers = (
            item.get("open_blockers_count")
            if item.get("open_blockers_count") is not None
            else (item.get("blockers") or 0)
        )
        try:
            blockers = max(0, int(raw_blockers))
        except (TypeError, ValueError):
            blockers = 0

        if not approver:
            unapproved_governance_gate_ids.append(gate_id)

        pass_pct = (c_met / c_total) * 100.0 if c_total > 0 else 0.0
        if c_total <= 0 or pass_pct + 1e-9 < min_pass_pct:
            bypassed_exit_criteria_gate_ids.append(gate_id)

        if blockers > 0:
            blocked_transition_gate_ids.append(gate_id)

    is_gate_compliant = bool(
        len(bypassed_exit_criteria_gate_ids) == 0
        and len(unapproved_governance_gate_ids) == 0
        and len(blocked_transition_gate_ids) == 0
    )

    if len(blocked_transition_gate_ids) > 0:
        gate_posture = "BLOCKED_GATE_TRANSITION_FORCE_PASSED"
    elif len(bypassed_exit_criteria_gate_ids) > 0:
        gate_posture = "EXIT_CRITERIA_BYPASS_DETECTED"
    elif len(unapproved_governance_gate_ids) > 0:
        gate_posture = "MISSING_GATE_GOVERNANCE_SIGNOFF"
    else:
        gate_posture = "RIGOROUS_STAGE_GATE_GOVERNANCE"

    return {
        "total_gates": total_gates,
        "approved_gates_count": approved_gates_count,
        "bypassed_exit_criteria_gate_ids": bypassed_exit_criteria_gate_ids,
        "unapproved_governance_gate_ids": unapproved_governance_gate_ids,
        "blocked_transition_gate_ids": blocked_transition_gate_ids,
        "is_gate_compliant": is_gate_compliant,
        "gate_posture": gate_posture,
    }


_VALID_MAKE_OR_BUY_CHOICES = frozenset({"make", "buy", "hacer", "comprar"})
_BUY_CHOICES = frozenset({"buy", "comprar"})


def audit_make_or_buy_and_vendor_bids(
    decisions: Optional[list[dict[str, Any]]] = None,
    min_competitive_bids: int = 2,
) -> dict[str, Any]:
    """Audita el Análisis Hacer-o-Comprar (Make-or-Buy) y la evaluación competitiva de ofertas según PMI PMBOK §12.1.3 y §12.2."""
    valid_decisions = [item for item in (decisions or []) if isinstance(item, dict)]
    total_decisions = len(valid_decisions)
    if total_decisions == 0:
        return {
            "total_decisions": 0,
            "buy_decisions_count": 0,
            "unjustified_decision_ids": [],
            "non_competitive_buy_ids": [],
            "low_scoring_vendor_award_ids": [],
            "is_compliant": True,
            "procurement_decision_posture": "NO_MAKE_OR_BUY_DECISIONS",
        }

    try:
        min_bids_req = max(1, int(min_competitive_bids))
    except (TypeError, ValueError):
        min_bids_req = 2

    buy_decisions_count = 0
    unjustified_decision_ids: list[str] = []
    non_competitive_buy_ids: list[str] = []
    low_scoring_vendor_award_ids: list[str] = []

    for idx, item in enumerate(valid_decisions, start=1):
        dec_id = (
            str(
                item.get("id")
                or item.get("decision_id")
                or item.get("item_id")
                or ""
            ).strip()
            or f"MOB-{idx}"
        )
        choice = str(item.get("decision") or item.get("strategy") or "").strip().lower()
        if choice not in _VALID_MAKE_OR_BUY_CHOICES:
            unjustified_decision_ids.append(dec_id)

        if choice in _BUY_CHOICES:
            buy_decisions_count += 1
            raw_bids = (
                item.get("bids_received")
                if item.get("bids_received") is not None
                else (item.get("bids_count") or 0)
            )
            try:
                bids = max(0, int(raw_bids))
            except (TypeError, ValueError):
                bids = 0

            sole_just = str(item.get("sole_source_justification") or "").strip()

            raw_score = (
                item.get("selected_vendor_score")
                if item.get("selected_vendor_score") is not None
                else (item.get("evaluation_score") or 0.0)
            )
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = 0.0

            if bids < min_bids_req and not sole_just:
                non_competitive_buy_ids.append(dec_id)
            if score < 70.0:
                low_scoring_vendor_award_ids.append(dec_id)

    is_compliant = bool(
        len(unjustified_decision_ids) == 0
        and len(non_competitive_buy_ids) == 0
        and len(low_scoring_vendor_award_ids) == 0
    )

    if len(unjustified_decision_ids) > 0:
        procurement_decision_posture = "UNJUSTIFIED_MAKE_OR_BUY_CHOICE"
    elif len(non_competitive_buy_ids) > 0:
        procurement_decision_posture = "NON_COMPETITIVE_SINGLE_BID_RISK"
    elif len(low_scoring_vendor_award_ids) > 0:
        procurement_decision_posture = "SUBTHRESHOLD_VENDOR_TECHNICAL_SCORE"
    else:
        procurement_decision_posture = "SOUND_PROCUREMENT_SOURCE_SELECTION"

    return {
        "total_decisions": total_decisions,
        "buy_decisions_count": buy_decisions_count,
        "unjustified_decision_ids": unjustified_decision_ids,
        "non_competitive_buy_ids": non_competitive_buy_ids,
        "low_scoring_vendor_award_ids": low_scoring_vendor_award_ids,
        "is_compliant": is_compliant,
        "procurement_decision_posture": procurement_decision_posture,
    }


ProjectLifecyclePMIService.audit_phase_gate_transition_readiness = staticmethod(
    audit_phase_gate_transition_readiness
)
ProjectLifecyclePMIService.audit_make_or_buy_and_vendor_bids = staticmethod(
    audit_make_or_buy_and_vendor_bids
)


_CLOSED_RISK_THRESHOLD_STATUSES = frozenset(
    {"closed", "cerrado", "retired", "mitigated_closed"}
)


def audit_risk_appetite_and_threshold_governance(
    risks: list[dict[str, Any]] | None = None,
    max_cost_threshold_pct: float = 5.0,
    max_schedule_threshold_days: float = 10.0,
) -> dict[str, Any]:
    """Audita el apetito de riesgo, umbrales de tolerancia y escalamiento según PMI PMBOK §11.1.3 y §11.7."""
    items = [item for item in (risks or []) if isinstance(item, dict)]
    total_risks = len(items)
    if total_risks == 0:
        return {
            "total_risks": 0,
            "threshold_breach_count": 0,
            "unescalated_breach_risk_ids": [],
            "unbuffered_breach_risk_ids": [],
            "is_threshold_governed": True,
            "threshold_posture": "NO_RISKS_EVALUATED",
        }

    try:
        cost_limit = float(max_cost_threshold_pct)
    except (TypeError, ValueError):
        cost_limit = 5.0
    try:
        sched_limit = float(max_schedule_threshold_days)
    except (TypeError, ValueError):
        sched_limit = 10.0

    threshold_breach_count = 0
    unescalated_breach_risk_ids: list[str] = []
    unbuffered_breach_risk_ids: list[str] = []

    for idx, item in enumerate(items, start=1):
        risk_id = (
            str(
                item.get("id")
                or item.get("risk_id")
                or item.get("code")
                or f"RSK-{idx}"
            ).strip()
            or f"RSK-{idx}"
        )
        status = (
            str(item.get("status") or item.get("state") or "open").strip().lower()
        )
        if status in _CLOSED_RISK_THRESHOLD_STATUSES:
            continue

        raw_cost = (
            item.get("cost_impact_pct")
            if item.get("cost_impact_pct") is not None
            else (
                item.get("cost_exposure_pct")
                if item.get("cost_exposure_pct") is not None
                else (item.get("budget_impact_pct") or 0.0)
            )
        )
        try:
            cost_impact_pct = max(0.0, float(raw_cost))
        except (TypeError, ValueError):
            cost_impact_pct = 0.0

        raw_sched = (
            item.get("schedule_impact_days")
            if item.get("schedule_impact_days") is not None
            else (
                item.get("delay_days")
                if item.get("delay_days") is not None
                else (item.get("schedule_exposure_days") or 0.0)
            )
        )
        try:
            schedule_impact_days = max(0.0, float(raw_sched))
        except (TypeError, ValueError):
            schedule_impact_days = 0.0

        exceeds_threshold = (
            (cost_impact_pct > cost_limit + 1e-9)
            or (schedule_impact_days > sched_limit + 1e-9)
            or bool(item.get("exceeds_appetite"))
        )
        if not exceeds_threshold:
            continue

        threshold_breach_count += 1
        owner = str(
            item.get("escalation_owner")
            or item.get("risk_owner")
            or item.get("owner")
            or ""
        ).strip()
        if not owner:
            unescalated_breach_risk_ids.append(risk_id)

        plan = str(
            item.get("contingency_plan")
            or item.get("response_plan")
            or item.get("mitigation_plan")
            or ""
        ).strip()
        raw_res = (
            item.get("contingency_reserve")
            if item.get("contingency_reserve") is not None
            else (item.get("allocated_reserve") or 0.0)
        )
        try:
            reserve = float(raw_res)
        except (TypeError, ValueError):
            reserve = 0.0

        if len(plan) < 5 or reserve <= 0.0:
            unbuffered_breach_risk_ids.append(risk_id)

    is_threshold_governed = bool(
        len(unescalated_breach_risk_ids) == 0
        and len(unbuffered_breach_risk_ids) == 0
    )

    if len(unescalated_breach_risk_ids) > 0:
        threshold_posture = "UNESCALATED_THRESHOLD_BREACH"
    elif len(unbuffered_breach_risk_ids) > 0:
        threshold_posture = "UNBUFFERED_CONTINGENCY_BREACH"
    elif threshold_breach_count > 0:
        threshold_posture = "GOVERNED_THRESHOLD_ESCALATION"
    else:
        threshold_posture = "WITHIN_RISK_APPETITE_THRESHOLDS"

    return {
        "total_risks": total_risks,
        "threshold_breach_count": threshold_breach_count,
        "unescalated_breach_risk_ids": unescalated_breach_risk_ids,
        "unbuffered_breach_risk_ids": unbuffered_breach_risk_ids,
        "is_threshold_governed": is_threshold_governed,
        "threshold_posture": threshold_posture,
    }


_SEAM_LEVEL_RANK = {
    "unaware": 1,
    "desconocedor": 1,
    "resistant": 2,
    "resistente": 2,
    "neutral": 3,
    "supportive": 4,
    "partidario": 4,
    "apoyo": 4,
    "leading": 5,
    "lider": 5,
    "líder": 5,
}
_SEAM_HIGH_POWER_VALUES = {"high", "alta", "alto", "critical", "critico", "crítico"}


def audit_stakeholder_engagement_assessment_matrix(
    stakeholders: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita la Matriz de Evaluación de Involucramiento de Interesados (SEAM) según PMI PMBOK §13.2.2.4."""
    items = [item for item in (stakeholders or []) if isinstance(item, dict)]
    total_stakeholders = len(items)
    if total_stakeholders == 0:
        return {
            "total_stakeholders": 0,
            "engagement_gap_count": 0,
            "critical_resistant_stakeholder_ids": [],
            "unaddressed_gap_stakeholder_ids": [],
            "misaligned_desired_state_ids": [],
            "is_seam_governed": True,
            "seam_posture": "NO_STAKEHOLDERS_EVALUATED",
        }

    engagement_gap_count = 0
    critical_resistant_stakeholder_ids: list[str] = []
    unaddressed_gap_stakeholder_ids: list[str] = []
    misaligned_desired_state_ids: list[str] = []

    for idx, item in enumerate(items, start=1):
        sh_id = (
            str(
                item.get("id")
                or item.get("stakeholder_id")
                or item.get("name")
                or f"SH-{idx}"
            ).strip()
            or f"SH-{idx}"
        )
        curr_raw = (
            str(
                item.get("current_engagement")
                or item.get("current_level")
                or "neutral"
            )
            .strip()
            .lower()
        )
        des_raw = (
            str(
                item.get("desired_engagement")
                or item.get("desired_level")
                or "supportive"
            )
            .strip()
            .lower()
        )
        curr_rank = _SEAM_LEVEL_RANK.get(curr_raw, 3)
        des_rank = _SEAM_LEVEL_RANK.get(des_raw, 4)

        power = (
            str(
                item.get("power")
                or item.get("influence")
                or item.get("power_level")
                or "medium"
            )
            .strip()
            .lower()
        )
        is_high_power = power in _SEAM_HIGH_POWER_VALUES
        strategy = str(
            item.get("engagement_strategy")
            or item.get("action_plan")
            or item.get("communication_plan")
            or ""
        ).strip()

        if is_high_power and curr_rank <= 2:
            critical_resistant_stakeholder_ids.append(sh_id)

        if curr_rank < des_rank:
            engagement_gap_count += 1
            if len(strategy) < 5:
                unaddressed_gap_stakeholder_ids.append(sh_id)

        if is_high_power and des_rank < 4:
            misaligned_desired_state_ids.append(sh_id)

    is_seam_governed = bool(
        len(unaddressed_gap_stakeholder_ids) == 0
        and len(misaligned_desired_state_ids) == 0
        and len(critical_resistant_stakeholder_ids) == 0
    )

    if len(critical_resistant_stakeholder_ids) > 0:
        seam_posture = "CRITICAL_HIGH_POWER_RESISTANCE"
    elif len(unaddressed_gap_stakeholder_ids) > 0:
        seam_posture = "UNADDRESSED_ENGAGEMENT_GAP"
    elif len(misaligned_desired_state_ids) > 0:
        seam_posture = "MISALIGNED_DESIRED_ENGAGEMENT"
    else:
        seam_posture = "ALIGNED_STAKEHOLDER_ENGAGEMENT"

    return {
        "total_stakeholders": total_stakeholders,
        "engagement_gap_count": engagement_gap_count,
        "critical_resistant_stakeholder_ids": critical_resistant_stakeholder_ids,
        "unaddressed_gap_stakeholder_ids": unaddressed_gap_stakeholder_ids,
        "misaligned_desired_state_ids": misaligned_desired_state_ids,
        "is_seam_governed": is_seam_governed,
        "seam_posture": seam_posture,
    }


_ACTIVE_RESIDUAL_RISK_STATUSES = {"OPEN", "ACTIVE", "MITIGATING"}
_RESPONSE_STRATEGIES_REQUIRING_TRIGGER = {"MITIGATE", "CONTINGENCY", "FALLBACK"}


def audit_risk_residual_exposure_and_triggers(
    risks: list[dict[str, Any]] | None = None,
    max_residual_emv: float = 5000.0,
) -> dict[str, Any]:
    """Audita exposición residual de riesgos frente a la inherente y presencia de disparadores de alerta temprana según PMI PMBOK §11.7 y §4.5."""
    items = [item for item in (risks or []) if isinstance(item, dict)]
    try:
        max_res_limit = max(0.0, float(max_residual_emv))
    except (TypeError, ValueError):
        max_res_limit = 5000.0

    def _nonneg_float(val: Any) -> float:
        if val is None or isinstance(val, bool):
            return 0.0
        try:
            return max(0.0, float(val))
        except (TypeError, ValueError):
            return 0.0

    total_active_risks = 0
    sum_inherent = 0.0
    sum_residual = 0.0
    inverted_residual_risk_ids: list[str] = []
    excessive_residual_risk_ids: list[str] = []
    missing_trigger_or_owner_ids: list[str] = []

    for item in items:
        risk_id = str(item.get("id") or item.get("risk_id") or "").strip()
        if not risk_id:
            continue
        status = str(item.get("status") or "OPEN").strip().upper()
        if status not in _ACTIVE_RESIDUAL_RISK_STATUSES:
            continue

        total_active_risks += 1
        inherent_emv = _nonneg_float(item.get("inherent_probability")) * _nonneg_float(
            item.get("inherent_impact")
        )
        residual_emv = _nonneg_float(item.get("residual_probability")) * _nonneg_float(
            item.get("residual_impact")
        )
        sum_inherent += inherent_emv
        sum_residual += residual_emv

        response_strategy = (
            str(item.get("response_strategy") or "MITIGATE").strip().upper()
        )
        trigger_condition = str(item.get("trigger_condition") or "").strip()
        risk_owner_id = str(item.get("risk_owner_id") or "").strip()

        if residual_emv > inherent_emv + 1e-6:
            inverted_residual_risk_ids.append(risk_id)
        if residual_emv > max_res_limit:
            excessive_residual_risk_ids.append(risk_id)
        if response_strategy in _RESPONSE_STRATEGIES_REQUIRING_TRIGGER and (
            not trigger_condition or not risk_owner_id
        ):
            missing_trigger_or_owner_ids.append(risk_id)

    is_residual_governance_valid = bool(
        total_active_risks > 0
        and len(inverted_residual_risk_ids) == 0
        and len(excessive_residual_risk_ids) == 0
        and len(missing_trigger_or_owner_ids) == 0
    )

    if total_active_risks == 0:
        residual_posture = "NO_ACTIVE_RISKS"
    elif len(inverted_residual_risk_ids) > 0:
        residual_posture = "RESIDUAL_EXCEEDS_INHERENT_EXPOSURE"
    elif len(excessive_residual_risk_ids) > 0:
        residual_posture = "EXCESSIVE_RESIDUAL_EXPOSURE"
    elif len(missing_trigger_or_owner_ids) > 0:
        residual_posture = "MISSING_RISK_TRIGGER_OR_OWNER"
    else:
        residual_posture = "GOVERNED_RESIDUAL_RISK_POSTURE"

    return {
        "total_active_risks": total_active_risks,
        "total_inherent_emv": round(sum_inherent, 2),
        "total_residual_emv": round(sum_residual, 2),
        "inverted_residual_risk_ids": inverted_residual_risk_ids,
        "excessive_residual_risk_ids": excessive_residual_risk_ids,
        "missing_trigger_or_owner_ids": missing_trigger_or_owner_ids,
        "is_residual_governance_valid": is_residual_governance_valid,
        "residual_posture": residual_posture,
    }


def audit_charter_funding_limit_reconciliation(
    periods: list[dict[str, Any]] | None = None,
    charter_authorized_budget: float = 0.0,
) -> dict[str, Any]:
    """Audita la reconciliación de límites de financiamiento por periodo frente al presupuesto autorizado en el Acta (PMBOK §4.1 / §7.3.2.5)."""
    total_periods = 0
    cumulative_planned = 0.0
    period_cap_breach_ids: list[str] = []

    for item in periods or []:
        if not isinstance(item, dict):
            continue
        period_id = str(item.get("period_id") or item.get("id") or "").strip()
        if not period_id:
            continue
        try:
            planned_outlay = max(0.0, float(item.get("planned_outlay") or 0.0))
        except (TypeError, ValueError):
            planned_outlay = 0.0
        try:
            funding_limit = max(0.0, float(item.get("funding_limit") or 0.0))
        except (TypeError, ValueError):
            funding_limit = 0.0

        total_periods += 1
        cumulative_planned += planned_outlay
        if planned_outlay > funding_limit + 1e-6:
            period_cap_breach_ids.append(period_id)

    try:
        auth_budget = max(0.0, float(charter_authorized_budget or 0.0))
    except (TypeError, ValueError):
        auth_budget = 0.0

    exceeds_charter_budget = bool(
        auth_budget > 0.0 and (cumulative_planned > auth_budget + 1e-6)
    )
    unallocated_charter_margin = (
        round(auth_budget - cumulative_planned, 2) if auth_budget > 0.0 else 0.0
    )
    is_funding_reconciled = bool(
        total_periods > 0
        and auth_budget > 0.0
        and len(period_cap_breach_ids) == 0
        and not exceeds_charter_budget
    )

    if total_periods == 0 or auth_budget <= 0.0:
        funding_posture = "NO_FUNDING_SCHEDULE_DEFINED"
    elif exceeds_charter_budget:
        funding_posture = "CHARTER_BUDGET_CEILING_EXCEEDED"
    elif len(period_cap_breach_ids) > 0:
        funding_posture = "PERIOD_FUNDING_LIMIT_BREACH"
    else:
        funding_posture = "RECONCILED_FUNDING_SCHEDULE"

    return {
        "total_periods": total_periods,
        "total_planned_outlay": round(cumulative_planned, 2),
        "charter_authorized_budget": round(auth_budget, 2),
        "unallocated_charter_margin": unallocated_charter_margin,
        "period_cap_breach_ids": period_cap_breach_ids,
        "exceeds_charter_budget": exceeds_charter_budget,
        "is_funding_reconciled": is_funding_reconciled,
        "funding_posture": funding_posture,
    }


def audit_team_tuckman_and_skill_redundancy(
    critical_skills: list[dict[str, Any]] | None = None,
    tuckman_stage: str = "FORMING",
    unresolved_team_conflicts: int = 0,
    min_qualified_members: int = 2,
) -> dict[str, Any]:
    """Audita redundancia de habilidades críticas (Cross-Training) y etapa de madurez de Tuckman del equipo según PMI PMBOK §9.4 y §9.5."""
    stage = str(tuckman_stage or "").strip().upper()
    valid_stages = {"FORMING", "STORMING", "NORMING", "PERFORMING", "ADJOURNING"}
    is_valid_stage = stage in valid_stages
    try:
        conflicts = max(0, int(unresolved_team_conflicts or 0))
    except (TypeError, ValueError):
        conflicts = 0
    try:
        min_qual = max(1, int(min_qualified_members))
    except (TypeError, ValueError):
        min_qual = 2

    total_critical_skills = 0
    spof_skill_ids: list[str] = []

    for item in critical_skills or []:
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get("skill_id") or item.get("id") or "").strip()
        if not skill_id:
            continue

        raw_q = item.get("qualified_members_count")
        if raw_q is not None:
            try:
                qualified_count = max(0, int(raw_q))
            except (TypeError, ValueError):
                qualified_count = 0
        else:
            raw_ids = item.get("qualified_member_ids")
            qualified_count = len(raw_ids) if isinstance(raw_ids, list) else 0

        total_critical_skills += 1
        if qualified_count < min_qual:
            spof_skill_ids.append(skill_id)

    is_team_resilient = bool(
        total_critical_skills > 0
        and is_valid_stage
        and len(spof_skill_ids) == 0
        and conflicts == 0
    )

    if total_critical_skills == 0:
        team_posture = "NO_CRITICAL_SKILLS_MAPPED"
    elif not is_valid_stage:
        team_posture = "INVALID_TUCKMAN_STAGE"
    elif len(spof_skill_ids) > 0:
        team_posture = "SINGLE_POINT_OF_FAILURE_SKILL_GAP"
    elif conflicts > 0:
        team_posture = "UNRESOLVED_TEAM_CONFLICT_ESCALATION"
    else:
        team_posture = "RESILIENT_CROSS_TRAINED_TEAM"

    return {
        "total_critical_skills": total_critical_skills,
        "tuckman_stage": stage,
        "unresolved_team_conflicts": conflicts,
        "spof_skill_ids": spof_skill_ids,
        "is_team_resilient": is_team_resilient,
        "team_posture": team_posture,
    }


ProjectLifecyclePMIService.audit_risk_appetite_and_threshold_governance = staticmethod(
    audit_risk_appetite_and_threshold_governance
)
ProjectLifecyclePMIService.audit_stakeholder_engagement_assessment_matrix = staticmethod(
    audit_stakeholder_engagement_assessment_matrix
)
ProjectLifecyclePMIService.audit_risk_residual_exposure_and_triggers = staticmethod(
    audit_risk_residual_exposure_and_triggers
)
ProjectLifecyclePMIService.audit_charter_funding_limit_reconciliation = staticmethod(
    audit_charter_funding_limit_reconciliation
)
ProjectLifecyclePMIService.audit_team_tuckman_and_skill_redundancy = staticmethod(
    audit_team_tuckman_and_skill_redundancy
)


def audit_stakeholder_escalation_matrix_readiness(
    escalation_tiers: Sequence[Mapping[str, Any]] | None,
    *,
    max_tier1_response_hours: float = 4.0,
) -> dict[str, Any]:
    """PMI PMBOK 10.1.3.1 / 13.2.3.1 — preparación de la matriz de escalamiento de comunicaciones e interesados.

    Evalúa dueño primario, backup (no SPOF), SLA máximo de respuesta
    (con tope específico para Tier 1) y canales de notificación por tier.
    """
    missing_primary_owner_tiers: list[int] = []
    single_point_of_failure_tiers: list[int] = []
    invalid_sla_tiers: list[int] = []
    unconfigured_channel_tiers: list[int] = []
    evaluated_tier_levels: list[int] = []

    for item in escalation_tiers or []:
        if not isinstance(item, Mapping):
            continue
        try:
            tier_level = int(item.get("tier_level"))
        except (TypeError, ValueError):
            continue
        if tier_level < 1:
            continue
        evaluated_tier_levels.append(tier_level)

        primary_owner_id = str(item.get("primary_owner_id") or "").strip()
        backup_owner_id = str(item.get("backup_owner_id") or "").strip()
        try:
            max_response_hours = float(item.get("max_response_hours", 0.0))
        except (TypeError, ValueError):
            max_response_hours = 0.0
        notification_channels = item.get("notification_channels")
        clean_channels = [
            str(channel).strip()
            for channel in (notification_channels or [])
            if channel is not None and str(channel).strip()
        ]

        if not primary_owner_id:
            missing_primary_owner_tiers.append(tier_level)

        if not backup_owner_id or (primary_owner_id and backup_owner_id == primary_owner_id):
            single_point_of_failure_tiers.append(tier_level)

        if max_response_hours <= 0 or (
            tier_level == 1 and max_response_hours > max_tier1_response_hours
        ):
            invalid_sla_tiers.append(tier_level)

        if not clean_channels:
            unconfigured_channel_tiers.append(tier_level)

    evaluated_tier_count = len(evaluated_tier_levels)
    problem_lists = (
        missing_primary_owner_tiers,
        single_point_of_failure_tiers,
        invalid_sla_tiers,
        unconfigured_channel_tiers,
    )
    compliant_tier_count = sum(
        1
        for tier_level in evaluated_tier_levels
        if all(tier_level not in problems for problems in problem_lists)
    )
    readiness_score_pct = (
        round((compliant_tier_count / evaluated_tier_count) * 100.0, 2)
        if evaluated_tier_count > 0
        else 0.0
    )
    has_tier_1 = 1 in evaluated_tier_levels
    is_ready = bool(
        evaluated_tier_count > 0
        and has_tier_1
        and all(len(problems) == 0 for problems in problem_lists)
    )

    return {
        "evaluated_tier_count": evaluated_tier_count,
        "has_tier_1": has_tier_1,
        "missing_primary_owner_tiers": missing_primary_owner_tiers,
        "single_point_of_failure_tiers": single_point_of_failure_tiers,
        "invalid_sla_tiers": invalid_sla_tiers,
        "unconfigured_channel_tiers": unconfigured_channel_tiers,
        "readiness_score_pct": readiness_score_pct,
        "is_ready": is_ready,
    }


ProjectLifecyclePMIService.audit_stakeholder_escalation_matrix_readiness = staticmethod(
    audit_stakeholder_escalation_matrix_readiness
)


def audit_team_calendar_burnout_contention(
    member_allocations: Sequence[Mapping[str, Any]] | None = None,
    *,
    max_sustainable_utilization_pct: float = 85.0,
    max_concurrent_projects: int = 3,
) -> dict[str, Any]:
    """Audita calendarios de recursos, sobreasignación sostenible y cambio de contexto según PMI PMBOK §9.2.3.2 & §9.5."""
    evaluated_member_count = 0
    burnout_risk_member_ids: list[str] = []
    context_switching_member_ids: list[str] = []
    pto_conflict_member_ids: list[str] = []
    invalid_calendar_member_ids: list[str] = []
    utilizations: list[float] = []

    for item in member_allocations or []:
        if not isinstance(item, Mapping):
            continue
        member_id = str(item.get("member_id") or "").strip()
        if not member_id:
            continue

        evaluated_member_count += 1
        try:
            available_hours = float(item.get("available_hours", 0.0) or 0.0)
        except (TypeError, ValueError):
            available_hours = 0.0
        try:
            allocated_hours = float(item.get("allocated_hours", 0.0) or 0.0)
        except (TypeError, ValueError):
            allocated_hours = -1.0

        if available_hours <= 0.0 or allocated_hours < 0.0:
            invalid_calendar_member_ids.append(member_id)
            continue

        utilization_pct = round((allocated_hours / available_hours) * 100.0, 2)
        utilizations.append(utilization_pct)

        if utilization_pct > float(max_sustainable_utilization_pct):
            burnout_risk_member_ids.append(member_id)

        raw_conc = item.get("concurrent_project_count", 1)
        try:
            concurrent_project_count = int(1 if raw_conc is None else raw_conc)
        except (TypeError, ValueError):
            concurrent_project_count = 1
        if concurrent_project_count > int(max_concurrent_projects):
            context_switching_member_ids.append(member_id)

        try:
            pto_conflict_hours = float(item.get("pto_conflict_hours", 0.0) or 0.0)
        except (TypeError, ValueError):
            pto_conflict_hours = 0.0
        if pto_conflict_hours > 0.0:
            pto_conflict_member_ids.append(member_id)

    average_utilization_pct = (
        round(sum(utilizations) / len(utilizations), 2)
        if utilizations
        else 0.0
    )
    is_sustainable = bool(
        evaluated_member_count > 0
        and len(burnout_risk_member_ids) == 0
        and len(context_switching_member_ids) == 0
        and len(pto_conflict_member_ids) == 0
        and len(invalid_calendar_member_ids) == 0
    )

    return {
        "evaluated_member_count": evaluated_member_count,
        "burnout_risk_member_ids": burnout_risk_member_ids,
        "context_switching_member_ids": context_switching_member_ids,
        "pto_conflict_member_ids": pto_conflict_member_ids,
        "invalid_calendar_member_ids": invalid_calendar_member_ids,
        "average_utilization_pct": average_utilization_pct,
        "is_sustainable": is_sustainable,
    }


ProjectLifecyclePMIService.audit_team_calendar_burnout_contention = staticmethod(
    audit_team_calendar_burnout_contention
)


def audit_charter_assumption_log_validity(
    assumption_entries: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Audita el Registro de Supuestos y Restricciones (Assumption Log PMI PMBOK §4.1.3.2 y §11.2)."""
    if not isinstance(assumption_entries, (list, tuple)):
        assumption_entries = []

    evaluated_entry_count = 0
    unowned_entry_ids: list[str] = []
    overdue_unvalidated_assumption_ids: list[str] = []
    unconverted_invalidated_assumption_ids: list[str] = []
    invalid_entry_ids: list[str] = []

    for item in assumption_entries:
        if not isinstance(item, Mapping):
            continue
        entry_id = str(item.get("entry_id") or "").strip()
        if not entry_id:
            continue
        evaluated_entry_count += 1

        entry_type = str(item.get("entry_type") or "").strip().lower()
        validation_status = str(item.get("validation_status") or "").strip().lower()
        if (
            entry_type not in {"assumption", "constraint"}
            or validation_status not in {"unvalidated", "validated", "invalidated"}
        ):
            invalid_entry_ids.append(entry_id)
            continue

        owner_id = str(item.get("owner_id") or "").strip()
        if not owner_id:
            unowned_entry_ids.append(entry_id)

        try:
            days_until_validation_due = float(
                item.get("days_until_validation_due", 0) or 0.0
            )
        except (TypeError, ValueError):
            days_until_validation_due = 0.0

        if (
            entry_type == "assumption"
            and validation_status == "unvalidated"
            and days_until_validation_due < 0.0
        ):
            overdue_unvalidated_assumption_ids.append(entry_id)

        converted_risk_id = str(item.get("converted_risk_id") or "").strip()
        if validation_status == "invalidated" and not converted_risk_id:
            unconverted_invalidated_assumption_ids.append(entry_id)

    is_valid = bool(
        evaluated_entry_count > 0
        and len(unowned_entry_ids) == 0
        and len(overdue_unvalidated_assumption_ids) == 0
        and len(unconverted_invalidated_assumption_ids) == 0
        and len(invalid_entry_ids) == 0
    )

    return {
        "evaluated_entry_count": evaluated_entry_count,
        "unowned_entry_ids": unowned_entry_ids,
        "overdue_unvalidated_assumption_ids": overdue_unvalidated_assumption_ids,
        "unconverted_invalidated_assumption_ids": unconverted_invalidated_assumption_ids,
        "invalid_entry_ids": invalid_entry_ids,
        "is_valid": is_valid,
    }


ProjectLifecyclePMIService.audit_charter_assumption_log_validity = staticmethod(
    audit_charter_assumption_log_validity
)


def audit_project_closure_handover_and_release_readiness(
    closure_package: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Audita la preparación de cierre administrativo, cierre de adquisiciones, transferencia operativa y liberación de recursos según PMI PMBOK §4.7 y §12.3."""
    pkg: Mapping[str, Any] = (
        closure_package if isinstance(closure_package, Mapping) else {}
    )

    try:
        open_claims_count = max(0, int(pkg.get("open_claims_count", 0) or 0))
    except (TypeError, ValueError):
        open_claims_count = 0

    try:
        unreleased_retention_amount = round(
            max(0.0, float(pkg.get("unreleased_retention_amount", 0.0) or 0.0)),
            2,
        )
    except (TypeError, ValueError):
        unreleased_retention_amount = 0.0

    final_acceptance_signed = bool(pkg.get("final_acceptance_signed", False))
    operations_handover_accepted = bool(
        pkg.get("operations_handover_accepted", False)
    )

    try:
        resources_released_pct = round(
            max(
                0.0,
                min(
                    100.0,
                    float(pkg.get("resources_released_pct", 0.0) or 0.0),
                ),
            ),
            2,
        )
    except (TypeError, ValueError):
        resources_released_pct = 0.0

    final_report_archived = bool(pkg.get("final_report_archived", False))

    blocking_gates: list[str] = []
    if not final_acceptance_signed:
        blocking_gates.append("missing_final_acceptance_signoff")
    if open_claims_count > 0:
        blocking_gates.append("unresolved_procurement_claims")
    if unreleased_retention_amount > 0.0:
        blocking_gates.append("unreleased_financial_retention")
    if not operations_handover_accepted:
        blocking_gates.append("pending_operations_handover")
    if resources_released_pct < 100.0:
        blocking_gates.append("incomplete_team_resource_release")
    if not final_report_archived:
        blocking_gates.append("unarchived_final_project_report")

    completed_criteria = 6 - len(blocking_gates)
    closure_readiness_pct = round((completed_criteria / 6.0) * 100.0, 2)
    is_ready_for_administrative_closure = bool(len(blocking_gates) == 0)

    return {
        "open_claims_count": open_claims_count,
        "unreleased_retention_amount": unreleased_retention_amount,
        "resources_released_pct": resources_released_pct,
        "blocking_gates": blocking_gates,
        "closure_readiness_pct": closure_readiness_pct,
        "is_ready_for_administrative_closure": is_ready_for_administrative_closure,
    }


ProjectLifecyclePMIService.audit_project_closure_handover_and_release_readiness = staticmethod(
    audit_project_closure_handover_and_release_readiness
)


__all__ = [
    "build_pmo_portfolio_matrix",
    "build_governance_summary",
    "compute_closure_readiness_pct",
    "compute_governance_maturity_pct",
    "evaluate_governance_health",
    "get_lifecycle",
    "save_charter",
    "list_stakeholders",
    "create_stakeholder",
    "update_stakeholder",
    "soft_delete_stakeholder",
    "finalize_closure",
    "evaluate_automation_governance_readiness",
    "evaluate_stakeholder_engagement_gaps",
    "evaluate_charter_authorization_readiness",
    "evaluate_administrative_closure_audit",
    "evaluate_pmo_portfolio_health_balance",
    "evaluate_phase_gate_transition_readiness",
    "evaluate_lessons_learned_institutional_reuse",
    "audit_charter_measurable_objectives",
    "audit_lessons_learned_actionable_followup",
    "audit_stakeholder_communication_cadence",
    "evaluate_benefits_realization_posture",
    "audit_assumption_and_constraint_log",
    "audit_assumption_and_constraint_log_governance",
    "audit_project_procurement_and_handover_closeout",
    "audit_stakeholder_engagement_transition_gaps",
    "audit_project_tailoring_and_opa_compliance",
    "audit_benefits_realization_sustainability",
    "audit_team_charter_and_tuckman_governance",
    "audit_phase_gate_transition_readiness",
    "audit_make_or_buy_and_vendor_bids",
    "audit_risk_appetite_and_threshold_governance",
    "audit_stakeholder_engagement_assessment_matrix",
    "audit_risk_residual_exposure_and_triggers",
    "audit_charter_funding_limit_reconciliation",
    "audit_team_tuckman_and_skill_redundancy",
    "audit_stakeholder_escalation_matrix_readiness",
    "audit_team_calendar_burnout_contention",
    "audit_charter_assumption_log_validity",
    "audit_project_closure_handover_and_release_readiness",
    "audit_stakeholder_salience_mitchell_classification",
    "audit_business_case_financial_viability_governance",
    "audit_team_conflict_resolution_governance",
    "audit_stage_gate_phase_transition_governance",
    "audit_stakeholder_engagement_seam_drift",
    "ProjectLifecyclePMIService",
]


def audit_stakeholder_salience_mitchell_classification(
    stakeholders: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """PMBOK §13.1.2.4 — clasificación de prominencia de interesados (modelo Mitchell).

    Atributos binarios: poder, urgencia, legitimidad.
    - 3/3 -> ``definitive_stakeholder_ids``; poder+urgencia sin legitimidad ->
      ``dangerous_stakeholder_ids``; 0 atributos -> ``non_stakeholder_ids``;
    - >= 2 atributos sin ``engagement_plan`` -> ``unmanaged_high_salience_ids``.
    """
    if not isinstance(stakeholders, (list, tuple)):
        stakeholders = []

    total_stakeholders = 0
    definitive_stakeholder_ids: list[str] = []
    dangerous_stakeholder_ids: list[str] = []
    non_stakeholder_ids: list[str] = []
    unmanaged_high_salience_ids: list[str] = []

    for item in stakeholders:
        if not isinstance(item, Mapping):
            continue
        stakeholder_id = str(item.get("stakeholder_id") or "").strip()
        if not stakeholder_id:
            continue

        has_power = bool(item.get("has_power", False))
        has_urgency = bool(item.get("has_urgency", False))
        has_legitimacy = bool(item.get("has_legitimacy", False))
        engagement_plan = str(item.get("engagement_plan") or "").strip()
        attrs_count = int(has_power) + int(has_urgency) + int(has_legitimacy)

        total_stakeholders += 1

        if attrs_count == 3:
            definitive_stakeholder_ids.append(stakeholder_id)

        if has_power and has_urgency and not has_legitimacy:
            dangerous_stakeholder_ids.append(stakeholder_id)

        if attrs_count == 0:
            non_stakeholder_ids.append(stakeholder_id)

        if attrs_count >= 2 and not engagement_plan:
            unmanaged_high_salience_ids.append(stakeholder_id)

    is_salience_governance_ready = bool(
        total_stakeholders > 0
        and not unmanaged_high_salience_ids
        and not non_stakeholder_ids
    )

    return {
        "total_stakeholders": total_stakeholders,
        "definitive_stakeholder_ids": definitive_stakeholder_ids,
        "dangerous_stakeholder_ids": dangerous_stakeholder_ids,
        "non_stakeholder_ids": non_stakeholder_ids,
        "unmanaged_high_salience_ids": unmanaged_high_salience_ids,
        "is_salience_governance_ready": is_salience_governance_ready,
    }


ProjectLifecyclePMIService.audit_stakeholder_salience_mitchell_classification = staticmethod(
    audit_stakeholder_salience_mitchell_classification
)


def audit_business_case_financial_viability_governance(
    business_case: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Audita la viabilidad financiera del Caso de Negocio (NPV, IRR vs Hurdle Rate, BCR y Payback) según PMI PMBOK §1.2.6 y §4.1."""
    bc: Mapping[str, Any] = (
        business_case if isinstance(business_case, Mapping) else {}
    )

    try:
        npv = round(float(bc.get("npv", 0.0) or 0.0), 2)
    except (TypeError, ValueError):
        npv = 0.0

    try:
        irr_pct = round(float(bc.get("irr_pct", 0.0) or 0.0), 2)
    except (TypeError, ValueError):
        irr_pct = 0.0

    try:
        hurdle_rate_pct = round(
            max(0.0, float(bc.get("hurdle_rate_pct", 0.0) or 0.0)), 2
        )
    except (TypeError, ValueError):
        hurdle_rate_pct = 0.0

    try:
        bcr = round(max(0.0, float(bc.get("bcr", 0.0) or 0.0)), 2)
    except (TypeError, ValueError):
        bcr = 0.0

    try:
        payback_months = round(
            max(0.0, float(bc.get("payback_months", 0.0) or 0.0)), 2
        )
    except (TypeError, ValueError):
        payback_months = 0.0

    try:
        max_payback_months = round(
            max(0.0, float(bc.get("max_payback_months", 0.0) or 0.0)), 2
        )
    except (TypeError, ValueError):
        max_payback_months = 0.0

    viability_breaches: list[str] = []
    if npv <= 0.0:
        viability_breaches.append("non_positive_npv")
    if hurdle_rate_pct <= 0.0 or irr_pct < hurdle_rate_pct:
        viability_breaches.append("irr_below_hurdle_rate")
    if bcr < 1.0:
        viability_breaches.append("benefit_cost_ratio_below_unity")
    if (
        max_payback_months <= 0.0
        or payback_months <= 0.0
        or payback_months > max_payback_months
    ):
        viability_breaches.append("payback_exceeds_horizon")

    is_financially_viable = bool(len(viability_breaches) == 0)

    return {
        "npv": npv,
        "irr_pct": irr_pct,
        "hurdle_rate_pct": hurdle_rate_pct,
        "bcr": bcr,
        "payback_months": payback_months,
        "viability_breaches": viability_breaches,
        "is_financially_viable": is_financially_viable,
    }


ProjectLifecyclePMIService.audit_business_case_financial_viability_governance = staticmethod(
    audit_business_case_financial_viability_governance
)


def audit_team_conflict_resolution_governance(
    conflicts: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Audita los modos de resolución de conflictos del equipo (modelo Thomas-Kilmann PMI PMBOK §9.4/§9.5 y §13.3)."""
    if (
        not conflicts
        or not isinstance(conflicts, Sequence)
        or isinstance(conflicts, (str, bytes, Mapping))
    ):
        conflicts = []

    valid_modes = {
        "collaborate",
        "problem_solve",
        "compromise",
        "smooth",
        "force",
        "direct",
        "withdraw",
        "avoid",
    }
    destructive_modes = {"force", "direct", "withdraw", "avoid"}

    total_conflicts = 0
    collaborative_count = 0
    invalid_mode_conflict_ids: list[str] = []
    destructive_high_severity_conflict_ids: list[str] = []
    stalled_or_undocumented_conflict_ids: list[str] = []

    for item in conflicts:
        if not isinstance(item, Mapping):
            continue
        conflict_id = str(item.get("conflict_id") or "").strip()
        if not conflict_id:
            continue

        total_conflicts += 1
        resolution_mode = str(item.get("resolution_mode") or "").strip().lower()
        severity = str(item.get("severity") or "").strip().lower()
        agreement_documented = bool(item.get("agreement_documented", False))
        try:
            escalated_unresolved_days = max(
                0.0, float(item.get("escalated_unresolved_days", 0.0) or 0.0)
            )
        except (TypeError, ValueError):
            escalated_unresolved_days = 0.0

        if resolution_mode not in valid_modes:
            invalid_mode_conflict_ids.append(conflict_id)

        if resolution_mode in destructive_modes and severity in {"high", "critical"}:
            destructive_high_severity_conflict_ids.append(conflict_id)

        if escalated_unresolved_days > 5.0 or (
            severity in {"high", "critical"} and not agreement_documented
        ):
            stalled_or_undocumented_conflict_ids.append(conflict_id)

        if (
            resolution_mode in {"collaborate", "problem_solve"}
            and agreement_documented
        ):
            collaborative_count += 1

    collaborative_resolution_rate_pct = (
        round((collaborative_count / total_conflicts) * 100.0, 2)
        if total_conflicts > 0
        else 0.0
    )
    is_conflict_governance_healthy = bool(
        total_conflicts > 0
        and not invalid_mode_conflict_ids
        and not destructive_high_severity_conflict_ids
        and not stalled_or_undocumented_conflict_ids
    )

    return {
        "total_conflicts": total_conflicts,
        "invalid_mode_conflict_ids": invalid_mode_conflict_ids,
        "destructive_high_severity_conflict_ids": destructive_high_severity_conflict_ids,
        "stalled_or_undocumented_conflict_ids": stalled_or_undocumented_conflict_ids,
        "collaborative_resolution_rate_pct": collaborative_resolution_rate_pct,
        "is_conflict_governance_healthy": is_conflict_governance_healthy,
    }


ProjectLifecyclePMIService.audit_team_conflict_resolution_governance = staticmethod(
    audit_team_conflict_resolution_governance
)


def audit_stage_gate_phase_transition_governance(
    phase_gates: Sequence[Mapping[str, Any]] | None,
    require_sponsor_signoff: bool = True,
) -> dict[str, Any]:
    """Audita las revisiones de transición de fase (Stage-Gates) y revalidación del Caso de Negocio según PMI PMBOK §2.4 y §4.1."""
    if (
        not phase_gates
        or not isinstance(phase_gates, Sequence)
        or isinstance(phase_gates, (str, bytes, Mapping))
    ):
        items: Sequence[Any] = []
    else:
        items = phase_gates

    total_gates = 0
    approved_gates_count = 0
    premature_phase_transitions: list[str] = []
    unvalidated_business_case_gates: list[str] = []
    conditional_go_missing_action_plan_gates: list[str] = []

    approved_decisions = {"go", "conditional_go"}

    for item in items:
        if not isinstance(item, Mapping):
            continue
        gate_id = str(item.get("gate_id") or item.get("phase_id") or "").strip()
        if not gate_id:
            continue

        total_gates += 1
        decision = str(item.get("decision") or "pending").strip().lower()
        deliverables_verified = bool(item.get("deliverables_verified") is True)
        sponsor_signed_off = bool(item.get("sponsor_signed_off") is True)
        business_case_revalidated = bool(
            item.get("business_case_revalidated") is True
        )
        try:
            open_blocker_count = int(item.get("open_blocker_count") or 0)
        except (TypeError, ValueError):
            open_blocker_count = 0
        next_phase_started = bool(item.get("next_phase_started") is True)

        if decision in approved_decisions:
            approved_gates_count += 1

        if next_phase_started and (
            decision not in approved_decisions
            or not deliverables_verified
            or (require_sponsor_signoff and not sponsor_signed_off)
            or open_blocker_count > 0
        ):
            premature_phase_transitions.append(gate_id)

        if decision in approved_decisions and not business_case_revalidated:
            unvalidated_business_case_gates.append(gate_id)

        if decision == "conditional_go" and (
            not str(item.get("remediation_plan") or "").strip()
            or not str(item.get("remediation_due_date") or "").strip()
        ):
            conditional_go_missing_action_plan_gates.append(gate_id)

    is_stage_gate_compliant = bool(
        len(premature_phase_transitions) == 0
        and len(unvalidated_business_case_gates) == 0
        and len(conditional_go_missing_action_plan_gates) == 0
    )

    recommendations: list[str] = []
    if premature_phase_transitions:
        recommendations.append(
            "Detener el inicio de fases subsiguientes hasta obtener firma del patrocinador, verificación de entregables y cierre de bloqueadores en la compuerta."
        )
    if unvalidated_business_case_gates:
        recommendations.append(
            "Revalidar formalmente el Caso de Negocio y el Plan de Gestión de Beneficios en cada Stage-Gate aprobado."
        )
    if conditional_go_missing_action_plan_gates:
        recommendations.append(
            "Documentar plan de remediación y fecha compromiso para toda decisión Conditional Go."
        )

    if len(premature_phase_transitions) > 0:
        status = "critical"
    elif (
        len(unvalidated_business_case_gates) > 0
        or len(conditional_go_missing_action_plan_gates) > 0
    ):
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_gates": total_gates,
        "approved_gates_count": approved_gates_count,
        "premature_phase_transitions": premature_phase_transitions,
        "unvalidated_business_case_gates": unvalidated_business_case_gates,
        "conditional_go_missing_action_plan_gates": conditional_go_missing_action_plan_gates,
        "is_stage_gate_compliant": is_stage_gate_compliant,
        "status": status,
        "recommendations": recommendations,
    }


ProjectLifecyclePMIService.audit_stage_gate_phase_transition_governance = staticmethod(
    audit_stage_gate_phase_transition_governance
)


_SEAM_ORDINAL_SCALE: dict[str, int] = {
    "unaware": 1,
    "resistant": 2,
    "neutral": 3,
    "supportive": 4,
    "leading": 5,
}


def audit_stakeholder_engagement_seam_drift(
    stakeholders: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Audita la Matriz de Evaluación del Involucramiento de los Interesados (SEAM), brechas de actitud y deriva de resistencia según PMI PMBOK §13.2.2.5 y §13.4."""
    if (
        not stakeholders
        or not isinstance(stakeholders, Sequence)
        or isinstance(stakeholders, (str, bytes, Mapping))
    ):
        items: Sequence[Any] = []
    else:
        items = stakeholders

    total_evaluated = 0
    engagement_gap_stakeholder_ids: list[str] = []
    unmitigated_gap_stakeholder_ids: list[str] = []
    high_impact_resistant_stakeholder_ids: list[str] = []
    regressing_engagement_stakeholder_ids: list[str] = []
    invalid_level_stakeholder_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        stakeholder_id = str(
            item.get("stakeholder_id") or item.get("id") or ""
        ).strip()
        if not stakeholder_id:
            continue

        total_evaluated += 1
        current_engagement = (
            str(item.get("current_engagement") or "").strip().lower()
        )
        desired_engagement = (
            str(item.get("desired_engagement") or "").strip().lower()
        )

        if (
            current_engagement not in _SEAM_ORDINAL_SCALE
            or desired_engagement not in _SEAM_ORDINAL_SCALE
        ):
            invalid_level_stakeholder_ids.append(stakeholder_id)
            continue

        current_score = _SEAM_ORDINAL_SCALE[current_engagement]
        desired_score = _SEAM_ORDINAL_SCALE[desired_engagement]

        if current_score < desired_score:
            engagement_gap_stakeholder_ids.append(stakeholder_id)
            if not str(item.get("engagement_action_plan") or "").strip():
                unmitigated_gap_stakeholder_ids.append(stakeholder_id)

        if current_engagement == "resistant" and bool(
            item.get("is_high_power_or_impact") is True
        ):
            high_impact_resistant_stakeholder_ids.append(stakeholder_id)

        previous_engagement = (
            str(item.get("previous_engagement") or "").strip().lower()
        )
        if previous_engagement in _SEAM_ORDINAL_SCALE:
            previous_score = _SEAM_ORDINAL_SCALE[previous_engagement]
            if current_score < previous_score:
                regressing_engagement_stakeholder_ids.append(stakeholder_id)

    is_seam_governance_healthy = bool(
        len(unmitigated_gap_stakeholder_ids) == 0
        and len(high_impact_resistant_stakeholder_ids) == 0
        and len(regressing_engagement_stakeholder_ids) == 0
        and len(invalid_level_stakeholder_ids) == 0
    )

    recommendations: list[str] = []
    if invalid_level_stakeholder_ids:
        recommendations.append(
            "Clasificar a todos los interesados dentro de la escala canónica SEAM (unaware, resistant, neutral, supportive, leading)."
        )
    if high_impact_resistant_stakeholder_ids:
        recommendations.append(
            "Intervenir prioritariamente con patrocinio ejecutivo a los interesados resistentes de alto poder o impacto."
        )
    if unmitigated_gap_stakeholder_ids:
        recommendations.append(
            "Documentar un plan de acción de involucramiento (engagement_action_plan) para cada interesado con brecha entre nivel actual y deseado."
        )
    if regressing_engagement_stakeholder_ids:
        recommendations.append(
            "Analizar las causas de regresión de actitud en interesados cuyo involucramiento disminuyó respecto al ciclo previo."
        )
    if engagement_gap_stakeholder_ids and not unmitigated_gap_stakeholder_ids:
        recommendations.append(
            "Monitorear la ejecución de los planes de acción para cerrar las brechas SEAM activas."
        )

    if (
        len(high_impact_resistant_stakeholder_ids) > 0
        or len(unmitigated_gap_stakeholder_ids) > 0
        or len(invalid_level_stakeholder_ids) > 0
    ):
        status = "critical"
    elif (
        len(regressing_engagement_stakeholder_ids) > 0
        or len(engagement_gap_stakeholder_ids) > 0
    ):
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_evaluated": total_evaluated,
        "engagement_gap_stakeholder_ids": engagement_gap_stakeholder_ids,
        "unmitigated_gap_stakeholder_ids": unmitigated_gap_stakeholder_ids,
        "high_impact_resistant_stakeholder_ids": high_impact_resistant_stakeholder_ids,
        "regressing_engagement_stakeholder_ids": regressing_engagement_stakeholder_ids,
        "invalid_level_stakeholder_ids": invalid_level_stakeholder_ids,
        "is_seam_governance_healthy": is_seam_governance_healthy,
        "status": status,
        "recommendations": recommendations,
    }


ProjectLifecyclePMIService.audit_stakeholder_engagement_seam_drift = staticmethod(
    audit_stakeholder_engagement_seam_drift
)


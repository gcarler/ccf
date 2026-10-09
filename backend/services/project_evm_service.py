"""Servicio de Gestión del Valor Ganado (Earned Value Management — EVM).

Implementa las fórmulas canónicas del PMI / PMBOK y estándares internacionales
para control físico-financiero de proyectos:
- BAC (Budget at Completion / Presupuesto Total)
- PV  (Planned Value / Valor Planificado)
- EV  (Earned Value / Valor Ganado Físico Monetizado)
- AC  (Actual Cost / Costo Real Gastado)
- CPI (Cost Performance Index = EV / AC) -> Desempeño Físico vs Financiero
- SPI (Schedule Performance Index = EV / PV) -> Desempeño del Cronograma
- CV  (Cost Variance = EV - AC)
- SV  (Schedule Variance = EV - PV)
- CR  (Critical Ratio = CPI * SPI)
- EAC (Estimate at Completion = BAC / CPI)
- VAC (Variance at Completion = BAC - EAC)
- Curva S de series temporales acumuladas
"""

from __future__ import annotations

import datetime
from datetime import timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = Any  # type: ignore

class _DummyModelMeta(type):
    def __getattr__(cls, name: str) -> Any:
        return cls

    def __eq__(cls, other: Any) -> Any:
        return cls

    def is_(cls, other: Any) -> Any:
        return cls

    def in_(cls, other: Any) -> Any:
        return cls

    def asc(cls) -> Any:
        return cls

    def desc(cls) -> Any:
        return cls


class _DummyModel(metaclass=_DummyModelMeta):
    pass


try:
    from backend.models_projects import (
        Project,
        ProjectComponent,
        ProjectExpense,
        ProjectMilestone,
        ProjectTask,
        ProjectTimeLog,
    )
except ImportError:
    # Fallback for testing environments without C-extension dependencies
    Project = _DummyModel  # type: ignore
    ProjectComponent = _DummyModel  # type: ignore
    ProjectExpense = _DummyModel  # type: ignore
    ProjectMilestone = _DummyModel  # type: ignore
    ProjectTask = _DummyModel  # type: ignore
    ProjectTimeLog = _DummyModel  # type: ignore


def _as_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Extrae de manera segura un valor flotante manejando None, Decimals, cadenas y MagicMocks."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    from decimal import Decimal
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
    return default


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(timezone.utc)


def calculate_project_evm(db: Session, project: Project) -> Dict[str, Any]:
    """Calcula las métricas canónicas de EVM para un proyecto dado."""
    now = _utcnow()
    bac = float(project.budget_allocated or 0.0)

    # 1. Costo Real (AC): Gastos reales registrados o campo budget_spent
    expenses_query = (
        db.query(ProjectExpense)
        .filter(
            ProjectExpense.project_id == project.id,
            ProjectExpense.deleted_at.is_(None),
            ProjectExpense.status.in_(["approved", "paid"]),
        )
        .all()
    )
    expenses_total = sum(float(e.amount or 0.0) for e in expenses_query)
    direct_spent = float(project.budget_spent or 0.0)
    ac = round(max(direct_spent, expenses_total), 2)

    # 2. Avance Físico (%)
    tasks = (
        db.query(ProjectTask)
        .filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        )
        .all()
    )
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status in ("completed", "done"))

    if project.progress_mode == "manual":
        progress_pct = max(0.0, min(100.0, float(project.manual_progress or 0.0)))
    elif project.progress_mode == "milestones":
        milestones = (
            db.query(ProjectMilestone)
            .filter(
                ProjectMilestone.project_id == project.id,
                ProjectMilestone.deleted_at.is_(None),
            )
            .all()
        )
        if milestones:
            done_m = sum(1 for m in milestones if m.is_completed)
            progress_pct = round((done_m / len(milestones)) * 100.0, 1)
        else:
            progress_pct = round((completed_tasks / max(total_tasks, 1)) * 100.0, 1) if total_tasks else 0.0
    else:
        progress_pct = round((completed_tasks / max(total_tasks, 1)) * 100.0, 1) if total_tasks else 0.0

    # 3. Valor Ganado (EV) = BAC * (% Avance Físico)
    ev = round(bac * (progress_pct / 100.0), 2)

    # 4. Valor Planificado (PV) a la fecha actual
    start_dt = _as_utc(project.start_date) or _as_utc(project.created_at) or now
    target_dt = _as_utc(project.target_date)

    if total_tasks > 0:
        # Calcular PV a partir de tareas que debían haber finalizado a la fecha de hoy
        due_tasks = 0
        for t in tasks:
            t_due = _as_utc(t.due_date)
            if t_due and t_due <= now:
                due_tasks += 1
            elif not t_due and target_dt and now >= target_dt:
                due_tasks += 1
        planned_ratio = due_tasks / total_tasks
        pv = round(bac * planned_ratio, 2)
    elif target_dt and target_dt > start_dt:
        # Interpolación lineal en función del tiempo transcurrido
        total_duration = (target_dt - start_dt).total_seconds()
        elapsed = (now - start_dt).total_seconds()
        time_ratio = max(0.0, min(1.0, elapsed / max(total_duration, 1.0)))
        pv = round(bac * time_ratio, 2)
    else:
        pv = ev

    # 5. Índice de Desempeño del Costo (CPI = EV / AC)
    if ac > 0:
        cpi = round(ev / ac, 2)
    else:
        cpi = 1.0 if ev == 0.0 else 2.0  # Sin gasto aún

    # 6. Índice de Desempeño del Cronograma (SPI = EV / PV)
    if pv > 0:
        spi = round(ev / pv, 2)
    else:
        spi = 1.0 if ev == 0.0 else 2.0

    # 7. Variaciones (CV y SV)
    cv = round(ev - ac, 2)
    sv = round(ev - pv, 2)

    # 8. Razón Crítica (CR = CPI * SPI)
    cr = round(cpi * spi, 2)

    # 9. Estimación y Variación a la Conclusión (EAC y VAC)
    if cpi > 0:
        eac = round(bac / cpi, 2)
    else:
        eac = bac
    vac = round(bac - eac, 2)

    financial_pct = round((ac / max(bac, 1.0)) * 100.0, 1) if bac > 0 else 0.0

    # 10. Diagnóstico y Semáforo
    recommendations: List[str] = []
    if cpi >= 1.0 and spi >= 1.0:
        health_status = "OPTIMO"
        health_color = "success"
        recommendations.append("El proyecto avanza según el cronograma y dentro del presupuesto aprobado.")
        recommendations.append("Mantener el ritmo de control semanal de hitos y tareas.")
    elif cpi >= 1.0 and spi < 1.0:
        health_status = "ATRASADO_SIN_SOBRECOSTO"
        health_color = "warning"
        recommendations.append(f"El cronograma presenta atraso (SPI: {spi}), pero los costos se mantienen bajo control (CPI: {cpi}).")
        recommendations.append("Revisar dependencias bloqueadas y evaluar aceleración de entregables en la ruta crítica.")
    elif cpi < 1.0 and spi >= 1.0:
        health_status = "ADELANTADO_CON_SOBRECOSTO"
        health_color = "warning"
        recommendations.append(f"El trabajo físico avanza a buen ritmo (SPI: {spi}), pero hay sobrecosto financiero (CPI: {cpi}).")
        recommendations.append("Auditar partidas de gasto y restringir adquisiciones no presupuestadas.")
    else:
        health_status = "CRITICO_RETRASO_Y_SOBRECOSTO"
        health_color = "destructive"
        recommendations.append(f"Alerta crítica: El proyecto presenta atraso físico (SPI: {spi}) y sobrecosto financiero (CPI: {cpi}).")
        recommendations.append("Convocar comité de proyecto para revisar la línea base y aplicar plan de contingencia.")
        recommendations.append(f"Pronóstico de costo final estimado al cierre: ${eac:,.2f} (Variación estimada: ${vac:,.2f}).")

    return {
        "project_id": str(project.id),
        "calculated_at": now.isoformat(),
        "bac": bac,
        "ac": ac,
        "ev": ev,
        "pv": pv,
        "progress_percentage": progress_pct,
        "financial_percentage": financial_pct,
        "cpi": cpi,
        "spi": spi,
        "cv": cv,
        "sv": sv,
        "cr": cr,
        "eac": eac,
        "vac": vac,
        "health_status": health_status,
        "health_color": health_color,
        "recommendations": recommendations,
    }


def generate_curve_s_data(db: Session, project: Project, points_count: int = 8) -> List[Dict[str, Any]]:
    """Genera las series temporales acumuladas de PV, EV y AC para graficar la Curva S."""
    now = _utcnow()
    bac = float(project.budget_allocated or 0.0)
    start_dt = _as_utc(project.start_date) or _as_utc(project.created_at) or now
    target_dt = _as_utc(project.target_date) or (start_dt + timedelta(days=90))

    if target_dt <= start_dt:
        target_dt = start_dt + timedelta(days=30)

    total_seconds = (target_dt - start_dt).total_seconds()
    step_seconds = total_seconds / max(points_count - 1, 1)

    # Gastos históricos ordenados
    expenses = (
        db.query(ProjectExpense)
        .filter(
            ProjectExpense.project_id == project.id,
            ProjectExpense.deleted_at.is_(None),
            ProjectExpense.status.in_(["approved", "paid"]),
        )
        .order_by(ProjectExpense.date.asc())
        .all()
    )

    current_evm = calculate_project_evm(db, project)
    final_ev = current_evm["ev"]
    final_ac = current_evm["ac"]

    points: List[Dict[str, Any]] = []

    for i in range(points_count):
        pt_dt = start_dt + timedelta(seconds=i * step_seconds)
        time_ratio = i / (points_count - 1)

        # 1. PV sigue típicamente una curva sigmoidea (S-curve) suave
        # Formula sigmoidea estándar normalizada: 3*t^2 - 2*t^3
        smooth_ratio = (3 * (time_ratio ** 2)) - (2 * (time_ratio ** 3))
        pv_val = round(bac * smooth_ratio, 2)

        # 2. AC acumulado a la fecha pt_dt
        if pt_dt <= now:
            ac_subset = sum(float(e.amount or 0.0) for e in expenses if _as_utc(e.date) <= pt_dt)
            # Interpolar con final_ac si no hay detalle de recibos
            if not expenses and final_ac > 0:
                elapsed_to_now = (min(pt_dt, now) - start_dt).total_seconds()
                now_total = max((now - start_dt).total_seconds(), 1.0)
                ac_val = round(final_ac * min(1.0, elapsed_to_now / now_total), 2)
            else:
                ac_val = round(ac_subset, 2)

            # 3. EV acumulado a la fecha pt_dt
            elapsed_to_pt = (pt_dt - start_dt).total_seconds()
            now_total = max((now - start_dt).total_seconds(), 1.0)
            ev_ratio = min(1.0, max(0.0, elapsed_to_pt / now_total))
            ev_val = round(final_ev * ev_ratio, 2)

            cpi_pt = round(ev_val / ac_val, 2) if ac_val > 0 else (1.0 if ev_val == 0 else 2.0)
            spi_pt = round(ev_val / pv_val, 2) if pv_val > 0 else 1.0
        else:
            # Proyección a futuro
            ac_val = None
            ev_val = None
            cpi_pt = None
            spi_pt = None

        points.append(
            {
                "date": pt_dt.strftime("%Y-%m-%d"),
                "label": pt_dt.strftime("%d %b"),
                "pv": pv_val,
                "ev": ev_val,
                "ac": ac_val,
                "cpi": cpi_pt,
                "spi": spi_pt,
            }
        )

    return points


# ── Component-Level EVM and 100% Rule Validation (PMI / WBS) ───────────────


def calculate_component_evm(
    db: Session,
    component: ProjectComponent,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """Calcula las métricas EVM y balance físico-financiero para un componente EDT.

    - BAC: Presupuesto asignado al componente.
    - Avance Físico: Ratio de tareas completadas asignadas al componente.
    - EV: BAC * (% Avance Físico).
    - AC: Suma de gastos con estado 'approved' o 'paid' vinculados al componente.
    - PV: Valor planificado a la fecha según vencimiento de tareas del componente.
    - CPI: EV / AC (1.0 si AC=0 y EV=0, 2.0 si AC=0 y EV>0).
    - SPI: EV / PV (1.0 si PV=0).
    - Balance Gap (%): Avance físico (%) - Avance financiero (%).
    """
    now = now or _utcnow()
    bac = float(component.budget_allocated or 0.0)

    # 1. Tareas asociadas al componente
    tasks = (
        db.query(ProjectTask)
        .filter(
            ProjectTask.component_id == component.id,
            ProjectTask.deleted_at.is_(None),
        )
        .all()
    )
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status in ("completed", "done"))

    # Avance físico continuo ponderado por esfuerzo o conteo
    if total_tasks > 0:
        total_hours = sum(_safe_float(getattr(t, "estimated_hours", 0.0)) for t in tasks)
        has_continuous_progress = any(_safe_float(getattr(t, "physical_progress_pct", 0.0)) > 0 for t in tasks)

        if total_hours > 0:
            weighted_sum = sum(
                (
                    _safe_float(getattr(t, "physical_progress_pct", 0.0))
                    or (100.0 if t.status in ("completed", "done") else 0.0)
                )
                * (
                    _safe_float(getattr(t, "estimated_hours", 0.0))
                    if _safe_float(getattr(t, "estimated_hours", 0.0)) > 0
                    else 1.0
                )
                for t in tasks
            )
            weight_denom = sum(
                (
                    _safe_float(getattr(t, "estimated_hours", 0.0))
                    if _safe_float(getattr(t, "estimated_hours", 0.0)) > 0
                    else 1.0
                )
                for t in tasks
            )
            physical_pct = round(weighted_sum / weight_denom, 1)
        elif has_continuous_progress:
            physical_pct = round(
                sum(
                    _safe_float(getattr(t, "physical_progress_pct", 0.0))
                    or (100.0 if t.status in ("completed", "done") else 0.0)
                    for t in tasks
                )
                / total_tasks,
                1,
            )
        else:
            physical_pct = round((completed_tasks / total_tasks) * 100.0, 1)
    else:
        physical_pct = 0.0

    # 2. EV (Earned Value)
    ev = round(bac * (physical_pct / 100.0), 2)

    # 3. AC (Actual Cost): gastos asignados al componente O a sus tareas
    task_ids = [t.id for t in tasks]
    direct_comp_expenses = (
        db.query(ProjectExpense)
        .filter(
            ProjectExpense.component_id == component.id,
            ProjectExpense.deleted_at.is_(None),
            ProjectExpense.status.in_(["approved", "paid"]),
        )
        .all()
    )
    task_comp_expenses = []
    if task_ids:
        task_comp_expenses = (
            db.query(ProjectExpense)
            .filter(
                ProjectExpense.task_id.in_(task_ids),
                ProjectExpense.deleted_at.is_(None),
                ProjectExpense.status.in_(["approved", "paid"]),
            )
            .all()
        )
    # Deduplicar por ID
    unique_expenses = {e.id: e for e in direct_comp_expenses + task_comp_expenses}
    ac = round(sum(float(e.amount or 0.0) for e in unique_expenses.values()), 2)

    # 4. PV (Planned Value)
    if total_tasks > 0:
        due_tasks = 0
        for t in tasks:
            t_due = _as_utc(t.due_date)
            if t_due and t_due <= now:
                due_tasks += 1
        planned_ratio = due_tasks / total_tasks
        pv = round(bac * planned_ratio, 2)
    else:
        pv = ev

    # 5. CPI y SPI
    if ac > 0:
        cpi = round(ev / ac, 2)
    else:
        cpi = 1.0 if ev == 0.0 else 2.0

    if pv > 0:
        spi = round(ev / pv, 2)
    else:
        spi = 1.0 if ev == 0.0 else 2.0

    cv = round(ev - ac, 2)
    sv = round(ev - pv, 2)
    cr = round(cpi * spi, 2)

    financial_pct = round((ac / max(bac, 1.0)) * 100.0, 1) if bac > 0 else 0.0
    balance_gap = round(physical_pct - financial_pct, 1)

    # Semáforo de salud del componente
    if cpi >= 1.0 and spi >= 1.0:
        health_status = "OPTIMO"
        health_color = "success"
    elif cpi >= 1.0 and spi < 1.0:
        health_status = "ATRASADO_SIN_SOBRECOSTO"
        health_color = "warning"
    elif cpi < 1.0 and spi >= 1.0:
        health_status = "ADELANTADO_CON_SOBRECOSTO"
        health_color = "warning"
    else:
        health_status = "CRITICO_RETRASO_Y_SOBRECOSTO"
        health_color = "destructive"

    return {
        "component_id": str(component.id),
        "code": component.code,
        "name": component.name,
        "budget_allocated": bac,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "physical_progress_pct": physical_pct,
        "ev": ev,
        "pv": pv,
        "ac": ac,
        "cpi": cpi,
        "spi": spi,
        "cv": cv,
        "sv": sv,
        "cr": cr,
        "financial_progress_pct": financial_pct,
        "balance_gap_pct": balance_gap,
        "health_status": health_status,
        "health_color": health_color,
    }


def validate_project_budget_100_rule(db: Session, project: Project) -> Dict[str, Any]:
    """Valida la Regla del 100% de la EDT (PMI / PMBOK).

    La suma de los presupuestos asignados a cada componente debe corresponder
    al 100% del presupuesto asignado al proyecto (BAC).
    """
    project_budget = float(project.budget_allocated or 0.0)
    components = (
        db.query(ProjectComponent)
        .filter(
            ProjectComponent.project_id == project.id,
            ProjectComponent.deleted_at.is_(None),
        )
        .order_by(ProjectComponent.order_index.asc())
        .all()
    )

    components_total = round(sum(float(c.budget_allocated or 0.0) for c in components), 2)
    difference = round(project_budget - components_total, 2)

    if project_budget > 0:
        allocation_pct = round((components_total / project_budget) * 100.0, 2)
    else:
        allocation_pct = 0.0

    recommendations: List[str] = []
    is_fully_allocated = abs(difference) < 0.01 and project_budget > 0

    if project_budget == 0.0:
        status_code = "no_project_budget"
        is_satisfied = False
        recommendations.append(
            "El proyecto no tiene un presupuesto total asignado (budget_allocated). "
            "Configure el presupuesto global del proyecto para validar la Regla del 100%."
        )
    elif abs(difference) < 0.01:
        status_code = "balanced"
        is_satisfied = True
        recommendations.append(
            "El presupuesto de los componentes cubre exactamente el 100% del presupuesto del proyecto. "
            "Cumple estrictamente la Regla del 100% PMI."
        )
    elif components_total < project_budget:
        status_code = "under_allocated"
        is_satisfied = True  # No excede el presupuesto, pero hay saldo pendiente
        pct_remaining = round(100.0 - allocation_pct, 1)
        recommendations.append(
            f"Falta asignar ${difference:,.2f} ({pct_remaining}%) del presupuesto global en componentes de la EDT."
        )
        recommendations.append("Cree o amplíe componentes para completar la descomposición total del proyecto.")
    else:
        status_code = "over_allocated"
        is_satisfied = False
        exceeded_amount = round(abs(difference), 2)
        recommendations.append(
            f"Alerta presupuestal PMI: La suma de componentes (${components_total:,.2f}) excede el presupuesto "
            f"aprobado (${project_budget:,.2f}) por ${exceeded_amount:,.2f} ({allocation_pct}% asignado)."
        )
        recommendations.append("Ajuste el presupuesto de los componentes o solicite una ampliación del BAC del proyecto.")

    return {
        "project_id": str(project.id),
        "project_budget_allocated": project_budget,
        "components_budget_total": components_total,
        "budget_difference": difference,
        "allocation_percentage": allocation_pct,
        "is_rule_satisfied": is_satisfied,
        "is_fully_allocated": is_fully_allocated,
        "status": status_code,
        "components_count": len(components),
        "recommendations": recommendations,
    }


def get_project_components_breakdown(db: Session, project: Project) -> Dict[str, Any]:
    """Genera el desglose completo de componentes EDT con EVM y la validación de la Regla del 100%."""
    budget_rule = validate_project_budget_100_rule(db, project)

    components = (
        db.query(ProjectComponent)
        .filter(
            ProjectComponent.project_id == project.id,
            ProjectComponent.deleted_at.is_(None),
        )
        .order_by(ProjectComponent.order_index.asc(), ProjectComponent.code.asc())
        .all()
    )

    component_details = []
    for comp in components:
        evm = calculate_component_evm(db, comp)
        tasks_count = (
            db.query(ProjectTask)
            .filter(ProjectTask.component_id == comp.id, ProjectTask.deleted_at.is_(None))
            .count()
        )
        expenses_count = (
            db.query(ProjectExpense)
            .filter(ProjectExpense.component_id == comp.id, ProjectExpense.deleted_at.is_(None))
            .count()
        )
        component_details.append(
            {
                "id": str(comp.id),
                "project_id": str(comp.project_id),
                "code": comp.code,
                "name": comp.name,
                "description": comp.description,
                "budget_allocated": float(comp.budget_allocated or 0.0),
                "order_index": comp.order_index,
                "color": comp.color or "#3b82f6",
                "status": comp.status,
                "created_at": comp.created_at,
                "updated_at": comp.updated_at,
                "deleted_at": comp.deleted_at,
                "tasks_count": tasks_count,
                "expenses_count": expenses_count,
                "evm": evm,
            }
        )

    return {
        "project_id": str(project.id),
        "components": component_details,
        "budget_rule": budget_rule,
    }


# ============================================================================
# WBS / EDT Nivel 3: Paquetes de Trabajo, 3 Dimensiones y Roll-Up (Fase 3)
# ============================================================================


def get_task_descendant_ids(db: Session, task_id: Any) -> List[Any]:
    """Obtiene recursivamente todos los UUIDs de subtareas activas (WBS Nivel 3, 4, ...)."""
    descendants: List[Any] = []
    queue = [task_id]
    visited = {str(task_id)}
    while queue:
        current_id = queue.pop(0)
        children = (
            db.query(ProjectTask.id)
            .filter(
                ProjectTask.parent_id == current_id,
                ProjectTask.deleted_at.is_(None),
            )
            .all()
        )
        for child_row in children:
            cid = child_row[0]
            str_cid = str(cid)
            if str_cid not in visited:
                visited.add(str_cid)
                descendants.append(cid)
                queue.append(cid)
    return descendants


def calculate_task_rollup(db: Session, task: ProjectTask) -> Dict[str, Any]:
    """Calcula las 3 Dimensiones de Control PMI y el Roll-Up de un paquete de trabajo."""
    # 1. Subtareas directas y descendientes
    direct_subtasks = (
        db.query(ProjectTask)
        .filter(
            ProjectTask.parent_id == task.id,
            ProjectTask.deleted_at.is_(None),
        )
        .order_by(ProjectTask.order_index.asc())
        .all()
    )
    is_leaf = len(direct_subtasks) == 0
    descendant_ids = get_task_descendant_ids(db, task.id)
    all_descendants = (
        db.query(ProjectTask)
        .filter(ProjectTask.id.in_(descendant_ids), ProjectTask.deleted_at.is_(None))
        .all()
        if descendant_ids
        else []
    )

    # ── Dimensión 1: Tiempo y Esfuerzo ──────────────────────────────────────────
    est_hours = _safe_float(getattr(task, "estimated_hours", 0.0))
    subtasks_est_hours = round(
        sum(_safe_float(getattr(st, "estimated_hours", 0.0)) for st in all_descendants), 2
    )
    total_est_hours = round(est_hours + subtasks_est_hours, 2) if est_hours > 0 else subtasks_est_hours

    # Horas reales desde project_time_logs
    all_task_ids = [task.id] + descendant_ids
    time_logs = (
        db.query(ProjectTimeLog)
        .filter(
            ProjectTimeLog.task_id.in_(all_task_ids),
            ProjectTimeLog.deleted_at.is_(None),
        )
        .all()
    )
    actual_hours = round(sum(_safe_float(tl.hours) for tl in time_logs), 2)

    duration_days = None
    if task.start_date and task.due_date:
        duration_days = max(1, (task.due_date - task.start_date).days + 1)

    time_dim = {
        "estimated_hours": est_hours,
        "actual_hours": actual_hours,
        "start_date": task.start_date,
        "due_date": task.due_date,
        "duration_days": duration_days,
        "subtasks_estimated_hours": subtasks_est_hours,
        "total_estimated_hours": total_est_hours,
    }

    # ── Dimensión 2: Avance Físico Continuo y Ponderado ──────────────────────────
    raw_physical_pct = _safe_float(getattr(task, "physical_progress_pct", 0.0))
    if is_leaf:
        if task.status in ("completed", "done") and raw_physical_pct == 0.0:
            raw_physical_pct = 100.0
        rolled_up_progress_pct = round(max(0.0, min(100.0, raw_physical_pct)), 2)
        weight_basis = "estimated_hours"
        completed_subtasks = 0
    else:
        # Calcular el avance continuo de cada subtarea directa
        subtask_progress_list = []
        for sub in direct_subtasks:
            sub_rollup = calculate_task_rollup(db, sub)
            sub_pct = sub_rollup["progress"]["rolled_up_progress_pct"]
            sub_weight = _safe_float(getattr(sub, "estimated_hours", 0.0))
            subtask_progress_list.append((sub_pct, sub_weight))

        total_weight = sum(w for _, w in subtask_progress_list if w > 0)
        if total_weight > 0:
            rolled_up_progress_pct = round(
                sum(pct * (w if w > 0 else 1.0) for pct, w in subtask_progress_list)
                / sum(w if w > 0 else 1.0 for _, w in subtask_progress_list),
                2,
            )
            weight_basis = "estimated_hours"
        else:
            rolled_up_progress_pct = round(
                sum(pct for pct, _ in subtask_progress_list) / len(subtask_progress_list), 2
            )
            weight_basis = "equal_count"

        completed_subtasks = sum(1 for st in direct_subtasks if st.status in ("completed", "done"))

    progress_dim = {
        "physical_progress_pct": raw_physical_pct,
        "rolled_up_progress_pct": rolled_up_progress_pct,
        "is_leaf": is_leaf,
        "subtasks_count": len(direct_subtasks),
        "completed_subtasks_count": completed_subtasks,
        "weight_basis": weight_basis,
    }

    # ── Dimensión 3: Costos e Imputación Financiera ──────────────────────────────
    direct_expenses = (
        db.query(ProjectExpense)
        .filter(
            ProjectExpense.task_id == task.id,
            ProjectExpense.deleted_at.is_(None),
        )
        .all()
    )
    direct_cost = round(sum(_safe_float(e.amount) for e in direct_expenses), 2)

    subtask_expenses = []
    if descendant_ids:
        subtask_expenses = (
            db.query(ProjectExpense)
            .filter(
                ProjectExpense.task_id.in_(descendant_ids),
                ProjectExpense.deleted_at.is_(None),
            )
            .all()
        )
    subtasks_cost = round(sum(_safe_float(e.amount) for e in subtask_expenses), 2)
    total_cost = round(direct_cost + subtasks_cost, 2)

    all_expenses = direct_expenses + subtask_expenses
    actual_cost = round(
        sum(_safe_float(e.amount) for e in all_expenses if e.status in ("approved", "paid")), 2
    )
    planned_cost = round(
        sum(_safe_float(e.amount) for e in all_expenses if e.status == "planned"), 2
    )
    committed_cost = round(
        sum(_safe_float(e.amount) for e in all_expenses if e.status == "committed"), 2
    )

    cost_dim = {
        "direct_cost": direct_cost,
        "subtasks_cost": subtasks_cost,
        "total_cost": total_cost,
        "actual_cost": actual_cost,
        "planned_cost": planned_cost,
        "committed_cost": committed_cost,
        "expenses_count": len(all_expenses),
    }

    component_name = task.component.name if getattr(task, "component", None) else None

    # Preparar lista de gastos asociados
    expenses_out = []
    for exp in all_expenses:
        expenses_out.append(
            {
                "id": str(exp.id),
                "project_id": str(exp.project_id),
                "component_id": str(exp.component_id) if exp.component_id else None,
                "task_id": str(exp.task_id) if exp.task_id else None,
                "task_title": task.title if exp.task_id == task.id else None,
                "category": exp.category,
                "description": exp.description,
                "amount": float(exp.amount or 0.0),
                "date": exp.date,
                "receipt_url": exp.receipt_url,
                "status": exp.status,
                "created_by": str(exp.created_by) if exp.created_by else None,
                "creator_name": exp.creator.nombre_completo if getattr(exp, "creator", None) else None,
                "created_at": exp.created_at,
                "updated_at": exp.updated_at,
            }
        )

    return {
        "task_id": str(task.id),
        "project_id": str(task.project_id),
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "parent_id": str(task.parent_id) if task.parent_id else None,
        "component_id": str(task.component_id) if task.component_id else None,
        "component_name": component_name,
        "time": time_dim,
        "progress": progress_dim,
        "cost": cost_dim,
        "expenses": expenses_out,
    }


def sync_parent_task_rollup(db: Session, parent_id: Any) -> None:
    """Actualiza en cascada el avance físico continuo del nodo padre basándose en sus subtareas."""
    if not parent_id:
        return
    parent = (
        db.query(ProjectTask)
        .filter(ProjectTask.id == parent_id, ProjectTask.deleted_at.is_(None))
        .first()
    )
    if not parent:
        return
    rollup = calculate_task_rollup(db, parent)
    new_pct = rollup["progress"]["rolled_up_progress_pct"]
    parent.physical_progress_pct = new_pct
    db.commit()
    # Si el padre a su vez tiene un parent_id, propagar hacia arriba recursivamente
    if parent.parent_id:
        sync_parent_task_rollup(db, parent.parent_id)


def calculate_project_tasks_rollup(db: Session, project: Project) -> Dict[str, Any]:
    """Calcula el Roll-Up consolidado de todas las tareas y paquetes de trabajo a nivel de proyecto."""
    all_tasks = (
        db.query(ProjectTask)
        .filter(ProjectTask.project_id == project.id, ProjectTask.deleted_at.is_(None))
        .order_by(ProjectTask.order_index.asc())
        .all()
    )

    tasks_details = []
    root_progress_values = []
    root_hours_weights = []
    total_est_hours = 0.0
    tasks_with_expenses = 0
    total_expenses_cost = 0.0
    leaf_count = 0
    parent_count = 0

    for t in all_tasks:
        rollup = calculate_task_rollup(db, t)
        tasks_details.append(rollup)

        if rollup["progress"]["is_leaf"]:
            leaf_count += 1
            total_est_hours += rollup["time"]["estimated_hours"]
        else:
            parent_count += 1

        if rollup["cost"]["total_cost"] > 0:
            tasks_with_expenses += 1
            total_expenses_cost += rollup["cost"]["total_cost"]

        # Si es tarea raíz (sin parent_id), contribuye al promedio global del proyecto
        if t.parent_id is None:
            root_pct = rollup["progress"]["rolled_up_progress_pct"]
            root_weight = rollup["time"]["total_estimated_hours"] or 1.0
            root_progress_values.append(root_pct)
            root_hours_weights.append(root_weight)

    # Horas reales totales desde time_logs
    time_logs = (
        db.query(ProjectTimeLog)
        .filter(ProjectTimeLog.project_id == project.id, ProjectTimeLog.deleted_at.is_(None))
        .all()
    )
    total_actual_hours = round(sum(float(tl.hours or 0.0) for tl in time_logs), 2)

    # Avance físico global ponderado
    if root_progress_values:
        total_root_weight = sum(root_hours_weights)
        if total_root_weight > 0:
            overall_pct = round(
                sum(p * w for p, w in zip(root_progress_values, root_hours_weights)) / total_root_weight,
                2,
            )
        else:
            overall_pct = round(sum(root_progress_values) / len(root_progress_values), 2)
    else:
        overall_pct = 0.0

    return {
        "project_id": str(project.id),
        "total_tasks": len(all_tasks),
        "leaf_tasks_count": leaf_count,
        "parent_tasks_count": parent_count,
        "total_estimated_hours": round(total_est_hours, 2),
        "total_actual_hours": total_actual_hours,
        "overall_physical_progress_pct": overall_pct,
        "total_expenses_cost": round(total_expenses_cost, 2),
        "tasks_with_expenses_count": tasks_with_expenses,
        "tasks_rollup": tasks_details,
    }


# ============================================================================
# WBS / EDT Nivel 4: Matriz de 4 Cuadrantes, Organigrama WBS y Modelos EAC (Fase 4)
# ============================================================================


def calculate_earned_schedule(
    db: Session,
    project: Project,
    ev: float,
    bac: float,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """Calcula las métricas de Tiempo Ganado (Earned Schedule - ES) bajo estándar Lipke / PMI."""
    if now is None:
        now = _utcnow()

    start_dt = _as_utc(project.start_date) or _as_utc(project.created_at) or now
    target_dt = _as_utc(project.target_date) or (start_dt + timedelta(days=90))
    if target_dt <= start_dt:
        target_dt = start_dt + timedelta(days=30)

    total_duration_days = max(1.0, (target_dt - start_dt).total_seconds() / 86400.0)
    actual_time_days = max(0.1, (now - start_dt).total_seconds() / 86400.0)

    # Interpolación de ES a partir de la curva normalizada sigmoidea de PV: 3*t^2 - 2*t^3
    if bac <= 0 or ev <= 0:
        es_days = 0.0
    elif ev >= bac:
        es_days = round(total_duration_days, 1)
    else:
        target_ratio = min(1.0, max(0.0, ev / bac))
        low, high = 0.0, 1.0
        for _ in range(25):
            mid = (low + high) / 2.0
            val = (3.0 * (mid ** 2)) - (2.0 * (mid ** 3))
            if val < target_ratio:
                low = mid
            else:
                high = mid
        t_fraction = (low + high) / 2.0
        es_days = round(t_fraction * total_duration_days, 1)

    # Variación en tiempo SV(t) = ES - AT
    sv_t_days = round(es_days - actual_time_days, 1)

    # Índice de desempeño en tiempo SPI(t) = ES / AT
    if actual_time_days > 0:
        spi_t = round(es_days / actual_time_days, 2)
    else:
        spi_t = 1.0

    # Duración estimada a la conclusión EDAC = PD / SPI(t)
    if spi_t > 0:
        edac_days = round(total_duration_days / spi_t, 1)
    else:
        edac_days = round(total_duration_days, 1)

    tvac_days = round(total_duration_days - edac_days, 1)
    projected_finish_date = (start_dt + timedelta(days=edac_days)).strftime("%Y-%m-%d")

    return {
        "planned_duration_days": round(total_duration_days, 1),
        "actual_time_days": round(actual_time_days, 1),
        "earned_schedule_days": es_days,
        "schedule_variance_time_days": sv_t_days,
        "schedule_performance_index_time": spi_t,
        "estimated_duration_at_completion_days": edac_days,
        "time_variance_at_completion_days": tvac_days,
        "projected_finish_date": projected_finish_date,
    }


def calculate_eac_forecasts(
    bac: float,
    ev: float,
    ac: float,
    cpi: float,
    spi: float,
) -> Dict[str, Any]:
    """Calcula los 3 Modelos de Pronóstico a la Conclusión (EAC, ETC, VAC) según el PMI / PMBOK."""
    work_remaining = max(0.0, bac - ev)

    # 1. EAC Típico: El desempeño de costos continuará al mismo ritmo (CPI)
    if cpi > 0:
        eac_typical = round(ac + (work_remaining / cpi), 2)
    else:
        eac_typical = round(ac + work_remaining, 2)
    etc_typical = round(max(0.0, eac_typical - ac), 2)
    vac_typical = round(bac - eac_typical, 2)
    vac_typical_pct = round((vac_typical / max(bac, 1.0)) * 100.0, 1)

    # 2. EAC Atípico: Las variaciones pasadas fueron atípicas; el trabajo restante costará según presupuesto
    eac_atypical = round(ac + work_remaining, 2)
    etc_atypical = round(work_remaining, 2)
    vac_atypical = round(bac - eac_atypical, 2)
    vac_atypical_pct = round((vac_atypical / max(bac, 1.0)) * 100.0, 1)

    # 3. EAC Combinado (CPI x SPI): El costo futuro se afecta por costos y retraso en el cronograma
    perf_factor = round(cpi * spi, 4)
    if perf_factor > 0:
        eac_composite = round(ac + (work_remaining / perf_factor), 2)
    elif cpi > 0:
        eac_composite = round(ac + (work_remaining / cpi), 2)
    else:
        eac_composite = round(ac + work_remaining, 2)
    etc_composite = round(max(0.0, eac_composite - ac), 2)
    vac_composite = round(bac - eac_composite, 2)
    vac_composite_pct = round((vac_composite / max(bac, 1.0)) * 100.0, 1)

    return {
        "typical": {
            "model_key": "typical",
            "title": "Pronóstico Típico (Tendencia CPI)",
            "description": "Asume que la eficiencia de costos actual (CPI) continuará durante el trabajo restante.",
            "formula": "EAC = AC + ((BAC - EV) / CPI)",
            "eac": eac_typical,
            "etc": etc_typical,
            "vac": vac_typical,
            "vac_percentage": vac_typical_pct,
        },
        "atypical": {
            "model_key": "atypical",
            "title": "Pronóstico Atípico (Presupuestado)",
            "description": "Asume que las variaciones pasadas fueron atípicas y el trabajo restante se ejecutará según el plan original.",
            "formula": "EAC = AC + (BAC - EV)",
            "eac": eac_atypical,
            "etc": etc_atypical,
            "vac": vac_atypical,
            "vac_percentage": vac_atypical_pct,
        },
        "composite": {
            "model_key": "composite",
            "title": "Pronóstico Combinado (CPI × SPI)",
            "description": "Modelo estricto que castiga el costo futuro por la ineficiencia de costo y el retraso en el cronograma.",
            "formula": "EAC = AC + ((BAC - EV) / (CPI × SPI))",
            "eac": eac_composite,
            "etc": etc_composite,
            "vac": vac_composite,
            "vac_percentage": vac_composite_pct,
        },
    }


def calculate_tcpi(
    bac: float,
    ev: float,
    ac: float,
    eac: float,
) -> Dict[str, Any]:
    """Calcula el Índice de Desempeño del Trabajo por Completar (TCPI)."""
    work_remaining = bac - ev
    funds_remaining_bac = bac - ac
    funds_remaining_eac = eac - ac

    is_budget_depleted = funds_remaining_bac <= 0

    if funds_remaining_bac > 0 and work_remaining >= 0:
        tcpi_bac = round(work_remaining / funds_remaining_bac, 2)
    else:
        tcpi_bac = None

    if funds_remaining_eac > 0 and work_remaining >= 0:
        tcpi_eac = round(work_remaining / funds_remaining_eac, 2)
    else:
        tcpi_eac = None

    if is_budget_depleted:
        difficulty = "critical"
        explanation = (
            "El presupuesto inicial (BAC) ha sido consumido en su totalidad. "
            "Requiere gestionar una adición presupuestaria formal o descopar el proyecto."
        )
    elif tcpi_bac is not None and tcpi_bac <= 1.0:
        difficulty = "feasible"
        explanation = f"TCPI de {tcpi_bac:.2f}: Se cuenta con holgura para completar el trabajo restante dentro del presupuesto original."
    elif tcpi_bac is not None and tcpi_bac <= 1.10:
        difficulty = "moderate"
        explanation = f"TCPI de {tcpi_bac:.2f}: Exige un control riguroso de cada partida para no exceder el presupuesto BAC."
    else:
        difficulty = "hard"
        tcpi_val = f"{tcpi_bac:.2f}" if tcpi_bac is not None else ">1.50"
        explanation = f"TCPI de {tcpi_val}: Nivel de exigencia muy alto. Es poco probable cumplir el BAC; se recomienda adoptar el EAC ({eac:,.2f}) como nueva meta."

    return {
        "tcpi_bac": tcpi_bac,
        "tcpi_eac": tcpi_eac,
        "is_budget_depleted": is_budget_depleted,
        "difficulty_level": difficulty,
        "explanation": explanation,
    }


def calculate_cpi_spi_quadrant(
    cpi: float,
    spi: float,
    spi_t: float,
    cr: float,
    physical_pct: float,
    financial_pct: float,
    tcpi_bac: Optional[float],
) -> Dict[str, Any]:
    """Calcula la ubicación en la Matriz de 4 Cuadrantes y detecta Alertas Tempranas (Regla del 15% PMI)."""
    # Determinar cuadrante con centro en (1.0, 1.0)
    if cpi >= 1.0 and spi >= 1.0:
        quadrant_id = "quadrant_1"
        quadrant_number = 1
        name = "Zona Óptima"
        health_status = "OPTIMO"
        badge_color = "success"
        description = "Eficiencia de costos alta (CPI >= 1.0) y avance de cronograma adelantado o al día (SPI >= 1.0)."
        action_recommendation = "Mantener los estándares de supervisión y documentar las buenas prácticas como lecciones aprendidas."
    elif cpi >= 1.0 and spi < 1.0:
        quadrant_id = "quadrant_2"
        quadrant_number = 2
        name = "Zona de Riesgo / Aceleración"
        health_status = "RIESGO"
        badge_color = "warning"
        description = "Atraso en el cronograma (SPI < 1.0) pero con margen de ahorro financiero (CPI >= 1.0)."
        action_recommendation = "Aprovechar la holgura presupuestaria para acelerar actividades de la ruta crítica (horas extra o refuerzos)."
    elif cpi < 1.0 and spi < 1.0:
        quadrant_id = "quadrant_3"
        quadrant_number = 3
        name = "Zona Crítica"
        health_status = "CRITICO"
        badge_color = "destructive"
        description = "Combinación crítica de sobrecosto (CPI < 1.0) y atraso en cronograma (SPI < 1.0)."
        action_recommendation = "Alerta roja: Convocar comité de emergencia para renegociar alcance, congelar gastos no esenciales y re-establecer la línea base."
    else:  # cpi < 1.0 and spi >= 1.0
        quadrant_id = "quadrant_4"
        quadrant_number = 4
        name = "Zona de Atención / Falso Ahorro"
        health_status = "ATENCION"
        badge_color = "accent"
        description = "Cronograma adelantado (SPI >= 1.0) a costa de un sobrecosto financiero acelerado (CPI < 1.0)."
        action_recommendation = "Revisar si se está comprando aceleración a un precio insostenible (quema de presupuesto)."

    # Normalizar punto para renderizado en gráfico SVG / Canvas (escala de 0.4 a 1.6 mapeada a 0%..100%)
    clamp_spi = max(0.4, min(1.6, spi))
    clamp_cpi = max(0.4, min(1.6, cpi))
    point_x_pct = round(((clamp_spi - 0.4) / (1.6 - 0.4)) * 100.0, 1)
    # En pantalla, el eje Y va de arriba hacia abajo (1.6 = arriba = 0%, 0.4 = abajo = 100%)
    point_y_pct = round((1.0 - ((clamp_cpi - 0.4) / (1.6 - 0.4))) * 100.0, 1)

    # Detección de Alertas Tempranas (Regla del 15% PMI)
    alerts: List[Dict[str, Any]] = []
    rule_15_triggered = False

    # 1. Regla 15% en CPI
    if cpi < 0.85:
        rule_15_triggered = True
        alerts.append({
            "metric": "cpi",
            "level": "critical",
            "title": "Regla 15%: Sobrecosto Crítico",
            "detail": f"El CPI ({cpi:.2f}) se encuentra por debajo de 0.85 (>15% de desviación negativa). Alerta temprana de quiebra presupuestaria.",
            "threshold": "CPI < 0.85",
            "current_value": cpi,
        })
    elif cpi < 0.95:
        alerts.append({
            "metric": "cpi",
            "level": "warning",
            "title": "Sobrecosto Moderado",
            "detail": f"El CPI ({cpi:.2f}) presenta una desviación negativa moderada (5-15%).",
            "threshold": "0.85 <= CPI < 0.95",
            "current_value": cpi,
        })

    # 2. Regla 15% en SPI
    if spi < 0.85:
        rule_15_triggered = True
        alerts.append({
            "metric": "spi",
            "level": "critical",
            "title": "Regla 15%: Atraso Crítico en Cronograma",
            "detail": f"El SPI ({spi:.2f}) se encuentra por debajo de 0.85 (>15% de desviación en valor planificado).",
            "threshold": "SPI < 0.85",
            "current_value": spi,
        })
    elif spi < 0.95:
        alerts.append({
            "metric": "spi",
            "level": "warning",
            "title": "Atraso Moderado en Cronograma",
            "detail": f"El SPI ({spi:.2f}) presenta una desviación del 5-15%.",
            "threshold": "0.85 <= SPI < 0.95",
            "current_value": spi,
        })

    # 3. Regla 15% en SPI(t) de Tiempo Ganado
    if spi_t < 0.85:
        rule_15_triggered = True
        alerts.append({
            "metric": "spi_t",
            "level": "critical",
            "title": "Atraso Severo en Tiempo Ganado ES",
            "detail": f"El SPI(t) ({spi_t:.2f}) confirma un retraso de más del 15% en tiempo real cronológico.",
            "threshold": "SPI(t) < 0.85",
            "current_value": spi_t,
        })

    # 4. Razón Crítica (CR = CPI x SPI)
    if cr < 0.80:
        alerts.append({
            "metric": "cr",
            "level": "critical",
            "title": "Razón Crítica en Nivel Peligroso",
            "detail": f"La razón combinada CPI × SPI ({cr:.2f}) está por debajo de 0.80. Proyecto en alto riesgo de fracaso simultáneo.",
            "threshold": "CR < 0.80",
            "current_value": cr,
        })

    # 5. Brecha Físico-Financiera
    gap = abs(physical_pct - financial_pct)
    if gap > 15.0:
        alerts.append({
            "metric": "balance_gap",
            "level": "warning",
            "title": "Desfase Físico vs Financiero > 15%",
            "detail": f"Existe una brecha de {gap:.1f}% entre el avance físico ({physical_pct}%) y el consumo financiero ({financial_pct}%).",
            "threshold": "|Físico% - Financiero%| > 15%",
            "current_value": gap,
        })

    # 6. TCPI alto
    if tcpi_bac and tcpi_bac > 1.15:
        alerts.append({
            "metric": "tcpi",
            "level": "warning",
            "title": "TCPI Exigente para Cumplir Presupuesto",
            "detail": f"Se requiere un rendimiento de {tcpi_bac:.2f} (>1.15) en los fondos restantes para no exceder el presupuesto.",
            "threshold": "TCPI > 1.15",
            "current_value": tcpi_bac,
        })

    return {
        "quadrant_id": quadrant_id,
        "quadrant_number": quadrant_number,
        "name": name,
        "health_status": health_status,
        "badge_color": badge_color,
        "description": description,
        "action_recommendation": action_recommendation,
        "cpi": cpi,
        "spi": spi,
        "point_x_pct": point_x_pct,
        "point_y_pct": point_y_pct,
        "rule_15_triggered": rule_15_triggered,
        "alerts": alerts,
    }


def calculate_project_evm_advanced(
    db: Session,
    project: Project,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """Cálculo integral de EVM Avanzado: Matriz de 4 Cuadrantes, Pronósticos EAC, ES y TCPI."""
    if now is None:
        now = _utcnow()

    # 1. EVM Estándar
    std_evm = calculate_project_evm(db, project)
    bac = std_evm["bac"]
    ev = std_evm["ev"]
    ac = std_evm["ac"]
    cpi = std_evm["cpi"]
    spi = std_evm["spi"]
    cr = std_evm["cr"]
    physical_pct = std_evm["progress_percentage"]
    financial_pct = std_evm["financial_percentage"]

    # 2. Tiempo Ganado (Earned Schedule)
    earned_schedule = calculate_earned_schedule(db, project, ev=ev, bac=bac, now=now)
    spi_t = earned_schedule["schedule_performance_index_time"]

    # 3. Modelos de Pronóstico EAC
    forecasts = calculate_eac_forecasts(bac=bac, ev=ev, ac=ac, cpi=cpi, spi=spi)
    typical_eac = forecasts["typical"]["eac"]

    # 4. TCPI
    tcpi = calculate_tcpi(bac=bac, ev=ev, ac=ac, eac=typical_eac)

    # 5. Matriz de 4 Cuadrantes y Alertas Tempranas
    quadrant = calculate_cpi_spi_quadrant(
        cpi=cpi,
        spi=spi,
        spi_t=spi_t,
        cr=cr,
        physical_pct=physical_pct,
        financial_pct=financial_pct,
        tcpi_bac=tcpi["tcpi_bac"],
    )

    return {
        "project_id": str(project.id),
        "calculated_at": now.isoformat(),
        "standard_evm": std_evm,
        "earned_schedule": earned_schedule,
        "forecast_models": forecasts,
        "tcpi": tcpi,
        "quadrant": quadrant,
        "early_warnings": quadrant["alerts"],
    }


def build_project_wbs_tree(db: Session, project: Project) -> Dict[str, Any]:
    """Construye el Organigrama / Árbol WBS completo con codificación recursiva automática (1.1, 1.1.1)."""
    # 1. Obtener componentes
    components = (
        db.query(ProjectComponent)
        .filter(
            ProjectComponent.project_id == project.id,
            ProjectComponent.deleted_at.is_(None),
        )
        .order_by(ProjectComponent.order_index.asc())
        .all()
    )

    # 2. Obtener todas las tareas activas
    all_tasks = (
        db.query(ProjectTask)
        .filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        )
        .order_by(ProjectTask.order_index.asc())
        .all()
    )

    # Agrupar tareas por parent_id y por component_id
    tasks_by_parent: Dict[Optional[str], List[ProjectTask]] = {}
    tasks_by_component: Dict[Optional[str], List[ProjectTask]] = {}

    for t in all_tasks:
        p_id = str(t.parent_id) if t.parent_id else None
        tasks_by_parent.setdefault(p_id, []).append(t)

        c_id = str(t.component_id) if t.component_id else None
        if p_id is None:
            tasks_by_component.setdefault(c_id, []).append(t)

    # Función recursiva para construir nodos de tareas
    def build_task_node(task: ProjectTask, prefix: str, depth: int) -> Dict[str, Any]:
        task_id_str = str(task.id)
        children_tasks = tasks_by_parent.get(task_id_str, [])
        is_leaf = len(children_tasks) == 0

        rollup = calculate_task_rollup(db, task)

        child_nodes = []
        for idx, child in enumerate(children_tasks, start=1):
            child_prefix = f"{prefix}.{idx}"
            child_nodes.append(build_task_node(child, child_prefix, depth + 1))

        prog_pct = rollup["progress"]["rolled_up_progress_pct"]
        return {
            "id": task_id_str,
            "wbs_code": prefix,
            "title": task.title,
            "type": "task",
            "level": depth,
            "status": task.status,
            "progress_pct": prog_pct,
            "estimated_hours": rollup["time"]["total_estimated_hours"],
            "actual_hours": rollup["time"]["actual_hours"],
            "budget_allocated": None,
            "cost": rollup["cost"]["total_cost"],
            "is_leaf": is_leaf,
            "health_status": "OPTIMO" if prog_pct >= 100.0 else "EN_PROCESO",
            "children": child_nodes,
        }

    component_nodes = []
    max_depth = 1
    total_nodes = 1  # contando la raíz

    for c_idx, comp in enumerate(components, start=1):
        total_nodes += 1
        comp_prefix = str(c_idx)
        comp_evm = calculate_component_evm(db, comp)

        comp_tasks = tasks_by_component.get(str(comp.id), [])
        comp_children = []

        for t_idx, t in enumerate(comp_tasks, start=1):
            total_nodes += 1
            task_prefix = f"{comp_prefix}.{t_idx}"
            t_node = build_task_node(t, task_prefix, depth=2)
            comp_children.append(t_node)

            def update_node_stats(node: Dict[str, Any]) -> None:
                nonlocal max_depth, total_nodes
                if node["level"] > max_depth:
                    max_depth = node["level"]
                for ch in node["children"]:
                    total_nodes += 1
                    update_node_stats(ch)

            update_node_stats(t_node)

        comp_est_hours = sum(ch["estimated_hours"] for ch in comp_children)
        comp_act_hours = sum(ch["actual_hours"] for ch in comp_children)

        component_nodes.append({
            "id": str(comp.id),
            "wbs_code": comp_prefix,
            "title": comp.name,
            "type": "component",
            "level": 1,
            "status": comp.status,
            "progress_pct": comp_evm["physical_progress_pct"],
            "estimated_hours": round(comp_est_hours, 2),
            "actual_hours": round(comp_act_hours, 2),
            "budget_allocated": comp.budget_allocated,
            "cost": comp_evm["ac"],
            "is_leaf": len(comp_children) == 0,
            "health_status": comp_evm["health_status"],
            "children": comp_children,
        })

    # Tareas sin componente
    unassigned_tasks = tasks_by_component.get(None, [])
    if unassigned_tasks:
        total_nodes += 1
        unassigned_children = []
        for u_idx, t in enumerate(unassigned_tasks, start=1):
            total_nodes += 1
            t_prefix = f"0.{u_idx}"
            t_node = build_task_node(t, t_prefix, depth=2)
            unassigned_children.append(t_node)

            def update_unassigned_stats(node: Dict[str, Any]) -> None:
                nonlocal max_depth, total_nodes
                if node["level"] > max_depth:
                    max_depth = node["level"]
                for ch in node["children"]:
                    total_nodes += 1
                    update_unassigned_stats(ch)

            update_unassigned_stats(t_node)

        component_nodes.append({
            "id": "unassigned-component",
            "wbs_code": "0",
            "title": "Actividades Generales (Sin Componente)",
            "type": "component",
            "level": 1,
            "status": "active",
            "progress_pct": (
                round(sum(ch["progress_pct"] for ch in unassigned_children) / len(unassigned_children), 1)
                if unassigned_children
                else 0.0
            ),
            "estimated_hours": round(sum(ch["estimated_hours"] for ch in unassigned_children), 2),
            "actual_hours": round(sum(ch["actual_hours"] for ch in unassigned_children), 2),
            "budget_allocated": 0.0,
            "cost": round(sum(ch["cost"] for ch in unassigned_children), 2),
            "is_leaf": len(unassigned_children) == 0,
            "health_status": "EN_PROCESO",
            "children": unassigned_children,
        })

    # Raíz del proyecto
    project_evm = calculate_project_evm(db, project)
    root_node = {
        "id": str(project.id),
        "wbs_code": "0",
        "title": project.name,
        "type": "project",
        "level": 0,
        "status": project.status,
        "progress_pct": project_evm["progress_percentage"],
        "estimated_hours": round(sum(cn["estimated_hours"] for cn in component_nodes), 2),
        "actual_hours": round(sum(cn["actual_hours"] for cn in component_nodes), 2),
        "budget_allocated": project.budget_allocated,
        "cost": project_evm["ac"],
        "is_leaf": len(component_nodes) == 0,
        "health_status": project_evm["health_status"],
        "children": component_nodes,
    }

    return {
        "project_id": str(project.id),
        "project_title": project.name,
        "total_nodes": total_nodes,
        "max_depth": max_depth,
        "root": root_node,
    }




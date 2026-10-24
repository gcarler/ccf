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
import uuid
from collections.abc import Mapping, Sequence
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
        ProjectBaseline,
        ProjectComponent,
        ProjectExpense,
        ProjectMilestone,
        ProjectRisk,
        ProjectTask,
        ProjectTimeLog,
    )
except ImportError:
    # Fallback for testing environments without C-extension dependencies
    Project = _DummyModel  # type: ignore
    ProjectBaseline = _DummyModel  # type: ignore
    ProjectComponent = _DummyModel  # type: ignore
    ProjectExpense = _DummyModel  # type: ignore
    ProjectMilestone = _DummyModel  # type: ignore
    ProjectRisk = _DummyModel  # type: ignore
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


def _is_valid_id(val: Any) -> bool:
    return isinstance(val, (str, uuid.UUID)) and bool(str(val).strip())


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(timezone.utc)


def _get_active_baseline(db: Session, project_id: Any) -> Optional[Any]:
    """Obtiene la última línea base activa del proyecto (seguro ante MagicMock en tests unitarios)."""
    if not _is_valid_id(project_id):
        return None
    try:
        q = db.query(ProjectBaseline).filter(
            ProjectBaseline.project_id == project_id,
            ProjectBaseline.deleted_at.is_(None),
        )
        candidate = q.order_by(ProjectBaseline.created_at.desc()).first()
        if (
            candidate is not None
            and _is_valid_id(getattr(candidate, "id", None))
            and isinstance(getattr(candidate, "snapshot_data", None), dict)
        ):
            return candidate
    except Exception:
        pass
    return None


def _compute_tasks_weighted_progress_pct(tasks: List[Any]) -> float:
    """Calcula el avance físico continuo ponderado haciendo roll-up Subtareas -> Actividades.

    - Si existen relaciones jerárquicas (parent_id dentro del conjunto de tareas),
      las subtareas tributan primero a su actividad padre ponderadas por estimated_hours.
    - Las actividades raíz tributan al nivel superior ponderadas por su esfuerzo total
      (estimated_hours propio + subtareas) o en proporción igual si no hay horas estimadas.
    """
    if not tasks:
        return 0.0

    task_map: Dict[str, Any] = {}
    for t in tasks:
        tid = getattr(t, "id", None)
        if _is_valid_id(tid):
            task_map[str(tid)] = t

    children_map: Dict[str, List[Any]] = {}
    child_ids: set[str] = set()
    for t in tasks:
        tid = getattr(t, "id", None)
        pid = getattr(t, "parent_id", None)
        if _is_valid_id(pid) and str(pid) in task_map:
            if not _is_valid_id(tid) or str(tid) != str(pid):
                children_map.setdefault(str(pid), []).append(t)
                if _is_valid_id(tid):
                    child_ids.add(str(tid))

    visited: set[str] = set()

    def _eval_node(node: Any) -> tuple[float, float]:
        nid_raw = getattr(node, "id", None)
        nid = str(nid_raw) if _is_valid_id(nid_raw) else None
        if nid and nid in visited:
            children: List[Any] = []
        else:
            if nid:
                visited.add(nid)
            children = children_map.get(nid, []) if nid else []

        own_est = max(0.0, _safe_float(getattr(node, "estimated_hours", 0.0)))
        raw_pct = _safe_float(getattr(node, "physical_progress_pct", 0.0))
        if getattr(node, "status", None) in ("completed", "done") and raw_pct == 0.0:
            raw_pct = 100.0
        own_pct = max(0.0, min(100.0, raw_pct))

        if not children:
            return own_pct, own_est

        child_evals = [_eval_node(ch) for ch in children]
        total_child_hours = sum(w for _, w in child_evals if w > 0)
        if total_child_hours > 0:
            rolled_pct = sum(p * (w if w > 0 else 1.0) for p, w in child_evals) / sum(
                (w if w > 0 else 1.0) for _, w in child_evals
            )
        else:
            rolled_pct = sum(p for p, _ in child_evals) / len(child_evals)

        total_hours = (own_est + total_child_hours) if own_est > 0 else total_child_hours
        return round(rolled_pct, 2), total_hours

    root_tasks = [
        t
        for t in tasks
        if not (_is_valid_id(getattr(t, "id", None)) and str(getattr(t, "id", None)) in child_ids)
    ]
    if not root_tasks:
        root_tasks = list(tasks)

    root_evals = [_eval_node(rt) for rt in root_tasks]
    has_hours = any(w > 0 for _, w in root_evals)
    if has_hours:
        weighted_sum = sum(p * (w if w > 0 else 1.0) for p, w in root_evals)
        weight_denom = sum((w if w > 0 else 1.0) for _, w in root_evals)
        return round(weighted_sum / weight_denom, 1)

    return round(sum(p for p, _ in root_evals) / len(root_evals), 1)


def _compute_project_continuous_progress_pct(
    db: Session,
    project: Project,
    tasks: List[Any],
) -> float:
    """Calcula el avance físico continuo del proyecto integrando la cadena:
    Subtareas -> Actividades -> Componentes EDT -> Proyecto.
    """
    if not tasks:
        return 0.0

    # Intentar obtener componentes activos del proyecto
    components: List[Any] = []
    try:
        comp_q = db.query(ProjectComponent).filter(
            ProjectComponent.project_id == project.id,
            ProjectComponent.deleted_at.is_(None),
        )
        raw_comps = comp_q.all()
        if not isinstance(raw_comps, list):
            raw_comps = comp_q.order_by(ProjectComponent.order_index.asc()).all()
        if isinstance(raw_comps, list):
            components = [c for c in raw_comps if _is_valid_id(getattr(c, "id", None))]
    except Exception:
        components = []

    if components:
        tasks_by_comp: Dict[str, List[Any]] = {}
        unassigned_tasks: List[Any] = []
        comp_ids = {str(c.id) for c in components}
        for t in tasks:
            cid = getattr(t, "component_id", None)
            if _is_valid_id(cid) and str(cid) in comp_ids:
                tasks_by_comp.setdefault(str(cid), []).append(t)
            else:
                unassigned_tasks.append(t)

        # Solo ponderar por componentes si al menos una tarea está vinculada a un componente
        if tasks_by_comp:
            comp_entries: List[tuple[float, float, int]] = []
            for comp in components:
                c_tasks = tasks_by_comp.get(str(comp.id), [])
                c_pct = _compute_tasks_weighted_progress_pct(c_tasks) if c_tasks else 0.0
                c_bac = max(0.0, _safe_float(getattr(comp, "budget_allocated", 0.0)))
                comp_entries.append((c_pct, c_bac, len(c_tasks)))

            # Budgeted scope remains in the denominator even before tasks exist.
            total_comp_budget = sum(b for _, b, _ in comp_entries)
            if total_comp_budget > 0 and not unassigned_tasks:
                weighted_ev = sum(pct * b for pct, b, _ in comp_entries if b > 0)
                return round(weighted_ev / total_comp_budget, 1)

    return _compute_tasks_weighted_progress_pct(tasks)


def _explicit_numeric_attr(obj: Any, attr_name: str, private_name: str) -> Optional[float]:
    d = getattr(obj, "__dict__", {})
    if isinstance(d, dict):
        if private_name in d and isinstance(d[private_name], (int, float)) and not isinstance(d[private_name], bool):
            return float(d[private_name])
        if attr_name in d and isinstance(d[attr_name], (int, float)) and not isinstance(d[attr_name], bool):
            return float(d[attr_name])
    try:
        val = getattr(obj, attr_name, None)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
    except Exception:
        pass
    return None


def calculate_cpi_stability_rule(progress_pct: float, cpi: float) -> Dict[str, Any]:
    """Evalúa la Regla Empírica del 15%-20% de Estabilidad del CPI (PMI Vol. 5 §2.1).

    Una vez superado el 15% de avance físico, el CPI acumulado se estabiliza y no
    varía más de ±0.10 (10%) hasta el cierre. Si CPI < 0.90 con avance >= 15%,
    el sobrecosto es estadísticamente irrecuperable sin re-baselining formal.
    """
    prog = round(max(0.0, min(100.0, float(progress_pct))), 1)
    curr_cpi = round(float(cpi), 2)
    is_applicable = bool(prog >= 15.0)
    floor_val = round(curr_cpi * 0.90, 2)
    ceiling_val = round(curr_cpi * 1.10, 2)
    is_irrecoverable = bool(is_applicable and curr_cpi > 0.0 and curr_cpi < 0.90)

    if not is_applicable:
        msg = (
            f"Avance físico ({prog:.1f}%) por debajo del umbral empírico del 15% PMI; "
            f"el CPI actual ({curr_cpi:.2f}) aún no entra en ventana de bloqueo estadístico."
        )
    elif is_irrecoverable:
        msg = (
            f"Regla del 15% PMI activa ({prog:.1f}% de avance): Con CPI={curr_cpi:.2f} "
            f"(banda esperada [{floor_val:.2f} - {ceiling_val:.2f}]), el sobrecosto es "
            f"estadísticamente irrecuperable sin re-baselining formal o reducción de alcance."
        )
    else:
        msg = (
            f"Regla del 15% PMI activa ({prog:.1f}% de avance): El CPI ({curr_cpi:.2f}) se encuentra "
            f"en zona de estabilidad estadística con banda proyectada [{floor_val:.2f} - {ceiling_val:.2f}] al cierre."
        )

    return {
        "is_applicable": is_applicable,
        "progress_pct": prog,
        "current_cpi": curr_cpi,
        "expected_cpi_floor": floor_val,
        "expected_cpi_ceiling": ceiling_val,
        "is_irrecoverable_without_rebaseline": is_irrecoverable,
        "diagnostic_message": msg,
    }


def calculate_early_warning_sentinel(cpi: float, spi: float) -> Dict[str, Any]:
    """Clasifica el nivel de Alerta Temprana (Sentinel) en los 4 umbrales de PMI Vol. 5 §4 según min(CPI, SPI)."""
    curr_cpi = round(float(cpi), 2)
    curr_spi = round(float(spi), 2)
    min_index = round(min(curr_cpi, curr_spi), 2)
    limiting_metric = "CPI" if curr_cpi <= curr_spi else "SPI"

    if curr_cpi >= 0.95 and curr_spi >= 0.95:
        level = "normal"
        label = "Desempeño Normal"
        threshold_range = "CPI >= 0.95 y SPI >= 0.95"
        protocol_action = "Reporte ordinario semanal"
        severity_color = "success"
    elif min_index >= 0.85:
        level = "attention"
        label = "Alerta Amarilla (Atención)"
        threshold_range = "0.85 <= min(CPI, SPI) < 0.95"
        protocol_action = "Notificación al Director de Proyecto para análisis de causa raíz"
        severity_color = "warning"
    elif min_index >= 0.75:
        level = "high_risk"
        label = "Alerta Naranja (Riesgo Alto)"
        threshold_range = "0.75 <= min(CPI, SPI) < 0.85"
        protocol_action = "Convocatoria a Comité de Control de Cambios (CCB) de la Sede"
        severity_color = "warning"
    else:
        level = "critical"
        label = "Alerta Roja (Crítico)"
        threshold_range = "min(CPI, SPI) < 0.75"
        protocol_action = "Auditoría forense inmediata por la PMO Central y suspensión preventiva"
        severity_color = "destructive"

    return {
        "level": level,
        "status": level,
        "label": label,
        "min_index": min_index,
        "cpi": curr_cpi,
        "spi": curr_spi,
        "limiting_metric": limiting_metric,
        "threshold_range": threshold_range,
        "protocol_action": protocol_action,
        "action": protocol_action,
        "severity_color": severity_color,
        "requires_ccb": level in ("high_risk", "critical"),
        "requires_pmo_audit": level == "critical",
    }


def compute_project_reserves_breakdown(
    db: Session,
    project: Project,
    bac: Optional[float] = None,
) -> Dict[str, Any]:
    """Calcula la Estructura Canónica de Reservas Presupuestarias (PMI Vol. 6 §3).

    - Paquetes de Trabajo (work_packages_budget) + Reserva de Contingencia EMV (contingency_reserve)
      = Línea Base de Costos (BAC).
    - BAC + Reserva de Gestión (management_reserve, 10% por defecto para desconocidos-desconocidos)
      = Presupuesto Total del Proyecto (total_project_budget).
    """
    base_bac = round(float(bac if bac is not None else (getattr(project, "budget_allocated", 0.0) or 0.0)), 2)

    # 1. Consultar riesgos activos para cuantificar EMV (Amenazas vs Oportunidades)
    risks: List[Any] = []
    try:
        raw_risks = (
            db.query(ProjectRisk)
            .filter(
                ProjectRisk.project_id == project.id,
                ProjectRisk.deleted_at.is_(None),
            )
            .all()
        )
        if isinstance(raw_risks, list):
            risks = [r for r in raw_risks if _is_valid_id(getattr(r, "id", None))]
    except Exception:
        risks = []

    if not risks:
        rel_risks = getattr(project, "__dict__", {}).get("risks")
        if isinstance(rel_risks, list):
            risks = [r for r in rel_risks if getattr(r, "deleted_at", None) is None]

    threats_emv = 0.0
    opportunities_emv = 0.0
    active_threats_count = 0
    active_opportunities_count = 0

    for r in risks:
        r_status = str(getattr(r, "status", "active") or "active").lower()
        if r_status != "active":
            continue
        r_type = str(getattr(r, "risk_type", "threat") or "threat").strip().lower()
        r_prob_scale = max(1, min(5, int(_safe_float(getattr(r, "probability", 3), 3.0))))
        r_prob_pct = _safe_float(getattr(r, "probability_pct", None), r_prob_scale * 20.0)
        r_fin_imp = max(0.0, _safe_float(getattr(r, "financial_impact", 0.0), 0.0))
        raw_emv = (r_prob_pct / 100.0) * r_fin_imp
        r_emv = _safe_float(
            getattr(r, "emv", None),
            (-abs(raw_emv) if r_type == "opportunity" else abs(raw_emv)),
        )
        if r_type == "opportunity":
            active_opportunities_count += 1
            opportunities_emv = round(opportunities_emv - abs(r_emv), 2)
        else:
            active_threats_count += 1
            threats_emv = round(threats_emv + abs(r_emv), 2)

    net_emv = round(threats_emv + opportunities_emv, 2)

    # 2. Reserva de Contingencia (conocidos-desconocidos, forma parte del BAC)
    explicit_contingency = _explicit_numeric_attr(project, "contingency_reserve", "_contingency_reserve")
    if explicit_contingency is not None:
        contingency_reserve = round(max(0.0, explicit_contingency), 2)
    else:
        contingency_reserve = round(max(0.0, threats_emv), 2)

    # 3. Presupuesto de Paquetes de Trabajo (EDT Nivel 2 o BAC - Contingencia)
    components: List[Any] = []
    try:
        raw_comps = (
            db.query(ProjectComponent)
            .filter(
                ProjectComponent.project_id == project.id,
                ProjectComponent.deleted_at.is_(None),
            )
            .all()
        )
        if isinstance(raw_comps, list):
            components = [
                c
                for c in raw_comps
                if _is_valid_id(getattr(c, "id", None))
                and str(getattr(c, "status", "active") or "active") != "cancelled"
            ]
    except Exception:
        components = []

    if not components:
        rel_comps = getattr(project, "__dict__", {}).get("components")
        if isinstance(rel_comps, list):
            components = [
                c
                for c in rel_comps
                if getattr(c, "deleted_at", None) is None
                and str(getattr(c, "status", "active") or "active") != "cancelled"
            ]

    comp_budget_sum = round(
        sum(max(0.0, _safe_float(getattr(c, "budget_allocated", 0.0))) for c in components),
        2,
    )
    if components and comp_budget_sum > 0.0:
        work_packages_budget = comp_budget_sum
    else:
        work_packages_budget = round(max(0.0, base_bac - contingency_reserve), 2)

    effective_bac = base_bac if base_bac > 0.0 else round(work_packages_budget + contingency_reserve, 2)

    # 4. Reserva de Gestión (desconocidos-desconocidos, fuera del BAC EVM, por defecto 10% del BAC)
    explicit_mgmt_pct = _explicit_numeric_attr(project, "management_reserve_pct", "_management_reserve_pct")
    management_reserve_pct = round(max(0.0, explicit_mgmt_pct if explicit_mgmt_pct is not None else 10.0), 2)

    explicit_mgmt = _explicit_numeric_attr(project, "management_reserve", "_management_reserve")
    if explicit_mgmt is not None:
        management_reserve = round(max(0.0, explicit_mgmt), 2)
    else:
        management_reserve = round(effective_bac * (management_reserve_pct / 100.0), 2)

    total_project_budget = round(effective_bac + management_reserve, 2)

    return {
        "work_packages_budget": work_packages_budget,
        "contingency_reserve": contingency_reserve,
        "cost_baseline_bac": effective_bac,
        "bac": effective_bac,
        "management_reserve": management_reserve,
        "management_reserve_pct": management_reserve_pct,
        "total_project_budget": total_project_budget,
        "threats_emv": round(threats_emv, 2),
        "opportunities_emv": round(opportunities_emv, 2),
        "net_emv": net_emv,
        "active_threats_count": active_threats_count,
        "active_opportunities_count": active_opportunities_count,
    }


def calculate_project_evm(
    db: Session, project: Project, now: Optional[datetime] = None
) -> Dict[str, Any]:
    """Calcula las métricas canónicas de EVM para un proyecto dado."""
    now = _as_utc(now) or _utcnow()
    bac = float(project.budget_allocated or 0.0)
    reserves_info = compute_project_reserves_breakdown(db, project, bac=bac)
    if bac <= 0.0 and reserves_info["bac"] > 0.0:
        bac = float(reserves_info["bac"])

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

    # 2. Avance Físico (%) — Roll-Up Continuo Subtareas -> Actividades -> Componentes EDT -> Proyecto
    tasks = (
        db.query(ProjectTask)
        .filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        )
        .all()
    )
    total_tasks = len(tasks)

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
            progress_pct = _compute_project_continuous_progress_pct(db, project, tasks)
    else:
        progress_pct = _compute_project_continuous_progress_pct(db, project, tasks)

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

    # 10. Diagnóstico, Semáforo, Regla del 15% de Estabilidad CPI y Early Warning Sentinel
    cpi_stability_rule = calculate_cpi_stability_rule(progress_pct=progress_pct, cpi=cpi)
    early_warning_sentinel = calculate_early_warning_sentinel(cpi=cpi, spi=spi)

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

    if cpi_stability_rule["is_irrecoverable_without_rebaseline"]:
        recommendations.append(cpi_stability_rule["diagnostic_message"])
    if early_warning_sentinel["level"] != "normal":
        recommendations.append(
            f"Protocolo Sentinel ({early_warning_sentinel['label']}): {early_warning_sentinel['protocol_action']}."
        )

    # 11. Conexión con Línea Base Activa (ProjectBaseline)
    active_baseline = _get_active_baseline(db, getattr(project, "id", None))
    has_baseline = active_baseline is not None
    baseline_id: Optional[str] = None
    baseline_name: Optional[str] = None
    baseline_bac: Optional[float] = None
    baseline_progress_pct: Optional[float] = None
    baseline_variance_cost: float = 0.0
    baseline_variance_schedule: float = 0.0

    if active_baseline is not None:
        snap = active_baseline.snapshot_data or {}
        baseline_id = str(active_baseline.id)
        baseline_name = str(getattr(active_baseline, "name", "") or "Línea Base")
        raw_b_bac = snap.get("bac", snap.get("budget_allocated"))
        baseline_bac = round(_safe_float(raw_b_bac, bac), 2)
        evm_snap = snap.get("evm") if isinstance(snap.get("evm"), dict) else {}
        raw_b_prog = evm_snap.get("progress_percentage", snap.get("progress_percentage"))
        if raw_b_prog is None:
            snap_tasks = snap.get("tasks") if isinstance(snap.get("tasks"), list) else []
            if snap_tasks:
                done_snap = sum(
                    1
                    for st in snap_tasks
                    if isinstance(st, dict) and st.get("status") in ("completed", "done")
                )
                raw_b_prog = round((done_snap / len(snap_tasks)) * 100.0, 1)
            else:
                raw_b_prog = 0.0
        baseline_progress_pct = round(_safe_float(raw_b_prog, 0.0), 1)
        baseline_variance_cost = round(baseline_bac - ac, 2)
        baseline_variance_schedule = round(progress_pct - baseline_progress_pct, 1)

    return {
        "project_id": str(project.id),
        "calculated_at": now.isoformat(),
        "bac": bac,
        "work_packages_budget": reserves_info["work_packages_budget"],
        "contingency_reserve": reserves_info["contingency_reserve"],
        "management_reserve": reserves_info["management_reserve"],
        "management_reserve_pct": reserves_info["management_reserve_pct"],
        "total_project_budget": reserves_info["total_project_budget"],
        "reserves": reserves_info,
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
        "cpi_stability_rule": cpi_stability_rule,
        "early_warning_sentinel": early_warning_sentinel,
        "has_baseline": has_baseline,
        "baseline_id": baseline_id,
        "baseline_name": baseline_name,
        "baseline_bac": baseline_bac,
        "baseline_progress_pct": baseline_progress_pct,
        "baseline_variance_cost": baseline_variance_cost,
        "baseline_variance_schedule": baseline_variance_schedule,
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
    baseline_bac = current_evm.get("baseline_bac")
    ref_baseline_bac = float(baseline_bac) if baseline_bac is not None else bac

    points: List[Dict[str, Any]] = []

    for i in range(points_count):
        pt_dt = start_dt + timedelta(seconds=i * step_seconds)
        time_ratio = i / (points_count - 1)

        # 1. PV sigue típicamente una curva sigmoidea (S-curve) suave
        # Formula sigmoidea estándar normalizada: 3*t^2 - 2*t^3
        smooth_ratio = (3 * (time_ratio ** 2)) - (2 * (time_ratio ** 3))
        pv_val = round(bac * smooth_ratio, 2)
        baseline_pv_val = round(ref_baseline_bac * smooth_ratio, 2)

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
                "baseline_pv": baseline_pv_val,
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

    # Avance físico continuo ponderado por jerarquía Subtareas -> Actividades -> Componente
    physical_pct = _compute_tasks_weighted_progress_pct(tasks) if total_tasks > 0 else 0.0

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


def evaluate_earned_schedule_duration_posture(
    planned_duration_days: int | float | None,
    elapsed_days: int | float | None,
    progress_pct: int | float | None,
) -> dict[str, Any]:
    """Evalúa la postura de duración con Earned Schedule (PMBOK §6.6 / §7.4 — ES, SV(t), SPI(t)).

    Entradas normalizadas: duración planificada y dias transcurridos clampados
    a >= 0 (2 decimales), progreso clampado a [0, 100].
    - `earned_schedule_days`: ES = (progreso / 100) * duración planificada.
    - `schedule_variance_days`: SV(t) = ES - dias transcurridos.
    - `spi_time`: SPI(t) = ES / dias transcurridos (1.0 si transcurridos == 0).
    - `estimated_total_duration_days`: EDAC = duración planificada / SPI(t)
      (duración planificada si SPI(t) <= 0).
    - `posture`: 'UNSCHEDULED_DURATION' sin duración planificada;
      'COMPLETED_ON_OR_AHEAD' / 'COMPLETED_LATE' al 100% de progreso según
      dias transcurridos; 'ON_TRACK_DURATION' con SPI(t) >= 0.95;
      'AT_RISK_DURATION_SLIP' con SPI(t) >= 0.80; y
      'CRITICAL_SCHEDULE_DELAY' con SPI(t) < 0.80.
    """
    safe_planned_days = max(0.0, round(float(planned_duration_days or 0.0), 2))
    safe_elapsed_days = max(0.0, round(float(elapsed_days or 0.0), 2))
    safe_progress = max(0.0, min(100.0, round(float(progress_pct or 0.0), 2)))

    earned_schedule_days = round((safe_progress / 100.0) * safe_planned_days, 2)
    schedule_variance_days = round(earned_schedule_days - safe_elapsed_days, 2)

    if safe_elapsed_days > 0:
        spi_time = round(earned_schedule_days / safe_elapsed_days, 4)
    else:
        spi_time = 1.0

    if spi_time > 0:
        estimated_total_duration_days = round(safe_planned_days / spi_time, 2)
    else:
        estimated_total_duration_days = safe_planned_days

    if safe_planned_days == 0.0:
        posture = "UNSCHEDULED_DURATION"
    elif safe_progress >= 100.0 and safe_elapsed_days <= safe_planned_days:
        posture = "COMPLETED_ON_OR_AHEAD"
    elif safe_progress >= 100.0:
        posture = "COMPLETED_LATE"
    elif spi_time >= 0.95:
        posture = "ON_TRACK_DURATION"
    elif spi_time >= 0.80:
        posture = "AT_RISK_DURATION_SLIP"
    else:
        posture = "CRITICAL_SCHEDULE_DELAY"

    return {
        "planned_duration_days": safe_planned_days,
        "elapsed_days": safe_elapsed_days,
        "progress_pct": safe_progress,
        "earned_schedule_days": earned_schedule_days,
        "schedule_variance_days": schedule_variance_days,
        "spi_time": spi_time,
        "estimated_total_duration_days": estimated_total_duration_days,
        "posture": posture,
    }


def evaluate_remaining_investment_viability(
    bac: float,
    ac: float,
    ev: float,
    expected_benefits_npv: float,
    cpi_floor: float = 0.70,
) -> Dict[str, Any]:
    """Evalúa la viabilidad de negocio de la inversión restante (PMBOK §7.4 / §1.2.6).

    Pronostica el costo de completar (ETC = (BAC-EV)/CPI_effectiva, EAC = AC+ETC)
    y compara contra el VAN de beneficios esperado:
    - `cpi`: EV/AC (1.0 si ac==0 y ev>0; 0.0 si ambos son 0).
    - `effective_cpi`: piso de estabilidad (max(cpi, 0.01) si cpi>0, si no 1.0).
    - `etc_forecast`/`eac_forecast`: pronóstico IPA/PPC; 0.0 si ev >= bac.
    - `benefit_cost_ratio_at_completion`: VAN / EAC.
    - `incremental_benefit_to_etc_ratio`: VAN / ETC (999.0 señal infinita solo
      si hay EV y no queda inversión; 0.0 si no hay beneficios).
    - `viability_posture`: 'NO_INVESTMENT_BASELINE' sin baseline ni beneficios;
      'TERMINATION_OR_RESTRUCTURE_REVIEW' con ratio incremental < 1.0;
      'NEGATIVE_NET_BENEFIT_AT_COMPLETION' con BCR < 1.0;
      'MARGINAL_INVESTMENT_EFFICIENCY' con BCR >= 1.0 pero CPI bajo el piso; y
      'VIABLE_BUSINESS_CASE' en el caso viable.
    - `recommendations`: decisiones de gobernanza según el hallazgo.
    """
    safe_bac = float(bac or 0.0)
    safe_ac = float(ac or 0.0)
    safe_ev = float(ev or 0.0)
    safe_npv = float(expected_benefits_npv or 0.0)
    safe_cpi_floor = float(cpi_floor or 0.70)

    if safe_ac > 0:
        cpi = round(safe_ev / safe_ac, 4)
    else:
        cpi = 1.0 if safe_ev > 0 else 0.0

    effective_cpi = max(cpi, 0.01) if cpi > 0 else 1.0

    if safe_bac > safe_ev:
        etc_forecast = round(max(0.0, safe_bac - safe_ev) / effective_cpi, 2)
    else:
        etc_forecast = 0.0
    eac_forecast = round(safe_ac + etc_forecast, 2)

    benefit_cost_ratio_at_completion = (
        round(safe_npv / eac_forecast, 4)
        if eac_forecast > 0
        else 0.0
    )
    if etc_forecast > 0:
        incremental_benefit_to_etc_ratio = round(safe_npv / etc_forecast, 4)
    else:
        incremental_benefit_to_etc_ratio = 999.0 if safe_npv > 0 else 0.0

    if safe_bac <= 0 and safe_npv <= 0:
        viability_posture = "NO_INVESTMENT_BASELINE"
    elif incremental_benefit_to_etc_ratio < 1.0:
        viability_posture = "TERMINATION_OR_RESTRUCTURE_REVIEW"
    elif benefit_cost_ratio_at_completion < 1.0:
        viability_posture = "NEGATIVE_NET_BENEFIT_AT_COMPLETION"
    elif benefit_cost_ratio_at_completion >= 1.0 and 0 < cpi < safe_cpi_floor:
        viability_posture = "MARGINAL_INVESTMENT_EFFICIENCY"
    else:
        viability_posture = "VIABLE_BUSINESS_CASE"

    recommendations: list[str] = []
    if viability_posture == "NO_INVESTMENT_BASELINE":
        recommendations.append(
            "Definir el BAC y el VAN de beneficios esperado para poder pronosticar la inversión restante (PMBOK §7.4)."
        )
    elif viability_posture == "TERMINATION_OR_RESTRUCTURE_REVIEW":
        recommendations.append(
            "Convocar revisión de negocio: los beneficios esperados no cubren la inversión remanente; evaluar terminación o reestructuración (PMBOK §1.2.6)."
        )
    elif viability_posture == "NEGATIVE_NET_BENEFIT_AT_COMPLETION":
        recommendations.append(
            "El VAN esperado es inferior al EAC pronosticado: renegociar alcance o beneficios antes de liberar la inversión restante."
        )
    elif viability_posture == "MARGINAL_INVESTMENT_EFFICIENCY":
        recommendations.append(
            "La eficiencia de costo opera bajo el piso de estabilidad: plan de recuperación de CPI y control de compras antes de comprometer los fondos finales."
        )
    else:
        recommendations.append(
            "Caso de negocio viable: liberar la inversión remanente por tramos verificando el CPI y el VAN en cada gate."
        )

    return {
        "bac": safe_bac,
        "ac": safe_ac,
        "ev": safe_ev,
        "expected_benefits_npv": safe_npv,
        "cpi": cpi,
        "effective_cpi": effective_cpi,
        "etc_forecast": etc_forecast,
        "eac_forecast": eac_forecast,
        "benefit_cost_ratio_at_completion": benefit_cost_ratio_at_completion,
        "incremental_benefit_to_etc_ratio": incremental_benefit_to_etc_ratio,
        "viability_posture": viability_posture,
        "recommendations": recommendations,
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
    std_evm = calculate_project_evm(db, project, now=now)
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
        "reserves": std_evm.get("reserves") or compute_project_reserves_breakdown(db, project, bac=bac),
        "cpi_stability_rule": std_evm.get("cpi_stability_rule") or calculate_cpi_stability_rule(physical_pct, cpi),
        "early_warning_sentinel": std_evm.get("early_warning_sentinel") or calculate_early_warning_sentinel(cpi, spi),
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
            "description": task.description,
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
            "description": comp.description,
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
            "description": None,
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
        "description": project.description,
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


# ============================================================================
# Fase 5: 3 Frentes de Ejecución + 6 Familias de Indicadores Pro + Tributación
# ============================================================================

EXECUTION_SOURCES_CATALOG: List[Dict[str, Any]] = [
    {
        "source_type": "manual",
        "code": "MAN-00",
        "label": "Captura Manual (Tradicional)",
        "frente": "manual",
        "unit": "unidades",
        "default_target": 100.0,
        "recommended_level": "PRODUCTO_PRINCIPAL",
        "supports_component": False,
        "description": "El valor actual se registra manualmente mediante avances periódicos.",
    },
    {
        "source_type": "pro_edt_progress",
        "code": "PRO-01",
        "label": "Familia Pro 1: Avance Físico Ponderado (EDT / Proyecto)",
        "frente": "tiempo",
        "unit": "%",
        "default_target": 100.0,
        "recommended_level": "COMPONENTE_EDT",
        "supports_component": True,
        "description": "Tributación continua Subtareas -> Actividades -> Componente EDT -> Proyecto ponderada por horas y presupuesto.",
    },
    {
        "source_type": "pro_hours_efficiency",
        "code": "PRO-02",
        "label": "Familia Pro 2: Eficiencia de Esfuerzo y Horas",
        "frente": "tiempo",
        "unit": "%",
        "default_target": 100.0,
        "recommended_level": "ACTIVIDAD_CRITICA",
        "supports_component": True,
        "description": "Relación entre las horas ganadas por avance físico y las horas reales registradas en bitácora.",
    },
    {
        "source_type": "pro_cost_efficiency",
        "code": "PRO-03",
        "label": "Familia Pro 3: Costo-Eficiencia Presupuestal (CPI)",
        "frente": "cruce_evm",
        "unit": "índice",
        "default_target": 1.0,
        "recommended_level": "FINANCIERO_EVM",
        "supports_component": True,
        "description": "Índice de Desempeño del Costo (CPI = EV / AC) cruzando valor ganado físico contra gasto aprobado/pagado.",
    },
    {
        "source_type": "pro_milestones_ontime",
        "code": "PRO-04",
        "label": "Familia Pro 4: Cumplimiento de Hitos a Tiempo",
        "frente": "tiempo",
        "unit": "%",
        "default_target": 100.0,
        "recommended_level": "PRODUCTO_PRINCIPAL",
        "supports_component": False,
        "description": "Porcentaje de hitos contractuales o ministeriales completados dentro de su fecha objetivo.",
    },
    {
        "source_type": "pro_raid_mitigated",
        "code": "PRO-05",
        "label": "Familia Pro 5: Mitigación de Riesgos RAID",
        "frente": "tiempo",
        "unit": "%",
        "default_target": 100.0,
        "recommended_level": "IMPACTO_MINISTERIAL",
        "supports_component": False,
        "description": "Porcentaje de riesgos del proyecto con estado mitigado/cerrado o con plan de mitigación activo.",
    },
    {
        "source_type": "pro_global_health",
        "code": "PRO-06",
        "label": "Familia Pro 6: Salud Global Compuesta (Razón Crítica CR)",
        "frente": "cruce_evm",
        "unit": "índice",
        "default_target": 1.0,
        "recommended_level": "IMPACTO_MINISTERIAL",
        "supports_component": True,
        "description": "Razón Crítica PMI (CR = CPI × SPI) que integra desempeño cronológico y eficiencia financiera.",
    },
    {
        "source_type": "frente_tiempo_spi",
        "code": "FRT-SPI",
        "label": "Frente Tiempo: Índice de Cronograma (SPI)",
        "frente": "tiempo",
        "unit": "índice",
        "default_target": 1.0,
        "recommended_level": "ACTIVIDAD_CRITICA",
        "supports_component": True,
        "description": "Índice de Desempeño del Cronograma (SPI = EV / PV) del proyecto o componente EDT.",
    },
    {
        "source_type": "frente_financiero_execution_pct",
        "code": "FRF-EXEC",
        "label": "Frente Financiero: % Ejecución Presupuestal (AC / BAC)",
        "frente": "financiero",
        "unit": "%",
        "default_target": 100.0,
        "recommended_level": "FINANCIERO_EVM",
        "supports_component": True,
        "description": "Porcentaje del presupuesto aprobado (BAC) ejecutado en gastos reales (AC).",
    },
    {
        "source_type": "frente_financiero_rule_100",
        "code": "FRF-R100",
        "label": "Frente Financiero: Cobertura Regla del 100% EDT",
        "frente": "financiero",
        "unit": "%",
        "default_target": 100.0,
        "recommended_level": "FINANCIERO_EVM",
        "supports_component": False,
        "description": "Porcentaje del presupuesto global del proyecto distribuido en componentes de la EDT.",
    },
    {
        "source_type": "frente_cruce_ev",
        "code": "FRC-EV",
        "label": "Frente Cruce EVM: Valor Ganado Monetizado (EV)",
        "frente": "cruce_evm",
        "unit": "USD",
        "default_target": 0.0,
        "recommended_level": "FINANCIERO_EVM",
        "supports_component": True,
        "description": "Valor monetario del trabajo físico realmente completado (EV = BAC × % Avance).",
    },
]


def build_project_execution_matrix(
    db: Session, project: Project, now: Optional[datetime] = None
) -> Dict[str, Any]:
    """Construye la Matriz Integral de Ejecución en 3 Frentes + Tributación Jerárquica + 6 Familias Pro.

    1. Frente Tiempo: SPI, SPI(t), SV, horas estimadas/reales, eficiencia de horas, hitos a tiempo.
    2. Frente Financiero: BAC, AC, comprometido, planificado, % ejecución, Regla del 100% EDT.
    3. Frente Cruce (Tiempo × Financiero): EV, PV, CPI, SPI, CR, CV, SV, EAC, VAC, TCPI, Brecha.
    4. Matriz de Tributación: Subtareas -> Actividades -> Componentes EDT -> Proyecto.
    5. 6 Familias de Indicadores Pro evaluadas en tiempo real.
    """
    now = _as_utc(now) or _utcnow()
    adv_evm = calculate_project_evm_advanced(db, project, now=now)
    std_evm = adv_evm["standard_evm"]
    es_metrics = adv_evm["earned_schedule"]
    tcpi_metrics = adv_evm["tcpi"]
    budget_rule = validate_project_budget_100_rule(db, project)

    # Tareas activas
    raw_tasks = (
        db.query(ProjectTask)
        .filter(ProjectTask.project_id == project.id, ProjectTask.deleted_at.is_(None))
        .all()
    )
    all_tasks = raw_tasks if isinstance(raw_tasks, list) else []

    # Logs de tiempo
    raw_logs = (
        db.query(ProjectTimeLog)
        .filter(ProjectTimeLog.project_id == project.id, ProjectTimeLog.deleted_at.is_(None))
        .all()
    )
    all_logs = raw_logs if isinstance(raw_logs, list) else []

    # Gastos (todos los estados para desglose financiero)
    raw_expenses = (
        db.query(ProjectExpense)
        .filter(ProjectExpense.project_id == project.id, ProjectExpense.deleted_at.is_(None))
        .all()
    )
    all_expenses = raw_expenses if isinstance(raw_expenses, list) else []

    # Hitos
    raw_milestones = (
        db.query(ProjectMilestone)
        .filter(ProjectMilestone.project_id == project.id, ProjectMilestone.deleted_at.is_(None))
        .all()
    )
    all_milestones = raw_milestones if isinstance(raw_milestones, list) else []

    # Riesgos RAID
    try:
        raw_risks = (
            db.query(ProjectRisk)
            .filter(ProjectRisk.project_id == project.id, ProjectRisk.deleted_at.is_(None))
            .all()
        )
        all_risks = raw_risks if isinstance(raw_risks, list) else []
    except Exception:
        all_risks = []

    # Componentes EDT
    try:
        comp_q = db.query(ProjectComponent).filter(
            ProjectComponent.project_id == project.id,
            ProjectComponent.deleted_at.is_(None),
        )
        raw_comps = comp_q.order_by(ProjectComponent.order_index.asc()).all()
        if not isinstance(raw_comps, list):
            raw_comps = comp_q.all()
        components = [c for c in raw_comps if _is_valid_id(getattr(c, "id", None))] if isinstance(raw_comps, list) else []
    except Exception:
        components = []

    # Jerarquía de tareas: separar actividades raíz y subtareas
    task_map: Dict[str, Any] = {
        str(t.id): t for t in all_tasks if _is_valid_id(getattr(t, "id", None))
    }
    children_by_parent: Dict[str, List[Any]] = {}
    subtasks_count = 0
    for t in all_tasks:
        pid = getattr(t, "parent_id", None)
        tid = getattr(t, "id", None)
        if _is_valid_id(pid) and str(pid) in task_map and (not _is_valid_id(tid) or str(tid) != str(pid)):
            children_by_parent.setdefault(str(pid), []).append(t)
            subtasks_count += 1

    activities_count = max(0, len(all_tasks) - subtasks_count)
    completed_tasks_count = sum(1 for t in all_tasks if getattr(t, "status", None) in ("completed", "done"))
    overdue_tasks_count = sum(
        1
        for t in all_tasks
        if getattr(t, "status", None) not in ("completed", "done")
        and _as_utc(getattr(t, "due_date", None)) is not None
        and _as_utc(getattr(t, "due_date", None)) < now
    )

    # Horas por tarea
    hours_by_task: Dict[str, float] = {}
    total_actual_hours = 0.0
    for tl in all_logs:
        h = max(0.0, _safe_float(getattr(tl, "hours", 0.0)))
        total_actual_hours += h
        tid = getattr(tl, "task_id", None)
        if _is_valid_id(tid):
            hours_by_task[str(tid)] = hours_by_task.get(str(tid), 0.0) + h
    total_actual_hours = round(total_actual_hours, 2)

    # Esfuerzo estimado total (evitando doble conteo entre padre e hijas cuando el padre no suma sus hijas)
    def _calc_subtree_hours(t: Any, visited_ids: set[str]) -> tuple[float, float]:
        tid_raw = getattr(t, "id", None)
        tid = str(tid_raw) if _is_valid_id(tid_raw) else None
        if tid and tid in visited_ids:
            return 0.0, 0.0
        if tid:
            visited_ids.add(tid)
        own_est = max(0.0, _safe_float(getattr(t, "estimated_hours", 0.0)))
        own_act = hours_by_task.get(tid, 0.0) if tid else 0.0
        ch_list = children_by_parent.get(tid, []) if tid else []
        ch_est_sum = 0.0
        ch_act_sum = 0.0
        for ch in ch_list:
            ce, ca = _calc_subtree_hours(ch, visited_ids)
            ch_est_sum += ce
            ch_act_sum += ca
        tot_est = (own_est + ch_est_sum) if own_est > 0 else ch_est_sum
        tot_act = own_act + ch_act_sum
        return round(tot_est, 2), round(tot_act, 2)

    root_tasks_all = [
        t
        for t in all_tasks
        if not (_is_valid_id(getattr(t, "parent_id", None)) and str(getattr(t, "parent_id", None)) in task_map)
    ]
    visited_global: set[str] = set()
    total_estimated_hours = 0.0
    for rt in root_tasks_all:
        re, _ = _calc_subtree_hours(rt, visited_global)
        total_estimated_hours += re
    total_estimated_hours = round(total_estimated_hours, 2)

    progress_pct = float(std_evm["progress_percentage"])
    earned_hours = round(total_estimated_hours * (progress_pct / 100.0), 2)
    if total_estimated_hours > 0 and total_actual_hours > 0:
        hours_efficiency_pct = round(min(150.0, (earned_hours / total_actual_hours) * 100.0), 1)
        hours_utilization_pct = round((total_actual_hours / total_estimated_hours) * 100.0, 1)
    elif total_estimated_hours > 0 and total_actual_hours == 0:
        hours_efficiency_pct = round(progress_pct, 1) if progress_pct > 0 else 100.0
        hours_utilization_pct = 0.0
    else:
        hours_efficiency_pct = round(progress_pct, 1)
        hours_utilization_pct = 0.0

    # Hitos a tiempo
    milestones_total = len(all_milestones)
    milestones_completed = 0
    milestones_on_time = 0
    for m in all_milestones:
        is_comp = bool(getattr(m, "is_completed", False))
        due_dt = _as_utc(getattr(m, "due_date", None) or getattr(m, "target_date", None))
        comp_dt = _as_utc(getattr(m, "completed_at", None))
        if is_comp:
            milestones_completed += 1
            if not due_dt or not comp_dt or comp_dt <= due_dt:
                milestones_on_time += 1
    if milestones_total > 0:
        milestones_on_time_pct = round((milestones_on_time / milestones_total) * 100.0, 1)
    else:
        milestones_on_time_pct = round(progress_pct, 1)

    # Riesgos RAID mitigados
    risks_total = len(all_risks)
    risks_mitigated = 0
    risks_active = 0
    risks_occurred = 0
    for r in all_risks:
        r_status = str(getattr(r, "status", "") or "").lower()
        has_plan = bool(str(getattr(r, "mitigation_plan", "") or "").strip())
        if r_status in ("mitigated", "closed", "resolved") or has_plan:
            risks_mitigated += 1
        elif r_status == "occurred":
            risks_occurred += 1
        else:
            risks_active += 1
    risks_mitigated_pct = round((risks_mitigated / risks_total) * 100.0, 1) if risks_total > 0 else 100.0

    # Desglose de gastos financieros
    committed_cost = round(
        sum(_safe_float(getattr(e, "amount", 0.0)) for e in all_expenses if getattr(e, "status", None) == "committed"),
        2,
    )
    planned_cost = round(
        sum(_safe_float(getattr(e, "amount", 0.0)) for e in all_expenses if getattr(e, "status", None) == "planned"),
        2,
    )

    # Tributación por Componente EDT
    bac = float(std_evm["bac"])
    comp_ids_set = {str(c.id) for c in components}
    tasks_by_comp: Dict[Optional[str], List[Any]] = {}
    for t in all_tasks:
        cid = getattr(t, "component_id", None)
        key = str(cid) if (_is_valid_id(cid) and str(cid) in comp_ids_set) else None
        tasks_by_comp.setdefault(key, []).append(t)

    component_rollups: List[Dict[str, Any]] = []
    total_comp_budget = sum(max(0.0, _safe_float(getattr(c, "budget_allocated", 0.0))) for c in components)

    for comp in components:
        cid_str = str(comp.id)
        comp_evm = calculate_component_evm(db, comp, now=now)
        c_tasks = tasks_by_comp.get(cid_str, [])
        c_root_tasks = [
            t
            for t in c_tasks
            if not (_is_valid_id(getattr(t, "parent_id", None)) and str(getattr(t, "parent_id", None)) in task_map)
        ]
        c_visited: set[str] = set()
        c_est_hours = 0.0
        c_act_hours = 0.0
        c_subtasks_count = 0
        activities_summary: List[Dict[str, Any]] = []
        for rt in c_root_tasks:
            re, ra = _calc_subtree_hours(rt, c_visited)
            c_est_hours += re
            c_act_hours += ra
            rt_id = str(rt.id) if _is_valid_id(getattr(rt, "id", None)) else ""
            rt_children = children_by_parent.get(rt_id, []) if rt_id else []
            c_subtasks_count += len(rt_children)
            rt_pct = _compute_tasks_weighted_progress_pct([rt] + rt_children)
            activities_summary.append(
                {
                    "id": rt_id,
                    "title": getattr(rt, "title", "Actividad"),
                    "status": getattr(rt, "status", "pending"),
                    "progress_pct": rt_pct,
                    "estimated_hours": round(re, 2),
                    "actual_hours": round(ra, 2),
                    "subtasks_count": len(rt_children),
                }
            )

        c_bac = float(comp_evm["budget_allocated"])
        weight_pct = (
            round((c_bac / bac) * 100.0, 1)
            if bac > 0
            else (round((c_bac / total_comp_budget) * 100.0, 1) if total_comp_budget > 0 else round(100.0 / max(len(components), 1), 1))
        )
        if c_est_hours > 0 and c_act_hours > 0:
            c_earned_h = c_est_hours * (float(comp_evm["physical_progress_pct"]) / 100.0)
            c_hours_eff = round(min(150.0, (c_earned_h / c_act_hours) * 100.0), 1)
        else:
            c_hours_eff = float(comp_evm["physical_progress_pct"])

        component_rollups.append(
            {
                "component_id": cid_str,
                "code": getattr(comp, "code", None) or "EDT",
                "name": getattr(comp, "name", "Componente EDT"),
                "budget_allocated": c_bac,
                "weight_pct": weight_pct,
                "budget_weight_pct": weight_pct,
                "physical_progress_pct": float(comp_evm["physical_progress_pct"]),
                "financial_progress_pct": float(comp_evm["financial_progress_pct"]),
                "balance_gap_pct": float(comp_evm["balance_gap_pct"]),
                "ev": float(comp_evm["ev"]),
                "pv": float(comp_evm["pv"]),
                "ac": float(comp_evm["ac"]),
                "cpi": float(comp_evm["cpi"]),
                "spi": float(comp_evm["spi"]),
                "cr": float(comp_evm["cr"]),
                "tasks_count": int(comp_evm["total_tasks"]),
                "completed_tasks": int(comp_evm["completed_tasks"]),
                "activities_count": len(c_root_tasks),
                "subtasks_count": c_subtasks_count,
                "estimated_hours": round(c_est_hours, 2),
                "actual_hours": round(c_act_hours, 2),
                "hours_efficiency_pct": c_hours_eff,
                "health_status": comp_evm["health_status"],
                "health_color": comp_evm["health_color"],
                "activities": activities_summary,
            }
        )

    unassigned_tasks = tasks_by_comp.get(None, [])
    unassigned_pct = _compute_tasks_weighted_progress_pct(unassigned_tasks) if unassigned_tasks else 0.0

    if getattr(project, "progress_mode", "auto_tasks") == "manual":
        rollup_method = "manual"
    elif getattr(project, "progress_mode", "auto_tasks") == "milestones" and milestones_total > 0:
        rollup_method = "milestones"
    elif components and total_comp_budget > 0 and not unassigned_tasks:
        rollup_method = "components_budget_weighted"
    else:
        rollup_method = "tasks_hours_weighted"

    frente_tiempo = {
        "time_progress_pct": progress_pct,
        "progress_pct": progress_pct,
        "spi": float(std_evm["spi"]),
        "spi_t": float(es_metrics["schedule_performance_index_time"]),
        "sv": float(std_evm["sv"]),
        "planned_duration_days": float(es_metrics["planned_duration_days"]),
        "actual_time_days": float(es_metrics["actual_time_days"]),
        "earned_schedule_days": float(es_metrics["earned_schedule_days"]),
        "total_estimated_hours": total_estimated_hours,
        "estimated_hours": total_estimated_hours,
        "actual_hours": total_actual_hours,
        "earned_hours": earned_hours,
        "hours_efficiency_pct": hours_efficiency_pct,
        "hours_utilization_pct": hours_utilization_pct,
        "milestones_total": milestones_total,
        "milestones_completed": milestones_completed,
        "milestones_on_time": milestones_on_time,
        "milestones_ontime": milestones_on_time,
        "milestones_on_time_pct": milestones_on_time_pct,
        "milestones_ontime_pct": milestones_on_time_pct,
        "tasks_total": len(all_tasks),
        "tasks_completed": completed_tasks_count,
        "tasks_overdue": overdue_tasks_count,
        "activities_count": activities_count,
        "subtasks_count": subtasks_count,
    }

    available_budget = round(max(0.0, bac - float(std_evm["ac"]) - committed_cost), 2)
    fin_exec_pct = float(std_evm["financial_percentage"])
    frente_financiero = {
        "cpi": float(std_evm["cpi"]),
        "cv": float(std_evm["cv"]),
        "bac": bac,
        "ac": float(std_evm["ac"]),
        "committed_cost": committed_cost,
        "planned_cost": planned_cost,
        "available_budget": available_budget,
        "remaining_budget": available_budget,
        "financial_execution_pct": fin_exec_pct,
        "burn_rate_pct": fin_exec_pct,
        "financial_progress_pct": fin_exec_pct,
        "expenses_count": len(all_expenses),
        "budget_100_rule": {
            "is_satisfied": bool(budget_rule["is_rule_satisfied"]),
            "is_fully_allocated": bool(budget_rule["is_fully_allocated"]),
            "allocation_percentage": float(budget_rule["allocation_percentage"]),
            "components_budget_total": float(budget_rule["components_budget_total"]),
            "budget_difference": float(budget_rule["budget_difference"]),
            "status": str(budget_rule["status"]),
        },
    }

    balance_gap_pct = round(progress_pct - fin_exec_pct, 1)
    frente_cruce_evm = {
        "ev": float(std_evm["ev"]),
        "pv": float(std_evm["pv"]),
        "ac": float(std_evm["ac"]),
        "bac": bac,
        "cpi": float(std_evm["cpi"]),
        "spi": float(std_evm["spi"]),
        "cr": float(std_evm["cr"]),
        "cv": float(std_evm["cv"]),
        "sv": float(std_evm["sv"]),
        "eac": float(std_evm["eac"]),
        "vac": float(std_evm["vac"]),
        "tcpi_bac": float(tcpi_metrics["tcpi_bac"]) if tcpi_metrics.get("tcpi_bac") is not None else 1.0,
        "balance_gap_pct": balance_gap_pct,
        "health_status": str(std_evm["health_status"]),
        "health_color": str(std_evm["health_color"]),
        "quadrant_name": str(adv_evm["quadrant"]["name"]),
    }

    rollup_hierarchy = {
        "project_progress_pct": progress_pct,
        "overall_progress_pct": progress_pct,
        "rollup_method": rollup_method,
        "subtasks_count": subtasks_count,
        "activities_count": activities_count,
        "components_count": len(component_rollups),
        "components": component_rollups,
        "unassigned_tasks_count": len(unassigned_tasks),
        "unassigned_activities_count": len(unassigned_tasks),
        "unassigned_progress_pct": unassigned_pct,
    }

    pro_families = [
        {
            "family_key": "pro_edt_progress",
            "code": "PRO-01",
            "name": "Avance Físico Ponderado (EDT -> Proyecto)",
            "title": "Avance Físico Ponderado (EDT -> Proyecto)",
            "frente": "tiempo",
            "level": "COMPONENTE_EDT",
            "unit": "%",
            "target_value": 100.0,
            "current_value": progress_pct,
            "spi": round(progress_pct / 100.0, 4),
            "status_color": "success" if progress_pct >= 80.0 else ("warning" if progress_pct >= 40.0 else "destructive"),
            "formula": "Σ(Avance Subtareas × Horas) -> Actividades -> Componentes EDT -> Proyecto",
        },
        {
            "family_key": "pro_hours_efficiency",
            "code": "PRO-02",
            "name": "Eficiencia de Esfuerzo y Horas",
            "title": "Eficiencia de Esfuerzo y Horas",
            "frente": "tiempo",
            "level": "ACTIVIDAD_CRITICA",
            "unit": "%",
            "target_value": 100.0,
            "current_value": hours_efficiency_pct,
            "spi": round(hours_efficiency_pct / 100.0, 4),
            "status_color": "success" if hours_efficiency_pct >= 90.0 else ("warning" if hours_efficiency_pct >= 70.0 else "destructive"),
            "formula": "(Horas Estimadas × % Avance) / Horas Reales Registradas",
        },
        {
            "family_key": "pro_cost_efficiency",
            "code": "PRO-03",
            "name": "Costo-Eficiencia Presupuestal (CPI)",
            "title": "Costo-Eficiencia Presupuestal (CPI)",
            "frente": "cruce_evm",
            "level": "FINANCIERO_EVM",
            "unit": "índice",
            "target_value": 1.0,
            "current_value": float(std_evm["cpi"]),
            "spi": round(float(std_evm["cpi"]), 4),
            "status_color": "success" if float(std_evm["cpi"]) >= 1.0 else ("warning" if float(std_evm["cpi"]) >= 0.85 else "destructive"),
            "formula": "CPI = Valor Ganado (EV) / Costo Real Ejecutado (AC)",
        },
        {
            "family_key": "pro_milestones_ontime",
            "code": "PRO-04",
            "name": "Cumplimiento de Hitos a Tiempo",
            "title": "Cumplimiento de Hitos a Tiempo",
            "frente": "tiempo",
            "level": "PRODUCTO_PRINCIPAL",
            "unit": "%",
            "target_value": 100.0,
            "current_value": milestones_on_time_pct,
            "spi": round(milestones_on_time_pct / 100.0, 4),
            "status_color": "success" if milestones_on_time_pct >= 85.0 else ("warning" if milestones_on_time_pct >= 60.0 else "destructive"),
            "formula": "Hitos Completados en Fecha / Total Hitos Planificados × 100",
        },
        {
            "family_key": "pro_raid_mitigated",
            "code": "PRO-05",
            "name": "Mitigación de Riesgos RAID",
            "title": "Mitigación de Riesgos RAID",
            "frente": "tiempo",
            "level": "IMPACTO_MINISTERIAL",
            "unit": "%",
            "target_value": 100.0,
            "current_value": risks_mitigated_pct,
            "spi": round(risks_mitigated_pct / 100.0, 4),
            "status_color": "success" if risks_mitigated_pct >= 85.0 else ("warning" if risks_mitigated_pct >= 60.0 else "destructive"),
            "formula": "Riesgos Mitigados o con Plan Activo / Total Riesgos RAID × 100",
        },
        {
            "family_key": "pro_global_health",
            "code": "PRO-06",
            "name": "Salud Global Compuesta (Razón Crítica CR)",
            "title": "Salud Global Compuesta (Razón Crítica CR)",
            "frente": "cruce_evm",
            "level": "IMPACTO_MINISTERIAL",
            "unit": "índice",
            "target_value": 1.0,
            "current_value": float(std_evm["cr"]),
            "spi": round(float(std_evm["cr"]), 4),
            "status_color": "success" if float(std_evm["cr"]) >= 1.0 else ("warning" if float(std_evm["cr"]) >= 0.80 else "destructive"),
            "formula": "CR = CPI (Eficiencia Costo) × SPI (Eficiencia Tiempo)",
        },
    ]

    familias_pro_map = {f["family_key"]: f for f in pro_families}
    sources_catalog_map = {
        s["source_type"]: {
            "label": s["label"],
            "frente": s["frente"],
            "unit": s["unit"],
            "default_target": s["default_target"],
            "category": s.get("recommended_level", "operational"),
        }
        for s in EXECUTION_SOURCES_CATALOG
    }

    return {
        "project_id": str(project.id),
        "calculated_at": now.isoformat(),
        "frentes": {
            "tiempo": frente_tiempo,
            "financiero": frente_financiero,
            "cruce_evm": frente_cruce_evm,
        },
        "frente_tiempo": frente_tiempo,
        "frente_financiero": frente_financiero,
        "frente_cruce_evm": frente_cruce_evm,
        "rollup_hierarchy": rollup_hierarchy,
        "familias_pro": familias_pro_map,
        "pro_families": pro_families,
        "raid_summary": {
            "total_risks": risks_total,
            "mitigated_risks": risks_mitigated,
            "active_risks": risks_active,
            "occurred_risks": risks_occurred,
            "mitigated_pct": risks_mitigated_pct,
        },
        "sources_catalog": sources_catalog_map,
        "available_sources": EXECUTION_SOURCES_CATALOG,
    }


def evaluate_execution_metric(
    db: Session,
    project: Project,
    source_type: Optional[str],
    component_id: Optional[Any] = None,
    target_value: Optional[float] = None,
    matrix: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evalúa el valor actual, meta sugerida y SPI de un KPI o Indicador conectado a la ejecución real."""
    src = str(source_type or "manual").strip()
    if src == "manual":
        return {
            "is_auto": False,
            "source_type": "manual",
            "frente": "manual",
            "current_value": None,
            "suggested_target": target_value,
            "spi": None,
            "unit": None,
            "component_name": None,
        }

    exec_matrix = matrix or build_project_execution_matrix(db, project)
    comp_id_str = str(component_id).strip() if _is_valid_id(component_id) else None
    comp_data: Optional[Dict[str, Any]] = None
    if comp_id_str:
        for c in exec_matrix.get("rollup_hierarchy", {}).get("components", []):
            if str(c.get("component_id")) == comp_id_str:
                comp_data = c
                break

    # G6: un vínculo hacia un componente EDT eliminado/inexistente es huérfano.
    # Solo los componentes activos de la matriz participan en la evaluación.
    is_orphaned = comp_id_str is not None and comp_data is None

    ft = exec_matrix["frente_tiempo"]
    ff = exec_matrix["frente_financiero"]
    fc = exec_matrix["frente_cruce_evm"]

    current_val = 0.0
    default_target = 100.0
    unit = "%"
    frente = "tiempo"

    if src in ("pro_edt_progress", "tasks_completion_pct"):
        current_val = float(comp_data["physical_progress_pct"]) if comp_data else float(ft["time_progress_pct"])
        default_target = 100.0
        unit = "%"
        frente = "tiempo"
    elif src == "pro_hours_efficiency":
        current_val = float(comp_data["hours_efficiency_pct"]) if comp_data else float(ft["hours_efficiency_pct"])
        default_target = 100.0
        unit = "%"
        frente = "tiempo"
    elif src == "hours_logged":
        current_val = float(comp_data["actual_hours"]) if comp_data else float(ft["actual_hours"])
        default_target = max(1.0, float(comp_data["estimated_hours"]) if comp_data else float(ft["total_estimated_hours"]))
        unit = "h"
        frente = "tiempo"
    elif src in ("pro_cost_efficiency", "evm_cpi"):
        current_val = float(comp_data["cpi"]) if comp_data else float(fc["cpi"])
        default_target = 1.0
        unit = "índice"
        frente = "financiero" if src == "evm_cpi" else "cruce_evm"
    elif src == "pro_milestones_ontime":
        current_val = float(ft["milestones_on_time_pct"])
        default_target = 100.0
        unit = "%"
        frente = "tiempo"
    elif src == "pro_raid_mitigated":
        raid_fam = next(
            (f for f in exec_matrix.get("pro_families", []) if f["family_key"] == "pro_raid_mitigated"),
            None,
        )
        current_val = float(raid_fam["current_value"]) if raid_fam else 100.0
        default_target = 100.0
        unit = "%"
        frente = "tiempo"
    elif src in ("pro_global_health", "evm_cr"):
        current_val = float(comp_data["cr"]) if comp_data else float(fc["cr"])
        default_target = 1.0
        unit = "índice"
        frente = "cruce_evm"
    elif src in ("frente_tiempo_spi", "evm_spi"):
        current_val = float(comp_data["spi"]) if comp_data else float(ft["spi"])
        default_target = 1.0
        unit = "índice"
        frente = "tiempo"
    elif src in ("frente_financiero_execution_pct", "budget_burn_pct"):
        current_val = (
            float(comp_data["financial_progress_pct"]) if comp_data else float(ff["financial_execution_pct"])
        )
        default_target = 100.0
        unit = "%"
        frente = "financiero"
    elif src == "frente_financiero_rule_100":
        current_val = float(ff["budget_100_rule"]["allocation_percentage"])
        default_target = 100.0
        unit = "%"
        frente = "financiero"
    elif src == "frente_cruce_ev":
        current_val = float(comp_data["ev"]) if comp_data else float(fc["ev"])
        default_target = float(comp_data["budget_allocated"]) if comp_data else float(fc["bac"])
        unit = "USD"
        frente = "cruce_evm"
    else:
        current_val = float(ft["time_progress_pct"])
        default_target = 100.0
        unit = "%"
        frente = "tiempo"

    eff_target = float(target_value) if (target_value is not None and float(target_value) > 0) else default_target
    spi = round(current_val / eff_target, 4) if eff_target > 0 else 1.0

    comp_label: Optional[str] = None
    if comp_data:
        c_code = comp_data.get("code")
        c_name = comp_data.get("name")
        comp_label = f"[{c_code}] {c_name}" if c_code and c_name else (c_name or c_code)

    orphan_reason = "component_not_present_in_active_edt" if is_orphaned else None
    return {
        "is_auto": True,
        "source_type": src,
        "frente": frente,
        # G6: el valor de un componente muerto no se sustituye silenciosamente
        # por el global del proyecto; se devuelve None y se marca el huérfano.
        "current_value": None if is_orphaned else round(current_val, 2),
        "suggested_target": round(eff_target, 2),
        "spi": None if is_orphaned else spi,
        "unit": unit,
        "component_name": comp_label,
        "orphaned": is_orphaned,
        "orphan_reason": orphan_reason,
    }


def calculate_project_metrics(
    first_arg: Any,
    second_arg: Any = None,
    *,
    db: Optional[Session] = None,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """Calcula las métricas EVM, Reservas Presupuestarias PMI, Regla 15% CPI y Sentinel."""
    if hasattr(first_arg, "query"):
        session: Session = first_arg
        project_or_id = second_arg
    else:
        project_or_id = first_arg
        session = db if db is not None else second_arg  # type: ignore[assignment]
    if session is None:
        raise ValueError("Database session 'db' is required for calculate_project_metrics")

    if isinstance(project_or_id, (str, uuid.UUID)):
        proj = (
            session.query(Project)
            .filter(Project.id == project_or_id, Project.deleted_at.is_(None))
            .first()
        )
        if proj is None:
            raise ValueError(f"Project {project_or_id} not found")
        return calculate_project_evm(session, proj, now=now)
    return calculate_project_evm(session, project_or_id, now=now)


def calculate_reserve_burn_index(contingency_reserve: float, cv: float) -> Dict[str, Any]:
    """Calcula el Índice de Consumo de Reserva de Contingencia (Reserve Burn Index — PMI §7.4.2.2)."""
    reserve = round(max(0.0, _safe_float(contingency_reserve, 0.0)), 2)
    consumed_amount = round(max(0.0, -_safe_float(cv, 0.0)), 2)
    remaining_reserve = round(max(0.0, reserve - consumed_amount), 2)
    if reserve > 0:
        burn_rate_pct = round(min(100.0, (consumed_amount / reserve) * 100.0), 1)
    else:
        burn_rate_pct = 100.0 if consumed_amount > 0 else 0.0

    if burn_rate_pct == 0.0:
        status = "intact"
    elif burn_rate_pct <= 50.0:
        status = "controlled"
    elif burn_rate_pct < 100.0:
        status = "warning"
    else:
        status = "exhausted"

    return {
        "contingency_reserve": reserve,
        "consumed_amount": consumed_amount,
        "remaining_reserve": remaining_reserve,
        "burn_rate_pct": burn_rate_pct,
        "status": status,
        "requires_reserve_drawdown_request": bool(burn_rate_pct > 50.0),
    }


def evaluate_control_accounts_concentration(
    components_metrics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Evalúa la concentración de variación en Cuentas de Control EDT Nivel 2 (PMI §5.4 / §7.4)."""
    if not components_metrics:
        return {
            "total_components": 0,
            "critical_components_count": 0,
            "overbudget_components_count": 0,
            "delayed_components_count": 0,
            "worst_cpi_component_code": None,
            "worst_spi_component_code": None,
            "concentration_risk_level": "none",
        }

    critical_count = 0
    overbudget_count = 0
    delayed_count = 0
    worst_cpi: Optional[float] = None
    worst_cpi_code: Optional[str] = None
    worst_spi: Optional[float] = None
    worst_spi_code: Optional[str] = None

    for comp in components_metrics:
        evm_data = comp.get("evm") if isinstance(comp.get("evm"), dict) else comp
        code = (
            str(
                comp.get("code")
                or evm_data.get("code")
                or comp.get("name")
                or evm_data.get("name")
                or ""
            ).strip()
            or None
        )
        cpi = _safe_float(evm_data.get("cpi"), 1.0)
        spi = _safe_float(evm_data.get("spi"), 1.0)
        cv = _safe_float(evm_data.get("cv"), 0.0)
        sv = _safe_float(evm_data.get("sv"), 0.0)
        health = str(evm_data.get("health_status") or "")

        if health == "CRITICO" or health.startswith("CRITICO") or cpi < 0.85 or spi < 0.85:
            critical_count += 1
        if cv < 0.0 or cpi < 1.0:
            overbudget_count += 1
        if sv < 0.0 or spi < 1.0:
            delayed_count += 1

        if cpi < 1.0 and (worst_cpi is None or cpi < worst_cpi):
            worst_cpi = cpi
            worst_cpi_code = code
        if spi < 1.0 and (worst_spi is None or spi < worst_spi):
            worst_spi = spi
            worst_spi_code = code

    total = len(components_metrics)
    if critical_count >= 2 or (total > 0 and (critical_count / total) >= 0.5):
        risk_level = "high"
    elif critical_count == 1 or overbudget_count > 0 or delayed_count > 0:
        risk_level = "moderate"
    else:
        risk_level = "low"

    return {
        "total_components": total,
        "critical_components_count": critical_count,
        "overbudget_components_count": overbudget_count,
        "delayed_components_count": delayed_count,
        "worst_cpi_component_code": worst_cpi_code,
        "worst_spi_component_code": worst_spi_code,
        "concentration_risk_level": risk_level,
    }


def evaluate_work_package_efficiency(
    estimated_hours: float,
    actual_hours: float,
    planned_cost: float,
    actual_cost: float,
    physical_progress_pct: float,
) -> Dict[str, Any]:
    """Evalúa la eficiencia de esfuerzo y sobrecosto de un paquete de trabajo WBS Nivel 3 (PMI §5.3 / §7.4)."""
    est_h = max(0.0, _safe_float(estimated_hours, 0.0))
    act_h = max(0.0, _safe_float(actual_hours, 0.0))
    plan_c = max(0.0, _safe_float(planned_cost, 0.0))
    act_c = max(0.0, _safe_float(actual_cost, 0.0))
    prog = max(0.0, min(100.0, _safe_float(physical_progress_pct, 0.0)))

    earned_hours = round(est_h * (prog / 100.0), 2)
    hours_efficiency_ratio = round(earned_hours / act_h, 2) if act_h > 0 else 1.0
    if plan_c > 0:
        cost_burn_pct = round((act_c / plan_c) * 100.0, 1)
    else:
        cost_burn_pct = 100.0 if act_c > 0 else 0.0

    is_effort_overrun = bool(est_h > 0 and act_h > est_h)
    is_cost_overrun = bool(plan_c > 0 and act_c > plan_c)

    if is_effort_overrun and is_cost_overrun:
        efficiency_status = "critical_overrun"
    elif is_effort_overrun or is_cost_overrun:
        efficiency_status = "warning_drift"
    else:
        efficiency_status = "optimal"

    return {
        "earned_hours": earned_hours,
        "hours_efficiency_ratio": hours_efficiency_ratio,
        "cost_burn_pct": cost_burn_pct,
        "is_effort_overrun": is_effort_overrun,
        "is_cost_overrun": is_cost_overrun,
        "efficiency_status": efficiency_status,
    }


def analyze_s_curve_velocity(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analiza la velocidad marginal, el punto de inflexión y la dirección de tendencia de la Curva S (PMBOK §7.4.2.3)."""
    if not points:
        return {
            "points_count": 0,
            "peak_ev_delta": 0.0,
            "peak_ac_delta": 0.0,
            "peak_period_label": None,
            "final_sv": 0.0,
            "final_cv": 0.0,
            "trend_direction": "flat",
        }

    valid_points = [
        pt for pt in points if pt.get("ev") is not None and pt.get("ac") is not None
    ]
    if not valid_points:
        valid_points = points

    ev_deltas: List[float] = []
    ac_deltas: List[float] = []
    for i, pt in enumerate(valid_points):
        curr_ev = _safe_float(pt.get("ev"), 0.0)
        curr_ac = _safe_float(pt.get("ac"), 0.0)
        if i == 0:
            ev_deltas.append(max(0.0, curr_ev))
            ac_deltas.append(max(0.0, curr_ac))
        else:
            prev_ev = _safe_float(valid_points[i - 1].get("ev"), 0.0)
            prev_ac = _safe_float(valid_points[i - 1].get("ac"), 0.0)
            ev_deltas.append(max(0.0, curr_ev - prev_ev))
            ac_deltas.append(max(0.0, curr_ac - prev_ac))

    raw_max_ev = max(ev_deltas, default=0.0)
    peak_ev_delta = round(raw_max_ev, 2)
    peak_ac_delta = round(max(ac_deltas, default=0.0), 2)

    peak_period_label: Optional[str] = None
    if peak_ev_delta > 0.0:
        for idx, delta in enumerate(ev_deltas):
            if abs(delta - raw_max_ev) < 1e-9:
                peak_period_label = str(valid_points[idx].get("label"))
                break

    last_pt = valid_points[-1]
    last_pv = _safe_float(last_pt.get("pv"), 0.0)
    last_ev = _safe_float(last_pt.get("ev"), 0.0)
    last_ac = _safe_float(last_pt.get("ac"), 0.0)
    final_sv = round(last_ev - last_pv, 2)
    final_cv = round(last_ev - last_ac, 2)

    if last_ev <= 0.0 or peak_ev_delta == 0.0:
        trend_direction = "flat"
    elif len(ev_deltas) >= 2:
        avg_delta = sum(ev_deltas) / len(ev_deltas)
        last_delta = ev_deltas[-1]
        if last_delta > avg_delta + 1e-6:
            trend_direction = "accelerating"
        elif last_delta < avg_delta - 1e-6:
            trend_direction = "decelerating"
        else:
            trend_direction = "steady"
    else:
        trend_direction = "steady"

    return {
        "points_count": len(valid_points),
        "peak_ev_delta": peak_ev_delta,
        "peak_ac_delta": peak_ac_delta,
        "peak_period_label": peak_period_label,
        "final_sv": final_sv,
        "final_cv": final_cv,
        "trend_direction": trend_direction,
    }


def evaluate_ieac_forecast_spread(
    ieac_cpi: float,
    ieac_composite: float,
    bac: float,
) -> Dict[str, Any]:
    """Evalúa la divergencia entre IEAC(CPI) e IEAC(CPI×SPI) según PMI EVM §4.4."""
    cpi_val = max(0.0, _safe_float(ieac_cpi, 0.0))
    comp_val = max(0.0, _safe_float(ieac_composite, 0.0))
    bac_val = _safe_float(bac, 0.0)

    spread_amount = round(comp_val - cpi_val, 2)
    if bac_val > 0.0:
        spread_pct_of_bac = round((abs(spread_amount) / bac_val) * 100.0, 2)
        overrun_vs_bac_pct = round(
            ((max(cpi_val, comp_val) - bac_val) / bac_val) * 100.0, 2
        )
    else:
        spread_pct_of_bac = 0.0
        overrun_vs_bac_pct = 0.0

    if bac_val <= 0.0:
        forecast_reliability = "unanchored"
    elif spread_pct_of_bac <= 10.0:
        forecast_reliability = "convergent"
    elif spread_pct_of_bac <= 25.0:
        forecast_reliability = "moderate_divergence"
    else:
        forecast_reliability = "high_divergence"

    return {
        "spread_amount": spread_amount,
        "spread_pct_of_bac": spread_pct_of_bac,
        "overrun_vs_bac_pct": overrun_vs_bac_pct,
        "forecast_reliability": forecast_reliability,
    }


def predict_schedule_slippage_days(
    planned_duration_days: float,
    spi_t: float,
) -> Dict[str, Any]:
    """Proyecta la duración total estimada al cierre IEAC(t) = PD / SPI(t) y el deslizamiento en días (Lipke / PMI Earned Schedule)."""
    pd = max(0.0, _safe_float(planned_duration_days, 0.0))
    spit = max(0.0, _safe_float(spi_t, 0.0))

    if pd <= 0.0:
        return {
            "planned_duration_days": 0.0,
            "ieac_t_days": 0.0,
            "projected_slippage_days": 0.0,
            "slippage_pct": 0.0,
            "schedule_forecast_status": "unscheduled",
        }

    if spit <= 0.0:
        return {
            "planned_duration_days": round(pd, 2),
            "ieac_t_days": None,
            "projected_slippage_days": None,
            "slippage_pct": None,
            "schedule_forecast_status": "stalled",
        }

    ieac_t_days = round(pd / spit, 2)
    projected_slippage_days = round(ieac_t_days - pd, 2)
    slippage_pct = round(((ieac_t_days - pd) / pd) * 100.0, 2)

    if projected_slippage_days <= 0.0:
        schedule_forecast_status = "ahead_or_on_time"
    elif slippage_pct <= 15.0:
        schedule_forecast_status = "minor_slippage"
    else:
        schedule_forecast_status = "critical_slippage"

    return {
        "planned_duration_days": round(pd, 2),
        "ieac_t_days": ieac_t_days,
        "projected_slippage_days": projected_slippage_days,
        "slippage_pct": slippage_pct,
        "schedule_forecast_status": schedule_forecast_status,
    }


def evaluate_wbs_scope_coverage(
    total_tasks: int,
    unassigned_tasks: int,
    components_count: int,
) -> Dict[str, Any]:
    """Audita el cumplimiento de la Regla del 100% de Alcance en la EDT/WBS (PMI Practice Standard for WBS)."""
    total = max(0, int(total_tasks or 0))
    unassigned = min(total, max(0, int(unassigned_tasks or 0)))
    assigned = total - unassigned
    comps = max(0, int(components_count or 0))

    scope_coverage_pct = round((assigned / total) * 100.0, 2) if total > 0 else 100.0
    orphan_leakage_pct = round((unassigned / total) * 100.0, 2) if total > 0 else 0.0

    if total == 0:
        wbs_scope_status = "empty_wbs"
    elif comps == 0 and total > 0:
        wbs_scope_status = "unstructured"
    elif unassigned == 0 and comps > 0:
        wbs_scope_status = "rule_100_compliant"
    elif 0.0 < orphan_leakage_pct <= 15.0:
        wbs_scope_status = "minor_scope_leakage"
    else:
        wbs_scope_status = "critical_scope_leakage"

    return {
        "total_tasks": total,
        "assigned_tasks": assigned,
        "unassigned_tasks": unassigned,
        "components_count": comps,
        "scope_coverage_pct": scope_coverage_pct,
        "orphan_leakage_pct": orphan_leakage_pct,
        "wbs_scope_status": wbs_scope_status,
    }


def calculate_pert_three_point_estimate(
    optimistic: float,
    most_likely: float,
    pessimistic: float,
) -> Dict[str, Any]:
    """Calcula la estimación PERT por Tres Valores Beta y Triangular (PMI PMBOK §6.4.2.4)."""
    o = round(max(0.0, float(optimistic or 0.0)), 2)
    m = round(max(0.0, float(most_likely or 0.0)), 2)
    p = round(max(0.0, float(pessimistic or 0.0)), 2)

    is_monotonic_order = bool(o <= m <= p)
    expected_estimate = round((o + 4.0 * m + p) / 6.0, 2)
    triangular_estimate = round((o + m + p) / 3.0, 2)
    std_deviation = round(max(0.0, p - o) / 6.0, 2)
    variance = round(std_deviation ** 2, 4)
    confidence_68_range = (
        round(max(0.0, expected_estimate - std_deviation), 2),
        round(expected_estimate + std_deviation, 2),
    )

    if not is_monotonic_order:
        uncertainty_status = "invalid_bounds"
    elif std_deviation == 0.0:
        uncertainty_status = "deterministic"
    elif expected_estimate > 0 and (std_deviation / expected_estimate) <= 0.15:
        uncertainty_status = "low_uncertainty"
    else:
        uncertainty_status = "high_uncertainty"

    return {
        "optimistic": o,
        "most_likely": m,
        "pessimistic": p,
        "is_monotonic_order": is_monotonic_order,
        "expected_estimate": expected_estimate,
        "triangular_estimate": triangular_estimate,
        "std_deviation": std_deviation,
        "variance": variance,
        "confidence_68_range": confidence_68_range,
        "uncertainty_status": uncertainty_status,
    }


def evaluate_contingency_reserve_burn_alignment(
    contingency_allocated: float,
    contingency_consumed: float,
    percent_complete: float,
) -> Dict[str, Any]:
    """Audita la tasa de consumo de la reserva de contingencia frente al avance físico (PMI PMBOK §7.4.2.6 / §11.7)."""
    allocated = round(max(0.0, float(contingency_allocated or 0.0)), 2)
    consumed = round(max(0.0, float(contingency_consumed or 0.0)), 2)
    pct_complete = round(min(100.0, max(0.0, float(percent_complete or 0.0))), 2)

    remaining_reserve = round(max(0.0, allocated - consumed), 2)
    reserve_burn_pct = (
        round((consumed / allocated) * 100.0, 2)
        if allocated > 0
        else (100.0 if consumed > 0 else 0.0)
    )

    if allocated <= 0:
        burn_to_progress_ratio = 0.0
    elif pct_complete > 0:
        burn_to_progress_ratio = round(reserve_burn_pct / pct_complete, 2)
    elif reserve_burn_pct > 0:
        burn_to_progress_ratio = round(reserve_burn_pct, 2)
    else:
        burn_to_progress_ratio = 0.0

    burn_variance_pct = round(reserve_burn_pct - pct_complete, 2)

    if allocated == 0.0:
        reserve_alignment_status = "no_contingency_allocated"
    elif consumed >= allocated and pct_complete < 100.0:
        reserve_alignment_status = "reserve_exhausted"
    elif consumed >= allocated and pct_complete == 100.0:
        reserve_alignment_status = "proportional_burn"
    elif burn_variance_pct >= 20.0:
        reserve_alignment_status = "premature_depletion"
    elif burn_variance_pct >= -15.0:
        reserve_alignment_status = "proportional_burn"
    else:
        reserve_alignment_status = "conservative_preservation"

    return {
        "contingency_allocated": allocated,
        "contingency_consumed": consumed,
        "remaining_reserve": remaining_reserve,
        "percent_complete": pct_complete,
        "reserve_burn_pct": reserve_burn_pct,
        "burn_to_progress_ratio": burn_to_progress_ratio,
        "burn_variance_pct": burn_variance_pct,
        "reserve_alignment_status": reserve_alignment_status,
    }


def evaluate_cost_schedule_index_csi(
    cpi: float | None,
    spi: float | None,
    percent_complete: float = 0.0,
) -> dict[str, Any]:
    """Evalúa el Cost-Schedule Index (CSI = CPI * SPI) y la viabilidad de recuperación según PMI EVM / PMBOK §7.4."""
    pct = round(min(100.0, max(0.0, float(percent_complete or 0.0))), 2)
    if cpi is None or spi is None or float(cpi) <= 0 or float(spi) <= 0:
        cpi_val = round(max(0.0, float(cpi or 0.0)), 4)
        spi_val = round(max(0.0, float(spi or 0.0)), 4)
        return {
            "cpi": cpi_val,
            "spi": spi_val,
            "csi": 0.0,
            "percent_complete": pct,
            "tradeoff_mode": "insufficient_data",
            "csi_health_band": "unassessed",
            "recovery_likelihood": "unassessed",
        }

    cpi_val = round(float(cpi), 4)
    spi_val = round(float(spi), 4)
    csi = round(cpi_val * spi_val, 4)

    if spi_val >= 1.0 and cpi_val < 0.95:
        tradeoff_mode = "crashing_cost_for_speed"
    elif cpi_val >= 1.0 and spi_val < 0.95:
        tradeoff_mode = "under_spending_behind_schedule"
    elif cpi_val < 0.95 and spi_val < 0.95:
        tradeoff_mode = "dual_degradation"
    else:
        tradeoff_mode = "aligned_execution"

    if csi >= 0.95:
        csi_health_band = "optimal"
    elif csi >= 0.80:
        csi_health_band = "caution"
    else:
        csi_health_band = "critical"

    if csi < 0.80 and pct >= 20.0:
        recovery_likelihood = "irreversible_overrun_likely"
    elif csi < 0.95:
        recovery_likelihood = "corrective_action_viable"
    else:
        recovery_likelihood = "on_track"

    return {
        "cpi": cpi_val,
        "spi": spi_val,
        "csi": csi,
        "percent_complete": pct,
        "tradeoff_mode": tradeoff_mode,
        "csi_health_band": csi_health_band,
        "recovery_likelihood": recovery_likelihood,
    }


def evaluate_variance_at_completion_alert(
    bac: float,
    eac: float,
    management_reserve: float = 0.0,
) -> dict[str, Any]:
    """Evalúa la Variación a la Conclusión (VAC = BAC - EAC) y cobertura por Reserva de Gestión según PMI PMBOK §7.4.2.2."""
    bac_val = round(max(0.0, float(bac or 0.0)), 2)
    eac_val = round(max(0.0, float(eac or 0.0)), 2)
    mr_val = round(max(0.0, float(management_reserve or 0.0)), 2)

    cost_baseline_plus_mr = round(bac_val + mr_val, 2)
    vac_amount = round(bac_val - eac_val, 2)
    vac_pct = round((vac_amount / bac_val) * 100.0, 2) if bac_val > 0 else 0.0
    overrun_amount = round(max(0.0, eac_val - bac_val), 2)
    unfunded_overrun = round(max(0.0, overrun_amount - mr_val), 2)
    is_covered_by_management_reserve = overrun_amount <= mr_val

    if bac_val == 0.0:
        vac_alert_status = "unbaselined"
    elif unfunded_overrun > 0.0:
        vac_alert_status = "budget_breach_beyond_mr"
    elif overrun_amount > 0.0 and is_covered_by_management_reserve:
        vac_alert_status = "overrun_absorbed_by_mr"
    else:
        vac_alert_status = "on_or_under_budget"

    return {
        "bac": bac_val,
        "eac": eac_val,
        "management_reserve": mr_val,
        "cost_baseline_plus_mr": cost_baseline_plus_mr,
        "vac_amount": vac_amount,
        "vac_pct": vac_pct,
        "overrun_amount": overrun_amount,
        "unfunded_overrun": unfunded_overrun,
        "is_covered_by_management_reserve": is_covered_by_management_reserve,
        "vac_alert_status": vac_alert_status,
    }


def evaluate_etc_forecasting_method_posture(
    bac: float | int | None,
    ev: float | int | None,
    ac: float | int | None,
    cpi: float | int | None = None,
    spi: float | int | None = None,
) -> dict[str, Any]:
    """Evalúa las 3 fórmulas canónicas de pronóstico ETC según PMI PMBOK §7.4 (Control Costs)."""
    safe_bac = max(0.0, float(bac or 0.0))
    safe_ev = max(0.0, min(safe_bac, float(ev or 0.0)))
    safe_ac = max(0.0, float(ac or 0.0))
    remaining_work = round(max(0.0, safe_bac - safe_ev), 2)

    if cpi is not None and float(cpi) > 0:
        effective_cpi = round(float(cpi), 4)
    elif safe_ac > 0 and safe_ev > 0:
        effective_cpi = round(safe_ev / safe_ac, 4)
    else:
        effective_cpi = 1.0

    if spi is not None and float(spi) > 0:
        effective_spi = round(float(spi), 4)
    else:
        effective_spi = 1.0

    etc_atypical = remaining_work
    etc_typical_cpi = round(remaining_work / effective_cpi, 2)
    etc_composite_cpi_spi = round(
        remaining_work / (effective_cpi * effective_spi), 2
    )

    if remaining_work == 0.0:
        recommended_method = "COMPLETED_NO_ETC"
    elif effective_cpi < 0.95 and effective_spi < 0.95:
        recommended_method = "COMPOSITE_CPI_SPI"
    elif effective_cpi < 0.95:
        recommended_method = "TYPICAL_CPI"
    else:
        recommended_method = "ATYPICAL_REMAINING_BUDGET"

    return {
        "remaining_work": remaining_work,
        "effective_cpi": effective_cpi,
        "effective_spi": effective_spi,
        "etc_atypical": etc_atypical,
        "etc_typical_cpi": etc_typical_cpi,
        "etc_composite_cpi_spi": etc_composite_cpi_spi,
        "recommended_method": recommended_method,
    }


def evaluate_funding_limit_reconciliation(
    planned_cumulative_spend: float | int | None,
    actual_cumulative_spend: float | int | None,
    periodic_funding_cap: float | int | None,
    management_reserve: float | int | None = 0.0,
) -> dict[str, Any]:
    """Evalúa la Conciliación del Límite de Financiamiento según PMI PMBOK §7.3 (Determine Budget) y §7.4 (Control Costs)."""
    safe_planned = max(0.0, round(float(planned_cumulative_spend or 0.0), 2))
    safe_actual = max(0.0, round(float(actual_cumulative_spend or 0.0), 2))
    safe_cap = max(0.0, round(float(periodic_funding_cap or 0.0), 2))
    safe_reserve = max(0.0, round(float(management_reserve or 0.0), 2))

    total_authorized_ceiling = round(safe_cap + safe_reserve, 2)
    cap_utilization_pct = (
        round((safe_actual / safe_cap) * 100.0, 2)
        if safe_cap > 0
        else (100.0 if safe_actual > 0 else 0.0)
    )
    funding_headroom = round(safe_cap - safe_actual, 2)
    planned_exceeds_cap = bool(safe_cap > 0 and safe_planned > safe_cap)
    actual_exceeds_cap = bool(safe_cap > 0 and safe_actual > safe_cap)

    if safe_cap == 0.0:
        posture = "UNCONFIGURED_FUNDING_CAP"
    elif safe_actual > total_authorized_ceiling:
        posture = "CEILING_BREACH_CRITICAL"
    elif actual_exceeds_cap and safe_actual <= total_authorized_ceiling:
        posture = "RESERVE_DRAWDOWN_REQUIRED"
    elif not actual_exceeds_cap and planned_exceeds_cap:
        posture = "RESCHEDULE_REQUIRED_FOR_CAP"
    else:
        posture = "RECONCILED_WITHIN_LIMITS"

    return {
        "safe_planned": safe_planned,
        "safe_actual": safe_actual,
        "safe_cap": safe_cap,
        "safe_reserve": safe_reserve,
        "total_authorized_ceiling": total_authorized_ceiling,
        "cap_utilization_pct": cap_utilization_pct,
        "funding_headroom": funding_headroom,
        "planned_exceeds_cap": planned_exceeds_cap,
        "actual_exceeds_cap": actual_exceeds_cap,
        "posture": posture,
    }


def evaluate_funding_limit_periods_reconciliation(
    periods: Optional[List[Dict[str, Any]]] = None,
    max_utilization_buffer_pct: float = 95.0,
) -> Dict[str, Any]:
    """Concilia desembolsos planificados frente a límites de financiamiento por período (PMBOK §7.3.2.3).

    Cada período declara `period`/`id`/`quarter` (fallback 'P-{idx}'),
    desembolso planificado (`planned_expenditure`/`planned_cost`) y límite
    autorizado (`funding_limit`/`authorized_funds`):
    - `breached_periods`: límite agotado o superado (sin límite con gasto, o
      planned > limit + 1e-9); aporta (planned - limit) a `total_funding_shortfall`.
    - `tight_buffer_periods`: utilization > `max_utilization_buffer_pct` sin brecha.
    - `peak_funding_utilization_pct` (2 decimales; 0.0 sin períodos con límite).
    - `is_reconciled`: sin períodos en breach.
    - `funding_posture`: 'NO_FUNDING_PERIODS_DEFINED' sin períodos;
      'FUNDING_LIMIT_BREACH'; 'TIGHT_FUNDING_BUFFER_WARNING';
      'RECONCILED_WITHIN_FUNDING_LIMITS'.
    """
    valid_periods = [p for p in (periods or []) if isinstance(p, dict)]
    evaluated_periods_count = len(valid_periods)
    if evaluated_periods_count == 0:
        return {
            "evaluated_periods_count": 0,
            "breached_periods": [],
            "tight_buffer_periods": [],
            "peak_funding_utilization_pct": 0.0,
            "total_funding_shortfall": 0.0,
            "is_reconciled": True,
            "funding_posture": "NO_FUNDING_PERIODS_DEFINED",
        }

    breached_periods: List[str] = []
    tight_buffer_periods: List[str] = []
    peak_funding_utilization_pct = 0.0
    total_funding_shortfall = 0.0

    for idx, item in enumerate(valid_periods, start=1):
        period_id = str(
            item.get("period") or item.get("id") or item.get("quarter") or ""
        ).strip() or f"P-{idx}"
        try:
            planned = max(
                0.0,
                float(
                    item.get("planned_expenditure")
                    if item.get("planned_expenditure") is not None
                    else (item.get("planned_cost") or 0.0)
                ),
            )
        except (TypeError, ValueError):
            planned = 0.0
        try:
            limit = max(
                0.0,
                float(
                    item.get("funding_limit")
                    if item.get("funding_limit") is not None
                    else (item.get("authorized_funds") or 0.0)
                ),
            )
        except (TypeError, ValueError):
            limit = 0.0

        if limit > 0.0:
            util_pct = (planned / limit) * 100.0
            peak_funding_utilization_pct = max(peak_funding_utilization_pct, util_pct)

        if (limit <= 0.0 and planned > 0.0) or (
            limit > 0.0 and planned > limit + 1e-9
        ):
            breached_periods.append(period_id)
            total_funding_shortfall += planned - limit
        elif (
            limit > 0.0
            and ((planned / limit) * 100.0)
            > float(max_utilization_buffer_pct) + 1e-9
        ):
            tight_buffer_periods.append(period_id)

    peak_funding_utilization_pct = round(peak_funding_utilization_pct, 2)
    total_funding_shortfall = round(total_funding_shortfall, 2)
    is_reconciled = bool(len(breached_periods) == 0)

    if evaluated_periods_count == 0:
        funding_posture = "NO_FUNDING_PERIODS_DEFINED"
    elif breached_periods:
        funding_posture = "FUNDING_LIMIT_BREACH"
    elif tight_buffer_periods:
        funding_posture = "TIGHT_FUNDING_BUFFER_WARNING"
    else:
        funding_posture = "RECONCILED_WITHIN_FUNDING_LIMITS"

    return {
        "evaluated_periods_count": evaluated_periods_count,
        "breached_periods": breached_periods,
        "tight_buffer_periods": tight_buffer_periods,
        "peak_funding_utilization_pct": peak_funding_utilization_pct,
        "total_funding_shortfall": total_funding_shortfall,
        "is_reconciled": is_reconciled,
        "funding_posture": funding_posture,
    }


def evaluate_cpi_trend_degradation(
    cpi_series: list[float | int] | None,
) -> dict[str, Any]:
    """Analiza una serie cronológica de lecturas de CPI según PMI PMBOK §7.4 (Trend Analysis)."""
    clean_series = [
        round(float(v), 4)
        for v in (cpi_series or [])
        if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) > 0.0
    ]
    periods_count = len(clean_series)
    latest_cpi = clean_series[-1] if periods_count > 0 else 1.0
    average_cpi = (
        round(sum(clean_series) / periods_count, 4) if periods_count > 0 else 1.0
    )

    consecutive_drops = 0
    for idx in range(periods_count - 1, 0, -1):
        if clean_series[idx] < clean_series[idx - 1]:
            consecutive_drops += 1
        else:
            break

    net_drift = (
        round(clean_series[-1] - clean_series[0], 4) if periods_count >= 2 else 0.0
    )

    if periods_count < 2:
        posture = "INSUFFICIENT_TREND_HISTORY"
    elif consecutive_drops >= 3 or (consecutive_drops >= 2 and latest_cpi < 0.90):
        posture = "SYSTEMIC_CPI_EROSION"
    elif consecutive_drops >= 1 and latest_cpi < 0.95:
        posture = "EARLY_DEGRADATION_WARNING"
    else:
        posture = "IMPROVING_OR_STABLE_TREND"

    return {
        "clean_series": clean_series,
        "periods_count": periods_count,
        "latest_cpi": latest_cpi,
        "average_cpi": average_cpi,
        "consecutive_drops": consecutive_drops,
        "net_drift": net_drift,
        "posture": posture,
    }


def evaluate_rebaselining_otb_threshold(
    bac: float,
    ac: float,
    ev: float,
    approved_change_delta: float = 0.0,
    tcpi_bac_ceiling: float = 1.20,
) -> Dict[str, Any]:
    """Evalúa cuándo una línea base de costos requiere Over-Target Baseline (OTB) o Rebaselining formal según PMI PMBOK §7.4."""
    ev_val = float(ev or 0.0)
    ac_val = float(ac or 0.0)
    ceiling_val = float(tcpi_bac_ceiling if tcpi_bac_ceiling is not None else 1.20)

    adjusted_bac = round(
        max(0.0, float(bac or 0.0) + float(approved_change_delta or 0.0)), 2
    )
    cpi = (
        round(ev_val / ac_val, 4)
        if ac_val > 0
        else (1.0 if ev_val > 0 else 0.0)
    )
    tcpi_bac = (
        round(max(0.0, adjusted_bac - ev_val) / (adjusted_bac - ac_val), 4)
        if (adjusted_bac - ac_val) > 0
        else (999.0 if ev_val < adjusted_bac else 0.0)
    )
    budget_exhausted = bool(
        adjusted_bac > 0 and ac_val >= adjusted_bac and ev_val < adjusted_bac
    )
    requires_otb_formal_review = bool(
        adjusted_bac > 0 and (budget_exhausted or tcpi_bac > ceiling_val)
    )

    recommendations: List[str] = []
    if adjusted_bac <= 0:
        baseline_posture = "NO_ACTIVE_BASELINE"
        recommendations.append(
            "Establecer y aprobar formalmente la línea base de costos (BAC) antes de evaluar umbrales OTB (PMI §7.3)."
        )
    elif budget_exhausted:
        baseline_posture = "OVER_TARGET_BASELINE_REQUIRED"
        recommendations.append(
            "Presupuesto agotado con trabajo pendiente: someter solicitud formal de Over-Target Baseline (OTB) al CCB; prohibido rebaselining unilateral (PMI §7.4)."
        )
    elif tcpi_bac > ceiling_val:
        baseline_posture = "REBASELINING_EVALUATION_RECOMMENDED"
        recommendations.append(
            "TCPI_BAC supera el umbral de recuperabilidad: evaluar rebaselining u OTB mediante control integrado de cambios (CCB) y recalcular EAC."
        )
    elif tcpi_bac > 1.0:
        baseline_posture = "BASELINE_RECOVERABLE"
        recommendations.append(
            "Línea base exigible pero recuperable: aplicar acciones correctivas de eficiencia de costos sin modificar la línea base."
        )
    else:
        baseline_posture = "BASELINE_WITHIN_TOLERANCE"
        recommendations.append(
            "Desempeño de costos dentro de la tolerancia de la línea base autorizada."
        )

    return {
        "adjusted_bac": adjusted_bac,
        "cpi": cpi,
        "tcpi_bac": tcpi_bac,
        "budget_exhausted": budget_exhausted,
        "requires_otb_formal_review": requires_otb_formal_review,
        "baseline_posture": baseline_posture,
        "recommendations": recommendations,
    }


def evaluate_management_reserve_release_governance(
    bac: float,
    management_reserve_initial: float,
    mr_releases: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Audita la gobernanza de liberaciones de Reserva de Gestión (Management Reserve — MR) según PMI PMBOK §7.4 y §11.6."""
    valid_releases = [
        item for item in (mr_releases or []) if isinstance(item, dict)
    ]

    try:
        safe_bac = max(0.0, float(bac or 0.0))
    except (TypeError, ValueError):
        safe_bac = 0.0

    try:
        initial_mr = round(max(0.0, float(management_reserve_initial or 0.0)), 2)
    except (TypeError, ValueError):
        initial_mr = 0.0

    authorized_sum = 0.0
    unauthorized_sum = 0.0
    unauthorized_release_ids: List[str] = []

    for idx, r in enumerate(valid_releases, start=1):
        raw_id = r.get("id") if r.get("id") is not None else r.get("release_id")
        rel_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"MR-{idx}"
        )

        try:
            amount = max(0.0, float(r.get("amount") or 0.0))
        except (TypeError, ValueError):
            amount = 0.0

        sponsor_approved = bool(r.get("sponsor_approved", False))
        justification = str(r.get("justification") or "").strip()
        is_authorized = sponsor_approved and len(justification) >= 10

        if is_authorized:
            authorized_sum += amount
        else:
            unauthorized_sum += amount
            unauthorized_release_ids.append(rel_id)

    authorized_mr_released = round(authorized_sum, 2)
    unauthorized_mr_amount = round(unauthorized_sum, 2)
    total_released = authorized_mr_released + unauthorized_mr_amount
    remaining_mr = round(initial_mr - total_released, 2)
    updated_project_budget_total = round(safe_bac + initial_mr, 2)
    mr_burn_pct = (
        round((total_released / initial_mr) * 100.0, 2)
        if initial_mr > 0
        else 0.0
    )

    recommendations: List[str] = []
    if initial_mr <= 0 and len(valid_releases) == 0:
        mr_governance_posture = "NO_MANAGEMENT_RESERVE"
        recommendations.append(
            "Definir Reserva de Gestión (Management Reserve) en el presupuesto del proyecto para cubrir riesgos imprevistos 'unknown-unknowns' (PMBOK §7.3 / §7.4)."
        )
    elif remaining_mr < 0:
        mr_governance_posture = "MANAGEMENT_RESERVE_OVERRUN"
        recommendations.append(
            f"Las liberaciones acumuladas superan la Reserva de Gestión inicial (saldo {remaining_mr}). Escalar al Patrocinador y CCB para ampliación presupuestaria u OTB (PMBOK §7.4)."
        )
    elif len(unauthorized_release_ids) > 0:
        mr_governance_posture = "UNAUTHORIZED_MR_DRAWDOWN"
        recommendations.append(
            f"Regularizar liberaciones de Reserva de Gestión sin aprobación formal del patrocinador o sin justificación suficiente ({', '.join(unauthorized_release_ids)}) mediante Control Integrado de Cambios (PMBOK §7.4 / §11.6)."
        )
    else:
        mr_governance_posture = "GOVERNED_MR_UTILIZATION"
        recommendations.append(
            "Uso de Reserva de Gestión gobernado conforme a PMI PMBOK §7.4 con aprobación del patrocinador y trazabilidad hacia la línea base BAC."
        )

    return {
        "initial_mr": initial_mr,
        "authorized_mr_released": authorized_mr_released,
        "unauthorized_mr_amount": unauthorized_mr_amount,
        "unauthorized_release_ids": unauthorized_release_ids,
        "remaining_mr": remaining_mr,
        "updated_project_budget_total": updated_project_budget_total,
        "mr_burn_pct": mr_burn_pct,
        "mr_governance_posture": mr_governance_posture,
        "recommendations": recommendations,
    }


def evaluate_tcpi_recovery_feasibility(
    bac: float = 0.0,
    ev: float = 0.0,
    ac: float = 0.0,
    eac: float | None = None,
    max_feasible_tcpi: float = 1.10,
    max_efficiency_jump: float = 0.15,
) -> dict[str, Any]:
    """Evalúa la viabilidad de recuperación BAC vía TCPI (PMBOK §7.4.2.4).

    Compara el TCPI sobre BAC frente al TCPI sobre EAC: si los fondos del
    BAC se agotan (AC >= BAC con EV < BAC) o se exige un salto de eficiencia
    fuera de los límites (max_feasible_tcpi, max_efficiency_jump), la meta
    BAC no es recuperable y la postura manda adoptar el EAC:
    - `tcpi_bac`: remaining_work / (bac - ac) con finanzas; 0.0 sin trabajo
      pendiente; 999.0 con fondos BAC agotados.
    - `tcpi_eac`: análogo sobre el EAC efectivo (eac provista o bac / cpi).
    - `efficiency_jump_required`: tcpi_bac - cpi (999.0 con fondos agotados).
    - `recovery_posture`: 'NO_BASELINE_BUDGET' sin BAC;
      'BAC_FUNDS_EXHAUSTED_REBASELINE_REQUIRED'; 'UNRECOVERABLE_BAC_ADOPT_EAC';
      'STRETCH_RECOVERY_MONITOR_CLOSELY' (TCPI_BAC > 1);
      'FEASIBLE_BAC_COMPLETION' (TCPI_BAC <= 1).
    """
    safe_bac = max(0.0, float(bac or 0.0))
    safe_ev = max(0.0, float(ev or 0.0))
    safe_ac = max(0.0, float(ac or 0.0))

    if safe_bac <= 0.0:
        return {
            "cpi": 1.0,
            "tcpi_bac": 1.0,
            "tcpi_eac": 1.0,
            "efficiency_jump_required": 0.0,
            "is_bac_funds_exhausted": False,
            "is_bac_recoverable": True,
            "recovery_posture": "NO_BASELINE_BUDGET",
        }

    cpi = round(safe_ev / safe_ac, 4) if safe_ac > 0.0 else 1.0
    remaining_work = max(0.0, safe_bac - safe_ev)
    remaining_funds_bac = safe_bac - safe_ac
    is_bac_funds_exhausted = bool(remaining_funds_bac <= 1e-9 and remaining_work > 1e-9)

    if remaining_work <= 1e-9:
        tcpi_bac = 0.0
    elif remaining_funds_bac <= 1e-9:
        tcpi_bac = 999.0
    else:
        tcpi_bac = round(remaining_work / remaining_funds_bac, 4)

    effective_eac = (
        float(eac)
        if (eac is not None and float(eac) > 0.0)
        else (round(safe_bac / cpi, 2) if cpi > 0.0 else safe_bac)
    )
    remaining_funds_eac = effective_eac - safe_ac
    if remaining_work <= 1e-9:
        tcpi_eac = 0.0
    elif remaining_funds_eac <= 1e-9:
        tcpi_eac = 999.0
    else:
        tcpi_eac = round(remaining_work / remaining_funds_eac, 4)

    if not is_bac_funds_exhausted:
        efficiency_jump_required = round(max(0.0, tcpi_bac - cpi), 4)
    else:
        efficiency_jump_required = 999.0

    is_bac_recoverable = bool(
        not is_bac_funds_exhausted
        and tcpi_bac <= float(max_feasible_tcpi) + 1e-9
        and efficiency_jump_required <= float(max_efficiency_jump) + 1e-9
    )

    if is_bac_funds_exhausted:
        recovery_posture = "BAC_FUNDS_EXHAUSTED_REBASELINE_REQUIRED"
    elif not is_bac_recoverable:
        recovery_posture = "UNRECOVERABLE_BAC_ADOPT_EAC"
    elif tcpi_bac > 1.0 + 1e-9:
        recovery_posture = "STRETCH_RECOVERY_MONITOR_CLOSELY"
    else:
        recovery_posture = "FEASIBLE_BAC_COMPLETION"

    return {
        "cpi": cpi,
        "tcpi_bac": tcpi_bac,
        "tcpi_eac": tcpi_eac,
        "efficiency_jump_required": efficiency_jump_required,
        "is_bac_funds_exhausted": is_bac_funds_exhausted,
        "is_bac_recoverable": is_bac_recoverable,
        "recovery_posture": recovery_posture,
    }


def audit_work_package_evmt_governance(
    work_packages: list[dict[str, Any]] | None = None,
    max_loe_share_pct: float = 15.0,
) -> dict[str, Any]:
    """Audita la gestión de técnicas EVMT en paquetes de trabajo (PMBOK §7.4).

    Paquetes válidos (dict con `id`/`wp_id` no vacío). Cada uno declara
    presupuesto (`budget`), técnica (`evmt`, default 'PERCENT_COMPLETE'),
    estado (`status`, default 'IN_PROGRESS'), avance reclamado (`claimed_pct`,
    clamp [0, 100]) y duración (`duration_periods`, default 1):
    - `formula_cap_violation_ids`: paquetes IN_PROGRESS con fórmula fija que
      reclaman avance por encima del tope (0/100 → > 0, 50/50 → > 50, 20/80 → > 20).
    - `long_duration_fixed_formula_ids`: fórmula fija con duration_periods > 2.
    - `loe_share_pct` del presupuesto LEVEL_OF_EFFORT (2 decimales; 0.0 sin presupuesto).
    - `is_evmt_governed`: paquetes, traspaso del tope LOE y sin hallazgos.
    - `evmt_posture`: 'NO_WORK_PACKAGES' sin paquetes;
      'FIXED_FORMULA_PERCENT_CAP_VIOLATION'; 'FIXED_FORMULA_ON_LONG_WORK_PACKAGE';
      'EXCESSIVE_LEVEL_OF_EFFORT_SHARE'; 'GOVERNED_EVMT_BASELINE'.
    """
    FIXED_FORMULA_CAPS = {"0_100": 0.0, "50_50": 50.0, "20_80": 20.0}
    CLOSED_STATUSES = {"COMPLETED", "DONE", "CLOSED"}
    valid_packages = [
        wp
        for wp in (work_packages or [])
        if isinstance(wp, dict) and str(wp.get("id") or wp.get("wp_id") or "").strip()
    ]
    total_work_packages = len(valid_packages)
    if total_work_packages == 0:
        return {
            "total_work_packages": 0,
            "loe_share_pct": 0.0,
            "formula_cap_violation_ids": [],
            "long_duration_fixed_formula_ids": [],
            "is_evmt_governed": False,
            "evmt_posture": "NO_WORK_PACKAGES",
        }

    total_budget = 0.0
    loe_budget = 0.0
    formula_cap_violation_ids: list[str] = []
    long_duration_fixed_formula_ids: list[str] = []

    for wp in valid_packages:
        wp_id = str(wp.get("id") or wp.get("wp_id") or "").strip()
        budget = max(0.0, float(wp.get("budget") or 0.0))
        evmt = str(wp.get("evmt") or "PERCENT_COMPLETE").strip().upper()
        status = str(wp.get("status") or "IN_PROGRESS").strip().upper()
        claimed_pct = max(0.0, min(100.0, float(wp.get("claimed_pct") or 0.0)))
        duration_periods = max(1, int(wp.get("duration_periods") or 1))

        total_budget += budget
        if evmt == "LEVEL_OF_EFFORT":
            loe_budget += budget

        if status not in CLOSED_STATUSES:
            cap = FIXED_FORMULA_CAPS.get(evmt)
            if cap is not None and claimed_pct > cap + 1e-6:
                formula_cap_violation_ids.append(wp_id)
        if evmt in FIXED_FORMULA_CAPS and duration_periods > 2:
            long_duration_fixed_formula_ids.append(wp_id)

    loe_share_pct = (
        round((loe_budget / total_budget) * 100.0, 2) if total_budget > 0.0 else 0.0
    )
    is_evmt_governed = bool(
        total_work_packages > 0
        and len(formula_cap_violation_ids) == 0
        and len(long_duration_fixed_formula_ids) == 0
        and loe_share_pct <= float(max_loe_share_pct)
    )

    if total_work_packages == 0:
        evmt_posture = "NO_WORK_PACKAGES"
    elif len(formula_cap_violation_ids) > 0:
        evmt_posture = "FIXED_FORMULA_PERCENT_CAP_VIOLATION"
    elif len(long_duration_fixed_formula_ids) > 0:
        evmt_posture = "FIXED_FORMULA_ON_LONG_WORK_PACKAGE"
    elif loe_share_pct > float(max_loe_share_pct):
        evmt_posture = "EXCESSIVE_LEVEL_OF_EFFORT_SHARE"
    else:
        evmt_posture = "GOVERNED_EVMT_BASELINE"

    return {
        "total_work_packages": total_work_packages,
        "loe_share_pct": loe_share_pct,
        "formula_cap_violation_ids": formula_cap_violation_ids,
        "long_duration_fixed_formula_ids": long_duration_fixed_formula_ids,
        "is_evmt_governed": is_evmt_governed,
        "evmt_posture": evmt_posture,
    }


class ProjectEVMService:
    """Fachada canónica del servicio EVM y Diagnóstico Predictivo PMI (Vol. 5 y Vol. 6)."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db

    @staticmethod
    def calculate_project_metrics(
        first_arg: Any,
        second_arg: Any = None,
        *,
        db: Optional[Session] = None,
        now: Optional[datetime.datetime] = None,
    ) -> Dict[str, Any]:
        return calculate_project_metrics(first_arg, second_arg, db=db, now=now)

    @staticmethod
    def calculate_project_evm(
        db: Session,
        project: Project,
        now: Optional[datetime.datetime] = None,
    ) -> Dict[str, Any]:
        return calculate_project_evm(db, project, now=now)

    @staticmethod
    def calculate_project_evm_advanced(
        db: Session,
        project: Project,
        now: Optional[datetime.datetime] = None,
    ) -> Dict[str, Any]:
        return calculate_project_evm_advanced(db, project, now=now)

    @staticmethod
    def calculate_cpi_stability_rule(progress_pct: float, cpi: float) -> Dict[str, Any]:
        return calculate_cpi_stability_rule(progress_pct, cpi)

    @staticmethod
    def evaluate_remaining_investment_viability(
        bac: float,
        ac: float,
        ev: float,
        expected_benefits_npv: float,
        cpi_floor: float = 0.70,
    ) -> Dict[str, Any]:
        return evaluate_remaining_investment_viability(
            bac, ac, ev, expected_benefits_npv, cpi_floor=cpi_floor
        )

    @staticmethod
    def calculate_early_warning_sentinel(cpi: float, spi: float) -> Dict[str, Any]:
        return calculate_early_warning_sentinel(cpi, spi)

    @staticmethod
    def compute_project_reserves_breakdown(
        db: Session, project: Project, bac: Optional[float] = None
    ) -> Dict[str, Any]:
        return compute_project_reserves_breakdown(db, project, bac=bac)

    @staticmethod
    def calculate_reserve_burn_index(contingency_reserve: float, cv: float) -> Dict[str, Any]:
        return calculate_reserve_burn_index(contingency_reserve, cv)

    @staticmethod
    def evaluate_control_accounts_concentration(
        components_metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return evaluate_control_accounts_concentration(components_metrics)

    @staticmethod
    def evaluate_work_package_efficiency(
        estimated_hours: float,
        actual_hours: float,
        planned_cost: float,
        actual_cost: float,
        physical_progress_pct: float,
    ) -> Dict[str, Any]:
        return evaluate_work_package_efficiency(
            estimated_hours, actual_hours, planned_cost, actual_cost, physical_progress_pct
        )

    @staticmethod
    def generate_curve_s_data(
        db: Session, project: Project, points_count: int = 8
    ) -> List[Dict[str, Any]]:
        return generate_curve_s_data(db, project, points_count=points_count)

    @staticmethod
    def analyze_s_curve_velocity(points: List[Dict[str, Any]]) -> Dict[str, Any]:
        return analyze_s_curve_velocity(points)

    @staticmethod
    def evaluate_ieac_forecast_spread(
        ieac_cpi: float,
        ieac_composite: float,
        bac: float,
    ) -> Dict[str, Any]:
        return evaluate_ieac_forecast_spread(ieac_cpi, ieac_composite, bac)

    @staticmethod
    def predict_schedule_slippage_days(
        planned_duration_days: float,
        spi_t: float,
    ) -> Dict[str, Any]:
        return predict_schedule_slippage_days(planned_duration_days, spi_t)

    @staticmethod
    def evaluate_wbs_scope_coverage(
        total_tasks: int,
        unassigned_tasks: int,
        components_count: int,
    ) -> Dict[str, Any]:
        return evaluate_wbs_scope_coverage(total_tasks, unassigned_tasks, components_count)

    @staticmethod
    def calculate_pert_three_point_estimate(
        optimistic: float,
        most_likely: float,
        pessimistic: float,
    ) -> Dict[str, Any]:
        return calculate_pert_three_point_estimate(optimistic, most_likely, pessimistic)

    @staticmethod
    def evaluate_contingency_reserve_burn_alignment(
        contingency_allocated: float,
        contingency_consumed: float,
        percent_complete: float,
    ) -> Dict[str, Any]:
        return evaluate_contingency_reserve_burn_alignment(
            contingency_allocated, contingency_consumed, percent_complete
        )

    @staticmethod
    def evaluate_cost_schedule_index_csi(
        cpi: float | None,
        spi: float | None,
        percent_complete: float = 0.0,
    ) -> dict[str, Any]:
        return evaluate_cost_schedule_index_csi(cpi, spi, percent_complete)

    @staticmethod
    def evaluate_variance_at_completion_alert(
        bac: float,
        eac: float,
        management_reserve: float = 0.0,
    ) -> dict[str, Any]:
        return evaluate_variance_at_completion_alert(bac, eac, management_reserve)

    @staticmethod
    def evaluate_etc_forecasting_method_posture(
        bac: float | int | None,
        ev: float | int | None,
        ac: float | int | None,
        cpi: float | int | None = None,
        spi: float | int | None = None,
    ) -> dict[str, Any]:
        return evaluate_etc_forecasting_method_posture(bac, ev, ac, cpi=cpi, spi=spi)

    @staticmethod
    def evaluate_funding_limit_reconciliation(
        planned_cumulative_spend: float | int | None,
        actual_cumulative_spend: float | int | None,
        periodic_funding_cap: float | int | None,
        management_reserve: float | int | None = 0.0,
    ) -> dict[str, Any]:
        return evaluate_funding_limit_reconciliation(
            planned_cumulative_spend,
            actual_cumulative_spend,
            periodic_funding_cap,
            management_reserve=management_reserve,
        )

    @staticmethod
    def evaluate_funding_limit_periods_reconciliation(
        periods: Optional[List[Dict[str, Any]]] = None,
        max_utilization_buffer_pct: float = 95.0,
    ) -> Dict[str, Any]:
        return evaluate_funding_limit_periods_reconciliation(
            periods,
            max_utilization_buffer_pct=max_utilization_buffer_pct,
        )

    @staticmethod
    def evaluate_cpi_trend_degradation(
        cpi_series: list[float | int] | None,
    ) -> dict[str, Any]:
        return evaluate_cpi_trend_degradation(cpi_series)

    @staticmethod
    def evaluate_rebaselining_otb_threshold(
        bac: float,
        ac: float,
        ev: float,
        approved_change_delta: float = 0.0,
        tcpi_bac_ceiling: float = 1.20,
    ) -> Dict[str, Any]:
        return evaluate_rebaselining_otb_threshold(
            bac,
            ac,
            ev,
            approved_change_delta=approved_change_delta,
            tcpi_bac_ceiling=tcpi_bac_ceiling,
        )

    @staticmethod
    def evaluate_management_reserve_release_governance(
        bac: float,
        management_reserve_initial: float,
        mr_releases: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return evaluate_management_reserve_release_governance(
            bac, management_reserve_initial, mr_releases=mr_releases
        )

    @staticmethod
    def evaluate_control_account_variance_masking(
        work_packages: Optional[List[Dict[str, Any]]],
        masking_threshold_pct: float = 15.0,
    ) -> Dict[str, Any]:
        return evaluate_control_account_variance_masking(
            work_packages, masking_threshold_pct=masking_threshold_pct
        )

    @staticmethod
    def evaluate_tcpi_recovery_feasibility(
        bac: float = 0.0,
        ev: float = 0.0,
        ac: float = 0.0,
        eac: float | None = None,
        max_feasible_tcpi: float = 1.10,
        max_efficiency_jump: float = 0.15,
    ) -> dict[str, Any]:
        return evaluate_tcpi_recovery_feasibility(
            bac,
            ev,
            ac,
            eac=eac,
            max_feasible_tcpi=max_feasible_tcpi,
            max_efficiency_jump=max_efficiency_jump,
        )

    @staticmethod
    def evaluate_earned_schedule_performance(
        *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        return evaluate_earned_schedule_performance(*args, **kwargs)


    @staticmethod
    def build_project_execution_matrix(
        db: Session, project: Project, now: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        return build_project_execution_matrix(db, project, now=now)


def evaluate_control_account_variance_masking(
    work_packages: Optional[List[Dict[str, Any]]],
    masking_threshold_pct: float = 15.0,
) -> Dict[str, Any]:
    """Detecta el fenómeno de enmascaramiento de variaciones (Variance Masking) en Cuentas de Control según PMI PMBOK §7.4."""
    packages = [wp for wp in (work_packages or []) if isinstance(wp, dict)]
    total_packages = len(packages)

    try:
        threshold_pct = max(0.0, float(masking_threshold_pct or 15.0))
    except (TypeError, ValueError):
        threshold_pct = 15.0

    net_cv_raw = 0.0
    gross_negative_raw = 0.0
    gross_positive_raw = 0.0
    severely_overrun_package_ids: List[str] = []

    for idx, wp in enumerate(packages, start=1):
        raw_id = wp.get("id") if wp.get("id") is not None else wp.get("code")
        wp_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"WP-{idx}"
        )

        try:
            ev = float(wp.get("ev") or 0.0)
        except (TypeError, ValueError):
            ev = 0.0
        try:
            ac = float(wp.get("ac") or 0.0)
        except (TypeError, ValueError):
            ac = 0.0

        raw_bac = wp.get("bac")
        raw_pv = wp.get("pv")
        try:
            ref_budget = float(raw_bac if raw_bac is not None else (raw_pv or 0.0))
        except (TypeError, ValueError):
            ref_budget = 0.0

        cv = ev - ac
        if ref_budget > 0.0:
            cv_pct = (cv / ref_budget) * 100.0
        else:
            cv_pct = -100.0 if cv < 0.0 else 0.0

        net_cv_raw += cv
        if cv < 0.0:
            gross_negative_raw += abs(cv)
            if abs(cv_pct) >= threshold_pct:
                severely_overrun_package_ids.append(wp_id)
        elif cv > 0.0:
            gross_positive_raw += cv

    net_control_account_cv = round(net_cv_raw, 2)
    gross_negative_cv = round(gross_negative_raw, 2)
    gross_positive_cv = round(gross_positive_raw, 2)

    is_variance_masked = bool(
        len(severely_overrun_package_ids) > 0
        and gross_positive_cv > 0.0
        and abs(net_control_account_cv) < gross_negative_cv * 0.5
    )

    recommendations: List[str] = []
    if total_packages == 0:
        masking_posture = "NO_WORK_PACKAGES"
        recommendations.append(
            "Desglosar la Cuenta de Control en paquetes de trabajo con métricas BAC/PV, EV y AC para auditar variaciones (PMBOK §7.4)."
        )
    elif is_variance_masked:
        masking_posture = "HIDDEN_VARIANCE_MASKING_DETECTED"
        recommendations.append(
            f"Las variaciones positivas (${gross_positive_cv:,.2f}) están ocultando sobrecostos severos (${gross_negative_cv:,.2f}) en los paquetes {', '.join(severely_overrun_package_ids)}. Prohibir compensación cruzada sin solicitud de cambio CCB y auditar paquetes deficitarios individualmente (PMBOK §7.4)."
        )
    elif len(severely_overrun_package_ids) > 0:
        masking_posture = "UNMASKED_PACKAGE_OVERRUN"
        recommendations.append(
            f"Ejecutar análisis de causa raíz y plan de acción correctiva sobre los paquetes con sobrecosto severo ({', '.join(severely_overrun_package_ids)}) conforme a PMBOK §7.4."
        )
    else:
        masking_posture = "UNIFORM_CONTROL_ACCOUNT_HEALTH"
        recommendations.append(
            "Cuenta de Control sin sobrecostos severos ni compensaciones ocultas entre paquetes de trabajo (PMBOK §7.4)."
        )

    return {
        "total_packages": total_packages,
        "net_control_account_cv": net_control_account_cv,
        "gross_negative_cv": gross_negative_cv,
        "gross_positive_cv": gross_positive_cv,
        "severely_overrun_package_ids": severely_overrun_package_ids,
        "is_variance_masked": is_variance_masked,
        "masking_posture": masking_posture,
        "recommendations": recommendations,
    }


_LEGACY_ES_UNSET = object()


def evaluate_earned_schedule_performance(
    earned_value: float = 0.0,
    actual_time_periods: float = 0.0,
    cumulative_pv_curve: list[float] | None = None,
    *,
    planned_value_curve: Any = _LEGACY_ES_UNSET,
    planned_duration_periods: Optional[float] = None,
) -> dict[str, Any]:
    """Evalúa el Cronograma Ganado (Earned Schedule - ES), SPI(t) y SV(t) proyectando EV sobre la curva acumulada de PV según PMI Practice Standard for EVM y PMBOK §7.4."""
    if planned_value_curve is not _LEGACY_ES_UNSET:
        curve: List[float] = []
        if isinstance(planned_value_curve, list):
            for val in planned_value_curve:
                if isinstance(val, bool) or val is None:
                    continue
                try:
                    num = float(val)
                except (TypeError, ValueError):
                    continue
                if num >= 0.0:
                    curve.append(num)

        try:
            at = float(actual_time_periods or 0.0)
        except (TypeError, ValueError):
            at = 0.0

        if not curve or curve[-1] <= 0.0 or at <= 0.0:
            return {
                "earned_schedule": 0.0,
                "actual_time_periods": max(0.0, round(at, 2)),
                "sv_t": 0.0,
                "spi_t": 1.0,
                "eac_t": 0.0,
                "is_on_schedule": True,
                "schedule_posture": "INSUFFICIENT_SCHEDULE_CURVE",
            }

        try:
            pd = (
                float(planned_duration_periods)
                if (
                    planned_duration_periods is not None
                    and float(planned_duration_periods) > 0.0
                )
                else float(len(curve))
            )
        except (TypeError, ValueError):
            pd = float(len(curve))

        try:
            raw_ev = float(earned_value or 0.0)
        except (TypeError, ValueError):
            raw_ev = 0.0
        ev = max(0.0, min(raw_ev, curve[-1]))

        pv_points = [0.0] + curve
        if ev >= pv_points[-1]:
            es = float(len(curve))
        elif ev <= 0.0:
            es = 0.0
        else:
            c_idx = 0
            for idx in range(len(curve)):
                if pv_points[idx] <= ev < pv_points[idx + 1]:
                    c_idx = idx
            delta_pv = pv_points[c_idx + 1] - pv_points[c_idx]
            fraction = (
                ((ev - pv_points[c_idx]) / delta_pv) if delta_pv > 0.0 else 0.0
            )
            es = float(c_idx) + fraction

        sv_t = es - at
        spi_t = (es / at) if at > 0.0 else 1.0
        eac_t = (pd / spi_t) if spi_t > 0.0 else pd

        es_round = round(es, 2)
        at_round = round(at, 2)
        sv_t_round = round(sv_t, 2)
        spi_t_round = round(spi_t, 2)
        eac_t_round = round(eac_t, 2)

        is_on_schedule = bool(spi_t_round >= 0.95)
        if spi_t_round < 0.85:
            schedule_posture = "CRITICAL_SCHEDULE_SLIPPAGE"
        elif spi_t_round < 0.95:
            schedule_posture = "MODERATE_SCHEDULE_DELAY"
        else:
            schedule_posture = "ON_OR_AHEAD_OF_SCHEDULE"

        return {
            "earned_schedule": es_round,
            "actual_time_periods": at_round,
            "sv_t": sv_t_round,
            "spi_t": spi_t_round,
            "eac_t": eac_t_round,
            "is_on_schedule": is_on_schedule,
            "schedule_posture": schedule_posture,
        }

    curve_vals: list[float] = []
    if isinstance(cumulative_pv_curve, list):
        for v in cumulative_pv_curve:
            if isinstance(v, bool) or v is None:
                continue
            try:
                curve_vals.append(max(0.0, float(v)))
            except (TypeError, ValueError):
                continue

    try:
        ev_val = max(0.0, float(earned_value or 0.0))
    except (TypeError, ValueError):
        ev_val = 0.0
    try:
        at_val = max(0.0, float(actual_time_periods or 0.0))
    except (TypeError, ValueError):
        at_val = 0.0

    planned_duration = len(curve_vals)
    if not curve_vals or at_val <= 0.0:
        return {
            "earned_schedule": 0.0,
            "actual_time_periods": round(at_val, 4),
            "sv_time": 0.0,
            "spi_time": 0.0,
            "planned_duration": planned_duration,
            "estimated_duration_at_completion": 0.0,
            "is_on_time_trajectory": False,
            "es_posture": "INSUFFICIENT_PV_BASELINE_CURVE",
        }

    pts = [0.0] + curve_vals
    if ev_val >= pts[-1] and pts[-1] > 0.0:
        es = float(len(curve_vals))
    else:
        c = 0
        for idx in range(len(curve_vals)):
            if pts[idx] <= ev_val:
                c = idx
        delta_pv = pts[c + 1] - pts[c]
        fraction = ((ev_val - pts[c]) / delta_pv) if delta_pv > 1e-9 else 0.0
        es = float(c) + min(1.0, max(0.0, fraction))

    sv_time = round(es - at_val, 4)
    spi_time = round(es / at_val, 4)
    estimated_duration_at_completion = (
        round(planned_duration / spi_time, 2) if spi_time > 1e-6 else 0.0
    )
    is_on_time_trajectory = bool(spi_time >= 0.95)

    if spi_time < 0.85:
        es_posture = "CRITICAL_SCHEDULE_SLIPPAGE"
    elif spi_time < 0.95:
        es_posture = "MODERATE_SCHEDULE_DELAY"
    elif spi_time <= 1.05:
        es_posture = "ON_TIME_EARNED_SCHEDULE"
    else:
        es_posture = "AHEAD_OF_PLANNED_SCHEDULE"

    return {
        "earned_schedule": round(es, 4),
        "actual_time_periods": round(at_val, 4),
        "sv_time": sv_time,
        "spi_time": spi_time,
        "planned_duration": planned_duration,
        "estimated_duration_at_completion": estimated_duration_at_completion,
        "is_on_time_trajectory": is_on_time_trajectory,
        "es_posture": es_posture,
    }



def evaluate_burn_rate_runway_sustainability(
    bac: float,
    actual_cost: float,
    elapsed_periods: float,
    remaining_periods: float,
    management_reserve: float = 0.0,
) -> Dict[str, Any]:
    """Evalúa la sostenibilidad de la tasa de consumo (Burn-Rate) y la pista presupuestaria restante (Runway) según PMI PMBOK §7.4."""
    try:
        bac_val = max(0.0, float(bac or 0.0))
    except (TypeError, ValueError):
        bac_val = 0.0
    try:
        ac_val = max(0.0, float(actual_cost or 0.0))
    except (TypeError, ValueError):
        ac_val = 0.0
    try:
        elapsed_val = max(0.0, float(elapsed_periods or 0.0))
    except (TypeError, ValueError):
        elapsed_val = 0.0
    try:
        rem_periods_val = max(0.0, float(remaining_periods or 0.0))
    except (TypeError, ValueError):
        rem_periods_val = 0.0
    try:
        mr_val = max(0.0, float(management_reserve or 0.0))
    except (TypeError, ValueError):
        mr_val = 0.0

    if bac_val <= 0.0 or elapsed_val <= 0.0:
        return {
            "actual_burn_rate": 0.0,
            "sustainable_burn_rate": 0.0,
            "budget_runway_periods": 0.0,
            "total_funds_runway_periods": 0.0,
            "runway_gap_periods": 0.0,
            "is_sustainable": True,
            "burn_posture": "INSUFFICIENT_BURN_DATA",
        }

    remaining_bac = max(0.0, bac_val - ac_val)
    remaining_total_funds = max(0.0, bac_val + mr_val - ac_val)
    actual_burn_rate = ac_val / elapsed_val
    sustainable_burn_rate = (
        (remaining_bac / rem_periods_val) if rem_periods_val > 0.0 else remaining_bac
    )
    budget_runway_periods = (
        (remaining_bac / actual_burn_rate)
        if actual_burn_rate > 0.0
        else rem_periods_val
    )
    total_funds_runway_periods = (
        (remaining_total_funds / actual_burn_rate)
        if actual_burn_rate > 0.0
        else rem_periods_val
    )
    runway_gap_periods = budget_runway_periods - rem_periods_val

    actual_burn_rate_round = round(actual_burn_rate, 2)
    sustainable_burn_rate_round = round(sustainable_burn_rate, 2)
    budget_runway_periods_round = round(budget_runway_periods, 2)
    total_funds_runway_periods_round = round(total_funds_runway_periods, 2)
    runway_gap_periods_round = round(runway_gap_periods, 2)

    is_sustainable = bool(
        ac_val <= bac_val
        and (
            rem_periods_val == 0.0
            or budget_runway_periods + 1e-9 >= rem_periods_val
        )
    )

    if ac_val >= bac_val:
        burn_posture = "BUDGET_EXHAUSTED"
    elif (
        rem_periods_val > 0.0
        and total_funds_runway_periods + 1e-9 < rem_periods_val
    ):
        burn_posture = "RUNWAY_SHORTFALL_BEYOND_RESERVES"
    elif (
        rem_periods_val > 0.0
        and budget_runway_periods + 1e-9 < rem_periods_val <= total_funds_runway_periods + 1e-9
    ):
        burn_posture = "RUNWAY_REQUIRES_MANAGEMENT_RESERVE"
    else:
        burn_posture = "SUSTAINABLE_BURN_RATE_RUNWAY"

    return {
        "actual_burn_rate": actual_burn_rate_round,
        "sustainable_burn_rate": sustainable_burn_rate_round,
        "budget_runway_periods": budget_runway_periods_round,
        "total_funds_runway_periods": total_funds_runway_periods_round,
        "runway_gap_periods": runway_gap_periods_round,
        "is_sustainable": is_sustainable,
        "burn_posture": burn_posture,
    }


ProjectEVMService.evaluate_burn_rate_runway_sustainability = staticmethod(
    evaluate_burn_rate_runway_sustainability
)


def evaluate_cpi_spi_stability_window(
    snapshots: list[dict[str, Any]] | None = None,
    max_band_width: float = 0.10,
    max_period_swing: float = 0.15,
) -> dict[str, Any]:
    """Audita la estabilidad de ventana de los índices CPI y SPI y saltos bruscos período a período según PMI PMBOK §7.4."""
    items = [item for item in (snapshots or []) if isinstance(item, dict)]

    try:
        band_limit = float(max_band_width)
    except (TypeError, ValueError):
        band_limit = 0.10
    try:
        swing_limit = float(max_period_swing)
    except (TypeError, ValueError):
        swing_limit = 0.15

    def _positive_float(val: Any) -> Optional[float]:
        if val is None or isinstance(val, bool):
            return None
        try:
            num = float(val)
        except (TypeError, ValueError):
            return None
        return num if num > 0.0 else None

    evaluated_snapshots_count = 0
    cpi_values: list[float] = []
    spi_values: list[float] = []
    volatile_period_ids: list[str] = []
    max_swing = 0.0
    prev_cpi: Optional[float] = None
    prev_spi: Optional[float] = None

    for idx, item in enumerate(items, start=1):
        period_id = (
            str(
                item.get("period")
                or item.get("snapshot_id")
                or item.get("id")
                or item.get("label")
                or ""
            ).strip()
            or f"SNAP-{idx}"
        )
        raw_cpi = (
            item.get("cpi")
            if item.get("cpi") is not None
            else item.get("cost_performance_index")
        )
        raw_spi = (
            item.get("spi")
            if item.get("spi") is not None
            else item.get("schedule_performance_index")
        )
        cpi_curr = _positive_float(raw_cpi)
        spi_curr = _positive_float(raw_spi)

        if cpi_curr is None and spi_curr is None:
            continue

        evaluated_snapshots_count += 1
        if cpi_curr is not None:
            cpi_values.append(cpi_curr)
        if spi_curr is not None:
            spi_values.append(spi_curr)

        is_volatile = False
        if prev_cpi is not None and cpi_curr is not None:
            cpi_swing = abs(cpi_curr - prev_cpi)
            if cpi_swing > max_swing:
                max_swing = cpi_swing
            if cpi_swing > swing_limit + 1e-9:
                is_volatile = True
        if prev_spi is not None and spi_curr is not None:
            spi_swing = abs(spi_curr - prev_spi)
            if spi_swing > max_swing:
                max_swing = spi_swing
            if spi_swing > swing_limit + 1e-9:
                is_volatile = True

        if is_volatile:
            volatile_period_ids.append(period_id)

        if cpi_curr is not None:
            prev_cpi = cpi_curr
        if spi_curr is not None:
            prev_spi = spi_curr

    if evaluated_snapshots_count == 0:
        return {
            "evaluated_snapshots_count": 0,
            "cpi_spread": 0.0,
            "spi_spread": 0.0,
            "max_observed_swing": 0.0,
            "volatile_period_ids": [],
            "is_index_stable": True,
            "stability_posture": "NO_SNAPSHOTS_EVALUATED",
        }

    cpi_spread = (
        round(max(cpi_values) - min(cpi_values), 4)
        if len(cpi_values) >= 2
        else 0.0
    )
    spi_spread = (
        round(max(spi_values) - min(spi_values), 4)
        if len(spi_values) >= 2
        else 0.0
    )
    max_observed_swing = (
        round(max_swing, 4) if evaluated_snapshots_count >= 2 else 0.0
    )

    is_index_stable = bool(
        evaluated_snapshots_count > 0
        and len(volatile_period_ids) == 0
        and cpi_spread <= band_limit + 1e-9
        and spi_spread <= band_limit + 1e-9
    )

    if len(volatile_period_ids) > 0:
        stability_posture = "VOLATILE_PERIOD_SWING_ALERT"
    elif cpi_spread > band_limit + 1e-9 or spi_spread > band_limit + 1e-9:
        stability_posture = "WIDE_INDEX_DRIFT_BAND"
    else:
        stability_posture = "STABLE_EVM_PERFORMANCE_WINDOW"

    return {
        "evaluated_snapshots_count": evaluated_snapshots_count,
        "cpi_spread": cpi_spread,
        "spi_spread": spi_spread,
        "max_observed_swing": max_observed_swing,
        "volatile_period_ids": volatile_period_ids,
        "is_index_stable": is_index_stable,
        "stability_posture": stability_posture,
    }


ProjectEVMService.evaluate_cpi_spi_stability_window = staticmethod(
    evaluate_cpi_spi_stability_window
)


def evaluate_reserve_drawdown_velocity(
    initial_contingency_reserve: float = 0.0,
    contingency_reserve_consumed: float = 0.0,
    percent_complete_pct: float = 0.0,
    management_reserve_used: float = 0.0,
    approved_mr_change_requests_count: int = 0,
    max_burn_velocity_ratio: float = 1.25,
) -> dict[str, Any]:
    """Evalúa la velocidad de consumo (Drawdown Velocity) de reservas de contingencia y gestión según PMI PMBOK §7.4.2.3."""

    def _nonneg_float(val: Any) -> float:
        if val is None or isinstance(val, bool):
            return 0.0
        try:
            return max(0.0, float(val))
        except (TypeError, ValueError):
            return 0.0

    init_cont = _nonneg_float(initial_contingency_reserve)
    used_cont = _nonneg_float(contingency_reserve_consumed)
    pct_comp = _nonneg_float(percent_complete_pct)
    mr_used = _nonneg_float(management_reserve_used)
    try:
        mr_cr_count = int(approved_mr_change_requests_count or 0)
    except (TypeError, ValueError):
        mr_cr_count = 0
    try:
        max_ratio = float(max_burn_velocity_ratio)
    except (TypeError, ValueError):
        max_ratio = 1.25

    if init_cont > 0.0:
        contingency_consumed_pct = round((used_cont / init_cont) * 100.0, 2)
    else:
        contingency_consumed_pct = 100.0 if used_cont > 0.0 else 0.0

    remaining_contingency_reserve = round(max(0.0, init_cont - used_cont), 2)

    if init_cont <= 0.0 and used_cont <= 0.0:
        burn_velocity_ratio = 0.0
    elif pct_comp <= 0.0:
        burn_velocity_ratio = (
            round(contingency_consumed_pct, 4)
            if contingency_consumed_pct > 0.0
            else 0.0
        )
    else:
        burn_velocity_ratio = round(contingency_consumed_pct / pct_comp, 4)

    has_unapproved_mr_drawdown = bool(mr_used > 1e-9 and mr_cr_count <= 0)
    is_contingency_overburned = bool(
        used_cont > init_cont + 1e-9 or burn_velocity_ratio > max_ratio + 1e-9
    )
    is_reserve_healthy = bool(
        not has_unapproved_mr_drawdown and not is_contingency_overburned
    )

    if init_cont <= 0.0 and used_cont <= 0.0 and mr_used <= 0.0:
        reserve_posture = "NO_RESERVE_CONFIGURED"
    elif has_unapproved_mr_drawdown:
        reserve_posture = "UNAPPROVED_MANAGEMENT_RESERVE_DRAWDOWN"
    elif (
        init_cont > 0.0 and used_cont >= init_cont - 1e-9
    ) or used_cont > init_cont:
        reserve_posture = "CONTINGENCY_RESERVE_EXHAUSTED"
    elif is_contingency_overburned:
        reserve_posture = "ACCELERATED_RESERVE_BURN_WARNING"
    else:
        reserve_posture = "PROPORTIONAL_RESERVE_DRAWDOWN"

    return {
        "contingency_consumed_pct": contingency_consumed_pct,
        "remaining_contingency_reserve": remaining_contingency_reserve,
        "burn_velocity_ratio": burn_velocity_ratio,
        "has_unapproved_mr_drawdown": has_unapproved_mr_drawdown,
        "is_contingency_overburned": is_contingency_overburned,
        "is_reserve_healthy": is_reserve_healthy,
        "reserve_posture": reserve_posture,
    }


ProjectEVMService.evaluate_reserve_drawdown_velocity = staticmethod(
    evaluate_reserve_drawdown_velocity
)


def audit_pmb_undistributed_budget_reconciliation(
    bac: float = 0.0,
    control_accounts_total: float = 0.0,
    undistributed_budget: float = 0.0,
    max_ub_share_pct: float = 10.0,
    tolerance: float = 1.0,
) -> dict[str, Any]:
    """Audita la reconciliación de la Línea Base de Medición del Desempeño (PMB = Control Accounts + UB) según PMI PMBOK §7.3 y §7.4."""

    def _to_float(val: Any, default: float = 0.0) -> float:
        if val is None or isinstance(val, bool):
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    bac_val = _to_float(bac, 0.0)
    ca_val = _to_float(control_accounts_total, 0.0)
    ub_val = _to_float(undistributed_budget, 0.0)
    max_ub_pct = _to_float(max_ub_share_pct, 10.0)
    tol_val = _to_float(tolerance, 1.0)

    if abs(bac_val) <= 1e-9 and abs(ca_val) <= 1e-9 and abs(ub_val) <= 1e-9:
        return {
            "allocated_pmb_total": 0.0,
            "reconciliation_discrepancy": 0.0,
            "ub_share_pct": 0.0,
            "has_negative_bucket": False,
            "is_pmb_reconciled": True,
            "pmb_posture": "NO_PMB_CONFIGURED",
        }

    allocated_pmb_total = round(ca_val + ub_val, 2)
    reconciliation_discrepancy = round(bac_val - allocated_pmb_total, 2)
    if bac_val > 0.0:
        ub_share_pct = round((max(0.0, ub_val) / bac_val) * 100.0, 2)
    else:
        ub_share_pct = 100.0 if ub_val > 0.0 else 0.0

    has_negative_bucket = bool(
        bac_val < -1e-9 or ca_val < -1e-9 or ub_val < -1e-9
    )
    is_discrepancy_within_tolerance = bool(
        abs(reconciliation_discrepancy) <= tol_val + 1e-9
    )
    is_ub_within_threshold = bool(ub_share_pct <= max_ub_pct + 1e-9)
    is_pmb_reconciled = bool(
        not has_negative_bucket
        and is_discrepancy_within_tolerance
        and is_ub_within_threshold
    )

    if has_negative_bucket:
        pmb_posture = "NEGATIVE_BUDGET_BUCKET_ERROR"
    elif not is_discrepancy_within_tolerance:
        pmb_posture = "PMB_BAC_RECONCILIATION_MISMATCH"
    elif not is_ub_within_threshold:
        pmb_posture = "EXCESSIVE_UNDISTRIBUTED_BUDGET_HOLDING"
    else:
        pmb_posture = "RECONCILED_PMB_BASELINE"

    return {
        "allocated_pmb_total": allocated_pmb_total,
        "reconciliation_discrepancy": reconciliation_discrepancy,
        "ub_share_pct": ub_share_pct,
        "has_negative_bucket": has_negative_bucket,
        "is_pmb_reconciled": is_pmb_reconciled,
        "pmb_posture": pmb_posture,
    }


ProjectEVMService.audit_pmb_undistributed_budget_reconciliation = staticmethod(
    audit_pmb_undistributed_budget_reconciliation
)

ProjectEVMService.audit_work_package_evmt_governance = staticmethod(
    audit_work_package_evmt_governance
)


def audit_eac_forecast_optimism_bias(
    bac: float = 0.0,
    ev: float = 0.0,
    ac: float = 0.0,
    pv: float = 0.0,
    manager_bottom_up_eac: float | None = None,
    max_optimism_gap_pct: float = 10.0,
) -> dict[str, Any]:
    """Audita el sesgo de optimismo gerencial y la divergencia entre pronósticos EAC independientes (PMBOK §7.4.2.2)."""
    try:
        bac_v = max(0.0, float(bac or 0.0))
    except (TypeError, ValueError):
        bac_v = 0.0
    try:
        ev_v = max(0.0, float(ev or 0.0))
    except (TypeError, ValueError):
        ev_v = 0.0
    try:
        ac_v = max(0.0, float(ac or 0.0))
    except (TypeError, ValueError):
        ac_v = 0.0
    try:
        pv_v = max(0.0, float(pv or 0.0))
    except (TypeError, ValueError):
        pv_v = 0.0

    if bac_v <= 0.0 or ev_v <= 0.0 or ac_v <= 0.0:
        try:
            mgr_fallback = round(float(manager_bottom_up_eac or 0.0), 2)
        except (TypeError, ValueError):
            mgr_fallback = 0.0
        return {
            "eac_atypical": 0.0,
            "eac_cpi": 0.0,
            "eac_composite": 0.0,
            "manager_eac": mgr_fallback,
            "optimism_gap_pct": 0.0,
            "is_forecast_credible": False,
            "forecast_posture": "INSUFFICIENT_EVM_DATA",
        }

    cpi = ev_v / ac_v
    spi = (ev_v / pv_v) if pv_v > 0.0 else 1.0
    rem_work = max(0.0, bac_v - ev_v)

    eac_atypical = round(ac_v + rem_work, 2)
    eac_cpi = round(bac_v / cpi, 2)
    composite_factor = cpi * spi
    eac_composite = (
        round(ac_v + (rem_work / composite_factor), 2)
        if composite_factor > 1e-6
        else eac_cpi
    )

    mgr_eac = (
        round(float(manager_bottom_up_eac), 2)
        if manager_bottom_up_eac is not None and float(manager_bottom_up_eac) > 0.0
        else eac_cpi
    )

    statistical_floor = max(eac_cpi, eac_composite) if cpi < 1.0 else eac_cpi
    optimism_gap_pct = (
        round(((statistical_floor - mgr_eac) / statistical_floor) * 100.0, 2)
        if statistical_floor > 0.0 and mgr_eac < statistical_floor
        else 0.0
    )

    violates_sunk_cost_floor = bool(mgr_eac < ac_v - 1e-6)
    has_optimism_bias = bool(optimism_gap_pct > float(max_optimism_gap_pct))
    is_forecast_credible = bool(
        not violates_sunk_cost_floor and not has_optimism_bias
    )

    if violates_sunk_cost_floor:
        forecast_posture = "UNREALISTIC_BELOW_ACTUAL_COST"
    elif has_optimism_bias:
        forecast_posture = "MANAGERIAL_OPTIMISM_BIAS_ALERT"
    elif mgr_eac >= statistical_floor:
        forecast_posture = "CONSERVATIVE_COMPOSITE_ALIGNED"
    else:
        forecast_posture = "CREDIBLE_EAC_FORECAST"

    return {
        "eac_atypical": eac_atypical,
        "eac_cpi": eac_cpi,
        "eac_composite": eac_composite,
        "manager_eac": mgr_eac,
        "optimism_gap_pct": optimism_gap_pct,
        "is_forecast_credible": is_forecast_credible,
        "forecast_posture": forecast_posture,
    }


def evaluate_management_reserve_ceiling_utilization(
    original_bac: float = 0.0,
    initial_management_reserve: float = 0.0,
    mr_drawdowns: list[dict[str, Any]] | None = None,
    current_eac: float = 0.0,
) -> dict[str, Any]:
    """Evalúa utilización de Reserva de Gestión (Management Reserve), ajuste de BAC y cumplimiento del techo presupuestal del proyecto según PMI PMBOK §7.3 y §7.4."""
    try:
        orig_bac = max(0.0, float(original_bac or 0.0))
    except (TypeError, ValueError):
        orig_bac = 0.0
    try:
        init_mr = max(0.0, float(initial_management_reserve or 0.0))
    except (TypeError, ValueError):
        init_mr = 0.0
    try:
        eac = max(0.0, float(current_eac or 0.0))
    except (TypeError, ValueError):
        eac = 0.0

    if orig_bac <= 0.0:
        return {
            "total_project_budget": 0.0,
            "current_bac": 0.0,
            "remaining_management_reserve": 0.0,
            "mr_utilization_pct": 0.0,
            "unauthorized_drawdown_ids": [],
            "exceeds_project_budget_ceiling": False,
            "is_mr_governance_sound": False,
            "mr_posture": "NO_COST_BASELINE",
        }

    total_drawn = 0.0
    unauthorized_drawdown_ids: list[str] = []

    for d in mr_drawdowns or []:
        if not isinstance(d, dict):
            continue
        dd_id = str(d.get("id") or d.get("drawdown_id") or "").strip()
        if not dd_id:
            continue
        try:
            amount = max(0.0, float(d.get("amount") or 0.0))
        except (TypeError, ValueError):
            amount = 0.0
        sponsor_approved = bool(d.get("sponsor_approved", False))
        total_drawn += amount
        if not sponsor_approved:
            unauthorized_drawdown_ids.append(dd_id)

    total_project_budget = round(orig_bac + init_mr, 2)
    current_bac = round(orig_bac + total_drawn, 2)
    remaining_mr = round(init_mr - total_drawn, 2)
    mr_utilization_pct = (
        round((total_drawn / init_mr) * 100.0, 2)
        if init_mr > 1e-6
        else (100.0 if total_drawn > 0 else 0.0)
    )
    exceeds_ceiling = bool(
        (total_drawn > init_mr + 1e-6) or (eac > total_project_budget + 1e-6)
    )
    is_mr_governance_sound = bool(
        len(unauthorized_drawdown_ids) == 0 and not exceeds_ceiling
    )

    if len(unauthorized_drawdown_ids) > 0:
        mr_posture = "UNAUTHORIZED_MANAGEMENT_RESERVE_DRAWDOWN"
    elif exceeds_ceiling:
        mr_posture = "PROJECT_BUDGET_CEILING_BREACHED"
    elif mr_utilization_pct > 75.0:
        mr_posture = "HIGH_MANAGEMENT_RESERVE_DEPLETION"
    else:
        mr_posture = "GOVERNED_MANAGEMENT_RESERVE_POSTURE"

    return {
        "total_project_budget": total_project_budget,
        "current_bac": current_bac,
        "remaining_management_reserve": remaining_mr,
        "mr_utilization_pct": mr_utilization_pct,
        "unauthorized_drawdown_ids": unauthorized_drawdown_ids,
        "exceeds_project_budget_ceiling": exceeds_ceiling,
        "is_mr_governance_sound": is_mr_governance_sound,
        "mr_posture": mr_posture,
    }


def evaluate_evm_funding_runway_exhaustion(
    *,
    total_authorized_funding: float,
    cumulative_actual_cost: float,
    periodic_ac_burn_series: Sequence[float] | None,
    remaining_schedule_periods: int,
    min_safety_margin_periods: float = 1.0,
) -> dict[str, Any]:
    """Evalúa la tasa de consumo financiero (AC burn-rate) frente a los períodos restantes de cronograma según PMI PMBOK §7.2 y §7.4."""
    auth_funding = float(total_authorized_funding or 0.0)
    cum_ac = float(cumulative_actual_cost or 0.0)
    rem_periods = int(remaining_schedule_periods or 0)
    safety_margin = float(min_safety_margin_periods or 0.0)

    remaining_funding = round(max(0.0, auth_funding - cum_ac), 2)
    is_overdrawn = cum_ac > auth_funding

    valid_burns: list[float] = []
    for val in periodic_ac_burn_series or []:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            f_val = float(val)
            if f_val > 0.0:
                valid_burns.append(f_val)

    if valid_burns:
        average_periodic_burn = round(sum(valid_burns) / len(valid_burns), 2)
        peak_periodic_burn = round(max(valid_burns), 2)
    else:
        average_periodic_burn = 0.0
        peak_periodic_burn = 0.0

    if average_periodic_burn > 0.0:
        estimated_runway_periods = round(
            remaining_funding / average_periodic_burn, 2
        )
    else:
        estimated_runway_periods = (
            float(rem_periods) if remaining_funding > 0.0 else 0.0
        )

    eff_rem_periods = float(max(0, rem_periods))
    runway_surplus_periods = round(
        estimated_runway_periods - eff_rem_periods, 2
    )

    if is_overdrawn or (remaining_funding == 0.0 and rem_periods > 0):
        runway_status = "EXHAUSTED"
    elif estimated_runway_periods < eff_rem_periods:
        runway_status = "SHORTFALL_RISK"
    elif runway_surplus_periods < safety_margin:
        runway_status = "TIGHT_RUNWAY"
    else:
        runway_status = "HEALTHY_RUNWAY"

    return {
        "remaining_funding": remaining_funding,
        "is_overdrawn": is_overdrawn,
        "average_periodic_burn": average_periodic_burn,
        "peak_periodic_burn": peak_periodic_burn,
        "estimated_runway_periods": estimated_runway_periods,
        "runway_surplus_periods": runway_surplus_periods,
        "runway_status": runway_status,
        "is_runway_sufficient": runway_status == "HEALTHY_RUNWAY",
    }


def evaluate_evm_joint_cost_schedule_index(
    *,
    cpi: float,
    spi: float,
    percent_complete: float,
    tcpi_bac: float = 1.0,
) -> dict[str, Any]:
    """Evalúa el Índice Compuesto Costo-Cronograma (CSI = CPI * SPI) y la factibilidad estadística de recuperación según PMI PMBOK §7.4.2.2."""
    f_cpi = float(cpi)
    f_spi = float(spi)
    f_pct = float(percent_complete)
    f_tcpi = float(tcpi_bac)

    csi = round(f_cpi * f_spi, 4)
    tradeoff_imbalance = round(abs(f_cpi - f_spi), 4)

    if csi >= 0.9:
        csi_zone = "GREEN"
    elif csi >= 0.8:
        csi_zone = "YELLOW"
    else:
        csi_zone = "RED"

    is_past_early_stabilization_point = f_pct >= 20.0
    requires_formal_rebaseline = bool(
        csi < 0.8
        or f_tcpi > 1.10
        or (is_past_early_stabilization_point and csi < 0.85)
    )
    is_jointly_healthy = bool(
        csi_zone == "GREEN" and not requires_formal_rebaseline
    )

    return {
        "csi": csi,
        "tradeoff_imbalance": tradeoff_imbalance,
        "csi_zone": csi_zone,
        "is_past_early_stabilization_point": is_past_early_stabilization_point,
        "requires_formal_rebaseline": requires_formal_rebaseline,
        "is_jointly_healthy": is_jointly_healthy,
    }


def evaluate_evm_earned_schedule_tspi_feasibility(
    metrics: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Evalúa el To-Complete Schedule Performance Index (TSPI) en Earned Schedule y la factibilidad de recuperación según PMI PMBOK §7.4 y Practice Standard for EVM."""
    invalid_result: dict[str, Any] = {
        "spi_t": 0.0,
        "sv_t_days": 0.0,
        "tspi_pd": 0.0,
        "tspi_ed": 0.0,
        "ieac_t_days": 0.0,
        "schedule_posture": "invalid_inputs",
        "is_recovery_feasible": False,
    }
    if not isinstance(metrics, Mapping):
        return invalid_result

    try:
        planned_duration_days = float(metrics.get("planned_duration_days", 0.0) or 0.0)
        actual_time_days = float(metrics.get("actual_time_days", 0.0) or 0.0)
        earned_schedule_days = float(metrics.get("earned_schedule_days", 0.0) or 0.0)
        deadline_extension_days = max(
            0.0, float(metrics.get("deadline_extension_days", 0.0) or 0.0)
        )
    except (TypeError, ValueError):
        return invalid_result

    if (
        planned_duration_days <= 0.0
        or actual_time_days < 0.0
        or earned_schedule_days < 0.0
    ):
        return invalid_result

    if actual_time_days > 0.0:
        spi_t = round(earned_schedule_days / actual_time_days, 4)
    else:
        spi_t = 1.0 if earned_schedule_days > 0.0 else 0.0

    sv_t_days = round(earned_schedule_days - actual_time_days, 2)
    remaining_work_days = max(0.0, planned_duration_days - earned_schedule_days)
    remaining_time_pd = planned_duration_days - actual_time_days

    if remaining_time_pd > 0.0:
        tspi_pd = round(remaining_work_days / remaining_time_pd, 4)
    else:
        tspi_pd = 0.0 if remaining_work_days == 0.0 else 999.0

    effective_deadline_days = planned_duration_days + deadline_extension_days
    remaining_time_ed = effective_deadline_days - actual_time_days

    if remaining_time_ed > 0.0:
        tspi_ed = round(remaining_work_days / remaining_time_ed, 4)
    else:
        tspi_ed = 0.0 if remaining_work_days == 0.0 else 999.0

    if spi_t > 0.0:
        ieac_t_days = round(planned_duration_days / spi_t, 2)
    else:
        ieac_t_days = round(effective_deadline_days * 2.0, 2)

    if remaining_work_days == 0.0:
        schedule_posture = "completed"
    elif tspi_pd <= 1.05 and spi_t >= 0.95:
        schedule_posture = "on_track"
    elif tspi_pd <= 1.10:
        schedule_posture = "recoverable_within_baseline"
    elif tspi_ed <= 1.10:
        schedule_posture = "recoverable_with_extension"
    else:
        schedule_posture = "unrecoverable_slippage"

    is_recovery_feasible = bool(
        schedule_posture
        in {
            "completed",
            "on_track",
            "recoverable_within_baseline",
            "recoverable_with_extension",
        }
    )

    return {
        "spi_t": spi_t,
        "sv_t_days": sv_t_days,
        "tspi_pd": tspi_pd,
        "tspi_ed": tspi_ed,
        "ieac_t_days": ieac_t_days,
        "schedule_posture": schedule_posture,
        "is_recovery_feasible": is_recovery_feasible,
    }


def evaluate_evm_vac_rebaseline_threshold(
    metrics: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Evalúa la Variación a la Conclusión (VAC = BAC - EAC), el porcentaje de sobrecosto proyectado y el umbral de re-baseline ante el CCB según PMI PMBOK §7.4."""
    invalid_result: dict[str, Any] = {
        "bac": 0.0,
        "eac": 0.0,
        "vac": 0.0,
        "vac_pct": 0.0,
        "tcpi_bac": 0.0,
        "rebaseline_status": "invalid_inputs",
        "requires_ccb_rebaseline": False,
    }
    if not isinstance(metrics, Mapping):
        return invalid_result

    try:
        bac = float(metrics.get("bac", 0.0) or 0.0)
        ev = float(metrics.get("ev", 0.0) or 0.0)
        ac = float(metrics.get("ac", 0.0) or 0.0)
        eac = float(metrics.get("eac", 0.0) or 0.0)
        raw_tol = metrics.get("tolerance_threshold_pct", 10.0)
        tolerance_threshold_pct = max(
            0.0, float(10.0 if raw_tol is None else raw_tol)
        )
    except (TypeError, ValueError):
        return invalid_result

    if bac <= 0.0 or ev < 0.0 or ac < 0.0 or eac <= 0.0:
        return invalid_result

    vac = round(bac - eac, 2)
    vac_pct = round((vac / bac) * 100.0, 2)
    remaining_work = max(0.0, bac - ev)
    remaining_funds_bac = bac - ac

    if remaining_funds_bac > 0.0:
        tcpi_bac = round(remaining_work / remaining_funds_bac, 4)
    else:
        tcpi_bac = 0.0 if remaining_work == 0.0 else 999.0

    overrun_pct = max(0.0, -vac_pct)
    if overrun_pct > tolerance_threshold_pct or tcpi_bac > 1.20:
        rebaseline_status = "ccb_rebaseline_required"
    elif overrun_pct <= tolerance_threshold_pct and tcpi_bac > 1.10:
        rebaseline_status = "watch_threshold"
    else:
        rebaseline_status = "within_tolerance"

    requires_ccb_rebaseline = bool(
        rebaseline_status == "ccb_rebaseline_required"
    )

    return {
        "bac": round(bac, 2),
        "eac": round(eac, 2),
        "vac": vac,
        "vac_pct": vac_pct,
        "tcpi_bac": tcpi_bac,
        "rebaseline_status": rebaseline_status,
        "requires_ccb_rebaseline": requires_ccb_rebaseline,
    }


ProjectEVMService.audit_eac_forecast_optimism_bias = staticmethod(
    audit_eac_forecast_optimism_bias
)
ProjectEVMService.evaluate_management_reserve_ceiling_utilization = staticmethod(
    evaluate_management_reserve_ceiling_utilization
)
ProjectEVMService.evaluate_evm_funding_runway_exhaustion = staticmethod(
    evaluate_evm_funding_runway_exhaustion
)
ProjectEVMService.evaluate_evm_joint_cost_schedule_index = staticmethod(
    evaluate_evm_joint_cost_schedule_index
)
ProjectEVMService.evaluate_evm_earned_schedule_tspi_feasibility = staticmethod(
    evaluate_evm_earned_schedule_tspi_feasibility
)
ProjectEVMService.evaluate_evm_vac_rebaseline_threshold = staticmethod(
    evaluate_evm_vac_rebaseline_threshold
)


__all__ = [
    "audit_work_package_evmt_governance",
    "evaluate_evm_to_complete_schedule_performance_index_tspi",
    "evaluate_tcpi_recovery_feasibility",
    "evaluate_funding_limit_periods_reconciliation",
    "evaluate_earned_schedule_performance",
    "evaluate_burn_rate_runway_sustainability",
    "evaluate_cpi_spi_stability_window",
    "evaluate_reserve_drawdown_velocity",
    "audit_pmb_undistributed_budget_reconciliation",
    "audit_eac_forecast_optimism_bias",
    "evaluate_management_reserve_ceiling_utilization",
    "evaluate_evm_funding_runway_exhaustion",
    "evaluate_evm_joint_cost_schedule_index",
    "evaluate_evm_earned_schedule_tspi_feasibility",
    "evaluate_evm_vac_rebaseline_threshold",
    "evaluate_evm_tcpi_eac_vs_bac_divergence",
    "audit_evm_accrual_method_inflation_bias",
    "evaluate_evm_critical_path_drag_decoupling",
    "evaluate_evm_undistributed_budget_and_planning_packages",
    "evaluate_evm_reserve_burn_vs_risk_exposure",
    "evaluate_evm_loe_masking_and_variance_distortion",
    "evaluate_evm_apportioned_effort_base_coherence",
    "evaluate_evm_retroactive_adjustment_and_negative_period_anomalies",
    "evaluate_evm_contract_budget_base_and_ub_reconciliation",
    "evaluate_evm_etc_bottom_up_vs_formulaic_divergence",
    "evaluate_evm_critical_path_drag_and_float_masking",
    "evaluate_evm_rolling_wave_planning_package_freeze_horizon",
    "evaluate_evm_loe_masking_and_discrete_variance_distortion",
    "evaluate_evm_retroactive_change_and_negative_period_anomaly",
    "evaluate_evm_subcontractor_flowdown_and_invoice_overbilling",
    "evaluate_evm_earning_rule_gaming_and_duration_split",
    "evaluate_evm_cost_schedule_index_compound_degradation",
    "evaluate_evm_undistributed_budget_and_planning_package_aging",
    "evaluate_evm_cost_variance_rate_vs_efficiency_decomposition",
    "evaluate_evm_contract_fee_and_point_of_total_assumption",
    "evaluate_evm_earned_schedule_eac_t_and_tspi",
    "evaluate_evm_loe_contamination_and_variance_masking",
    "evaluate_evm_funding_limit_reconciliation_and_liquidity",
    "evaluate_evm_subcontractor_retainage_and_progress_billing",
    "evaluate_evm_fx_currency_volatility_and_hedging_coverage",
    "evaluate_evm_time_and_materials_nte_and_rate_blend",
    "evaluate_evm_economic_price_adjustment_and_inflation_erosion",
    "evaluate_evm_capex_opex_classification_and_amortization",
    "evaluate_evm_learning_curve_cost_improvement_and_productivity",
    "evaluate_evm_milestone_payment_holdback_and_acceptance_gate",
    "evaluate_evm_value_engineering_target_costing_and_worth_index",
    "evaluate_evm_contingency_and_management_reserve_drawdown_governance",
    "evaluate_evm_sla_penalty_service_credits_and_earn_back",
    "evaluate_evm_cpif_share_ratio_and_point_of_total_assumption",
    "evaluate_evm_performance_bond_and_letter_of_credit_coverage",
    "evaluate_evm_fx_hedging_collar_and_currency_exposure",
    "evaluate_evm_time_and_materials_nte_ceiling_and_rate_card",
    "evaluate_evm_working_capital_cash_conversion_and_mobilization_advance",
    "evaluate_evm_liquidated_damages_cap_and_eot_relief",
    "evaluate_evm_epa_inflation_indexation_and_escalation_cap",
    "evaluate_evm_subcontractor_lien_waiver_and_flow_down",
    "evaluate_evm_capex_opex_software_capitalization_gate",
    "evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare",
    "evaluate_evm_cpaf_award_fee_pool_and_rollover_governance",
    "evaluate_evm_standby_demurrage_and_force_account_rates",
    "evaluate_evm_schedule_of_values_front_loading_and_stored_materials",
    "evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer",
    "evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus",
    "evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement",
    "evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate",
    "evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve",
    "evaluate_evm_economic_price_adjustment_epa_corridor_and_share",
    "evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi",
    "evaluate_evm_vecp_net_savings_and_contractor_share_split",
    "evaluate_evm_builders_risk_dsu_indemnity_and_subrogation_waiver",
    "evaluate_evm_prevailing_wage_wh347_payroll_and_restitution_withholding",
    "evaluate_evm_stored_materials_bonded_warehouse_and_title_transfer",
    "evaluate_evm_prompt_payment_act_flowdown_and_interest_penalty",
    "evaluate_evm_force_majeure_weather_days_and_eichleay_hooh_claim",
    "evaluate_evm_cardinal_change_and_cumulative_impact_leonard_loss",
    "evaluate_evm_differing_site_conditions_dsc_geotechnical_overrun",
    "evaluate_evm_termination_for_convenience_t4c_settlement_proposal",
    "evaluate_evm_acceleration_claim_overtime_inefficiency_and_shift_premium",
    "evaluate_evm_surety_performance_bond_t4d_takeover_and_overpayment",
    "evaluate_evm_davis_bacon_prevailing_wage_wh347_and_restitution",
    "evaluate_evm_vecp_far_52_248_shared_savings_and_development_cost_offset",
    "ProjectEVMService",
]


def evaluate_evm_tcpi_eac_vs_bac_divergence(
    metrics: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """PMBOK §7.4 — divergencia TCPI(BAC) vs TCPI(EAC) y realismo del EAC.

    - ``cpi`` = EV/AC (round 4; 1.0 si AC<=0 con EV>0; 0.0 si no).
    - ``tcpi_bac``/``tcpi_eac`` = trabajo restante sobre fondos restantes
      (round 4; 999.0 si fondos restantes <= 0 con trabajo pendiente).
    - Postura: ``completed``, ``unrealistic_eac`` (rem_eac <= 0, gap > 0.15
      o TCPI_EAC > 1.20), ``rebaselined_aligned`` (TCPI_BAC > 1.10 con
      TCPI_EAC <= 1.10 y gap <= 0.15) o ``baseline_achievable``.
    """
    if not isinstance(metrics, Mapping):
        return {
            "tcpi_bac": 0.0,
            "tcpi_eac": 0.0,
            "tcpi_spread": 0.0,
            "cpi": 0.0,
            "efficiency_gap_vs_cpi": 0.0,
            "divergence_posture": "invalid_inputs",
            "is_eac_realistic": False,
        }

    def _float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    bac = _float(metrics.get("bac", 0.0) or 0.0)
    ev = _float(metrics.get("ev", 0.0) or 0.0)
    ac = _float(metrics.get("ac", 0.0) or 0.0)
    eac = _float(metrics.get("eac", 0.0) or 0.0)

    if bac <= 0 or ev < 0 or ac < 0 or eac <= 0:
        return {
            "tcpi_bac": 0.0,
            "tcpi_eac": 0.0,
            "tcpi_spread": 0.0,
            "cpi": 0.0,
            "efficiency_gap_vs_cpi": 0.0,
            "divergence_posture": "invalid_inputs",
            "is_eac_realistic": False,
        }

    cpi = round(ev / ac, 4) if ac > 0 else (1.0 if ev > 0 else 0.0)
    remaining_work = max(0.0, bac - ev)
    rem_bac = bac - ac
    rem_eac = eac - ac

    tcpi_bac = (
        round(remaining_work / rem_bac, 4)
        if rem_bac > 0
        else (0.0 if remaining_work == 0 else 999.0)
    )
    tcpi_eac = (
        round(remaining_work / rem_eac, 4)
        if rem_eac > 0
        else (0.0 if remaining_work == 0 else 999.0)
    )
    tcpi_spread = round(abs(tcpi_bac - tcpi_eac), 4)
    efficiency_gap_vs_cpi = round(tcpi_eac - cpi, 4)

    if remaining_work == 0:
        divergence_posture = "completed"
    elif rem_eac <= 0 or efficiency_gap_vs_cpi > 0.15 or tcpi_eac > 1.20:
        divergence_posture = "unrealistic_eac"
    elif tcpi_bac > 1.10 and tcpi_eac <= 1.10 and efficiency_gap_vs_cpi <= 0.15:
        divergence_posture = "rebaselined_aligned"
    else:
        divergence_posture = "baseline_achievable"

    is_eac_realistic = bool(
        divergence_posture in {"completed", "rebaselined_aligned", "baseline_achievable"}
    )

    return {
        "tcpi_bac": tcpi_bac,
        "tcpi_eac": tcpi_eac,
        "tcpi_spread": tcpi_spread,
        "cpi": cpi,
        "efficiency_gap_vs_cpi": efficiency_gap_vs_cpi,
        "divergence_posture": divergence_posture,
        "is_eac_realistic": is_eac_realistic,
    }


ProjectEVMService.evaluate_evm_tcpi_eac_vs_bac_divergence = staticmethod(
    evaluate_evm_tcpi_eac_vs_bac_divergence
)


def audit_evm_accrual_method_inflation_bias(
    work_packages: Sequence[Mapping[str, Any]] | None,
    *,
    max_50_50_duration_days: float = 20.0,
) -> dict[str, Any]:
    """Audita el método de devengo de valor ganado (EVMT: 0/100, 50/50, weighted_milestones, percent_complete, level_of_effort) para prevenir sesgo de inflación en paquetes largos o sin evidencia objetiva según PMI PMBOK §7.3 y §7.4."""
    if (
        work_packages is None
        or isinstance(work_packages, (str, bytes, Mapping))
        or not isinstance(work_packages, Sequence)
    ):
        items: Sequence[Any] = []
    else:
        items = work_packages

    valid_methods = {
        "0_100",
        "50_50",
        "weighted_milestones",
        "percent_complete",
        "level_of_effort",
    }
    total_work_packages = 0
    invalid_method_wp_ids: list[str] = []
    long_duration_50_50_wp_ids: list[str] = []
    inflated_or_unsubstantiated_wp_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        wp_id = str(item.get("wp_id") or "").strip()
        if not wp_id:
            continue

        total_work_packages += 1
        accrual_method = str(item.get("accrual_method") or "").strip().lower()
        try:
            duration_days = max(0.0, float(item.get("duration_days", 0.0) or 0.0))
        except (TypeError, ValueError):
            duration_days = 0.0

        try:
            claimed_ev = max(0.0, float(item.get("claimed_ev", 0.0) or 0.0))
        except (TypeError, ValueError):
            claimed_ev = 0.0

        try:
            bac = max(0.0, float(item.get("bac", 0.0) or 0.0))
        except (TypeError, ValueError):
            bac = 0.0

        objective_evidence_attached = bool(
            item.get("objective_evidence_attached", False)
        )

        if accrual_method not in valid_methods:
            invalid_method_wp_ids.append(wp_id)

        if accrual_method == "50_50" and duration_days > float(
            max_50_50_duration_days
        ):
            long_duration_50_50_wp_ids.append(wp_id)

        if claimed_ev > bac or (
            accrual_method == "percent_complete"
            and claimed_ev > 0.0
            and not objective_evidence_attached
        ):
            inflated_or_unsubstantiated_wp_ids.append(wp_id)

    is_accrual_governance_sound = bool(
        total_work_packages > 0
        and not invalid_method_wp_ids
        and not long_duration_50_50_wp_ids
        and not inflated_or_unsubstantiated_wp_ids
    )

    return {
        "total_work_packages": total_work_packages,
        "invalid_method_wp_ids": invalid_method_wp_ids,
        "long_duration_50_50_wp_ids": long_duration_50_50_wp_ids,
        "inflated_or_unsubstantiated_wp_ids": inflated_or_unsubstantiated_wp_ids,
        "is_accrual_governance_sound": is_accrual_governance_sound,
    }


ProjectEVMService.audit_evm_accrual_method_inflation_bias = staticmethod(
    audit_evm_accrual_method_inflation_bias
)


def evaluate_evm_critical_path_drag_decoupling(
    spi: float,
    sv_amount: float,
    critical_path_slip_days: float = 0.0,
    critical_path_ev_share_pct: float = 100.0,
    non_critical_float_consumed_days: float = 0.0,
    max_acceptable_cp_slip_days: float = 0.0,
    min_cp_ev_share_pct: float = 40.0,
) -> dict[str, Any]:
    """Evalúa la divergencia entre SPI/SV y el atraso real de la Ruta Crítica (Critical Path Drag & SV Masking) según PMI PMBOK §7.4 y §6.5."""
    spi_val = round(float(spi), 4)
    sv_val = round(float(sv_amount), 2)
    cp_slip_val = round(float(critical_path_slip_days), 2)
    cp_share_val = round(float(critical_path_ev_share_pct), 2)
    float_consumed_val = round(float(non_critical_float_consumed_days), 2)
    max_slip_val = float(max_acceptable_cp_slip_days)
    min_share_val = float(min_cp_ev_share_pct)

    false_schedule_optimism_detected = bool(
        spi_val >= 1.0 and cp_slip_val > max_slip_val
    )
    cp_ev_dilution_detected = bool(
        cp_share_val < min_share_val and cp_slip_val > 0.0
    )
    float_exhaustion_warning = bool(
        float_consumed_val > 5.0 and cp_share_val < 50.0
    )

    violations: list[str] = []
    recommendations: list[str] = []

    if false_schedule_optimism_detected:
        violations.append(
            f"Optimismo falso de cronograma: SPI ({spi_val}) >= 1.0 oculta un atraso de {cp_slip_val} días en la ruta crítica."
        )
        recommendations.append(
            "Reorientar recursos de actividades con holgura hacia la ruta crítica (fast-tracking/crashing) y complementar SPI con Earned Schedule SPI(t)."
        )
    elif cp_slip_val > max_slip_val:
        violations.append(
            f"Deslizamiento en la ruta crítica ({cp_slip_val} días) excede el umbral aceptable ({round(max_slip_val, 2)} días)."
        )
        recommendations.append(
            "Aplicar compresión de cronograma sobre las actividades con mayor Critical Path Drag."
        )

    if cp_ev_dilution_detected:
        violations.append(
            f"Dilución de Valor Ganado en ruta crítica: solo {cp_share_val}% del EV proviene de actividades críticas (mínimo requerido {round(min_share_val, 2)}%) mientras la ruta crítica se desliza."
        )
        recommendations.append(
            "Restringir el devengo prematuro de paquetes no críticos y priorizar entregables de ruta crítica."
        )

    if float_exhaustion_warning:
        recommendations.append(
            f"Erosión de holgura no crítica ({float_consumed_val} días consumidos): vigilar rutas cuasi-críticas para evitar nuevas rutas críticas."
        )

    is_schedule_aligned = bool(len(violations) == 0)

    if false_schedule_optimism_detected or cp_slip_val > max_slip_val + 5.0:
        status = "critical"
    elif len(violations) > 0 or float_exhaustion_warning:
        status = "warning"
    else:
        status = "healthy"

    return {
        "spi": spi_val,
        "sv_amount": sv_val,
        "critical_path_slip_days": cp_slip_val,
        "critical_path_ev_share_pct": cp_share_val,
        "non_critical_float_consumed_days": float_consumed_val,
        "false_schedule_optimism_detected": false_schedule_optimism_detected,
        "cp_ev_dilution_detected": cp_ev_dilution_detected,
        "float_exhaustion_warning": float_exhaustion_warning,
        "is_schedule_aligned": is_schedule_aligned,
        "status": status,
        "violations": violations,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_critical_path_drag_decoupling = staticmethod(
    evaluate_evm_critical_path_drag_decoupling
)


def evaluate_evm_undistributed_budget_and_planning_packages(
    bac: float,
    distributed_work_packages_budget: float,
    planning_packages_budget: float = 0.0,
    undistributed_budget: float = 0.0,
    ub_holding_days: float = 0.0,
    max_ub_share_pct: float = 10.0,
    max_ub_holding_days: float = 30.0,
) -> dict[str, Any]:
    """PMBOK §7.3 & ANSI/EIA-748 — reconciliación PMB, Presupuesto No Distribuido (UB) y paquetes de planificación.

    - ``calculated_pmb`` = distribuidos + planificación + UB; reconciliado con
      BAC si la discrepancia <= 0.01.
    - ``ub_share_pct`` contra ``max_ub_share_pct``; retención de UB con fondos
      pendientes contra ``max_ub_holding_days``.
    """
    numeric_inputs = {
        "bac": bac,
        "distributed_work_packages_budget": distributed_work_packages_budget,
        "planning_packages_budget": planning_packages_budget,
        "undistributed_budget": undistributed_budget,
        "ub_holding_days": ub_holding_days,
        "max_ub_share_pct": max_ub_share_pct,
        "max_ub_holding_days": max_ub_holding_days,
    }
    for name, value in numeric_inputs.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (value == value):
            raise ValueError(f"EVM PMB: {name} debe ser numérico real, no bool/NaN")
    if bac <= 0:
        raise ValueError("EVM PMB: bac debe ser > 0")
    for name in (
        "distributed_work_packages_budget",
        "planning_packages_budget",
        "undistributed_budget",
        "ub_holding_days",
        "max_ub_share_pct",
        "max_ub_holding_days",
    ):
        if numeric_inputs[name] < 0:
            raise ValueError(f"EVM PMB: {name} debe ser >= 0")

    calculated_pmb = round(
        float(distributed_work_packages_budget)
        + float(planning_packages_budget)
        + float(undistributed_budget),
        2,
    )
    pmb_bac_discrepancy_amount = round(calculated_pmb - float(bac), 2)
    pmb_reconciled_with_bac = bool(abs(pmb_bac_discrepancy_amount) <= 0.01)
    ub_share_pct = round((float(undistributed_budget) / float(bac)) * 100.0, 2)
    planning_package_share_pct = round(
        (float(planning_packages_budget) / float(bac)) * 100.0,
        2,
    )
    ub_share_exceeded = bool(ub_share_pct > max_ub_share_pct)
    ub_holding_sla_breached = bool(
        float(undistributed_budget) > 0.0
        and float(ub_holding_days) > max_ub_holding_days
    )
    is_pmb_baseline_healthy = bool(
        pmb_reconciled_with_bac
        and not ub_share_exceeded
        and not ub_holding_sla_breached
    )

    return {
        "bac": round(float(bac), 2),
        "calculated_pmb": calculated_pmb,
        "pmb_bac_discrepancy_amount": pmb_bac_discrepancy_amount,
        "pmb_reconciled_with_bac": pmb_reconciled_with_bac,
        "ub_share_pct": ub_share_pct,
        "planning_package_share_pct": planning_package_share_pct,
        "ub_share_exceeded": ub_share_exceeded,
        "ub_holding_sla_breached": ub_holding_sla_breached,
        "is_pmb_baseline_healthy": is_pmb_baseline_healthy,
    }


ProjectEVMService.evaluate_evm_undistributed_budget_and_planning_packages = staticmethod(
    evaluate_evm_undistributed_budget_and_planning_packages
)


def evaluate_evm_reserve_burn_vs_risk_exposure(
    initial_contingency_reserve: float,
    remaining_contingency_reserve: float,
    remaining_emv_exposure: float,
    percent_complete: float,
    management_reserve_used: float = 0.0,
    mr_ccb_approved: bool = True,
    max_burn_disproportion_pct: float = 20.0,
) -> dict[str, Any]:
    """Audita la tasa de consumo de la Reserva de Contingencia frente al avance físico y la exposición EMV residual, así como la gobernanza de la Reserva de Gestión (MR) según PMI PMBOK §7.4 y §11.6."""
    numeric_inputs = {
        "initial_contingency_reserve": initial_contingency_reserve,
        "remaining_contingency_reserve": remaining_contingency_reserve,
        "remaining_emv_exposure": remaining_emv_exposure,
        "percent_complete": percent_complete,
        "management_reserve_used": management_reserve_used,
        "max_burn_disproportion_pct": max_burn_disproportion_pct,
    }
    for name, value in numeric_inputs.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not (value == value)
            or abs(float(value)) == float("inf")
        ):
            raise ValueError(f"EVM Reserve: {name} debe ser numérico real, no bool/NaN/Inf")

    init_res = float(initial_contingency_reserve)
    rem_res = float(remaining_contingency_reserve)
    rem_emv = float(remaining_emv_exposure)
    pct_comp = float(percent_complete)
    mr_used = float(management_reserve_used)
    max_disp = float(max_burn_disproportion_pct)

    if init_res <= 0.0:
        raise ValueError("EVM Reserve: initial_contingency_reserve debe ser > 0")
    if rem_res < 0.0 or rem_res > init_res:
        raise ValueError(
            "EVM Reserve: remaining_contingency_reserve debe estar en [0, initial_contingency_reserve]"
        )
    if rem_emv < 0.0:
        raise ValueError("EVM Reserve: remaining_emv_exposure debe ser >= 0")
    if pct_comp < 0.0 or pct_comp > 100.0:
        raise ValueError("EVM Reserve: percent_complete debe estar en [0, 100]")
    if mr_used < 0.0:
        raise ValueError("EVM Reserve: management_reserve_used debe ser >= 0")
    if max_disp < 0.0:
        raise ValueError("EVM Reserve: max_burn_disproportion_pct debe ser >= 0")

    contingency_burn_pct = round(((init_res - rem_res) / init_res) * 100.0, 2)
    reserve_coverage_ratio = (
        round(rem_res / rem_emv, 4) if rem_emv > 0.0 else 1.0
    )
    burn_vs_progress_delta_pct = round(contingency_burn_pct - pct_comp, 2)

    reserve_shortfall_detected = bool(rem_res < rem_emv)
    premature_reserve_depletion = bool(burn_vs_progress_delta_pct > max_disp)
    unapproved_mr_drawdown = bool(mr_used > 0.0 and not bool(mr_ccb_approved is True))

    is_reserve_healthy = bool(
        not reserve_shortfall_detected
        and not premature_reserve_depletion
        and not unapproved_mr_drawdown
    )

    recommendations: list[str] = []
    if reserve_shortfall_detected:
        recommendations.append(
            "Solicitar suplemento de reserva o re-evaluar respuestas a riesgos: la reserva de contingencia remanente no cubre la exposición EMV residual."
        )
    if unapproved_mr_drawdown:
        recommendations.append(
            "Someter a ratificación formal del CCB el uso de Reserva de Gestión (MR) e incorporarla a la línea base de costos."
        )
    if premature_reserve_depletion:
        recommendations.append(
            "Auditar las causas de consumo acelerado de contingencia respecto al porcentaje de avance físico ejecutado."
        )

    if reserve_shortfall_detected or unapproved_mr_drawdown:
        status = "critical"
    elif premature_reserve_depletion:
        status = "warning"
    else:
        status = "healthy"

    return {
        "contingency_burn_pct": contingency_burn_pct,
        "reserve_coverage_ratio": reserve_coverage_ratio,
        "burn_vs_progress_delta_pct": burn_vs_progress_delta_pct,
        "reserve_shortfall_detected": reserve_shortfall_detected,
        "premature_reserve_depletion": premature_reserve_depletion,
        "unapproved_mr_drawdown": unapproved_mr_drawdown,
        "is_reserve_healthy": is_reserve_healthy,
        "status": status,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_reserve_burn_vs_risk_exposure = staticmethod(
    evaluate_evm_reserve_burn_vs_risk_exposure
)


def evaluate_evm_loe_masking_and_variance_distortion(
    control_accounts: object,
    *,
    max_loe_share_pct: float = 15.0,
) -> dict[str, object]:
    """Evalúa distorsión de varianzas y enmascaramiento de atrasos por Nivel de Esfuerzo (Level-of-Effort - LOE) en Cuentas de Control según PMI PMBOK §7.4 y ANSI/EIA-748."""
    total_evaluated = 0
    excessive_loe_share_ca_ids: list[str] = []
    loe_schedule_variance_violation_ca_ids: list[str] = []
    loe_masked_delay_ca_ids: list[str] = []

    if isinstance(control_accounts, Sequence) and not isinstance(
        control_accounts, (str, bytes, bytearray)
    ):
        for item in control_accounts:
            if not isinstance(item, Mapping):
                continue
            ca_id = str(item.get("ca_id") or item.get("id") or "").strip()
            if not ca_id:
                continue

            total_evaluated += 1
            try:
                total_bac = float(item.get("total_bac", 0.0) or 0.0)
            except (TypeError, ValueError):
                total_bac = 0.0

            try:
                loe_bac = float(item.get("loe_bac", 0.0) or 0.0)
            except (TypeError, ValueError):
                loe_bac = 0.0

            try:
                loe_ev = float(item.get("loe_ev", 0.0) or 0.0)
            except (TypeError, ValueError):
                loe_ev = 0.0

            try:
                loe_pv = float(item.get("loe_pv", 0.0) or 0.0)
            except (TypeError, ValueError):
                loe_pv = 0.0

            try:
                discrete_sv = float(item.get("discrete_sv", 0.0) or 0.0)
            except (TypeError, ValueError):
                discrete_sv = 0.0

            try:
                reported_total_sv = float(
                    item.get("reported_total_sv", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                reported_total_sv = 0.0

            if total_bac > 0.0 and ((loe_bac / total_bac) * 100.0) > float(
                max_loe_share_pct
            ):
                excessive_loe_share_ca_ids.append(ca_id)

            if abs(loe_ev - loe_pv) > 0.01:
                loe_schedule_variance_violation_ca_ids.append(ca_id)

            if discrete_sv < 0.0 and reported_total_sv >= 0.0:
                loe_masked_delay_ca_ids.append(ca_id)

    return {
        "total_evaluated": total_evaluated,
        "excessive_loe_share_ca_ids": excessive_loe_share_ca_ids,
        "loe_schedule_variance_violation_ca_ids": loe_schedule_variance_violation_ca_ids,
        "loe_masked_delay_ca_ids": loe_masked_delay_ca_ids,
        "is_loe_accounting_compliant": (
            len(excessive_loe_share_ca_ids) == 0
            and len(loe_schedule_variance_violation_ca_ids) == 0
            and len(loe_masked_delay_ca_ids) == 0
        ),
    }


ProjectEVMService.evaluate_evm_loe_masking_and_variance_distortion = staticmethod(
    evaluate_evm_loe_masking_and_variance_distortion
)


def evaluate_evm_apportioned_effort_base_coherence(
    apportioned_packages: object,
) -> dict[str, object]:
    """Evalúa coherencia de paquetes de Esfuerzo Prorrateado (Apportioned Effort - AE) respecto a su paquete discreto base, factor de prorrateo y sincronización de avance según PMI PMBOK §7.4 y ANSI/EIA-748."""
    total_evaluated = 0
    unlinked_or_non_discrete_base_wp_ids: list[str] = []
    invalid_factor_wp_ids: list[str] = []
    progress_desync_wp_ids: list[str] = []

    if isinstance(apportioned_packages, Sequence) and not isinstance(
        apportioned_packages, (str, bytes, bytearray)
    ):
        for item in apportioned_packages:
            if not isinstance(item, Mapping):
                continue
            wp_id = str(item.get("wp_id") or item.get("id") or "").strip()
            if not wp_id:
                continue

            total_evaluated += 1
            base_discrete_wp_id = str(
                item.get("base_discrete_wp_id") or ""
            ).strip()
            base_wp_evmt = (
                str(item.get("base_wp_evmt") or "discrete").strip().lower()
            )

            try:
                apportionment_factor_pct = float(
                    item.get("apportionment_factor_pct", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                apportionment_factor_pct = 0.0

            try:
                base_progress_pct = float(
                    item.get("base_progress_pct", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                base_progress_pct = 0.0

            try:
                reported_ae_progress_pct = float(
                    item.get("reported_ae_progress_pct", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                reported_ae_progress_pct = 0.0

            if not base_discrete_wp_id or base_wp_evmt == "loe":
                unlinked_or_non_discrete_base_wp_ids.append(wp_id)

            if (
                apportionment_factor_pct <= 0.0
                or apportionment_factor_pct > 100.0
            ):
                invalid_factor_wp_ids.append(wp_id)

            if abs(reported_ae_progress_pct - base_progress_pct) > 0.5:
                progress_desync_wp_ids.append(wp_id)

    return {
        "total_evaluated": total_evaluated,
        "unlinked_or_non_discrete_base_wp_ids": unlinked_or_non_discrete_base_wp_ids,
        "invalid_factor_wp_ids": invalid_factor_wp_ids,
        "progress_desync_wp_ids": progress_desync_wp_ids,
        "is_apportioned_effort_coherent": (
            len(unlinked_or_non_discrete_base_wp_ids) == 0
            and len(invalid_factor_wp_ids) == 0
            and len(progress_desync_wp_ids) == 0
        ),
    }


ProjectEVMService.evaluate_evm_apportioned_effort_base_coherence = staticmethod(
    evaluate_evm_apportioned_effort_base_coherence
)


def evaluate_evm_retroactive_adjustment_and_negative_period_anomalies(
    period_snapshots: object,
) -> dict[str, object]:
    """Evalúa ajustes retroactivos de valor ganado (de-earning), reversiones de costo real (AC negativo) sin bitácora autorizada y violaciones del techo BAC según PMI PMBOK §7.4 y ANSI/EIA-748."""
    total_evaluated = 0
    unexplained_negative_ev_period_ids: list[str] = []
    unexplained_negative_ac_period_ids: list[str] = []
    ev_exceeds_bac_ceiling_period_ids: list[str] = []

    if isinstance(period_snapshots, Sequence) and not isinstance(
        period_snapshots, (str, bytes, bytearray)
    ):
        for item in period_snapshots:
            if not isinstance(item, Mapping):
                continue
            period_id = str(
                item.get("period_id") or item.get("id") or ""
            ).strip()
            if not period_id:
                continue

            total_evaluated += 1
            try:
                period_delta_ev = float(
                    item.get("period_delta_ev", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                period_delta_ev = 0.0

            try:
                period_delta_ac = float(
                    item.get("period_delta_ac", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                period_delta_ac = 0.0

            try:
                cumulative_ev = float(item.get("cumulative_ev", 0.0) or 0.0)
            except (TypeError, ValueError):
                cumulative_ev = 0.0

            try:
                bac = float(item.get("bac", 0.0) or 0.0)
            except (TypeError, ValueError):
                bac = 0.0

            has_approved_retroactive_adjustment_log = bool(
                item.get("has_approved_retroactive_adjustment_log", False)
            )

            if (
                period_delta_ev < 0.0
                and not has_approved_retroactive_adjustment_log
            ):
                unexplained_negative_ev_period_ids.append(period_id)

            if (
                period_delta_ac < 0.0
                and not has_approved_retroactive_adjustment_log
            ):
                unexplained_negative_ac_period_ids.append(period_id)

            if bac > 0.0 and cumulative_ev > (bac + 0.01):
                ev_exceeds_bac_ceiling_period_ids.append(period_id)

    return {
        "total_evaluated": total_evaluated,
        "unexplained_negative_ev_period_ids": unexplained_negative_ev_period_ids,
        "unexplained_negative_ac_period_ids": unexplained_negative_ac_period_ids,
        "ev_exceeds_bac_ceiling_period_ids": ev_exceeds_bac_ceiling_period_ids,
        "is_period_accounting_clean": (
            len(unexplained_negative_ev_period_ids) == 0
            and len(unexplained_negative_ac_period_ids) == 0
            and len(ev_exceeds_bac_ceiling_period_ids) == 0
        ),
    }


ProjectEVMService.evaluate_evm_retroactive_adjustment_and_negative_period_anomalies = staticmethod(
    evaluate_evm_retroactive_adjustment_and_negative_period_anomalies
)


def evaluate_evm_contract_budget_base_and_ub_reconciliation(
    baseline_ledger: dict[str, object],
    *,
    max_ub_holding_days: int = 30,
    max_ub_to_pm_baseline_ratio: float = 0.10,
) -> dict[str, object]:
    """Evalúa la reconciliación jerárquica de líneas base EVM (DB + UB = PMB, PMB + MR = CBB, CBB vs TAB/OTB) y la gobernanza del Undistributed Budget según PMI PMBOK §7.4 y ANSI/EIA-748."""
    ledger = baseline_ledger if isinstance(baseline_ledger, Mapping) else {}

    def _num(key: str, default: float = 0.0) -> float:
        raw = ledger.get(key, default)
        if raw is None or isinstance(raw, bool):
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    distributed_budgets_sum = _num("distributed_budgets_sum", 0.0)
    undistributed_budget_ub = _num("undistributed_budget_ub", 0.0)
    performance_measurement_baseline_pmb = _num(
        "performance_measurement_baseline_pmb", 0.0
    )
    management_reserve_mr = _num("management_reserve_mr", 0.0)
    contract_budget_base_cbb = _num("contract_budget_base_cbb", 0.0)
    total_allocated_budget_tab = _num("total_allocated_budget_tab", 0.0)
    over_target_baseline_authorized = bool(
        ledger.get("over_target_baseline_authorized", False)
    )
    ub_oldest_unallocated_days = _num("ub_oldest_unallocated_days", 0.0)

    try:
        holding_cap_days = float(max_ub_holding_days)
    except (TypeError, ValueError):
        holding_cap_days = 30.0

    try:
        ub_ratio_cap = float(max_ub_to_pm_baseline_ratio)
    except (TypeError, ValueError):
        ub_ratio_cap = 0.10

    expected_pmb = round(
        float(distributed_budgets_sum) + float(undistributed_budget_ub), 2
    )
    pmb_reconciliation_delta = round(
        float(performance_measurement_baseline_pmb) - expected_pmb, 2
    )
    has_pmb_imbalance = abs(pmb_reconciliation_delta) > 0.01

    expected_cbb = round(
        float(performance_measurement_baseline_pmb)
        + float(management_reserve_mr),
        2,
    )
    cbb_reconciliation_delta = round(
        float(contract_budget_base_cbb) - expected_cbb, 2
    )
    has_cbb_imbalance = abs(cbb_reconciliation_delta) > 0.01

    tab_exceeds_cbb = (
        float(total_allocated_budget_tab) - float(contract_budget_base_cbb)
    ) > 0.01
    has_unauthorized_over_target_baseline = (
        tab_exceeds_cbb and not bool(over_target_baseline_authorized)
    )

    if float(performance_measurement_baseline_pmb) > 0:
        ub_ratio = round(
            float(undistributed_budget_ub)
            / float(performance_measurement_baseline_pmb),
            4,
        )
    else:
        ub_ratio = 1.0 if float(undistributed_budget_ub) > 0 else 0.0

    has_excessive_or_stale_ub = (
        (float(undistributed_budget_ub) < 0)
        or (ub_ratio > float(ub_ratio_cap))
        or (
            float(undistributed_budget_ub) > 0
            and float(ub_oldest_unallocated_days) > float(holding_cap_days)
        )
    )

    is_baseline_reconciliation_compliant = not (
        has_pmb_imbalance
        or has_cbb_imbalance
        or has_unauthorized_over_target_baseline
        or has_excessive_or_stale_ub
        or float(management_reserve_mr) < 0
    )

    return {
        "expected_pmb": expected_pmb,
        "pmb_reconciliation_delta": pmb_reconciliation_delta,
        "has_pmb_imbalance": has_pmb_imbalance,
        "expected_cbb": expected_cbb,
        "cbb_reconciliation_delta": cbb_reconciliation_delta,
        "has_cbb_imbalance": has_cbb_imbalance,
        "has_unauthorized_over_target_baseline": has_unauthorized_over_target_baseline,
        "ub_ratio": ub_ratio,
        "has_excessive_or_stale_ub": has_excessive_or_stale_ub,
        "is_baseline_reconciliation_compliant": is_baseline_reconciliation_compliant,
    }


ProjectEVMService.evaluate_evm_contract_budget_base_and_ub_reconciliation = staticmethod(
    evaluate_evm_contract_budget_base_and_ub_reconciliation
)


def evaluate_evm_etc_bottom_up_vs_formulaic_divergence(
    control_account_forecasts: list[dict[str, object]],
    *,
    max_optimistic_divergence_pct: float = 15.0,
) -> dict[str, object]:
    """Evalúa la divergencia entre el Estimate to Complete (ETC) bottom-up y el ETC formulado típico ((BAC - EV) / CPI), exigiendo Basis of Estimate (BOE) ante optimismo excesivo y detectando recuperaciones irrealistas con CPI < 0.85 según PMI PMBOK §7.4."""
    try:
        max_div_pct = float(max_optimistic_divergence_pct)
    except (TypeError, ValueError):
        max_div_pct = 15.0

    total_control_accounts = 0
    invalid_forecast_metric_ca_ids: list[str] = []
    optimistic_etc_divergence_ca_ids: list[str] = []
    unjustified_optimistic_etc_ca_ids: list[str] = []
    unrealistic_recovery_etc_ca_ids: list[str] = []

    if isinstance(control_account_forecasts, Sequence) and not isinstance(
        control_account_forecasts, (str, bytes, bytearray)
    ):
        for item in control_account_forecasts:
            if not isinstance(item, Mapping):
                continue
            ca_id = str(item.get("ca_id") or item.get("id") or "").strip()
            if not ca_id:
                continue

            total_control_accounts += 1

            def _metric(key: str, default: float = -1.0) -> float:
                raw = item.get(key)
                if raw is None or isinstance(raw, bool):
                    return default
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return default

            bac = _metric("bac", -1.0)
            ev = _metric("ev", -1.0)
            ac = _metric("ac", -1.0)
            bottom_up_etc = _metric("bottom_up_etc", -1.0)
            boe_documented = bool(item.get("basis_of_estimate_documented", False))

            if (
                bac <= 0.0
                or ev < 0.0
                or ac < 0.0
                or bottom_up_etc < 0.0
                or ev > bac
            ):
                invalid_forecast_metric_ca_ids.append(ca_id)
                continue

            remaining_work = bac - ev
            if remaining_work > 0.0:
                cpi = (ev / ac) if ac > 0.0 else 1.0
                typical_etc = (
                    (remaining_work / cpi) if cpi > 0.0 else remaining_work
                )
                if typical_etc > 0.0:
                    optimistic_delta_pct = round(
                        ((typical_etc - bottom_up_etc) / typical_etc) * 100.0,
                        2,
                    )
                    if optimistic_delta_pct > max_div_pct:
                        optimistic_etc_divergence_ca_ids.append(ca_id)
                        if not boe_documented:
                            unjustified_optimistic_etc_ca_ids.append(ca_id)

                if cpi < 0.85 and bottom_up_etc < remaining_work:
                    unrealistic_recovery_etc_ca_ids.append(ca_id)

    return {
        "total_control_accounts": total_control_accounts,
        "invalid_forecast_metric_ca_ids": invalid_forecast_metric_ca_ids,
        "optimistic_etc_divergence_ca_ids": optimistic_etc_divergence_ca_ids,
        "unjustified_optimistic_etc_ca_ids": unjustified_optimistic_etc_ca_ids,
        "unrealistic_recovery_etc_ca_ids": unrealistic_recovery_etc_ca_ids,
        "is_etc_forecast_credible": (
            len(invalid_forecast_metric_ca_ids) == 0
            and len(unjustified_optimistic_etc_ca_ids) == 0
            and len(unrealistic_recovery_etc_ca_ids) == 0
        ),
    }


ProjectEVMService.evaluate_evm_etc_bottom_up_vs_formulaic_divergence = staticmethod(
    evaluate_evm_etc_bottom_up_vs_formulaic_divergence
)


def evaluate_evm_critical_path_drag_and_float_masking(
    work_package_earned_schedule: list[dict[str, object]],
    *,
    overall_spi_t: float = 1.0,
) -> dict[str, object]:
    """Evalúa el arrastre de ruta crítica (Critical Path Drag) y el enmascaramiento de atrasos críticos por adelanto de paquetes con holgura (Non-Critical Float Masking) según PMI PMBOK §6.5 y §7.4."""
    try:
        spi_t_val = float(overall_spi_t)
    except (TypeError, ValueError):
        spi_t_val = 1.0

    critical_pv_sum = 0.0
    critical_ev_sum = 0.0
    non_critical_pv_sum = 0.0
    non_critical_ev_sum = 0.0

    invalid_schedule_metric_wp_ids: list[str] = []
    contradictory_critical_float_wp_ids: list[str] = []
    high_drag_lagging_critical_wp_ids: list[str] = []

    if isinstance(work_package_earned_schedule, Sequence) and not isinstance(
        work_package_earned_schedule, (str, bytes, bytearray)
    ):
        for item in work_package_earned_schedule:
            if not isinstance(item, Mapping):
                continue
            wp_id = str(item.get("wp_id") or item.get("id") or "").strip()
            if not wp_id:
                continue

            def _num(key: str, default: float = -1.0) -> float:
                raw = item.get(key)
                if raw is None:
                    return default
                if isinstance(raw, bool):
                    return -1.0
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return -1.0

            pv = _num("planned_value_pv", -1.0)
            ev = _num("earned_value_ev", -1.0)
            total_float = _num("total_float_days", 0.0)
            drag_days = _num("critical_path_drag_days", 0.0)
            is_critical = bool(item.get("is_critical_path", False))

            if pv < 0.0 or ev < 0.0 or drag_days < 0.0:
                invalid_schedule_metric_wp_ids.append(wp_id)
                continue

            if is_critical:
                critical_pv_sum += pv
                critical_ev_sum += ev
                if total_float > 0.0:
                    contradictory_critical_float_wp_ids.append(wp_id)
                if (
                    drag_days >= 5.0
                    and pv > 0.0
                    and (ev / pv) < 0.90
                ):
                    high_drag_lagging_critical_wp_ids.append(wp_id)
            else:
                non_critical_pv_sum += pv
                non_critical_ev_sum += ev

    critical_path_spi = (
        round(critical_ev_sum / critical_pv_sum, 4)
        if critical_pv_sum > 0.0
        else 1.0
    )
    non_critical_spi = (
        round(non_critical_ev_sum / non_critical_pv_sum, 4)
        if non_critical_pv_sum > 0.0
        else 1.0
    )

    has_non_critical_float_masking = (
        critical_pv_sum > 0.0 and critical_path_spi < 0.90
    ) and (spi_t_val >= 0.95 or non_critical_spi >= 1.05)

    return {
        "critical_path_spi": critical_path_spi,
        "non_critical_spi": non_critical_spi,
        "has_non_critical_float_masking": has_non_critical_float_masking,
        "invalid_schedule_metric_wp_ids": invalid_schedule_metric_wp_ids,
        "contradictory_critical_float_wp_ids": contradictory_critical_float_wp_ids,
        "high_drag_lagging_critical_wp_ids": high_drag_lagging_critical_wp_ids,
        "is_earned_schedule_critical_path_coherent": (
            len(invalid_schedule_metric_wp_ids) == 0
            and len(contradictory_critical_float_wp_ids) == 0
            and len(high_drag_lagging_critical_wp_ids) == 0
            and not has_non_critical_float_masking
        ),
    }


ProjectEVMService.evaluate_evm_critical_path_drag_and_float_masking = staticmethod(
    evaluate_evm_critical_path_drag_and_float_masking
)


def evaluate_evm_rolling_wave_planning_package_freeze_horizon(
    planning_packages: list[dict[str, object]],
    *,
    freeze_horizon_days: int = 30,
    max_planning_package_share_pct: float = 40.0,
    total_control_account_bac: float = 0.0,
) -> dict[str, object]:
    """PMBOK §6.2 / §7.4 — horizonte de congelación Rolling Wave y EV prematuro en Planning Packages."""
    if not isinstance(planning_packages, Sequence) or isinstance(
        planning_packages, (str, bytes)
    ):
        return {
            "total_planning_packages": 0,
            "undecomposed_share_pct": 0.0,
            "exceeds_undecomposed_share_cap": False,
            "invalid_planning_package_ids": [],
            "premature_ev_on_undecomposed_pp_ids": [],
            "unfrozen_imminent_planning_package_ids": [],
            "is_rolling_wave_horizon_compliant": True,
        }

    try:
        horizon_val = float(freeze_horizon_days)
    except (TypeError, ValueError):
        horizon_val = 30.0

    try:
        cap_pct = float(max_planning_package_share_pct)
    except (TypeError, ValueError):
        cap_pct = 40.0

    try:
        ca_bac = float(total_control_account_bac)
    except (TypeError, ValueError):
        ca_bac = 0.0

    total_planning_packages = 0
    invalid_planning_package_ids: list[str] = []
    premature_ev_on_undecomposed_pp_ids: list[str] = []
    unfrozen_imminent_planning_package_ids: list[str] = []

    valid_bac_sum = 0.0
    undecomposed_pp_bac = 0.0

    for item in planning_packages:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("pp_id")
        if raw_id is None:
            continue
        pp_id = str(raw_id).strip()
        if not pp_id:
            continue

        total_planning_packages += 1

        try:
            bac = float(item.get("budget_bac", 0.0))
            ev_claimed = float(item.get("earned_value_claimed", 0.0))
            days_until = float(item.get("days_until_scheduled_start", 0.0))
        except (TypeError, ValueError):
            invalid_planning_package_ids.append(pp_id)
            continue

        if bac <= 0.0 or ev_claimed < 0.0:
            invalid_planning_package_ids.append(pp_id)
            continue

        decomposed = bool(item.get("decomposed_into_work_packages", False))
        valid_bac_sum += bac

        if not decomposed:
            undecomposed_pp_bac += bac
            if ev_claimed > 0.0:
                premature_ev_on_undecomposed_pp_ids.append(pp_id)
            if days_until <= horizon_val:
                unfrozen_imminent_planning_package_ids.append(pp_id)

    denom = max(ca_bac, valid_bac_sum)
    if denom > 0.0:
        undecomposed_share_pct = round((undecomposed_pp_bac / denom) * 100.0, 2)
    else:
        undecomposed_share_pct = 0.0

    exceeds_undecomposed_share_cap = undecomposed_share_pct > cap_pct

    return {
        "total_planning_packages": total_planning_packages,
        "undecomposed_share_pct": undecomposed_share_pct,
        "exceeds_undecomposed_share_cap": exceeds_undecomposed_share_cap,
        "invalid_planning_package_ids": invalid_planning_package_ids,
        "premature_ev_on_undecomposed_pp_ids": premature_ev_on_undecomposed_pp_ids,
        "unfrozen_imminent_planning_package_ids": unfrozen_imminent_planning_package_ids,
        "is_rolling_wave_horizon_compliant": (
            len(invalid_planning_package_ids) == 0
            and len(premature_ev_on_undecomposed_pp_ids) == 0
            and len(unfrozen_imminent_planning_package_ids) == 0
            and not exceeds_undecomposed_share_cap
        ),
    }


ProjectEVMService.evaluate_evm_rolling_wave_planning_package_freeze_horizon = staticmethod(
    evaluate_evm_rolling_wave_planning_package_freeze_horizon
)



def evaluate_evm_to_complete_schedule_performance_index_tspi(
    planned_duration_days: float,
    earned_schedule_days: float,
    actual_time_days: float,
    estimated_duration_days: float = 0.0,
    *,
    max_achievable_tspi: float = 1.10,
) -> dict:
    """Evalúa TSPI de Earned Schedule y factibilidad de recuperación (Practice Standard for EVM).

    Validaciones (ValueError): planned_duration_days > 0, earned_schedule_days >= 0,
    actual_time_days >= 0, estimated_duration_days >= 0, max_achievable_tspi >= 1.0.
    - remaining_earned_schedule_days = max(0, planned - earned).
    - remaining_planned_time_days = max(0, planned - actual).
    - tspi_pd: 0.0 si no queda earned schedule por consumir; si queda tiempo
      planeado, round(remaining_es / remaining_pt, 4); None si el plazo
      original se agotó con trabajo pendiente.
    - tspi_ed: solo si estimated_duration_days > 0 y > actual_time_days;
      round(remaining_es / (estimated - actual), 4); None en otro caso.
    - schedule_recovery_feasibility: 'ACHIEVABLE' (tspi_pd <= 1.0),
      'CHALLENGING' (1.0 < tspi_pd <= max_achievable_tspi),
      'UNACHIEVABLE' (tspi_pd None o > max).
    - requires_schedule_rebaseline = (feasibility == 'UNACHIEVABLE').
    """
    planned = float(planned_duration_days)
    earned = float(earned_schedule_days)
    actual = float(actual_time_days)
    estimated = float(estimated_duration_days)
    max_tspi = float(max_achievable_tspi)

    if planned <= 0:
        raise ValueError("planned_duration_days debe ser > 0")
    if earned < 0:
        raise ValueError("earned_schedule_days debe ser >= 0")
    if actual < 0:
        raise ValueError("actual_time_days debe ser >= 0")
    if estimated < 0:
        raise ValueError("estimated_duration_days debe ser >= 0")
    if max_tspi < 1.0:
        raise ValueError("max_achievable_tspi debe ser >= 1.0")

    remaining_earned_schedule_days = round(max(0.0, planned - earned), 2)
    remaining_planned_time_days = round(max(0.0, planned - actual), 2)

    if remaining_earned_schedule_days == 0.0:
        tspi_pd: float | None = 0.0
    elif remaining_planned_time_days > 0.0:
        tspi_pd = round(remaining_earned_schedule_days / remaining_planned_time_days, 4)
    else:
        # Plazo original agotado con trabajo pendiente.
        tspi_pd = None

    if estimated > 0 and estimated > actual:
        tspi_ed: float | None = round(remaining_earned_schedule_days / (estimated - actual), 4)
    else:
        tspi_ed = None

    if tspi_pd is None or tspi_pd > max_tspi:
        schedule_recovery_feasibility = "UNACHIEVABLE"
    elif tspi_pd <= 1.0:
        schedule_recovery_feasibility = "ACHIEVABLE"
    else:
        schedule_recovery_feasibility = "CHALLENGING"

    requires_schedule_rebaseline = schedule_recovery_feasibility == "UNACHIEVABLE"

    return {
        "tspi_pd": tspi_pd,
        "tspi_ed": tspi_ed,
        "remaining_earned_schedule_days": remaining_earned_schedule_days,
        "remaining_planned_time_days": remaining_planned_time_days,
        "schedule_recovery_feasibility": schedule_recovery_feasibility,
        "requires_schedule_rebaseline": requires_schedule_rebaseline,
    }


ProjectEVMService.evaluate_evm_to_complete_schedule_performance_index_tspi = staticmethod(
    evaluate_evm_to_complete_schedule_performance_index_tspi
)


def evaluate_evm_loe_masking_and_discrete_variance_distortion(
    work_packages: list[dict[str, Any]],
    *,
    max_loe_share_pct: float = 20.0,
    discrete_spi_alert_threshold: float = 0.90,
) -> dict[str, Any]:
    """PMBOK §7.4 — evalúa enmascaramiento por Level of Effort (LOE) y distorsión de varianza discreta."""
    if not isinstance(work_packages, Sequence) or isinstance(
        work_packages, (str, bytes)
    ):
        return {
            "total_work_packages": 0,
            "loe_work_packages_count": 0,
            "loe_share_pct": 0.0,
            "composite_spi": 1.0,
            "discrete_only_spi": 1.0,
            "spi_masking_spread": 0.0,
            "is_loe_masking_discrete_delay": False,
            "loe_ev_pv_mismatch_wps": [],
            "loe_governance_status": "HEALTHY",
        }

    try:
        max_loe_pct = float(max_loe_share_pct)
    except (TypeError, ValueError):
        max_loe_pct = 20.0

    try:
        spi_thresh = float(discrete_spi_alert_threshold)
    except (TypeError, ValueError):
        spi_thresh = 0.90

    total_work_packages = 0
    loe_work_packages_count = 0
    total_pv = 0.0
    total_ev = 0.0
    total_ac = 0.0
    loe_pv = 0.0
    discrete_pv = 0.0
    discrete_ev = 0.0
    discrete_ac = 0.0
    loe_ev_pv_mismatch_wps: list[str] = []

    for item in work_packages:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("wp_id")
        if raw_id is None:
            continue
        wp_id = str(raw_id).strip()
        if not wp_id:
            continue

        total_work_packages += 1

        is_loe = bool(item.get("is_level_of_effort", False))
        pv = float(item.get("planned_value_pv", 0.0) or 0.0)
        ev = float(item.get("earned_value_ev", 0.0) or 0.0)
        ac = float(item.get("actual_cost_ac", 0.0) or 0.0)

        total_pv += pv
        total_ev += ev
        total_ac += ac

        if is_loe:
            loe_work_packages_count += 1
            loe_pv += pv
            if abs(ev - pv) > 0.01:
                loe_ev_pv_mismatch_wps.append(wp_id)
        else:
            discrete_pv += pv
            discrete_ev += ev
            discrete_ac += ac

    loe_share_pct = round((loe_pv / total_pv) * 100.0, 2) if total_pv > 0.0 else 0.0
    composite_spi = round(total_ev / total_pv, 4) if total_pv > 0.0 else 1.0
    discrete_only_spi = (
        round(discrete_ev / discrete_pv, 4) if discrete_pv > 0.0 else 1.0
    )
    spi_masking_spread = round(composite_spi - discrete_only_spi, 4)

    is_loe_masking_discrete_delay = bool(
        (
            discrete_pv > 0.0
            and discrete_only_spi < spi_thresh
            and composite_spi >= spi_thresh
        )
        or (loe_share_pct > max_loe_pct and spi_masking_spread >= 0.05)
    )

    if (
        loe_share_pct <= max_loe_pct
        and not is_loe_masking_discrete_delay
        and len(loe_ev_pv_mismatch_wps) == 0
    ):
        status = "HEALTHY"
    elif is_loe_masking_discrete_delay or len(loe_ev_pv_mismatch_wps) > 0:
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_work_packages": total_work_packages,
        "loe_work_packages_count": loe_work_packages_count,
        "loe_share_pct": loe_share_pct,
        "composite_spi": composite_spi,
        "discrete_only_spi": discrete_only_spi,
        "spi_masking_spread": spi_masking_spread,
        "is_loe_masking_discrete_delay": is_loe_masking_discrete_delay,
        "loe_ev_pv_mismatch_wps": loe_ev_pv_mismatch_wps,
        "loe_governance_status": status,
    }


ProjectEVMService.evaluate_evm_loe_masking_and_discrete_variance_distortion = staticmethod(
    evaluate_evm_loe_masking_and_discrete_variance_distortion
)


def evaluate_evm_retroactive_change_and_negative_period_anomaly(
    reporting_periods: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evalua cambios retroactivos en periodos cerrados y anomalias de PV/EV/AC negativos (PMBOK §7.4, EVM Practice Standard)."""
    if not isinstance(reporting_periods, list):
        reporting_periods = []

    total_periods_evaluated = 0
    compliant_periods_count = 0
    unauthorized_retroactive_periods_count = 0
    unexplained_negative_ev_pv_periods_count = 0
    unexplained_negative_ac_periods_count = 0
    anomalies: list[dict[str, Any]] = []

    for raw in reporting_periods:
        if not isinstance(raw, dict):
            continue
        total_periods_evaluated += 1
        period_id = str(raw.get("period_id") or "").strip() or f"PERIOD-{total_periods_evaluated}"
        period_pv = float(raw.get("period_pv", 0.0) or 0.0)
        period_ev = float(raw.get("period_ev", 0.0) or 0.0)
        period_ac = float(raw.get("period_ac", 0.0) or 0.0)
        prior_closed_period_adjusted = bool(raw.get("prior_closed_period_adjusted", False))
        authorized_reprogramming_cr_id = raw.get("authorized_reprogramming_cr_id")
        justification_documented = bool(raw.get("justification_documented", False))

        unauthorized_retroactive = prior_closed_period_adjusted and (
            not bool(str(authorized_reprogramming_cr_id or "").strip())
        )
        unexplained_negative_ev_pv = (
            period_pv < 0.0 or period_ev < 0.0
        ) and (not justification_documented)
        unexplained_negative_ac = (period_ac < 0.0) and (not justification_documented)

        reasons: list[str] = []
        if unauthorized_retroactive:
            unauthorized_retroactive_periods_count += 1
            reasons.append("unauthorized_retroactive_baseline_change")
        if unexplained_negative_ev_pv:
            unexplained_negative_ev_pv_periods_count += 1
            reasons.append("unexplained_negative_period_ev_or_pv")
        if unexplained_negative_ac:
            unexplained_negative_ac_periods_count += 1
            reasons.append("unexplained_negative_period_ac")

        if not reasons:
            compliant_periods_count += 1
        else:
            anomalies.append(
                {
                    "period_id": period_id,
                    "reasons": reasons,
                }
            )

    if (
        unauthorized_retroactive_periods_count == 0
        and unexplained_negative_ev_pv_periods_count == 0
        and unexplained_negative_ac_periods_count == 0
    ):
        status = "HEALTHY"
    elif (
        unauthorized_retroactive_periods_count > 0
        or unexplained_negative_ev_pv_periods_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_periods_evaluated": total_periods_evaluated,
        "compliant_periods_count": compliant_periods_count,
        "unauthorized_retroactive_periods_count": unauthorized_retroactive_periods_count,
        "unexplained_negative_ev_pv_periods_count": unexplained_negative_ev_pv_periods_count,
        "unexplained_negative_ac_periods_count": unexplained_negative_ac_periods_count,
        "period_accounting_integrity_status": status,
        "anomalies": anomalies,
    }


ProjectEVMService.evaluate_evm_retroactive_change_and_negative_period_anomaly = staticmethod(
    evaluate_evm_retroactive_change_and_negative_period_anomaly
)


def evaluate_evm_subcontractor_flowdown_and_invoice_overbilling(
    subcontracts: list[dict[str, Any]],
    *,
    max_advance_billing_spread_pct: float = 5.0,
) -> dict[str, Any]:
    """Evalua flow-down de Valor Ganado de subcontratistas y conciliacion contra sobrefacturacion AC (PMBOK §7.4, EVM Practice Standard)."""
    if not isinstance(subcontracts, list):
        subcontracts = []

    max_spread_pct = float(max_advance_billing_spread_pct)
    total_subcontracts = 0
    compliant_subcontracts_count = 0
    ev_overstated_subcontracts_count = 0
    unbacked_overbilling_subcontracts_count = 0
    total_ev_overstatement_raw = 0.0
    discrepancies: list[dict[str, Any]] = []

    for raw in subcontracts:
        if not isinstance(raw, dict):
            continue
        total_subcontracts += 1
        subcontract_id = (
            str(raw.get("subcontract_id") or "").strip()
            or f"SUB-{total_subcontracts}"
        )
        bac = float(raw.get("subcontract_bac", 0.0) or 0.0)
        claimed_ev = float(raw.get("claimed_ev", 0.0) or 0.0)
        phys_pct = float(raw.get("physical_progress_verified_pct", 0.0) or 0.0)
        billed_ac = float(raw.get("billed_ac", 0.0) or 0.0)
        retention_withheld = float(raw.get("retention_withheld_amount", 0.0) or 0.0)

        verified_ev = round(bac * (phys_pct / 100.0), 2)
        ev_overstatement_amount = round(max(0.0, claimed_ev - verified_ev), 2)
        total_ev_overstatement_raw += ev_overstatement_amount
        ev_overstated = ev_overstatement_amount > 0.01

        billing_spread_pct = (
            round(((billed_ac - verified_ev) / bac) * 100.0, 2) if bac > 0.0 else 0.0
        )
        unbacked_overbilling = (billing_spread_pct > max_spread_pct) and (
            retention_withheld + 1e-6 < (billed_ac - verified_ev)
        )

        reasons: list[str] = []
        if ev_overstated:
            ev_overstated_subcontracts_count += 1
            reasons.append("claimed_ev_exceeds_verified_physical_progress")
        if unbacked_overbilling:
            unbacked_overbilling_subcontracts_count += 1
            reasons.append("unbacked_invoice_overbilling")

        if not reasons:
            compliant_subcontracts_count += 1
        else:
            discrepancies.append(
                {
                    "subcontract_id": subcontract_id,
                    "verified_ev": verified_ev,
                    "ev_overstatement_amount": ev_overstatement_amount,
                    "reasons": reasons,
                }
            )

    total_ev_overstatement_amount = round(total_ev_overstatement_raw, 2)
    if (
        ev_overstated_subcontracts_count == 0
        and unbacked_overbilling_subcontracts_count == 0
    ):
        status = "HEALTHY"
    elif unbacked_overbilling_subcontracts_count > 0:
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_subcontracts": total_subcontracts,
        "compliant_subcontracts_count": compliant_subcontracts_count,
        "ev_overstated_subcontracts_count": ev_overstated_subcontracts_count,
        "unbacked_overbilling_subcontracts_count": unbacked_overbilling_subcontracts_count,
        "total_ev_overstatement_amount": total_ev_overstatement_amount,
        "subcontractor_evm_status": status,
        "discrepancies": discrepancies,
    }


ProjectEVMService.evaluate_evm_subcontractor_flowdown_and_invoice_overbilling = staticmethod(
    evaluate_evm_subcontractor_flowdown_and_invoice_overbilling
)


def evaluate_evm_earning_rule_gaming_and_duration_split(
    work_packages: Sequence[Mapping[str, Any]] | None,
    *,
    max_0_100_reporting_periods: int = 1,
    max_50_50_reporting_periods: int = 2,
    max_50_50_stalled_periods: int = 1,
) -> dict[str, Any]:
    """Evalúa la adecuación de técnicas EVMT (0/100 y 50/50) frente a la duración en períodos contables y el estancamiento oportunista al 50% (PMI PMBOK §7.4)."""
    if (
        work_packages is None
        or isinstance(work_packages, (str, bytes))
        or not isinstance(work_packages, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = work_packages

    try:
        max_0_100 = int(max_0_100_reporting_periods)
    except (TypeError, ValueError):
        max_0_100 = 1

    try:
        max_50_50 = int(max_50_50_reporting_periods)
    except (TypeError, ValueError):
        max_50_50 = 2

    try:
        max_stalled = int(max_50_50_stalled_periods)
    except (TypeError, ValueError):
        max_stalled = 1

    total_work_packages = 0
    compliant_work_packages = 0
    premature_ev_exposure_raw = 0.0

    inappropriate_0_100_duration_ids: list[str] = []
    inappropriate_50_50_duration_ids: list[str] = []
    stalled_50_50_opening_credit_ids: list[str] = []
    rule_credit_violation_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_work_packages += 1

        wp_id = (
            str(raw.get("id") or raw.get("wp_id") or "").strip()
            or "WP-UNKNOWN"
        )
        earning_rule = str(raw.get("earning_rule") or "").strip().lower()

        try:
            planned_reporting_periods = max(
                1, int(raw.get("planned_reporting_periods") or 1)
            )
        except (TypeError, ValueError):
            planned_reporting_periods = 1

        try:
            periods_in_progress = max(
                0, int(raw.get("periods_in_progress") or 0)
            )
        except (TypeError, ValueError):
            periods_in_progress = 0

        try:
            claimed_ev_pct = max(
                0.0, min(100.0, float(raw.get("claimed_ev_pct") or 0.0))
            )
        except (TypeError, ValueError):
            claimed_ev_pct = 0.0

        try:
            bac = max(0.0, float(raw.get("bac") or 0.0))
        except (TypeError, ValueError):
            bac = 0.0

        is_inappropriate_0_100 = (
            earning_rule == "0_100" and planned_reporting_periods > max_0_100
        )
        is_inappropriate_50_50 = (
            earning_rule == "50_50" and planned_reporting_periods > max_50_50
        )
        is_stalled_50_50 = (
            earning_rule == "50_50"
            and 49.0 <= claimed_ev_pct <= 51.0
            and periods_in_progress > max_stalled
        )
        is_credit_violation = (
            earning_rule == "0_100" and 0.0 < claimed_ev_pct < 100.0
        ) or (
            earning_rule == "50_50"
            and all(abs(claimed_ev_pct - v) > 0.01 for v in (0.0, 50.0, 100.0))
        )

        if is_inappropriate_0_100:
            inappropriate_0_100_duration_ids.append(wp_id)
        if is_inappropriate_50_50:
            inappropriate_50_50_duration_ids.append(wp_id)
        if is_stalled_50_50:
            stalled_50_50_opening_credit_ids.append(wp_id)
        if is_credit_violation:
            rule_credit_violation_ids.append(wp_id)

        if (
            is_stalled_50_50
            or is_credit_violation
            or is_inappropriate_50_50
        ):
            premature_ev_exposure_raw += bac * (claimed_ev_pct / 100.0)

        if (
            not is_inappropriate_0_100
            and not is_inappropriate_50_50
            and not is_stalled_50_50
            and not is_credit_violation
        ):
            compliant_work_packages += 1

    premature_ev_exposure_amount = round(premature_ev_exposure_raw, 2)

    is_compliant = (
        len(inappropriate_0_100_duration_ids) == 0
        and len(inappropriate_50_50_duration_ids) == 0
        and len(stalled_50_50_opening_credit_ids) == 0
        and len(rule_credit_violation_ids) == 0
    )

    if is_compliant:
        evmt_governance_health = "healthy"
    elif (
        len(stalled_50_50_opening_credit_ids) > 0
        or len(rule_credit_violation_ids) > 0
    ):
        evmt_governance_health = "critical"
    else:
        evmt_governance_health = "at_risk"

    recommendations: list[str] = []
    if inappropriate_0_100_duration_ids:
        recommendations.append(
            f"Subdividir o migrar a hitos ponderados los paquetes 0/100 que exceden {max_0_100} período(s): {inappropriate_0_100_duration_ids}."
        )
    if inappropriate_50_50_duration_ids:
        recommendations.append(
            f"Migrar a weighted_milestones los paquetes 50/50 que abarcan más de {max_50_50} períodos: {inappropriate_50_50_duration_ids}."
        )
    if stalled_50_50_opening_credit_ids:
        recommendations.append(
            f"Auditar paquetes 50/50 estancados en 50% por más de {max_stalled} período(s): {stalled_50_50_opening_credit_ids}."
        )
    if rule_credit_violation_ids:
        recommendations.append(
            f"Corregir porcentajes de EV reclamados que violan las reglas discretas 0/100 o 50/50 en {rule_credit_violation_ids}."
        )

    return {
        "total_work_packages": total_work_packages,
        "compliant_work_packages": compliant_work_packages,
        "inappropriate_0_100_duration_ids": inappropriate_0_100_duration_ids,
        "inappropriate_50_50_duration_ids": inappropriate_50_50_duration_ids,
        "stalled_50_50_opening_credit_ids": stalled_50_50_opening_credit_ids,
        "rule_credit_violation_ids": rule_credit_violation_ids,
        "premature_ev_exposure_amount": premature_ev_exposure_amount,
        "evmt_governance_health": evmt_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_earning_rule_gaming_and_duration_split = staticmethod(
    evaluate_evm_earning_rule_gaming_and_duration_split
)


def evaluate_evm_cost_schedule_index_compound_degradation(
    control_accounts: Sequence[Mapping[str, Any]] | None,
    *,
    warning_csi_threshold: float = 0.90,
    critical_csi_threshold: float = 0.80,
    irrecoverable_pct_complete_gate: float = 20.0,
) -> dict[str, Any]:
    """Evalúa degradación compuesta del índice costo-cronograma (CSI = CPI * SPI), compensación enmascarada y umbral de irrecuperabilidad post-20% (PMI PMBOK §7.4)."""
    if (
        control_accounts is None
        or isinstance(control_accounts, (str, bytes))
        or not isinstance(control_accounts, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = control_accounts

    try:
        warn_thresh = float(warning_csi_threshold)
    except (TypeError, ValueError):
        warn_thresh = 0.90

    try:
        crit_thresh = float(critical_csi_threshold)
    except (TypeError, ValueError):
        crit_thresh = 0.80

    try:
        irrec_gate = float(irrecoverable_pct_complete_gate)
    except (TypeError, ValueError):
        irrec_gate = 20.0

    total_accounts = 0
    compliant_accounts = 0
    csis: list[float] = []

    tradeoff_masking_ids: list[str] = []
    warning_compound_degradation_ids: list[str] = []
    critical_compound_degradation_ids: list[str] = []
    post_gate_irrecoverable_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_accounts += 1

        ca_id = (
            str(raw.get("id") or raw.get("ca_id") or "").strip()
            or "CA-UNKNOWN"
        )

        try:
            cpi = max(0.0, float(raw.get("cpi") or 0.0))
        except (TypeError, ValueError):
            cpi = 0.0

        try:
            spi = max(0.0, float(raw.get("spi") or 0.0))
        except (TypeError, ValueError):
            spi = 0.0

        try:
            pct_complete = max(
                0.0, min(100.0, float(raw.get("pct_complete") or 0.0))
            )
        except (TypeError, ValueError):
            pct_complete = 0.0

        csi = round(cpi * spi, 4)
        csis.append(csi)

        is_tradeoff_masking = (cpi < 0.90 and spi > 1.05) or (
            spi < 0.90 and cpi > 1.05
        )
        is_warning_csi = crit_thresh <= csi < warn_thresh
        is_critical_csi = csi < crit_thresh
        is_post_gate_irrecoverable = (
            csi < crit_thresh and pct_complete >= irrec_gate
        )

        if is_tradeoff_masking:
            tradeoff_masking_ids.append(ca_id)
        if is_warning_csi:
            warning_compound_degradation_ids.append(ca_id)
        if is_critical_csi:
            critical_compound_degradation_ids.append(ca_id)
        if is_post_gate_irrecoverable:
            post_gate_irrecoverable_ids.append(ca_id)

        if (
            not is_tradeoff_masking
            and not is_warning_csi
            and not is_critical_csi
            and not is_post_gate_irrecoverable
        ):
            compliant_accounts += 1

    min_csi = 1.0 if not csis else round(min(csis), 4)

    if len(critical_compound_degradation_ids) > 0:
        csi_governance_health = "critical"
    elif (
        len(warning_compound_degradation_ids) > 0
        or len(tradeoff_masking_ids) > 0
    ):
        csi_governance_health = "at_risk"
    else:
        csi_governance_health = "healthy"

    is_compliant = csi_governance_health == "healthy"

    recommendations: list[str] = []
    if tradeoff_masking_ids:
        recommendations.append(
            f"Auditar compensación peligrosa costo-cronograma (CPI vs SPI divergentes) en {tradeoff_masking_ids}."
        )
    if warning_compound_degradation_ids:
        recommendations.append(
            f"Aplicar acciones preventivas de recuperación en cuentas con degradación compuesta CSI en banda de alerta: {warning_compound_degradation_ids}."
        )
    if critical_compound_degradation_ids:
        recommendations.append(
            f"Intervenir cuentas con degradación compuesta crítica (CSI < {crit_thresh}): {critical_compound_degradation_ids}."
        )
    if post_gate_irrecoverable_ids:
        recommendations.append(
            f"Evaluar re-baselining formal ante CCB para cuentas con CSI < {crit_thresh} tras superar el {irrec_gate}% de avance: {post_gate_irrecoverable_ids}."
        )

    return {
        "total_accounts": total_accounts,
        "compliant_accounts": compliant_accounts,
        "min_csi": min_csi,
        "tradeoff_masking_ids": tradeoff_masking_ids,
        "warning_compound_degradation_ids": warning_compound_degradation_ids,
        "critical_compound_degradation_ids": critical_compound_degradation_ids,
        "post_gate_irrecoverable_ids": post_gate_irrecoverable_ids,
        "csi_governance_health": csi_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_cost_schedule_index_compound_degradation = staticmethod(
    evaluate_evm_cost_schedule_index_compound_degradation
)


def evaluate_evm_undistributed_budget_and_planning_package_aging(
    budget_buckets: Sequence[Mapping[str, Any]] | None,
    *,
    max_ub_holding_days: int = 30,
    min_planning_package_conversion_lead_days: int = 30,
    max_ub_to_pmb_pct: float = 10.0,
) -> dict[str, Any]:
    """Evalúa el envejecimiento del Presupuesto No Distribuido (UB), la conversión oportuna de Planning Packages en Rolling Wave Planning y la prohibición de reclamar EV fuera de Work Packages (PMI PMBOK §7.3 y §7.4)."""
    if (
        budget_buckets is None
        or isinstance(budget_buckets, (str, bytes))
        or not isinstance(budget_buckets, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = budget_buckets

    try:
        max_ub_days = int(max_ub_holding_days)
    except (TypeError, ValueError):
        max_ub_days = 30

    try:
        min_pp_lead_days = int(min_planning_package_conversion_lead_days)
    except (TypeError, ValueError):
        min_pp_lead_days = 30

    try:
        max_ub_pct = float(max_ub_to_pmb_pct)
    except (TypeError, ValueError):
        max_ub_pct = 10.0

    def _pos_float(val: Any) -> float:
        try:
            return max(0.0, float(val or 0.0))
        except (TypeError, ValueError):
            return 0.0

    total_buckets = 0
    compliant_buckets = 0
    total_ub_amount_accum = 0.0

    stale_or_unscoped_ub_ids: list[str] = []
    unconverted_imminent_planning_package_ids: list[str] = []
    illegal_ev_on_non_work_package_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_buckets += 1

        bucket_id = (
            str(raw.get("id") or raw.get("bucket_id") or "").strip()
            or "BKT-UNKNOWN"
        )
        bucket_type = str(raw.get("bucket_type") or "").strip().lower()
        amount = _pos_float(raw.get("amount"))
        pmb_total = _pos_float(raw.get("pmb_total"))

        try:
            days_held_in_ub = max(0, int(raw.get("days_held_in_ub") or 0))
        except (TypeError, ValueError):
            days_held_in_ub = 0

        raw_lead = raw.get("days_until_scheduled_start")
        if raw_lead is None:
            days_until_scheduled_start = 90
        else:
            try:
                days_until_scheduled_start = int(raw_lead)
            except (TypeError, ValueError):
                days_until_scheduled_start = 90

        scope_statement_linked = bool(raw.get("scope_statement_linked"))
        ev_claimed = _pos_float(raw.get("ev_claimed"))

        if bucket_type == "undistributed_budget":
            total_ub_amount_accum += amount

        is_stale_or_unscoped_ub = bucket_type == "undistributed_budget" and (
            days_held_in_ub > max_ub_days
            or not scope_statement_linked
            or (
                pmb_total > 0.0
                and (amount / pmb_total) * 100.0 > max_ub_pct
            )
        )
        is_unconverted_pp = (
            bucket_type == "planning_package"
            and days_until_scheduled_start < min_pp_lead_days
        )
        is_illegal_ev = (
            bucket_type in {"undistributed_budget", "planning_package"}
            and ev_claimed > 0.0
        )

        if is_stale_or_unscoped_ub:
            stale_or_unscoped_ub_ids.append(bucket_id)
        if is_unconverted_pp:
            unconverted_imminent_planning_package_ids.append(bucket_id)
        if is_illegal_ev:
            illegal_ev_on_non_work_package_ids.append(bucket_id)

        if (
            not is_stale_or_unscoped_ub
            and not is_unconverted_pp
            and not is_illegal_ev
        ):
            compliant_buckets += 1

    is_compliant = (
        len(stale_or_unscoped_ub_ids) == 0
        and len(unconverted_imminent_planning_package_ids) == 0
        and len(illegal_ev_on_non_work_package_ids) == 0
    )

    if is_compliant:
        pmb_governance_health = "healthy"
    elif len(illegal_ev_on_non_work_package_ids) > 0:
        pmb_governance_health = "critical"
    else:
        pmb_governance_health = "at_risk"

    recommendations: list[str] = []
    if stale_or_unscoped_ub_ids:
        recommendations.append(
            f"Distribuir oportunamente el Undistributed Budget (<= {max_ub_days}d, <= {max_ub_pct}% PMB y con alcance vinculado) a Cuentas de Control en {stale_or_unscoped_ub_ids}."
        )
    if unconverted_imminent_planning_package_ids:
        recommendations.append(
            f"Descomponer los Planning Packages inminentes (< {min_pp_lead_days}d para inicio) en Work Packages detallados en {unconverted_imminent_planning_package_ids}."
        )
    if illegal_ev_on_non_work_package_ids:
        recommendations.append(
            f"Revertir el Earned Value reclamado ilegalmente sobre partidas UB o Planning Packages en {illegal_ev_on_non_work_package_ids}."
        )

    return {
        "total_buckets": total_buckets,
        "compliant_buckets": compliant_buckets,
        "total_ub_amount": round(total_ub_amount_accum, 2),
        "stale_or_unscoped_ub_ids": stale_or_unscoped_ub_ids,
        "unconverted_imminent_planning_package_ids": unconverted_imminent_planning_package_ids,
        "illegal_ev_on_non_work_package_ids": illegal_ev_on_non_work_package_ids,
        "pmb_governance_health": pmb_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_undistributed_budget_and_planning_package_aging = staticmethod(
    evaluate_evm_undistributed_budget_and_planning_package_aging
)



def evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
    work_packages: Sequence[Mapping[str, Any]] | None,
    *,
    max_adverse_rate_variance_pct: float = 10.0,
    max_adverse_efficiency_variance_pct: float = 15.0,
) -> dict[str, Any]:
    """PMBOK 7.4 & EVM Practice Standard — descomposición de la Cost Variance.

    Auditoría pura sobre ``work_packages``. Entradas no-lista/None se
    tratan como lista vacía y elementos no-dict se ignoran. Para cada
    paquete: ``ev = earned_hours * planned_hourly_rate``, ``ac = actual_hours
    * actual_hourly_rate``, ``rate_variance = (planned_rate - actual_rate) *
    actual_hours`` y ``efficiency_variance = (earned_hours - actual_hours) *
    planned_rate``. Reglas:

    1. ``adverse_rate_variance_breach``: ``planned_hourly_rate > 0`` AND
       ``actual_hours > 0`` AND ((actual_rate - planned_rate) / planned_rate
       * 100) > ``max_adverse_rate_variance_pct``.
    2. ``adverse_efficiency_variance_breach``: ``earned_hours > 0`` AND
       ``actual_hours > earned_hours`` AND ((actual - earned) / earned *
       100) > ``max_adverse_efficiency_variance_pct``.
    3. ``unaddressed_negative_cv``: (``ev - ac``) < 0 AND NOT
       ``corrective_action_logged``.

    Retorna total/compliant packages, los 3 conteos, totales de variación
    (rate y efficiency, redondeados a 2 decimales), cv_decomposition_status
    (HEALTHY/AT_RISK/CRITICAL) y violations (``wp_id`` / ``reasons``).
    """
    raw_items = work_packages if isinstance(work_packages, list) else []
    items = [entry for entry in raw_items if isinstance(entry, Mapping)]

    total = 0
    rate_breach_count = 0
    efficiency_breach_count = 0
    negative_cv_count = 0
    compliant_count = 0
    total_rate_variance = 0.0
    total_efficiency_variance = 0.0
    violations: list[dict[str, Any]] = []

    for entry in items:
        total += 1

        wp_id = entry.get("wp_id")
        planned_rate = entry.get("planned_hourly_rate")
        actual_rate = entry.get("actual_hourly_rate")
        earned_hours = entry.get("earned_hours")
        actual_hours = entry.get("actual_hours")
        corrective_action_logged = entry.get("corrective_action_logged")

        is_num = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)  # noqa: E731

        ev = (
            earned_hours * planned_rate
            if is_num(earned_hours) and is_num(planned_rate)
            else 0.0
        )
        ac = (
            actual_hours * actual_rate
            if is_num(actual_hours) and is_num(actual_rate)
            else 0.0
        )
        rate_variance = (
            (planned_rate - actual_rate) * actual_hours
            if is_num(planned_rate) and is_num(actual_rate) and is_num(actual_hours)
            else 0.0
        )
        efficiency_variance = (
            (earned_hours - actual_hours) * planned_rate
            if is_num(earned_hours) and is_num(actual_hours) and is_num(planned_rate)
            else 0.0
        )
        total_rate_variance += rate_variance
        total_efficiency_variance += efficiency_variance

        reasons: list[str] = []

        if (
            is_num(planned_rate)
            and is_num(actual_rate)
            and is_num(actual_hours)
            and planned_rate > 0
            and actual_hours > 0
            and ((actual_rate - planned_rate) / planned_rate) * 100.0
            > max_adverse_rate_variance_pct
        ):
            reasons.append("adverse_rate_variance_breach")

        if (
            is_num(earned_hours)
            and is_num(actual_hours)
            and earned_hours > 0
            and actual_hours > earned_hours
            and ((actual_hours - earned_hours) / earned_hours) * 100.0
            > max_adverse_efficiency_variance_pct
        ):
            reasons.append("adverse_efficiency_variance_breach")

        if (ev - ac) < 0.0 and corrective_action_logged is not True:
            reasons.append("unaddressed_negative_cv")

        ordered_reasons = list(dict.fromkeys(reasons))
        if not ordered_reasons:
            compliant_count += 1
            continue

        if "adverse_rate_variance_breach" in ordered_reasons:
            rate_breach_count += 1
        if "adverse_efficiency_variance_breach" in ordered_reasons:
            efficiency_breach_count += 1
        if "unaddressed_negative_cv" in ordered_reasons:
            negative_cv_count += 1

        violations.append(
            {
                "wp_id": wp_id,
                "reasons": ordered_reasons,
            }
        )

    if negative_cv_count > 0 or (rate_breach_count > 0 and efficiency_breach_count > 0):
        status = "CRITICAL"
    elif rate_breach_count > 0 or efficiency_breach_count > 0:
        status = "AT_RISK"
    else:
        status = "HEALTHY"

    return {
        "total_packages": total,
        "compliant_packages_count": compliant_count,
        "adverse_rate_variance_breach_count": rate_breach_count,
        "adverse_efficiency_variance_breach_count": efficiency_breach_count,
        "unaddressed_negative_cv_count": negative_cv_count,
        "total_rate_variance": round(total_rate_variance, 2),
        "total_efficiency_variance": round(total_efficiency_variance, 2),
        "cv_decomposition_status": status,
        "violations": violations,
    }


ProjectEVMService.evaluate_evm_cost_variance_rate_vs_efficiency_decomposition = staticmethod(
    evaluate_evm_cost_variance_rate_vs_efficiency_decomposition
)


def evaluate_evm_contract_fee_and_point_of_total_assumption(
    *,
    contract_type: str = "FPIF",
    target_cost: float = 0.0,
    target_price: float = 0.0,
    ceiling_price: float = 0.0,
    buyer_share_ratio: float = 0.70,
    seller_share_ratio: float = 0.30,
    estimated_actual_cost_eac: float = 0.0,
    min_fee: float = 0.0,
    max_fee: float = 0.0,
) -> dict[str, Any]:
    """Evalúa la estructura de honorarios e incentivos contractuales (FPIF / CPIF), el precio techo (Ceiling Price) y el Punto de Asunción Total (Point of Total Assumption - PTA) según PMI PMBOK §7.4 y §12.1."""
    c_type = str(contract_type or "FPIF").strip().upper()
    t_cost = float(target_cost or 0.0)
    t_price = float(target_price or 0.0)
    c_price = float(ceiling_price or 0.0)
    b_ratio = float(buyer_share_ratio if buyer_share_ratio is not None else 0.70)
    s_ratio = float(seller_share_ratio if seller_share_ratio is not None else 0.30)
    eac = float(estimated_actual_cost_eac or 0.0)
    min_f = float(min_fee or 0.0)
    max_f = float(max_fee or 0.0)

    target_fee = round(t_price - t_cost, 2)
    share_ratio_sum_valid = abs((b_ratio + s_ratio) - 1.0) <= 0.001

    if c_type == "FPIF" and b_ratio > 0.0 and c_price > t_price:
        point_of_total_assumption_pta: float | None = round(
            t_cost + ((c_price - t_price) / b_ratio), 2
        )
    else:
        point_of_total_assumption_pta = None

    cost_overrun_or_underrun = round(eac - t_cost, 2)
    raw_fee = round(target_fee - (cost_overrun_or_underrun * s_ratio), 2)

    if c_type == "CPIF":
        if max_f > 0.0:
            projected_seller_fee = round(min(max_f, max(min_f, raw_fee)), 2)
        else:
            projected_seller_fee = round(max(min_f, raw_fee), 2)
        projected_buyer_total_price = round(eac + projected_seller_fee, 2)
    else:
        uncapped_price = round(eac + raw_fee, 2)
        projected_buyer_total_price = (
            min(round(c_price, 2), uncapped_price)
            if c_price > 0.0
            else uncapped_price
        )
        projected_seller_fee = round(projected_buyer_total_price - eac, 2)

    has_breached_pta = bool(
        point_of_total_assumption_pta is not None
        and eac >= point_of_total_assumption_pta
    )
    has_breached_ceiling = bool(c_price > 0.0 and eac > c_price)

    issues: list[str] = []
    if not share_ratio_sum_valid:
        issues.append(
            f"La suma de ratios de reparto comprador/vendedor ({b_ratio + s_ratio:.3f}) debe ser igual a 1.0."
        )
    if has_breached_pta:
        issues.append(
            f"El costo proyectado EAC ({eac:.2f}) iguala o supera el Point of Total Assumption PTA ({point_of_total_assumption_pta:.2f})."
        )
    if has_breached_ceiling:
        issues.append(
            f"El costo proyectado EAC ({eac:.2f}) supera el precio techo contractual ({c_price:.2f})."
        )

    if has_breached_pta or has_breached_ceiling or not share_ratio_sum_valid:
        contract_exposure_status = "PTA_OR_CEILING_BREACH"
    elif eac > t_cost:
        contract_exposure_status = "COST_OVERRUN_SHARED"
    else:
        contract_exposure_status = "ON_OR_UNDER_TARGET"

    return {
        "contract_type": c_type,
        "target_fee": target_fee,
        "share_ratio_sum_valid": share_ratio_sum_valid,
        "point_of_total_assumption_pta": point_of_total_assumption_pta,
        "cost_overrun_or_underrun": cost_overrun_or_underrun,
        "raw_fee": raw_fee,
        "projected_seller_fee": projected_seller_fee,
        "projected_buyer_total_price": projected_buyer_total_price,
        "has_breached_pta": has_breached_pta,
        "has_breached_ceiling": has_breached_ceiling,
        "contract_exposure_status": contract_exposure_status,
        "issues": issues,
    }


ProjectEVMService.evaluate_evm_contract_fee_and_point_of_total_assumption = staticmethod(
    evaluate_evm_contract_fee_and_point_of_total_assumption
)



def evaluate_evm_earned_schedule_eac_t_and_tspi(
    *,
    earned_schedule_months: float = 0.0,
    actual_time_months: float = 0.0,
    planned_duration_months: float = 0.0,
    target_completion_months: float = 0.0,
    max_feasible_tspi: float = 1.10,
) -> dict[str, Any]:
    """Practice Standard for EVM — Earned Schedule, TV, EAC(t) y TSPI.

    Cálculo puro por reglas del estándar:

    1. ``time_variance_tv_months`` = round(ES - AT, 2).
    2. ``spi_t`` = round(ES / AT, 4) si AT > 0, sino 1.0.
    3. ``independent_eac_t_months`` = round(PD / spi_t, 2) si spi_t > 0,
       sino round(PD, 2).
    4. ``effective_target_months`` = target si target > 0, sino PD.
    5. ``remaining_work_months`` = max(0.0, PD - ES); ``remaining_time_months``
       = effective_target - AT. TSPI: 0.0 si remaining_work == 0; 999.0 si
       remaining_time <= 0; en otro caso round(remaining_work /
       remaining_time, 4).
    6. ``is_schedule_recoverable`` = bool(tspi <= max_feasible_tspi AND
       (remaining_time > 0 OR remaining_work == 0)).
    7. ``earned_schedule_status``: UNRECOVERABLE_SLIP si no recuperable;
       BEHIND_RECOVERABLE si recuperable y spi_t < 0.95; ON_OR_AHEAD_OF_TIME
       en caso contrario.
    """
    def _num(value) -> float:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else float(value or 0.0)

    es = _num(earned_schedule_months)
    at = _num(actual_time_months)
    pd = _num(planned_duration_months)
    target = _num(target_completion_months)
    ts_max = _num(max_feasible_tspi)

    time_variance_tv_months = round(es - at, 2)
    spi_t = round(es / at, 4) if at > 0 else 1.0
    independent_eac_t_months = round(pd / spi_t, 2) if spi_t > 0 else round(pd, 2)
    effective_target_months = target if target > 0 else pd
    remaining_work_months = max(0.0, pd - es)
    remaining_time_months = effective_target_months - at

    if remaining_work_months == 0:
        tspi = 0.0
    elif remaining_time_months <= 0:
        tspi = 999.0
    else:
        tspi = round(remaining_work_months / remaining_time_months, 4)

    is_schedule_recoverable = bool(
        tspi <= ts_max and (remaining_time_months > 0 or remaining_work_months == 0)
    )

    if not is_schedule_recoverable:
        earned_schedule_status = "UNRECOVERABLE_SLIP"
    elif spi_t < 0.95:
        earned_schedule_status = "BEHIND_RECOVERABLE"
    else:
        earned_schedule_status = "ON_OR_AHEAD_OF_TIME"

    return {
        "time_variance_tv_months": time_variance_tv_months,
        "spi_t": spi_t,
        "independent_eac_t_months": independent_eac_t_months,
        "tspi": tspi,
        "is_schedule_recoverable": is_schedule_recoverable,
        "earned_schedule_status": earned_schedule_status,
    }


ProjectEVMService.evaluate_evm_earned_schedule_eac_t_and_tspi = staticmethod(
    evaluate_evm_earned_schedule_eac_t_and_tspi
)


def evaluate_evm_loe_contamination_and_variance_masking(
    control_accounts: list[dict[str, Any]],
    *,
    max_loe_budget_share_pct: float = 15.0,
) -> dict[str, Any]:
    """Evalúa contaminación de Level of Effort (LOE) y enmascaramiento de varianza de cronograma (PMI PMBOK §7.4 / EIA-748)."""
    if not isinstance(control_accounts, list):
        return {
            "total_control_accounts": 0,
            "excessive_loe_ca_ids": [],
            "loe_pv_mismatch_ca_ids": [],
            "masked_schedule_delay_ca_ids": [],
            "project_loe_share_pct": 0.0,
            "loe_governance_status": "CLEAN",
            "is_loe_compliant": True,
            "issues": [],
        }

    max_share = float(
        max_loe_budget_share_pct if max_loe_budget_share_pct is not None else 15.0
    )

    total_control_accounts = 0
    excessive_loe_ca_ids: list[str] = []
    loe_pv_mismatch_ca_ids: list[str] = []
    masked_schedule_delay_ca_ids: list[str] = []
    issues: list[str] = []

    sum_loe_bac = 0.0
    sum_total_bac = 0.0

    for idx, item in enumerate(control_accounts):
        if not isinstance(item, dict):
            continue
        total_control_accounts += 1
        ca_id = str(item.get("ca_id") or f"CA-{idx + 1}").strip()

        discrete_bac = max(0.0, float(item.get("discrete_bac") or 0.0))
        loe_bac = max(0.0, float(item.get("loe_bac") or 0.0))
        discrete_ev = max(0.0, float(item.get("discrete_ev") or 0.0))
        discrete_pv = max(0.0, float(item.get("discrete_pv") or 0.0))
        loe_ev = max(0.0, float(item.get("loe_ev") or 0.0))
        loe_pv = max(0.0, float(item.get("loe_pv") or 0.0))

        ca_total_bac = discrete_bac + loe_bac
        sum_loe_bac += loe_bac
        sum_total_bac += ca_total_bac

        if ca_total_bac > 0.0:
            loe_share_pct = (loe_bac / ca_total_bac) * 100.0
            if loe_share_pct > max_share:
                excessive_loe_ca_ids.append(ca_id)
                issues.append(
                    f"Cuenta de control '{ca_id}' excede el límite de LOE ({loe_share_pct:.2f}% > {max_share:.2f}%)"
                )

        if abs(loe_ev - loe_pv) > 0.01:
            loe_pv_mismatch_ca_ids.append(ca_id)
            issues.append(
                f"Cuenta de control '{ca_id}' presenta discrepancia contable LOE (EV_loe={loe_ev:.2f} != PV_loe={loe_pv:.2f})"
            )

        total_pv = discrete_pv + loe_pv
        if total_pv > 0.0 and discrete_pv > 0.0:
            combined_spi = (discrete_ev + loe_ev) / total_pv
            discrete_spi = discrete_ev / discrete_pv
            if combined_spi >= 0.95 and discrete_spi < 0.90:
                masked_schedule_delay_ca_ids.append(ca_id)
                issues.append(
                    f"Cuenta de control '{ca_id}' enmascara retraso discreto con LOE (SPI combinado={combined_spi:.2f} vs SPI discreto={discrete_spi:.2f})"
                )

    project_loe_share_pct = (
        round((sum_loe_bac / sum_total_bac) * 100.0, 2) if sum_total_bac > 0.0 else 0.0
    )

    if len(loe_pv_mismatch_ca_ids) > 0 or len(masked_schedule_delay_ca_ids) > 0:
        loe_governance_status = "MASKING_OR_ACCOUNTING_ERROR"
    elif len(excessive_loe_ca_ids) > 0 or project_loe_share_pct > max_share:
        loe_governance_status = "LOE_HEAVY"
    else:
        loe_governance_status = "CLEAN"

    return {
        "total_control_accounts": total_control_accounts,
        "excessive_loe_ca_ids": excessive_loe_ca_ids,
        "loe_pv_mismatch_ca_ids": loe_pv_mismatch_ca_ids,
        "masked_schedule_delay_ca_ids": masked_schedule_delay_ca_ids,
        "project_loe_share_pct": project_loe_share_pct,
        "loe_governance_status": loe_governance_status,
        "is_loe_compliant": loe_governance_status == "CLEAN",
        "issues": issues,
    }


ProjectEVMService.evaluate_evm_loe_contamination_and_variance_masking = staticmethod(
    evaluate_evm_loe_contamination_and_variance_masking
)


def evaluate_evm_funding_limit_reconciliation_and_liquidity(
    fiscal_periods: list[dict[str, Any]],
    *,
    min_liquidity_headroom_pct: float = 5.0,
) -> dict[str, Any]:
    """Evalúa conciliación con límites de financiamiento y liquidez de flujo de caja (PMI PMBOK §7.3 / §7.4)."""
    if not isinstance(fiscal_periods, list):
        return {
            "total_periods": 0,
            "planned_breach_period_ids": [],
            "actual_commitment_breach_period_ids": [],
            "tight_headroom_period_ids": [],
            "max_funding_deficit_usd": 0.0,
            "funding_reconciliation_status": "RECONCILED",
            "is_funding_reconciled": True,
            "issues": [],
        }

    min_headroom_pct = float(
        min_liquidity_headroom_pct if min_liquidity_headroom_pct is not None else 5.0
    )

    total_periods = 0
    planned_breach_period_ids: list[str] = []
    actual_commitment_breach_period_ids: list[str] = []
    tight_headroom_period_ids: list[str] = []
    issues: list[str] = []
    max_deficit = 0.0

    for idx, item in enumerate(fiscal_periods):
        if not isinstance(item, dict):
            continue
        total_periods += 1
        period_id = str(item.get("period_id") or f"PERIOD-{idx + 1}").strip()
        funding_limit = float(item.get("cumulative_funding_limit_usd") or 0.0)
        planned_pv = float(item.get("cumulative_planned_outflow_pv_usd") or 0.0)
        actual_ac = float(item.get("cumulative_actual_commitments_ac_usd") or 0.0)
        mr_earmarked = max(
            0.0, float(item.get("management_reserve_earmarked_usd") or 0.0)
        )

        required_planned_usd = planned_pv + mr_earmarked
        peak_demand_usd = max(required_planned_usd, actual_ac)

        if required_planned_usd > funding_limit:
            planned_breach_period_ids.append(period_id)
            issues.append(
                f"Periodo '{period_id}' excede el límite de financiamiento en demanda planificada ({required_planned_usd:.2f} > {funding_limit:.2f} USD)."
            )

        if actual_ac > funding_limit:
            actual_commitment_breach_period_ids.append(period_id)
            issues.append(
                f"Periodo '{period_id}' excede el límite de financiamiento en compromisos reales AC ({actual_ac:.2f} > {funding_limit:.2f} USD)."
            )

        if peak_demand_usd > funding_limit:
            deficit = peak_demand_usd - funding_limit
            if deficit > max_deficit:
                max_deficit = deficit
        elif funding_limit > 0.0:
            headroom_pct = ((funding_limit - peak_demand_usd) / funding_limit) * 100.0
            if headroom_pct < min_headroom_pct:
                tight_headroom_period_ids.append(period_id)
                issues.append(
                    f"Periodo '{period_id}' presenta margen de liquidez estrecho ({headroom_pct:.2f}% < {min_headroom_pct:.2f}%)."
                )

    max_funding_deficit_usd = round(max_deficit, 2)

    if (
        len(planned_breach_period_ids) > 0
        or len(actual_commitment_breach_period_ids) > 0
    ):
        funding_reconciliation_status = "FUNDING_CAP_BREACHED"
    elif len(tight_headroom_period_ids) > 0:
        funding_reconciliation_status = "HEADROOM_CONSTRAINED"
    else:
        funding_reconciliation_status = "RECONCILED"

    return {
        "total_periods": total_periods,
        "planned_breach_period_ids": planned_breach_period_ids,
        "actual_commitment_breach_period_ids": actual_commitment_breach_period_ids,
        "tight_headroom_period_ids": tight_headroom_period_ids,
        "max_funding_deficit_usd": max_funding_deficit_usd,
        "funding_reconciliation_status": funding_reconciliation_status,
        "is_funding_reconciled": funding_reconciliation_status == "RECONCILED",
        "issues": issues,
    }


ProjectEVMService.evaluate_evm_funding_limit_reconciliation_and_liquidity = staticmethod(
    evaluate_evm_funding_limit_reconciliation_and_liquidity
)


def evaluate_evm_subcontractor_retainage_and_progress_billing(
    invoices: list[dict[str, Any]],
    *,
    standard_retainage_pct: float = 10.0,
    overbilling_tolerance_pct: float = 5.0,
) -> dict[str, Any]:
    """Evalúa facturación por avance de subcontratistas frente al EV, retención de garantía y liberación de gravámenes (PMI PMBOK §7.4 / §12.3)."""
    if not isinstance(invoices, list):
        return {
            "total_invoices": 0,
            "total_billed_to_date": 0.0,
            "total_net_earned_value": 0.0,
            "total_retainage_withheld": 0.0,
            "overbilled_invoice_ids": [],
            "retainage_shortfall_invoice_ids": [],
            "premature_release_invoice_ids": [],
            "missing_lien_waiver_invoice_ids": [],
            "billing_governance_status": "COMPLIANT",
            "recommendations": [],
        }

    ret_pct = float(
        standard_retainage_pct if standard_retainage_pct is not None else 10.0
    )
    tol_pct = float(
        overbilling_tolerance_pct if overbilling_tolerance_pct is not None else 5.0
    )

    total_invoices = 0
    sum_billed = 0.0
    sum_net_ev = 0.0
    sum_retainage_withheld = 0.0

    overbilled_invoice_ids: list[str] = []
    retainage_shortfall_invoice_ids: list[str] = []
    premature_release_invoice_ids: list[str] = []
    missing_lien_waiver_invoice_ids: list[str] = []
    recommendations: list[str] = []

    for idx, item in enumerate(invoices):
        if not isinstance(item, dict):
            continue
        total_invoices += 1
        invoice_id = str(item.get("invoice_id") or f"INV-{idx + 1}").strip()
        billed = max(0.0, float(item.get("billed_to_date") or 0.0))
        verified_ev = max(0.0, float(item.get("verified_ev_to_date") or 0.0))
        retainage_withheld = max(0.0, float(item.get("retainage_withheld") or 0.0))
        lien_waiver_signed = bool(item.get("lien_waiver_signed", True))
        substantial_completion = bool(
            item.get("substantial_completion_reached", False)
        )
        retainage_released = max(0.0, float(item.get("retainage_released") or 0.0))
        backcharge = max(0.0, float(item.get("defective_work_backcharge") or 0.0))

        net_earned_value = max(0.0, verified_ev - backcharge)
        sum_billed += billed
        sum_net_ev += net_earned_value
        sum_retainage_withheld += retainage_withheld

        if net_earned_value > 0.0:
            front_loading_pct = round(
                ((billed - net_earned_value) / net_earned_value) * 100.0, 2
            )
        elif billed > 0.0:
            front_loading_pct = 100.0
        else:
            front_loading_pct = 0.0

        if front_loading_pct > tol_pct:
            overbilled_invoice_ids.append(invoice_id)
            recommendations.append(
                f"Ajustar factura '{invoice_id}' por sobrefacturación frente a EV neto ({front_loading_pct:.2f}% > {tol_pct:.2f}%)."
            )

        expected_retainage = round(billed * (ret_pct / 100.0), 2)
        retainage_shortfall = round(
            max(0.0, expected_retainage - (retainage_withheld + retainage_released)),
            2,
        )
        if retainage_shortfall > 0.0:
            retainage_shortfall_invoice_ids.append(invoice_id)
            recommendations.append(
                f"Retener {retainage_shortfall:.2f} adicionales en factura '{invoice_id}' para cubrir la garantía contractual del {ret_pct:.1f}%."
            )

        if retainage_released > 0.0 and not substantial_completion:
            premature_release_invoice_ids.append(invoice_id)
            recommendations.append(
                f"Bloquear liberación prematura de retención en factura '{invoice_id}' hasta alcanzar terminación sustancial."
            )

        if billed > 0.0 and not lien_waiver_signed:
            missing_lien_waiver_invoice_ids.append(invoice_id)
            recommendations.append(
                f"Exigir firma de certificado de liberación de gravámenes (lien waiver) antes de pagar factura '{invoice_id}'."
            )

    if (
        len(premature_release_invoice_ids) > 0
        or len(missing_lien_waiver_invoice_ids) > 0
        or len(overbilled_invoice_ids) > 1
    ):
        billing_governance_status = "CRITICAL"
    elif (
        len(overbilled_invoice_ids) == 1
        or len(retainage_shortfall_invoice_ids) > 0
    ):
        billing_governance_status = "WARNING"
    else:
        billing_governance_status = "COMPLIANT"

    return {
        "total_invoices": total_invoices,
        "total_billed_to_date": round(sum_billed, 2),
        "total_net_earned_value": round(sum_net_ev, 2),
        "total_retainage_withheld": round(sum_retainage_withheld, 2),
        "overbilled_invoice_ids": overbilled_invoice_ids,
        "retainage_shortfall_invoice_ids": retainage_shortfall_invoice_ids,
        "premature_release_invoice_ids": premature_release_invoice_ids,
        "missing_lien_waiver_invoice_ids": missing_lien_waiver_invoice_ids,
        "billing_governance_status": billing_governance_status,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_subcontractor_retainage_and_progress_billing = staticmethod(
    evaluate_evm_subcontractor_retainage_and_progress_billing
)


def evaluate_evm_fx_currency_volatility_and_hedging_coverage(
    currency_tranches: Sequence[Mapping[str, Any]] | None,
    *,
    fx_management_reserve: float = 0.0,
    max_unhedged_exposure_pct: float = 20.0,
    max_fx_variance_pct: float = 5.0,
) -> dict[str, Any]:
    """PMBOK §7.3 & §11.5 — volatilidad cambiaria (FX), exposición no cubierta y erosión de reserva."""
    if (
        currency_tranches is None
        or isinstance(currency_tranches, (str, bytes))
        or not isinstance(currency_tranches, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = currency_tranches

    reserve = max(0.0, float(fx_management_reserve or 0.0))
    max_unhedged_pct = max(0.0, float(max_unhedged_exposure_pct or 0.0))
    max_var_pct = max(0.0, float(max_fx_variance_pct or 0.0))

    total_tranches = 0
    sum_baseline_base_cost = 0.0
    sum_unhedged_base_exposure = 0.0
    sum_fx_loss_base = 0.0
    volatile_tranche_ids: list[str] = []
    underhedged_tranche_ids: list[str] = []
    recommendations: list[str] = []

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            continue
        total_tranches += 1
        tranche_id = (
            str(item.get("tranche_id") or item.get("id") or f"FX-{idx}").strip()
            or f"FX-{idx}"
        )
        currency_code = str(item.get("currency_code") or "FX").strip().upper() or "FX"
        baseline_amount_local = max(0.0, float(item.get("baseline_amount_local") or 0.0))
        baseline_fx_rate = float(item.get("baseline_fx_rate_to_base") or 0.0)
        spot_fx_rate = float(item.get("spot_fx_rate_to_base") or 0.0)
        raw_hedged = item.get("hedged_ratio_pct")
        hedged_ratio_pct = min(
            100.0,
            max(0.0, float(raw_hedged if raw_hedged is not None else 0.0)),
        )

        baseline_base_cost = (
            baseline_amount_local * baseline_fx_rate if baseline_fx_rate > 0.0 else 0.0
        )
        unhedged_ratio = max(0.0, min(1.0, 1.0 - (hedged_ratio_pct / 100.0)))
        unhedged_base_exposure = baseline_base_cost * unhedged_ratio
        fx_loss_base = (
            max(
                0.0,
                baseline_amount_local
                * (spot_fx_rate - baseline_fx_rate)
                * unhedged_ratio,
            )
            if baseline_fx_rate > 0.0 and spot_fx_rate > 0.0
            else 0.0
        )
        fx_rate_drift_pct = (
            ((spot_fx_rate - baseline_fx_rate) / baseline_fx_rate) * 100.0
            if baseline_fx_rate > 0.0
            else 0.0
        )

        sum_baseline_base_cost += baseline_base_cost
        sum_unhedged_base_exposure += unhedged_base_exposure
        sum_fx_loss_base += fx_loss_base

        if fx_rate_drift_pct > max_var_pct:
            volatile_tranche_ids.append(tranche_id)
            recommendations.append(
                f"Tramo '{tranche_id}' ({currency_code}) presenta apreciación adversa del {fx_rate_drift_pct:.2f}% (> {max_var_pct:.2f}%); activar cobertura o cláusula de ajuste cambiario."
            )

        if (unhedged_ratio * 100.0) > max_unhedged_pct and fx_rate_drift_pct > 0.0:
            underhedged_tranche_ids.append(tranche_id)
            recommendations.append(
                f"Incrementar cobertura forward/swap en tramo '{tranche_id}' ({currency_code}): exposición descubierta del {unhedged_ratio * 100.0:.1f}% supera el máximo de {max_unhedged_pct:.1f}%."
            )

    total_baseline_base_cost = round(sum_baseline_base_cost, 2)
    total_unhedged_base_exposure = round(sum_unhedged_base_exposure, 2)
    unhedged_exposure_share_pct = (
        round((sum_unhedged_base_exposure / sum_baseline_base_cost) * 100.0, 2)
        if sum_baseline_base_cost > 0.0
        else 0.0
    )
    total_fx_loss_base = round(sum_fx_loss_base, 2)
    fx_reserve_coverage_ratio = (
        round(reserve / total_fx_loss_base, 2) if total_fx_loss_base > 0.0 else 1.0
    )

    if total_fx_loss_base > reserve:
        recommendations.append(
            f"La pérdida cambiaria acumulada ({total_fx_loss_base:.2f}) excede la reserva de gestión FX ({reserve:.2f}); gestionar solicitud de fondos suplementarios."
        )

    if total_fx_loss_base > reserve or len(volatile_tranche_ids) >= 2:
        fx_governance_status = "CRITICAL"
    elif volatile_tranche_ids or underhedged_tranche_ids:
        fx_governance_status = "WARNING"
    else:
        fx_governance_status = "HEDGED"

    return {
        "total_tranches": total_tranches,
        "total_baseline_base_cost": total_baseline_base_cost,
        "total_unhedged_base_exposure": total_unhedged_base_exposure,
        "unhedged_exposure_share_pct": unhedged_exposure_share_pct,
        "total_fx_loss_base": total_fx_loss_base,
        "fx_reserve_coverage_ratio": fx_reserve_coverage_ratio,
        "volatile_tranche_ids": volatile_tranche_ids,
        "underhedged_tranche_ids": underhedged_tranche_ids,
        "fx_governance_status": fx_governance_status,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_fx_currency_volatility_and_hedging_coverage = staticmethod(
    evaluate_evm_fx_currency_volatility_and_hedging_coverage
)


def evaluate_evm_time_and_materials_nte_and_rate_blend(
    contracts: list[dict[str, Any]],
    *,
    nte_warning_threshold_pct: float = 85.0,
    max_rate_drift_pct: float = 10.0,
) -> dict[str, Any]:
    """Evaluate PMI PMBOK §7.4 & §12.1 Time & Materials (T&M) NTE ceiling burn and blended hourly rate drift."""
    nte_breach_contract_ids: list[str] = []
    nte_threshold_warning_contract_ids: list[str] = []
    seniority_mix_rate_drift_contract_ids: list[str] = []
    recommendations: list[str] = []

    valid_contracts = (
        [
            c
            for c in contracts
            if isinstance(c, dict) and str(c.get("contract_id", "")).strip()
        ]
        if isinstance(contracts, list)
        else []
    )

    total_nte_ceiling = 0.0
    total_actual_billed = 0.0

    for contract in valid_contracts:
        contract_id = str(contract.get("contract_id", "")).strip()
        nte_ceiling_amount = float(contract.get("nte_ceiling_amount", 0.0) or 0.0)
        actual_hours_logged = float(contract.get("actual_hours_logged", 0.0) or 0.0)
        actual_billed_amount = float(contract.get("actual_billed_amount", 0.0) or 0.0)
        baseline_blended_hourly_rate = float(
            contract.get("baseline_blended_hourly_rate", 0.0) or 0.0
        )
        pct_scope_completed = float(contract.get("pct_scope_completed", 0.0) or 0.0)

        total_nte_ceiling += nte_ceiling_amount
        total_actual_billed += actual_billed_amount

        actual_blended_rate = (
            round(actual_billed_amount / actual_hours_logged, 2)
            if actual_hours_logged > 0.0
            else 0.0
        )
        rate_drift_pct = (
            round(
                ((actual_blended_rate - baseline_blended_hourly_rate) / baseline_blended_hourly_rate)
                * 100.0,
                2,
            )
            if actual_hours_logged > 0.0 and baseline_blended_hourly_rate > 0.0
            else 0.0
        )
        nte_burn_pct = (
            round((actual_billed_amount / nte_ceiling_amount) * 100.0, 2)
            if nte_ceiling_amount > 0.0
            else 0.0
        )

        if pct_scope_completed > 0.0:
            projected_eac_tm = round(
                actual_billed_amount / (pct_scope_completed / 100.0), 2
            )
        else:
            projected_eac_tm = (
                actual_billed_amount
                if actual_billed_amount == 0.0
                else round(nte_ceiling_amount * 2.0, 2)
            )

        if (
            actual_billed_amount > nte_ceiling_amount
            or projected_eac_tm > nte_ceiling_amount
        ):
            nte_breach_contract_ids.append(contract_id)

        if (
            nte_burn_pct >= nte_warning_threshold_pct
            and actual_billed_amount <= nte_ceiling_amount
        ):
            nte_threshold_warning_contract_ids.append(contract_id)

        if rate_drift_pct > max_rate_drift_pct:
            seniority_mix_rate_drift_contract_ids.append(contract_id)

    total_nte_ceiling = round(total_nte_ceiling, 2)
    total_actual_billed = round(total_actual_billed, 2)

    if nte_breach_contract_ids:
        recommendations.append(
            f"Initiate formal contract change orders or stop-work directives for T&M contracts breaching NTE ceilings: {', '.join(nte_breach_contract_ids)}."
        )
    if nte_threshold_warning_contract_ids:
        recommendations.append(
            f"Enforce pre-approval of remaining T&M hours on contracts approaching NTE ceiling (>={nte_warning_threshold_pct:.1f}%): {', '.join(nte_threshold_warning_contract_ids)}."
        )
    if seniority_mix_rate_drift_contract_ids:
        recommendations.append(
            f"Rebalance vendor staffing seniority pyramid to correct blended hourly rate drift (>{max_rate_drift_pct:.1f}%) on: {', '.join(seniority_mix_rate_drift_contract_ids)}."
        )

    if nte_breach_contract_ids:
        tm_governance_status = "CRITICAL"
    elif nte_threshold_warning_contract_ids or seniority_mix_rate_drift_contract_ids:
        tm_governance_status = "WARNING"
    else:
        tm_governance_status = "WITHIN_NTE"

    return {
        "total_contracts": len(valid_contracts),
        "total_nte_ceiling": total_nte_ceiling,
        "total_actual_billed": total_actual_billed,
        "nte_breach_contract_ids": nte_breach_contract_ids,
        "nte_threshold_warning_contract_ids": nte_threshold_warning_contract_ids,
        "seniority_mix_rate_drift_contract_ids": seniority_mix_rate_drift_contract_ids,
        "tm_governance_status": tm_governance_status,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_time_and_materials_nte_and_rate_blend = staticmethod(
    evaluate_evm_time_and_materials_nte_and_rate_blend
)


def evaluate_evm_economic_price_adjustment_and_inflation_erosion(
    work_packages: Sequence[Mapping[str, Any]] | None,
    *,
    epa_escalation_reserve: float = 0.0,
    epa_trigger_threshold_pct: float = 4.0,
    epa_cap_pct: float = 12.0,
) -> dict[str, Any]:
    """PMBOK §7.3 & §12.1.1.6 — contratos FP-EPA: ajuste económico de precios y erosión inflacionaria."""
    if (
        work_packages is None
        or isinstance(work_packages, (str, bytes))
        or not isinstance(work_packages, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = work_packages

    reserve = max(0.0, float(epa_escalation_reserve or 0.0))
    trigger_pct = max(0.0, float(epa_trigger_threshold_pct or 0.0))
    cap_pct = max(0.0, float(epa_cap_pct or 0.0))

    total_work_packages = 0
    sum_remaining_bac = 0.0
    sum_inflation_cost_impact = 0.0
    epa_triggered_wp_ids: list[str] = []
    epa_cap_breached_wp_ids: list[str] = []
    unindexed_exposure_wp_ids: list[str] = []
    recommendations: list[str] = []

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            continue
        total_work_packages += 1
        wp_id = (
            str(item.get("wp_id") or item.get("id") or f"WP-{idx}").strip()
            or f"WP-{idx}"
        )
        remaining_bac = max(0.0, float(item.get("remaining_bac") or 0.0))
        baseline_cpi = float(item.get("baseline_cpi_index") or 0.0)
        current_cpi = float(item.get("current_cpi_index") or 0.0)
        has_epa_clause = bool(item.get("has_epa_clause", True))

        index_escalation_pct = (
            ((current_cpi - baseline_cpi) / baseline_cpi) * 100.0
            if baseline_cpi > 0.0
            else 0.0
        )
        _effective_escalation_pct = (
            max(0.0, index_escalation_pct - trigger_pct)
            if index_escalation_pct > trigger_pct
            else 0.0
        )
        inflation_cost_impact = (
            remaining_bac * (index_escalation_pct / 100.0)
            if index_escalation_pct > trigger_pct
            else 0.0
        )

        sum_remaining_bac += remaining_bac
        sum_inflation_cost_impact += inflation_cost_impact

        if index_escalation_pct > trigger_pct:
            epa_triggered_wp_ids.append(wp_id)
            recommendations.append(
                f"Paquete '{wp_id}' supera el umbral de activación EPA ({index_escalation_pct:.2f}% > {trigger_pct:.2f}%); aplicar ajuste de precios sobre saldo BAC."
            )

        if index_escalation_pct > cap_pct:
            epa_cap_breached_wp_ids.append(wp_id)
            recommendations.append(
                f"Paquete '{wp_id}' excede el tope contractual EPA ({index_escalation_pct:.2f}% > {cap_pct:.2f}%); renegociar términos o activar reserva de gestión."
            )

        if index_escalation_pct > trigger_pct and not has_epa_clause:
            unindexed_exposure_wp_ids.append(wp_id)
            recommendations.append(
                f"Paquete '{wp_id}' carece de cláusula EPA frente a escalada inflacionaria del {index_escalation_pct:.2f}%; evaluar riesgo de incumplimiento del proveedor."
            )

    total_remaining_bac = round(sum_remaining_bac, 2)
    total_inflation_cost_impact = round(sum_inflation_cost_impact, 2)
    reserve_shortfall = round(max(0.0, total_inflation_cost_impact - reserve), 2)

    if reserve_shortfall > 0.0:
        recommendations.append(
            f"El impacto inflacionario total ({total_inflation_cost_impact:.2f}) excede la reserva EPA ({reserve:.2f}) con un déficit de {reserve_shortfall:.2f}."
        )

    if (
        reserve_shortfall > 0.0
        or epa_cap_breached_wp_ids
        or unindexed_exposure_wp_ids
    ):
        epa_governance_status = "CRITICAL"
    elif epa_triggered_wp_ids:
        epa_governance_status = "WARNING"
    else:
        epa_governance_status = "STABLE"

    return {
        "total_work_packages": total_work_packages,
        "total_remaining_bac": total_remaining_bac,
        "total_inflation_cost_impact": total_inflation_cost_impact,
        "reserve_shortfall": reserve_shortfall,
        "epa_triggered_wp_ids": epa_triggered_wp_ids,
        "epa_cap_breached_wp_ids": epa_cap_breached_wp_ids,
        "unindexed_exposure_wp_ids": unindexed_exposure_wp_ids,
        "epa_governance_status": epa_governance_status,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_economic_price_adjustment_and_inflation_erosion = staticmethod(
    evaluate_evm_economic_price_adjustment_and_inflation_erosion
)


def evaluate_evm_capex_opex_classification_and_amortization(
    cost_entries: list[dict[str, Any]],
    *,
    min_capex_share_target_pct: float = 50.0,
    max_misclassification_pct: float = 5.0,
) -> dict[str, Any]:
    """Evaluate PMI PMBOK §7.4 & §1.2.6 CapEx vs OpEx accounting classification eligibility (ASC 350-40 / IAS 38)."""
    improper_capitalization_entry_ids: list[str] = []
    unclaimed_capex_entry_ids: list[str] = []
    recommendations: list[str] = []

    valid_entries = (
        [
            e
            for e in cost_entries
            if isinstance(e, dict) and str(e.get("entry_id", "")).strip()
        ]
        if isinstance(cost_entries, list)
        else []
    )

    total_recorded_capex = 0.0
    total_recorded_opex = 0.0
    improper_capex_amount = 0.0

    for entry in valid_entries:
        entry_id = str(entry.get("entry_id", "")).strip()
        project_stage = (
            str(entry.get("project_stage", "APPLICATION_DEVELOPMENT")).strip().upper()
        )
        recorded_category = (
            str(entry.get("recorded_category", "OPEX")).strip().upper()
        )
        amount = float(entry.get("amount", 0.0) or 0.0)
        is_maintenance_or_training = bool(
            entry.get("is_maintenance_or_training", False)
        )
        useful_life_months = int(
            entry.get("useful_life_months", 36)
            if entry.get("useful_life_months") is not None
            else 36
        )

        is_capex_eligible = (
            project_stage == "APPLICATION_DEVELOPMENT"
            and not is_maintenance_or_training
            and useful_life_months >= 12
        )

        if recorded_category == "CAPEX":
            total_recorded_capex += amount
            if not is_capex_eligible:
                improper_capitalization_entry_ids.append(entry_id)
                improper_capex_amount += amount
        else:
            total_recorded_opex += amount
            if is_capex_eligible:
                unclaimed_capex_entry_ids.append(entry_id)

    total_recorded_capex = round(total_recorded_capex, 2)
    total_recorded_opex = round(total_recorded_opex, 2)
    total_spend = round(total_recorded_capex + total_recorded_opex, 2)
    improper_capex_amount = round(improper_capex_amount, 2)
    adjusted_valid_capex = round(total_recorded_capex - improper_capex_amount, 2)

    valid_capex_share_pct = (
        round((adjusted_valid_capex / total_spend) * 100.0, 2)
        if total_spend > 0.0
        else 100.0
    )
    misclassification_share_pct = (
        round((improper_capex_amount / total_spend) * 100.0, 2)
        if total_spend > 0.0
        else 0.0
    )

    if improper_capitalization_entry_ids:
        recommendations.append(
            f"Reclassify improper CapEx entries (preliminary/post-implementation/training or useful life <12m) to OpEx: {', '.join(improper_capitalization_entry_ids)}."
        )
    if unclaimed_capex_entry_ids:
        recommendations.append(
            f"Capitalize eligible APPLICATION_DEVELOPMENT software/infrastructure assets currently expensed as OpEx: {', '.join(unclaimed_capex_entry_ids)}."
        )
    if total_spend > 0.0 and valid_capex_share_pct < min_capex_share_target_pct:
        recommendations.append(
            f"Review work package structure to improve valid CapEx ratio ({valid_capex_share_pct:.2f}% < {min_capex_share_target_pct:.2f}%)."
        )

    if (
        improper_capitalization_entry_ids
        and misclassification_share_pct > max_misclassification_pct
    ):
        accounting_governance_status = "AUDIT_RISK"
    elif (
        improper_capitalization_entry_ids
        or unclaimed_capex_entry_ids
        or (total_spend > 0.0 and valid_capex_share_pct < min_capex_share_target_pct)
    ):
        accounting_governance_status = "WARNING"
    else:
        accounting_governance_status = "COMPLIANT"

    return {
        "total_entries": len(valid_entries),
        "total_recorded_capex": total_recorded_capex,
        "total_recorded_opex": total_recorded_opex,
        "adjusted_valid_capex": adjusted_valid_capex,
        "improper_capex_amount": improper_capex_amount,
        "valid_capex_share_pct": valid_capex_share_pct,
        "misclassification_share_pct": misclassification_share_pct,
        "improper_capitalization_entry_ids": improper_capitalization_entry_ids,
        "unclaimed_capex_entry_ids": unclaimed_capex_entry_ids,
        "accounting_governance_status": accounting_governance_status,
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_capex_opex_classification_and_amortization = staticmethod(
    evaluate_evm_capex_opex_classification_and_amortization
)


def evaluate_evm_learning_curve_cost_improvement_and_productivity(
    batches: list[dict[str, Any]],
    *,
    target_learning_rate_pct: float = 85.0,
    max_productivity_stall_pct: float = 10.0,
) -> dict[str, Any]:
    """Evaluate PMI PMBOK §7.2.2 & §7.4 Wright/Crawford learning curve cost/productivity improvement across doubling batches."""
    stalled_learning_batch_ids: list[str] = []
    regressed_batch_ids: list[str] = []
    recommendations: list[str] = []

    valid_batches = (
        [
            b
            for b in batches
            if isinstance(b, dict) and str(b.get("batch_id", "")).strip()
        ]
        if isinstance(batches, list)
        else []
    )

    learning_ratio = float(target_learning_rate_pct) / 100.0

    for batch in valid_batches:
        batch_id = str(batch.get("batch_id", "")).strip()
        doubling_step_index = max(1, int(batch.get("doubling_step_index", 1) or 1))
        first_batch_unit_hours = float(batch.get("first_batch_unit_hours", 0.0) or 0.0)
        actual_unit_hours = float(batch.get("actual_unit_hours", 0.0) or 0.0)

        expected_unit_hours = (
            first_batch_unit_hours * (learning_ratio ** (doubling_step_index - 1))
            if first_batch_unit_hours > 0.0
            else 0.0
        )
        stall_variance_pct = (
            ((actual_unit_hours - expected_unit_hours) / expected_unit_hours) * 100.0
            if expected_unit_hours > 0.0
            else 0.0
        )

        if stall_variance_pct > max_productivity_stall_pct:
            stalled_learning_batch_ids.append(batch_id)

        if doubling_step_index > 1 and actual_unit_hours > first_batch_unit_hours:
            regressed_batch_ids.append(batch_id)

    if regressed_batch_ids:
        recommendations.append(
            f"Investigate productivity regression where subsequent batches exceed initial unit hours: {', '.join(regressed_batch_ids)}."
        )
    if stalled_learning_batch_ids:
        recommendations.append(
            f"Remove tooling/process bottlenecks or update ETC estimates for batches stalling above learning curve target ({target_learning_rate_pct:.1f}%): {', '.join(stalled_learning_batch_ids)}."
        )

    if regressed_batch_ids or len(stalled_learning_batch_ids) >= 2:
        learning_governance_status = "REGRESSED"
    elif stalled_learning_batch_ids:
        learning_governance_status = "WARNING"
    else:
        learning_governance_status = "ON_CURVE"

    return {
        "total_batches": len(valid_batches),
        "stalled_learning_batch_ids": stalled_learning_batch_ids,
        "regressed_batch_ids": regressed_batch_ids,
        "learning_governance_status": learning_governance_status,
        "is_on_learning_curve": learning_governance_status == "ON_CURVE",
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_learning_curve_cost_improvement_and_productivity = staticmethod(
    evaluate_evm_learning_curve_cost_improvement_and_productivity
)


def evaluate_evm_milestone_payment_holdback_and_acceptance_gate(
    milestones: list[dict[str, Any]],
    *,
    max_advance_disbursement_pct: float = 20.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Milestone Payment Gate, Deliverable Sign-Off Holdback & Premature Disbursement Evaluator."""
    valid_milestones: list[dict[str, Any]] = []
    for item in milestones or []:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("milestone_id") or "").strip()
        if not mid:
            continue
        valid_milestones.append({**item, "_mid": mid})

    if not valid_milestones:
        return {
            "total_milestones": 0,
            "total_scheduled_payments": 0.0,
            "total_disbursed_amount": 0.0,
            "unaccepted_disbursed_amount": 0.0,
            "advance_disbursement_share_pct": 0.0,
            "premature_disbursement_milestone_ids": [],
            "punchlist_bypass_milestone_ids": [],
            "overpaid_milestone_ids": [],
            "payment_gate_status": "GATED",
            "is_payment_gate_compliant": True,
            "recommendations": [],
        }

    raw_scheduled_sum = 0.0
    raw_disbursed_sum = 0.0
    raw_unaccepted_disbursed_sum = 0.0

    premature_disbursement_milestone_ids: list[str] = []
    punchlist_bypass_milestone_ids: list[str] = []
    overpaid_milestone_ids: list[str] = []

    for ms in valid_milestones:
        mid = ms["_mid"]
        sched = max(0.0, float(ms.get("scheduled_payment_amount", 0.0) or 0.0))
        disb = max(0.0, float(ms.get("disbursed_amount", 0.0) or 0.0))
        accepted = bool(ms.get("deliverable_formally_accepted", False))
        defects = max(0, int(ms.get("open_punchlist_defects", 0) or 0))
        holdback = max(0.0, float(ms.get("warranty_holdback_retained", 0.0) or 0.0))

        raw_scheduled_sum += sched
        raw_disbursed_sum += disb
        if not accepted:
            raw_unaccepted_disbursed_sum += disb

        if not accepted and disb > sched * (max_advance_disbursement_pct / 100.0):
            premature_disbursement_milestone_ids.append(mid)

        if accepted and defects > 0 and disb >= sched and holdback <= 0.0:
            punchlist_bypass_milestone_ids.append(mid)

        if disb > sched:
            overpaid_milestone_ids.append(mid)

    total_scheduled_payments = round(raw_scheduled_sum, 2)
    total_disbursed_amount = round(raw_disbursed_sum, 2)
    unaccepted_disbursed_amount = round(raw_unaccepted_disbursed_sum, 2)

    if total_scheduled_payments > 0:
        advance_disbursement_share_pct = round(
            (unaccepted_disbursed_amount / total_scheduled_payments) * 100.0, 2
        )
    else:
        advance_disbursement_share_pct = 0.0

    recommendations: list[str] = []
    if premature_disbursement_milestone_ids:
        recommendations.append(
            f"Halt premature disbursement exceeding {max_advance_disbursement_pct}% advance cap prior to formal deliverable acceptance on milestone(s): {', '.join(premature_disbursement_milestone_ids)}."
        )
    if overpaid_milestone_ids:
        recommendations.append(
            f"Recover or offset milestone overpayment exceeding scheduled contract value on milestone(s): {', '.join(overpaid_milestone_ids)}."
        )
    if punchlist_bypass_milestone_ids:
        recommendations.append(
            f"Enforce warranty/punchlist holdback retention until open defects are closed on milestone(s): {', '.join(punchlist_bypass_milestone_ids)}."
        )
    if advance_disbursement_share_pct > max_advance_disbursement_pct:
        recommendations.append(
            f"Reduce portfolio advance disbursement share ({advance_disbursement_share_pct:.2f}%) below {max_advance_disbursement_pct:.2f}% ceiling."
        )

    if premature_disbursement_milestone_ids or overpaid_milestone_ids:
        payment_gate_status = "DISBURSEMENT_BREACH"
    elif (
        punchlist_bypass_milestone_ids
        or advance_disbursement_share_pct > max_advance_disbursement_pct
    ):
        payment_gate_status = "WARNING"
    else:
        payment_gate_status = "GATED"

    return {
        "total_milestones": len(valid_milestones),
        "total_scheduled_payments": total_scheduled_payments,
        "total_disbursed_amount": total_disbursed_amount,
        "unaccepted_disbursed_amount": unaccepted_disbursed_amount,
        "advance_disbursement_share_pct": advance_disbursement_share_pct,
        "premature_disbursement_milestone_ids": premature_disbursement_milestone_ids,
        "punchlist_bypass_milestone_ids": punchlist_bypass_milestone_ids,
        "overpaid_milestone_ids": overpaid_milestone_ids,
        "payment_gate_status": payment_gate_status,
        "is_payment_gate_compliant": payment_gate_status == "GATED",
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_milestone_payment_holdback_and_acceptance_gate = staticmethod(
    evaluate_evm_milestone_payment_holdback_and_acceptance_gate
)


def evaluate_evm_value_engineering_target_costing_and_worth_index(
    functions: Any,
    *,
    min_value_index: float = 0.85,
    max_over_engineering_cost_ratio: float = 1.25,
) -> Dict[str, object]:
    """Evaluación PMBOK 7.2 y 8.1: value engineering y target costing.

    Calcula por función el índice de valor (worth / costo estimado) y el
    ratio contra el costo objetivo admisible, detectando funciones de
    bajo valor, sobrecostos de over-engineering y gold-plating, y
    sumando el ahorro potencial de costo.
    """
    entries = functions if isinstance(functions, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    low_value_index_function_ids: List[str] = []
    target_cost_exceeded_function_ids: List[str] = []
    gold_plating_function_ids: List[str] = []
    total_potential_cost_savings = 0.0

    for item in rows:
        function_id = item.get("function_id")
        estimated_cost = item.get("estimated_function_cost", 0.0)
        worth = item.get("essential_function_worth", 0.0)
        target_cost = item.get("target_allowable_cost", 0.0)

        estimated_val = estimated_cost if isinstance(estimated_cost, (int, float)) else 0.0
        worth_val = worth if isinstance(worth, (int, float)) else 0.0
        target_val = target_cost if isinstance(target_cost, (int, float)) else 0.0

        if estimated_val > 0:
            value_index = round(worth_val / estimated_val, 2)
        else:
            value_index = 1.0

        if target_val > 0:
            target_cost_ratio = round(estimated_val / target_val, 2)
        else:
            target_cost_ratio = 1.0

        if value_index < min_value_index:
            low_value_index_function_ids.append(function_id)

        if target_cost_ratio > max_over_engineering_cost_ratio:
            target_cost_exceeded_function_ids.append(function_id)

        if item.get("is_gold_plated_non_essential", False) is True:
            gold_plating_function_ids.append(function_id)

        total_potential_cost_savings += max(0.0, estimated_val - worth_val)

    total_potential_cost_savings = round(total_potential_cost_savings, 2)

    if gold_plating_function_ids or target_cost_exceeded_function_ids:
        value_engineering_status = "GOLD_PLATING_OR_SEVERE_OVERRUN"
    elif low_value_index_function_ids:
        value_engineering_status = "SUBOPTIMAL_VALUE_INDEX"
    else:
        value_engineering_status = "VALUE_OPTIMIZED"

    return {
        "total_functions_evaluated": len(rows),
        "low_value_index_function_ids": low_value_index_function_ids,
        "target_cost_exceeded_function_ids": target_cost_exceeded_function_ids,
        "gold_plating_function_ids": gold_plating_function_ids,
        "total_potential_cost_savings": total_potential_cost_savings,
        "value_engineering_status": value_engineering_status,
        "is_value_engineered_compliant": value_engineering_status == "VALUE_OPTIMIZED",
    }


ProjectEVMService.evaluate_evm_value_engineering_target_costing_and_worth_index = staticmethod(
    evaluate_evm_value_engineering_target_costing_and_worth_index
)


def evaluate_evm_contingency_and_management_reserve_drawdown_governance(
    drawdowns: list[dict[str, Any]],
    *,
    contingency_reserve_initial: float = 10000.0,
    management_reserve_initial: float = 10000.0,
    project_percent_complete: float = 50.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §11.2 — EVM Contingency vs Management Reserve Burn Rate, Unapproved Drawdown & Risk Trigger Linkage Evaluator."""
    valid_drawdowns: list[dict[str, Any]] = []
    if isinstance(drawdowns, (list, tuple)):
        for item in drawdowns:
            if not isinstance(item, dict):
                continue
            did = str(item.get("drawdown_id") or "").strip()
            if not did:
                continue
            valid_drawdowns.append({**item, "_did": did})

    if not valid_drawdowns:
        return {
            "total_drawdowns_evaluated": 0,
            "contingency_consumed": 0.0,
            "management_consumed": 0.0,
            "contingency_consumed_pct": 0.0,
            "reserve_burn_to_progress_ratio": 0.0,
            "unlinked_contingency_drawdown_ids": [],
            "unauthorized_management_drawdown_ids": [],
            "reserve_governance_status": "RESERVE_PROTECTED",
            "is_reserve_drawdown_compliant": True,
            "recommendations": [],
        }

    raw_contingency_sum = 0.0
    raw_management_sum = 0.0
    unlinked_contingency_drawdown_ids: list[str] = []
    unauthorized_management_drawdown_ids: list[str] = []

    for dd in valid_drawdowns:
        did = dd["_did"]
        rtype = str(dd.get("reserve_type") or "").strip().upper()
        amt = max(0.0, float(dd.get("amount", 0.0) or 0.0))
        has_risk = bool(dd.get("has_linked_risk_id", False))
        has_bcr = bool(dd.get("has_sponsor_bcr_approval", False))

        if rtype == "CONTINGENCY":
            raw_contingency_sum += amt
            if not has_risk:
                unlinked_contingency_drawdown_ids.append(did)
        elif rtype == "MANAGEMENT":
            raw_management_sum += amt
            if not has_bcr:
                unauthorized_management_drawdown_ids.append(did)

    contingency_consumed = round(raw_contingency_sum, 2)
    management_consumed = round(raw_management_sum, 2)

    if contingency_reserve_initial > 0:
        contingency_consumed_pct = round(
            (contingency_consumed / contingency_reserve_initial) * 100.0, 2
        )
    else:
        contingency_consumed_pct = 0.0

    if project_percent_complete > 0:
        reserve_burn_to_progress_ratio = round(
            contingency_consumed_pct / project_percent_complete, 2
        )
    elif contingency_consumed_pct > 0:
        reserve_burn_to_progress_ratio = round(contingency_consumed_pct, 2)
    else:
        reserve_burn_to_progress_ratio = 0.0

    recommendations: list[str] = []
    if unlinked_contingency_drawdown_ids:
        recommendations.append(
            f"Link contingency reserve drawdown(s) to identified Risk Register trigger(s): {', '.join(unlinked_contingency_drawdown_ids)}."
        )
    if unauthorized_management_drawdown_ids:
        recommendations.append(
            f"Obtain formal Sponsor/CCB Baseline Change Request (BCR) approval for management reserve drawdown(s): {', '.join(unauthorized_management_drawdown_ids)}."
        )
    if (
        contingency_consumed > contingency_reserve_initial
        or management_consumed > management_reserve_initial
    ):
        recommendations.append(
            "Re-baseline cost reserves via formal contract/charter modification due to reserve exhaustion."
        )
    if reserve_burn_to_progress_ratio > 1.25:
        recommendations.append(
            f"Curb premature contingency reserve burn (burn-to-progress ratio {reserve_burn_to_progress_ratio:.2f} > 1.25)."
        )

    if (
        unlinked_contingency_drawdown_ids
        or unauthorized_management_drawdown_ids
        or contingency_consumed > contingency_reserve_initial
        or management_consumed > management_reserve_initial
    ):
        reserve_governance_status = "UNAUTHORIZED_OR_EXHAUSTED_BREACH"
    elif reserve_burn_to_progress_ratio > 1.25:
        reserve_governance_status = "PREMATURE_BURN_WARNING"
    else:
        reserve_governance_status = "RESERVE_PROTECTED"

    return {
        "total_drawdowns_evaluated": len(valid_drawdowns),
        "contingency_consumed": contingency_consumed,
        "management_consumed": management_consumed,
        "contingency_consumed_pct": contingency_consumed_pct,
        "reserve_burn_to_progress_ratio": reserve_burn_to_progress_ratio,
        "unlinked_contingency_drawdown_ids": unlinked_contingency_drawdown_ids,
        "unauthorized_management_drawdown_ids": unauthorized_management_drawdown_ids,
        "reserve_governance_status": reserve_governance_status,
        "is_reserve_drawdown_compliant": reserve_governance_status
        == "RESERVE_PROTECTED",
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_contingency_and_management_reserve_drawdown_governance = staticmethod(
    evaluate_evm_contingency_and_management_reserve_drawdown_governance
)


def evaluate_evm_sla_penalty_service_credits_and_earn_back(
    billing_periods: list[dict[str, Any]],
    *,
    min_sla_uptime_pct: float = 99.9,
    max_at_risk_fee_pool_pct: float = 15.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Managed Services SLA Uptime Penalty Deducts, Service Credit Cap & Earn-Back Clawback Evaluator."""
    sla_breach_period_ids: list[str] = []
    uncollected_penalty_period_ids: list[str] = []
    premature_earn_back_period_ids: list[str] = []
    fee_pool_cap_exceeded_period_ids: list[str] = []

    valid_periods = (
        [
            p
            for p in billing_periods
            if isinstance(p, dict) and str(p.get("period_id", "")).strip()
        ]
        if isinstance(billing_periods, list)
        else []
    )

    net_credits_raw = 0.0

    for period in valid_periods:
        period_id = str(period.get("period_id", "")).strip()
        monthly_base_fee = float(period.get("monthly_base_fee", 0.0) or 0.0)
        observed_uptime_pct = float(
            period.get("observed_uptime_pct", 100.0)
            if period.get("observed_uptime_pct") is not None
            else 100.0
        )
        penalty_credit_claimed = float(
            period.get("penalty_credit_claimed", 0.0) or 0.0
        )
        earn_back_credit_applied = float(
            period.get("earn_back_credit_applied", 0.0) or 0.0
        )
        consecutive_clean_months_for_earn_back = int(
            period.get("consecutive_clean_months_for_earn_back", 0) or 0
        )

        net_credits_raw += max(0.0, penalty_credit_claimed) - max(
            0.0, earn_back_credit_applied
        )

        if observed_uptime_pct < min_sla_uptime_pct:
            sla_breach_period_ids.append(period_id)
            if penalty_credit_claimed <= 0.0:
                uncollected_penalty_period_ids.append(period_id)

        if (
            earn_back_credit_applied > 0.0
            and consecutive_clean_months_for_earn_back < 3
        ):
            premature_earn_back_period_ids.append(period_id)

        if (
            monthly_base_fee > 0.0
            and (penalty_credit_claimed / monthly_base_fee) * 100.0
            > max_at_risk_fee_pool_pct
        ):
            fee_pool_cap_exceeded_period_ids.append(period_id)

    net_service_credits_retained = round(net_credits_raw, 2)

    if uncollected_penalty_period_ids or premature_earn_back_period_ids:
        sla_financial_governance_status = "PENALTY_OR_EARNBACK_LEAKAGE"
    elif fee_pool_cap_exceeded_period_ids or sla_breach_period_ids:
        sla_financial_governance_status = "AT_RISK_CAP_EXCEEDED_WARNING"
    else:
        sla_financial_governance_status = "SLA_CREDITS_BALANCED"

    return {
        "total_periods_evaluated": len(valid_periods),
        "sla_breach_period_ids": sla_breach_period_ids,
        "uncollected_penalty_period_ids": uncollected_penalty_period_ids,
        "premature_earn_back_period_ids": premature_earn_back_period_ids,
        "fee_pool_cap_exceeded_period_ids": fee_pool_cap_exceeded_period_ids,
        "net_service_credits_retained": net_service_credits_retained,
        "sla_financial_governance_status": sla_financial_governance_status,
        "is_sla_credit_compliant": sla_financial_governance_status
        == "SLA_CREDITS_BALANCED",
    }


ProjectEVMService.evaluate_evm_sla_penalty_service_credits_and_earn_back = staticmethod(
    evaluate_evm_sla_penalty_service_credits_and_earn_back
)


def evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(
    contracts: Any,
) -> Dict[str, object]:
    """Evaluación PMBOK 12.1.1.6 y 7.4: contratos cost-plus-incentive-fee.

    Calcula por contrato el fee con la fórmula de reparto comprador-
    vendedor, el fee final acotado entre floor y ceiling, el Point of
    Total Assumption (PTA) y las brechas de techo de precio.
    """
    entries = contracts if isinstance(contracts, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    pta_breached_contract_ids: List[str] = []
    min_fee_floor_hit_contract_ids: List[str] = []
    ceiling_price_exceeded_contract_ids: List[str] = []
    total_final_fees_payable = 0.0

    for item in rows:
        contract_id = item.get("contract_id")
        target_cost = item.get("target_cost", 0.0)
        target_fee = item.get("target_fee", 0.0)
        actual_cost = item.get("actual_or_forecast_cost", 0.0)
        fee_floor = item.get("min_fee_floor", 0.0)
        fee_ceiling = item.get("max_fee_ceiling", 0.0)
        seller_share_pct = item.get("seller_cost_overrun_share_pct", 20.0)
        ceiling_price = item.get("ceiling_price", 0.0)

        target_cost_val = target_cost if isinstance(target_cost, (int, float)) else 0.0
        target_fee_val = target_fee if isinstance(target_fee, (int, float)) else 0.0
        actual_val = actual_cost if isinstance(actual_cost, (int, float)) else 0.0
        floor_val = fee_floor if isinstance(fee_floor, (int, float)) else 0.0
        ceiling_val = fee_ceiling if isinstance(fee_ceiling, (int, float)) else 0.0
        share_pct = seller_share_pct if isinstance(seller_share_pct, (int, float)) else 20.0
        ceiling_price_val = ceiling_price if isinstance(ceiling_price, (int, float)) else 0.0

        cost_delta = target_cost_val - actual_val

        raw_fee = target_fee_val + cost_delta * (share_pct / 100.0)
        final_fee = round(min(max(raw_fee, floor_val), ceiling_val), 2)
        total_final_fees_payable += final_fee

        if share_pct < 100.0 and ceiling_price_val > 0:
            pta_cost = round(
                target_cost_val
                + ((ceiling_price_val - (target_cost_val + target_fee_val))
                   / (1.0 - share_pct / 100.0)),
                2,
            )
        else:
            pta_cost = target_cost_val

        if ceiling_price_val > 0 and actual_val > pta_cost:
            pta_breached_contract_ids.append(contract_id)

        if raw_fee < floor_val:
            min_fee_floor_hit_contract_ids.append(contract_id)

        if ceiling_price_val > 0 and (actual_val + final_fee) > ceiling_price_val:
            ceiling_price_exceeded_contract_ids.append(contract_id)

    if pta_breached_contract_ids or ceiling_price_exceeded_contract_ids:
        cpif_governance_status = "CEILING_OR_PTA_BREACH"
    elif min_fee_floor_hit_contract_ids:
        cpif_governance_status = "FEE_FLOOR_EROSION_WARNING"
    else:
        cpif_governance_status = "INCENTIVE_ALIGNED"

    return {
        "total_contracts_evaluated": len(rows),
        "pta_breached_contract_ids": pta_breached_contract_ids,
        "min_fee_floor_hit_contract_ids": min_fee_floor_hit_contract_ids,
        "ceiling_price_exceeded_contract_ids": ceiling_price_exceeded_contract_ids,
        "total_final_fees_payable": round(total_final_fees_payable, 2),
        "cpif_governance_status": cpif_governance_status,
        "is_cpif_compliant": cpif_governance_status == "INCENTIVE_ALIGNED",
    }


ProjectEVMService.evaluate_evm_cpif_share_ratio_and_point_of_total_assumption = staticmethod(
    evaluate_evm_cpif_share_ratio_and_point_of_total_assumption
)


def evaluate_evm_performance_bond_and_letter_of_credit_coverage(
    instruments: list[dict[str, Any]],
    *,
    min_coverage_pct_of_contract: float = 10.0,
    min_days_beyond_completion_buffer: int = 30,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Letter of Credit (LC) / Performance Bond Expiry, Coverage Ratio & Drawdown Trigger Evaluator."""
    valid_instruments: list[dict[str, Any]] = []
    if isinstance(instruments, (list, tuple)):
        for item in instruments:
            if not isinstance(item, dict):
                continue
            iid = str(item.get("instrument_id") or "").strip()
            if not iid:
                continue
            valid_instruments.append({**item, "_iid": iid})

    if not valid_instruments:
        return {
            "total_instruments_evaluated": 0,
            "total_bonded_coverage_amount": 0.0,
            "underinsured_instrument_ids": [],
            "premature_expiry_instrument_ids": [],
            "non_compliant_issuer_or_revocable_ids": [],
            "bond_governance_status": "BOND_COVERAGE_SOUND",
            "is_bond_coverage_compliant": True,
            "recommendations": [],
        }

    underinsured_instrument_ids: list[str] = []
    premature_expiry_instrument_ids: list[str] = []
    non_compliant_issuer_or_revocable_ids: list[str] = []
    bonded_sum = 0.0

    for inst in valid_instruments:
        iid = inst["_iid"]
        contract_val = max(
            0.0, float(inst.get("contract_total_value", 0.0) or 0.0)
        )
        face_amt = max(
            0.0, float(inst.get("bond_or_lc_face_amount", 0.0) or 0.0)
        )
        days_valid = int(
            inst.get("days_valid_after_scheduled_completion", 60)
            if inst.get("days_valid_after_scheduled_completion") is not None
            else 60
        )
        inv_grade = bool(
            inst.get("issuer_credit_rating_investment_grade", True)
        )
        irrevocable = bool(inst.get("is_irrevocable_on_demand", True))

        bonded_sum += face_amt

        coverage_pct = (
            round((face_amt / contract_val) * 100.0, 2)
            if contract_val > 0.0
            else 100.0
        )

        if coverage_pct < min_coverage_pct_of_contract:
            underinsured_instrument_ids.append(iid)

        if days_valid < min_days_beyond_completion_buffer:
            premature_expiry_instrument_ids.append(iid)

        if not inv_grade or not irrevocable:
            non_compliant_issuer_or_revocable_ids.append(iid)

    total_bonded_coverage_amount = round(bonded_sum, 2)

    recommendations: list[str] = []
    if non_compliant_issuer_or_revocable_ids:
        recommendations.append(
            f"Replace revocable or sub-investment-grade surety instruments with irrevocable on-demand LCs for instrument(s): {', '.join(non_compliant_issuer_or_revocable_ids)}."
        )
    if underinsured_instrument_ids:
        recommendations.append(
            f"Increase performance bond/LC face amount to >= {min_coverage_pct_of_contract}% of contract value for instrument(s): {', '.join(underinsured_instrument_ids)}."
        )
    if premature_expiry_instrument_ids:
        recommendations.append(
            f"Extend LC/bond validity to >= {min_days_beyond_completion_buffer} days beyond scheduled completion for instrument(s): {', '.join(premature_expiry_instrument_ids)}."
        )

    if non_compliant_issuer_or_revocable_ids or underinsured_instrument_ids:
        bond_governance_status = "COUNTERPARTY_DEFAULT_EXPOSURE"
    elif premature_expiry_instrument_ids:
        bond_governance_status = "EXPIRY_BUFFER_WARNING"
    else:
        bond_governance_status = "BOND_COVERAGE_SOUND"

    return {
        "total_instruments_evaluated": len(valid_instruments),
        "total_bonded_coverage_amount": total_bonded_coverage_amount,
        "underinsured_instrument_ids": underinsured_instrument_ids,
        "premature_expiry_instrument_ids": premature_expiry_instrument_ids,
        "non_compliant_issuer_or_revocable_ids": non_compliant_issuer_or_revocable_ids,
        "bond_governance_status": bond_governance_status,
        "is_bond_coverage_compliant": bond_governance_status
        == "BOND_COVERAGE_SOUND",
        "recommendations": recommendations,
    }


ProjectEVMService.evaluate_evm_performance_bond_and_letter_of_credit_coverage = staticmethod(
    evaluate_evm_performance_bond_and_letter_of_credit_coverage
)


def evaluate_evm_fx_hedging_collar_and_currency_exposure(
    currency_tranches: Any,
    *,
    min_hedge_coverage_pct: float = 80.0,
    max_unhedged_fx_var_pct_of_bac: float = 2.0,
) -> Dict[str, object]:
    """Evaluación PMBOK 7.4 y 11.2: cobertura FX y exposición de traducción.

    Agrega por tranche la exposición y cobertura en moneda base, calcula
    el VaR de las fracciones sin cubrir frente al BAC total del proyecto
    y detecta monedas sub-cubiertas o sin collar/forward activo.
    """
    entries = currency_tranches if isinstance(currency_tranches, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    total_fx_exposure_base = 0.0
    total_hedged_base = 0.0
    total_unhedged_fx_var_amount = 0.0
    total_bac = 0.0
    underhedged_currency_codes: List[str] = []

    for item in rows:
        currency_code = item.get("currency_code")
        exposure = item.get("exposure_in_base_currency", 0.0)
        hedged = item.get("hedged_amount_in_base_currency", 0.0)
        var_pct = item.get("spot_volatility_var_pct", 5.0)
        has_collar = item.get("has_active_fx_collar_or_forward", True)
        bac = item.get("total_project_bac", 100000.0)

        exposure_val = exposure if isinstance(exposure, (int, float)) and exposure >= 0 else 0.0
        hedged_raw = hedged if isinstance(hedged, (int, float)) and hedged >= 0 else 0.0
        var_pct_val = var_pct if isinstance(var_pct, (int, float)) and var_pct >= 0 else 0.0
        bac_val = bac if isinstance(bac, (int, float)) and bac >= 0 else 0.0

        # El monto cubierto no puede exceder la exposición de la tranche.
        hedged_val = min(hedged_raw, exposure_val)

        total_fx_exposure_base += exposure_val
        total_hedged_base += hedged_val
        total_unhedged_fx_var_amount += (
            max(0.0, exposure_val - hedged_val) * (var_pct_val / 100.0)
        )
        total_bac += bac_val

        if exposure_val > 0:
            hedge_coverage_pct = round((hedged_val / exposure_val) * 100.0, 2)
        else:
            hedge_coverage_pct = 100.0

        if exposure_val > 0 and (hedge_coverage_pct < min_hedge_coverage_pct or has_collar is not True):
            underhedged_currency_codes.append(currency_code)

    aggregate_hedge_coverage_pct = (
        round((total_hedged_base / total_fx_exposure_base) * 100.0, 2)
        if total_fx_exposure_base > 0
        else 100.0
    )

    unhedged_fx_var_pct_of_bac = (
        round((total_unhedged_fx_var_amount / total_bac) * 100.0, 2)
        if total_bac > 0
        else 0.0
    )

    if unhedged_fx_var_pct_of_bac > max_unhedged_fx_var_pct_of_bac:
        fx_exposure_status = "FX_TRANSLATION_VAR_BREACH"
    elif underhedged_currency_codes:
        fx_exposure_status = "FX_HEDGE_COVERAGE_WARNING"
    else:
        fx_exposure_status = "FX_HEDGED_OPTIMAL"

    return {
        "total_fx_exposure_base": round(total_fx_exposure_base, 2),
        "total_hedged_base": round(total_hedged_base, 2),
        "aggregate_hedge_coverage_pct": aggregate_hedge_coverage_pct,
        "total_unhedged_fx_var_amount": round(total_unhedged_fx_var_amount, 2),
        "unhedged_fx_var_pct_of_bac": unhedged_fx_var_pct_of_bac,
        "underhedged_currency_codes": underhedged_currency_codes,
        "fx_exposure_status": fx_exposure_status,
        "is_fx_compliant": fx_exposure_status == "FX_HEDGED_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_fx_hedging_collar_and_currency_exposure = staticmethod(
    evaluate_evm_fx_hedging_collar_and_currency_exposure
)


def evaluate_evm_time_and_materials_nte_ceiling_and_rate_card(
    tm_contracts: Sequence[Mapping[str, Any]] | None,
    *,
    nte_early_warning_threshold_pct: float = 85.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Time & Materials (T&M) Ceiling Cap (NTE), Labor Rate Card Audit & Burn-Rate Exhaustion Evaluator."""
    valid_contracts = [
        cnt
        for cnt in (tm_contracts or [])
        if isinstance(cnt, Mapping) and str(cnt.get("contract_id") or "").strip()
    ]

    nte_breach_or_rate_violation_contract_ids: list[str] = []
    burn_ahead_of_progress_contract_ids: list[str] = []

    for cnt in valid_contracts:
        cid = str(cnt.get("contract_id")).strip()
        ceiling = float(
            cnt.get("not_to_exceed_ceiling", 100000.0)
            if cnt.get("not_to_exceed_ceiling") is not None
            else 100000.0
        )
        billed = float(
            cnt.get("cumulative_billed_amount", 0.0)
            if cnt.get("cumulative_billed_amount") is not None
            else 0.0
        )
        completion_pct = float(
            cnt.get("work_completion_pct", 0.0)
            if cnt.get("work_completion_pct") is not None
            else 0.0
        )
        overrides_count = int(
            cnt.get("unapproved_rate_card_overrides_count", 0)
            if cnt.get("unapproved_rate_card_overrides_count") is not None
            else 0
        )
        timesheet_verified = bool(
            cnt.get("timesheet_audit_verified", True)
            if cnt.get("timesheet_audit_verified") is not None
            else True
        )

        if (
            billed > ceiling
            or overrides_count > 0
            or not timesheet_verified
        ):
            nte_breach_or_rate_violation_contract_ids.append(cid)

        if ceiling > 0:
            burn_pct = (billed / ceiling) * 100.0
            if (
                burn_pct >= nte_early_warning_threshold_pct
                and completion_pct < (burn_pct - 15.0)
            ):
                burn_ahead_of_progress_contract_ids.append(cid)

    if nte_breach_or_rate_violation_contract_ids:
        tm_governance_status = "TM_NTE_CEILING_OR_RATE_CARD_BREACH"
    elif burn_ahead_of_progress_contract_ids:
        tm_governance_status = "TM_BURN_EXHAUSTION_WARNING"
    else:
        tm_governance_status = "TM_CONTRACT_CONTROL_OPTIMAL"

    return {
        "evaluated_contracts_count": len(valid_contracts),
        "nte_breach_or_rate_violation_contract_ids": nte_breach_or_rate_violation_contract_ids,
        "burn_ahead_of_progress_contract_ids": burn_ahead_of_progress_contract_ids,
        "tm_governance_status": tm_governance_status,
        "is_tm_contract_compliant": tm_governance_status
        == "TM_CONTRACT_CONTROL_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_time_and_materials_nte_ceiling_and_rate_card = staticmethod(
    evaluate_evm_time_and_materials_nte_ceiling_and_rate_card
)


def evaluate_evm_working_capital_cash_conversion_and_mobilization_advance(
    billing_cycles: Sequence[Mapping[str, Any]] | None,
    *,
    max_dso_days: float = 45.0,
    min_cash_runway_months: float = 3.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.3 & §7.4 — EVM Working Capital Cash Conversion Cycle (DSO/DPO), Mobilization Advance Amortization & Liquidity Runway Evaluator."""
    valid_cycles = [
        cyc
        for cyc in (billing_cycles or [])
        if isinstance(cyc, Mapping) and str(cyc.get("cycle_id") or "").strip()
    ]

    liquidity_crunch_or_unamortized_advance_cycle_ids: list[str] = []
    high_dso_or_positive_cash_gap_cycle_ids: list[str] = []

    for cyc in valid_cycles:
        cid = str(cyc.get("cycle_id")).strip()
        raw_dso = cyc.get("days_sales_outstanding_dso")
        dso = float(raw_dso if raw_dso is not None else 30.0)
        raw_dpo = cyc.get("days_payable_outstanding_dpo")
        dpo = float(raw_dpo if raw_dpo is not None else 35.0)
        raw_adv = cyc.get("mobilization_advance_unamortized_balance")
        unamortized_adv = float(raw_adv if raw_adv is not None else 0.0)
        raw_rem = cyc.get("remaining_contract_billings")
        rem_billings = float(raw_rem if raw_rem is not None else 100000.0)
        raw_runway = cyc.get("available_project_cash_runway_months")
        runway_months = float(raw_runway if raw_runway is not None else 4.0)

        if (
            runway_months < min_cash_runway_months
            or unamortized_adv > rem_billings
        ):
            liquidity_crunch_or_unamortized_advance_cycle_ids.append(cid)

        if dso > max_dso_days or (dso - dpo) > 15.0:
            high_dso_or_positive_cash_gap_cycle_ids.append(cid)

    if liquidity_crunch_or_unamortized_advance_cycle_ids:
        working_capital_status = "WORKING_CAPITAL_LIQUIDITY_OR_ADVANCE_BREACH"
    elif high_dso_or_positive_cash_gap_cycle_ids:
        working_capital_status = "WORKING_CAPITAL_DSO_CASH_GAP_WARNING"
    else:
        working_capital_status = "WORKING_CAPITAL_FLOW_OPTIMAL"

    return {
        "evaluated_cycles_count": len(valid_cycles),
        "liquidity_crunch_or_unamortized_advance_cycle_ids": liquidity_crunch_or_unamortized_advance_cycle_ids,
        "high_dso_or_positive_cash_gap_cycle_ids": high_dso_or_positive_cash_gap_cycle_ids,
        "working_capital_status": working_capital_status,
        "is_working_capital_compliant": working_capital_status
        == "WORKING_CAPITAL_FLOW_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_working_capital_cash_conversion_and_mobilization_advance = staticmethod(
    evaluate_evm_working_capital_cash_conversion_and_mobilization_advance
)


def evaluate_evm_liquidated_damages_cap_and_eot_relief(
    milestones: Sequence[Mapping[str, Any]] | None,
    *,
    max_ld_cap_pct_of_contract: float = 10.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Liquidated Damages (LD) Delay Penalty Cap, Grace Period Exhaustion & Excused Extension (EOT) Evaluator."""
    valid_milestones = [
        ms
        for ms in (milestones or [])
        if isinstance(ms, Mapping) and str(ms.get("milestone_id") or "").strip()
    ]

    net_chargeable_delay_days_by_milestone: dict[str, float] = {}
    uncapped_ld_exposure_total = 0.0
    ld_cap_breached_milestone_ids: list[str] = []
    active_ld_accrual_milestone_ids: list[str] = []

    for ms in valid_milestones:
        mid = str(ms.get("milestone_id")).strip()
        total_delay = float(
            ms.get("total_delay_days", 0)
            if ms.get("total_delay_days") is not None
            else 0
        )
        grace_days = float(
            ms.get("grace_period_days", 5)
            if ms.get("grace_period_days") is not None
            else 5
        )
        eot_relief = float(
            ms.get("approved_eot_relief_days", 0)
            if ms.get("approved_eot_relief_days") is not None
            else 0
        )
        daily_rate = float(
            ms.get("daily_ld_rate", 1000.0)
            if ms.get("daily_ld_rate") is not None
            else 1000.0
        )
        contract_val = float(
            ms.get("contract_value", 100000.0)
            if ms.get("contract_value") is not None
            else 100000.0
        )

        chargeable_days = max(0.0, total_delay - grace_days - eot_relief)
        net_chargeable_delay_days_by_milestone[mid] = chargeable_days
        milestone_ld = chargeable_days * daily_rate
        uncapped_ld_exposure_total += milestone_ld

        if (
            contract_val > 0
            and (milestone_ld / contract_val) * 100.0
            >= max_ld_cap_pct_of_contract
        ):
            ld_cap_breached_milestone_ids.append(mid)

        if chargeable_days > 0:
            active_ld_accrual_milestone_ids.append(mid)

    if ld_cap_breached_milestone_ids:
        liquidated_damages_status = "LD_PENALTY_CAP_EXHAUSTED_BREACH"
    elif active_ld_accrual_milestone_ids:
        liquidated_damages_status = "LD_DELAY_ACCRUAL_ACTIVE_WARNING"
    else:
        liquidated_damages_status = "LD_ZERO_EXPOSURE_OPTIMAL"

    return {
        "evaluated_milestones_count": len(valid_milestones),
        "net_chargeable_delay_days_by_milestone": net_chargeable_delay_days_by_milestone,
        "uncapped_ld_exposure_total": round(uncapped_ld_exposure_total, 2),
        "ld_cap_breached_milestone_ids": ld_cap_breached_milestone_ids,
        "active_ld_accrual_milestone_ids": active_ld_accrual_milestone_ids,
        "liquidated_damages_status": liquidated_damages_status,
        "is_ld_exposure_compliant": liquidated_damages_status
        == "LD_ZERO_EXPOSURE_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_liquidated_damages_cap_and_eot_relief = staticmethod(
    evaluate_evm_liquidated_damages_cap_and_eot_relief
)


def evaluate_evm_epa_inflation_indexation_and_escalation_cap(
    epa_clauses: Sequence[Mapping[str, Any]] | None,
    *,
    max_annual_escalation_cap_pct: float = 6.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Economic Price Adjustment (EPA) Inflation Indexation, Commodity Pass-Through Cap & Escalation Formula Evaluator."""
    valid_clauses = [
        cls_item
        for cls_item in (epa_clauses or [])
        if isinstance(cls_item, Mapping)
        and str(cls_item.get("clause_id") or "").strip()
    ]

    overclaimed_or_unverified_index_clause_ids: list[str] = []
    within_deadband_or_near_cap_clause_ids: list[str] = []

    for cls_item in valid_clauses:
        cid = str(cls_item.get("clause_id")).strip()
        base_index_value = float(
            cls_item.get("base_index_value", 100.0)
            if cls_item.get("base_index_value") is not None
            else 100.0
        )
        current_index_value = float(
            cls_item.get("current_index_value", 103.0)
            if cls_item.get("current_index_value") is not None
            else 103.0
        )
        claimed_escalation_pct = float(
            cls_item.get("claimed_escalation_pct", 3.0)
            if cls_item.get("claimed_escalation_pct") is not None
            else 3.0
        )
        contractual_cap_pct = float(
            cls_item.get("contractual_cap_pct", max_annual_escalation_cap_pct)
            if cls_item.get("contractual_cap_pct") is not None
            else max_annual_escalation_cap_pct
        )
        deadband_threshold_pct = float(
            cls_item.get("deadband_threshold_pct", 2.0)
            if cls_item.get("deadband_threshold_pct") is not None
            else 2.0
        )
        official_bls_or_cpi_source_verified = bool(
            cls_item.get("official_bls_or_cpi_source_verified", True)
            if cls_item.get("official_bls_or_cpi_source_verified") is not None
            else True
        )

        if (
            not official_bls_or_cpi_source_verified
            or claimed_escalation_pct > contractual_cap_pct
            or (
                base_index_value > 0
                and claimed_escalation_pct
                > round(
                    ((current_index_value - base_index_value) / base_index_value)
                    * 100.0,
                    2,
                )
                + 0.05
            )
        ):
            overclaimed_or_unverified_index_clause_ids.append(cid)

        if (
            base_index_value > 0
            and abs(
                ((current_index_value - base_index_value) / base_index_value)
                * 100.0
            )
            <= deadband_threshold_pct
            and claimed_escalation_pct > 0
        ) or claimed_escalation_pct >= (contractual_cap_pct * 0.9):
            within_deadband_or_near_cap_clause_ids.append(cid)

    if overclaimed_or_unverified_index_clause_ids:
        epa_escalation_status = "EPA_INDEX_OVERCLAIM_OR_UNVERIFIED_BREACH"
    elif within_deadband_or_near_cap_clause_ids:
        epa_escalation_status = "EPA_DEADBAND_OR_CAP_PROXIMITY_WARNING"
    else:
        epa_escalation_status = "EPA_INDEXATION_COMPLIANT_OPTIMAL"

    return {
        "evaluated_clauses_count": len(valid_clauses),
        "overclaimed_or_unverified_index_clause_ids": overclaimed_or_unverified_index_clause_ids,
        "within_deadband_or_near_cap_clause_ids": within_deadband_or_near_cap_clause_ids,
        "epa_escalation_status": epa_escalation_status,
        "is_epa_escalation_compliant": epa_escalation_status
        == "EPA_INDEXATION_COMPLIANT_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_epa_inflation_indexation_and_escalation_cap = staticmethod(
    evaluate_evm_epa_inflation_indexation_and_escalation_cap
)


def evaluate_evm_subcontractor_lien_waiver_and_flow_down(
    subcontract_vouchers: Sequence[Mapping[str, Any]] | None,
    *,
    max_payment_disbursement_lag_days: int | float = 10,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Subcontractor Back-to-Back Flow-Down Clause, Lien Waiver Release & Pay-When-Paid Compliance Evaluator."""
    valid_vouchers = [
        vch
        for vch in (subcontract_vouchers or [])
        if isinstance(vch, Mapping) and str(vch.get("voucher_id") or "").strip()
    ]

    missing_lien_waiver_or_flow_down_voucher_ids: list[str] = []
    overdue_disbursement_voucher_ids: list[str] = []

    for vch in valid_vouchers:
        vid = str(vch.get("voucher_id")).strip()
        unconditional_lien_waiver_signed = bool(
            vch.get("unconditional_lien_waiver_signed", True)
            if vch.get("unconditional_lien_waiver_signed") is not None
            else True
        )
        mandatory_flow_down_clauses_accepted = bool(
            vch.get("mandatory_flow_down_clauses_accepted", True)
            if vch.get("mandatory_flow_down_clauses_accepted") is not None
            else True
        )
        days_since_prime_payment_received = float(
            vch.get("days_since_prime_payment_received", 3)
            if vch.get("days_since_prime_payment_received") is not None
            else 3
        )
        subcontractor_paid = bool(
            vch.get("subcontractor_paid", True)
            if vch.get("subcontractor_paid") is not None
            else True
        )
        certified_payroll_attached = bool(
            vch.get("certified_payroll_attached", True)
            if vch.get("certified_payroll_attached") is not None
            else True
        )

        if (
            not unconditional_lien_waiver_signed
            or not mandatory_flow_down_clauses_accepted
            or not certified_payroll_attached
        ):
            missing_lien_waiver_or_flow_down_voucher_ids.append(vid)

        if (
            not subcontractor_paid
            and days_since_prime_payment_received
            > max_payment_disbursement_lag_days
        ):
            overdue_disbursement_voucher_ids.append(vid)

    if missing_lien_waiver_or_flow_down_voucher_ids:
        subcontractor_payment_status = "SUBCONTRACT_LIEN_OR_FLOW_DOWN_BREACH"
    elif overdue_disbursement_voucher_ids:
        subcontractor_payment_status = (
            "SUBCONTRACT_PAY_DISBURSEMENT_LAG_WARNING"
        )
    else:
        subcontractor_payment_status = (
            "SUBCONTRACT_FLOW_DOWN_COMPLIANT_OPTIMAL"
        )

    return {
        "evaluated_vouchers_count": len(valid_vouchers),
        "missing_lien_waiver_or_flow_down_voucher_ids": missing_lien_waiver_or_flow_down_voucher_ids,
        "overdue_disbursement_voucher_ids": overdue_disbursement_voucher_ids,
        "subcontractor_payment_status": subcontractor_payment_status,
        "is_subcontract_payment_compliant": subcontractor_payment_status
        == "SUBCONTRACT_FLOW_DOWN_COMPLIANT_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_subcontractor_lien_waiver_and_flow_down = staticmethod(
    evaluate_evm_subcontractor_lien_waiver_and_flow_down
)


def evaluate_evm_capex_opex_software_capitalization_gate(
    work_packages: Sequence[Mapping[str, Any]] | None,
    *,
    max_preliminary_or_post_impl_capex_pct: float = 0.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.3 & §7.4 — EVM Capital Expenditure (CapEx) vs Operational Expenditure (OpEx) Software Capitalization (ASC 350-40 / IAS 38) Phase Gate Evaluator."""
    valid_packages = [
        pkg
        for pkg in (work_packages or [])
        if isinstance(pkg, Mapping) and str(pkg.get("package_id") or "").strip()
    ]

    improper_capex_classification_package_ids: list[str] = []
    excessive_amortization_horizon_package_ids: list[str] = []

    for pkg in valid_packages:
        pid = str(pkg.get("package_id")).strip()
        accounting_stage = str(
            pkg.get("accounting_stage", "application_development")
            if pkg.get("accounting_stage") is not None
            else "application_development"
        ).strip()
        capitalized_capex_amount = float(
            pkg.get("capitalized_capex_amount", 10000.0)
            if pkg.get("capitalized_capex_amount") is not None
            else 10000.0
        )
        management_authorization_signed = bool(
            pkg.get("management_authorization_signed", True)
            if pkg.get("management_authorization_signed") is not None
            else True
        )
        amortization_useful_life_months = int(
            pkg.get("amortization_useful_life_months", 36)
            if pkg.get("amortization_useful_life_months") is not None
            else 36
        )

        if (
            accounting_stage
            in ("preliminary_project", "post_implementation_maintenance")
            and capitalized_capex_amount
            > max_preliminary_or_post_impl_capex_pct
        ) or (
            capitalized_capex_amount > 0
            and not management_authorization_signed
        ):
            improper_capex_classification_package_ids.append(pid)

        if capitalized_capex_amount > 0 and (
            amortization_useful_life_months <= 0
            or amortization_useful_life_months > 60
        ):
            excessive_amortization_horizon_package_ids.append(pid)

    if improper_capex_classification_package_ids:
        capex_governance_status = "CAPEX_ASC350_MISCLASSIFICATION_BREACH"
    elif excessive_amortization_horizon_package_ids:
        capex_governance_status = "CAPEX_AMORTIZATION_HORIZON_WARNING"
    else:
        capex_governance_status = "CAPEX_OPEX_ACCOUNTING_OPTIMAL"

    return {
        "evaluated_packages_count": len(valid_packages),
        "improper_capex_classification_package_ids": improper_capex_classification_package_ids,
        "excessive_amortization_horizon_package_ids": excessive_amortization_horizon_package_ids,
        "capex_governance_status": capex_governance_status,
        "is_capex_accounting_compliant": capex_governance_status
        == "CAPEX_OPEX_ACCOUNTING_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_capex_opex_software_capitalization_gate = staticmethod(
    evaluate_evm_capex_opex_software_capitalization_gate
)


def evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare(
    proposals: list[dict] | None,
    *,
    min_function_worth_index: float = 1.15,
    max_implementation_payback_months: float = 18.0,
) -> dict:
    """PMBOK §7.4 & §12.3 — Evalúa índice función-valor de Ingeniería de Valor (VE), retorno de implementación y reparto de ahorros VECP."""
    raw_items = proposals if isinstance(proposals, list) else []
    valid_proposals: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("vecp_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_proposals.append(item)

    quality_compromised_or_unaudited_vecp_ids: list[str] = []
    low_worth_or_slow_payback_vecp_ids: list[str] = []

    for p in valid_proposals:
        vid = p["vecp_id"].strip()
        raw_worth = p.get("function_worth_index", 1.35)
        function_worth_index = float(1.35 if raw_worth is None else raw_worth)

        raw_payback = p.get("implementation_payback_months", 8.0)
        implementation_payback_months = float(
            8.0 if raw_payback is None else raw_payback
        )

        raw_degrades = p.get("degrades_essential_quality_or_safety", False)
        degrades_essential_quality_or_safety = bool(
            False if raw_degrades is None else raw_degrades
        )

        raw_audit = p.get("independent_cost_audit_verified", True)
        independent_cost_audit_verified = bool(
            True if raw_audit is None else raw_audit
        )

        if (
            degrades_essential_quality_or_safety
            or not independent_cost_audit_verified
        ):
            quality_compromised_or_unaudited_vecp_ids.append(vid)

        if (
            function_worth_index < min_function_worth_index
            or implementation_payback_months
            > max_implementation_payback_months
        ):
            low_worth_or_slow_payback_vecp_ids.append(vid)

    if quality_compromised_or_unaudited_vecp_ids:
        value_engineering_status = "VECP_QUALITY_OR_AUDIT_BREACH"
    elif low_worth_or_slow_payback_vecp_ids:
        value_engineering_status = "VECP_LOW_WORTH_OR_PAYBACK_WARNING"
    else:
        value_engineering_status = "VECP_GAINSHARE_OPTIMAL"

    return {
        "evaluated_proposals_count": len(valid_proposals),
        "quality_compromised_or_unaudited_vecp_ids": quality_compromised_or_unaudited_vecp_ids,
        "low_worth_or_slow_payback_vecp_ids": low_worth_or_slow_payback_vecp_ids,
        "value_engineering_status": value_engineering_status,
        "is_value_engineering_compliant": value_engineering_status
        == "VECP_GAINSHARE_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare = staticmethod(
    evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare
)


def evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
    periods: list[dict] | None,
    *,
    max_base_fee_pct: float = 3.0,
    allow_unearned_fee_rollover: bool = False,
) -> dict:
    """PMBOK §12.1 & §7.4 — Evalúa pool de evaluación subjetiva CPAF, determinaciones unilaterales del board y rollover de honorarios no devengados."""
    raw_items = periods if isinstance(periods, list) else []
    valid_periods: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("period_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_periods.append(item)

    def _num(value, default):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _bool(value, default):
        return value if isinstance(value, bool) else default

    unauthorized_rollover_or_unpublished_plan_period_ids: list[str] = []
    excessive_base_or_overrun_rewarded_period_ids: list[str] = []

    for period in valid_periods:
        period_id = str(period.get("period_id")).strip()
        base_fee_pct = _num(period.get("base_fee_pct"), 2.0)
        plan_published = _bool(
            period.get("award_fee_plan_published_in_advance"), True
        )
        fee_rolled_over = _bool(
            period.get("unearned_fee_rolled_over"), False
        )
        cost_overrun = _bool(
            period.get("cost_overrun_occurred"), False
        )
        award_fee_granted_pct = _num(
            period.get("award_fee_granted_pct"), 80.0
        )

        if not plan_published or (
            not allow_unearned_fee_rollover and fee_rolled_over
        ):
            unauthorized_rollover_or_unpublished_plan_period_ids.append(
                period_id
            )

        if base_fee_pct > max_base_fee_pct or (
            cost_overrun and award_fee_granted_pct > 50.0
        ):
            excessive_base_or_overrun_rewarded_period_ids.append(period_id)

    if unauthorized_rollover_or_unpublished_plan_period_ids:
        cpaf_governance_status = "CPAF_UNPUBLISHED_PLAN_OR_ROLLOVER_BREACH"
    elif excessive_base_or_overrun_rewarded_period_ids:
        cpaf_governance_status = "CPAF_BASE_FEE_OR_OVERRUN_REWARD_WARNING"
    else:
        cpaf_governance_status = "CPAF_AWARD_FEE_GOVERNANCE_OPTIMAL"

    return {
        "evaluated_periods_count": len(valid_periods),
        "unauthorized_rollover_or_unpublished_plan_period_ids": unauthorized_rollover_or_unpublished_plan_period_ids,
        "excessive_base_or_overrun_rewarded_period_ids": excessive_base_or_overrun_rewarded_period_ids,
        "cpaf_governance_status": cpaf_governance_status,
        "is_cpaf_governance_compliant": cpaf_governance_status
        == "CPAF_AWARD_FEE_GOVERNANCE_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_cpaf_award_fee_pool_and_rollover_governance = staticmethod(
    evaluate_evm_cpaf_award_fee_pool_and_rollover_governance
)


def evaluate_evm_standby_demurrage_and_force_account_rates(
    claims: list[dict] | None,
    *,
    max_standby_rate_of_active_pct: float = 50.0,
    max_mob_demob_contract_share_pct: float = 10.0,
) -> dict:
    """PMBOK §7.4 & §12.3 — Evalúa reclamos de demora por equipo en espera (standby demurrage), verificación de tarifas force-account y tope de movilización/desmovilización."""
    raw_items = claims if isinstance(claims, list) else []
    valid_claims: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("claim_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_claims.append(item)

    unverified_log_or_self_inflicted_idle_claim_ids: list[str] = []
    excessive_standby_rate_or_mob_cap_claim_ids: list[str] = []

    for c in valid_claims:
        cid = c["claim_id"].strip()
        raw_log = c.get("daily_field_log_countersigned", True)
        daily_field_log_countersigned = bool(
            True if raw_log is None else raw_log
        )

        raw_excl = c.get("contractor_caused_idle_excluded", True)
        contractor_caused_idle_excluded = bool(
            True if raw_excl is None else raw_excl
        )

        raw_standby = c.get("standby_rate_of_active_pct", 35.0)
        standby_rate_of_active_pct = float(
            35.0 if raw_standby is None else raw_standby
        )

        raw_mob = c.get("mob_demob_contract_share_pct", 6.0)
        mob_demob_contract_share_pct = float(
            6.0 if raw_mob is None else raw_mob
        )

        if (
            not daily_field_log_countersigned
            or not contractor_caused_idle_excluded
        ):
            unverified_log_or_self_inflicted_idle_claim_ids.append(cid)

        if (
            standby_rate_of_active_pct > max_standby_rate_of_active_pct
            or mob_demob_contract_share_pct > max_mob_demob_contract_share_pct
        ):
            excessive_standby_rate_or_mob_cap_claim_ids.append(cid)

    if unverified_log_or_self_inflicted_idle_claim_ids:
        standby_demurrage_status = (
            "DEMURRAGE_UNVERIFIED_LOG_OR_SELF_IDLE_BREACH"
        )
    elif excessive_standby_rate_or_mob_cap_claim_ids:
        standby_demurrage_status = (
            "DEMURRAGE_STANDBY_RATE_OR_MOB_CAP_WARNING"
        )
    else:
        standby_demurrage_status = "DEMURRAGE_FORCE_ACCOUNT_OPTIMAL"

    return {
        "evaluated_claims_count": len(valid_claims),
        "unverified_log_or_self_inflicted_idle_claim_ids": unverified_log_or_self_inflicted_idle_claim_ids,
        "excessive_standby_rate_or_mob_cap_claim_ids": excessive_standby_rate_or_mob_cap_claim_ids,
        "standby_demurrage_status": standby_demurrage_status,
        "is_standby_demurrage_compliant": standby_demurrage_status
        == "DEMURRAGE_FORCE_ACCOUNT_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_standby_demurrage_and_force_account_rates = staticmethod(
    evaluate_evm_standby_demurrage_and_force_account_rates
)


def evaluate_evm_schedule_of_values_front_loading_and_stored_materials(
    line_items: list[dict[str, Any]] | None,
    *,
    max_early_phase_markup_skew_pct: float = 15.0,
    max_stored_materials_share_pct: float = 20.0,
) -> dict[str, Any]:
    """PMI PMBOK §7.4 & §12.3 — EVM Schedule of Values (SOV) Front-Loading Detection, Off-Site Stored Materials Insurance & Bill-of-Sale Evaluator."""
    raw_items = line_items if isinstance(line_items, (list, tuple)) else []
    valid_items = [
        item
        for item in raw_items
        if isinstance(item, Mapping)
        and isinstance(item.get("item_id"), str)
        and item["item_id"].strip()
    ]

    uninsured_or_untitled_stored_material_item_ids: list[str] = []
    front_loaded_or_excess_stored_item_ids: list[str] = []

    for item in valid_items:
        iid = str(item["item_id"]).strip()
        early_phase_markup_skew_pct = float(
            item.get("early_phase_markup_skew_pct", 5.0)
            if item.get("early_phase_markup_skew_pct") is not None
            else 5.0
        )
        stored_materials_share_pct = float(
            item.get("stored_materials_share_pct", 8.0)
            if item.get("stored_materials_share_pct") is not None
            else 8.0
        )
        bonded_warehouse_and_insurance_verified = bool(
            item.get("bonded_warehouse_and_insurance_verified", True)
            if item.get("bonded_warehouse_and_insurance_verified") is not None
            else True
        )
        unconditional_title_transfer_bill_of_sale = bool(
            item.get("unconditional_title_transfer_bill_of_sale", True)
            if item.get("unconditional_title_transfer_bill_of_sale") is not None
            else True
        )

        if stored_materials_share_pct > 0.0 and (
            not bonded_warehouse_and_insurance_verified
            or not unconditional_title_transfer_bill_of_sale
        ):
            uninsured_or_untitled_stored_material_item_ids.append(iid)

        if (
            early_phase_markup_skew_pct > max_early_phase_markup_skew_pct
            or stored_materials_share_pct > max_stored_materials_share_pct
        ):
            front_loaded_or_excess_stored_item_ids.append(iid)

    if uninsured_or_untitled_stored_material_item_ids:
        sov_billing_status = "SOV_STORED_MATERIAL_TITLE_OR_INSURANCE_BREACH"
    elif front_loaded_or_excess_stored_item_ids:
        sov_billing_status = "SOV_FRONT_LOADING_OR_STORED_CAP_WARNING"
    else:
        sov_billing_status = "SOV_PROGRESS_BILLING_OPTIMAL"

    return {
        "evaluated_items_count": len(valid_items),
        "uninsured_or_untitled_stored_material_item_ids": uninsured_or_untitled_stored_material_item_ids,
        "front_loaded_or_excess_stored_item_ids": front_loaded_or_excess_stored_item_ids,
        "sov_billing_status": sov_billing_status,
        "is_sov_billing_compliant": sov_billing_status
        == "SOV_PROGRESS_BILLING_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_schedule_of_values_front_loading_and_stored_materials = staticmethod(
    evaluate_evm_schedule_of_values_front_loading_and_stored_materials
)


def evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer(
    letters: list[dict] | None,
    *,
    min_expiry_buffer_days: int = 60,
    require_tier1_bank_and_irrevocable: bool = True,
) -> dict:
    """PMBOK §7.4 & §12.3 — Evalúa giro documental de cartas de crédito (LC) irrevocables, colchón evergreen de expiración y calificación crediticia del banco emisor."""
    raw_items = letters if isinstance(letters, list) else []
    valid_letters: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("lc_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_letters.append(item)

    revocable_or_subprime_bank_lc_ids: list[str] = []
    expiring_buffer_or_underfunded_lc_ids: list[str] = []

    for lc in valid_letters:
        lid = str(lc["lc_id"]).strip()
        raw_irrev = lc.get("is_irrevocable_and_unconditional", True)
        is_irrevocable_and_unconditional = bool(
            True if raw_irrev is None else raw_irrev
        )

        raw_bank = lc.get("issuing_bank_investment_grade_verified", True)
        issuing_bank_investment_grade_verified = bool(
            True if raw_bank is None else raw_bank
        )

        raw_days = lc.get("days_until_expiry", 120)
        days_until_expiry = int(120 if raw_days is None else raw_days)

        raw_cov = lc.get("undrawn_coverage_adequacy_pct", 105.0)
        undrawn_coverage_adequacy_pct = float(
            105.0 if raw_cov is None else raw_cov
        )

        if (
            require_tier1_bank_and_irrevocable
            and (
                not is_irrevocable_and_unconditional
                or not issuing_bank_investment_grade_verified
            )
        ) or days_until_expiry <= 0:
            revocable_or_subprime_bank_lc_ids.append(lid)

        if (
            0 < days_until_expiry < min_expiry_buffer_days
            or undrawn_coverage_adequacy_pct < 100.0
        ):
            expiring_buffer_or_underfunded_lc_ids.append(lid)

    if revocable_or_subprime_bank_lc_ids:
        letter_of_credit_status = "LC_REVOCABLE_OR_BANK_SOLVENCY_BREACH"
    elif expiring_buffer_or_underfunded_lc_ids:
        letter_of_credit_status = "LC_EXPIRY_BUFFER_OR_COVERAGE_WARNING"
    else:
        letter_of_credit_status = "LC_DOCUMENTARY_SECURITY_OPTIMAL"

    return {
        "evaluated_letters_count": len(valid_letters),
        "revocable_or_subprime_bank_lc_ids": revocable_or_subprime_bank_lc_ids,
        "expiring_buffer_or_underfunded_lc_ids": expiring_buffer_or_underfunded_lc_ids,
        "letter_of_credit_status": letter_of_credit_status,
        "is_letter_of_credit_compliant": letter_of_credit_status
        == "LC_DOCUMENTARY_SECURITY_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer = staticmethod(
    evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer
)


def evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus(
    milestone_contracts: list[dict[str, Any]] | None,
    *,
    max_ld_cap_pct_of_contract: float = 10.0,
    require_concurrent_delay_apportionment: bool = True,
    max_early_bonus_cap_pct: float = 5.0,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.3 — Evalúa topes de daños liquidados (LD), extensiones por retrasos excusables, prorrateo de retrasos concurrentes y bonos por terminación anticipada."""
    raw_items = (
        milestone_contracts if isinstance(milestone_contracts, list) else []
    )
    max_ld_cap = max(0.0, float(max_ld_cap_pct_of_contract))
    max_bonus_cap = max(0.0, float(max_early_bonus_cap_pct))

    records: list[dict[str, Any]] = []
    ld_cap_breach_milestone_ids: list[str] = []
    unapportioned_delay_milestone_ids: list[str] = []
    early_bonus_breach_milestone_ids: list[str] = []
    excusable_ld_milestone_ids: list[str] = []
    violations: list[str] = []

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("milestone_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        milestone_id = raw_id.strip()

        raw_cv = item.get("contract_value", 100000.0)
        try:
            contract_value = float(100000.0 if raw_cv is None else raw_cv)
        except (TypeError, ValueError):
            continue
        if contract_value <= 0.0:
            continue

        def _non_neg_int(key: str, default: int = 0) -> int:
            val = item.get(key, default)
            if val is None or isinstance(val, bool):
                return default
            try:
                return max(0, int(val))
            except (TypeError, ValueError):
                return default

        def _non_neg_float(key: str, default: float = 0.0) -> float:
            val = item.get(key, default)
            if val is None or isinstance(val, bool):
                return default
            try:
                return max(0.0, float(val))
            except (TypeError, ValueError):
                return default

        baseline_duration_days = _non_neg_int("baseline_duration_days", 0)
        actual_duration_days = _non_neg_int("actual_duration_days", 0)
        excusable_delay_days = _non_neg_int("excusable_delay_days", 0)
        concurrent_owner_delay_days = _non_neg_int(
            "concurrent_owner_delay_days", 0
        )

        raw_app = item.get("concurrent_delay_apportioned", True)
        concurrent_delay_apportioned = bool(
            True if raw_app is None else raw_app
        )

        daily_ld_rate = _non_neg_float("daily_ld_rate", 0.0)
        daily_early_bonus_rate = _non_neg_float("daily_early_bonus_rate", 0.0)
        accrued_ld_amount = _non_neg_float("accrued_ld_amount", 0.0)
        accrued_bonus_amount = _non_neg_float("accrued_bonus_amount", 0.0)

        adjusted_completion_days = (
            baseline_duration_days + excusable_delay_days
        )
        net_unexcused_delay_days = max(
            0, actual_duration_days - adjusted_completion_days
        )
        early_days = max(0, adjusted_completion_days - actual_duration_days)

        ld_pct_of_contract = (accrued_ld_amount / contract_value) * 100.0
        bonus_pct_of_contract = (accrued_bonus_amount / contract_value) * 100.0

        ld_cap_exceeded = ld_pct_of_contract > max_ld_cap
        concurrent_delay_unapportioned = (
            bool(require_concurrent_delay_apportionment)
            and concurrent_owner_delay_days > 0
            and not concurrent_delay_apportioned
        )
        early_bonus_cap_exceeded = bonus_pct_of_contract > max_bonus_cap
        ld_assessed_during_excusable_delay = (
            net_unexcused_delay_days == 0 and accrued_ld_amount > 0.0
        )

        if ld_cap_exceeded:
            ld_cap_breach_milestone_ids.append(milestone_id)
            violations.append(
                f"{milestone_id}: ld_cap_exceeded ({ld_pct_of_contract:.2f}% > {max_ld_cap:.2f}%)"
            )
        if concurrent_delay_unapportioned:
            unapportioned_delay_milestone_ids.append(milestone_id)
            violations.append(
                f"{milestone_id}: concurrent_delay_unapportioned ({concurrent_owner_delay_days} owner delay days)"
            )
        if early_bonus_cap_exceeded:
            early_bonus_breach_milestone_ids.append(milestone_id)
            violations.append(
                f"{milestone_id}: early_bonus_cap_exceeded ({bonus_pct_of_contract:.2f}% > {max_bonus_cap:.2f}%)"
            )
        if ld_assessed_during_excusable_delay:
            excusable_ld_milestone_ids.append(milestone_id)
            violations.append(
                f"{milestone_id}: ld_assessed_during_excusable_delay (accrued_ld={accrued_ld_amount:.2f} with 0 net unexcused delay days)"
            )

        records.append(
            {
                "milestone_id": milestone_id,
                "contract_value": round(contract_value, 2),
                "baseline_duration_days": baseline_duration_days,
                "actual_duration_days": actual_duration_days,
                "excusable_delay_days": excusable_delay_days,
                "concurrent_owner_delay_days": concurrent_owner_delay_days,
                "concurrent_delay_apportioned": concurrent_delay_apportioned,
                "daily_ld_rate": round(daily_ld_rate, 2),
                "daily_early_bonus_rate": round(daily_early_bonus_rate, 2),
                "accrued_ld_amount": round(accrued_ld_amount, 2),
                "accrued_bonus_amount": round(accrued_bonus_amount, 2),
                "adjusted_completion_days": adjusted_completion_days,
                "net_unexcused_delay_days": net_unexcused_delay_days,
                "early_days": early_days,
                "ld_pct_of_contract": round(ld_pct_of_contract, 2),
                "bonus_pct_of_contract": round(bonus_pct_of_contract, 2),
                "ld_cap_exceeded": ld_cap_exceeded,
                "concurrent_delay_unapportioned": concurrent_delay_unapportioned,
                "early_bonus_cap_exceeded": early_bonus_cap_exceeded,
                "ld_assessed_during_excusable_delay": ld_assessed_during_excusable_delay,
            }
        )

    if (
        ld_cap_breach_milestone_ids
        or unapportioned_delay_milestone_ids
        or excusable_ld_milestone_ids
    ):
        status = "critical"
    elif early_bonus_breach_milestone_ids:
        status = "warning"
    else:
        status = "compliant"

    return {
        "status": status,
        "is_compliant": status == "compliant",
        "milestones_evaluated": len(records),
        "ld_cap_breach_milestone_ids": ld_cap_breach_milestone_ids,
        "unapportioned_delay_milestone_ids": unapportioned_delay_milestone_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


ProjectEVMService.evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus = staticmethod(
    evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus
)


def evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement(
    subcontract_ledgers: list[dict[str, Any]],
    *,
    min_cure_notice_hours: float = 48.0,
    max_backcharge_pct_of_subcontract: float = 15.0,
    require_joint_check_on_supplier_arrears: bool = True,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.3 — Evalúa ventana de aviso de subsanación (cure notice) de contracargos a subcontratistas, tope porcentual de compensación y acuerdos de cheque conjunto / liberación de gravamen (lien waiver)."""
    raw_items = subcontract_ledgers if isinstance(subcontract_ledgers, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    improper_backcharge_subcontract_ids: list[str] = []
    lien_risk_subcontract_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        subcontract_id = (
            str(
                item.get("subcontract_id") or item.get("id") or f"sub-{idx + 1}"
            ).strip()
            or f"sub-{idx + 1}"
        )
        subcontract_value = max(0.0, float(item.get("subcontract_value") or 0.0))
        backcharge_amount = max(0.0, float(item.get("backcharge_amount") or 0.0))
        cure_notice_hours_given = max(
            0.0, float(item.get("cure_notice_hours_given") or 0.0)
        )

        raw_subst = item.get("photo_and_cost_substantiation_attached", True)
        photo_and_cost_substantiation_attached = bool(
            True if raw_subst is None else raw_subst
        )

        lower_tier_supplier_arrears_amount = max(
            0.0, float(item.get("lower_tier_supplier_arrears_amount") or 0.0)
        )

        raw_joint = item.get("joint_check_agreement_active", True)
        joint_check_agreement_active = bool(
            True if raw_joint is None else raw_joint
        )

        raw_waiver = item.get("unconditional_lien_waiver_on_file", True)
        unconditional_lien_waiver_on_file = bool(
            True if raw_waiver is None else raw_waiver
        )

        if subcontract_value > 0:
            backcharge_pct = round(
                (backcharge_amount / subcontract_value) * 100.0, 2
            )
        elif backcharge_amount > 0:
            backcharge_pct = 100.0
        else:
            backcharge_pct = 0.0

        cure_notice_or_substantiation_breach = bool(
            backcharge_amount > 0
            and (
                cure_notice_hours_given < min_cure_notice_hours
                or not photo_and_cost_substantiation_attached
            )
        )
        backcharge_cap_exceeded = (
            backcharge_pct > max_backcharge_pct_of_subcontract
        )
        unprotected_supplier_arrears = bool(
            require_joint_check_on_supplier_arrears
            and lower_tier_supplier_arrears_amount > 0
            and not joint_check_agreement_active
        )
        missing_lien_waiver = not unconditional_lien_waiver_on_file

        if cure_notice_or_substantiation_breach or backcharge_cap_exceeded:
            improper_backcharge_subcontract_ids.append(subcontract_id)
            if cure_notice_or_substantiation_breach:
                has_critical = True
                violations.append(
                    f"Subcontract '{subcontract_id}' has backcharge without required cure notice or substantiation."
                )
            if backcharge_cap_exceeded:
                has_warning = True
                violations.append(
                    f"Subcontract '{subcontract_id}' backcharge {backcharge_pct}% exceeds cap {max_backcharge_pct_of_subcontract}%."
                )

        if unprotected_supplier_arrears or missing_lien_waiver:
            lien_risk_subcontract_ids.append(subcontract_id)
            has_critical = True
            if unprotected_supplier_arrears:
                violations.append(
                    f"Subcontract '{subcontract_id}' has lower-tier supplier arrears without active joint-check agreement."
                )
            if missing_lien_waiver:
                violations.append(
                    f"Subcontract '{subcontract_id}' is missing unconditional lien waiver on file."
                )

        records.append(
            {
                "subcontract_id": subcontract_id,
                "subcontract_value": subcontract_value,
                "backcharge_amount": backcharge_amount,
                "backcharge_pct": backcharge_pct,
                "cure_notice_hours_given": cure_notice_hours_given,
                "photo_and_cost_substantiation_attached": photo_and_cost_substantiation_attached,
                "lower_tier_supplier_arrears_amount": lower_tier_supplier_arrears_amount,
                "joint_check_agreement_active": joint_check_agreement_active,
                "unconditional_lien_waiver_on_file": unconditional_lien_waiver_on_file,
                "cure_notice_or_substantiation_breach": cure_notice_or_substantiation_breach,
                "backcharge_cap_exceeded": backcharge_cap_exceeded,
                "unprotected_supplier_arrears": unprotected_supplier_arrears,
                "missing_lien_waiver": missing_lien_waiver,
            }
        )

    if has_critical:
        status = "critical"
        is_compliant = False
    elif has_warning:
        status = "warning"
        is_compliant = False
    else:
        status = "compliant"
        is_compliant = True

    return {
        "status": status,
        "is_compliant": is_compliant,
        "subcontracts_evaluated": len(records),
        "improper_backcharge_subcontract_ids": improper_backcharge_subcontract_ids,
        "lien_risk_subcontract_ids": lien_risk_subcontract_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


ProjectEVMService.evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement = staticmethod(
    evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement
)



def evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
    equipment_logs: list[dict] | None,
    *,
    max_idle_standby_rate_factor: float = 0.50,
    max_unsubstantiated_fuel_surcharge_pct: float = 5.0,
) -> dict:
    """PMBOK §7.4 & §12.3 — Evalúa tarifas O&O del parque de construcción: idle/standby, consumables en idle y substantiation de fuel surcharge."""
    raw_items = equipment_logs if isinstance(equipment_logs, list) else []
    valid_equipment: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_equipment_id = item.get("equipment_id")
        if not isinstance(raw_equipment_id, str) or not raw_equipment_id.strip():
            continue
        valid_equipment.append(item)

    def _bool(value, default):
        return value if isinstance(value, bool) else default

    def _float(value, default):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    overbilled_idle_or_consumables_equipment_ids: list[str] = []
    unsubstantiated_fuel_surcharge_equipment_ids: list[str] = []

    for equipment in valid_equipment:
        equipment_id = str(equipment.get("equipment_id")).strip()
        ownership_hourly_rate = _float(
            equipment.get("ownership_hourly_rate"), 100.0
        )
        consumables_on_idle = _bool(
            equipment.get("operating_consumables_charged_on_idle"), False
        )
        billed_idle_hourly_rate = _float(
            equipment.get("billed_idle_hourly_rate"), 45.0
        )
        fuel_surcharge_pct = _float(equipment.get("fuel_surcharge_pct"), 3.0)
        fuel_invoice_attached = _bool(
            equipment.get("fuel_index_invoice_attached"), True
        )

        if (
            bool(consumables_on_idle) is True
            or float(billed_idle_hourly_rate)
            > float(ownership_hourly_rate) * float(max_idle_standby_rate_factor)
        ):
            overbilled_idle_or_consumables_equipment_ids.append(equipment_id)

        if (
            float(fuel_surcharge_pct)
            > float(max_unsubstantiated_fuel_surcharge_pct)
            and not bool(fuel_invoice_attached)
        ):
            unsubstantiated_fuel_surcharge_equipment_ids.append(equipment_id)

    if overbilled_idle_or_consumables_equipment_ids:
        equipment_rate_status = "IDLE_STANDBY_OR_CONSUMABLES_OVERBILL_BREACH"
    elif unsubstantiated_fuel_surcharge_equipment_ids:
        equipment_rate_status = "FUEL_SURCHARGE_SUBSTANTIATION_WARNING"
    else:
        equipment_rate_status = "EQUIPMENT_FLEET_BILLING_OPTIMAL"

    return {
        "evaluated_equipment_count": len(valid_equipment),
        "overbilled_idle_or_consumables_equipment_ids": overbilled_idle_or_consumables_equipment_ids,
        "unsubstantiated_fuel_surcharge_equipment_ids": unsubstantiated_fuel_surcharge_equipment_ids,
        "equipment_rate_status": equipment_rate_status,
        "is_equipment_billing_compliant": equipment_rate_status
        == "EQUIPMENT_FLEET_BILLING_OPTIMAL",
    }


ProjectEVMService.evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate = staticmethod(
    evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate
)


def evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve(
    currency_tranches: list[dict[str, Any]],
    *,
    max_unhedged_exposure_pct: float = 15.0,
    max_fx_rate_collar_breach_pct: float = 5.0,
    require_revaluation_reserve_coverage: bool = True,
) -> dict[str, Any]:
    """PMBOK §7.4 & §11.5 — Evalúa banda de collar de cobertura cambiaria (FX hedging), tope de exposición descubierta y reserva de revaluación mark-to-market."""
    raw_items = currency_tranches if isinstance(currency_tranches, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    unhedged_or_underreserved_tranche_ids: list[str] = []
    collar_drift_tranche_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        tranche_id = (
            str(
                item.get("tranche_id") or item.get("id") or f"fx-{idx + 1}"
            ).strip()
            or f"fx-{idx + 1}"
        )
        total_foreign_commitment_usd = max(
            0.0, float(item.get("total_foreign_commitment_usd") or 0.0)
        )
        hedged_notional_usd = max(
            0.0, float(item.get("hedged_notional_usd") or 0.0)
        )

        raw_base = item.get("baseline_fx_rate", 1.0)
        baseline_fx_rate = float(1.0 if raw_base is None else raw_base)

        raw_spot = item.get("spot_fx_rate", 1.0)
        spot_fx_rate = float(1.0 if raw_spot is None else raw_spot)

        unrealized_fx_loss_usd = max(
            0.0, float(item.get("unrealized_fx_loss_usd") or 0.0)
        )
        fx_revaluation_reserve_usd = max(
            0.0, float(item.get("fx_revaluation_reserve_usd") or 0.0)
        )

        if total_foreign_commitment_usd > 0:
            unhedged_exposure_pct = round(
                max(0.0, total_foreign_commitment_usd - hedged_notional_usd)
                / total_foreign_commitment_usd
                * 100.0,
                2,
            )
        else:
            unhedged_exposure_pct = 0.0

        if baseline_fx_rate > 0:
            fx_rate_drift_pct = round(
                abs(spot_fx_rate - baseline_fx_rate) / baseline_fx_rate * 100.0,
                2,
            )
        else:
            fx_rate_drift_pct = 0.0

        unhedged_exposure_or_reserve_deficit_breach = bool(
            unhedged_exposure_pct > max_unhedged_exposure_pct
            or (
                require_revaluation_reserve_coverage
                and unrealized_fx_loss_usd > fx_revaluation_reserve_usd
            )
        )
        fx_collar_band_exceeded = (
            fx_rate_drift_pct > max_fx_rate_collar_breach_pct
        )

        if unhedged_exposure_or_reserve_deficit_breach:
            unhedged_or_underreserved_tranche_ids.append(tranche_id)
            has_critical = True
            violations.append(
                f"Tranche '{tranche_id}' exceeds unhedged exposure cap or has FX revaluation reserve deficit."
            )

        if fx_collar_band_exceeded:
            collar_drift_tranche_ids.append(tranche_id)
            has_warning = True
            violations.append(
                f"Tranche '{tranche_id}' FX rate drift ({fx_rate_drift_pct}%) exceeds collar band ({max_fx_rate_collar_breach_pct}%)."
            )

        records.append(
            {
                "tranche_id": tranche_id,
                "total_foreign_commitment_usd": total_foreign_commitment_usd,
                "hedged_notional_usd": hedged_notional_usd,
                "unhedged_exposure_pct": unhedged_exposure_pct,
                "baseline_fx_rate": baseline_fx_rate,
                "spot_fx_rate": spot_fx_rate,
                "fx_rate_drift_pct": fx_rate_drift_pct,
                "unrealized_fx_loss_usd": unrealized_fx_loss_usd,
                "fx_revaluation_reserve_usd": fx_revaluation_reserve_usd,
                "unhedged_exposure_or_reserve_deficit_breach": unhedged_exposure_or_reserve_deficit_breach,
                "fx_collar_band_exceeded": fx_collar_band_exceeded,
            }
        )

    if has_critical:
        status = "critical"
        is_compliant = False
    elif has_warning:
        status = "warning"
        is_compliant = False
    else:
        status = "compliant"
        is_compliant = True

    return {
        "status": status,
        "is_compliant": is_compliant,
        "tranches_evaluated": len(records),
        "unhedged_or_underreserved_tranche_ids": unhedged_or_underreserved_tranche_ids,
        "collar_drift_tranche_ids": collar_drift_tranche_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


ProjectEVMService.evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve = staticmethod(
    evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve
)


def evaluate_evm_economic_price_adjustment_epa_corridor_and_share(
    commodity_clauses: list[dict[str, Any]],
    *,
    deadband_corridor_pct: float = 5.0,
    max_owner_epa_payout_cap_pct: float = 15.0,
    require_published_bls_or_lme_index: bool = True,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.1 — Evalúa banda muerta (deadband corridor) de cláusulas EPA por índice de commodities, verificación de índice BLS/LME publicado y tope de ajuste asumido por el dueño."""
    raw_items = commodity_clauses if isinstance(commodity_clauses, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    improper_deadband_or_index_clause_ids: list[str] = []
    cap_exceeded_clause_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        clause_id = (
            str(
                item.get("clause_id") or item.get("id") or f"epa-{idx + 1}"
            ).strip()
            or f"epa-{idx + 1}"
        )
        baseline_commodity_cost = max(
            0.0, float(item.get("baseline_commodity_cost") or 0.0)
        )
        index_change_pct = float(item.get("index_change_pct") or 0.0)
        billed_epa_adjustment_amount = max(
            0.0, float(item.get("billed_epa_adjustment_amount") or 0.0)
        )

        raw_verified = item.get("published_index_verified", True)
        published_index_verified = bool(
            True if raw_verified is None else raw_verified
        )

        epa_payout_pct = (
            round(
                (billed_epa_adjustment_amount / baseline_commodity_cost) * 100.0,
                2,
            )
            if baseline_commodity_cost > 0.0
            else 0.0
        )

        unverified_index_or_within_deadband_billing = bool(
            (require_published_bls_or_lme_index and not published_index_verified)
            or (
                abs(index_change_pct) <= deadband_corridor_pct
                and billed_epa_adjustment_amount > 0.0
            )
        )
        epa_payout_cap_exceeded = bool(
            baseline_commodity_cost > 0.0
            and (billed_epa_adjustment_amount / baseline_commodity_cost) * 100.0
            > max_owner_epa_payout_cap_pct
        )

        if unverified_index_or_within_deadband_billing:
            improper_deadband_or_index_clause_ids.append(clause_id)
            has_critical = True
            violations.append(
                f"EPA clause '{clause_id}' billed within deadband corridor (|{index_change_pct}%| <= {deadband_corridor_pct}%) or lacks published BLS/LME index verification."
            )

        if epa_payout_cap_exceeded:
            cap_exceeded_clause_ids.append(clause_id)
            has_warning = True
            violations.append(
                f"EPA clause '{clause_id}' payout ({epa_payout_pct}%) exceeds maximum owner cap ({max_owner_epa_payout_cap_pct}%)."
            )

        records.append(
            {
                "clause_id": clause_id,
                "baseline_commodity_cost": baseline_commodity_cost,
                "index_change_pct": index_change_pct,
                "billed_epa_adjustment_amount": billed_epa_adjustment_amount,
                "epa_payout_pct": epa_payout_pct,
                "published_index_verified": published_index_verified,
                "unverified_index_or_within_deadband_billing": unverified_index_or_within_deadband_billing,
                "epa_payout_cap_exceeded": epa_payout_cap_exceeded,
            }
        )

    if has_critical:
        status = "critical"
        is_compliant = False
    elif has_warning:
        status = "warning"
        is_compliant = False
    else:
        status = "compliant"
        is_compliant = True

    return {
        "status": status,
        "is_compliant": is_compliant,
        "clauses_evaluated": len(records),
        "improper_deadband_or_index_clause_ids": improper_deadband_or_index_clause_ids,
        "cap_exceeded_clause_ids": cap_exceeded_clause_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


ProjectEVMService.evaluate_evm_economic_price_adjustment_epa_corridor_and_share = staticmethod(
    evaluate_evm_economic_price_adjustment_epa_corridor_and_share
)

def evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
    current_bac: float,
    original_contract_sum: float,
    performance_bond_penal_sum: float,
    payment_bond_penal_sum: float,
    sdi_subcontractor_exposures: list[dict[str, Any]] | None = None,
    *,
    sdi_deductible_per_loss: float = 50000.0,
    sdi_coinsurance_pct: float = 10.0,
    min_bond_coverage_ratio_pct: float = 100.0,
    max_unendorsed_bac_growth_pct: float = 10.0,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.2 — Evalúa cobertura de fianzas de performance/payment (penal sum) vs BAC vigente, crecimiento de BAC sin rider de fianza, pérdidas retenidas de SDI e indemnización neta por incumplimiento de subcontratistas.

    - Cobertura de cada fianza: `(penal_sum / current_bac) * 100.0`; si el BAC
      no es positivo se asume 100.0 (noevaluable, sin subcobertura).
    - Crecimiento de BAC sin rider: `((current_bac / original_contract_sum) - 1)
      * 100.0`; si la suma original no es positiva se asume 0.0.
    - SDI por exposición válida (subcontractor_id str no vacío): retención =
      min(costo, deducible) + coaseguro% aplicado al exceso sobre el deducible;
      indemnización neta = max(0, costo - retención).
    - Estados (precedencia): 'CRITICAL_BOND_UNDERCOVERAGE' si alguna fianza
      cubre menos del mínimo; 'RIDER_ENDORSEMENT_REQUIRED' si el crecimiento
      de BAC excede el máximo no endosado; 'BOND_ADEQUATE' si limpio.
    """
    def _safe_float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _coverage_ratio_pct(penal_sum: float) -> float:
        bac = _safe_float(current_bac, 0.0)
        sum_val = _safe_float(penal_sum, 0.0)
        if bac <= 0:
            return 100.0
        return round(sum_val / bac * 100.0, 2)

    performance_coverage_ratio_pct = _coverage_ratio_pct(performance_bond_penal_sum)
    payment_coverage_ratio_pct = _coverage_ratio_pct(payment_bond_penal_sum)

    bac_value = _safe_float(current_bac, 0.0)
    original_sum = _safe_float(original_contract_sum, 0.0)
    if original_sum > 0 and bac_value > 0:
        bac_growth_pct = round((bac_value / original_sum - 1.0) * 100.0, 2)
    else:
        bac_growth_pct = 0.0

    deductible = _safe_float(sdi_deductible_per_loss, 50000.0)
    coinsurance_pct = _safe_float(sdi_coinsurance_pct, 10.0)

    raw_exposures = (
        sdi_subcontractor_exposures if isinstance(sdi_subcontractor_exposures, list) else []
    )
    valid_exposures = []
    for item in raw_exposures:
        if not isinstance(item, dict):
            continue
        subcontractor_id = item.get("subcontractor_id")
        if not isinstance(subcontractor_id, str) or not subcontractor_id.strip():
            continue
        valid_exposures.append(item)

    defaulted_exposures_count = 0
    sdi_retained_loss_total = 0.0
    sdi_net_recoverable_total = 0.0
    for exposure in valid_exposures:
        if exposure.get("status") != "DEFAULTED":
            continue
        defaulted_exposures_count += 1
        exposure_cost = _safe_float(exposure.get("exposure_cost"), 0.0)
        if exposure_cost <= 0:
            continue
        retained_loss = min(exposure_cost, deductible)
        if exposure_cost > deductible:
            retained_loss += (exposure_cost - deductible) * coinsurance_pct / 100.0
        sdi_retained_loss_total += round(retained_loss, 2)
        sdi_net_recoverable_total += round(max(0.0, exposure_cost - retained_loss), 2)

    sdi_retained_loss_total = round(sdi_retained_loss_total, 2)
    sdi_net_recoverable_total = round(sdi_net_recoverable_total, 2)

    critical_bond_undercoverage = (
        performance_coverage_ratio_pct < _safe_float(min_bond_coverage_ratio_pct, 100.0)
        or payment_coverage_ratio_pct < _safe_float(min_bond_coverage_ratio_pct, 100.0)
    )
    rider_endorsement_required = bac_growth_pct > _safe_float(
        max_unendorsed_bac_growth_pct, 10.0
    )

    if critical_bond_undercoverage:
        bond_coverage_status = "CRITICAL_BOND_UNDERCOVERAGE"
    elif rider_endorsement_required:
        bond_coverage_status = "RIDER_ENDORSEMENT_REQUIRED"
    else:
        bond_coverage_status = "BOND_ADEQUATE"

    return {
        "bac_growth_pct": bac_growth_pct,
        "performance_bond_coverage_ratio_pct": performance_coverage_ratio_pct,
        "payment_bond_coverage_ratio_pct": payment_coverage_ratio_pct,
        "sdi_evaluated_subcontractors_count": len(valid_exposures),
        "sdi_defaulted_exposures_count": defaulted_exposures_count,
        "sdi_retained_loss_total": sdi_retained_loss_total,
        "sdi_net_recoverable_total": sdi_net_recoverable_total,
        "bond_coverage_status": bond_coverage_status,
        "is_surety_coverage_adequate": bond_coverage_status == "BOND_ADEQUATE",
    }


ProjectEVMService.evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi = staticmethod(
    evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi
)
def evaluate_evm_vecp_net_savings_and_contractor_share_split(
    proposals: list[dict[str, Any]] | None,
    *,
    contractor_instant_share_pct: float = 50.0,
    collateral_savings_royalty_pct: float = 20.0,
    max_collateral_cap_per_proposal: float = 100000.0,
    min_net_savings_roi_ratio: float = 1.5,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.2 — Evalúa VECP bajo FAR 52.248-1: ahorro neto instantáneo de adquisición, split del share del contratista, regalía de ahorros colaterales de O&M y ratio ROI mínimo de implementación.

    Cada propuesta válida declara `proposal_id` (str no vacío),
    `gross_instant_contract_savings` (default 0.0),
    `contractor_development_cost` (default 0.0),
    `government_implementation_cost` (default 0.0),
    `annual_collateral_om_savings` (default 0.0) y
    `technical_equivalence_certified` (default True):
    - `net_instant_savings = gross - desarrollo - implementación` (por propuesta).
    - Si net > 0 y certificada: share contratista = net * share_pct/100;
      share propietario = net - share; regalía colateral = min(cap,
      max(0, O&M anual) * royalty_pct/100).
    - `owner_net_benefit` = share propietario + regalía colateral.
    - `uncertified_or_negative_net_proposal_ids`: no certificada o net <= 0
      (brecha de viabilidad, precedencia).
    - `low_roi_proposal_ids`: costos > 0 y gross/costos < min ROI (advertencia).
    - Estados: 'UNVIABLE_OR_UNCERTIFIED_VECP_BREACH' |
      'LOW_ROI_IMPLEMENTATION_WARNING' | 'VECP_PORTFOLIO_ACCRETIVE'.
    """
    raw_items = proposals if isinstance(proposals, list) else []
    valid_proposals: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_proposal_id = item.get("proposal_id")
        if not isinstance(raw_proposal_id, str) or not raw_proposal_id.strip():
            continue
        valid_proposals.append(item)

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    share_pct = _float(contractor_instant_share_pct, 50.0)
    royalty_pct = _float(collateral_savings_royalty_pct, 20.0)
    collateral_cap = _float(max_collateral_cap_per_proposal, 100000.0)
    min_roi_ratio = _float(min_net_savings_roi_ratio, 1.5)

    total_net_instant_savings = 0.0
    total_contractor_share_amount = 0.0
    total_owner_net_benefit_amount = 0.0
    total_collateral_royalty_amount = 0.0
    uncertified_or_negative_net_proposal_ids: list[str] = []
    low_roi_proposal_ids: list[str] = []

    for proposal in valid_proposals:
        proposal_id = str(proposal.get("proposal_id")).strip()
        gross_savings = _float(proposal.get("gross_instant_contract_savings"), 0.0)
        development_cost = _float(proposal.get("contractor_development_cost"), 0.0)
        implementation_cost = _float(
            proposal.get("government_implementation_cost"), 0.0
        )
        annual_collateral = _float(proposal.get("annual_collateral_om_savings"), 0.0)
        certified = _bool(
            proposal.get("technical_equivalence_certified"), True
        )

        net_instant_savings = round(
            gross_savings - development_cost - implementation_cost, 2
        )

        if not bool(certified) or net_instant_savings <= 0:
            uncertified_or_negative_net_proposal_ids.append(proposal_id)
        else:
            contractor_instant_share = round(
                net_instant_savings * share_pct / 100.0, 2
            )
            owner_instant_share = round(net_instant_savings - contractor_instant_share, 2)
            collateral_royalty = round(
                min(collateral_cap, max(0.0, annual_collateral) * royalty_pct / 100.0),
                2,
            )
            total_net_instant_savings = round(
                total_net_instant_savings + net_instant_savings, 2
            )
            total_contractor_share_amount = round(
                total_contractor_share_amount + contractor_instant_share, 2
            )
            total_owner_net_benefit_amount = round(
                total_owner_net_benefit_amount
                + owner_instant_share
                + collateral_royalty,
                2,
            )
            total_collateral_royalty_amount = round(
                total_collateral_royalty_amount + collateral_royalty, 2
            )

        implementation_total = development_cost + implementation_cost
        if implementation_total > 0 and gross_savings / implementation_total < min_roi_ratio:
            low_roi_proposal_ids.append(proposal_id)

    if uncertified_or_negative_net_proposal_ids:
        vecp_evaluation_status = "UNVIABLE_OR_UNCERTIFIED_VECP_BREACH"
    elif low_roi_proposal_ids:
        vecp_evaluation_status = "LOW_ROI_IMPLEMENTATION_WARNING"
    else:
        vecp_evaluation_status = "VECP_PORTFOLIO_ACCRETIVE"

    return {
        "evaluated_proposal_count": len(valid_proposals),
        "total_net_instant_savings": total_net_instant_savings,
        "total_contractor_share_amount": total_contractor_share_amount,
        "total_owner_net_benefit_amount": total_owner_net_benefit_amount,
        "total_collateral_royalty_amount": total_collateral_royalty_amount,
        "uncertified_or_negative_net_proposal_ids": uncertified_or_negative_net_proposal_ids,
        "low_roi_proposal_ids": low_roi_proposal_ids,
        "vecp_evaluation_status": vecp_evaluation_status,
        "is_vecp_portfolio_accretive": vecp_evaluation_status
        == "VECP_PORTFOLIO_ACCRETIVE",
    }


ProjectEVMService.evaluate_evm_vecp_net_savings_and_contractor_share_split = staticmethod(
    evaluate_evm_vecp_net_savings_and_contractor_share_split
)
def evaluate_evm_builders_risk_dsu_indemnity_and_subrogation_waiver(
    claims: list[dict[str, Any]] | None,
    *,
    policy_tcv_limit: float = 10000000.0,
    current_forecast_eac: float = 10000000.0,
    dsu_waiting_period_days: int = 30,
    dsu_daily_indemnity_rate: float = 15000.0,
    max_uninsured_loss_pct_of_eac: float = 2.0,
) -> dict[str, Any]:
    """PMBOK §7.4 & §11.5 — Evalúa la póliza Builder's Risk: límite TCV vs EAC vigente (riesgo de coaseguro por subaseguro), indemnidad DSU con periodo de espera, pérdidas retenidas no aseguradas y renuncia de subrogación endosada.

    Cada siniestro válido declara `claim_id` (str no vacío),
    `physical_damage_loss` (default 0.0), `physical_deductible`
    (default 25000.0), `delay_days` (default 0) y
    `waiver_of_subrogation_endorsed` (default True):
    - `net_physical_recovery = max(0, daño - deducible)`.
    - `compensable_dsu_days = max(0, delay_days - waiting_period)`;
      indemnidad DSU = días compensables * tarifa diaria.
    - `uninsured_retained_loss = (danio - recuperacion neta) + espera
      compensada (min(delay, waiting) * tarifa diaria)`.
    - `tcv_underinsured_gap_amount = max(0, EAC - límite TCV)`: el crecimiento
      del EAC por encima del límite TCV sin rider es brecha crítica de
      coaseguro.
    - `unendorsed_subrogation_claim_ids`: renuncia de subrogación sin endosar
      (brecha crítica, precedencia sobre la advertencia).
    - Advertencia: total de pérdidas retenidas > max_uninsured_loss_pct_of_eac
      del EAC.
    - Estados: 'CRITICAL_TCV_UNDERINSURANCE_OR_SUBROGATION_BREACH' |
      'UNINSURED_RETENTION_OR_DSU_DEDUCTIBLE_WARNING' |
      'BUILDERS_RISK_COVERAGE_SOUND'.
    """
    raw_items = claims if isinstance(claims, list) else []
    valid_claims: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_claim_id = item.get("claim_id")
        if not isinstance(raw_claim_id, str) or not raw_claim_id.strip():
            continue
        valid_claims.append(item)

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    eac_value = _float(current_forecast_eac, 10000000.0)
    tcv_limit = _float(policy_tcv_limit, 10000000.0)
    waiting_period = _int(dsu_waiting_period_days, 30)
    daily_rate = _float(dsu_daily_indemnity_rate, 15000.0)

    total_physical_recovery_amount = 0.0
    total_dsu_indemnity_amount = 0.0
    total_uninsured_retained_loss = 0.0
    unendorsed_subrogation_claim_ids: list[str] = []

    for claim in valid_claims:
        claim_id = str(claim.get("claim_id")).strip()
        damage_loss = _float(claim.get("physical_damage_loss"), 0.0)
        deductible = _float(claim.get("physical_deductible"), 25000.0)
        delay_days = _int(claim.get("delay_days"), 0)
        subro_endorsed = _bool(
            claim.get("waiver_of_subrogation_endorsed"), True
        )

        net_physical_recovery = round(
            max(0.0, float(damage_loss) - float(deductible)), 2
        )
        compensable_dsu_days = max(0, int(delay_days) - int(waiting_period))
        dsu_indemnity = round(compensable_dsu_days * daily_rate, 2)
        waiting_indemnified_cost = round(
            min(max(0, int(delay_days)), max(0, int(waiting_period)))
            * daily_rate,
            2,
        )
        retained_loss = round(
            (float(damage_loss) - net_physical_recovery) + waiting_indemnified_cost,
            2,
        )

        total_physical_recovery_amount = round(
            total_physical_recovery_amount + net_physical_recovery, 2
        )
        total_dsu_indemnity_amount = round(
            total_dsu_indemnity_amount + dsu_indemnity, 2
        )
        total_uninsured_retained_loss = round(
            total_uninsured_retained_loss + retained_loss, 2
        )

        if not bool(subro_endorsed):
            unendorsed_subrogation_claim_ids.append(claim_id)

    tcv_underinsured_gap_amount = round(max(0.0, eac_value - tcv_limit), 2)

    tcv_or_subrogation_breach = (
        tcv_underinsured_gap_amount > 0.0
        or bool(unendorsed_subrogation_claim_ids)
    )
    eac_positive = eac_value > 0
    uninsured_pct_of_eac = round(
        total_uninsured_retained_loss / eac_value * 100.0, 2
    ) if eac_positive else 0.0
    retention_warning = (
        eac_positive
        and uninsured_pct_of_eac
        > _float(max_uninsured_loss_pct_of_eac, 2.0)
    )

    if tcv_or_subrogation_breach:
        builders_risk_status = "CRITICAL_TCV_UNDERINSURANCE_OR_SUBROGATION_BREACH"
    elif retention_warning:
        builders_risk_status = "UNINSURED_RETENTION_OR_DSU_DEDUCTIBLE_WARNING"
    else:
        builders_risk_status = "BUILDERS_RISK_COVERAGE_SOUND"

    return {
        "evaluated_claim_count": len(valid_claims),
        "total_physical_recovery_amount": total_physical_recovery_amount,
        "total_dsu_indemnity_amount": total_dsu_indemnity_amount,
        "total_uninsured_retained_loss": total_uninsured_retained_loss,
        "tcv_underinsured_gap_amount": tcv_underinsured_gap_amount,
        "unendorsed_subrogation_claim_ids": unendorsed_subrogation_claim_ids,
        "builders_risk_status": builders_risk_status,
        "is_builders_risk_coverage_sound": builders_risk_status
        == "BUILDERS_RISK_COVERAGE_SOUND",
    }


ProjectEVMService.evaluate_evm_builders_risk_dsu_indemnity_and_subrogation_waiver = staticmethod(
    evaluate_evm_builders_risk_dsu_indemnity_and_subrogation_waiver
)
def evaluate_evm_prevailing_wage_wh347_payroll_and_restitution_withholding(
    payrolls: list[dict[str, Any]] | None,
    *,
    statutory_liquidated_damages_per_violation_day: float = 31.0,
    max_wh347_filing_delay_days: int = 7,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.2 — Evalúa Davis-Bacon: shortfall de salario prevalecente + beneficios, retención de restitución salarial, WH-347 certificado atrasado y daños liquidados estatutarios por día de violación.

    Cada nómina válida declara `payroll_id` (str no vacío), tarifa pagada
    (`paid_hourly_rate`, default 40.0), tarifa prevaleciente
    (`prevailing_wage_rate`, default 40.0), fringe pagado
    (`paid_fringe_rate`, default 15.0), fringe requerido
    (`required_fringe_rate`, default 15.0), horas trabajadas
    (`hours_worked`, default 40.0), días de violación por trabajador
    (`violation_worker_days`, default 0), atraso de filing WH-347
    (`wh347_filing_delay_days`, default 0) y cumplimiento de ratio de
    aprendices (`apprentice_ratio_compliant`, default True):
    - `hourly_shortfall = max(0, (prev + fringe_req) - (paid + fringe_pag))`.
    - `wage_restitution_due = shortfall * max(0, horas)`.
    - `statutory_ld_penalty`: violación_worker_days * LD por día, solo si
      shortfall > 0 o ratio de aprendices incumplido; si no, 0.0.
    - `underpaid_or_ratio_breach_payroll_ids`: shortfall > 0 o ratio incumplido
      (brecha crítica, precedencia).
    - `late_wh347_certified_payroll_ids`: atraso de filing > máximo
      (estricto; == máximo es OK) (advertencia).
    - Estados: 'CRITICAL_WAGE_UNDERPAYMENT_OR_RATIO_BREACH' |
      'LATE_WH347_CERTIFICATION_WARNING' | 'PREVAILING_WAGE_WH347_COMPLIANT'.
    """
    raw_items = payrolls if isinstance(payrolls, list) else []
    valid_payrolls: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_payroll_id = item.get("payroll_id")
        if not isinstance(raw_payroll_id, str) or not raw_payroll_id.strip():
            continue
        valid_payrolls.append(item)

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    ld_per_day = _float(
        statutory_liquidated_damages_per_violation_day, 31.0
    )

    total_wage_restitution_withholding = 0.0
    total_statutory_liquidated_damages = 0.0
    underpaid_or_ratio_breach_payroll_ids: list[str] = []
    late_wh347_certified_payroll_ids: list[str] = []

    for payroll in valid_payrolls:
        payroll_id = str(payroll.get("payroll_id")).strip()
        paid_rate = _float(payroll.get("paid_hourly_rate"), 40.0)
        prevailing_rate = _float(payroll.get("prevailing_wage_rate"), 40.0)
        paid_fringe = _float(payroll.get("paid_fringe_rate"), 15.0)
        required_fringe = _float(payroll.get("required_fringe_rate"), 15.0)
        hours_worked = _float(payroll.get("hours_worked"), 40.0)
        violation_days = _int(payroll.get("violation_worker_days"), 0)
        filing_delay_days = _int(payroll.get("wh347_filing_delay_days"), 0)
        ratio_compliant = _bool(
            payroll.get("apprentice_ratio_compliant"), True
        )

        hourly_shortfall = round(
            max(
                0.0,
                (float(prevailing_rate) + float(required_fringe))
                - (float(paid_rate) + float(paid_fringe)),
            ),
            2,
        )
        wage_restitution_due = round(
            hourly_shortfall * max(0.0, float(hours_worked)), 2
        )

        if hourly_shortfall > 0 or not bool(ratio_compliant):
            underpaid_or_ratio_breach_payroll_ids.append(payroll_id)
            statutory_ld_penalty = round(
                max(0, int(violation_days)) * ld_per_day, 2
            )
        else:
            statutory_ld_penalty = 0.0

        total_wage_restitution_withholding = round(
            total_wage_restitution_withholding + wage_restitution_due, 2
        )
        total_statutory_liquidated_damages = round(
            total_statutory_liquidated_damages + statutory_ld_penalty, 2
        )

        if int(filing_delay_days) > int(max_wh347_filing_delay_days):
            late_wh347_certified_payroll_ids.append(payroll_id)

    if underpaid_or_ratio_breach_payroll_ids:
        prevailing_wage_status = "CRITICAL_WAGE_UNDERPAYMENT_OR_RATIO_BREACH"
    elif late_wh347_certified_payroll_ids:
        prevailing_wage_status = "LATE_WH347_CERTIFICATION_WARNING"
    else:
        prevailing_wage_status = "PREVAILING_WAGE_WH347_COMPLIANT"

    return {
        "evaluated_payroll_count": len(valid_payrolls),
        "total_wage_restitution_withholding": total_wage_restitution_withholding,
        "total_statutory_liquidated_damages": total_statutory_liquidated_damages,
        "underpaid_or_ratio_breach_payroll_ids": underpaid_or_ratio_breach_payroll_ids,
        "late_wh347_certified_payroll_ids": late_wh347_certified_payroll_ids,
        "prevailing_wage_status": prevailing_wage_status,
        "is_prevailing_wage_compliant": prevailing_wage_status
        == "PREVAILING_WAGE_WH347_COMPLIANT",
    }


ProjectEVMService.evaluate_evm_prevailing_wage_wh347_payroll_and_restitution_withholding = staticmethod(
    evaluate_evm_prevailing_wage_wh347_payroll_and_restitution_withholding
)
def evaluate_evm_stored_materials_bonded_warehouse_and_title_transfer(
    material_vouchers: list[dict[str, Any]] | None,
    *,
    current_contract_bac: float = 5000000.0,
    max_stored_materials_pct_of_bac: float = 15.0,
    offsite_payment_advance_cap_pct: float = 75.0,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.3 — Evalúa pagos de progreso por materiales almacenados (stored materials): elegibilidad bill-and-hold (title transfer, segregación/tagging, seguro all-risk, almacén bonded), cap de anticipo off-site y participación sobre el BAC vigente.

    Cada voucher válido declara `voucher_id` (str no vacío),
    `invoiced_material_cost` (default 0.0), `storage_location` (default
    'ONSITE'; se normaliza upper: ONSITE | OFFSITE_BONDED |
    OFFSITE_UNBONDED), `bill_of_sale_title_transferred` (default True),
    `segregated_and_tagged_for_project` (default True) y
    `all_risk_transit_storage_insured` (default True):
    - Elegible: title transfer Y segregado/taggeado Y asegurado Y ubicación
      != OFFSITE_UNBONDED. Los no elegibles son bill-and-hold improcedente
      (brecha crítica, precedencia) y su importe es disallowed.
    - Pago elegible: ONSITE 100% del importe; OFFSITE_BONDED
      advance_cap_pct% del importe.
    - `stored_materials_bac_share_pct` = total payable / BAC * 100.0;
      share > max_stored_materials_pct_of_bac es advertencia de cap.
    - Estados: 'CRITICAL_UNBONDED_OR_UNTITLED_BILL_AND_HOLD_BREACH' |
      'STORED_MATERIALS_BAC_CAP_WARNING' | 'STORED_MATERIALS_BILLING_COMPLIANT'.
    """
    raw_items = material_vouchers if isinstance(material_vouchers, list) else []
    valid_vouchers: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_voucher_id = item.get("voucher_id")
        if not isinstance(raw_voucher_id, str) or not raw_voucher_id.strip():
            continue
        valid_vouchers.append(item)

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    bac_value = _float(current_contract_bac, 5000000.0)
    advance_cap_pct = _float(offsite_payment_advance_cap_pct, 75.0)

    total_payable_stored_materials_amount = 0.0
    disallowed_stored_materials_amount = 0.0
    ineligible_bill_and_hold_voucher_ids: list[str] = []
    evaluated_voucher_count = 0

    for voucher in valid_vouchers:
        evaluated_voucher_count += 1
        voucher_id = str(voucher.get("voucher_id")).strip()
        invoiced_cost = _float(voucher.get("invoiced_material_cost"), 0.0)
        raw_location = voucher.get("storage_location")
        location = (
            raw_location.upper()
            if isinstance(raw_location, str)
            else "ONSITE"
        )
        title_transferred = _bool(
            voucher.get("bill_of_sale_title_transferred"), True
        )
        segregated = _bool(
            voucher.get("segregated_and_tagged_for_project"), True
        )
        insured = _bool(
            voucher.get("all_risk_transit_storage_insured"), True
        )

        eligible = bool(
            title_transferred
            and segregated
            and insured
            and location != "OFFSITE_UNBONDED"
        )

        if not eligible:
            ineligible_bill_and_hold_voucher_ids.append(voucher_id)
            disallowed_stored_materials_amount = round(
                disallowed_stored_materials_amount
                + max(0.0, float(invoiced_cost)),
                2,
            )
            continue

        if location == "ONSITE":
            payable_advance = float(invoiced_cost)
        else:
            payable_advance = float(invoiced_cost) * advance_cap_pct / 100.0
        total_payable_stored_materials_amount = round(
            total_payable_stored_materials_amount + max(0.0, payable_advance), 2
        )

    stored_materials_bac_share_pct = round(
        total_payable_stored_materials_amount / bac_value * 100.0, 2
    ) if bac_value > 0 else 0.0

    if ineligible_bill_and_hold_voucher_ids:
        stored_materials_status = "CRITICAL_UNBONDED_OR_UNTITLED_BILL_AND_HOLD_BREACH"
    elif (
        bac_value > 0
        and stored_materials_bac_share_pct
        > _float(max_stored_materials_pct_of_bac, 15.0)
    ):
        stored_materials_status = "STORED_MATERIALS_BAC_CAP_WARNING"
    else:
        stored_materials_status = "STORED_MATERIALS_BILLING_COMPLIANT"

    return {
        "evaluated_voucher_count": evaluated_voucher_count,
        "total_payable_stored_materials_amount": total_payable_stored_materials_amount,
        "disallowed_stored_materials_amount": disallowed_stored_materials_amount,
        "stored_materials_bac_share_pct": stored_materials_bac_share_pct,
        "ineligible_bill_and_hold_voucher_ids": ineligible_bill_and_hold_voucher_ids,
        "stored_materials_status": stored_materials_status,
        "is_stored_materials_billing_compliant": stored_materials_status
        == "STORED_MATERIALS_BILLING_COMPLIANT",
    }


ProjectEVMService.evaluate_evm_stored_materials_bonded_warehouse_and_title_transfer = staticmethod(
    evaluate_evm_stored_materials_bonded_warehouse_and_title_transfer
)
def evaluate_evm_prompt_payment_act_flowdown_and_interest_penalty(
    disbursements: list[dict[str, Any]] | None,
    *,
    max_flowdown_days_after_owner_receipt: int = 7,
    annual_statutory_interest_rate_pct: float = 12.0,
    max_disputed_withholding_multiplier: float = 1.5,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.2 — Evalúa Prompt Payment Act (31 U.S.C. §3905) en flow-down a subcontratistas: plazo de 7 días tras el pago del owner, interés estatutario anual prorrateado por días de retraso y retención bona fide de disputas (good-faith disputed withholding).

    Cada desembolso válido declara `disbursement_id` (str no vacío),
    `undisputed_sub_amount` (default 0.0),
    `days_elapsed_since_owner_payment` (default 3),
    `disputed_defect_estimate` (default 0.0),
    `actual_withheld_amount` (default 0.0) y
    `written_dispute_notice_served` (default True):
    - `late_days = max(0, días transcurridos - max_flowdown_days)`.
    - `interest_penalty = max(0, undisputed) * rate_pct/100 * late_days/365`.
    - `abusive_withholding_disbursement_ids`: retención activa sin aviso
      escrito de disputa o por encima de defect_estimate * multiplicador
      (brecha crítica, precedencia).
    - `late_flowdown_disbursement_ids`: late_days > 0 con importe undisputed
      > 0 (advertencia de interés).
    - Estados: 'CRITICAL_UNLAWFUL_WITHHOLDING_BREACH' |
      'LATE_DISBURSEMENT_INTEREST_WARNING' |
      'PROMPT_PAYMENT_FLOWDOWN_COMPLIANT'.
    """
    raw_items = disbursements if isinstance(disbursements, list) else []
    valid_items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("disbursement_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_items.append(item)

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    flowdown_limit = _int(max_flowdown_days_after_owner_receipt, 7)
    rate_pct = _float(annual_statutory_interest_rate_pct, 12.0)
    withholding_multiplier = _float(max_disputed_withholding_multiplier, 1.5)

    total_interest_penalty_accrued = 0.0
    abusive_withholding_disbursement_ids: list[str] = []
    late_flowdown_disbursement_ids: list[str] = []

    for disbursement in valid_items:
        disbursement_id = str(disbursement.get("disbursement_id")).strip()
        undisputed_amount = _float(disbursement.get("undisputed_sub_amount"), 0.0)
        days_elapsed = _int(
            disbursement.get("days_elapsed_since_owner_payment"), 3
        )
        defect_estimate = _float(disbursement.get("disputed_defect_estimate"), 0.0)
        withheld_amount = _float(disbursement.get("actual_withheld_amount"), 0.0)
        notice_served = _bool(
            disbursement.get("written_dispute_notice_served"), True
        )

        late_days = max(0, int(days_elapsed) - int(flowdown_limit))
        interest_penalty = round(
            max(0.0, float(undisputed_amount))
            * rate_pct
            / 100.0
            * (late_days / 365.0),
            2,
        )
        total_interest_penalty_accrued = round(
            total_interest_penalty_accrued + interest_penalty, 2
        )

        excessive_or_unnoticed_withholding = float(withheld_amount) > 0 and (
            (not bool(notice_served))
            or float(withheld_amount)
            > max(0.0, float(defect_estimate)) * withholding_multiplier
        )
        if excessive_or_unnoticed_withholding:
            abusive_withholding_disbursement_ids.append(disbursement_id)

        if late_days > 0 and float(undisputed_amount) > 0:
            late_flowdown_disbursement_ids.append(disbursement_id)

    if abusive_withholding_disbursement_ids:
        prompt_payment_status = "CRITICAL_UNLAWFUL_WITHHOLDING_BREACH"
    elif late_flowdown_disbursement_ids:
        prompt_payment_status = "LATE_DISBURSEMENT_INTEREST_WARNING"
    else:
        prompt_payment_status = "PROMPT_PAYMENT_FLOWDOWN_COMPLIANT"

    return {
        "evaluated_disbursement_count": len(valid_items),
        "total_interest_penalty_accrued": total_interest_penalty_accrued,
        "abusive_withholding_disbursement_ids": abusive_withholding_disbursement_ids,
        "late_flowdown_disbursement_ids": late_flowdown_disbursement_ids,
        "prompt_payment_status": prompt_payment_status,
        "is_prompt_payment_compliant": prompt_payment_status
        == "PROMPT_PAYMENT_FLOWDOWN_COMPLIANT",
    }


ProjectEVMService.evaluate_evm_prompt_payment_act_flowdown_and_interest_penalty = staticmethod(
    evaluate_evm_prompt_payment_act_flowdown_and_interest_penalty
)


def evaluate_evm_force_majeure_weather_days_and_eichleay_hooh_claim(
    contract_billings: float,
    total_company_billings: float,
    total_home_office_overhead: float,
    contract_performance_days: int,
    compensable_owner_delay_days: int,
    *,
    claimed_weather_delay_days: int = 0,
    contractual_noaa_baseline_weather_days: int = 10,
    contractor_on_standby: bool = True,
    replacement_work_available: bool = False,
    max_hooh_claim_pct_of_contract: float = 10.0,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.3 — Evalúa reclamaciones de construcción por force majeure: allowance de días de clima excusables non-compensable contra baseline contractual (NOAA) y fórmula Eichleay de overhead de home-office no absorbido (HOOH) por demora compensable del owner.

    Fórmula Eichleay: `allocable_hooh = (max(0, contract_billings) /
    max(1, total_company_billings)) * max(0, total_home_office_overhead)`
    (0.0 si las facturaciones de compañía son <= 0); la tasa diaria
    reparte entre días de performance del contrato (0.0 si <= 0):
    - `eichleay_eligible`: contractor en standby, sin reemplazo disponible
      y con demora compensable del owner > 0. Sin elegibilidad no hay claim
      HOOH (demora compensable sin elegibilidad es brecha crítica, precedencia)
      al igual que el claim que excede `max_hooh_claim_pct_of_contract`.
    - `net_excusable_weather_extension_days` = excedente del clima reclamado
      sobre el baseline contractual (excusable, non-compensable).
    - Estados: 'CRITICAL_DISPUTED_EICHLEAY_OR_EXCESS_HOOH_BREACH' |
      'COMPENSABLE_OR_EXCUSABLE_EXTENSION_WARNING' |
      'WITHIN_BASELINE_ALLOWANCE_CLEAN'.
    """
    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    contract_billed = _float(contract_billings, 0.0)
    company_billed = _float(total_company_billings, 0.0)
    hooh_total = _float(total_home_office_overhead, 0.0)
    performance_days = _int(contract_performance_days, 0)
    owner_delay_days = _int(compensable_owner_delay_days, 0)

    claimed_weather = _int(claimed_weather_delay_days, 0)
    baseline_weather = _int(contractual_noaa_baseline_weather_days, 10)
    standby = _bool(contractor_on_standby, True)
    replacement_available = _bool(replacement_work_available, False)
    claim_cap = _float(max_hooh_claim_pct_of_contract, 10.0)

    if company_billed > 0:
        allocable_hooh_raw = (
            max(0.0, contract_billed) / max(1.0, company_billed)
        ) * max(0.0, hooh_total)
    else:
        allocable_hooh_raw = 0.0

    if performance_days > 0:
        daily_contract_hooh_rate_raw = allocable_hooh_raw / max(1, performance_days)
    else:
        daily_contract_hooh_rate_raw = 0.0

    eichleay_eligible = (
        standby
        and (not replacement_available)
        and owner_delay_days > 0
    )

    if eichleay_eligible:
        unabsorbed_hooh_claim_amount = round(
            daily_contract_hooh_rate_raw * max(0, owner_delay_days), 2
        )
    else:
        unabsorbed_hooh_claim_amount = 0.0

    net_excusable_weather_extension_days = max(
        0, claimed_weather - max(0, baseline_weather)
    )

    if contract_billed > 0:
        hooh_claim_pct_of_contract = round(
            (unabsorbed_hooh_claim_amount / max(1.0, contract_billed)) * 100.0, 2
        )
    else:
        hooh_claim_pct_of_contract = 0.0

    disputed_without_eligibility = (
        owner_delay_days > 0 and (not eichleay_eligible)
    )
    excess_claim = hooh_claim_pct_of_contract > claim_cap

    if disputed_without_eligibility or excess_claim:
        delay_claim_status = "CRITICAL_DISPUTED_EICHLEAY_OR_EXCESS_HOOH_BREACH"
    elif unabsorbed_hooh_claim_amount > 0 or net_excusable_weather_extension_days > 0:
        delay_claim_status = "COMPENSABLE_OR_EXCUSABLE_EXTENSION_WARNING"
    else:
        delay_claim_status = "WITHIN_BASELINE_ALLOWANCE_CLEAN"

    return {
        "allocable_hooh": round(allocable_hooh_raw, 2),
        "daily_contract_hooh_rate": round(daily_contract_hooh_rate_raw, 2),
        "eichleay_eligible": eichleay_eligible,
        "unabsorbed_hooh_claim_amount": unabsorbed_hooh_claim_amount,
        "net_excusable_weather_extension_days": net_excusable_weather_extension_days,
        "hooh_claim_pct_of_contract": hooh_claim_pct_of_contract,
        "delay_claim_status": delay_claim_status,
    }


ProjectEVMService.evaluate_evm_force_majeure_weather_days_and_eichleay_hooh_claim = staticmethod(
    evaluate_evm_force_majeure_weather_days_and_eichleay_hooh_claim
)


def evaluate_evm_cardinal_change_and_cumulative_impact_leonard_loss(
    original_contract_hours: float,
    approved_change_order_hours: float,
    base_labor_rate_per_hour: float,
    *,
    unpriced_field_directives_count: int = 0,
    leonard_coefficient: float = 0.29,
    cardinal_change_hours_threshold_pct: float = 50.0,
    cumulative_impact_trigger_pct: float = 10.0,
    bilateral_cumulative_waiver_signed: bool = False,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.3 — Evalúa la doctrina de cardinal change y la pérdida de productividad sinérgica por impacto acumulativo (curva de Leonard) en contratos de construcción: ripple de horas de change orders sobre el contrato original, costo del ripple sobre horas base no impactadas y umbral de abandono de contrato.

    - `change_order_hours_pct = max(0, CO hours) / max(1, original hours) * 100`
      (0.0 si el contrato original es <= 0).
    - `ripple_triggered`: CO pct >= `cumulative_impact_trigger_pct` (10.0,
      inclusivo) sin waiver bilateral de impacto acumulativo firmado.
    - `productivity_loss_pct` = pct * `leonard_coefficient` (0.29) si hay
      ripple; sobre horas base no impactadas del contrato original.
    - `cumulative_impact_cost_claim` = horas perdidas * tarifa laboral base.
    - `is_cardinal_change_breach`: CO pct >= umbral cardinal (50.0,
      inclusivo, doctrina de abandono) O directivas de campo sin precio > 10
      (estricto: 10 exacto NO es brecha).
    - Estados: 'CRITICAL_CARDINAL_CHANGE_OR_UNPRICED_DIRECTIVE_BREACH' |
      'CUMULATIVE_IMPACT_RIPPLE_CLAIM_WARNING' (ripple o directivas > 0) |
      'WITHIN_CONTRACT_SCOPE_CLEAN'.
    """
    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    original_hours = _float(original_contract_hours, 0.0)
    change_order_hours = _float(approved_change_order_hours, 0.0)
    labor_rate = _float(base_labor_rate_per_hour, 0.0)
    unpriced_count = _int(unpriced_field_directives_count, 0)
    leonard = _float(leonard_coefficient, 0.29)
    cardinal_threshold = _float(cardinal_change_hours_threshold_pct, 50.0)
    ripple_trigger = _float(cumulative_impact_trigger_pct, 10.0)
    waiver_signed = _bool(bilateral_cumulative_waiver_signed, False)

    if original_hours > 0:
        change_order_hours_pct = round(
            (max(0.0, change_order_hours) / max(1.0, original_hours)) * 100.0, 2
        )
    else:
        change_order_hours_pct = 0.0

    ripple_triggered = (
        change_order_hours_pct >= ripple_trigger and (not waiver_signed)
    )

    if ripple_triggered:
        productivity_loss_pct = round(
            (change_order_hours_pct / 100.0) * max(0.0, leonard) * 100.0, 2
        )
        unimpacted_base_hours_lost = round(
            max(0.0, original_hours) * (productivity_loss_pct / 100.0), 2
        )
    else:
        productivity_loss_pct = 0.0
        unimpacted_base_hours_lost = 0.0

    cumulative_impact_cost_claim = round(
        unimpacted_base_hours_lost * max(0.0, labor_rate), 2
    )

    is_cardinal_change_breach = (
        change_order_hours_pct >= cardinal_threshold or unpriced_count > 10
    )

    if is_cardinal_change_breach:
        cardinal_change_status = "CRITICAL_CARDINAL_CHANGE_OR_UNPRICED_DIRECTIVE_BREACH"
    elif ripple_triggered or unpriced_count > 0:
        cardinal_change_status = "CUMULATIVE_IMPACT_RIPPLE_CLAIM_WARNING"
    else:
        cardinal_change_status = "WITHIN_CONTRACT_SCOPE_CLEAN"

    return {
        "change_order_hours_pct": change_order_hours_pct,
        "productivity_loss_pct": productivity_loss_pct,
        "unimpacted_base_hours_lost": unimpacted_base_hours_lost,
        "cumulative_impact_cost_claim": cumulative_impact_cost_claim,
        "is_cardinal_change_breach": is_cardinal_change_breach,
        "cardinal_change_status": cardinal_change_status,
    }


ProjectEVMService.evaluate_evm_cardinal_change_and_cumulative_impact_leonard_loss = staticmethod(
    evaluate_evm_cardinal_change_and_cumulative_impact_leonard_loss
)


def evaluate_evm_differing_site_conditions_dsc_geotechnical_overrun(
    gbr_baseline_excavation_cost: float,
    actual_geotechnical_cost: float,
    *,
    dsc_claim_type: str = "TYPE_I",
    days_to_written_notice: int = 3,
    max_contractual_notice_days: int = 14,
    site_disturbed_before_owner_inspection: bool = False,
    owner_prejudice_established: bool = False,
    materiality_threshold_pct: float = 15.0,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.3 — Evalúa condiciones del sitio diferentes (Differing Site Conditions, FAR 52.236-2 Tipo I condiciones físicas inusual y Tipo II datos físicos desorientadores), overrun contra el Geotechnical Baseline Report (GBR) y la ventana de aviso escrito al owner sin disturbio ni perjuicio.

    - `geotechnical_overrun_amount = max(0, costo_geotecnico_real)
      - max(0, baseline_GBR)` (2 dec).
    - `overrun_pct_of_gbr` sobre `max(1, baseline)` (0.0 si baseline <= 0).
    - `valid_dsc_type`: 'TYPE_I' / 'TYPE_II' normalizados a mayúsculas.
    - `notice_timely`: `0 <= días_aviso <= ventana_contractual`.
    - `claim_barred_by_disturbance_or_late_notice`: sitio disturbado antes
      de la inspección del owner, aviso tardío con perjuicio establecido, o
      tipo de claim DSC inválido (brecha crítica en precedencia).
    - `equitable_adjustment_recoverable`: monto del overrun solo si el claim
      no está barrado y `overrun_pct >= materiality_threshold_pct` (15.0,
      inclusive).
    - Estados: 'CRITICAL_DSC_CLAIM_BARRED_OR_INVALID_BREACH' (overrun barrado)
      | 'EQUITABLE_ADJUSTMENT_OR_LATE_NOTICE_WARNING' (recuperable o aviso
      tardío) | 'WITHIN_GBR_GEOTECHNICAL_BASELINE_CLEAN'.
    """
    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    baseline_cost = _float(gbr_baseline_excavation_cost, 0.0)
    actual_cost = _float(actual_geotechnical_cost, 0.0)
    notice_days = _int(days_to_written_notice, 3)
    notice_window = _int(max_contractual_notice_days, 14)
    disturbed = _bool(site_disturbed_before_owner_inspection, False)
    prejudice = _bool(owner_prejudice_established, False)
    materiality = _float(materiality_threshold_pct, 15.0)

    geotechnical_overrun_amount = round(
        max(0.0, actual_cost) - max(0.0, baseline_cost), 2
    )

    if baseline_cost > 0:
        overrun_pct_of_gbr = round(
            (geotechnical_overrun_amount / max(1.0, baseline_cost)) * 100.0, 2
        )
    else:
        overrun_pct_of_gbr = 0.0

    valid_dsc_type = (
        str(dsc_claim_type).strip().upper() in {"TYPE_I", "TYPE_II"}
    )
    notice_timely = 0 <= notice_days <= notice_window

    claim_barred_by_disturbance_or_late_notice = (
        disturbed
        or ((not notice_timely) and prejudice)
        or (not valid_dsc_type)
    )

    if (not claim_barred_by_disturbance_or_late_notice) and (
        overrun_pct_of_gbr >= materiality
    ):
        equitable_adjustment_recoverable = round(
            geotechnical_overrun_amount, 2
        )
    else:
        equitable_adjustment_recoverable = 0.0

    if geotechnical_overrun_amount > 0 and (
        claim_barred_by_disturbance_or_late_notice
    ):
        dsc_claim_status = "CRITICAL_DSC_CLAIM_BARRED_OR_INVALID_BREACH"
    elif equitable_adjustment_recoverable > 0 or (
        geotechnical_overrun_amount > 0 and (not notice_timely)
    ):
        dsc_claim_status = "EQUITABLE_ADJUSTMENT_OR_LATE_NOTICE_WARNING"
    else:
        dsc_claim_status = "WITHIN_GBR_GEOTECHNICAL_BASELINE_CLEAN"

    return {
        "geotechnical_overrun_amount": geotechnical_overrun_amount,
        "overrun_pct_of_gbr": overrun_pct_of_gbr,
        "notice_timely": notice_timely,
        "claim_barred_by_disturbance_or_late_notice": claim_barred_by_disturbance_or_late_notice,
        "equitable_adjustment_recoverable": equitable_adjustment_recoverable,
        "dsc_claim_status": dsc_claim_status,
    }


ProjectEVMService.evaluate_evm_differing_site_conditions_dsc_geotechnical_overrun = staticmethod(
    evaluate_evm_differing_site_conditions_dsc_geotechnical_overrun
)


def evaluate_evm_termination_for_convenience_t4c_settlement_proposal(
    total_contract_ceiling: float,
    costs_incurred_to_date: float,
    demobilization_and_settlement_expenses: float,
    *,
    claimed_anticipatory_profit_on_unperformed_work: float = 0.0,
    reasonable_profit_rate_on_performed_pct: float = 8.0,
    estimated_cost_to_complete_unperformed: float = 0.0,
    payments_already_received: float = 0.0,
    proposal_submitted_days_after_t4c: int = 90,
    max_t4c_proposal_deadline_days: int = 365,
) -> dict[str, Any]:
    """PMBOK §12.3 & §7.4 — Evalúa la Termination for Convenience (T4C, FAR 52.249-2) de contratos de construcción: settlement proposal con costo incurrido, profit razonable sobre trabajo performed, allowance de demobilization y settlement expenses, cap del techo del contrato, ajuste de contrato en pérdida (loss-ratio, profit a 0), qué es neto tras pagos recibidos y la barra del profit anticipatorio sobre trabajo unperformed (PMBOK §12.3, prohibido bajo FAR 52.249-2).

    - `indicated_total_cost_at_completion = max(0, incurrido)
      + max(0, estimado_a_completar)`.
    - `is_loss_contract`: indicado > techo (con techo > 0) -> profit a 0.
    - `allowable_profit_on_performed`: incurrido * tasa (%), 0.0 si loss.
    - `gross_settlement_before_cap`: incurrido + profit + demobilización.
    - `capped_gross_settlement`: min(gross, techo + demobilización) si hay
      techo > 0; gross sin cap si no lo hay.
    - `net_t4c_settlement_payable`: capped + menos pagos recibidos (>= 0).
    - `proposal_timely`: `0 <= días desde la T4C <= plazo (365)`.
    - `disallowed_anticipatory_profit_claimed`: profit sobre trabajo
      unperformed > 0 (brecha crítica en precedencia, junto con la
      presentación fuera del plazo).
    - Estados: 'CRITICAL_DISALLOWED_ANTICIPATORY_PROFIT_OR_UNTIMELY_T4C_BREACH' |
      'LOSS_CONTRACT_PROFIT_ZEROED_OR_CAPPED_WARNING' (loss o capped < gross)
      | 'T4C_EQUITABLE_SETTLEMENT_CLEAN'.
    """
    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    ceiling = _float(total_contract_ceiling, 0.0)
    incurred = _float(costs_incurred_to_date, 0.0)
    demob = _float(demobilization_and_settlement_expenses, 0.0)
    anticipatory_claim = _float(
        claimed_anticipatory_profit_on_unperformed_work, 0.0
    )
    profit_rate = _float(reasonable_profit_rate_on_performed_pct, 8.0)
    est_to_complete = _float(estimated_cost_to_complete_unperformed, 0.0)
    received = _float(payments_already_received, 0.0)
    submitted_days = _int(proposal_submitted_days_after_t4c, 90)
    deadline_days = _int(max_t4c_proposal_deadline_days, 365)

    incurred_positive = max(0.0, incurred)
    demob_positive = max(0.0, demob)
    ceiling_positive = max(0.0, ceiling)

    indicated_total_cost_at_completion = (
        incurred_positive + max(0.0, est_to_complete)
    )
    is_loss_contract = (
        indicated_total_cost_at_completion > ceiling_positive
        and ceiling > 0
    )

    if is_loss_contract:
        allowable_profit_on_performed = 0.0
    else:
        allowable_profit_on_performed = round(
            incurred_positive * (max(0.0, profit_rate) / 100.0), 2
        )

    gross_settlement_before_cap = round(
        incurred_positive + allowable_profit_on_performed + demob_positive, 2
    )

    if ceiling > 0:
        capped_gross_settlement = round(
            min(
                gross_settlement_before_cap,
                ceiling_positive + demob_positive,
            ),
            2,
        )
    else:
        capped_gross_settlement = gross_settlement_before_cap

    net_t4c_settlement_payable = round(
        max(0.0, capped_gross_settlement - max(0.0, received)), 2
    )

    proposal_timely = 0 <= submitted_days <= deadline_days
    disallowed_anticipatory_profit_claimed = anticipatory_claim > 0.0

    if disallowed_anticipatory_profit_claimed or (not proposal_timely):
        t4c_settlement_status = "CRITICAL_DISALLOWED_ANTICIPATORY_PROFIT_OR_UNTIMELY_T4C_BREACH"
    elif is_loss_contract or gross_settlement_before_cap > capped_gross_settlement:
        t4c_settlement_status = "LOSS_CONTRACT_PROFIT_ZEROED_OR_CAPPED_WARNING"
    else:
        t4c_settlement_status = "T4C_EQUITABLE_SETTLEMENT_CLEAN"

    return {
        "is_loss_contract": is_loss_contract,
        "allowable_profit_on_performed": allowable_profit_on_performed,
        "gross_settlement_before_cap": gross_settlement_before_cap,
        "capped_gross_settlement": capped_gross_settlement,
        "net_t4c_settlement_payable": net_t4c_settlement_payable,
        "proposal_timely": proposal_timely,
        "t4c_settlement_status": t4c_settlement_status,
    }


ProjectEVMService.evaluate_evm_termination_for_convenience_t4c_settlement_proposal = staticmethod(
    evaluate_evm_termination_for_convenience_t4c_settlement_proposal
)


def evaluate_evm_acceleration_claim_overtime_inefficiency_and_shift_premium(
    base_straight_time_hours: float,
    overtime_hours_worked: float,
    base_hourly_wage: float,
    *,
    overtime_premium_multiplier: float = 1.5,
    brt_fatigue_inefficiency_pct: float = 15.0,
    excusable_delay_days_entitled: int = 10,
    time_extension_days_granted_by_owner: int = 0,
    owner_acceleration_order_or_denial_documented: bool = True,
    max_overtime_ratio_pct: float = 35.0,
) -> dict[str, Any]:
    """PMBOK §6.5 & §12.3 — Evalúa aceleración dirigida vs. constructiva (constructive acceleration) de un contrato de construcción: días de demora excusables no concedidos con orden/denial documentado del owner, premium de overtime con diferencial de turno (shift premium = horas OT * wage * (multiplicador - 1)), ineficiencia por fatiga de overtime según la curva BRT sobre las horas totales y ratio de overtime excesivo.

    - `ungranted_excusable_delay_days = max(0, entitled - granted)`.
    - `constructive_acceleration_established`: días no concedidos > 0 con
      orden/denial de aceleración del owner documentado.
    - `overtime_ratio_pct` sobre `max(1, horas_straight)` (0.0 si <= 0).
    - `overtime_shift_premium_cost`: horas OT * wage * (multiplicador - 1)
      (solo el diferencial de premium; time-and-a-half paga 0.5 extra).
    - `fatigue_lost_hours` (curva BRT): horas totales * pct de ineficiencia,
      solo si hay horas OT > 0.
    - `fatigue_inefficiency_cost = horas_perdidas * wage`.
    - `recoverable_acceleration_claim`: premium + fatiga solo si la
      aceleración constructiva está establecida (voluntad propia sin orden ni
      demora no concedida es overtime pedido, brecha crítica en precedencia,
      igual que un ratio > `max_overtime_ratio_pct`).
    - Estados: 'CRITICAL_VOLUNTARY_UNORDERED_OR_EXCESSIVE_OVERTIME_BREACH' |
      'CONSTRUCTIVE_ACCELERATION_RECOVERABLE_WARNING' |
      'NO_ACCELERATION_BASELINE_PACE_CLEAN'.
    """
    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    straight_hours = _float(base_straight_time_hours, 0.0)
    ot_hours = _float(overtime_hours_worked, 0.0)
    wage = _float(base_hourly_wage, 0.0)
    ot_multiplier = _float(overtime_premium_multiplier, 1.5)
    brt_pct = _float(brt_fatigue_inefficiency_pct, 15.0)
    entitled_days = _int(excusable_delay_days_entitled, 10)
    granted_days = _int(time_extension_days_granted_by_owner, 0)
    order_documented = _bool(
        owner_acceleration_order_or_denial_documented, True
    )
    ratio_cap = _float(max_overtime_ratio_pct, 35.0)

    straight_positive = max(0.0, straight_hours)
    ot_positive = max(0.0, ot_hours)

    ungranted_excusable_delay_days = max(
        0, entitled_days - max(0, granted_days)
    )
    constructive_acceleration_established = (
        ungranted_excusable_delay_days > 0 and order_documented
    )

    if straight_hours > 0:
        overtime_ratio_pct = round(
            (ot_positive / max(1.0, straight_positive)) * 100.0, 2
        )
    else:
        overtime_ratio_pct = 0.0

    overtime_shift_premium_cost = round(
        ot_positive
        * max(0.0, wage)
        * max(0.0, ot_multiplier - 1.0),
        2,
    )

    if ot_positive > 0:
        fatigue_lost_hours = round(
            (straight_positive + ot_positive)
            * (max(0.0, brt_pct) / 100.0),
            2,
        )
    else:
        fatigue_lost_hours = 0.0

    fatigue_inefficiency_cost = round(
        fatigue_lost_hours * max(0.0, wage), 2
    )

    if constructive_acceleration_established:
        recoverable_acceleration_claim = round(
            overtime_shift_premium_cost + fatigue_inefficiency_cost, 2
        )
    else:
        recoverable_acceleration_claim = 0.0

    excessive_overtime_ratio = overtime_ratio_pct > ratio_cap
    unordered_overtime = ot_positive > 0 and (
        not constructive_acceleration_established
    )

    if unordered_overtime or excessive_overtime_ratio:
        acceleration_claim_status = "CRITICAL_VOLUNTARY_UNORDERED_OR_EXCESSIVE_OVERTIME_BREACH"
    elif recoverable_acceleration_claim > 0:
        acceleration_claim_status = "CONSTRUCTIVE_ACCELERATION_RECOVERABLE_WARNING"
    else:
        acceleration_claim_status = "NO_ACCELERATION_BASELINE_PACE_CLEAN"

    return {
        "constructive_acceleration_established": constructive_acceleration_established,
        "overtime_ratio_pct": overtime_ratio_pct,
        "overtime_shift_premium_cost": overtime_shift_premium_cost,
        "fatigue_inefficiency_cost": fatigue_inefficiency_cost,
        "recoverable_acceleration_claim": recoverable_acceleration_claim,
        "acceleration_claim_status": acceleration_claim_status,
    }


ProjectEVMService.evaluate_evm_acceleration_claim_overtime_inefficiency_and_shift_premium = staticmethod(
    evaluate_evm_acceleration_claim_overtime_inefficiency_and_shift_premium
)


def evaluate_evm_surety_performance_bond_t4d_takeover_and_overpayment(
    remaining_contract_balance_unpaid: float,
    estimated_cost_to_complete_by_replacement: float,
    performance_bond_penal_sum: float,
    *,
    front_loaded_overpayment_detected_amount: float = 0.0,
    cure_notice_10_day_expired: bool = True,
    surety_takeover_agreement_executed: bool = True,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.3 — Evalúa la ejecución de la fianza de cumplimiento (surety performance bond) tras una Termination for Default (T4D): deficit de completion contra el balance no pagado del contrato, ejecución del takeover agreement de la afianzadora, deducción pro-tanto del sobrepago por front-loading negligente del propietario del penal sum, indemne indemnización de la afianzadora y exposición no afianzada del propietario.

    - `net_completion_deficit` = max(0, costo_reemplazo - balance_no_pagado).
    - `effective_bond_penal_cap` = penal_sum - sobrepago_front_loading
      (la afianzadora deduce pro-tanto el sobrepago negligente del owner).
    - `surety_recoverable_indemnity` = min(deficit, cap) solo si el cure
      notice de 10 días expiró con el takeover agreement ejecutado; si falta
      cualquiera de los dos, la indemnización no es ejecutable.
    - `unbonded_owner_exposure` = deficit - indemnidad, exposición que el
      penal sum no cubre.
    - `bond_discharge_or_exhaustion_breach`: cure notice sin expirar, takeover
      sin ejecutar, o exposición no afianzada > 0.
    - Estados (precedencia): 'CRITICAL_SURETY_DISCHARGE_OR_PENAL_SUM_EXHAUSTION_BREACH'
      (deficit con breach) | 'SURETY_BOND_INDEMNIFIED_TAKEOVER_WARNING'
      (deficit o sobrepago detectado) |
      'CONTRACT_BALANCE_SUFFICIENT_NO_BOND_CALL_CLEAN'.
    """
    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _clamp_non_negative_float(value: Any, default: float) -> float:
        coerced = _float(value, default)
        return max(0.0, coerced)

    balance_unpaid = _clamp_non_negative_float(
        remaining_contract_balance_unpaid, 0.0
    )
    replacement_cost = _clamp_non_negative_float(
        estimated_cost_to_complete_by_replacement, 0.0
    )
    penal_sum = _clamp_non_negative_float(
        performance_bond_penal_sum, 0.0
    )
    front_load_overpayment = _clamp_non_negative_float(
        front_loaded_overpayment_detected_amount, 0.0
    )
    cure_expired = _bool(cure_notice_10_day_expired, True)
    takeover_executed = _bool(surety_takeover_agreement_executed, True)

    net_completion_deficit = round(
        max(0.0, replacement_cost - balance_unpaid), 2
    )
    effective_bond_penal_cap = round(
        max(0.0, penal_sum - front_load_overpayment), 2
    )

    if cure_expired and takeover_executed:
        surety_recoverable_indemnity = round(
            min(net_completion_deficit, effective_bond_penal_cap), 2
        )
    else:
        surety_recoverable_indemnity = 0.0

    unbonded_owner_exposure = round(
        max(0.0, net_completion_deficit - surety_recoverable_indemnity), 2
    )

    bond_discharge_or_exhaustion_breach = (
        (not cure_expired)
        or (not takeover_executed)
        or unbonded_owner_exposure > 0.0
    )

    if net_completion_deficit > 0.0 and bond_discharge_or_exhaustion_breach:
        t4d_surety_status = "CRITICAL_SURETY_DISCHARGE_OR_PENAL_SUM_EXHAUSTION_BREACH"
    elif net_completion_deficit > 0.0 or front_load_overpayment > 0.0:
        t4d_surety_status = "SURETY_BOND_INDEMNIFIED_TAKEOVER_WARNING"
    else:
        t4d_surety_status = "CONTRACT_BALANCE_SUFFICIENT_NO_BOND_CALL_CLEAN"

    return {
        "net_completion_deficit": net_completion_deficit,
        "effective_bond_penal_cap": effective_bond_penal_cap,
        "surety_recoverable_indemnity": surety_recoverable_indemnity,
        "unbonded_owner_exposure": unbonded_owner_exposure,
        "bond_discharge_or_exhaustion_breach": bond_discharge_or_exhaustion_breach,
        "t4d_surety_status": t4d_surety_status,
    }


ProjectEVMService.evaluate_evm_surety_performance_bond_t4d_takeover_and_overpayment = staticmethod(
    evaluate_evm_surety_performance_bond_t4d_takeover_and_overpayment
)


def evaluate_evm_davis_bacon_prevailing_wage_wh347_and_restitution(
    hours_worked_by_craft: float,
    actual_hourly_rate_plus_fringe_paid: float,
    wd_prevailing_hourly_rate_plus_fringe: float,
    *,
    uncertified_wh347_payroll_weeks_count: int = 0,
    apprentice_ratio_exceeded_workers_count: int = 0,
    falsified_payroll_or_kickback_detected: bool = False,
    copeland_act_liquidated_damages_per_day: float = 31.0,
) -> dict[str, Any]:
    """PMBOK §9.4 & §12.3 — Evaluador Davis-Bacon (FAR 52.222-6) de salario prevaleciente + fringe, restitución de back wages, nómina certificada WH-347 sin certificar, ratio de aprendices excedido y riesgo de inhabilitación de 3 años por nómina falsificada o kickbacks (Copeland Act LD 31.0/día).

    Coerción de entradas: floats inválidos (`bool` excluido) o negativos
    clamp a 0.0; enteros inválidos (`bool` excluido) o negativos clamp a 0;
    flags inválidos revierten a su default (`False`); LD por día de tipo
    inválido revierte a su default 31.0.
    Calcula:
    - `hourly_wage_shortfall = max(0.0, prevaleciente - pagado)`, 2 dec.
    - `back_wages_restitution_owed = horas * shortfall`, 2 dec.
    - `cwssa_liquidated_damages = (semanas WH-347 sin certificar * 5 +
      trabajadores con ratio de aprendices excedido * 5) * LD/día`, 2 dec.
    - `total_contract_withholding_amount` = restitución + LD, 2 dec.
    - `three_year_debarment_risk_triggered`: falsificación/kickback o
      shortfall > 0 con >= 4 semanas de WH-347 sin certificar.
    Estados con precedencia CRITICAL > WARNING > CLEAN:
    - 'CRITICAL_DAVIS_BACON_DEBARMENT_OR_KICKBACK_WITHHOLDING_BREACH':
      riesgo de inhabilitación o restitución > 10000.0.
    - 'DAVIS_BACON_WH347_DELINQUENCY_OR_WAGE_RESTITUTION_WARNING':
      retención total > 0.0.
    - 'DAVIS_BACON_WH347_PREVAILING_WAGE_COMPLIANT_CLEAN': sin hallazgos.
    """
    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _clamp_non_negative_float(value: Any, default: float) -> float:
        return max(0.0, _float(value, default))

    def _clamp_non_negative_int(value: Any, default: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return max(0, int(value))

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    hours_worked = _clamp_non_negative_float(hours_worked_by_craft, 0.0)
    actual_rate_paid = _clamp_non_negative_float(
        actual_hourly_rate_plus_fringe_paid, 0.0
    )
    prevailing_rate = _clamp_non_negative_float(
        wd_prevailing_hourly_rate_plus_fringe, 0.0
    )
    uncertified_weeks = _clamp_non_negative_int(
        uncertified_wh347_payroll_weeks_count, 0
    )
    apprentices_exceeded = _clamp_non_negative_int(
        apprentice_ratio_exceeded_workers_count, 0
    )
    falsified_or_kickback = _bool(
        falsified_payroll_or_kickback_detected, False
    )
    ld_per_day = _clamp_non_negative_float(
        copeland_act_liquidated_damages_per_day, 31.0
    )

    hourly_wage_shortfall = round(
        max(0.0, prevailing_rate - actual_rate_paid), 2
    )
    back_wages_restitution_owed = round(
        hours_worked * hourly_wage_shortfall, 2
    )
    cwssa_liquidated_damages = round(
        (uncertified_weeks * 5 + apprentices_exceeded * 5) * ld_per_day,
        2,
    )
    total_contract_withholding_amount = round(
        back_wages_restitution_owed + cwssa_liquidated_damages, 2
    )
    three_year_debarment_risk_triggered = bool(
        falsified_or_kickback
        or (hourly_wage_shortfall > 0.0 and uncertified_weeks >= 4)
    )

    if (
        three_year_debarment_risk_triggered
        or back_wages_restitution_owed > 10000.0
    ):
        davis_bacon_compliance_status = (
            "CRITICAL_DAVIS_BACON_DEBARMENT_OR_KICKBACK_WITHHOLDING_BREACH"
        )
    elif total_contract_withholding_amount > 0.0:
        davis_bacon_compliance_status = (
            "DAVIS_BACON_WH347_DELINQUENCY_OR_WAGE_RESTITUTION_WARNING"
        )
    else:
        davis_bacon_compliance_status = (
            "DAVIS_BACON_WH347_PREVAILING_WAGE_COMPLIANT_CLEAN"
        )

    return {
        "hourly_wage_shortfall": hourly_wage_shortfall,
        "back_wages_restitution_owed": back_wages_restitution_owed,
        "cwssa_liquidated_damages": cwssa_liquidated_damages,
        "total_contract_withholding_amount": total_contract_withholding_amount,
        "three_year_debarment_risk_triggered":
            three_year_debarment_risk_triggered,
        "davis_bacon_compliance_status": davis_bacon_compliance_status,
    }


ProjectEVMService.evaluate_evm_davis_bacon_prevailing_wage_wh347_and_restitution = staticmethod(
    evaluate_evm_davis_bacon_prevailing_wage_wh347_and_restitution
)


def evaluate_evm_vecp_far_52_248_shared_savings_and_development_cost_offset(
    gross_instant_contract_savings: float,
    allowable_contractor_vecp_development_cost: float,
    government_implementation_cost: float = 0.0,
    *,
    contractor_sharing_rate_pct: float = 50.0,
    essential_function_or_safety_degraded: bool = False,
    formal_contract_modification_bilateral_signed: bool = True,
) -> dict[str, Any]:
    """PMBOK §7.4 & §12.2 — Evaluador VECP (FAR 52.248-1) de Ingeniería de Valor: ahorro instantáneo bruto en contrato, costo de desarrollo permitido del contratista, costo de implementación del gobierno (Net Acquisition Savings), rate de participación acotado [20, 75] y condición de modificación bilateral con esencial/seguridad sin degradar.

    Coerción: montos inválidos (`bool` excluido) o negativos clamp a 0.0;
    `contractor_sharing_rate_pct` acotado a [20.0, 75.0] (default 50.0 si
    tipo inválido o bool); flags inválidos revierten a sus defaults
    (`False`/`True`).
    Calcula:
    - `net_acquisition_savings = bruto - desarrollo permitido -
      implementación del gobierno`, 2 dec (puede ser negativo).
    - `contractor_incentive_share_amount` y `owner_retained_net_savings`:
      solo si no hay degradación de esencial/seguridad, modificación
      bilateral firmada y ahorro neto > 0.0; comparten el ahorro neto
      máximo(0, ...) según el rate; en caso contrario 0.0.
    - `vecp_uneconomic_or_rejected`: degradación, sin modificación
      bilateral, o ahorro neto <= 0.0.
    Estados (precedencia CRITICAL > WARNING > CLEAN):
    - 'CRITICAL_VECP_SAFETY_DEGRADATION_OR_UNILATERAL_IMPLEMENTATION_BREACH'
      (degradación de esencial/seguridad o implementación unilateral).
    - 'VECP_NEGATIVE_NET_ACQUISITION_SAVINGS_UNECONOMIC_WARNING'.
    - 'VECP_SHARED_SAVINGS_ACCREDITED_CLEAN'.
    """
    def _float(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _clamp_non_negative_float(value: Any, default: float) -> float:
        return max(0.0, _float(value, default))

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    gross_savings = _clamp_non_negative_float(
        gross_instant_contract_savings, 0.0
    )
    development_cost = _clamp_non_negative_float(
        allowable_contractor_vecp_development_cost, 0.0
    )
    implementation_cost = _clamp_non_negative_float(
        government_implementation_cost, 0.0
    )
    if isinstance(contractor_sharing_rate_pct, bool) or not isinstance(
        contractor_sharing_rate_pct, (int, float)
    ):
        clamped_sharing_rate_pct = 50.0
    else:
        clamped_sharing_rate_pct = float(
            min(75.0, max(20.0, float(contractor_sharing_rate_pct)))
        )
    safety_degraded = _bool(essential_function_or_safety_degraded, False)
    bilateral_signed = _bool(formal_contract_modification_bilateral_signed, True)

    net_acquisition_savings = round(
        gross_savings - development_cost - implementation_cost, 2
    )

    savings_accredited = bool(
        (not safety_degraded)
        and bilateral_signed
        and net_acquisition_savings > 0.0
    )

    if savings_accredited:
        contractor_incentive_share_amount = round(
            max(0.0, net_acquisition_savings)
            * (clamped_sharing_rate_pct / 100.0),
            2,
        )
        owner_retained_net_savings = round(
            max(0.0, net_acquisition_savings)
            - contractor_incentive_share_amount,
            2,
        )
    else:
        contractor_incentive_share_amount = 0.0
        owner_retained_net_savings = 0.0

    vecp_uneconomic_or_rejected = bool(
        safety_degraded
        or (not bilateral_signed)
        or (net_acquisition_savings <= 0.0)
    )

    if safety_degraded or (not bilateral_signed):
        vecp_evaluation_status = (
            "CRITICAL_VECP_SAFETY_DEGRADATION_OR_UNILATERAL_IMPLEMENTATION_BREACH"
        )
    elif net_acquisition_savings <= 0.0:
        vecp_evaluation_status = (
            "VECP_NEGATIVE_NET_ACQUISITION_SAVINGS_UNECONOMIC_WARNING"
        )
    else:
        vecp_evaluation_status = "VECP_SHARED_SAVINGS_ACCREDITED_CLEAN"

    return {
        "clamped_sharing_rate_pct": clamped_sharing_rate_pct,
        "net_acquisition_savings": net_acquisition_savings,
        "contractor_incentive_share_amount": contractor_incentive_share_amount,
        "owner_retained_net_savings": owner_retained_net_savings,
        "vecp_uneconomic_or_rejected": vecp_uneconomic_or_rejected,
        "vecp_evaluation_status": vecp_evaluation_status,
    }


ProjectEVMService.evaluate_evm_vecp_far_52_248_shared_savings_and_development_cost_offset = staticmethod(
    evaluate_evm_vecp_far_52_248_shared_savings_and_development_cost_offset
)

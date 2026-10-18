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

            total_comp_budget = sum(b for _, b, cnt in comp_entries if cnt > 0)
            if total_comp_budget > 0 and not unassigned_tasks:
                weighted_ev = sum(pct * b for pct, b, cnt in comp_entries if cnt > 0 and b > 0)
                budget_denom = sum(b for _, b, cnt in comp_entries if cnt > 0 and b > 0)
                if budget_denom > 0:
                    return round(weighted_ev / budget_denom, 1)

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

    return {
        "is_auto": True,
        "source_type": src,
        "frente": frente,
        "current_value": round(current_val, 2),
        "suggested_target": round(eff_target, 2),
        "spi": spi,
        "unit": unit,
        "component_name": comp_label,
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
    def evaluate_earned_schedule_performance(
        planned_value_curve: Optional[List[float]],
        earned_value: float,
        actual_time_periods: float,
        planned_duration_periods: Optional[float] = None,
    ) -> Dict[str, Any]:
        return evaluate_earned_schedule_performance(
            planned_value_curve,
            earned_value,
            actual_time_periods,
            planned_duration_periods=planned_duration_periods,
        )

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


def evaluate_earned_schedule_performance(
    planned_value_curve: Optional[List[float]],
    earned_value: float,
    actual_time_periods: float,
    planned_duration_periods: Optional[float] = None,
) -> Dict[str, Any]:
    """Evalúa el Cronograma Ganado (Earned Schedule - ES) e índice SPI(t) proyectando EV sobre la curva acumulada de PV según PMI Practice Standard for EVM y PMBOK §7.4."""
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
            if (planned_duration_periods is not None and float(planned_duration_periods) > 0.0)
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
        fraction = ((ev - pv_points[c_idx]) / delta_pv) if delta_pv > 0.0 else 0.0
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


__all__ = [
    "evaluate_funding_limit_periods_reconciliation",
    "evaluate_earned_schedule_performance",
    "evaluate_burn_rate_runway_sustainability",
    "evaluate_cpi_spi_stability_window",
    "evaluate_reserve_drawdown_velocity",
    "ProjectEVMService",
]

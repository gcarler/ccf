"""Pruebas unitarias para EVM Avanzado, Matriz de 4 Cuadrantes, Modelos EAC, Tiempo Ganado (ES) y Organigrama WBS.

Fase 4 del Plan Maestro PMI.
"""

from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

from backend import models, schemas
from backend.services.project_evm_service import (
    build_project_wbs_tree,
    calculate_cpi_spi_quadrant,
    calculate_eac_forecasts,
    calculate_earned_schedule,
    calculate_project_evm_advanced,
    calculate_tcpi,
)


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(timezone.utc)



def test_earned_schedule_standard_ahead_and_behind():
    """Valida los cálculos matemáticos de Tiempo Ganado (Earned Schedule - ES)."""
    now = _utcnow()
    start_dt = now - timedelta(days=50)
    target_dt = now + timedelta(days=50)  # Planned Duration = 100 days

    project = MagicMock(spec=models.Project)
    project.start_date = start_dt
    project.created_at = start_dt
    project.target_date = target_dt

    db = MagicMock()

    # Caso 1: Atrasado en tiempo (AT = 50 días, pero EV solo cubre 25% del BAC)
    bac = 100000.0
    ev_behind = 25000.0  # 25%
    es_data_behind = calculate_earned_schedule(db, project, ev=ev_behind, bac=bac, now=now)

    assert es_data_behind["planned_duration_days"] == 100.0
    assert es_data_behind["actual_time_days"] == 50.0
    # En curva sigmoidea, 25% de EV ocurre antes del 50% de tiempo (ES < 50 días)
    assert es_data_behind["earned_schedule_days"] < 50.0
    assert es_data_behind["schedule_variance_time_days"] < 0.0  # Retraso en días
    assert es_data_behind["schedule_performance_index_time"] < 1.0  # SPI(t) < 1.0
    assert es_data_behind["estimated_duration_at_completion_days"] > 100.0  # Proyecto tardará más de 100 días
    assert es_data_behind["time_variance_at_completion_days"] < 0.0

    # Caso 2: Adelantado en tiempo (AT = 50 días, pero EV ya lleva 80% del BAC)
    ev_ahead = 80000.0
    es_data_ahead = calculate_earned_schedule(db, project, ev=ev_ahead, bac=bac, now=now)
    assert es_data_ahead["earned_schedule_days"] > 50.0
    assert es_data_ahead["schedule_variance_time_days"] > 0.0
    assert es_data_ahead["schedule_performance_index_time"] > 1.0
    assert es_data_ahead["estimated_duration_at_completion_days"] < 100.0
    assert es_data_ahead["time_variance_at_completion_days"] > 0.0


def test_earned_schedule_edge_cases():
    """Valida casos extremos: EV cero, EV mayor o igual a BAC, o BAC cero."""
    now = _utcnow()
    project = MagicMock(spec=models.Project)
    project.start_date = now - timedelta(days=20)
    project.created_at = project.start_date
    project.target_date = now + timedelta(days=80)

    db = MagicMock()

    # EV cero
    es_zero = calculate_earned_schedule(db, project, ev=0.0, bac=100000.0, now=now)
    assert es_zero["earned_schedule_days"] == 0.0
    assert es_zero["schedule_performance_index_time"] == 0.0

    # EV >= BAC (Completado)
    es_done = calculate_earned_schedule(db, project, ev=100000.0, bac=100000.0, now=now)
    assert es_done["earned_schedule_days"] == 100.0
    assert es_done["time_variance_at_completion_days"] >= 0.0


def test_eac_forecast_three_models():
    """Valida los 3 modelos canónicos de pronóstico EAC, ETC y VAC según PMBOK."""
    bac = 100000.0
    ev = 40000.0
    ac = 50000.0
    cpi = 0.8  # Sobrecosto (40k / 50k = 0.8)
    spi = 0.8  # Atraso (40k / 50k = 0.8)

    forecasts = calculate_eac_forecasts(bac=bac, ev=ev, ac=ac, cpi=cpi, spi=spi)

    # 1. Típico: EAC = AC + (BAC - EV) / CPI = 50,000 + 60,000 / 0.8 = 50,000 + 75,000 = 125,000
    typ = forecasts["typical"]
    assert typ["model_key"] == "typical"
    assert typ["eac"] == 125000.0
    assert typ["etc"] == 75000.0
    assert typ["vac"] == -25000.0
    assert typ["vac_percentage"] == -25.0

    # 2. Atípico: EAC = AC + (BAC - EV) = 50,000 + 60,000 = 110,000
    atyp = forecasts["atypical"]
    assert atyp["model_key"] == "atypical"
    assert atyp["eac"] == 110000.0
    assert atyp["etc"] == 60000.0
    assert atyp["vac"] == -10000.0
    assert atyp["vac_percentage"] == -10.0

    # 3. Combinado (CPI x SPI): EAC = AC + (BAC - EV) / (0.8 * 0.8) = 50,000 + 60,000 / 0.64 = 50,000 + 93,750 = 143,750
    comp = forecasts["composite"]
    assert comp["model_key"] == "composite"
    assert comp["eac"] == 143750.0
    assert comp["etc"] == 93750.0
    assert comp["vac"] == -43750.0
    assert comp["vac_percentage"] == -43.8


def test_tcpi_calculations():
    """Valida el cálculo del To-Complete Performance Index (TCPI) respecto a BAC y EAC."""
    bac = 100000.0
    ev = 40000.0

    # Caso 1: ac = 30,000 (bajo presupuesto, holgura)
    # Work remaining = 60,000, Funds remaining = 70,000 -> TCPI = 60/70 = 0.86
    tcpi_easy = calculate_tcpi(bac=bac, ev=ev, ac=30000.0, eac=90000.0)
    assert tcpi_easy["tcpi_bac"] == 0.86
    assert tcpi_easy["is_budget_depleted"] is False
    assert tcpi_easy["difficulty_level"] == "feasible"

    # Caso 2: ac = 70,000 (sobrecosto severo)
    # Work remaining = 60,000, Funds remaining = 30,000 -> TCPI = 60/30 = 2.0
    tcpi_hard = calculate_tcpi(bac=bac, ev=ev, ac=70000.0, eac=130000.0)
    assert tcpi_hard["tcpi_bac"] == 2.0
    assert tcpi_hard["difficulty_level"] == "hard"

    # Caso 3: Presupuesto agotado (ac >= bac)
    tcpi_depleted = calculate_tcpi(bac=bac, ev=ev, ac=105000.0, eac=150000.0)
    assert tcpi_depleted["is_budget_depleted"] is True
    assert tcpi_depleted["difficulty_level"] == "critical"
    assert tcpi_depleted["tcpi_bac"] is None


def test_cpi_spi_quadrants_and_early_warning_rule_15():
    """Valida los 4 cuadrantes y la activación de alertas tempranas (Regla 15%)."""
    # Cuadrante 1: Óptimo (CPI >= 1.0, SPI >= 1.0)
    q1 = calculate_cpi_spi_quadrant(
        cpi=1.1, spi=1.05, spi_t=1.05, cr=1.15, physical_pct=50.0, financial_pct=45.0, tcpi_bac=0.9
    )
    assert q1["quadrant_number"] == 1
    assert q1["health_status"] == "OPTIMO"
    assert q1["rule_15_triggered"] is False
    assert len(q1["alerts"]) == 0

    # Cuadrante 2: Riesgo/Aceleración (CPI >= 1.0, SPI < 1.0)
    q2 = calculate_cpi_spi_quadrant(
        cpi=1.08, spi=0.92, spi_t=0.90, cr=0.99, physical_pct=40.0, financial_pct=38.0, tcpi_bac=1.05
    )
    assert q2["quadrant_number"] == 2
    assert q2["health_status"] == "RIESGO"
    assert q2["badge_color"] == "warning"

    # Cuadrante 3: Crítico (CPI < 1.0, SPI < 1.0) con violación de la Regla del 15%
    q3 = calculate_cpi_spi_quadrant(
        cpi=0.82, spi=0.80, spi_t=0.79, cr=0.66, physical_pct=30.0, financial_pct=48.0, tcpi_bac=1.35
    )
    assert q3["quadrant_number"] == 3
    assert q3["health_status"] == "CRITICO"
    assert q3["rule_15_triggered"] is True
    # Debe disparar alertas críticas de CPI < 0.85, SPI < 0.85, SPI(t) < 0.85 y CR < 0.80
    critical_alerts = [a for a in q3["alerts"] if a["level"] == "critical"]
    assert len(critical_alerts) >= 3

    # Cuadrante 4: Atención / Falso Ahorro (CPI < 1.0, SPI >= 1.0)
    q4 = calculate_cpi_spi_quadrant(
        cpi=0.88, spi=1.15, spi_t=1.10, cr=1.01, physical_pct=60.0, financial_pct=70.0, tcpi_bac=1.20
    )
    assert q4["quadrant_number"] == 4
    assert q4["health_status"] == "ATENCION"
    assert q4["badge_color"] == "accent"


def test_build_project_wbs_tree_hierarchy_and_coding():
    """Valida la construcción recursiva del Organigrama WBS y la codificación automática."""
    proj_id = uuid.uuid4()
    project = MagicMock(spec=models.Project)
    project.id = proj_id
    project.name = "Plataforma Educativa"
    project.status = "in_progress"
    project.budget_allocated = 100000.0

    # 2 Componentes
    comp1 = MagicMock(spec=models.ProjectComponent)
    comp1.id = uuid.uuid4()
    comp1.name = "Infraestructura Cloud"
    comp1.order_index = 1
    comp1.status = "active"
    comp1.budget_allocated = 40000.0
    comp1.deleted_at = None

    comp2 = MagicMock(spec=models.ProjectComponent)
    comp2.id = uuid.uuid4()
    comp2.name = "Desarrollo Frontend"
    comp2.order_index = 2
    comp2.status = "active"
    comp2.budget_allocated = 60000.0
    comp2.deleted_at = None

    # Tareas bajo comp1:
    # Task 1.1 (padre) -> Subtask 1.1.1 (hija)
    t1_1_id = uuid.uuid4()
    t1_1 = MagicMock(spec=models.ProjectTask)
    t1_1.id = t1_1_id
    t1_1.project_id = proj_id
    t1_1.component_id = comp1.id
    t1_1.parent_id = None
    t1_1.title = "Provisionar Servidores"
    t1_1.status = "in_progress"
    t1_1.order_index = 1
    t1_1.physical_progress_pct = 50.0
    t1_1.estimated_hours = 20.0
    t1_1.deleted_at = None

    t1_1_1 = MagicMock(spec=models.ProjectTask)
    t1_1_1.id = uuid.uuid4()
    t1_1_1.project_id = proj_id
    t1_1_1.component_id = comp1.id
    t1_1_1.parent_id = t1_1_id
    t1_1_1.title = "Configurar VPC y Subnets"
    t1_1_1.status = "completed"
    t1_1_1.order_index = 1
    t1_1_1.physical_progress_pct = 100.0
    t1_1_1.estimated_hours = 10.0
    t1_1_1.deleted_at = None

    db = MagicMock()

    def query_mock(arg):
        q = MagicMock()
        if arg is models.ProjectComponent or getattr(arg, "class_", None) is models.ProjectComponent:
            q.filter.return_value.order_by.return_value.all.return_value = [comp1, comp2]
            return q
        if arg is models.ProjectTask or getattr(arg, "class_", None) is models.ProjectTask:
            q.filter.return_value.order_by.return_value.all.return_value = [t1_1, t1_1_1]
            q.filter.return_value.all.return_value = [t1_1, t1_1_1]
            return q
        if arg is models.ProjectTimeLog or getattr(arg, "class_", None) is models.ProjectTimeLog:
            q.filter.return_value.all.return_value = []
            return q
        if arg is models.ProjectExpense or getattr(arg, "class_", None) is models.ProjectExpense:
            q.filter.return_value.all.return_value = []
            return q
        q.filter.return_value.all.return_value = []
        return q

    db.query.side_effect = query_mock

    # Mock de calculate_task_rollup y calculate_component_evm para pruebas unitarias aisladas
    mock_rollup_parent = {
        "time": {"total_estimated_hours": 30.0, "actual_hours": 15.0},
        "progress": {"rolled_up_progress_pct": 75.0},
        "cost": {"total_cost": 5000.0},
    }
    mock_rollup_child = {
        "time": {"total_estimated_hours": 10.0, "actual_hours": 8.0},
        "progress": {"rolled_up_progress_pct": 100.0},
        "cost": {"total_cost": 2000.0},
    }

    def rollup_side_effect(s_db, task):
        if task.id == t1_1_id:
            return mock_rollup_parent
        return mock_rollup_child

    with patch("backend.services.project_evm_service.calculate_task_rollup", side_effect=rollup_side_effect), \
         patch("backend.services.project_evm_service.calculate_component_evm", return_value={"physical_progress_pct": 75.0, "ac": 5000.0, "health_status": "OPTIMO"}), \
         patch("backend.services.project_evm_service.calculate_project_evm", return_value={"progress_percentage": 50.0, "ac": 5000.0, "health_status": "OPTIMO"}):

        tree = build_project_wbs_tree(db, project)

    assert tree["project_id"] == str(proj_id)
    assert tree["project_title"] == "Plataforma Educativa"
    assert tree["root"]["type"] == "project"
    assert tree["root"]["wbs_code"] == "0"
    assert len(tree["root"]["children"]) == 2  # 2 componentes

    # Verificar codificación WBS del componente 1
    c1_node = tree["root"]["children"][0]
    assert c1_node["wbs_code"] == "1"
    assert c1_node["type"] == "component"
    assert len(c1_node["children"]) == 1

    # Verificar codificación de la tarea raíz 1.1
    t1_node = c1_node["children"][0]
    assert t1_node["wbs_code"] == "1.1"
    assert t1_node["type"] == "task"
    assert len(t1_node["children"]) == 1

    # Verificar codificación de la subtarea 1.1.1
    sub_node = t1_node["children"][0]
    assert sub_node["wbs_code"] == "1.1.1"
    assert sub_node["type"] == "task"
    assert sub_node["is_leaf"] is True


def test_pydantic_schemas_evm_advanced_and_wbs():
    """Valida la instanciación e integridad de los esquemas Pydantic para Fase 4."""
    es = schemas.EarnedScheduleMetrics(
        planned_duration_days=90.0,
        actual_time_days=45.0,
        earned_schedule_days=50.0,
        schedule_variance_time_days=5.0,
        schedule_performance_index_time=1.11,
        estimated_duration_at_completion_days=81.1,
        time_variance_at_completion_days=8.9,
        projected_finish_date="2026-11-15",
    )
    assert es.schedule_performance_index_time == 1.11

    eac_mod = schemas.EACForecastModel(
        model_key="typical",
        title="Pronóstico Típico",
        description="Tendencia de costos CPI",
        formula="EAC = AC + (BAC - EV)/CPI",
        eac=120000.0,
        etc=70000.0,
        vac=-20000.0,
        vac_percentage=-20.0,
    )
    assert eac_mod.eac == 120000.0

    tcpi = schemas.TCPIMetrics(
        tcpi_bac=1.05,
        tcpi_eac=0.95,
        is_budget_depleted=False,
        difficulty_level="moderate",
        explanation="Exige control riguroso",
    )
    assert tcpi.difficulty_level == "moderate"

    alert = schemas.EarlyWarningAlert(
        metric="cpi",
        level="critical",
        title="Sobrecosto Crítico",
        detail="CPI < 0.85",
        threshold="CPI < 0.85",
        current_value=0.81,
    )
    assert alert.level == "critical"

    quad = schemas.CPIversusSPIQuadrant(
        quadrant_id="quadrant_1",
        quadrant_number=1,
        name="Zona Óptima",
        health_status="OPTIMO",
        badge_color="success",
        description="Excelente desempeño",
        action_recommendation="Mantener supervisión",
        cpi=1.15,
        spi=1.10,
        point_x_pct=65.0,
        point_y_pct=35.0,
        rule_15_triggered=False,
        alerts=[],
    )
    assert quad.health_status == "OPTIMO"


def test_calculate_project_evm_advanced_integration():
    """Valida el cálculo integral de EVM Avanzado consolidando cuadrantes, pronósticos y tiempo ganado."""
    proj_id = uuid.uuid4()
    project = MagicMock(spec=models.Project)
    project.id = proj_id
    project.budget_allocated = 100000.0
    now = _utcnow()
    project.start_date = now - timedelta(days=30)
    project.created_at = project.start_date
    project.target_date = now + timedelta(days=70)

    db = MagicMock()

    mock_std_evm = {
        "project_id": str(proj_id),
        "calculated_at": now.isoformat(),
        "bac": 100000.0,
        "ac": 45000.0,
        "ev": 50000.0,
        "pv": 48000.0,
        "progress_percentage": 50.0,
        "financial_percentage": 45.0,
        "cpi": 1.11,
        "spi": 1.04,
        "cv": 5000.0,
        "sv": 2000.0,
        "cr": 1.15,
        "eac": 90090.0,
        "vac": 9910.0,
        "health_status": "OPTIMO",
        "health_color": "success",
        "recommendations": ["Buen desempeño."],
    }

    with patch("backend.services.project_evm_service.calculate_project_evm", return_value=mock_std_evm):
        res = calculate_project_evm_advanced(db, project, now=now)

    assert res["project_id"] == str(proj_id)
    assert res["standard_evm"]["cpi"] == 1.11
    assert res["earned_schedule"]["schedule_performance_index_time"] > 0
    assert "typical" in res["forecast_models"]
    assert "atypical" in res["forecast_models"]
    assert "composite" in res["forecast_models"]
    assert res["quadrant"]["quadrant_number"] == 1
    assert res["tcpi"]["is_budget_depleted"] is False


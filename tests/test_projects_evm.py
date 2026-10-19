"""Pruebas unitarias para la suite de Gestión del Valor Ganado (EVM)
y cálculo del Índice de Desempeño del Costo (CPI) y Cronograma (SPI).

Verifica:
1. Fórmulas canónicas de EVM (BAC, EV, PV, AC).
2. Cálculo exacto de CPI (físico vs financiero) y SPI (cronograma).
3. Variación de costo (CV) y proyección al cierre (EAC, VAC).
4. Casos de borde defensivos (AC = 0, BAC = 0, sin tareas).
5. Generación de series de la Curva S físico-financiera.
"""

from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone
from unittest.mock import MagicMock

try:
    import pytest
except ImportError:
    pytest = None

from backend.services.project_evm_service import (
    ProjectEVMService,
    analyze_s_curve_velocity,
    calculate_project_evm,
    evaluate_contingency_reserve_burn_alignment,
    generate_curve_s_data,
    predict_schedule_slippage_days,
)


def _mock_project(
    budget_allocated: float = 100000.0,
    budget_spent: float = 50000.0,
    manual_progress: float = 50.0,
    progress_mode: str = "manual",
    start_days_ago: int = 30,
    target_days_ahead: int = 30,
):
    now = datetime.datetime.now(timezone.utc)
    proj = MagicMock()
    proj.id = uuid.uuid4()
    proj.budget_allocated = budget_allocated
    proj.budget_spent = budget_spent
    proj.manual_progress = manual_progress
    proj.progress_mode = progress_mode
    proj.start_date = now - timedelta(days=start_days_ago)
    proj.target_date = now + timedelta(days=target_days_ahead)
    proj.created_at = proj.start_date
    return proj


def test_evm_balanced_project():
    """Proyecto en equilibrio: avance físico 50%, gasto 50% -> CPI = 1.0."""
    db = MagicMock()
    db.query().filter().all.return_value = []  # Sin gastos detallados en tabla, usa budget_spent

    proj = _mock_project(budget_allocated=100000.0, budget_spent=50000.0, manual_progress=50.0)
    evm = calculate_project_evm(db, proj)

    assert evm["bac"] == 100000.0
    assert evm["ac"] == 50000.0
    assert evm["ev"] == 50000.0
    assert evm["progress_percentage"] == 50.0
    assert evm["financial_percentage"] == 50.0
    assert evm["cpi"] == 1.0
    assert evm["cv"] == 0.0
    assert evm["eac"] == 100000.0
    assert evm["vac"] == 0.0


def test_evm_cost_overrun_critical():
    """Proyecto con sobrecosto grave: avance físico 20%, gasto 60% -> CPI = 0.33."""
    db = MagicMock()
    db.query().filter().all.return_value = []

    proj = _mock_project(budget_allocated=100000.0, budget_spent=60000.0, manual_progress=20.0)
    evm = calculate_project_evm(db, proj)

    assert evm["bac"] == 100000.0
    assert evm["ac"] == 60000.0
    assert evm["ev"] == 20000.0
    assert evm["cpi"] == 0.33
    assert evm["cv"] == -40000.0  # Pérdida de 40k a la fecha
    assert evm["eac"] > 100000.0  # El costo final proyectado se dispara
    assert evm["health_color"] in ("warning", "destructive")
    assert len(evm["recommendations"]) > 0


def test_evm_cost_efficient():
    """Proyecto eficiente: avance físico 80%, gasto 50% -> CPI = 1.6."""
    db = MagicMock()
    db.query().filter().all.return_value = []

    proj = _mock_project(budget_allocated=100000.0, budget_spent=50000.0, manual_progress=80.0)
    evm = calculate_project_evm(db, proj)

    assert evm["bac"] == 100000.0
    assert evm["ac"] == 50000.0
    assert evm["ev"] == 80000.0
    assert evm["cpi"] == 1.6
    assert evm["cv"] == 30000.0  # Superávit de 30k
    assert evm["eac"] < 100000.0  # Ahorro proyectado al cierre
    assert evm["vac"] > 0.0


def test_evm_zero_cost_edge_case():
    """Proyecto recién iniciado: sin gastos (AC = 0) -> Manejo seguro sin ZeroDivisionError."""
    db = MagicMock()
    db.query().filter().all.return_value = []

    proj = _mock_project(budget_allocated=50000.0, budget_spent=0.0, manual_progress=0.0)
    evm = calculate_project_evm(db, proj)

    assert evm["bac"] == 50000.0
    assert evm["ac"] == 0.0
    assert evm["ev"] == 0.0
    assert evm["cpi"] == 1.0
    assert evm["cv"] == 0.0
    assert evm["eac"] == 50000.0


def test_curve_s_generation():
    """Verifica que generate_curve_s_data retorne la serie temporal de PV, EV y AC."""
    db = MagicMock()
    db.query().filter().all.return_value = []
    db.query().filter().order_by().all.return_value = []

    proj = _mock_project(budget_allocated=100000.0, budget_spent=40000.0, manual_progress=40.0)
    points = generate_curve_s_data(db, proj, points_count=8)

    assert len(points) == 8
    # El primer punto de PV es 0.0
    assert points[0]["pv"] == 0.0
    # El último punto de PV alcanza el BAC completo (100.000)
    assert points[-1]["pv"] == 100000.0
    # Todos los puntos tienen fecha y etiqueta
    for pt in points:
        assert "date" in pt
        assert "label" in pt
        assert "pv" in pt
        assert "ev" in pt
        assert "ac" in pt


def test_continuous_weighted_rollup_subtasks_activities_components_project(db_session):
    """Verifica tributación continua Subtareas -> Actividades -> Componentes EDT -> Proyecto."""
    from backend import crud, models, schemas
    from backend.services.project_evm_service import (
        build_project_execution_matrix,
        calculate_component_evm,
        calculate_project_evm,
    )
    from tests.conftest import seed_admin

    user, persona, sede = seed_admin(db_session, email="evm-rollup-pro@example.com")

    now = datetime.datetime.now(timezone.utc)
    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto Tributación Continua Pro",
        sede_id=sede.id,
        budget_allocated=100000.0,
        progress_mode="auto_tasks",
        start_date=now - timedelta(days=15),
        target_date=now + timedelta(days=15),
    )
    db_session.add(project)
    db_session.commit()

    # Componente 1 (60% del presupuesto = 60,000) y Componente 2 (40% = 40,000)
    c1 = crud.create_project_component(
        db_session,
        project.id,
        schemas.ProjectComponentCreate(code="EDT-1", name="Infraestructura", budget_allocated=60000.0, order_index=1),
    )
    c2 = crud.create_project_component(
        db_session,
        project.id,
        schemas.ProjectComponentCreate(code="EDT-2", name="Capacitación", budget_allocated=40000.0, order_index=2),
    )

    # Actividad 1 en Componente 1 (en progreso, con 2 subtareas ponderadas por horas)
    act1 = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=c1.id,
        title="Actividad Principal C1",
        status="in_progress",
        estimated_hours=0.0,
    )
    db_session.add(act1)
    db_session.flush()

    # Subtarea 1.1: 30 horas al 100% -> 30h ganadas
    sub1 = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=c1.id,
        parent_id=act1.id,
        title="Subtarea 1.1",
        status="in_progress",
        estimated_hours=30.0,
        physical_progress_pct=100.0,
    )
    # Subtarea 1.2: 10 horas al 20% -> 2h ganadas
    # Avance ponderado de act1 = (30*100 + 10*20) / 40 = 80.0%
    sub2 = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=c1.id,
        parent_id=act1.id,
        title="Subtarea 1.2",
        status="in_progress",
        estimated_hours=10.0,
        physical_progress_pct=20.0,
    )

    # Actividad 2 en Componente 2: hoja directa con 50% de avance físico
    act2 = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=c2.id,
        title="Actividad Principal C2",
        status="in_progress",
        estimated_hours=20.0,
        physical_progress_pct=50.0,
    )
    db_session.add_all([sub1, sub2, act2])
    db_session.commit()

    # 1. Validar EVM de Componente 1: 80% de avance continuo -> EV = 60,000 * 0.80 = 48,000
    comp1_evm = calculate_component_evm(db_session, c1, now=now)
    assert comp1_evm["physical_progress_pct"] == 80.0
    assert comp1_evm["ev"] == 48000.0

    # 2. Validar EVM de Componente 2: 50% de avance continuo -> EV = 40,000 * 0.50 = 20,000
    comp2_evm = calculate_component_evm(db_session, c2, now=now)
    assert comp2_evm["physical_progress_pct"] == 50.0
    assert comp2_evm["ev"] == 20000.0

    # 3. Validar Roll-up al Proyecto: (60k * 80% + 40k * 50%) / 100k = 68.0% -> EV = 68,000
    proj_evm = calculate_project_evm(db_session, project, now=now)
    assert proj_evm["progress_percentage"] == 68.0
    assert proj_evm["ev"] == 68000.0

    # 4. Validar Matriz de Ejecución de 3 Frentes y 6 Familias Pro
    matrix = build_project_execution_matrix(db_session, project, now=now)
    assert matrix["frentes"]["tiempo"]["progress_pct"] == 68.0
    assert matrix["rollup_hierarchy"]["overall_progress_pct"] == 68.0
    assert len(matrix["rollup_hierarchy"]["components"]) == 2
    assert len(matrix["familias_pro"]) == 6
    assert matrix["familias_pro"]["pro_edt_progress"]["current_value"] == 68.0


def test_sync_execution_and_connected_kpis_indicators_endpoints(client, db_session):
    """Verifica sincronización real de KPIs e Indicadores con 3 frentes y 6 familias Pro vía API."""
    from backend import models
    from tests.conftest import auth_headers, seed_admin

    user, persona, sede = seed_admin(db_session, email="kpi-sync-pro@example.com")
    headers = auth_headers(client, email="kpi-sync-pro@example.com")

    now = datetime.datetime.now(timezone.utc)
    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto Sincronización Pro",
        sede_id=sede.id,
        budget_allocated=50000.0,
        progress_mode="auto_tasks",
        start_date=now - timedelta(days=10),
        target_date=now + timedelta(days=10),
    )
    db_session.add(project)
    db_session.commit()

    # Crear componente y actividad al 75%
    comp = models.ProjectComponent(
        id=uuid.uuid4(),
        project_id=project.id,
        code="EDT-A",
        name="Módulo A",
        budget_allocated=50000.0,
        order_index=1,
    )
    db_session.add(comp)
    db_session.flush()

    task = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=comp.id,
        title="Entrega Módulo A",
        status="in_progress",
        estimated_hours=40.0,
        physical_progress_pct=75.0,
    )
    expense = models.ProjectExpense(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=comp.id,
        amount=25000.0,
        status="paid",
    )
    db_session.add_all([task, expense])
    db_session.commit()

    # 1. GET /indicators/execution-matrix
    r_mat = client.get(f"/api/projects/{project.id}/indicators/execution-matrix", headers=headers)
    assert r_mat.status_code == 200, r_mat.text
    mat = r_mat.json()
    assert mat["frentes"]["tiempo"]["progress_pct"] == 75.0
    assert mat["frentes"]["financiero"]["burn_rate_pct"] == 50.0
    assert mat["frentes"]["cruce_evm"]["ev"] == 37500.0
    assert mat["frentes"]["cruce_evm"]["cpi"] == 1.5

    # 2. POST /indicators/sync-execution sembrando 6 familias Pro en Indicadores y KPIs
    r_sync = client.post(
        f"/api/projects/{project.id}/indicators/sync-execution",
        json={"seed_pro_indicators": True, "seed_pro_kpis": True, "record_period": "2026-M10"},
        headers=headers,
    )
    assert r_sync.status_code == 200, r_sync.text
    sync_data = r_sync.json()
    assert sync_data["seeded_indicators"] >= 6
    assert sync_data["seeded_kpis"] == 6
    assert sync_data["synced_indicators"] >= 6
    assert sync_data["synced_kpis"] == 6

    # 3. Verificar que GET /kpis devuelve los KPIs con source_type, frente y current_value real
    r_kpis = client.get(f"/api/projects/{project.id}/kpis", headers=headers)
    assert r_kpis.status_code == 200
    kpis = r_kpis.json()
    edt_kpi = next(k for k in kpis if k["source_type"] == "pro_edt_progress")
    assert edt_kpi["current_value"] == 75.0
    assert edt_kpi["frente"] == "tiempo"
    assert edt_kpi["is_auto_synced"] is True

    # 4. Crear un KPI conectado específicamente al componente EDT
    r_new_kpi = client.post(
        f"/api/projects/{project.id}/kpis",
        json={
            "title": "Avance Módulo A",
            "target_value": 100.0,
            "current_value": 0.0,
            "unit": "%",
            "category": "operational",
            "source_type": "tasks_completion_pct",
            "component_id": str(comp.id),
        },
        headers=headers,
    )
    assert r_new_kpi.status_code == 201, r_new_kpi.text
    created_kpi = r_new_kpi.json()
    assert created_kpi["current_value"] == 75.0
    assert created_kpi["component_id"] == str(comp.id)
    assert "EDT-A" in (created_kpi["component_name"] or "")

    # 5. Verificar que GET /export/executive-data y GET /export/summary-pdf incluyen execution_matrix, kpis, indicators y roll-up continuo (75%)
    r_exec_report = client.get(f"/api/projects/{project.id}/export/executive-data", headers=headers)
    assert r_exec_report.status_code == 200, r_exec_report.text
    exec_report = r_exec_report.json()
    assert exec_report["project"]["progress_percentage"] == 75.0
    assert exec_report["execution_matrix"]["frentes"]["tiempo"]["progress_pct"] == 75.0
    assert len(exec_report["kpis"]) >= 7
    assert len(exec_report["indicators"]) >= 6

    r_pdf = client.get(f"/api/projects/{project.id}/export/summary-pdf", headers=headers)
    assert r_pdf.status_code == 200
    assert r_pdf.content.startswith(b"%PDF")

    # 6. Verificar que GET /evm/curve-s incluye execution_matrix para ProjectEVMDrawer
    r_curve = client.get(f"/api/projects/{project.id}/evm/curve-s?points=8", headers=headers)
    assert r_curve.status_code == 200, r_curve.text
    curve_json = r_curve.json()
    assert curve_json["summary"]["progress_percentage"] == 75.0
    assert curve_json["execution_matrix"]["rollup_hierarchy"]["overall_progress_pct"] == 75.0


def test_six_submodules_connected_to_real_execution(client, db_session):
    """Verifica la conexión en tiempo real de los 6 submódulos:
    1) Automatizaciones (task_completed, milestone_completed, expense_approved)
    2) Suministros -> ProjectExpense (AC de tarea, componente y proyecto)
    3) Línea Base -> EVM y Curva S (baseline_bac, baseline_pv, varianzas)
    4) TimeTracking -> actual_hours, physical_progress_pct y roll-up EDT al padre
    5) Workload -> horas estimadas, horas reales registradas y % utilización
    6) Ruta Crítica CPM -> exclusión de padres contenedores EDT y lag_days
    """
    from backend import models
    from tests.conftest import auth_headers, seed_admin

    user, persona, sede = seed_admin(db_session, email="submodules-pro@example.com")
    headers = auth_headers(client, email="submodules-pro@example.com")
    now = datetime.datetime.now(timezone.utc)

    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto 6 Submódulos Conectados",
        sede_id=sede.id,
        owner_id=persona.id,
        budget_allocated=100000.0,
        progress_mode="auto_tasks",
        start_date=now - timedelta(days=15),
        target_date=now + timedelta(days=15),
    )
    db_session.add(project)
    db_session.flush()

    comp = models.ProjectComponent(
        id=uuid.uuid4(),
        project_id=project.id,
        code="COMP-1",
        name="Infraestructura",
        budget_allocated=100000.0,
        order_index=1,
    )
    db_session.add(comp)
    db_session.commit()

    # ── 1. Automatizaciones: crear reglas activas ───────────────────────────
    r_rule_task = client.post(
        f"/api/projects/{project.id}/automations",
        json={
            "name": "Auto Seguimiento al Completar",
            "trigger_event": "task_completed",
            "condition_data": {},
            "action_type": "create_followup_task",
            "action_data": {
                "title": "Verificación QA Automática",
                "priority": "high",
                "duration_days": 3,
            },
            "is_active": True,
        },
        headers=headers,
    )
    assert r_rule_task.status_code == 201, r_rule_task.text
    rule_task_id = r_rule_task.json()["id"]

    r_rule_ms = client.post(
        f"/api/projects/{project.id}/automations",
        json={
            "name": "Notificar al Completar Hito",
            "trigger_event": "milestone_completed",
            "condition_data": {},
            "action_type": "notify_assignee",
            "action_data": {},
            "is_active": True,
        },
        headers=headers,
    )
    assert r_rule_ms.status_code == 201, r_rule_ms.text
    rule_ms_id = r_rule_ms.json()["id"]

    r_rule_exp = client.post(
        f"/api/projects/{project.id}/automations",
        json={
            "name": "Notificar Gasto Pagado",
            "trigger_event": "expense_approved",
            "condition_data": {},
            "action_type": "notify_assignee",
            "action_data": {},
            "is_active": True,
        },
        headers=headers,
    )
    assert r_rule_exp.status_code == 201, r_rule_exp.text
    rule_exp_id = r_rule_exp.json()["id"]

    # Crear actividad padre y dos subtareas hoja
    parent_task = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=comp.id,
        title="Actividad Contenedora Padre",
        status="todo",
        assignee_id=persona.id,
        estimated_hours=20.0,
        start_date=now - timedelta(days=10),
        due_date=now + timedelta(days=5),
    )
    db_session.add(parent_task)
    db_session.flush()

    leaf_1 = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=comp.id,
        parent_id=parent_task.id,
        title="Subtarea Hoja 1 (Diseño)",
        status="todo",
        assignee_id=persona.id,
        estimated_hours=10.0,
        start_date=now - timedelta(days=10),
        due_date=now - timedelta(days=6),  # 5 días de duración
    )
    leaf_2 = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=comp.id,
        parent_id=parent_task.id,
        title="Subtarea Hoja 2 (Implementación)",
        status="todo",
        assignee_id=persona.id,
        estimated_hours=10.0,
        start_date=now - timedelta(days=5),
        due_date=now - timedelta(days=2),  # 4 días de duración
    )
    db_session.add_all([leaf_1, leaf_2])
    db_session.commit()

    # ── 2. TimeTracking -> actual_hours, avance físico de tarea y roll-up al padre ──
    r_log = client.post(
        f"/api/projects/{project.id}/time-logs",
        json={
            "task_id": str(leaf_2.id),
            "hours": 5.0,
            "description": "Desarrollo backend 5h de 10h",
            "is_billable": True,
        },
        headers=headers,
    )
    assert r_log.status_code == 201, r_log.text

    db_session.expire_all()
    refreshed_leaf_2 = db_session.query(models.ProjectTask).filter_by(id=leaf_2.id).first()
    refreshed_parent = db_session.query(models.ProjectTask).filter_by(id=parent_task.id).first()
    assert refreshed_leaf_2.actual_hours == 5.0
    assert refreshed_leaf_2.physical_progress_pct == 50.0
    assert refreshed_leaf_2.status == "in_progress"
    # Padre tiene 2 subtareas de 10h cada una (0% y 50% -> 25% ponderado)
    assert refreshed_parent.physical_progress_pct == 25.0

    # ── 3. Suministros -> Costo Real AC (ProjectExpense + budget_spent + EVM) ──
    r_sup = client.post(
        f"/api/projects/{project.id}/tasks/{leaf_1.id}/supplies",
        json={
            "item_name": "Servidores Dedicados",
            "quantity": 2,
            "unit_cost": 4000.0,
            "status": "ready",
        },
        headers=headers,
    )
    assert r_sup.status_code == 201, r_sup.text
    sup_json = r_sup.json()
    assert sup_json["unit_cost"] == 4000.0
    assert sup_json["total_cost"] == 8000.0
    assert sup_json["expense_id"] is not None

    db_session.expire_all()
    refreshed_proj = db_session.query(models.Project).filter_by(id=project.id).first()
    assert float(refreshed_proj.budget_spent) == 8000.0
    assert float(leaf_1.actual_cost) == 8000.0
    # Regla de expense_approved disparada automáticamente por el suministro pagado
    rule_exp_db = db_session.query(models.ProjectAutomationRule).filter_by(id=uuid.UUID(rule_exp_id)).first()
    assert (rule_exp_db.execution_count or 0) >= 1

    # ── 4. Línea Base Conectada a EVM y Curva S ─────────────────────────────
    r_base = client.post(
        f"/api/projects/{project.id}/baselines",
        json={"name": "Línea Base Oficial v1", "description": "Congelamiento inicial"},
        headers=headers,
    )
    assert r_base.status_code == 201, r_base.text
    base_json = r_base.json()
    assert base_json["snapshot_data"]["bac"] == 100000.0
    assert "evm" in base_json["snapshot_data"]

    # Modificar el BAC del proyecto a 120000 para verificar comparación contra baseline_bac (100000)
    refreshed_proj.budget_allocated = 120000.0
    db_session.commit()

    r_curve = client.get(f"/api/projects/{project.id}/evm/curve-s?points=6", headers=headers)
    assert r_curve.status_code == 200, r_curve.text
    curve_data = r_curve.json()
    assert curve_data["summary"]["has_baseline"] is True
    assert curve_data["summary"]["baseline_name"] == "Línea Base Oficial v1"
    assert curve_data["summary"]["baseline_bac"] == 100000.0
    assert curve_data["summary"]["baseline_variance_cost"] == 92000.0  # 100000 - 8000 AC
    assert curve_data["points"][-1]["pv"] == 120000.0
    assert curve_data["points"][-1]["baseline_pv"] == 100000.0

    # ── 5. Workload Ponderado por Horas ─────────────────────────────────────
    r_wl = client.get(f"/api/projects/{project.id}/workload", headers=headers)
    assert r_wl.status_code == 200, r_wl.text
    wl_data = r_wl.json()
    # Las 2 subtareas hoja suman 20h estimadas (sin duplicar las 20h del padre contenedor)
    assert wl_data["total_estimated_hours"] == 20.0
    assert wl_data["total_actual_hours"] == 5.0
    member_entry = next(m for m in wl_data["members"] if m["persona_id"] == str(persona.id))
    assert member_entry["estimated_hours_total"] == 20.0
    assert member_entry["actual_hours_logged"] == 5.0
    assert member_entry["hours_utilization_pct"] == 25.0

    # ── 6. CPM Consciente de EDT y lag_days ─────────────────────────────────
    r_dep = client.post(
        f"/api/projects/{project.id}/dependencies",
        json={
            "predecessor_id": str(leaf_1.id),
            "successor_id": str(leaf_2.id),
            "dependency_type": "FS",
            "lag_days": 3,
        },
        headers=headers,
    )
    assert r_dep.status_code == 201, r_dep.text

    r_cpm = client.get(f"/api/projects/{project.id}/critical-path", headers=headers)
    assert r_cpm.status_code == 200, r_cpm.text
    cpm_data = r_cpm.json()
    assert cpm_data["excluded_parent_tasks_count"] >= 1
    assert cpm_data["total_lag_days"] == 3
    cpm_task_ids = [t["task_id"] for t in cpm_data["tasks"]]
    assert str(parent_task.id) not in cpm_task_ids
    leaf2_cpm = next(t for t in cpm_data["tasks"] if t["task_id"] == str(leaf_2.id))
    assert leaf2_cpm["lag_days"] == 3
    # Duración total = 5 días (leaf_1) + 3 días (lag) + 4 días (leaf_2) = 12 días
    assert cpm_data["total_duration_days"] == 12

    # ── Disparar automatización de tarea completada y de hito completado en tiempo real ──
    r_done = client.patch(
        f"/api/projects/{project.id}/tasks/{leaf_1.id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert r_done.status_code == 200, r_done.text

    db_session.expire_all()
    rule_task_db = db_session.query(models.ProjectAutomationRule).filter_by(id=uuid.UUID(rule_task_id)).first()
    assert (rule_task_db.execution_count or 0) == 1
    followup = (
        db_session.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == project.id,
            models.ProjectTask.title == "Verificación QA Automática",
        )
        .first()
    )
    assert followup is not None

    r_ms = client.post(
        f"/api/projects/{project.id}/milestones",
        json={"title": "Hito Entrega Fase 1", "is_completed": False},
        headers=headers,
    )
    assert r_ms.status_code == 201, r_ms.text
    ms_id = r_ms.json()["id"]

    r_ms_done = client.patch(
        f"/api/projects/{project.id}/milestones/{ms_id}",
        json={"is_completed": True},
        headers=headers,
    )
    assert r_ms_done.status_code == 200, r_ms_done.text
    db_session.expire_all()
    rule_ms_db = db_session.query(models.ProjectAutomationRule).filter_by(id=uuid.UUID(rule_ms_id)).first()
    assert (rule_ms_db.execution_count or 0) == 1


def test_pmi_vol5_vol6_emv_reserves_cpi_stability_and_sentinel(client, db_session):
    """
    Verifica la Doctrina PMI Vol. 5 y Vol. 6:
    1) Valor Monetario Esperado (EMV) y tipología threat/opportunity en Matriz de Riesgos.
    2) Estructura Canónica de Reservas (work_packages_budget + contingency_reserve = BAC + management_reserve = total_project_budget).
    3) Regla del 15% de Estabilidad del CPI (banda ±10% e irrecuperabilidad sin re-baseline cuando CPI < 0.90 y avance >= 15%).
    4) Early Warning Sentinel en los 4 niveles canónicos (normal, attention, high_risk, critical).
    """
    from backend import models
    from backend.services.project_evm_service import (
        ProjectEVMService,
        calculate_cpi_stability_rule,
        calculate_early_warning_sentinel,
    )
    from tests.conftest import auth_headers, seed_admin

    user, persona, sede = seed_admin(db_session, email="pmi-vol5-vol6@example.com")
    headers = auth_headers(client, email="pmi-vol5-vol6@example.com")
    now = datetime.datetime.now(timezone.utc)

    project = models.Project(
        id=uuid.uuid4(),
        sede_id=sede.id,
        owner_id=persona.id,
        title="Proyecto Doctrina PMI Vol 5 y 6",
        status="in_progress",
        budget_allocated=100000.0,
        budget_spent=35000.0,
        progress_mode="manual",
        manual_progress=25.0,
        start_date=now - timedelta(days=20),
        target_date=now + timedelta(days=20),
    )
    db_session.add(project)
    db_session.commit()

    # 1. Crear riesgo de Amenaza (threat): prob 60%, impacto $10,000 -> EMV = +$6,000
    r_threat = client.post(
        f"/api/projects/{project.id}/risks",
        json={
            "title": "Alza en acero estructural",
            "category": "financial",
            "risk_type": "threat",
            "probability": 3,
            "probability_pct": 60.0,
            "impact": 4,
            "financial_impact": 10000.0,
            "mitigation_plan": "Contrato de precio fijo con proveedor",
            "status": "active",
        },
        headers=headers,
    )
    assert r_threat.status_code == 201, r_threat.text
    threat_data = r_threat.json()
    assert threat_data["risk_type"] == "threat"
    assert threat_data["probability_pct"] == 60.0
    assert threat_data["financial_impact"] == 10000.0
    assert threat_data["emv"] == 6000.0

    # 2. Crear riesgo de Oportunidad (opportunity): prob 50%, impacto $4,000 -> EMV = -$2,000 (ahorro esperado)
    r_opp = client.post(
        f"/api/projects/{project.id}/risks",
        json={
            "title": "Descuento por compra anticipada de luminarias",
            "category": "financial",
            "risk_type": "opportunity",
            "probability": 3,
            "probability_pct": 50.0,
            "impact": 3,
            "financial_impact": 4000.0,
            "mitigation_plan": "Adelantar orden de compra",
            "status": "active",
        },
        headers=headers,
    )
    assert r_opp.status_code == 201, r_opp.text
    opp_data = r_opp.json()
    assert opp_data["risk_type"] == "opportunity"
    assert opp_data["probability_pct"] == 50.0
    assert opp_data["financial_impact"] == 4000.0
    assert opp_data["emv"] == -2000.0

    # 3. Verificar resumen de Matriz de Riesgos (/risks-summary)
    r_summary = client.get(f"/api/projects/{project.id}/risks-summary", headers=headers)
    assert r_summary.status_code == 200, r_summary.text
    summary_data = r_summary.json()
    assert summary_data["threats_count"] == 1
    assert summary_data["opportunities_count"] == 1
    assert summary_data["threats_emv"] == 6000.0
    assert summary_data["required_contingency_reserve"] == 6000.0
    assert summary_data["opportunities_emv"] == -2000.0
    assert summary_data["total_emv"] == 4000.0

    # 4. Verificar Estructura Canónica de Reservas, Regla del 15% de CPI y Sentinel en /budget-summary y ProjectEVMService
    r_budget = client.get(f"/api/projects/{project.id}/budget-summary", headers=headers)
    assert r_budget.status_code == 200, r_budget.text
    budget_data = r_budget.json()
    # BAC = 100,000; Reserva Contingencia EMV = 6,000 -> Paquetes de Trabajo = 94,000
    # Reserva de Gestión (10%) = 10,000 -> Presupuesto Total = 110,000
    assert budget_data["work_packages_budget"] == 94000.0
    assert budget_data["contingency_reserve"] == 6000.0
    assert budget_data["management_reserve"] == 10000.0
    assert budget_data["total_project_budget"] == 110000.0
    # Con avance = 25% (>= 15%), EV = 25,000 y AC = 35,000 -> CPI = 0.71 (< 0.90)
    assert budget_data["cpi_stability_rule"]["is_applicable"] is True
    assert budget_data["cpi_stability_rule"]["is_irrecoverable_without_rebaseline"] is True
    assert budget_data["early_warning_sentinel"]["level"] in ("critical", "high_risk")

    # 5. Verificar ProjectEVMService.calculate_project_metrics directamente y niveles del Sentinel
    evm_metrics = ProjectEVMService.calculate_project_metrics(project, db=db_session)
    assert evm_metrics["work_packages_budget"] == 94000.0
    assert evm_metrics["contingency_reserve"] == 6000.0
    assert evm_metrics["management_reserve"] == 10000.0
    assert evm_metrics["total_project_budget"] == 110000.0
    assert evm_metrics["cpi_stability_rule"]["is_applicable"] is True
    assert evm_metrics["cpi_stability_rule"]["is_irrecoverable_without_rebaseline"] is True

    # Validar los 4 niveles canónicos de Early Warning Sentinel (Vol. 5 §4)
    s_normal = calculate_early_warning_sentinel(0.98, 1.02)
    assert s_normal["level"] == "normal"

    s_attention = calculate_early_warning_sentinel(0.88, 0.96)
    assert s_attention["level"] == "attention"

    s_high_risk = calculate_early_warning_sentinel(0.80, 0.95)
    assert s_high_risk["level"] == "high_risk"

    s_critical = calculate_early_warning_sentinel(0.72, 0.95)
    assert s_critical["level"] == "critical"

    # Validar Regla del 15% en fase temprana (< 15%) vs fase madura (>= 15%)
    rule_early = calculate_cpi_stability_rule(10.0, 0.80)
    assert rule_early["is_applicable"] is False
    assert rule_early["is_irrecoverable_without_rebaseline"] is False

    rule_mature = calculate_cpi_stability_rule(20.0, 0.85)
    assert rule_mature["is_applicable"] is True
    assert rule_mature["expected_cpi_floor"] == 0.77
    assert rule_mature["expected_cpi_ceiling"] == 0.94
    assert rule_mature["is_irrecoverable_without_rebaseline"] is True


def test_analyze_s_curve_velocity_trends_and_integration():
    """Verifica el analizador de velocidad marginal, punto de inflexión y tendencia de la Curva S (PMBOK §7.4.2.3)."""
    empty_res = analyze_s_curve_velocity([])
    assert empty_res == {
        "points_count": 0,
        "peak_ev_delta": 0.0,
        "peak_ac_delta": 0.0,
        "peak_period_label": None,
        "final_sv": 0.0,
        "final_cv": 0.0,
        "trend_direction": "flat",
    }

    accel_points = [
        {"label": "P1", "pv": 0.0, "ev": 0.0, "ac": 0.0},
        {"label": "P2", "pv": 15000.0, "ev": 10000.0, "ac": 12000.0},
        {"label": "P3", "pv": 40000.0, "ev": 35000.0, "ac": 36000.0},
        {"label": "P4", "pv": 75000.0, "ev": 80000.0, "ac": 78000.0},
    ]
    accel_res = analyze_s_curve_velocity(accel_points)
    assert accel_res["points_count"] == 4
    assert accel_res["trend_direction"] == "accelerating"
    assert accel_res["peak_ev_delta"] == 45000.0
    assert accel_res["peak_ac_delta"] == 42000.0
    assert accel_res["peak_period_label"] == "P4"
    assert accel_res["final_sv"] == 5000.0
    assert accel_res["final_cv"] == 2000.0

    decel_points = [
        {"label": "P1", "pv": 0.0, "ev": 0.0, "ac": 0.0},
        {"label": "P2", "pv": 45000.0, "ev": 50000.0, "ac": 48000.0},
        {"label": "P3", "pv": 70000.0, "ev": 70000.0, "ac": 72000.0},
        {"label": "P4", "pv": 85000.0, "ev": 75000.0, "ac": 80000.0},
    ]
    decel_res = analyze_s_curve_velocity(decel_points)
    assert decel_res["points_count"] == 4
    assert decel_res["trend_direction"] == "decelerating"
    assert decel_res["peak_ev_delta"] == 50000.0
    assert decel_res["peak_period_label"] == "P2"
    assert decel_res["final_sv"] == -10000.0
    assert decel_res["final_cv"] == -5000.0

    db = MagicMock()
    db.query().filter().all.return_value = []
    db.query().filter().order_by().all.return_value = []
    proj = _mock_project(budget_allocated=100000.0, budget_spent=40000.0, manual_progress=40.0)
    generated_points = generate_curve_s_data(db, proj, points_count=8)
    integrated_res = ProjectEVMService.analyze_s_curve_velocity(generated_points)
    assert integrated_res["points_count"] >= 1
    assert integrated_res["peak_ev_delta"] > 0.0
    assert integrated_res["peak_period_label"] is not None
    assert integrated_res["trend_direction"] in {"accelerating", "decelerating", "steady"}


def test_predict_schedule_slippage_days_ahead_or_on_time():
    """Cronograma en tiempo o adelantado (PD=100, SPI(t)=1.25 -> IEAC(t)=80.0, slippage=-20.0, ahead_or_on_time)."""
    res = predict_schedule_slippage_days(100, 1.25)
    assert res == {
        "planned_duration_days": 100.0,
        "ieac_t_days": 80.0,
        "projected_slippage_days": -20.0,
        "slippage_pct": -20.0,
        "schedule_forecast_status": "ahead_or_on_time",
    }

    on_time = ProjectEVMService.predict_schedule_slippage_days(100, 1.0)
    assert on_time["projected_slippage_days"] == 0.0
    assert on_time["schedule_forecast_status"] == "ahead_or_on_time"


def test_predict_schedule_slippage_days_minor_slippage():
    """Deslizamiento menor <= 15% (PD=100, SPI(t)=0.90 -> IEAC(t)=111.11, slippage=11.11, minor_slippage)."""
    res = predict_schedule_slippage_days(100, 0.90)
    assert res == {
        "planned_duration_days": 100.0,
        "ieac_t_days": 111.11,
        "projected_slippage_days": 11.11,
        "slippage_pct": 11.11,
        "schedule_forecast_status": "minor_slippage",
    }


def test_predict_schedule_slippage_days_critical_slippage():
    """Deslizamiento crítico > 15% (PD=100, SPI(t)=0.80 -> IEAC(t)=125.0, slippage=25.0, critical_slippage)."""
    res = ProjectEVMService.predict_schedule_slippage_days(100, 0.80)
    assert res == {
        "planned_duration_days": 100.0,
        "ieac_t_days": 125.0,
        "projected_slippage_days": 25.0,
        "slippage_pct": 25.0,
        "schedule_forecast_status": "critical_slippage",
    }


def test_predict_schedule_slippage_days_unscheduled_and_stalled():
    """Casos borde PD <= 0 ('unscheduled') y SPI(t) <= 0 ('stalled', ieac_t_days=None)."""
    unsched = predict_schedule_slippage_days(0, 1.0)
    assert unsched == {
        "planned_duration_days": 0.0,
        "ieac_t_days": 0.0,
        "projected_slippage_days": 0.0,
        "slippage_pct": 0.0,
        "schedule_forecast_status": "unscheduled",
    }

    stalled = predict_schedule_slippage_days(120, 0.0)
    assert stalled == {
        "planned_duration_days": 120.0,
        "ieac_t_days": None,
        "projected_slippage_days": None,
        "slippage_pct": None,
        "schedule_forecast_status": "stalled",
    }


def test_evaluate_contingency_reserve_burn_alignment_proportional_and_conservative():
    """Valida consumo proporcional (-15% <= burn_variance_pct < 20%) y preservación conservadora (< -15%)."""
    prop = evaluate_contingency_reserve_burn_alignment(
        contingency_allocated=10000.0,
        contingency_consumed=4500.0,
        percent_complete=50.0,
    )
    assert prop == {
        "contingency_allocated": 10000.0,
        "contingency_consumed": 4500.0,
        "remaining_reserve": 5500.0,
        "percent_complete": 50.0,
        "reserve_burn_pct": 45.0,
        "burn_to_progress_ratio": 0.9,
        "burn_variance_pct": -5.0,
        "reserve_alignment_status": "proportional_burn",
    }
    assert (
        ProjectEVMService.evaluate_contingency_reserve_burn_alignment(10000.0, 4500.0, 50.0)
        == prop
    )

    cons = evaluate_contingency_reserve_burn_alignment(
        contingency_allocated=10000.0,
        contingency_consumed=1000.0,
        percent_complete=60.0,
    )
    assert cons["reserve_burn_pct"] == 10.0
    assert cons["burn_variance_pct"] == -50.0
    assert cons["reserve_alignment_status"] == "conservative_preservation"


def test_evaluate_contingency_reserve_burn_alignment_premature_depletion():
    """Valida agotamiento prematuro cuando burn_variance_pct >= 20% sin agotar el 100% de la reserva."""
    res = evaluate_contingency_reserve_burn_alignment(
        contingency_allocated=10000.0,
        contingency_consumed=7000.0,
        percent_complete=35.0,
    )
    assert res == {
        "contingency_allocated": 10000.0,
        "contingency_consumed": 7000.0,
        "remaining_reserve": 3000.0,
        "percent_complete": 35.0,
        "reserve_burn_pct": 70.0,
        "burn_to_progress_ratio": 2.0,
        "burn_variance_pct": 35.0,
        "reserve_alignment_status": "premature_depletion",
    }


def test_evaluate_contingency_reserve_burn_alignment_reserve_exhausted():
    """Valida reserva agotada cuando consumed >= allocated antes de llegar al 100% de avance."""
    res = evaluate_contingency_reserve_burn_alignment(
        contingency_allocated=10000.0,
        contingency_consumed=10500.0,
        percent_complete=60.0,
    )
    assert res["remaining_reserve"] == 0.0
    assert res["reserve_burn_pct"] == 105.0
    assert res["reserve_alignment_status"] == "reserve_exhausted"


def test_evaluate_contingency_reserve_burn_alignment_no_contingency_allocated():
    """Valida estado no_contingency_allocated cuando la reserva asignada es 0."""
    res = evaluate_contingency_reserve_burn_alignment(
        contingency_allocated=0.0,
        contingency_consumed=0.0,
        percent_complete=40.0,
    )
    assert res == {
        "contingency_allocated": 0.0,
        "contingency_consumed": 0.0,
        "remaining_reserve": 0.0,
        "percent_complete": 40.0,
        "reserve_burn_pct": 0.0,
        "burn_to_progress_ratio": 0.0,
        "burn_variance_pct": -40.0,
        "reserve_alignment_status": "no_contingency_allocated",
    }


def test_evaluate_variance_at_completion_alert_on_or_under_budget():
    """Valida ahorro proyectado (VAC >= 0) con estado on_or_under_budget."""
    from backend.services.project_evm_service import evaluate_variance_at_completion_alert

    res = evaluate_variance_at_completion_alert(
        bac=100000.0, eac=92000.0, management_reserve=5000.0
    )
    assert res == {
        "bac": 100000.0,
        "eac": 92000.0,
        "management_reserve": 5000.0,
        "cost_baseline_plus_mr": 105000.0,
        "vac_amount": 8000.0,
        "vac_pct": 8.0,
        "overrun_amount": 0.0,
        "unfunded_overrun": 0.0,
        "is_covered_by_management_reserve": True,
        "vac_alert_status": "on_or_under_budget",
    }
    assert (
        ProjectEVMService.evaluate_variance_at_completion_alert(100000.0, 92000.0, 5000.0)
        == res
    )


def test_evaluate_variance_at_completion_alert_overrun_absorbed_by_mr():
    """Valida sobrecosto proyectado absorbido por la Reserva de Gestión (MR)."""
    from backend.services.project_evm_service import evaluate_variance_at_completion_alert

    res = evaluate_variance_at_completion_alert(
        bac=100000.0, eac=108000.0, management_reserve=10000.0
    )
    assert res["vac_amount"] == -8000.0
    assert res["vac_pct"] == -8.0
    assert res["overrun_amount"] == 8000.0
    assert res["unfunded_overrun"] == 0.0
    assert res["is_covered_by_management_reserve"] is True
    assert res["vac_alert_status"] == "overrun_absorbed_by_mr"


def test_evaluate_variance_at_completion_alert_budget_breach_beyond_mr():
    """Valida sobrecosto proyectado que excede el BAC más la Reserva de Gestión -> budget_breach_beyond_mr."""
    from backend.services.project_evm_service import evaluate_variance_at_completion_alert

    res = evaluate_variance_at_completion_alert(
        bac=100000.0, eac=118000.0, management_reserve=10000.0
    )
    assert res["vac_amount"] == -18000.0
    assert res["overrun_amount"] == 18000.0
    assert res["unfunded_overrun"] == 8000.0
    assert res["is_covered_by_management_reserve"] is False
    assert res["vac_alert_status"] == "budget_breach_beyond_mr"


def test_evaluate_variance_at_completion_alert_unbaselined():
    """Valida proyecto sin BAC (bac=0) -> estado unbaselined y vac_pct=0.0."""
    from backend.services.project_evm_service import evaluate_variance_at_completion_alert

    res = evaluate_variance_at_completion_alert(bac=0.0, eac=5000.0)
    assert res["bac"] == 0.0
    assert res["vac_pct"] == 0.0
    assert res["vac_alert_status"] == "unbaselined"


def test_evaluate_etc_forecasting_method_posture_completed_no_etc():
    """remaining_work == 0.0 (EV >= BAC o BAC == 0) -> 'COMPLETED_NO_ETC'."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_etc_forecasting_method_posture,
    )

    res = evaluate_etc_forecasting_method_posture(
        bac=100000.0, ev=100000.0, ac=95000.0, cpi=1.05, spi=1.0
    )
    assert res == {
        "remaining_work": 0.0,
        "effective_cpi": 1.05,
        "effective_spi": 1.0,
        "etc_atypical": 0.0,
        "etc_typical_cpi": 0.0,
        "etc_composite_cpi_spi": 0.0,
        "recommended_method": "COMPLETED_NO_ETC",
    }
    assert (
        ProjectEVMService.evaluate_etc_forecasting_method_posture(
            100000.0, 100000.0, 95000.0, cpi=1.05, spi=1.0
        )
        == res
    )


def test_evaluate_etc_forecasting_method_posture_composite_cpi_spi():
    """effective_cpi < 0.95 y effective_spi < 0.95 -> 'COMPOSITE_CPI_SPI'."""
    from backend.services.project_evm_service import (
        evaluate_etc_forecasting_method_posture,
    )

    res = evaluate_etc_forecasting_method_posture(
        bac=100000.0, ev=40000.0, ac=50000.0, cpi=0.80, spi=0.75
    )
    assert res == {
        "remaining_work": 60000.0,
        "effective_cpi": 0.8,
        "effective_spi": 0.75,
        "etc_atypical": 60000.0,
        "etc_typical_cpi": 75000.0,
        "etc_composite_cpi_spi": 100000.0,
        "recommended_method": "COMPOSITE_CPI_SPI",
    }


def test_evaluate_etc_forecasting_method_posture_typical_cpi():
    """effective_cpi < 0.95 (derivado de EV/AC cuando cpi=None) y effective_spi >= 0.95 -> 'TYPICAL_CPI'."""
    from backend.services.project_evm_service import (
        evaluate_etc_forecasting_method_posture,
    )

    res = evaluate_etc_forecasting_method_posture(
        bac=100000.0, ev=40000.0, ac=50000.0, cpi=None, spi=1.0
    )
    assert res == {
        "remaining_work": 60000.0,
        "effective_cpi": 0.8,
        "effective_spi": 1.0,
        "etc_atypical": 60000.0,
        "etc_typical_cpi": 75000.0,
        "etc_composite_cpi_spi": 75000.0,
        "recommended_method": "TYPICAL_CPI",
    }


def test_evaluate_etc_forecasting_method_posture_atypical_remaining_budget():
    """effective_cpi >= 0.95 -> 'ATYPICAL_REMAINING_BUDGET'."""
    from backend.services.project_evm_service import (
        evaluate_etc_forecasting_method_posture,
    )

    res = evaluate_etc_forecasting_method_posture(
        bac=100000.0, ev=50000.0, ac=50000.0, cpi=1.0, spi=1.0
    )
    assert res == {
        "remaining_work": 50000.0,
        "effective_cpi": 1.0,
        "effective_spi": 1.0,
        "etc_atypical": 50000.0,
        "etc_typical_cpi": 50000.0,
        "etc_composite_cpi_spi": 50000.0,
        "recommended_method": "ATYPICAL_REMAINING_BUDGET",
    }


# ─── evaluate_earned_schedule_duration_posture (pure helper) ──────────────


def test_earned_schedule_duration_posture_on_track_and_at_risk():
    """SPI(t) >= 0.95 -> ON_TRACK_DURATION; SPI(t) en [0.80, 0.95) -> AT_RISK_DURATION_SLIP."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_duration_posture,
    )

    on_track = evaluate_earned_schedule_duration_posture(100, 50, 60)
    assert on_track["earned_schedule_days"] == 60.0
    assert on_track["schedule_variance_days"] == 10.0
    assert on_track["spi_time"] == 1.2
    assert on_track["estimated_total_duration_days"] == 83.33
    assert on_track["posture"] == "ON_TRACK_DURATION"

    at_risk = evaluate_earned_schedule_duration_posture(100, 50, 45)
    assert at_risk["schedule_variance_days"] == -5.0
    assert at_risk["spi_time"] == 0.9
    assert at_risk["estimated_total_duration_days"] == 111.11
    assert at_risk["posture"] == "AT_RISK_DURATION_SLIP"


def test_earned_schedule_duration_posture_critical_delay():
    """SPI(t) < 0.80 -> CRITICAL_SCHEDULE_DELAY con EDAC inflado."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_duration_posture,
    )

    res = evaluate_earned_schedule_duration_posture(100, 50, 30)
    assert res["earned_schedule_days"] == 30.0
    assert res["schedule_variance_days"] == -20.0
    assert res["spi_time"] == 0.6
    assert res["estimated_total_duration_days"] == 166.67
    assert res["posture"] == "CRITICAL_SCHEDULE_DELAY"


def test_earned_schedule_duration_posture_completed_on_or_ahead_and_late():
    """Progreso >= 100%: dentro del plazo -> COMPLETED_ON_OR_AHEAD; excedido -> COMPLETED_LATE."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_duration_posture,
    )

    on_or_ahead = evaluate_earned_schedule_duration_posture(100, 80, 100)
    assert on_or_ahead["earned_schedule_days"] == 100.0
    assert on_or_ahead["spi_time"] == 1.25
    assert on_or_ahead["posture"] == "COMPLETED_ON_OR_AHEAD"

    late = evaluate_earned_schedule_duration_posture(100, 120, 100)
    assert late["schedule_variance_days"] == -20.0
    assert round(late["spi_time"], 4) == round(100 / 120, 4)
    assert late["posture"] == "COMPLETED_LATE"


def test_earned_schedule_duration_posture_unscheduled_duration():
    """Sin duración planificada -> UNSCHEDULED_DURATION; sin dias transcurridos -> SPI(t) 1.0."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_duration_posture,
    )

    unscheduled = evaluate_earned_schedule_duration_posture(None, 30, 50)
    assert unscheduled["planned_duration_days"] == 0.0
    assert unscheduled["earned_schedule_days"] == 0.0
    assert unscheduled["posture"] == "UNSCHEDULED_DURATION"

    no_elapsed = evaluate_earned_schedule_duration_posture(100, 0, 50)
    assert no_elapsed["spi_time"] == 1.0
    assert no_elapsed["schedule_variance_days"] == 50.0
    assert no_elapsed["posture"] == "ON_TRACK_DURATION"


def test_evaluate_funding_limit_reconciliation_within_limits_and_reschedule():
    """Dentro de límite -> 'RECONCILED_WITHIN_LIMITS'; planificado > cap -> 'RESCHEDULE_REQUIRED_FOR_CAP'."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_funding_limit_reconciliation,
    )

    within = evaluate_funding_limit_reconciliation(
        planned_cumulative_spend=80000.0,
        actual_cumulative_spend=75000.0,
        periodic_funding_cap=100000.0,
        management_reserve=15000.0,
    )
    assert within == {
        "safe_planned": 80000.0,
        "safe_actual": 75000.0,
        "safe_cap": 100000.0,
        "safe_reserve": 15000.0,
        "total_authorized_ceiling": 115000.0,
        "cap_utilization_pct": 75.0,
        "funding_headroom": 25000.0,
        "planned_exceeds_cap": False,
        "actual_exceeds_cap": False,
        "posture": "RECONCILED_WITHIN_LIMITS",
    }

    reschedule = ProjectEVMService.evaluate_funding_limit_reconciliation(
        planned_cumulative_spend=110000.0,
        actual_cumulative_spend=90000.0,
        periodic_funding_cap=100000.0,
        management_reserve=10000.0,
    )
    assert reschedule["planned_exceeds_cap"] is True
    assert reschedule["actual_exceeds_cap"] is False
    assert reschedule["funding_headroom"] == 10000.0
    assert reschedule["posture"] == "RESCHEDULE_REQUIRED_FOR_CAP"


def test_evaluate_funding_limit_reconciliation_reserve_drawdown_required():
    """Gasto real supera cap pero cubierto por reserva de gestión -> 'RESERVE_DRAWDOWN_REQUIRED'."""
    from backend.services.project_evm_service import (
        evaluate_funding_limit_reconciliation,
    )

    res = evaluate_funding_limit_reconciliation(
        planned_cumulative_spend=95000.0,
        actual_cumulative_spend=108000.0,
        periodic_funding_cap=100000.0,
        management_reserve=10000.0,
    )
    assert res["actual_exceeds_cap"] is True
    assert res["total_authorized_ceiling"] == 110000.0
    assert res["funding_headroom"] == -8000.0
    assert res["cap_utilization_pct"] == 108.0
    assert res["posture"] == "RESERVE_DRAWDOWN_REQUIRED"


def test_evaluate_funding_limit_reconciliation_ceiling_breach_critical():
    """Gasto real supera cap + reserva de gestión -> 'CEILING_BREACH_CRITICAL'."""
    from backend.services.project_evm_service import (
        evaluate_funding_limit_reconciliation,
    )

    res = evaluate_funding_limit_reconciliation(
        planned_cumulative_spend=100000.0,
        actual_cumulative_spend=125000.0,
        periodic_funding_cap=100000.0,
        management_reserve=15000.0,
    )
    assert res["actual_exceeds_cap"] is True
    assert res["total_authorized_ceiling"] == 115000.0
    assert res["funding_headroom"] == -25000.0
    assert res["cap_utilization_pct"] == 125.0
    assert res["posture"] == "CEILING_BREACH_CRITICAL"


def test_evaluate_funding_limit_reconciliation_unconfigured_cap():
    """Sin límite de financiamiento periódico (0 o None) -> 'UNCONFIGURED_FUNDING_CAP'."""
    from backend.services.project_evm_service import (
        evaluate_funding_limit_reconciliation,
    )

    zero_cap_with_spend = evaluate_funding_limit_reconciliation(
        planned_cumulative_spend=50000.0,
        actual_cumulative_spend=20000.0,
        periodic_funding_cap=0.0,
        management_reserve=5000.0,
    )
    assert zero_cap_with_spend["safe_cap"] == 0.0
    assert zero_cap_with_spend["cap_utilization_pct"] == 100.0
    assert zero_cap_with_spend["planned_exceeds_cap"] is False
    assert zero_cap_with_spend["actual_exceeds_cap"] is False
    assert zero_cap_with_spend["posture"] == "UNCONFIGURED_FUNDING_CAP"

    none_all = evaluate_funding_limit_reconciliation(None, None, None, None)
    assert none_all["cap_utilization_pct"] == 0.0
    assert none_all["posture"] == "UNCONFIGURED_FUNDING_CAP"


def test_evaluate_cpi_trend_degradation_systemic_erosion():
    """3 caídas consecutivas o 2 caídas con latest_cpi < 0.90 -> 'SYSTEMIC_CPI_EROSION'."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_cpi_trend_degradation,
    )

    three_drops = ProjectEVMService.evaluate_cpi_trend_degradation(
        [1.04, 1.01, 0.98, 0.96]
    )
    assert three_drops == {
        "clean_series": [1.04, 1.01, 0.98, 0.96],
        "periods_count": 4,
        "latest_cpi": 0.96,
        "average_cpi": 0.9975,
        "consecutive_drops": 3,
        "net_drift": -0.08,
        "posture": "SYSTEMIC_CPI_EROSION",
    }

    two_drops_low = evaluate_cpi_trend_degradation([1.0, 0.93, 0.88])
    assert two_drops_low["consecutive_drops"] == 2
    assert two_drops_low["latest_cpi"] == 0.88
    assert two_drops_low["posture"] == "SYSTEMIC_CPI_EROSION"


def test_evaluate_cpi_trend_degradation_early_warning():
    """Caída final >= 1 con latest_cpi < 0.95 sin alcanzar erosión sistémica -> 'EARLY_DEGRADATION_WARNING'."""
    from backend.services.project_evm_service import evaluate_cpi_trend_degradation

    res = evaluate_cpi_trend_degradation([0.92, 0.97, 0.93])
    assert res["periods_count"] == 3
    assert res["latest_cpi"] == 0.93
    assert res["consecutive_drops"] == 1
    assert res["net_drift"] == 0.01
    assert res["posture"] == "EARLY_DEGRADATION_WARNING"


def test_evaluate_cpi_trend_degradation_improving_or_stable():
    """Tendencia al alza o caída leve con latest_cpi >= 0.95 -> 'IMPROVING_OR_STABLE_TREND'."""
    from backend.services.project_evm_service import evaluate_cpi_trend_degradation

    up_res = evaluate_cpi_trend_degradation([0.89, 0.94, 1.02])
    assert up_res["consecutive_drops"] == 0
    assert up_res["net_drift"] == 0.13
    assert up_res["posture"] == "IMPROVING_OR_STABLE_TREND"

    mild_drop = evaluate_cpi_trend_degradation([1.05, 1.01, 0.97])
    assert mild_drop["consecutive_drops"] == 2
    assert mild_drop["latest_cpi"] == 0.97
    assert mild_drop["posture"] == "IMPROVING_OR_STABLE_TREND"


def test_evaluate_cpi_trend_degradation_insufficient_history():
    """Menos de 2 lecturas válidas (> 0) -> 'INSUFFICIENT_TREND_HISTORY'."""
    from backend.services.project_evm_service import evaluate_cpi_trend_degradation

    single = evaluate_cpi_trend_degradation([0.0, -1.2, False, True, 0.95])
    assert single["clean_series"] == [0.95]
    assert single["periods_count"] == 1
    assert single["latest_cpi"] == 0.95
    assert single["net_drift"] == 0.0
    assert single["posture"] == "INSUFFICIENT_TREND_HISTORY"

    empty = evaluate_cpi_trend_degradation(None)
    assert empty["periods_count"] == 0
    assert empty["latest_cpi"] == 1.0
    assert empty["average_cpi"] == 1.0
    assert empty["posture"] == "INSUFFICIENT_TREND_HISTORY"


def test_evaluate_rebaselining_otb_threshold_over_target_baseline_required():
    """AC >= adjusted_bac con trabajo pendiente (ev < adjusted_bac) -> 'OVER_TARGET_BASELINE_REQUIRED'."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_rebaselining_otb_threshold,
    )

    res = ProjectEVMService.evaluate_rebaselining_otb_threshold(
        bac=100000.0,
        ac=115000.0,
        ev=85000.0,
        approved_change_delta=10000.0,
        tcpi_bac_ceiling=1.20,
    )
    assert res["adjusted_bac"] == 110000.0
    assert res["cpi"] == round(85000.0 / 115000.0, 4)
    assert res["tcpi_bac"] == 999.0
    assert res["budget_exhausted"] is True
    assert res["requires_otb_formal_review"] is True
    assert res["baseline_posture"] == "OVER_TARGET_BASELINE_REQUIRED"
    assert isinstance(res["recommendations"], list) and len(res["recommendations"]) >= 1
    assert (
        evaluate_rebaselining_otb_threshold(
            100000.0, 115000.0, 85000.0, approved_change_delta=10000.0
        )
        == res
    )


def test_evaluate_rebaselining_otb_threshold_rebaselining_recommended():
    """Presupuesto no agotado pero tcpi_bac > tcpi_bac_ceiling -> 'REBASELINING_EVALUATION_RECOMMENDED'."""
    from backend.services.project_evm_service import evaluate_rebaselining_otb_threshold

    res = evaluate_rebaselining_otb_threshold(
        bac=100000.0,
        ac=70000.0,
        ev=55000.0,
        approved_change_delta=0.0,
        tcpi_bac_ceiling=1.20,
    )
    assert res["adjusted_bac"] == 100000.0
    assert res["cpi"] == round(55000.0 / 70000.0, 4)
    assert res["tcpi_bac"] == 1.5
    assert res["budget_exhausted"] is False
    assert res["requires_otb_formal_review"] is True
    assert res["baseline_posture"] == "REBASELINING_EVALUATION_RECOMMENDED"


def test_evaluate_rebaselining_otb_threshold_recoverable():
    """1.0 < tcpi_bac <= tcpi_bac_ceiling -> 'BASELINE_RECOVERABLE'."""
    from backend.services.project_evm_service import evaluate_rebaselining_otb_threshold

    res = evaluate_rebaselining_otb_threshold(
        bac=100000.0,
        ac=52000.0,
        ev=48000.0,
        approved_change_delta=0.0,
        tcpi_bac_ceiling=1.20,
    )
    assert res["adjusted_bac"] == 100000.0
    assert res["tcpi_bac"] == round(52000.0 / 48000.0, 4)
    assert res["budget_exhausted"] is False
    assert res["requires_otb_formal_review"] is False
    assert res["baseline_posture"] == "BASELINE_RECOVERABLE"


def test_evaluate_rebaselining_otb_threshold_within_tolerance_and_no_baseline():
    """tcpi_bac <= 1.0 -> 'BASELINE_WITHIN_TOLERANCE'; adjusted_bac <= 0 -> 'NO_ACTIVE_BASELINE'."""
    from backend.services.project_evm_service import evaluate_rebaselining_otb_threshold

    within = evaluate_rebaselining_otb_threshold(
        bac=80000.0,
        ac=45000.0,
        ev=50000.0,
        approved_change_delta=20000.0,
    )
    assert within["adjusted_bac"] == 100000.0
    assert within["tcpi_bac"] == round(50000.0 / 55000.0, 4)
    assert within["budget_exhausted"] is False
    assert within["requires_otb_formal_review"] is False
    assert within["baseline_posture"] == "BASELINE_WITHIN_TOLERANCE"

    no_base = evaluate_rebaselining_otb_threshold(
        bac=0.0, ac=0.0, ev=0.0, approved_change_delta=-500.0
    )
    assert no_base["adjusted_bac"] == 0.0
    assert no_base["cpi"] == 0.0
    assert no_base["tcpi_bac"] == 0.0
    assert no_base["budget_exhausted"] is False
    assert no_base["requires_otb_formal_review"] is False
    assert no_base["baseline_posture"] == "NO_ACTIVE_BASELINE"


def test_evaluate_management_reserve_release_governance_governed_utilization():
    """Liberaciones con sponsor_approved=True y justificación >= 10 chars dentro de MR -> 'GOVERNED_MR_UTILIZATION'."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_management_reserve_release_governance,
    )

    releases = [
        {
            "id": "MR-101",
            "amount": 6000.0,
            "sponsor_approved": True,
            "justification": "Mitigación regulatoria imprevista aprobada por el patrocinador.",
        },
        {
            "release_id": "MR-102",
            "amount": 4000.0,
            "sponsor_approved": True,
            "justification": "Refuerzo estructural de emergencia en sede central.",
        },
    ]

    res = ProjectEVMService.evaluate_management_reserve_release_governance(
        bac=100000.0,
        management_reserve_initial=20000.0,
        mr_releases=releases,
    )
    assert res["initial_mr"] == 20000.0
    assert res["authorized_mr_released"] == 10000.0
    assert res["unauthorized_mr_amount"] == 0.0
    assert res["unauthorized_release_ids"] == []
    assert res["remaining_mr"] == 10000.0
    assert res["updated_project_budget_total"] == 120000.0
    assert res["mr_burn_pct"] == 50.0
    assert res["mr_governance_posture"] == "GOVERNED_MR_UTILIZATION"
    assert len(res["recommendations"]) >= 1
    assert (
        evaluate_management_reserve_release_governance(
            100000.0, 20000.0, mr_releases=releases
        )
        == res
    )


def test_evaluate_management_reserve_release_governance_unauthorized_drawdown():
    """Liberaciones sin sponsor_approved o con justificación < 10 chars -> 'UNAUTHORIZED_MR_DRAWDOWN'."""
    from backend.services.project_evm_service import (
        evaluate_management_reserve_release_governance,
    )

    releases = [
        {
            "id": "MR-201",
            "amount": 5000.0,
            "sponsor_approved": True,
            "justification": "Cambio regulatorio externo documentado.",
        },
        {
            "id": "MR-202",
            "amount": 3000.0,
            "sponsor_approved": False,
            "justification": "Uso directo sin firma del patrocinador.",
        },
        {
            "release_id": "MR-203",
            "amount": 2000.0,
            "sponsor_approved": True,
            "justification": "Urgente",
        },
    ]

    res = evaluate_management_reserve_release_governance(
        bac=80000.0,
        management_reserve_initial=15000.0,
        mr_releases=releases,
    )
    assert res["initial_mr"] == 15000.0
    assert res["authorized_mr_released"] == 5000.0
    assert res["unauthorized_mr_amount"] == 5000.0
    assert res["unauthorized_release_ids"] == ["MR-202", "MR-203"]
    assert res["remaining_mr"] == 5000.0
    assert res["updated_project_budget_total"] == 95000.0
    assert res["mr_burn_pct"] == 66.67
    assert res["mr_governance_posture"] == "UNAUTHORIZED_MR_DRAWDOWN"
    assert any("MR-202" in rec for rec in res["recommendations"])


def test_evaluate_management_reserve_release_governance_overrun():
    """Liberaciones acumuladas > initial_mr (remaining_mr < 0) -> 'MANAGEMENT_RESERVE_OVERRUN'."""
    from backend.services.project_evm_service import (
        evaluate_management_reserve_release_governance,
    )

    releases = [
        {
            "id": "MR-301",
            "amount": 9000.0,
            "sponsor_approved": True,
            "justification": "Contingencia desconocida fase 1 autorizada.",
        },
        {
            "id": "MR-302",
            "amount": 4500.0,
            "sponsor_approved": True,
            "justification": "Contingencia desconocida fase 2 autorizada.",
        },
    ]

    res = evaluate_management_reserve_release_governance(
        bac=50000.0,
        management_reserve_initial=10000.0,
        mr_releases=releases,
    )
    assert res["initial_mr"] == 10000.0
    assert res["authorized_mr_released"] == 13500.0
    assert res["unauthorized_mr_amount"] == 0.0
    assert res["remaining_mr"] == -3500.0
    assert res["updated_project_budget_total"] == 60000.0
    assert res["mr_burn_pct"] == 135.0
    assert res["mr_governance_posture"] == "MANAGEMENT_RESERVE_OVERRUN"
    assert len(res["recommendations"]) >= 1


def test_evaluate_management_reserve_release_governance_no_reserve():
    """initial_mr <= 0 y sin liberaciones -> 'NO_MANAGEMENT_RESERVE'."""
    from backend.services.project_evm_service import (
        evaluate_management_reserve_release_governance,
    )

    for releases in (None, [], ["invalid"]):
        res = evaluate_management_reserve_release_governance(
            bac=60000.0,
            management_reserve_initial=0.0,
            mr_releases=releases,  # type: ignore[arg-type]
        )
        assert res["initial_mr"] == 0.0
        assert res["authorized_mr_released"] == 0.0
        assert res["unauthorized_mr_amount"] == 0.0
        assert res["unauthorized_release_ids"] == []
        assert res["remaining_mr"] == 0.0
        assert res["updated_project_budget_total"] == 60000.0
        assert res["mr_burn_pct"] == 0.0
        assert res["mr_governance_posture"] == "NO_MANAGEMENT_RESERVE"
        assert len(res["recommendations"]) == 1


# ─── evaluate_remaining_investment_viability (pure helper) ──────────────


def test_remaining_investment_viability_viable_business_case():
    """CPI sobre el piso y BCR >= 1 -> VIABLE_BUSINESS_CASE con pronóstico IPA/PPC."""
    from backend.services.project_evm_service import (
        evaluate_remaining_investment_viability,
    )

    res = evaluate_remaining_investment_viability(
        bac=100000.0, ac=40000.0, ev=45000.0, expected_benefits_npv=200000.0
    )

    assert res["cpi"] == 1.125
    assert res["effective_cpi"] == 1.125
    assert res["etc_forecast"] == 48888.89
    assert res["eac_forecast"] == 88888.89
    assert res["benefit_cost_ratio_at_completion"] == 2.25
    assert res["incremental_benefit_to_etc_ratio"] == 4.0909
    assert res["viability_posture"] == "VIABLE_BUSINESS_CASE"
    assert len(res["recommendations"]) == 1


def test_remaining_investment_viability_termination_or_restructure():
    """Beneficios insuficientes frente a la inversión remanente -> TERMINATION_OR_RESTRUCTURE_REVIEW."""
    from backend.services.project_evm_service import (
        evaluate_remaining_investment_viability,
    )

    res = evaluate_remaining_investment_viability(
        bac=100000.0, ac=20000.0, ev=10000.0, expected_benefits_npv=1000.0
    )

    assert res["cpi"] == 0.5
    assert res["etc_forecast"] == 180000.0
    assert res["eac_forecast"] == 200000.0
    assert res["benefit_cost_ratio_at_completion"] == 0.005
    assert res["incremental_benefit_to_etc_ratio"] == 0.0056
    assert res["viability_posture"] == "TERMINATION_OR_RESTRUCTURE_REVIEW"


def test_remaining_investment_viability_negative_net_benefit():
    """Ratio incremental >= 1 pero BCR < 1 -> NEGATIVE_NET_BENEFIT_AT_COMPLETION."""
    from backend.services.project_evm_service import (
        evaluate_remaining_investment_viability,
    )

    res = evaluate_remaining_investment_viability(
        bac=100000.0, ac=50000.0, ev=50000.0, expected_benefits_npv=60000.0
    )

    assert res["cpi"] == 1.0
    assert res["etc_forecast"] == 50000.0
    assert res["eac_forecast"] == 100000.0
    assert res["benefit_cost_ratio_at_completion"] == 0.6
    assert res["incremental_benefit_to_etc_ratio"] == 1.2
    assert res["viability_posture"] == "NEGATIVE_NET_BENEFIT_AT_COMPLETION"


def test_remaining_investment_viability_marginal_and_no_baseline():
    """BCR >= 1 con CPI bajo el piso -> MARGINAL; sin BAC ni VAN -> NO_INVESTMENT_BASELINE; ev>=bac -> ETC 0."""
    from backend.services.project_evm_service import (
        evaluate_remaining_investment_viability,
    )

    marginal = evaluate_remaining_investment_viability(
        bac=100000.0, ac=50000.0, ev=20000.0, expected_benefits_npv=300000.0
    )
    assert marginal["cpi"] == 0.4
    assert marginal["etc_forecast"] == 200000.0
    assert marginal["eac_forecast"] == 250000.0
    assert marginal["benefit_cost_ratio_at_completion"] == 1.2
    assert marginal["incremental_benefit_to_etc_ratio"] == 1.5
    assert marginal["viability_posture"] == "MARGINAL_INVESTMENT_EFFICIENCY"

    no_baseline = evaluate_remaining_investment_viability(
        bac=0.0, ac=0.0, ev=0.0, expected_benefits_npv=None  # type: ignore[arg-type]
    )
    assert no_baseline["viability_posture"] == "NO_INVESTMENT_BASELINE"
    assert no_baseline["etc_forecast"] == 0.0

    completed = evaluate_remaining_investment_viability(
        bac=1000.0, ac=800.0, ev=1000.0, expected_benefits_npv=5000.0
    )
    assert completed["etc_forecast"] == 0.0
    assert completed["eac_forecast"] == 800.0
    assert completed["incremental_benefit_to_etc_ratio"] == 999.0
    assert completed["benefit_cost_ratio_at_completion"] == 6.25
    assert completed["viability_posture"] == "VIABLE_BUSINESS_CASE"


# ─── evaluate_control_account_variance_masking (pure helper) ──────────────


def test_evaluate_control_account_variance_masking_hidden_masking_detected():
    """Variación positiva compensa sobrecosto severo (<50% del negativo bruto en neto) -> HIDDEN_VARIANCE_MASKING_DETECTED."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_control_account_variance_masking,
    )

    packages = [
        {"id": "WP-101", "bac": 50000.0, "ev": 30000.0, "ac": 42000.0},  # CV = -12000 (-24%)
        {"code": "WP-102", "pv": 50000.0, "ev": 35000.0, "ac": 25000.0},  # CV = +10000 (+20%)
    ]

    res = evaluate_control_account_variance_masking(packages, masking_threshold_pct=15.0)
    assert res["total_packages"] == 2
    assert res["net_control_account_cv"] == -2000.0
    assert res["gross_negative_cv"] == 12000.0
    assert res["gross_positive_cv"] == 10000.0
    assert res["severely_overrun_package_ids"] == ["WP-101"]
    assert res["is_variance_masked"] is True
    assert res["masking_posture"] == "HIDDEN_VARIANCE_MASKING_DETECTED"
    assert any("WP-101" in r for r in res["recommendations"])
    assert (
        ProjectEVMService.evaluate_control_account_variance_masking(
            packages, masking_threshold_pct=15.0
        )
        == res
    )


def test_evaluate_control_account_variance_masking_unmasked_overrun():
    """Sobrecosto severo sin compensación suficiente -> UNMASKED_PACKAGE_OVERRUN."""
    from backend.services.project_evm_service import (
        evaluate_control_account_variance_masking,
    )

    packages = [
        {"id": "WP-201", "bac": 40000.0, "ev": 20000.0, "ac": 30000.0},  # CV = -10000 (-25%)
        {"id": "WP-202", "bac": 20000.0, "ev": 12000.0, "ac": 10000.0},  # CV = +2000 (+10%)
    ]

    res = evaluate_control_account_variance_masking(packages, masking_threshold_pct=15.0)
    assert res["total_packages"] == 2
    assert res["net_control_account_cv"] == -8000.0
    assert res["gross_negative_cv"] == 10000.0
    assert res["gross_positive_cv"] == 2000.0
    assert res["severely_overrun_package_ids"] == ["WP-201"]
    assert res["is_variance_masked"] is False
    assert res["masking_posture"] == "UNMASKED_PACKAGE_OVERRUN"
    assert any("WP-201" in r for r in res["recommendations"])


def test_evaluate_control_account_variance_masking_uniform_health():
    """Variaciones negativas leves (< umbral) o positivas -> UNIFORM_CONTROL_ACCOUNT_HEALTH."""
    from backend.services.project_evm_service import (
        evaluate_control_account_variance_masking,
    )

    packages = [
        {"id": "WP-301", "bac": 50000.0, "ev": 24000.0, "ac": 26000.0},  # CV = -2000 (-4%)
        {"id": "WP-302", "bac": 50000.0, "ev": 30000.0, "ac": 27000.0},  # CV = +3000 (+6%)
    ]

    res = evaluate_control_account_variance_masking(packages, masking_threshold_pct=15.0)
    assert res["total_packages"] == 2
    assert res["net_control_account_cv"] == 1000.0
    assert res["gross_negative_cv"] == 2000.0
    assert res["gross_positive_cv"] == 3000.0
    assert res["severely_overrun_package_ids"] == []
    assert res["is_variance_masked"] is False
    assert res["masking_posture"] == "UNIFORM_CONTROL_ACCOUNT_HEALTH"
    assert len(res["recommendations"]) == 1


def test_evaluate_control_account_variance_masking_no_work_packages():
    """Lista vacía, None o entradas no-dict -> NO_WORK_PACKAGES."""
    from backend.services.project_evm_service import (
        evaluate_control_account_variance_masking,
    )

    for payload in (None, [], ["invalid", 42]):
        res = evaluate_control_account_variance_masking(payload)  # type: ignore[arg-type]
        assert res["total_packages"] == 0
        assert res["net_control_account_cv"] == 0.0
        assert res["gross_negative_cv"] == 0.0
        assert res["gross_positive_cv"] == 0.0
        assert res["severely_overrun_package_ids"] == []
        assert res["is_variance_masked"] is False
        assert res["masking_posture"] == "NO_WORK_PACKAGES"
        assert len(res["recommendations"]) == 1


def test_evaluate_earned_schedule_performance_on_or_ahead():
    """SPI(t) >= 0.95 -> ON_OR_AHEAD_OF_SCHEDULE."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_earned_schedule_performance,
    )

    pv_curve = [100.0, 250.0, 450.0, 700.0, 1000.0]
    res = evaluate_earned_schedule_performance(
        planned_value_curve=pv_curve,
        earned_value=500.0,
        actual_time_periods=3.0,
        planned_duration_periods=5.0,
    )
    # C = 3 (PV_3 = 450, PV_4 = 700), I = (500 - 450) / (700 - 450) = 0.2 -> ES = 3.2
    assert res["earned_schedule"] == 3.2
    assert res["actual_time_periods"] == 3.0
    assert res["sv_t"] == 0.2
    assert res["spi_t"] == 1.07
    assert res["eac_t"] == 4.69
    assert res["is_on_schedule"] is True
    assert res["schedule_posture"] == "ON_OR_AHEAD_OF_SCHEDULE"
    assert (
        ProjectEVMService.evaluate_earned_schedule_performance(
            planned_value_curve=pv_curve,
            earned_value=500.0,
            actual_time_periods=3.0,
            planned_duration_periods=5.0,
        )
        == res
    )


def test_evaluate_earned_schedule_performance_moderate_delay():
    """0.85 <= SPI(t) < 0.95 -> MODERATE_SCHEDULE_DELAY."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_performance,
    )

    pv_curve = [100.0, 200.0, 300.0, 400.0, 500.0]
    res = evaluate_earned_schedule_performance(
        planned_value_curve=pv_curve,
        earned_value=360.0,
        actual_time_periods=4.0,
        planned_duration_periods=5.0,
    )
    # C = 3 (PV_3 = 300, PV_4 = 400), I = (360 - 300) / 100 = 0.6 -> ES = 3.6
    # SPI(t) = 3.6 / 4.0 = 0.90, SV(t) = -0.4, EAC(t) = 5.0 / 0.9 = 5.56
    assert res["earned_schedule"] == 3.6
    assert res["actual_time_periods"] == 4.0
    assert res["sv_t"] == -0.4
    assert res["spi_t"] == 0.9
    assert res["eac_t"] == 5.56
    assert res["is_on_schedule"] is False
    assert res["schedule_posture"] == "MODERATE_SCHEDULE_DELAY"


def test_evaluate_earned_schedule_performance_critical_slippage():
    """SPI(t) < 0.85 con interpolación en primer periodo -> CRITICAL_SCHEDULE_SLIPPAGE."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_performance,
    )

    pv_curve = [200.0, 400.0, 600.0, 800.0]
    res = evaluate_earned_schedule_performance(
        planned_value_curve=pv_curve,
        earned_value=150.0,
        actual_time_periods=2.0,
    )
    # EV < PV_1 -> C = 0, I = 150 / 200 = 0.75 -> ES = 0.75
    # SPI(t) = 0.75 / 2.0 = 0.375 -> 0.38, PD = 4.0 -> EAC(t) = 4.0 / 0.375 = 10.67
    assert res["earned_schedule"] == 0.75
    assert res["actual_time_periods"] == 2.0
    assert res["sv_t"] == -1.25
    assert res["spi_t"] == 0.38
    assert res["eac_t"] == 10.67
    assert res["is_on_schedule"] is False
    assert res["schedule_posture"] == "CRITICAL_SCHEDULE_SLIPPAGE"


def test_evaluate_earned_schedule_performance_insufficient_curve():
    """Curva vacía, None, curve[-1] <= 0 o AT <= 0 -> INSUFFICIENT_SCHEDULE_CURVE."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_performance,
    )

    for curve, at in [(None, 3.0), ([], 2.0), ([100.0, 200.0], 0.0), ([0.0, 0.0], 2.0)]:
        res = evaluate_earned_schedule_performance(
            planned_value_curve=curve,
            earned_value=50.0,
            actual_time_periods=at,
        )
        assert res["earned_schedule"] == 0.0
        assert res["sv_t"] == 0.0
        assert res["spi_t"] == 1.0
        assert res["eac_t"] == 0.0
        assert res["is_on_schedule"] is True
        assert res["schedule_posture"] == "INSUFFICIENT_SCHEDULE_CURVE"


if __name__ == "__main__":
    test_evm_balanced_project()
    test_evm_cost_overrun_critical()
    test_evm_cost_efficient()
    test_evm_zero_cost_edge_case()
    test_curve_s_generation()
    test_analyze_s_curve_velocity_trends_and_integration()
    test_predict_schedule_slippage_days_ahead_or_on_time()
    test_predict_schedule_slippage_days_minor_slippage()
    test_predict_schedule_slippage_days_critical_slippage()
    test_predict_schedule_slippage_days_unscheduled_and_stalled()
    test_evaluate_contingency_reserve_burn_alignment_proportional_and_conservative()
    test_evaluate_contingency_reserve_burn_alignment_premature_depletion()
    test_evaluate_contingency_reserve_burn_alignment_reserve_exhausted()
    test_evaluate_contingency_reserve_burn_alignment_no_contingency_allocated()
    test_evaluate_variance_at_completion_alert_on_or_under_budget()
    test_evaluate_variance_at_completion_alert_overrun_absorbed_by_mr()
    test_evaluate_variance_at_completion_alert_budget_breach_beyond_mr()
    test_evaluate_variance_at_completion_alert_unbaselined()
    test_evaluate_etc_forecasting_method_posture_completed_no_etc()
    test_evaluate_etc_forecasting_method_posture_composite_cpi_spi()
    test_evaluate_etc_forecasting_method_posture_typical_cpi()
    test_evaluate_etc_forecasting_method_posture_atypical_remaining_budget()
    test_evaluate_funding_limit_reconciliation_within_limits_and_reschedule()
    test_evaluate_funding_limit_reconciliation_reserve_drawdown_required()
    test_evaluate_funding_limit_reconciliation_ceiling_breach_critical()
    test_evaluate_funding_limit_reconciliation_unconfigured_cap()
    test_evaluate_cpi_trend_degradation_systemic_erosion()
    test_evaluate_cpi_trend_degradation_early_warning()
    test_evaluate_cpi_trend_degradation_improving_or_stable()
    test_evaluate_cpi_trend_degradation_insufficient_history()
    test_evaluate_rebaselining_otb_threshold_over_target_baseline_required()
    test_evaluate_rebaselining_otb_threshold_rebaselining_recommended()
    test_evaluate_rebaselining_otb_threshold_recoverable()
    test_evaluate_rebaselining_otb_threshold_within_tolerance_and_no_baseline()
    test_evaluate_management_reserve_release_governance_governed_utilization()
    test_evaluate_management_reserve_release_governance_unauthorized_drawdown()
    test_evaluate_management_reserve_release_governance_overrun()
    test_evaluate_management_reserve_release_governance_no_reserve()
    test_evaluate_control_account_variance_masking_hidden_masking_detected()
    test_evaluate_control_account_variance_masking_unmasked_overrun()
    test_evaluate_control_account_variance_masking_uniform_health()
    test_evaluate_control_account_variance_masking_no_work_packages()
    test_evaluate_earned_schedule_performance_on_or_ahead()
    test_evaluate_earned_schedule_performance_moderate_delay()
    test_evaluate_earned_schedule_performance_critical_slippage()
    test_evaluate_earned_schedule_performance_insufficient_curve()
    print("✅ All EVM tests passed successfully!")



def test_evaluate_funding_limit_periods_reconciliation_reconciled_within_limits():
    """>= 2 periodos dentro del buffer 95% -> RECONCILED_WITHIN_FUNDING_LIMITS."""
    from backend.services.project_evm_service import (
        evaluate_funding_limit_periods_reconciliation as eval_fn,
    )

    res = eval_fn(
        [
            {
                "period": "2026-Q3",
                "planned_expenditure": 40000.0,
                "funding_limit": 50000.0,
            },
            {
                "id": "2026-Q4",
                "planned_cost": 30000.0,
                "authorized_funds": 40000.0,
            },
        ]
    )
    assert res["is_reconciled"] is True
    assert res["evaluated_periods_count"] == 2
    assert res["breached_periods"] == []
    assert res["tight_buffer_periods"] == []
    assert res["peak_funding_utilization_pct"] == 80.0
    assert res["total_funding_shortfall"] == 0.0
    assert res["funding_posture"] == "RECONCILED_WITHIN_FUNDING_LIMITS"


def test_evaluate_funding_limit_periods_reconciliation_tight_buffer():
    """Utilización > 95% sin superar el límite -> TIGHT_FUNDING_BUFFER_WARNING."""
    from backend.services.project_evm_service import (
        evaluate_funding_limit_periods_reconciliation as eval_fn,
    )

    res = eval_fn(
        [
            {
                "period": "2027-Q1",
                "planned_expenditure": 4800.0,
                "funding_limit": 5000.0,
            }
        ]
    )
    assert res["is_reconciled"] is True
    assert res["evaluated_periods_count"] == 1
    assert res["breached_periods"] == []
    assert res["tight_buffer_periods"] == ["2027-Q1"]
    assert res["peak_funding_utilization_pct"] == 96.0
    assert res["total_funding_shortfall"] == 0.0
    assert res["funding_posture"] == "TIGHT_FUNDING_BUFFER_WARNING"


def test_evaluate_funding_limit_periods_reconciliation_breach_with_shortfall():
    """Superar el límite o gasto sin límite -> FUNDING_LIMIT_BREACH con shortfall exacto."""
    from backend.services.project_evm_service import (
        evaluate_funding_limit_periods_reconciliation as eval_fn,
    )

    res = eval_fn(
        [
            {
                "period": "2027-Q2",
                "planned_expenditure": 10500.0,
                "funding_limit": 10000.0,
            },
            {
                "quarter": "2027-Q3",
                "planned_expenditure": 2500.0,
            },
            {
                "period": "2027-Q4",
                "planned_expenditure": 1500.0,
                "funding_limit": 2000.0,
            },
        ]
    )
    assert res["is_reconciled"] is False
    assert res["evaluated_periods_count"] == 3
    # 2027-Q2: 105% > límite -> brecha de 500.0; 2027-Q3: sin límite con gasto -> brecha de 2500.0.
    assert res["breached_periods"] == ["2027-Q2", "2027-Q3"]
    assert res["tight_buffer_periods"] == []
    assert res["peak_funding_utilization_pct"] == 105.0
    assert res["total_funding_shortfall"] == 3000.0
    assert res["funding_posture"] == "FUNDING_LIMIT_BREACH"


def test_evaluate_funding_limit_periods_reconciliation_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_FUNDING_PERIODS_DEFINED."""
    from backend.services.project_evm_service import (
        evaluate_funding_limit_periods_reconciliation as eval_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = eval_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_periods_count": 0,
            "breached_periods": [],
            "tight_buffer_periods": [],
            "peak_funding_utilization_pct": 0.0,
            "total_funding_shortfall": 0.0,
            "is_reconciled": True,
            "funding_posture": "NO_FUNDING_PERIODS_DEFINED",
        }


def test_evaluate_burn_rate_runway_sustainability_sustainable():
    """Burn-rate sostenible con budget_runway_periods >= remaining_periods -> SUSTAINABLE_BURN_RATE_RUNWAY."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_burn_rate_runway_sustainability,
    )

    # BAC=100k, AC=36k en 4 períodos -> burn_rate=9k/período.
    # Restan 64k para 6 períodos -> sustainable_burn=10666.67, runway=7.11 >= 6.
    res = evaluate_burn_rate_runway_sustainability(
        bac=100000.0,
        actual_cost=36000.0,
        elapsed_periods=4.0,
        remaining_periods=6.0,
        management_reserve=10000.0,
    )
    assert res == {
        "actual_burn_rate": 9000.0,
        "sustainable_burn_rate": 10666.67,
        "budget_runway_periods": 7.11,
        "total_funds_runway_periods": 8.22,
        "runway_gap_periods": 1.11,
        "is_sustainable": True,
        "burn_posture": "SUSTAINABLE_BURN_RATE_RUNWAY",
    }
    assert (
        ProjectEVMService.evaluate_burn_rate_runway_sustainability(
            bac=100000.0,
            actual_cost=36000.0,
            elapsed_periods=4.0,
            remaining_periods=6.0,
            management_reserve=10000.0,
        )
        == res
    )


def test_evaluate_burn_rate_runway_sustainability_requires_management_reserve():
    """Pista BAC insuficiente pero cubierta con management_reserve -> RUNWAY_REQUIRES_MANAGEMENT_RESERVE."""
    from backend.services.project_evm_service import (
        evaluate_burn_rate_runway_sustainability,
    )

    # BAC=100k, AC=50k en 4 períodos -> burn_rate=12.5k/período.
    # Restan 50k BAC (runway=4.0 < 5.0 períodos restantes), pero con MR=15k (total_funds_runway=5.2 >= 5.0).
    res = evaluate_burn_rate_runway_sustainability(
        bac=100000.0,
        actual_cost=50000.0,
        elapsed_periods=4.0,
        remaining_periods=5.0,
        management_reserve=15000.0,
    )
    assert res == {
        "actual_burn_rate": 12500.0,
        "sustainable_burn_rate": 10000.0,
        "budget_runway_periods": 4.0,
        "total_funds_runway_periods": 5.2,
        "runway_gap_periods": -1.0,
        "is_sustainable": False,
        "burn_posture": "RUNWAY_REQUIRES_MANAGEMENT_RESERVE",
    }


def test_evaluate_burn_rate_runway_sustainability_shortfall_and_budget_exhausted():
    """Pista insuficiente aun con MR -> RUNWAY_SHORTFALL_BEYOND_RESERVES; AC >= BAC -> BUDGET_EXHAUSTED."""
    from backend.services.project_evm_service import (
        evaluate_burn_rate_runway_sustainability,
    )

    shortfall_res = evaluate_burn_rate_runway_sustainability(
        bac=100000.0,
        actual_cost=60000.0,
        elapsed_periods=3.0,
        remaining_periods=5.0,
        management_reserve=10000.0,
    )
    assert shortfall_res["actual_burn_rate"] == 20000.0
    assert shortfall_res["budget_runway_periods"] == 2.0
    assert shortfall_res["total_funds_runway_periods"] == 2.5
    assert shortfall_res["runway_gap_periods"] == -3.0
    assert shortfall_res["is_sustainable"] is False
    assert shortfall_res["burn_posture"] == "RUNWAY_SHORTFALL_BEYOND_RESERVES"

    exhausted_res = evaluate_burn_rate_runway_sustainability(
        bac=80000.0,
        actual_cost=85000.0,
        elapsed_periods=5.0,
        remaining_periods=2.0,
        management_reserve=10000.0,
    )
    assert exhausted_res["budget_runway_periods"] == 0.0
    assert exhausted_res["is_sustainable"] is False
    assert exhausted_res["burn_posture"] == "BUDGET_EXHAUSTED"


def test_evaluate_burn_rate_runway_sustainability_insufficient_data():
    """bac <= 0 o elapsed_periods <= 0 -> INSUFFICIENT_BURN_DATA."""
    from backend.services.project_evm_service import (
        evaluate_burn_rate_runway_sustainability,
    )

    for bac_val, elapsed_val in ((0.0, 3.0), (50000.0, 0.0), (-10.0, -1.0)):
        res = evaluate_burn_rate_runway_sustainability(
            bac=bac_val,
            actual_cost=1000.0,
            elapsed_periods=elapsed_val,
            remaining_periods=4.0,
        )
        assert res == {
            "actual_burn_rate": 0.0,
            "sustainable_burn_rate": 0.0,
            "budget_runway_periods": 0.0,
            "total_funds_runway_periods": 0.0,
            "runway_gap_periods": 0.0,
            "is_sustainable": True,
            "burn_posture": "INSUFFICIENT_BURN_DATA",
        }


def test_evaluate_cpi_spi_stability_window_stable():
    """Ventana estable con spreads <= 0.10 y swings <= 0.15 -> STABLE_EVM_PERFORMANCE_WINDOW."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_cpi_spi_stability_window,
    )

    snapshots = [
        {"period": "2026-W01", "cpi": 0.98, "spi": 1.01},
        {"period": "2026-W02", "cpi": 1.02, "spi": 0.99},
        {"period": "2026-W03", "cpi": 1.00, "spi": 1.03},
    ]
    res = evaluate_cpi_spi_stability_window(
        snapshots, max_band_width=0.10, max_period_swing=0.15
    )
    assert res == {
        "evaluated_snapshots_count": 3,
        "cpi_spread": 0.04,
        "spi_spread": 0.04,
        "max_observed_swing": 0.04,
        "volatile_period_ids": [],
        "is_index_stable": True,
        "stability_posture": "STABLE_EVM_PERFORMANCE_WINDOW",
    }
    assert (
        ProjectEVMService.evaluate_cpi_spi_stability_window(
            snapshots, max_band_width=0.10, max_period_swing=0.15
        )
        == res
    )


def test_evaluate_cpi_spi_stability_window_volatile_period_swing():
    """Salto brusco período a período (> max_period_swing) -> VOLATILE_PERIOD_SWING_ALERT."""
    from backend.services.project_evm_service import (
        evaluate_cpi_spi_stability_window,
    )

    snapshots = [
        {"period": "2026-M01", "cpi": 1.01, "spi": 1.00},
        {"period": "2026-M02", "cpi": 0.80, "spi": 0.98},
        {"period": "2026-M03", "cpi": 0.82, "spi": 0.78},
    ]
    res = evaluate_cpi_spi_stability_window(
        snapshots, max_band_width=0.10, max_period_swing=0.15
    )
    assert res["evaluated_snapshots_count"] == 3
    assert res["cpi_spread"] == 0.21
    assert res["spi_spread"] == 0.22
    assert res["max_observed_swing"] == 0.21
    assert res["volatile_period_ids"] == ["2026-M02", "2026-M03"]
    assert res["is_index_stable"] is False
    assert res["stability_posture"] == "VOLATILE_PERIOD_SWING_ALERT"


def test_evaluate_cpi_spi_stability_window_wide_drift_band():
    """Deriva gradual acumulada que supera max_band_width sin superar max_period_swing -> WIDE_INDEX_DRIFT_BAND."""
    from backend.services.project_evm_service import (
        evaluate_cpi_spi_stability_window,
    )

    # Pasos de 0.06 (<= 0.15 swing), pero spread total = 0.18 > 0.10 band width
    snapshots = [
        {"snapshot_id": "S1", "cost_performance_index": 1.04, "schedule_performance_index": 1.00},
        {"snapshot_id": "S2", "cost_performance_index": 0.98, "schedule_performance_index": 0.99},
        {"snapshot_id": "S3", "cost_performance_index": 0.92, "schedule_performance_index": 0.98},
        {"snapshot_id": "S4", "cost_performance_index": 0.86, "schedule_performance_index": 0.97},
    ]
    res = evaluate_cpi_spi_stability_window(
        snapshots, max_band_width=0.10, max_period_swing=0.15
    )
    assert res["evaluated_snapshots_count"] == 4
    assert res["cpi_spread"] == 0.18
    assert res["spi_spread"] == 0.03
    assert res["max_observed_swing"] == 0.06
    assert res["volatile_period_ids"] == []
    assert res["is_index_stable"] is False
    assert res["stability_posture"] == "WIDE_INDEX_DRIFT_BAND"


def test_evaluate_cpi_spi_stability_window_empty_or_none():
    """Lista vacía, None o snapshots sin CPI/SPI > 0 -> NO_SNAPSHOTS_EVALUATED."""
    from backend.services.project_evm_service import (
        evaluate_cpi_spi_stability_window,
    )

    for payload in (None, [], ["invalid", 42], [{"period": "P1", "cpi": 0.0, "spi": -1.0}]):
        res = evaluate_cpi_spi_stability_window(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_snapshots_count": 0,
            "cpi_spread": 0.0,
            "spi_spread": 0.0,
            "max_observed_swing": 0.0,
            "volatile_period_ids": [],
            "is_index_stable": True,
            "stability_posture": "NO_SNAPSHOTS_EVALUATED",
        }


def test_evaluate_reserve_drawdown_velocity_proportional():
    """Consumo proporcional de contingencia y MR con CR aprobada -> PROPORTIONAL_RESERVE_DRAWDOWN."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_reserve_drawdown_velocity,
    )

    res = evaluate_reserve_drawdown_velocity(
        initial_contingency_reserve=20000.0,
        contingency_reserve_consumed=8000.0,
        percent_complete_pct=50.0,
        management_reserve_used=5000.0,
        approved_mr_change_requests_count=1,
        max_burn_velocity_ratio=1.25,
    )
    assert res == {
        "contingency_consumed_pct": 40.0,
        "remaining_contingency_reserve": 12000.0,
        "burn_velocity_ratio": 0.8,
        "has_unapproved_mr_drawdown": False,
        "is_contingency_overburned": False,
        "is_reserve_healthy": True,
        "reserve_posture": "PROPORTIONAL_RESERVE_DRAWDOWN",
    }
    assert (
        ProjectEVMService.evaluate_reserve_drawdown_velocity(
            initial_contingency_reserve=20000.0,
            contingency_reserve_consumed=8000.0,
            percent_complete_pct=50.0,
            management_reserve_used=5000.0,
            approved_mr_change_requests_count=1,
            max_burn_velocity_ratio=1.25,
        )
        == res
    )


def test_evaluate_reserve_drawdown_velocity_unapproved_mr_drawdown():
    """Uso de Reserva de Gestión sin CR aprobada -> UNAPPROVED_MANAGEMENT_RESERVE_DRAWDOWN."""
    from backend.services.project_evm_service import (
        evaluate_reserve_drawdown_velocity,
    )

    res = evaluate_reserve_drawdown_velocity(
        initial_contingency_reserve=10000.0,
        contingency_reserve_consumed=2000.0,
        percent_complete_pct=30.0,
        management_reserve_used=3500.0,
        approved_mr_change_requests_count=0,
    )
    assert res["has_unapproved_mr_drawdown"] is True
    assert res["is_reserve_healthy"] is False
    assert res["reserve_posture"] == "UNAPPROVED_MANAGEMENT_RESERVE_DRAWDOWN"


def test_evaluate_reserve_drawdown_velocity_accelerated_and_exhausted():
    """Quema acelerada (> 1.25) -> ACCELERATED_RESERVE_BURN_WARNING y agotamiento -> CONTINGENCY_RESERVE_EXHAUSTED."""
    from backend.services.project_evm_service import (
        evaluate_reserve_drawdown_velocity,
    )

    accel_res = evaluate_reserve_drawdown_velocity(
        initial_contingency_reserve=10000.0,
        contingency_reserve_consumed=7000.0,
        percent_complete_pct=40.0,
        max_burn_velocity_ratio=1.25,
    )
    assert accel_res["contingency_consumed_pct"] == 70.0
    assert accel_res["burn_velocity_ratio"] == 1.75
    assert accel_res["is_contingency_overburned"] is True
    assert accel_res["is_reserve_healthy"] is False
    assert accel_res["reserve_posture"] == "ACCELERATED_RESERVE_BURN_WARNING"

    exhausted_res = evaluate_reserve_drawdown_velocity(
        initial_contingency_reserve=10000.0,
        contingency_reserve_consumed=10000.0,
        percent_complete_pct=60.0,
    )
    assert exhausted_res["remaining_contingency_reserve"] == 0.0
    assert exhausted_res["is_contingency_overburned"] is True
    assert exhausted_res["is_reserve_healthy"] is False
    assert exhausted_res["reserve_posture"] == "CONTINGENCY_RESERVE_EXHAUSTED"


def test_evaluate_reserve_drawdown_velocity_no_reserve_configured():
    """Sin reservas configuradas -> NO_RESERVE_CONFIGURED."""
    from backend.services.project_evm_service import (
        evaluate_reserve_drawdown_velocity,
    )

    res = evaluate_reserve_drawdown_velocity(
        initial_contingency_reserve=0.0,
        contingency_reserve_consumed=0.0,
        percent_complete_pct=25.0,
        management_reserve_used=0.0,
    )
    assert res == {
        "contingency_consumed_pct": 0.0,
        "remaining_contingency_reserve": 0.0,
        "burn_velocity_ratio": 0.0,
        "has_unapproved_mr_drawdown": False,
        "is_contingency_overburned": False,
        "is_reserve_healthy": True,
        "reserve_posture": "NO_RESERVE_CONFIGURED",
    }


def test_evaluate_tcpi_recovery_feasible_stretch():
    """> TCPI_BAC justo en el limite 1.10 con salto 0.1125 -> STRETCH monitor closely."""
    from backend.services.project_evm_service import evaluate_tcpi_recovery_feasibility as eval_fn

    res = eval_fn(bac=900.0, ev=790.0, ac=800.0)
    assert res["cpi"] == 0.9875
    assert res["tcpi_bac"] == 1.1
    assert res["tcpi_eac"] == 0.9875
    assert res["efficiency_jump_required"] == 0.1125
    assert res["is_bac_funds_exhausted"] is False
    assert res["is_bac_recoverable"] is True
    assert res["recovery_posture"] == "STRETCH_RECOVERY_MONITOR_CLOSELY"


def test_evaluate_tcpi_recovery_feasible_bc():
    """> TCPI_BAC <= 1.0 -> FEASIBLE_BAC_COMPLETION sin salto exigido."""
    from backend.services.project_evm_service import evaluate_tcpi_recovery_feasibility as eval_fn

    res = eval_fn(bac=1000.0, ev=900.0, ac=850.0)
    # CPI = 1.0588; trabajo 100, fondos 150 -> TCPI_BAC = 0.6667.
    assert res["cpi"] == 1.0588
    assert res["tcpi_bac"] == 0.6667
    assert res["efficiency_jump_required"] == 0.0
    assert res["is_bac_funds_exhausted"] is False
    assert res["is_bac_recoverable"] is True
    assert res["recovery_posture"] == "FEASIBLE_BAC_COMPLETION"


def test_evaluate_tcpi_recovery_unrecoverable_severe_overrun():
    """> TCPI_BAC > 1.10 y salto gordo -> UNRECOVERABLE_BAC_ADOPT_EAC."""
    from backend.services.project_evm_service import evaluate_tcpi_recovery_feasibility as eval_fn

    res = eval_fn(bac=1000.0, ev=600.0, ac=700.0)
    assert res["is_bac_funds_exhausted"] is False
    assert res["is_bac_recoverable"] is False
    assert res["cpi"] == 0.8571
    assert res["tcpi_bac"] == 1.3333
    # TCPI_EAC sobre eac derivado bac/cpi redondeado a 2 dec (4dp en el cociente).
    assert res["tcpi_eac"] == 0.857
    assert res["efficiency_jump_required"] == 0.4762
    assert res["recovery_posture"] == "UNRECOVERABLE_BAC_ADOPT_EAC"


def test_evaluate_tcpi_recovery_funds_exhausted_and_no_budget():
    """> AC >= BAC con EV < BAC -> rebase; BAC=0 -> NO_BASELINE_BUDGET."""
    from backend.services.project_evm_service import evaluate_tcpi_recovery_feasibility as eval_fn

    res = eval_fn(bac=1000.0, ev=400.0, ac=1000.0)
    assert res["is_bac_funds_exhausted"] is True
    assert res["is_bac_recoverable"] is False
    assert res["tcpi_bac"] == 999.0
    assert res["efficiency_jump_required"] == 999.0
    assert res["recovery_posture"] == "BAC_FUNDS_EXHAUSTED_REBASELINE_REQUIRED"

    empty = eval_fn(bac=0.0, ev=0.0, ac=0.0)
    assert empty == {
        "cpi": 1.0,
        "tcpi_bac": 1.0,
        "tcpi_eac": 1.0,
        "efficiency_jump_required": 0.0,
        "is_bac_funds_exhausted": False,
        "is_bac_recoverable": True,
        "recovery_posture": "NO_BASELINE_BUDGET",
    }


def test_audit_pmb_undistributed_budget_reconciliation_reconciled():
    """PMB reconciliado con CA + UB == BAC y UB <= 10% -> RECONCILED_PMB_BASELINE."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        audit_pmb_undistributed_budget_reconciliation,
    )

    res = audit_pmb_undistributed_budget_reconciliation(
        bac=100000.0,
        control_accounts_total=94000.0,
        undistributed_budget=6000.0,
        max_ub_share_pct=10.0,
        tolerance=1.0,
    )
    assert res == {
        "allocated_pmb_total": 100000.0,
        "reconciliation_discrepancy": 0.0,
        "ub_share_pct": 6.0,
        "has_negative_bucket": False,
        "is_pmb_reconciled": True,
        "pmb_posture": "RECONCILED_PMB_BASELINE",
    }
    assert (
        ProjectEVMService.audit_pmb_undistributed_budget_reconciliation(
            bac=100000.0,
            control_accounts_total=94000.0,
            undistributed_budget=6000.0,
        )["pmb_posture"]
        == "RECONCILED_PMB_BASELINE"
    )


def test_audit_pmb_undistributed_budget_reconciliation_mismatch():
    """Descuadre entre BAC y CA + UB mayor a tolerance -> PMB_BAC_RECONCILIATION_MISMATCH."""
    from backend.services.project_evm_service import (
        audit_pmb_undistributed_budget_reconciliation,
    )

    res = audit_pmb_undistributed_budget_reconciliation(
        bac=100000.0,
        control_accounts_total=85000.0,
        undistributed_budget=5000.0,
        tolerance=1.0,
    )
    assert res["allocated_pmb_total"] == 90000.0
    assert res["reconciliation_discrepancy"] == 10000.0
    assert res["ub_share_pct"] == 5.0
    assert res["is_pmb_reconciled"] is False
    assert res["pmb_posture"] == "PMB_BAC_RECONCILIATION_MISMATCH"


def test_audit_pmb_undistributed_budget_reconciliation_excessive_ub_and_negative_bucket():
    """UB > 10% -> EXCESSIVE_UNDISTRIBUTED_BUDGET_HOLDING; bucket negativo -> NEGATIVE_BUDGET_BUCKET_ERROR."""
    from backend.services.project_evm_service import (
        audit_pmb_undistributed_budget_reconciliation,
    )

    res_ub = audit_pmb_undistributed_budget_reconciliation(
        bac=100000.0,
        control_accounts_total=80000.0,
        undistributed_budget=20000.0,
        max_ub_share_pct=10.0,
    )
    assert res_ub["reconciliation_discrepancy"] == 0.0
    assert res_ub["ub_share_pct"] == 20.0
    assert res_ub["is_pmb_reconciled"] is False
    assert res_ub["pmb_posture"] == "EXCESSIVE_UNDISTRIBUTED_BUDGET_HOLDING"

    res_neg = audit_pmb_undistributed_budget_reconciliation(
        bac=100000.0,
        control_accounts_total=105000.0,
        undistributed_budget=-5000.0,
    )
    assert res_neg["has_negative_bucket"] is True
    assert res_neg["is_pmb_reconciled"] is False
    assert res_neg["pmb_posture"] == "NEGATIVE_BUDGET_BUCKET_ERROR"


def test_audit_pmb_undistributed_budget_reconciliation_no_pmb_configured():
    """Sin PMB configurado (0, 0, 0) -> NO_PMB_CONFIGURED e is_pmb_reconciled=True."""
    from backend.services.project_evm_service import (
        audit_pmb_undistributed_budget_reconciliation,
    )

    res = audit_pmb_undistributed_budget_reconciliation(
        bac=0.0, control_accounts_total=0.0, undistributed_budget=0.0
    )
    assert res == {
        "allocated_pmb_total": 0.0,
        "reconciliation_discrepancy": 0.0,
        "ub_share_pct": 0.0,
        "has_negative_bucket": False,
        "is_pmb_reconciled": True,
        "pmb_posture": "NO_PMB_CONFIGURED",
    }


def test_evaluate_earned_schedule_performance_spi_time_on_time_and_ahead():
    """SPI(t) en [0.95, 1.05] -> ON_TIME_EARNED_SCHEDULE; SPI(t) > 1.05 -> AHEAD_OF_PLANNED_SCHEDULE."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_earned_schedule_performance,
    )

    curve = [100.0, 200.0, 300.0, 400.0, 500.0]
    res_on = evaluate_earned_schedule_performance(
        earned_value=300.0,
        actual_time_periods=3.0,
        cumulative_pv_curve=curve,
    )
    assert res_on == {
        "earned_schedule": 3.0,
        "actual_time_periods": 3.0,
        "sv_time": 0.0,
        "spi_time": 1.0,
        "planned_duration": 5,
        "estimated_duration_at_completion": 5.0,
        "is_on_time_trajectory": True,
        "es_posture": "ON_TIME_EARNED_SCHEDULE",
    }

    res_ahead = ProjectEVMService.evaluate_earned_schedule_performance(
        earned_value=350.0,
        actual_time_periods=3.0,
        cumulative_pv_curve=curve,
    )
    assert res_ahead["earned_schedule"] == 3.5
    assert res_ahead["sv_time"] == 0.5
    assert res_ahead["spi_time"] == 1.1667
    assert res_ahead["is_on_time_trajectory"] is True
    assert res_ahead["es_posture"] == "AHEAD_OF_PLANNED_SCHEDULE"


def test_evaluate_earned_schedule_performance_spi_time_moderate_delay():
    """0.85 <= SPI(t) < 0.95 -> MODERATE_SCHEDULE_DELAY."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_performance,
    )

    res = evaluate_earned_schedule_performance(
        earned_value=360.0,
        actual_time_periods=4.0,
        cumulative_pv_curve=[100.0, 200.0, 300.0, 400.0, 500.0],
    )
    assert res["earned_schedule"] == 3.6
    assert res["sv_time"] == -0.4
    assert res["spi_time"] == 0.9
    assert res["planned_duration"] == 5
    assert res["estimated_duration_at_completion"] == 5.56
    assert res["is_on_time_trajectory"] is False
    assert res["es_posture"] == "MODERATE_SCHEDULE_DELAY"


def test_evaluate_earned_schedule_performance_spi_time_late_project_slippage():
    """Proyecto vencido donde EV == BAC pero AT > PD -> SPI(t) < 0.85 CRITICAL_SCHEDULE_SLIPPAGE."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_performance,
    )

    res = evaluate_earned_schedule_performance(
        earned_value=500.0,
        actual_time_periods=7.0,
        cumulative_pv_curve=[100.0, 200.0, 300.0, 400.0, 500.0],
    )
    assert res["earned_schedule"] == 5.0
    assert res["sv_time"] == -2.0
    assert res["spi_time"] == 0.7143
    assert res["estimated_duration_at_completion"] == 7.0
    assert res["is_on_time_trajectory"] is False
    assert res["es_posture"] == "CRITICAL_SCHEDULE_SLIPPAGE"


def test_evaluate_earned_schedule_performance_spi_time_insufficient_baseline():
    """Curva vacía o actual_time_periods <= 0 -> INSUFFICIENT_PV_BASELINE_CURVE."""
    from backend.services.project_evm_service import (
        evaluate_earned_schedule_performance,
    )

    for ev, at, curve in [(100.0, 2.0, None), (100.0, 2.0, []), (100.0, 0.0, [100.0, 200.0])]:
        res = evaluate_earned_schedule_performance(
            earned_value=ev,
            actual_time_periods=at,
            cumulative_pv_curve=curve,
        )
        assert res["earned_schedule"] == 0.0
        assert res["sv_time"] == 0.0
        assert res["spi_time"] == 0.0
        assert res["estimated_duration_at_completion"] == 0.0
        assert res["is_on_time_trajectory"] is False
        assert res["es_posture"] == "INSUFFICIENT_PV_BASELINE_CURVE"


def test_audit_eac_forecast_optimism_bias_conservative_and_credible():
    """EAC gerencial >= statistical_floor -> CONSERVATIVE_COMPOSITE_ALIGNED; brecha <= max_optimism_gap_pct -> CREDIBLE_EAC_FORECAST."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        audit_eac_forecast_optimism_bias,
    )

    # BAC=100k, EV=40k, AC=50k (CPI=0.8), PV=50k (SPI=0.8) -> CPI*SPI=0.64
    # eac_atypical = 50k + 60k = 110k
    # eac_cpi = 100k / 0.8 = 125k
    # eac_composite = 50k + 60k / 0.64 = 143750.0 (statistical_floor = 143750.0)
    res_cons = audit_eac_forecast_optimism_bias(
        bac=100000.0,
        ev=40000.0,
        ac=50000.0,
        pv=50000.0,
        manager_bottom_up_eac=145000.0,
        max_optimism_gap_pct=10.0,
    )
    assert res_cons == {
        "eac_atypical": 110000.0,
        "eac_cpi": 125000.0,
        "eac_composite": 143750.0,
        "manager_eac": 145000.0,
        "optimism_gap_pct": 0.0,
        "is_forecast_credible": True,
        "forecast_posture": "CONSERVATIVE_COMPOSITE_ALIGNED",
    }
    assert (
        ProjectEVMService.audit_eac_forecast_optimism_bias(
            bac=100000.0,
            ev=40000.0,
            ac=50000.0,
            pv=50000.0,
            manager_bottom_up_eac=145000.0,
        )
        == res_cons
    )

    res_cred = audit_eac_forecast_optimism_bias(
        bac=100000.0,
        ev=40000.0,
        ac=50000.0,
        pv=50000.0,
        manager_bottom_up_eac=135000.0,
        max_optimism_gap_pct=10.0,
    )
    assert res_cred["optimism_gap_pct"] == 6.09
    assert res_cred["is_forecast_credible"] is True
    assert res_cred["forecast_posture"] == "CREDIBLE_EAC_FORECAST"


def test_audit_eac_forecast_optimism_bias_managerial_optimism_alert():
    """Brecha de optimismo > max_optimism_gap_pct -> MANAGERIAL_OPTIMISM_BIAS_ALERT."""
    from backend.services.project_evm_service import audit_eac_forecast_optimism_bias

    res = audit_eac_forecast_optimism_bias(
        bac=100000.0,
        ev=40000.0,
        ac=50000.0,
        pv=50000.0,
        manager_bottom_up_eac=112000.0,
        max_optimism_gap_pct=10.0,
    )
    assert res["eac_composite"] == 143750.0
    assert res["optimism_gap_pct"] == 22.09
    assert res["is_forecast_credible"] is False
    assert res["forecast_posture"] == "MANAGERIAL_OPTIMISM_BIAS_ALERT"


def test_audit_eac_forecast_optimism_bias_below_actual_cost():
    """manager_bottom_up_eac < AC -> UNREALISTIC_BELOW_ACTUAL_COST."""
    from backend.services.project_evm_service import audit_eac_forecast_optimism_bias

    res = audit_eac_forecast_optimism_bias(
        bac=100000.0,
        ev=50000.0,
        ac=65000.0,
        pv=50000.0,
        manager_bottom_up_eac=60000.0,
    )
    assert res["manager_eac"] == 60000.0
    assert res["is_forecast_credible"] is False
    assert res["forecast_posture"] == "UNREALISTIC_BELOW_ACTUAL_COST"


def test_audit_eac_forecast_optimism_bias_insufficient_evm_data():
    """BAC, EV o AC <= 0 -> INSUFFICIENT_EVM_DATA."""
    from backend.services.project_evm_service import audit_eac_forecast_optimism_bias

    for b_val, ev_val, ac_val in [(0.0, 50.0, 50.0), (100.0, 0.0, 50.0), (100.0, 50.0, 0.0)]:
        res = audit_eac_forecast_optimism_bias(
            bac=b_val,
            ev=ev_val,
            ac=ac_val,
            pv=50.0,
            manager_bottom_up_eac=95.0,
        )
        assert res == {
            "eac_atypical": 0.0,
            "eac_cpi": 0.0,
            "eac_composite": 0.0,
            "manager_eac": 95.0,
            "optimism_gap_pct": 0.0,
            "is_forecast_credible": False,
            "forecast_posture": "INSUFFICIENT_EVM_DATA",
        }


def test_audit_work_package_evmt_governance_governed():
    """> Fórmulas con tope respetado, LOE dentro del share y paquetes cortos -> GOVERNED."""
    from backend.services.project_evm_service import (
        audit_work_package_evmt_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "WP-1",
                "budget": 8000.0,
                "evmt": "0_100",
                "status": "COMPLETED",
                "claimed_pct": 100.0,
                "duration_periods": 2,
            },
            {
                "id": "WP-2",
                "budget": 6000.0,
                "evmt": "50_50",
                "claimed_pct": 50.0,
                "duration_periods": 1,
            },
            {
                "id": "WP-3",
                "budget": 4000.0,
                "evmt": "20_80",
                "claimed_pct": 20.0,
            },
            {
                "id": "WP-4",
                "budget": 2000.0,
                "evmt": "PERCENT_COMPLETE",
                "claimed_pct": 75.0,
                "duration_periods": 5,
            },
        ],
        max_loe_share_pct=15.0,
    )
    assert res["total_work_packages"] == 4
    assert res["loe_share_pct"] == 0.0
    assert res["formula_cap_violation_ids"] == []
    assert res["long_duration_fixed_formula_ids"] == []
    assert res["is_evmt_governed"] is True
    assert res["evmt_posture"] == "GOVERNED_EVMT_BASELINE"


def test_audit_work_package_evmt_governance_cap_violation():
    """> Paquete IN_PROGRESS con fórmula fija reclamando más del tope -> CAP violation."""
    from backend.services.project_evm_service import (
        audit_work_package_evmt_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "WP-OK",
                "evmt": "0_100",
                "claimed_pct": 0.0,
                "duration_periods": 2,
            },
            {
                "id": "WP-GREEDY-50",
                "budget": 1000.0,
                "evmt": "50_50",
                "claimed_pct": 75.0,
            },
            {
                "id": "WP-GREEDY-20",
                "budget": 2000.0,
                "evmt": "20_80",
                "claimed_pct": 80.0,
            },
        ]
    )
    assert res["total_work_packages"] == 3
    assert res["formula_cap_violation_ids"] == ["WP-GREEDY-50", "WP-GREEDY-20"]
    assert res["long_duration_fixed_formula_ids"] == []
    assert res["is_evmt_governed"] is False
    assert res["evmt_posture"] == "FIXED_FORMULA_PERCENT_CAP_VIOLATION"


def test_audit_work_package_evmt_governance_long_duration_and_loe():
    """> Fórmula fija en paquete largo y share LOE excesivo (precedencia cap)."""
    from backend.services.project_evm_service import (
        audit_work_package_evmt_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "WP-LONG",
                "budget": 5000.0,
                "evmt": "0_100",
                "claimed_pct": 0.0,
                "duration_periods": 6,
            },
            {
                "id": "WP-LOE",
                "budget": 45000.0,
                "evmt": "LEVEL_OF_EFFORT",
            },
        ],
        max_loe_share_pct=15.0,
    )
    assert res["total_work_packages"] == 2
    # LOE: 45000/50000 = 90.0% > 15%.
    assert res["loe_share_pct"] == 90.0
    assert res["long_duration_fixed_formula_ids"] == ["WP-LONG"]
    assert res["formula_cap_violation_ids"] == []
    assert res["is_evmt_governed"] is False
    assert res["evmt_posture"] == "FIXED_FORMULA_ON_LONG_WORK_PACKAGE"


def test_audit_work_package_evmt_governance_empty_or_none():
    """None, lista vacía, entradas no-dict o sin wp_id -> NO_WORK_PACKAGES."""
    from backend.services.project_evm_service import (
        audit_work_package_evmt_governance as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, {"budget": 100.0}]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_work_packages": 0,
            "loe_share_pct": 0.0,
            "formula_cap_violation_ids": [],
            "long_duration_fixed_formula_ids": [],
            "is_evmt_governed": False,
            "evmt_posture": "NO_WORK_PACKAGES",
        }


def test_evaluate_management_reserve_ceiling_utilization_governed_and_high_depletion():
    """Retiros aprobados por Sponsor y EAC dentro del techo -> GOVERNED_MANAGEMENT_RESERVE_POSTURE o HIGH_MANAGEMENT_RESERVE_DEPLETION."""
    import backend.services.project_evm_service as evm_module
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_management_reserve_ceiling_utilization,
    )

    drawdowns = [
        {"id": "DD-01", "amount": 5000.0, "sponsor_approved": True},
        {"drawdown_id": "DD-02", "amount": 3000.0, "sponsor_approved": True},
    ]
    res = evaluate_management_reserve_ceiling_utilization(
        original_bac=100000.0,
        initial_management_reserve=20000.0,
        mr_drawdowns=drawdowns,
        current_eac=110000.0,
    )
    assert res == {
        "total_project_budget": 120000.0,
        "current_bac": 108000.0,
        "remaining_management_reserve": 12000.0,
        "mr_utilization_pct": 40.0,
        "unauthorized_drawdown_ids": [],
        "exceeds_project_budget_ceiling": False,
        "is_mr_governance_sound": True,
        "mr_posture": "GOVERNED_MANAGEMENT_RESERVE_POSTURE",
    }
    assert (
        ProjectEVMService.evaluate_management_reserve_ceiling_utilization(
            original_bac=100000.0,
            initial_management_reserve=20000.0,
            mr_drawdowns=drawdowns,
            current_eac=110000.0,
        )
        == res
    )
    assert "evaluate_management_reserve_ceiling_utilization" in evm_module.__all__

    res_high = evaluate_management_reserve_ceiling_utilization(
        original_bac=100000.0,
        initial_management_reserve=20000.0,
        mr_drawdowns=[{"id": "DD-BIG", "amount": 16000.0, "sponsor_approved": True}],
        current_eac=118000.0,
    )
    assert res_high["mr_utilization_pct"] == 80.0
    assert res_high["is_mr_governance_sound"] is True
    assert res_high["mr_posture"] == "HIGH_MANAGEMENT_RESERVE_DEPLETION"


def test_evaluate_management_reserve_ceiling_utilization_unauthorized_drawdown():
    """Retiro de MR sin sponsor_approved -> UNAUTHORIZED_MANAGEMENT_RESERVE_DRAWDOWN."""
    from backend.services.project_evm_service import (
        evaluate_management_reserve_ceiling_utilization,
    )

    res = evaluate_management_reserve_ceiling_utilization(
        original_bac=100000.0,
        initial_management_reserve=15000.0,
        mr_drawdowns=[
            {"id": "DD-UNAUTH", "amount": 4000.0, "sponsor_approved": False},
        ],
        current_eac=105000.0,
    )
    assert res["unauthorized_drawdown_ids"] == ["DD-UNAUTH"]
    assert res["is_mr_governance_sound"] is False
    assert res["mr_posture"] == "UNAUTHORIZED_MANAGEMENT_RESERVE_DRAWDOWN"


def test_evaluate_management_reserve_ceiling_utilization_ceiling_breached():
    """Retiros > MR inicial o EAC > presupuesto total -> PROJECT_BUDGET_CEILING_BREACHED."""
    from backend.services.project_evm_service import (
        evaluate_management_reserve_ceiling_utilization,
    )

    res = evaluate_management_reserve_ceiling_utilization(
        original_bac=100000.0,
        initial_management_reserve=10000.0,
        mr_drawdowns=[{"id": "DD-1", "amount": 5000.0, "sponsor_approved": True}],
        current_eac=115000.0,
    )
    assert res["total_project_budget"] == 110000.0
    assert res["exceeds_project_budget_ceiling"] is True
    assert res["is_mr_governance_sound"] is False
    assert res["mr_posture"] == "PROJECT_BUDGET_CEILING_BREACHED"


def test_evaluate_management_reserve_ceiling_utilization_no_cost_baseline():
    """original_bac <= 0 -> NO_COST_BASELINE."""
    from backend.services.project_evm_service import (
        evaluate_management_reserve_ceiling_utilization,
    )

    for bac_val in (0.0, -5000.0):
        res = evaluate_management_reserve_ceiling_utilization(
            original_bac=bac_val,
            initial_management_reserve=10000.0,
        )
        assert res == {
            "total_project_budget": 0.0,
            "current_bac": 0.0,
            "remaining_management_reserve": 0.0,
            "mr_utilization_pct": 0.0,
            "unauthorized_drawdown_ids": [],
            "exceeds_project_budget_ceiling": False,
            "is_mr_governance_sound": False,
            "mr_posture": "NO_COST_BASELINE",
        }


def test_evaluate_evm_funding_runway_exhaustion_healthy_runway():
    """Runway estimado supera períodos restantes con margen >= min_safety_margin_periods -> HEALTHY_RUNWAY."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_funding_runway_exhaustion,
    )

    res = evaluate_evm_funding_runway_exhaustion(
        total_authorized_funding=100000.0,
        cumulative_actual_cost=40000.0,
        periodic_ac_burn_series=[9000.0, 11000.0, 10000.0, 0.0, -500.0],
        remaining_schedule_periods=4,
        min_safety_margin_periods=1.0,
    )
    assert res == {
        "remaining_funding": 60000.0,
        "is_overdrawn": False,
        "average_periodic_burn": 10000.0,
        "peak_periodic_burn": 11000.0,
        "estimated_runway_periods": 6.0,
        "runway_surplus_periods": 2.0,
        "runway_status": "HEALTHY_RUNWAY",
        "is_runway_sufficient": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_funding_runway_exhaustion(
            total_authorized_funding=100000.0,
            cumulative_actual_cost=40000.0,
            periodic_ac_burn_series=[9000.0, 11000.0, 10000.0],
            remaining_schedule_periods=4,
            min_safety_margin_periods=1.0,
        )
        == res
    )


def test_evaluate_evm_funding_runway_exhaustion_tight_and_shortfall_risk():
    """Superávit < margen -> TIGHT_RUNWAY; runway < períodos restantes -> SHORTFALL_RISK."""
    from backend.services.project_evm_service import (
        evaluate_evm_funding_runway_exhaustion,
    )

    res_tight = evaluate_evm_funding_runway_exhaustion(
        total_authorized_funding=100000.0,
        cumulative_actual_cost=55000.0,
        periodic_ac_burn_series=[10000.0, 10000.0],
        remaining_schedule_periods=4,
        min_safety_margin_periods=1.0,
    )
    assert res_tight["estimated_runway_periods"] == 4.5
    assert res_tight["runway_surplus_periods"] == 0.5
    assert res_tight["runway_status"] == "TIGHT_RUNWAY"
    assert res_tight["is_runway_sufficient"] is False

    res_short = evaluate_evm_funding_runway_exhaustion(
        total_authorized_funding=100000.0,
        cumulative_actual_cost=70000.0,
        periodic_ac_burn_series=[10000.0, 10000.0],
        remaining_schedule_periods=4,
        min_safety_margin_periods=1.0,
    )
    assert res_short["estimated_runway_periods"] == 3.0
    assert res_short["runway_surplus_periods"] == -1.0
    assert res_short["runway_status"] == "SHORTFALL_RISK"
    assert res_short["is_runway_sufficient"] is False


def test_evaluate_evm_funding_runway_exhaustion_overdrawn_or_exhausted():
    """AC > financiamiento autorizado o fondo restante 0 con períodos > 0 -> EXHAUSTED."""
    from backend.services.project_evm_service import (
        evaluate_evm_funding_runway_exhaustion,
    )

    res_over = evaluate_evm_funding_runway_exhaustion(
        total_authorized_funding=80000.0,
        cumulative_actual_cost=85000.0,
        periodic_ac_burn_series=[15000.0, 20000.0],
        remaining_schedule_periods=2,
    )
    assert res_over["remaining_funding"] == 0.0
    assert res_over["is_overdrawn"] is True
    assert res_over["runway_status"] == "EXHAUSTED"
    assert res_over["is_runway_sufficient"] is False

    res_zero = evaluate_evm_funding_runway_exhaustion(
        total_authorized_funding=80000.0,
        cumulative_actual_cost=80000.0,
        periodic_ac_burn_series=[10000.0],
        remaining_schedule_periods=1,
    )
    assert res_zero["is_overdrawn"] is False
    assert res_zero["runway_status"] == "EXHAUSTED"
    assert res_zero["is_runway_sufficient"] is False


def test_evaluate_evm_funding_runway_exhaustion_no_burn_series():
    """Sin quemas positivas y con fondos disponibles -> estimated_runway_periods igual a períodos restantes."""
    from backend.services.project_evm_service import (
        evaluate_evm_funding_runway_exhaustion,
    )

    res = evaluate_evm_funding_runway_exhaustion(
        total_authorized_funding=50000.0,
        cumulative_actual_cost=0.0,
        periodic_ac_burn_series=None,
        remaining_schedule_periods=5,
        min_safety_margin_periods=0.0,
    )
    assert res == {
        "remaining_funding": 50000.0,
        "is_overdrawn": False,
        "average_periodic_burn": 0.0,
        "peak_periodic_burn": 0.0,
        "estimated_runway_periods": 5.0,
        "runway_surplus_periods": 0.0,
        "runway_status": "HEALTHY_RUNWAY",
        "is_runway_sufficient": True,
    }


def test_evaluate_evm_joint_cost_schedule_index_green_and_healthy():
    """CSI >= 0.90 y TCPI <= 1.10 -> csi_zone GREEN, requires_formal_rebaseline False, is_jointly_healthy True."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_joint_cost_schedule_index,
    )

    res = evaluate_evm_joint_cost_schedule_index(
        cpi=0.98,
        spi=0.95,
        percent_complete=35.0,
        tcpi_bac=1.02,
    )
    assert res == {
        "csi": 0.931,
        "tradeoff_imbalance": 0.03,
        "csi_zone": "GREEN",
        "is_past_early_stabilization_point": True,
        "requires_formal_rebaseline": False,
        "is_jointly_healthy": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_joint_cost_schedule_index(
            cpi=0.98,
            spi=0.95,
            percent_complete=35.0,
            tcpi_bac=1.02,
        )
        == res
    )


def test_evaluate_evm_joint_cost_schedule_index_yellow_early_vs_post_stabilization():
    """CSI entre 0.80 y 0.85: antes de 20% de avance no exige rebaseline; después de 20% exige rebaseline."""
    from backend.services.project_evm_service import (
        evaluate_evm_joint_cost_schedule_index,
    )

    res_early = evaluate_evm_joint_cost_schedule_index(
        cpi=0.90,
        spi=0.92,
        percent_complete=15.0,
        tcpi_bac=1.05,
    )
    assert res_early["csi"] == 0.828
    assert res_early["csi_zone"] == "YELLOW"
    assert res_early["is_past_early_stabilization_point"] is False
    assert res_early["requires_formal_rebaseline"] is False
    assert res_early["is_jointly_healthy"] is False

    res_late = evaluate_evm_joint_cost_schedule_index(
        cpi=0.90,
        spi=0.92,
        percent_complete=25.0,
        tcpi_bac=1.05,
    )
    assert res_late["csi"] == 0.828
    assert res_late["csi_zone"] == "YELLOW"
    assert res_late["is_past_early_stabilization_point"] is True
    assert res_late["requires_formal_rebaseline"] is True
    assert res_late["is_jointly_healthy"] is False


def test_evaluate_evm_joint_cost_schedule_index_red_zone():
    """CSI < 0.80 -> csi_zone RED, requires_formal_rebaseline True."""
    from backend.services.project_evm_service import (
        evaluate_evm_joint_cost_schedule_index,
    )

    res = evaluate_evm_joint_cost_schedule_index(
        cpi=0.80,
        spi=0.90,
        percent_complete=10.0,
        tcpi_bac=1.08,
    )
    assert res == {
        "csi": 0.72,
        "tradeoff_imbalance": 0.1,
        "csi_zone": "RED",
        "is_past_early_stabilization_point": False,
        "requires_formal_rebaseline": True,
        "is_jointly_healthy": False,
    }


def test_evaluate_evm_joint_cost_schedule_index_high_tcpi_triggers_rebaseline():
    """Incluso con CSI >= 0.90, si tcpi_bac > 1.10 -> requires_formal_rebaseline True e is_jointly_healthy False."""
    from backend.services.project_evm_service import (
        evaluate_evm_joint_cost_schedule_index,
    )

    res = evaluate_evm_joint_cost_schedule_index(
        cpi=0.85,
        spi=1.10,
        percent_complete=60.0,
        tcpi_bac=1.18,
    )
    assert res["csi"] == 0.935
    assert res["csi_zone"] == "GREEN"
    assert res["tradeoff_imbalance"] == 0.25
    assert res["requires_formal_rebaseline"] is True
    assert res["is_jointly_healthy"] is False


def test_evaluate_evm_earned_schedule_tspi_feasibility_on_track_and_completed():
    """Verifica posturas on_track y completed con is_recovery_feasible=True."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_earned_schedule_tspi_feasibility,
    )

    on_track_metrics = {
        "planned_duration_days": 100.0,
        "actual_time_days": 50.0,
        "earned_schedule_days": 50.0,
        "deadline_extension_days": 0.0,
    }
    res_on_track = evaluate_evm_earned_schedule_tspi_feasibility(on_track_metrics)
    assert res_on_track == {
        "spi_t": 1.0,
        "sv_t_days": 0.0,
        "tspi_pd": 1.0,
        "tspi_ed": 1.0,
        "ieac_t_days": 100.0,
        "schedule_posture": "on_track",
        "is_recovery_feasible": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_earned_schedule_tspi_feasibility(
            on_track_metrics
        )
        == res_on_track
    )

    res_completed = evaluate_evm_earned_schedule_tspi_feasibility(
        {
            "planned_duration_days": 100.0,
            "actual_time_days": 105.0,
            "earned_schedule_days": 100.0,
        }
    )
    assert res_completed["schedule_posture"] == "completed"
    assert res_completed["tspi_pd"] == 0.0
    assert res_completed["is_recovery_feasible"] is True


def test_evaluate_evm_earned_schedule_tspi_feasibility_recoverable_baseline_and_extension():
    """Verifica recoverable_within_baseline (tspi_pd <= 1.10) y recoverable_with_extension (tspi_ed <= 1.10)."""
    from backend.services.project_evm_service import (
        evaluate_evm_earned_schedule_tspi_feasibility,
    )

    res_baseline = evaluate_evm_earned_schedule_tspi_feasibility(
        {
            "planned_duration_days": 100.0,
            "actual_time_days": 50.0,
            "earned_schedule_days": 46.0,
        }
    )
    assert res_baseline["spi_t"] == 0.92
    assert res_baseline["tspi_pd"] == 1.08
    assert res_baseline["schedule_posture"] == "recoverable_within_baseline"
    assert res_baseline["is_recovery_feasible"] is True

    res_ext = evaluate_evm_earned_schedule_tspi_feasibility(
        {
            "planned_duration_days": 100.0,
            "actual_time_days": 60.0,
            "earned_schedule_days": 50.0,
            "deadline_extension_days": 10.0,
        }
    )
    assert res_ext["tspi_pd"] == 1.25
    assert res_ext["tspi_ed"] == 1.0
    assert res_ext["schedule_posture"] == "recoverable_with_extension"
    assert res_ext["is_recovery_feasible"] is True


def test_evaluate_evm_earned_schedule_tspi_feasibility_unrecoverable_slippage():
    """Cuando tspi_pd > 1.10 y tspi_ed > 1.10 reporta unrecoverable_slippage e is_recovery_feasible=False."""
    from backend.services.project_evm_service import (
        evaluate_evm_earned_schedule_tspi_feasibility,
    )

    res = evaluate_evm_earned_schedule_tspi_feasibility(
        {
            "planned_duration_days": 100.0,
            "actual_time_days": 80.0,
            "earned_schedule_days": 50.0,
            "deadline_extension_days": 5.0,
        }
    )
    assert res == {
        "spi_t": 0.625,
        "sv_t_days": -30.0,
        "tspi_pd": 2.5,
        "tspi_ed": 2.0,
        "ieac_t_days": 160.0,
        "schedule_posture": "unrecoverable_slippage",
        "is_recovery_feasible": False,
    }


def test_evaluate_evm_earned_schedule_tspi_feasibility_invalid_inputs():
    """Entradas no-Mapping o con duraciones inválidas devuelven schedule_posture=invalid_inputs."""
    from backend.services.project_evm_service import (
        evaluate_evm_earned_schedule_tspi_feasibility,
    )

    for bad_payload in (
        None,
        {},
        {"planned_duration_days": 0.0, "actual_time_days": 10.0, "earned_schedule_days": 5.0},
        {"planned_duration_days": 100.0, "actual_time_days": -1.0, "earned_schedule_days": 5.0},
    ):
        assert evaluate_evm_earned_schedule_tspi_feasibility(bad_payload) == {  # type: ignore[arg-type]
            "spi_t": 0.0,
            "sv_t_days": 0.0,
            "tspi_pd": 0.0,
            "tspi_ed": 0.0,
            "ieac_t_days": 0.0,
            "schedule_posture": "invalid_inputs",
            "is_recovery_feasible": False,
        }


def test_evaluate_evm_vac_rebaseline_threshold_within_tolerance():
    """VAC dentro del umbral y TCPI <= 1.10 retorna within_tolerance y requires_ccb_rebaseline=False."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_vac_rebaseline_threshold,
    )

    metrics = {
        "bac": 100000.0,
        "ev": 50000.0,
        "ac": 52000.0,
        "eac": 104000.0,
        "tolerance_threshold_pct": 10.0,
    }
    res = evaluate_evm_vac_rebaseline_threshold(metrics)
    assert res == {
        "bac": 100000.0,
        "eac": 104000.0,
        "vac": -4000.0,
        "vac_pct": -4.0,
        "tcpi_bac": 1.0417,
        "rebaseline_status": "within_tolerance",
        "requires_ccb_rebaseline": False,
    }
    assert ProjectEVMService.evaluate_evm_vac_rebaseline_threshold(metrics) == res


def test_evaluate_evm_vac_rebaseline_threshold_watch_threshold():
    """Overrun <= tolerancia pero 1.10 < TCPI <= 1.20 retorna watch_threshold."""
    from backend.services.project_evm_service import (
        evaluate_evm_vac_rebaseline_threshold,
    )

    res = evaluate_evm_vac_rebaseline_threshold(
        {
            "bac": 1000.0,
            "ev": 500.0,
            "ac": 560.0,
            "eac": 1080.0,
            "tolerance_threshold_pct": 10.0,
        }
    )
    assert res == {
        "bac": 1000.0,
        "eac": 1080.0,
        "vac": -80.0,
        "vac_pct": -8.0,
        "tcpi_bac": 1.1364,
        "rebaseline_status": "watch_threshold",
        "requires_ccb_rebaseline": False,
    }


def test_evaluate_evm_vac_rebaseline_threshold_ccb_rebaseline_required():
    """Sobrecosto > tolerancia o TCPI > 1.20 dispara ccb_rebaseline_required y requires_ccb_rebaseline=True."""
    from backend.services.project_evm_service import (
        evaluate_evm_vac_rebaseline_threshold,
    )

    res_overrun = evaluate_evm_vac_rebaseline_threshold(
        {
            "bac": 1000.0,
            "ev": 400.0,
            "ac": 450.0,
            "eac": 1150.0,
            "tolerance_threshold_pct": 10.0,
        }
    )
    assert res_overrun["vac"] == -150.0
    assert res_overrun["vac_pct"] == -15.0
    assert res_overrun["rebaseline_status"] == "ccb_rebaseline_required"
    assert res_overrun["requires_ccb_rebaseline"] is True

    res_tcpi = evaluate_evm_vac_rebaseline_threshold(
        {
            "bac": 1000.0,
            "ev": 400.0,
            "ac": 550.0,
            "eac": 1050.0,
            "tolerance_threshold_pct": 10.0,
        }
    )
    assert res_tcpi["tcpi_bac"] == 1.3333
    assert res_tcpi["rebaseline_status"] == "ccb_rebaseline_required"
    assert res_tcpi["requires_ccb_rebaseline"] is True


def test_evaluate_evm_vac_rebaseline_threshold_invalid_inputs():
    """Entradas no-Mapping o con BAC/EAC <= 0 devuelven rebaseline_status=invalid_inputs."""
    from backend.services.project_evm_service import (
        evaluate_evm_vac_rebaseline_threshold,
    )

    for bad in (
        None,
        {},
        {"bac": 0.0, "ev": 10.0, "ac": 10.0, "eac": 100.0},
        {"bac": 100.0, "ev": 10.0, "ac": 10.0, "eac": 0.0},
    ):
        assert evaluate_evm_vac_rebaseline_threshold(bad) == {  # type: ignore[arg-type]
            "bac": 0.0,
            "eac": 0.0,
            "vac": 0.0,
            "vac_pct": 0.0,
            "tcpi_bac": 0.0,
            "rebaseline_status": "invalid_inputs",
            "requires_ccb_rebaseline": False,
        }




def test_evaluate_evm_tcpi_eac_vs_bac_divergence_baseline_and_completed():
    """TCPI_BAC dentro del umbral -> baseline_achievable; EV==BAC -> completed."""
    from backend.services.project_evm_service import (
        evaluate_evm_tcpi_eac_vs_bac_divergence as eval_fn,
    )

    res = eval_fn({"bac": 1000.0, "ev": 300.0, "ac": 350.0, "eac": 1100.0})
    # cpi=0.8571; tcpi_bac=700/650=1.0769 (<=1.10); tcpi_eac=700/750=0.9333.
    assert res["tcpi_bac"] == 1.0769
    assert res["tcpi_eac"] == 0.9333
    assert res["tcpi_spread"] == 0.1436
    assert res["cpi"] == 0.8571
    assert res["efficiency_gap_vs_cpi"] == 0.0762
    assert res["divergence_posture"] == "baseline_achievable"
    assert res["is_eac_realistic"] is True

    res_completed = eval_fn(
        {"bac": 1000.0, "ev": 1000.0, "ac": 800.0, "eac": 900.0},
    )
    assert res_completed["tcpi_bac"] == 0.0
    assert res_completed["tcpi_eac"] == 0.0
    assert res_completed["cpi"] == 1.25
    assert res_completed["divergence_posture"] == "completed"
    assert res_completed["is_eac_realistic"] is True


def test_evaluate_evm_tcpi_eac_vs_bac_divergence_rebaselined_aligned():
    """TCPI_BAC > 1.10 pero el EAC reajusta TCPI_EAC <= 1.10 -> rebaselined_aligned."""
    from backend.services.project_evm_service import (
        evaluate_evm_tcpi_eac_vs_bac_divergence as eval_fn,
        ProjectEVMService,
    )

    res = eval_fn({"bac": 1000.0, "ev": 600.0, "ac": 700.0, "eac": 1300.0})
    assert res["tcpi_bac"] == 1.3333
    assert res["tcpi_eac"] == 0.6667
    assert res["tcpi_spread"] == 0.6666
    assert res["cpi"] == 0.8571
    assert res["efficiency_gap_vs_cpi"] == -0.1904
    assert res["divergence_posture"] == "rebaselined_aligned"
    assert res["is_eac_realistic"] is True

    res_static = ProjectEVMService.evaluate_evm_tcpi_eac_vs_bac_divergence(
        {"bac": 1000.0, "ev": 600.0, "ac": 700.0, "eac": 1300.0}
    )
    assert res_static == res


def test_evaluate_evm_tcpi_eac_vs_bac_divergence_unrealistic_eac():
    """TCPI_EAC > 1.20 (y gap > 0.15) o rem_eac <= 0 -> unrealistic_eac."""
    from backend.services.project_evm_service import (
        evaluate_evm_tcpi_eac_vs_bac_divergence as eval_fn,
    )

    res_thin = eval_fn({"bac": 1000.0, "ev": 500.0, "ac": 500.0, "eac": 600.0})
    # cpi=1.0; rem_eac=100 -> tcpi_eac=5.0 > 1.20 y gap=4.0 > 0.15.
    assert res_thin["tcpi_bac"] == 1.0
    assert res_thin["tcpi_eac"] == 5.0
    assert res_thin["efficiency_gap_vs_cpi"] == 4.0
    assert res_thin["divergence_posture"] == "unrealistic_eac"
    assert res_thin["is_eac_realistic"] is False

    res_no_funds = eval_fn({"bac": 1000.0, "ev": 500.0, "ac": 600.0, "eac": 500.0})
    # rem_eac = -100 <= 0 con trabajo pendiente -> tcpi_eac=999.0.
    assert res_no_funds["tcpi_eac"] == 999.0
    assert res_no_funds["tcpi_bac"] == 1.25
    assert res_no_funds["divergence_posture"] == "unrealistic_eac"
    assert res_no_funds["is_eac_realistic"] is False


def test_evaluate_evm_tcpi_eac_vs_bac_divergence_invalid_inputs():
    """None, vacío, bac<=0, eac<=0 o ev/ac negativos -> invalid_inputs."""
    from backend.services.project_evm_service import (
        evaluate_evm_tcpi_eac_vs_bac_divergence as eval_fn,
    )

    invalid_result = {
        "tcpi_bac": 0.0,
        "tcpi_eac": 0.0,
        "tcpi_spread": 0.0,
        "cpi": 0.0,
        "efficiency_gap_vs_cpi": 0.0,
        "divergence_posture": "invalid_inputs",
        "is_eac_realistic": False,
    }

    for payload in (
        None,
        {},
        {"bac": 0.0, "ev": 100.0, "ac": 50.0, "eac": 200.0},
        {"bac": 1000.0, "ev": 100.0, "ac": 50.0, "eac": 0.0},
        {"bac": 1000.0, "ev": -5.0, "ac": 50.0, "eac": 200.0},
        {"bac": 1000.0, "ev": 100.0, "ac": -1.0, "eac": 200.0},
        42,
        "metrics-string",
    ):
        assert eval_fn(payload) == invalid_result  # type: ignore[arg-type]


def test_audit_evm_accrual_method_inflation_bias_sound():
    """Paquetes con método válido, 50/50 de corta duración y percent_complete con evidencia pasan is_accrual_governance_sound=True."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        audit_evm_accrual_method_inflation_bias,
    )

    wps = [
        {
            "wp_id": "WP-01",
            "accrual_method": "50_50",
            "duration_days": 15.0,
            "claimed_ev": 2500.0,
            "bac": 5000.0,
            "objective_evidence_attached": False,
        },
        {
            "wp_id": "WP-02",
            "accrual_method": "percent_complete",
            "duration_days": 45.0,
            "claimed_ev": 6000.0,
            "bac": 10000.0,
            "objective_evidence_attached": True,
        },
        {
            "wp_id": "WP-03",
            "accrual_method": "0_100",
            "duration_days": 10.0,
            "claimed_ev": 3000.0,
            "bac": 3000.0,
            "objective_evidence_attached": True,
        },
    ]
    res = audit_evm_accrual_method_inflation_bias(wps, max_50_50_duration_days=20.0)
    assert res == {
        "total_work_packages": 3,
        "invalid_method_wp_ids": [],
        "long_duration_50_50_wp_ids": [],
        "inflated_or_unsubstantiated_wp_ids": [],
        "is_accrual_governance_sound": True,
    }
    assert (
        ProjectEVMService.audit_evm_accrual_method_inflation_bias(
            wps, max_50_50_duration_days=20.0
        )
        == res
    )


def test_audit_evm_accrual_method_inflation_bias_invalid_method_and_long_50_50():
    """Detecta método de devengo inválido y uso de 50_50 en paquetes que exceden max_50_50_duration_days."""
    from backend.services.project_evm_service import (
        audit_evm_accrual_method_inflation_bias,
    )

    res = audit_evm_accrual_method_inflation_bias(
        [
            {
                "wp_id": "WP-BAD-METH",
                "accrual_method": "subjective_guess",
                "duration_days": 10.0,
                "claimed_ev": 500.0,
                "bac": 1000.0,
            },
            {
                "wp_id": "WP-LONG-5050",
                "accrual_method": "50_50",
                "duration_days": 35.0,
                "claimed_ev": 2000.0,
                "bac": 4000.0,
            },
        ],
        max_50_50_duration_days=20.0,
    )
    assert res == {
        "total_work_packages": 2,
        "invalid_method_wp_ids": ["WP-BAD-METH"],
        "long_duration_50_50_wp_ids": ["WP-LONG-5050"],
        "inflated_or_unsubstantiated_wp_ids": [],
        "is_accrual_governance_sound": False,
    }


def test_audit_evm_accrual_method_inflation_bias_inflated_or_unsubstantiated():
    """Detecta claimed_ev > bac y percent_complete con claimed_ev > 0 sin evidencia objetiva."""
    from backend.services.project_evm_service import (
        audit_evm_accrual_method_inflation_bias,
    )

    res = audit_evm_accrual_method_inflation_bias(
        [
            {
                "wp_id": "WP-OVER-BAC",
                "accrual_method": "weighted_milestones",
                "duration_days": 30.0,
                "claimed_ev": 5500.0,
                "bac": 5000.0,
                "objective_evidence_attached": True,
            },
            {
                "wp_id": "WP-UNSUB-PCT",
                "accrual_method": "percent_complete",
                "duration_days": 25.0,
                "claimed_ev": 1500.0,
                "bac": 5000.0,
                "objective_evidence_attached": False,
            },
        ]
    )
    assert res == {
        "total_work_packages": 2,
        "invalid_method_wp_ids": [],
        "long_duration_50_50_wp_ids": [],
        "inflated_or_unsubstantiated_wp_ids": ["WP-OVER-BAC", "WP-UNSUB-PCT"],
        "is_accrual_governance_sound": False,
    }


def test_audit_evm_accrual_method_inflation_bias_empty_or_invalid():
    """Entrada None, vacía o no secuencial retorna total_work_packages=0 e is_accrual_governance_sound=False."""
    from backend.services.project_evm_service import (
        audit_evm_accrual_method_inflation_bias,
    )

    for payload in (None, [], "invalid", {"wp_id": "WP-1"}, [{"wp_id": "  "}]):
        assert audit_evm_accrual_method_inflation_bias(payload) == {  # type: ignore[arg-type]
            "total_work_packages": 0,
            "invalid_method_wp_ids": [],
            "long_duration_50_50_wp_ids": [],
            "inflated_or_unsubstantiated_wp_ids": [],
            "is_accrual_governance_sound": False,
        }


def test_evaluate_evm_critical_path_drag_decoupling_healthy_aligned():
    """Cronograma alineado con SPI >= 1.0, sin atraso en ruta crítica y alta participación EV crítica -> healthy."""
    from backend.services.project_evm_service import (
        evaluate_evm_critical_path_drag_decoupling,
    )

    res = evaluate_evm_critical_path_drag_decoupling(
        spi=1.03,
        sv_amount=5000.0,
        critical_path_slip_days=0.0,
        critical_path_ev_share_pct=65.0,
        non_critical_float_consumed_days=1.5,
    )
    assert res["spi"] == 1.03
    assert res["sv_amount"] == 5000.0
    assert res["critical_path_slip_days"] == 0.0
    assert res["critical_path_ev_share_pct"] == 65.0
    assert res["non_critical_float_consumed_days"] == 1.5
    assert res["false_schedule_optimism_detected"] is False
    assert res["cp_ev_dilution_detected"] is False
    assert res["float_exhaustion_warning"] is False
    assert res["is_schedule_aligned"] is True
    assert res["status"] == "healthy"
    assert res["violations"] == []


def test_evaluate_evm_critical_path_drag_decoupling_false_schedule_optimism_critical():
    """SPI >= 1.0 con deslizamiento en ruta crítica dispara false_schedule_optimism_detected=True y status='critical'."""
    from backend.services.project_evm_service import (
        evaluate_evm_critical_path_drag_decoupling,
    )

    res = evaluate_evm_critical_path_drag_decoupling(
        spi=1.05,
        sv_amount=12000.0,
        critical_path_slip_days=4.0,
        critical_path_ev_share_pct=55.0,
        non_critical_float_consumed_days=2.0,
        max_acceptable_cp_slip_days=0.0,
    )
    assert res["false_schedule_optimism_detected"] is True
    assert res["cp_ev_dilution_detected"] is False
    assert res["is_schedule_aligned"] is False
    assert res["status"] == "critical"
    assert len(res["violations"]) >= 1
    assert len(res["recommendations"]) >= 1


def test_evaluate_evm_critical_path_drag_decoupling_cp_ev_dilution_warning():
    """Dilución de EV en ruta crítica con atraso moderado (SPI < 1.0 y slip <= max + 5) retorna cp_ev_dilution_detected=True y status='warning'."""
    from backend.services.project_evm_service import (
        evaluate_evm_critical_path_drag_decoupling,
    )

    res = evaluate_evm_critical_path_drag_decoupling(
        spi=0.96,
        sv_amount=-3200.0,
        critical_path_slip_days=2.0,
        critical_path_ev_share_pct=25.0,
        non_critical_float_consumed_days=6.0,
        max_acceptable_cp_slip_days=0.0,
        min_cp_ev_share_pct=40.0,
    )
    assert res["false_schedule_optimism_detected"] is False
    assert res["cp_ev_dilution_detected"] is True
    assert res["float_exhaustion_warning"] is True
    assert res["is_schedule_aligned"] is False
    assert res["status"] == "warning"
    assert len(res["violations"]) == 2


def test_evaluate_evm_critical_path_drag_decoupling_via_service_staticmethod():
    """Verifica invocación vía ProjectEVMService.evaluate_evm_critical_path_drag_decoupling."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_critical_path_drag_decoupling,
    )

    kwargs = {
        "spi": 0.88,
        "sv_amount": -9500.0,
        "critical_path_slip_days": 8.0,
        "critical_path_ev_share_pct": 30.0,
        "non_critical_float_consumed_days": 4.0,
        "max_acceptable_cp_slip_days": 1.0,
        "min_cp_ev_share_pct": 40.0,
    }
    direct = evaluate_evm_critical_path_drag_decoupling(**kwargs)
    via_service = ProjectEVMService.evaluate_evm_critical_path_drag_decoupling(
        **kwargs
    )
    assert via_service == direct
    assert via_service["status"] == "critical"
    assert via_service["cp_ev_dilution_detected"] is True


def test_evaluate_evm_undistributed_budget_and_planning_packages_healthy():
    """> PMB reconciliado, UB dentro de umbral y retención dentro de SLA -> healthy."""
    from backend.services.project_evm_service import (
        evaluate_evm_undistributed_budget_and_planning_packages,
    )

    res = evaluate_evm_undistributed_budget_and_planning_packages(
        bac=1000.0,
        distributed_work_packages_budget=700.0,
        planning_packages_budget=200.0,
        undistributed_budget=100.0,
        ub_holding_days=30.0,
    )
    assert res["bac"] == 1000.0
    assert res["calculated_pmb"] == 1000.0
    assert res["pmb_bac_discrepancy_amount"] == 0.0
    assert res["pmb_reconciled_with_bac"] is True
    assert res["ub_share_pct"] == 10.0
    assert res["planning_package_share_pct"] == 20.0
    assert res["ub_share_exceeded"] is False
    assert res["ub_holding_sla_breached"] is False
    assert res["is_pmb_baseline_healthy"] is True

    static_res = ProjectEVMService.evaluate_evm_undistributed_budget_and_planning_packages(
        1000.0,
        700.0,
        200.0,
        100.0,
        30.0,
    )
    assert static_res == res


def test_evaluate_evm_undistributed_budget_and_planning_packages_pmb_bac_discrepancy():
    """> PMB calculado != BAC (tolerancia 0.01) -> no reconciliado."""
    from backend.services.project_evm_service import (
        evaluate_evm_undistributed_budget_and_planning_packages,
    )

    res = evaluate_evm_undistributed_budget_and_planning_packages(
        bac=1000.0,
        distributed_work_packages_budget=710.0,
        planning_packages_budget=200.0,
        undistributed_budget=100.0,
    )
    assert res["calculated_pmb"] == 1010.0
    assert res["pmb_bac_discrepancy_amount"] == 10.0
    assert res["pmb_reconciled_with_bac"] is False
    assert res["is_pmb_baseline_healthy"] is False

    res_tol = evaluate_evm_undistributed_budget_and_planning_packages(
        bac=1000.0,
        distributed_work_packages_budget=700.0,
        planning_packages_budget=200.0,
        undistributed_budget=100.005,
    )
    assert res_tol["calculated_pmb"] == 1000.0
    assert res_tol["pmb_bac_discrepancy_amount"] == 0.0
    assert res_tol["pmb_reconciled_with_bac"] is True


def test_evaluate_evm_undistributed_budget_and_planning_packages_ub_share_and_sla_breach():
    """> UB share > umbral y retención > max_ub_holding_days con fondos pendientes."""
    from backend.services.project_evm_service import (
        evaluate_evm_undistributed_budget_and_planning_packages,
    )

    res = evaluate_evm_undistributed_budget_and_planning_packages(
        bac=1000.0,
        distributed_work_packages_budget=650.0,
        planning_packages_budget=200.0,
        undistributed_budget=150.0,
        ub_holding_days=40.0,
    )
    assert res["calculated_pmb"] == 1000.0
    assert res["pmb_reconciled_with_bac"] is True
    assert res["ub_share_pct"] == 15.0
    assert res["ub_share_exceeded"] is True
    assert res["ub_holding_sla_breached"] is True
    assert res["is_pmb_baseline_healthy"] is False

    # UB en cero: la retención no viola SLA aunque los días pasen el tope.
    res_no_ub = evaluate_evm_undistributed_budget_and_planning_packages(
        bac=1000.0,
        distributed_work_packages_budget=800.0,
        planning_packages_budget=200.0,
        undistributed_budget=0.0,
        ub_holding_days=99.0,
    )
    assert res_no_ub["ub_holding_sla_breached"] is False
    assert res_no_ub["is_pmb_baseline_healthy"] is True


def test_evaluate_evm_undistributed_budget_and_planning_packages_value_errors():
    """> ValueError ante bac<=0, montos negativos, bool o NaN; staticmethod vía clase."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_undistributed_budget_and_planning_packages,
    )

    bad_calls = (
        (0.0, 700.0),
        (-1000.0, 700.0),
        (1000.0, -1.0),
        (1000.0, 700.0, -1.0),
        (1000.0, 700.0, 200.0, -0.5),
        (1000.0, 700.0, 200.0, 100.0, -5.0),
        (True, 700.0),
        (1000.0, True),
        (1000.0, 700.0, 200.0, True),
        (float("nan"), 700.0),
        (1000.0, 700.0, 200.0, float("nan")),
    )
    for args in bad_calls:
        with pytest.raises(ValueError):
            evaluate_evm_undistributed_budget_and_planning_packages(*args)

    assert ProjectEVMService.evaluate_evm_undistributed_budget_and_planning_packages(
        100.0, 100.0
    )["is_pmb_baseline_healthy"] is True


def test_evaluate_evm_reserve_burn_vs_risk_exposure_healthy():
    """Reserva suficiente y consumo proporcional al avance físico -> healthy."""
    from backend.services.project_evm_service import (
        evaluate_evm_reserve_burn_vs_risk_exposure,
    )

    res = evaluate_evm_reserve_burn_vs_risk_exposure(
        initial_contingency_reserve=20000.0,
        remaining_contingency_reserve=12000.0,
        remaining_emv_exposure=8000.0,
        percent_complete=45.0,
        management_reserve_used=0.0,
        mr_ccb_approved=True,
        max_burn_disproportion_pct=20.0,
    )
    assert res == {
        "contingency_burn_pct": 40.0,
        "reserve_coverage_ratio": 1.5,
        "burn_vs_progress_delta_pct": -5.0,
        "reserve_shortfall_detected": False,
        "premature_reserve_depletion": False,
        "unapproved_mr_drawdown": False,
        "is_reserve_healthy": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_evaluate_evm_reserve_burn_vs_risk_exposure_critical_shortfall_and_unapproved_mr():
    """Déficit de reserva frente a EMV residual o uso de Reserva de Gestión sin aprobación CCB -> critical."""
    from backend.services.project_evm_service import (
        evaluate_evm_reserve_burn_vs_risk_exposure,
    )

    res_shortfall = evaluate_evm_reserve_burn_vs_risk_exposure(
        initial_contingency_reserve=10000.0,
        remaining_contingency_reserve=4000.0,
        remaining_emv_exposure=5500.0,
        percent_complete=55.0,
    )
    assert res_shortfall["contingency_burn_pct"] == 60.0
    assert res_shortfall["reserve_coverage_ratio"] == 0.7273
    assert res_shortfall["reserve_shortfall_detected"] is True
    assert res_shortfall["premature_reserve_depletion"] is False
    assert res_shortfall["unapproved_mr_drawdown"] is False
    assert res_shortfall["is_reserve_healthy"] is False
    assert res_shortfall["status"] == "critical"
    assert len(res_shortfall["recommendations"]) >= 1

    res_mr = evaluate_evm_reserve_burn_vs_risk_exposure(
        initial_contingency_reserve=10000.0,
        remaining_contingency_reserve=8000.0,
        remaining_emv_exposure=5000.0,
        percent_complete=25.0,
        management_reserve_used=1500.0,
        mr_ccb_approved=False,
    )
    assert res_mr["reserve_shortfall_detected"] is False
    assert res_mr["unapproved_mr_drawdown"] is True
    assert res_mr["is_reserve_healthy"] is False
    assert res_mr["status"] == "critical"
    assert len(res_mr["recommendations"]) >= 1


def test_evaluate_evm_reserve_burn_vs_risk_exposure_warning_premature_depletion():
    """Agotamiento prematuro de contingencia respecto al avance físico sin déficit EMV -> warning."""
    from backend.services.project_evm_service import (
        evaluate_evm_reserve_burn_vs_risk_exposure,
    )

    res = evaluate_evm_reserve_burn_vs_risk_exposure(
        initial_contingency_reserve=10000.0,
        remaining_contingency_reserve=4500.0,
        remaining_emv_exposure=3000.0,
        percent_complete=20.0,
        max_burn_disproportion_pct=20.0,
    )
    assert res["contingency_burn_pct"] == 55.0
    assert res["burn_vs_progress_delta_pct"] == 35.0
    assert res["reserve_coverage_ratio"] == 1.5
    assert res["reserve_shortfall_detected"] is False
    assert res["premature_reserve_depletion"] is True
    assert res["unapproved_mr_drawdown"] is False
    assert res["is_reserve_healthy"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 1


def test_evaluate_evm_reserve_burn_vs_risk_exposure_value_errors_and_staticmethod():
    """Rechaza entradas inválidas con ValueError y verifica llamada vía ProjectEVMService.evaluate_evm_reserve_burn_vs_risk_exposure."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_reserve_burn_vs_risk_exposure,
    )

    bad_calls = [
        (0.0, 0.0, 100.0, 50.0),
        (-100.0, 50.0, 100.0, 50.0),
        (1000.0, -10.0, 100.0, 50.0),
        (1000.0, 1200.0, 100.0, 50.0),
        (1000.0, 500.0, -1.0, 50.0),
        (1000.0, 500.0, 100.0, -5.0),
        (1000.0, 500.0, 100.0, 105.0),
        (1000.0, 500.0, 100.0, 50.0, -10.0),
        (1000.0, 500.0, 100.0, 50.0, 0.0, True, -1.0),
        (True, 500.0, 100.0, 50.0),
        (1000.0, float("nan"), 100.0, 50.0),
    ]
    for args in bad_calls:
        with pytest.raises(ValueError):
            evaluate_evm_reserve_burn_vs_risk_exposure(*args)  # type: ignore[arg-type]

    assert (
        ProjectEVMService.evaluate_evm_reserve_burn_vs_risk_exposure(
            10000.0, 10000.0, 0.0, 10.0
        )
        == evaluate_evm_reserve_burn_vs_risk_exposure(10000.0, 10000.0, 0.0, 10.0)
    )


def test_evaluate_evm_loe_masking_and_variance_distortion_compliant():
    """Cuentas de control con proporción LOE <= 15%, EV_LOE == PV_LOE y sin enmascaramiento -> compliant True."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_loe_masking_and_variance_distortion,
    )

    accounts = [
        {
            "ca_id": "CA-01",
            "total_bac": 100000.0,
            "loe_bac": 10000.0,
            "loe_ev": 5000.0,
            "loe_pv": 5000.0,
            "discrete_sv": -2000.0,
            "reported_total_sv": -2000.0,
        },
        {
            "id": "CA-02",
            "total_bac": 50000.0,
            "loe_bac": 5000.0,
            "loe_ev": 2500.0,
            "loe_pv": 2500.0,
            "discrete_sv": 1000.0,
            "reported_total_sv": 1000.0,
        },
    ]
    res = evaluate_evm_loe_masking_and_variance_distortion(accounts)
    assert res == {
        "total_evaluated": 2,
        "excessive_loe_share_ca_ids": [],
        "loe_schedule_variance_violation_ca_ids": [],
        "loe_masked_delay_ca_ids": [],
        "is_loe_accounting_compliant": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_loe_masking_and_variance_distortion(
            accounts
        )
        == res
    )


def test_evaluate_evm_loe_masking_and_variance_distortion_excessive_share_and_sv_violation():
    """Detecta exceso de proporción LOE (> max_loe_share_pct) y violación contable EV_LOE != PV_LOE."""
    from backend.services.project_evm_service import (
        evaluate_evm_loe_masking_and_variance_distortion,
    )

    accounts = [
        {
            "ca_id": "CA-HIGH-LOE",
            "total_bac": 100000.0,
            "loe_bac": 25000.0,
            "loe_ev": 10000.0,
            "loe_pv": 10000.0,
            "discrete_sv": 0.0,
            "reported_total_sv": 0.0,
        },
        {
            "ca_id": "CA-BAD-SV",
            "total_bac": 100000.0,
            "loe_bac": 10000.0,
            "loe_ev": 6500.0,
            "loe_pv": 5000.0,
            "discrete_sv": 0.0,
            "reported_total_sv": 1500.0,
        },
    ]
    res = evaluate_evm_loe_masking_and_variance_distortion(
        accounts, max_loe_share_pct=15.0
    )
    assert res["total_evaluated"] == 2
    assert res["excessive_loe_share_ca_ids"] == ["CA-HIGH-LOE"]
    assert res["loe_schedule_variance_violation_ca_ids"] == ["CA-BAD-SV"]
    assert res["loe_masked_delay_ca_ids"] == []
    assert res["is_loe_accounting_compliant"] is False


def test_evaluate_evm_loe_masking_and_variance_distortion_masked_delay():
    """Detecta atraso en trabajo discreto (discrete_sv < 0) ocultado por reported_total_sv >= 0."""
    from backend.services.project_evm_service import (
        evaluate_evm_loe_masking_and_variance_distortion,
    )

    accounts = [
        {
            "ca_id": "CA-MASKED",
            "total_bac": 100000.0,
            "loe_bac": 12000.0,
            "loe_ev": 6000.0,
            "loe_pv": 6000.0,
            "discrete_sv": -3500.0,
            "reported_total_sv": 200.0,
        }
    ]
    res = evaluate_evm_loe_masking_and_variance_distortion(accounts)
    assert res["total_evaluated"] == 1
    assert res["excessive_loe_share_ca_ids"] == []
    assert res["loe_schedule_variance_violation_ca_ids"] == []
    assert res["loe_masked_delay_ca_ids"] == ["CA-MASKED"]
    assert res["is_loe_accounting_compliant"] is False


def test_evaluate_evm_loe_masking_and_variance_distortion_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin ca_id válido y verifica exportación en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_loe_masking_and_variance_distortion,
    )

    assert "evaluate_evm_loe_masking_and_variance_distortion" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"xyz"), [{"ca_id": "  "}, 42]):
        res = evaluate_evm_loe_masking_and_variance_distortion(bad)
        assert res == {
            "total_evaluated": 0,
            "excessive_loe_share_ca_ids": [],
            "loe_schedule_variance_violation_ca_ids": [],
            "loe_masked_delay_ca_ids": [],
            "is_loe_accounting_compliant": True,
        }


def test_evaluate_evm_apportioned_effort_base_coherence_compliant():
    """Valida paquetes AE vinculados a trabajo discreto, factor (0, 100] y avance sincronizado."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_apportioned_effort_base_coherence,
    )

    packages = [
        {
            "wp_id": "WP-AE-QA-01",
            "base_discrete_wp_id": "WP-DEV-01",
            "base_wp_evmt": "fixed_formula",
            "apportionment_factor_pct": 15.0,
            "base_progress_pct": 60.0,
            "reported_ae_progress_pct": 60.3,
        },
        {
            "id": "WP-AE-INSP-02",
            "base_discrete_wp_id": "WP-DEV-02",
            "base_wp_evmt": "weighted_milestones",
            "apportionment_factor_pct": 10.0,
            "base_progress_pct": 100.0,
            "reported_ae_progress_pct": 100.0,
        },
    ]
    res = evaluate_evm_apportioned_effort_base_coherence(packages)
    assert res == {
        "total_evaluated": 2,
        "unlinked_or_non_discrete_base_wp_ids": [],
        "invalid_factor_wp_ids": [],
        "progress_desync_wp_ids": [],
        "is_apportioned_effort_coherent": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_apportioned_effort_base_coherence(
            packages
        )
        == res
    )


def test_evaluate_evm_apportioned_effort_base_coherence_unlinked_and_loe_base():
    """Detecta paquetes AE sin base_discrete_wp_id o vinculados a un paquete LOE."""
    from backend.services.project_evm_service import (
        evaluate_evm_apportioned_effort_base_coherence,
    )

    packages = [
        {
            "wp_id": "WP-AE-NO-BASE",
            "base_discrete_wp_id": "   ",
            "base_wp_evmt": "discrete",
            "apportionment_factor_pct": 12.0,
            "base_progress_pct": 40.0,
            "reported_ae_progress_pct": 40.0,
        },
        {
            "wp_id": "WP-AE-ON-LOE",
            "base_discrete_wp_id": "WP-PMO-LOE",
            "base_wp_evmt": "LOE",
            "apportionment_factor_pct": 20.0,
            "base_progress_pct": 50.0,
            "reported_ae_progress_pct": 50.0,
        },
    ]
    res = evaluate_evm_apportioned_effort_base_coherence(packages)
    assert res["total_evaluated"] == 2
    assert res["unlinked_or_non_discrete_base_wp_ids"] == [
        "WP-AE-NO-BASE",
        "WP-AE-ON-LOE",
    ]
    assert res["invalid_factor_wp_ids"] == []
    assert res["progress_desync_wp_ids"] == []
    assert res["is_apportioned_effort_coherent"] is False


def test_evaluate_evm_apportioned_effort_base_coherence_factor_and_desync():
    """Detecta factores de prorrateo fuera de (0, 100] y desincronización de avance > 0.5%."""
    from backend.services.project_evm_service import (
        evaluate_evm_apportioned_effort_base_coherence,
    )

    packages = [
        {
            "wp_id": "WP-AE-ZERO-FACTOR",
            "base_discrete_wp_id": "WP-DISC-1",
            "apportionment_factor_pct": 0.0,
            "base_progress_pct": 30.0,
            "reported_ae_progress_pct": 30.0,
        },
        {
            "wp_id": "WP-AE-OVER-FACTOR",
            "base_discrete_wp_id": "WP-DISC-2",
            "apportionment_factor_pct": 125.0,
            "base_progress_pct": 50.0,
            "reported_ae_progress_pct": 65.0,
        },
    ]
    res = evaluate_evm_apportioned_effort_base_coherence(packages)
    assert res["total_evaluated"] == 2
    assert res["unlinked_or_non_discrete_base_wp_ids"] == []
    assert res["invalid_factor_wp_ids"] == [
        "WP-AE-ZERO-FACTOR",
        "WP-AE-OVER-FACTOR",
    ]
    assert res["progress_desync_wp_ids"] == ["WP-AE-OVER-FACTOR"]
    assert res["is_apportioned_effort_coherent"] is False


def test_evaluate_evm_apportioned_effort_base_coherence_invalid_inputs_and_export():
    """Maneja entradas no secuencia o ítems sin wp_id e incluye exportación en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_apportioned_effort_base_coherence,
    )

    assert "evaluate_evm_apportioned_effort_base_coherence" in _m.__all__
    for bad in (None, "str", b"bytes", bytearray(b"123"), [{"wp_id": ""}, 99]):
        assert evaluate_evm_apportioned_effort_base_coherence(bad) == {
            "total_evaluated": 0,
            "unlinked_or_non_discrete_base_wp_ids": [],
            "invalid_factor_wp_ids": [],
            "progress_desync_wp_ids": [],
            "is_apportioned_effort_coherent": True,
        }


def test_evaluate_evm_retroactive_adjustment_and_negative_period_anomalies_clean():
    """Periodos con variaciones positivas o ajustes retroactivos autorizados y EV <= BAC."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_retroactive_adjustment_and_negative_period_anomalies,
    )

    periods = [
        {
            "period_id": "2026-08",
            "period_delta_ev": 12000.0,
            "period_delta_ac": 11500.0,
            "cumulative_ev": 60000.0,
            "bac": 100000.0,
            "has_approved_retroactive_adjustment_log": False,
        },
        {
            "id": "2026-09",
            "period_delta_ev": -1500.0,
            "period_delta_ac": -800.0,
            "cumulative_ev": 58500.0,
            "bac": 100000.0,
            "has_approved_retroactive_adjustment_log": True,
        },
    ]
    res = evaluate_evm_retroactive_adjustment_and_negative_period_anomalies(
        periods
    )
    assert res == {
        "total_evaluated": 2,
        "unexplained_negative_ev_period_ids": [],
        "unexplained_negative_ac_period_ids": [],
        "ev_exceeds_bac_ceiling_period_ids": [],
        "is_period_accounting_clean": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_retroactive_adjustment_and_negative_period_anomalies(
            periods
        )
        == res
    )


def test_evaluate_evm_retroactive_unexplained_negative_ev_and_ac():
    """Detecta de-earning (EV < 0) o reversión AC < 0 sin bitácora de ajuste retroactivo aprobada."""
    from backend.services.project_evm_service import (
        evaluate_evm_retroactive_adjustment_and_negative_period_anomalies,
    )

    periods = [
        {
            "period_id": "2026-10-NEG-EV",
            "period_delta_ev": -2500.0,
            "period_delta_ac": 4000.0,
            "cumulative_ev": 45000.0,
            "bac": 100000.0,
            "has_approved_retroactive_adjustment_log": False,
        },
        {
            "period_id": "2026-11-NEG-AC",
            "period_delta_ev": 3000.0,
            "period_delta_ac": -1200.0,
            "cumulative_ev": 48000.0,
            "bac": 100000.0,
            "has_approved_retroactive_adjustment_log": False,
        },
    ]
    res = evaluate_evm_retroactive_adjustment_and_negative_period_anomalies(
        periods
    )
    assert res["total_evaluated"] == 2
    assert res["unexplained_negative_ev_period_ids"] == ["2026-10-NEG-EV"]
    assert res["unexplained_negative_ac_period_ids"] == ["2026-11-NEG-AC"]
    assert res["ev_exceeds_bac_ceiling_period_ids"] == []
    assert res["is_period_accounting_clean"] is False


def test_evaluate_evm_retroactive_ev_exceeds_bac_ceiling():
    """Detecta cuando cumulative_ev supera el techo BAC + 0.01."""
    from backend.services.project_evm_service import (
        evaluate_evm_retroactive_adjustment_and_negative_period_anomalies,
    )

    periods = [
        {
            "period_id": "2026-12-OVER-BAC",
            "period_delta_ev": 15000.0,
            "period_delta_ac": 14000.0,
            "cumulative_ev": 105000.0,
            "bac": 100000.0,
            "has_approved_retroactive_adjustment_log": False,
        }
    ]
    res = evaluate_evm_retroactive_adjustment_and_negative_period_anomalies(
        periods
    )
    assert res["total_evaluated"] == 1
    assert res["unexplained_negative_ev_period_ids"] == []
    assert res["unexplained_negative_ac_period_ids"] == []
    assert res["ev_exceeds_bac_ceiling_period_ids"] == ["2026-12-OVER-BAC"]
    assert res["is_period_accounting_clean"] is False


def test_evaluate_evm_retroactive_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin period_id válido y verifica exportación en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_retroactive_adjustment_and_negative_period_anomalies,
    )

    assert (
        "evaluate_evm_retroactive_adjustment_and_negative_period_anomalies"
        in _m.__all__
    )
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"abc"), [{"period_id": "  "}, 12]):
        assert evaluate_evm_retroactive_adjustment_and_negative_period_anomalies(
            bad
        ) == {
            "total_evaluated": 0,
            "unexplained_negative_ev_period_ids": [],
            "unexplained_negative_ac_period_ids": [],
            "ev_exceeds_bac_ceiling_period_ids": [],
            "is_period_accounting_clean": True,
        }


def test_evaluate_evm_contract_budget_base_and_ub_reconciliation_compliant():
    """Jerarquía reconciliada (DB + UB = PMB, PMB + MR = CBB = TAB) con UB dentro de umbrales cumple §7.4."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_contract_budget_base_and_ub_reconciliation,
    )

    ledger = {
        "distributed_budgets_sum": 460000.0,
        "undistributed_budget_ub": 40000.0,
        "performance_measurement_baseline_pmb": 500000.0,
        "management_reserve_mr": 50000.0,
        "contract_budget_base_cbb": 550000.0,
        "total_allocated_budget_tab": 550000.0,
        "over_target_baseline_authorized": False,
        "ub_oldest_unallocated_days": 14,
    }
    res = evaluate_evm_contract_budget_base_and_ub_reconciliation(ledger)
    assert res == {
        "expected_pmb": 500000.0,
        "pmb_reconciliation_delta": 0.0,
        "has_pmb_imbalance": False,
        "expected_cbb": 550000.0,
        "cbb_reconciliation_delta": 0.0,
        "has_cbb_imbalance": False,
        "has_unauthorized_over_target_baseline": False,
        "ub_ratio": 0.08,
        "has_excessive_or_stale_ub": False,
        "is_baseline_reconciliation_compliant": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_contract_budget_base_and_ub_reconciliation(
            ledger
        )
        == res
    )


def test_evaluate_evm_contract_budget_base_pmb_and_cbb_imbalances():
    """Detecta desbalances contables cuando PMB != DB + UB o CBB != PMB + MR."""
    from backend.services.project_evm_service import (
        evaluate_evm_contract_budget_base_and_ub_reconciliation,
    )

    ledger = {
        "distributed_budgets_sum": 450000.0,
        "undistributed_budget_ub": 20000.0,
        "performance_measurement_baseline_pmb": 480000.0,  # +10000 vs 470000
        "management_reserve_mr": 40000.0,
        "contract_budget_base_cbb": 515000.0,  # -5000 vs 520000
        "total_allocated_budget_tab": 515000.0,
        "over_target_baseline_authorized": False,
        "ub_oldest_unallocated_days": 10,
    }
    res = evaluate_evm_contract_budget_base_and_ub_reconciliation(ledger)
    assert res["expected_pmb"] == 470000.0
    assert res["pmb_reconciliation_delta"] == 10000.0
    assert res["has_pmb_imbalance"] is True
    assert res["expected_cbb"] == 520000.0
    assert res["cbb_reconciliation_delta"] == -5000.0
    assert res["has_cbb_imbalance"] is True
    assert res["has_unauthorized_over_target_baseline"] is False
    assert res["is_baseline_reconciliation_compliant"] is False


def test_evaluate_evm_contract_budget_base_unauthorized_vs_authorized_otb():
    """Detecta Over-Target Baseline (TAB > CBB) sin autorización formal y permite OTB autorizado."""
    from backend.services.project_evm_service import (
        evaluate_evm_contract_budget_base_and_ub_reconciliation,
    )

    base_ledger = {
        "distributed_budgets_sum": 300000.0,
        "undistributed_budget_ub": 0.0,
        "performance_measurement_baseline_pmb": 300000.0,
        "management_reserve_mr": 30000.0,
        "contract_budget_base_cbb": 330000.0,
        "total_allocated_budget_tab": 360000.0,
        "over_target_baseline_authorized": False,
        "ub_oldest_unallocated_days": 0,
    }
    unauth = evaluate_evm_contract_budget_base_and_ub_reconciliation(base_ledger)
    assert unauth["has_unauthorized_over_target_baseline"] is True
    assert unauth["is_baseline_reconciliation_compliant"] is False

    auth = evaluate_evm_contract_budget_base_and_ub_reconciliation(
        {**base_ledger, "over_target_baseline_authorized": True}
    )
    assert auth["has_unauthorized_over_target_baseline"] is False
    assert auth["is_baseline_reconciliation_compliant"] is True


def test_evaluate_evm_contract_budget_base_excessive_or_stale_ub_and_export():
    """Detecta UB excesivo en proporción al PMB, UB estancado (> max_ub_holding_days) y verifica exportación en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_contract_budget_base_and_ub_reconciliation,
    )

    assert "evaluate_evm_contract_budget_base_and_ub_reconciliation" in _m.__all__

    # UB ratio 0.15 > 0.10
    high_ratio = evaluate_evm_contract_budget_base_and_ub_reconciliation(
        {
            "distributed_budgets_sum": 170000.0,
            "undistributed_budget_ub": 30000.0,
            "performance_measurement_baseline_pmb": 200000.0,
            "management_reserve_mr": 20000.0,
            "contract_budget_base_cbb": 220000.0,
            "total_allocated_budget_tab": 220000.0,
            "ub_oldest_unallocated_days": 12,
        },
        max_ub_to_pm_baseline_ratio=0.10,
    )
    assert high_ratio["ub_ratio"] == 0.15
    assert high_ratio["has_excessive_or_stale_ub"] is True
    assert high_ratio["is_baseline_reconciliation_compliant"] is False

    # UB ratio 0.05 <= 0.10 pero estancado 45 días > 30
    stale_ub = evaluate_evm_contract_budget_base_and_ub_reconciliation(
        {
            "distributed_budgets_sum": 190000.0,
            "undistributed_budget_ub": 10000.0,
            "performance_measurement_baseline_pmb": 200000.0,
            "management_reserve_mr": 20000.0,
            "contract_budget_base_cbb": 220000.0,
            "total_allocated_budget_tab": 220000.0,
            "ub_oldest_unallocated_days": 45,
        },
        max_ub_holding_days=30,
    )
    assert stale_ub["ub_ratio"] == 0.05
    assert stale_ub["has_excessive_or_stale_ub"] is True
    assert stale_ub["is_baseline_reconciliation_compliant"] is False


def test_evaluate_evm_etc_bottom_up_vs_formulaic_divergence_credible():
    """Pronósticos ETC bottom-up alineados o con divergencia respaldada por BOE cumplen §7.4."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_etc_bottom_up_vs_formulaic_divergence,
    )

    forecasts = [
        {
            "ca_id": "CA-ALIGNED",
            "bac": 100000.0,
            "ev": 50000.0,
            "ac": 50000.0,
            "bottom_up_etc": 48000.0,  # 4% menor que 50k <= 15%
            "basis_of_estimate_documented": False,
        },
        {
            "ca_id": "CA-OPT-WITH-BOE",
            "bac": 100000.0,
            "ev": 50000.0,
            "ac": 55000.0,  # CPI = 0.909, typical_etc = 55000
            "bottom_up_etc": 45000.0,  # delta 18.18% > 15%, pero con BOE y CPI >= 0.85
            "basis_of_estimate_documented": True,
        },
    ]
    res = evaluate_evm_etc_bottom_up_vs_formulaic_divergence(forecasts)
    assert res == {
        "total_control_accounts": 2,
        "invalid_forecast_metric_ca_ids": [],
        "optimistic_etc_divergence_ca_ids": ["CA-OPT-WITH-BOE"],
        "unjustified_optimistic_etc_ca_ids": [],
        "unrealistic_recovery_etc_ca_ids": [],
        "is_etc_forecast_credible": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_etc_bottom_up_vs_formulaic_divergence(
            forecasts
        )
        == res
    )


def test_evaluate_evm_etc_bottom_up_unjustified_optimistic_divergence():
    """Detecta divergencia optimista > max_optimistic_divergence_pct sin Basis of Estimate (BOE)."""
    from backend.services.project_evm_service import (
        evaluate_evm_etc_bottom_up_vs_formulaic_divergence,
    )

    forecasts = [
        {
            "ca_id": "CA-OPT-NO-BOE",
            "bac": 200000.0,
            "ev": 100000.0,
            "ac": 110000.0,  # CPI = 0.9091, typical_etc = 110000
            "bottom_up_etc": 85000.0,  # delta ~22.73% > 15% sin BOE
            "basis_of_estimate_documented": False,
        }
    ]
    res = evaluate_evm_etc_bottom_up_vs_formulaic_divergence(
        forecasts, max_optimistic_divergence_pct=15.0
    )
    assert res["total_control_accounts"] == 1
    assert res["optimistic_etc_divergence_ca_ids"] == ["CA-OPT-NO-BOE"]
    assert res["unjustified_optimistic_etc_ca_ids"] == ["CA-OPT-NO-BOE"]
    assert res["unrealistic_recovery_etc_ca_ids"] == []
    assert res["is_etc_forecast_credible"] is False


def test_evaluate_evm_etc_bottom_up_unrealistic_recovery_with_low_cpi():
    """Detecta cuando CPI < 0.85 pero bottom_up_etc < (BAC - EV) incluso si existe BOE."""
    from backend.services.project_evm_service import (
        evaluate_evm_etc_bottom_up_vs_formulaic_divergence,
    )

    forecasts = [
        {
            "ca_id": "CA-LOW-CPI-UNREALISTIC",
            "bac": 100000.0,
            "ev": 40000.0,
            "ac": 55000.0,  # CPI = 0.727 < 0.85, remaining = 60000
            "bottom_up_etc": 52000.0,  # < 60000
            "basis_of_estimate_documented": True,
        }
    ]
    res = evaluate_evm_etc_bottom_up_vs_formulaic_divergence(forecasts)
    assert res["optimistic_etc_divergence_ca_ids"] == ["CA-LOW-CPI-UNREALISTIC"]
    assert res["unjustified_optimistic_etc_ca_ids"] == []
    assert res["unrealistic_recovery_etc_ca_ids"] == ["CA-LOW-CPI-UNREALISTIC"]
    assert res["is_etc_forecast_credible"] is False


def test_evaluate_evm_etc_bottom_up_invalid_metrics_and_export():
    """Detecta métricas inválidas (BAC <= 0, EV > BAC, negativos), ignora no-secuencias y verifica __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_etc_bottom_up_vs_formulaic_divergence,
    )

    assert "evaluate_evm_etc_bottom_up_vs_formulaic_divergence" in _m.__all__
    res = evaluate_evm_etc_bottom_up_vs_formulaic_divergence(
        [
            {
                "ca_id": "CA-EV-GT-BAC",
                "bac": 50000.0,
                "ev": 60000.0,
                "ac": 50000.0,
                "bottom_up_etc": 1000.0,
            },
            {
                "ca_id": "CA-NEG-ETC",
                "bac": 50000.0,
                "ev": 20000.0,
                "ac": 20000.0,
                "bottom_up_etc": -500.0,
            },
        ]
    )
    assert res["invalid_forecast_metric_ca_ids"] == [
        "CA-EV-GT-BAC",
        "CA-NEG-ETC",
    ]
    assert res["is_etc_forecast_credible"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"ca_id": "  "}]):
        assert evaluate_evm_etc_bottom_up_vs_formulaic_divergence(bad) == {
            "total_control_accounts": 0,
            "invalid_forecast_metric_ca_ids": [],
            "optimistic_etc_divergence_ca_ids": [],
            "unjustified_optimistic_etc_ca_ids": [],
            "unrealistic_recovery_etc_ca_ids": [],
            "is_etc_forecast_credible": True,
        }


def test_evaluate_evm_critical_path_drag_and_float_masking_coherent():
    """Paquetes en ruta crítica con holgura <= 0, SPI crítico >= 0.90 y sin enmascaramiento cumplen §6.5 y §7.4."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_critical_path_drag_and_float_masking,
    )

    wps = [
        {
            "wp_id": "WP-CRIT-01",
            "is_critical_path": True,
            "planned_value_pv": 100000.0,
            "earned_value_ev": 98000.0,
            "total_float_days": 0.0,
            "critical_path_drag_days": 4.0,
        },
        {
            "wp_id": "WP-NONCRIT-02",
            "is_critical_path": False,
            "planned_value_pv": 50000.0,
            "earned_value_ev": 50000.0,
            "total_float_days": 8.0,
            "critical_path_drag_days": 0.0,
        },
    ]
    res = evaluate_evm_critical_path_drag_and_float_masking(
        wps, overall_spi_t=0.98
    )
    assert res == {
        "critical_path_spi": 0.98,
        "non_critical_spi": 1.0,
        "has_non_critical_float_masking": False,
        "invalid_schedule_metric_wp_ids": [],
        "contradictory_critical_float_wp_ids": [],
        "high_drag_lagging_critical_wp_ids": [],
        "is_earned_schedule_critical_path_coherent": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_critical_path_drag_and_float_masking(
            wps, overall_spi_t=0.98
        )
        == res
    )


def test_evaluate_evm_critical_path_drag_float_masking_and_high_drag_lag():
    """Detecta enmascaramiento de atraso en ruta crítica por tareas no críticas adelantadas y paquetes críticos con drag >= 5d."""
    from backend.services.project_evm_service import (
        evaluate_evm_critical_path_drag_and_float_masking,
    )

    wps = [
        {
            "wp_id": "WP-CRIT-LAGGING",
            "is_critical_path": True,
            "planned_value_pv": 100000.0,
            "earned_value_ev": 75000.0,  # SPI 0.75 < 0.90
            "total_float_days": 0.0,
            "critical_path_drag_days": 6.5,
        },
        {
            "wp_id": "WP-NONCRIT-AHEAD",
            "is_critical_path": False,
            "planned_value_pv": 100000.0,
            "earned_value_ev": 125000.0,  # SPI 1.25 >= 1.05
            "total_float_days": 12.0,
            "critical_path_drag_days": 0.0,
        },
    ]
    res = evaluate_evm_critical_path_drag_and_float_masking(
        wps, overall_spi_t=1.0
    )
    assert res["critical_path_spi"] == 0.75
    assert res["non_critical_spi"] == 1.25
    assert res["has_non_critical_float_masking"] is True
    assert res["high_drag_lagging_critical_wp_ids"] == ["WP-CRIT-LAGGING"]
    assert res["is_earned_schedule_critical_path_coherent"] is False


def test_evaluate_evm_critical_path_drag_contradictory_float():
    """Detecta paquetes marcados en ruta crítica que reportan holgura total positiva."""
    from backend.services.project_evm_service import (
        evaluate_evm_critical_path_drag_and_float_masking,
    )

    wps = [
        {
            "wp_id": "WP-CRIT-WITH-FLOAT",
            "is_critical_path": True,
            "planned_value_pv": 50000.0,
            "earned_value_ev": 50000.0,
            "total_float_days": 5.0,
            "critical_path_drag_days": 2.0,
        }
    ]
    res = evaluate_evm_critical_path_drag_and_float_masking(wps)
    assert res["contradictory_critical_float_wp_ids"] == ["WP-CRIT-WITH-FLOAT"]
    assert res["is_earned_schedule_critical_path_coherent"] is False


def test_evaluate_evm_critical_path_drag_invalid_metrics_and_export():
    """Detecta métricas negativas, maneja entradas vacías y verifica exportación en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_critical_path_drag_and_float_masking,
    )

    assert "evaluate_evm_critical_path_drag_and_float_masking" in _m.__all__
    res = evaluate_evm_critical_path_drag_and_float_masking(
        [
            {
                "wp_id": "WP-NEG-PV",
                "is_critical_path": True,
                "planned_value_pv": -1000.0,
                "earned_value_ev": 0.0,
            }
        ]
    )
    assert res["invalid_schedule_metric_wp_ids"] == ["WP-NEG-PV"]
    assert res["is_earned_schedule_critical_path_coherent"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"wp_id": "  "}]):
        assert evaluate_evm_critical_path_drag_and_float_masking(bad) == {
            "critical_path_spi": 1.0,
            "non_critical_spi": 1.0,
            "has_non_critical_float_masking": False,
            "invalid_schedule_metric_wp_ids": [],
            "contradictory_critical_float_wp_ids": [],
            "high_drag_lagging_critical_wp_ids": [],
            "is_earned_schedule_critical_path_coherent": True,
        }


def test_evaluate_evm_rolling_wave_planning_package_freeze_horizon_compliant():
    """Cumple cuando paquetes en horizonte próximo están descompuestos, sin EV prematuro y bajo tope de participación."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_rolling_wave_planning_package_freeze_horizon,
    )

    packages = [
        {
            "pp_id": "PP-WAVE-1",
            "budget_bac": 65000.0,
            "days_until_scheduled_start": 10,
            "decomposed_into_work_packages": True,
            "earned_value_claimed": 15000.0,
        },
        {
            "pp_id": "PP-WAVE-2",
            "budget_bac": 35000.0,
            "days_until_scheduled_start": 60,
            "decomposed_into_work_packages": False,
            "earned_value_claimed": 0.0,
        },
    ]
    res = evaluate_evm_rolling_wave_planning_package_freeze_horizon(
        packages,
        freeze_horizon_days=30,
        max_planning_package_share_pct=40.0,
        total_control_account_bac=100000.0,
    )
    assert res["total_planning_packages"] == 2
    assert res["undecomposed_share_pct"] == 35.0
    assert res["exceeds_undecomposed_share_cap"] is False
    assert res["invalid_planning_package_ids"] == []
    assert res["premature_ev_on_undecomposed_pp_ids"] == []
    assert res["unfrozen_imminent_planning_package_ids"] == []
    assert res["is_rolling_wave_horizon_compliant"] is True
    assert (
        ProjectEVMService.evaluate_evm_rolling_wave_planning_package_freeze_horizon(
            packages, total_control_account_bac=100000.0
        )
        == res
    )


def test_evaluate_evm_rolling_wave_premature_ev_and_imminent_unfrozen():
    """Detecta EV reclamado en Planning Package sin descomponer y falta de descomposición dentro del horizonte de congelación."""
    from backend.services.project_evm_service import (
        evaluate_evm_rolling_wave_planning_package_freeze_horizon,
    )

    res = evaluate_evm_rolling_wave_planning_package_freeze_horizon(
        [
            {
                "pp_id": "PP-PREMATURE-EV",
                "budget_bac": 20000.0,
                "days_until_scheduled_start": 45,
                "decomposed_into_work_packages": False,
                "earned_value_claimed": 5000.0,
            },
            {
                "pp_id": "PP-IMMINENT-UNFROZEN",
                "budget_bac": 15000.0,
                "days_until_scheduled_start": 15,
                "decomposed_into_work_packages": False,
                "earned_value_claimed": 0.0,
            },
        ],
        freeze_horizon_days=30,
        max_planning_package_share_pct=40.0,
        total_control_account_bac=100000.0,
    )
    assert res["premature_ev_on_undecomposed_pp_ids"] == ["PP-PREMATURE-EV"]
    assert res["unfrozen_imminent_planning_package_ids"] == ["PP-IMMINENT-UNFROZEN"]
    assert res["is_rolling_wave_horizon_compliant"] is False


def test_evaluate_evm_rolling_wave_exceeds_share_cap():
    """Detecta cuando la proporción de BAC en Planning Packages no descompuestos supera el tope permitido."""
    from backend.services.project_evm_service import (
        evaluate_evm_rolling_wave_planning_package_freeze_horizon,
    )

    res = evaluate_evm_rolling_wave_planning_package_freeze_horizon(
        [
            {
                "pp_id": "PP-DECOMPOSED",
                "budget_bac": 40000.0,
                "days_until_scheduled_start": 5,
                "decomposed_into_work_packages": True,
                "earned_value_claimed": 10000.0,
            },
            {
                "pp_id": "PP-DISTANT-HEAVY",
                "budget_bac": 60000.0,
                "days_until_scheduled_start": 90,
                "decomposed_into_work_packages": False,
                "earned_value_claimed": 0.0,
            },
        ],
        freeze_horizon_days=30,
        max_planning_package_share_pct=40.0,
    )
    assert res["undecomposed_share_pct"] == 60.0
    assert res["exceeds_undecomposed_share_cap"] is True
    assert res["is_rolling_wave_horizon_compliant"] is False


def test_evaluate_evm_rolling_wave_invalid_package_and_export():
    """Detecta BAC <= 0 o EV negativo, maneja entradas malformadas y verifica exportación en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_rolling_wave_planning_package_freeze_horizon,
    )

    assert "evaluate_evm_rolling_wave_planning_package_freeze_horizon" in _m.__all__
    res = evaluate_evm_rolling_wave_planning_package_freeze_horizon(
        [
            {"pp_id": "PP-ZERO-BAC", "budget_bac": 0.0},
            {
                "pp_id": "PP-NEG-EV",
                "budget_bac": 10000.0,
                "decomposed_into_work_packages": True,
                "earned_value_claimed": -100.0,
            },
        ]
    )
    assert res["invalid_planning_package_ids"] == ["PP-ZERO-BAC", "PP-NEG-EV"]
    assert res["is_rolling_wave_horizon_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"pp_id": "  "}]):
        assert evaluate_evm_rolling_wave_planning_package_freeze_horizon(bad) == {
            "total_planning_packages": 0,
            "undecomposed_share_pct": 0.0,
            "exceeds_undecomposed_share_cap": False,
            "invalid_planning_package_ids": [],
            "premature_ev_on_undecomposed_pp_ids": [],
            "unfrozen_imminent_planning_package_ids": [],
            "is_rolling_wave_horizon_compliant": True,
        }



def test_evaluate_evm_tspi_achievable_and_earned_schedule_consumed():
    """tspi_pd <= 1.0 -> ACHIEVABLE; res_es == 0 -> tspi_pd 0.0 aunque plazo agotado."""
    import pytest

    from backend.services.project_evm_service import (
        evaluate_evm_to_complete_schedule_performance_index_tspi as fn,
    )

    res = fn(20.0, 10.0, 8.0)
    assert res == {
        "tspi_pd": 0.8333,
        "tspi_ed": None,
        "remaining_earned_schedule_days": 10.0,
        "remaining_planned_time_days": 12.0,
        "schedule_recovery_feasibility": "ACHIEVABLE",
        "requires_schedule_rebaseline": False,
    }

    # Borde exacto tspi_pd == 1.0 -> ACHIEVABLE (no CHALLENGING).
    border = fn(20.0, 10.0, 10.0)
    assert border["tspi_pd"] == 1.0
    assert border["schedule_recovery_feasibility"] == "ACHIEVABLE"

    # Earned schedule consumido por completo -> tspi_pd = 0.0 (regla primero).
    consumed = fn(20.0, 20.0, 25.0)
    assert consumed["tspi_pd"] == 0.0
    assert consumed["remaining_earned_schedule_days"] == 0.0
    assert consumed["remaining_planned_time_days"] == 0.0
    assert consumed["schedule_recovery_feasibility"] == "ACHIEVABLE"
    assert consumed["requires_schedule_rebaseline"] is False


def test_evaluate_evm_tspi_challenging_unachievable_and_tspi_ed():
    """1.0 < tspi_pd <= max -> CHALLENGING; None o > max -> UNACHIEVABLE; tspi_ed."""
    from backend.services.project_evm_service import (
        evaluate_evm_to_complete_schedule_performance_index_tspi as fn,
    )

    # 1.2 > default 1.10 -> UNACHIEVABLE con rebaseline.
    over = fn(20.0, 8.0, 10.0)
    assert over["tspi_pd"] == 1.2
    assert over["schedule_recovery_feasibility"] == "UNACHIEVABLE"
    assert over["requires_schedule_rebaseline"] is True

    # max 1.30 -> 1.2 en rango CHALLENGING, sin rebaseline.
    challenging = fn(20.0, 8.0, 10.0, max_achievable_tspi=1.30)
    assert challenging["schedule_recovery_feasibility"] == "CHALLENGING"
    assert challenging["requires_schedule_rebaseline"] is False

    # tspi_ed con estimated > 0 y > actual: 12 / (30-10) = 0.6
    with_estimate = fn(20.0, 8.0, 10.0, 30.0)
    assert with_estimate["tspi_ed"] == 0.6

    # estimated 0 o <= actual -> tspi_ed None.
    assert fn(20.0, 8.0, 10.0, 0.0)["tspi_ed"] is None
    assert fn(20.0, 8.0, 30.0, 20.0)["tspi_ed"] is None

    # Plazo original agotado con trabajo pendiente -> tspi_pd None -> UNACHIEVABLE.
    expired = fn(20.0, 10.0, 20.0)
    assert expired["tspi_pd"] is None
    assert expired["tspi_ed"] is None
    assert expired["schedule_recovery_feasibility"] == "UNACHIEVABLE"
    assert expired["requires_schedule_rebaseline"] is True


def test_evaluate_evm_tspi_validation_valueerrors():
    """Validaciones de dominio: ValueError en planned <= 0, negativos y max < 1.0."""
    import pytest

    from backend.services.project_evm_service import (
        evaluate_evm_to_complete_schedule_performance_index_tspi as fn,
    )

    invalid_cases = [
        ((0.0, 1.0, 1.0), {}),                 # planned_duration_days <= 0
        ((20.0, -1.0, 1.0), {}),                # earned_schedule_days < 0
        ((20.0, 1.0, -1.0), {}),                # actual_time_days < 0
        ((20.0, 1.0, 1.0, -5.0), {}),           # estimated_duration_days < 0
        ((20.0, 1.0, 1.0, 0.0), {"max_achievable_tspi": 0.9}),  # max < 1.0
    ]
    for args, kwargs in invalid_cases:
        with pytest.raises(ValueError):
            fn(*args, **kwargs)

    # Bloque kwarg-only en max_achievable_tspi.
    with pytest.raises(TypeError):
        fn(20.0, 10.0, 8.0, 25.0, 1.20)  # type: ignore[misc]


def test_evaluate_evm_tspi_proxy_staticmethod_and_all():
    """Proxy estatico en ProjectEVMService + entrada en __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_to_complete_schedule_performance_index_tspi as fn,
    )

    sample = (20.0, 10.0, 8.0)
    assert (
        ProjectEVMService.evaluate_evm_to_complete_schedule_performance_index_tspi(*sample)
        == fn(*sample)
    )
    assert "evaluate_evm_to_complete_schedule_performance_index_tspi" in mod.__all__


def test_evaluate_evm_loe_masking_and_discrete_variance_distortion_healthy():
    """Verifica estado HEALTHY cuando la proporción LOE es baja, EV==PV en LOE y el trabajo discreto cumple SPI."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_loe_masking_and_discrete_variance_distortion,
    )

    wps = [
        {
            "wp_id": "WP-DISC-01",
            "is_level_of_effort": False,
            "planned_value_pv": 85000.0,
            "earned_value_ev": 83300.0,
            "actual_cost_ac": 82000.0,
        },
        {
            "wp_id": "WP-LOE-PMO",
            "is_level_of_effort": True,
            "planned_value_pv": 15000.0,
            "earned_value_ev": 15000.0,
            "actual_cost_ac": 14800.0,
        },
    ]
    res = evaluate_evm_loe_masking_and_discrete_variance_distortion(
        wps, max_loe_share_pct=20.0, discrete_spi_alert_threshold=0.90
    )
    assert res == {
        "total_work_packages": 2,
        "loe_work_packages_count": 1,
        "loe_share_pct": 15.0,
        "composite_spi": 0.983,
        "discrete_only_spi": 0.98,
        "spi_masking_spread": 0.003,
        "is_loe_masking_discrete_delay": False,
        "loe_ev_pv_mismatch_wps": [],
        "loe_governance_status": "HEALTHY",
    }
    assert (
        ProjectEVMService.evaluate_evm_loe_masking_and_discrete_variance_distortion(wps)
        == res
    )


def test_evaluate_evm_loe_masking_and_discrete_variance_distortion_at_risk():
    """Verifica estado AT_RISK cuando el peso LOE supera max_loe_share_pct pero no enmascara atraso discreto ni tiene mismatch."""
    from backend.services.project_evm_service import (
        evaluate_evm_loe_masking_and_discrete_variance_distortion,
    )

    res = evaluate_evm_loe_masking_and_discrete_variance_distortion(
        [
            {
                "wp_id": "WP-DISC-OK",
                "is_level_of_effort": False,
                "planned_value_pv": 70000.0,
                "earned_value_ev": 68600.0,
                "actual_cost_ac": 68000.0,
            },
            {
                "wp_id": "WP-LOE-HEAVY",
                "is_level_of_effort": True,
                "planned_value_pv": 30000.0,
                "earned_value_ev": 30000.0,
                "actual_cost_ac": 30000.0,
            },
        ],
        max_loe_share_pct=20.0,
        discrete_spi_alert_threshold=0.90,
    )
    assert res["loe_share_pct"] == 30.0
    assert res["is_loe_masking_discrete_delay"] is False
    assert res["loe_governance_status"] == "AT_RISK"


def test_evaluate_evm_loe_masking_and_discrete_variance_distortion_critical_masking_and_mismatch():
    """Verifica estado CRITICAL cuando paquetes LOE maquillan un SPI discreto < 0.90 o presentan EV != PV."""
    from backend.services.project_evm_service import (
        evaluate_evm_loe_masking_and_discrete_variance_distortion,
    )

    res = evaluate_evm_loe_masking_and_discrete_variance_distortion(
        [
            {
                "wp_id": "WP-DISC-LAGGING",
                "is_level_of_effort": False,
                "planned_value_pv": 60000.0,
                "earned_value_ev": 51000.0,
                "actual_cost_ac": 55000.0,
            },
            {
                "wp_id": "WP-LOE-INFLATED",
                "is_level_of_effort": True,
                "planned_value_pv": 40000.0,
                "earned_value_ev": 41000.0,
                "actual_cost_ac": 40000.0,
            },
        ],
        max_loe_share_pct=20.0,
        discrete_spi_alert_threshold=0.90,
    )
    assert res["discrete_only_spi"] == 0.85
    assert res["composite_spi"] == 0.92
    assert res["is_loe_masking_discrete_delay"] is True
    assert res["loe_ev_pv_mismatch_wps"] == ["WP-LOE-INFLATED"]
    assert res["loe_governance_status"] == "CRITICAL"


def test_evaluate_evm_loe_masking_and_discrete_variance_distortion_empty_and_export():
    """Verifica manejo de entradas vacías o no secuencia y exportación en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_loe_masking_and_discrete_variance_distortion,
    )

    assert "evaluate_evm_loe_masking_and_discrete_variance_distortion" in _m.__all__
    for bad in ([], None, "invalid"):
        assert evaluate_evm_loe_masking_and_discrete_variance_distortion(bad) == {
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


def test_evaluate_evm_retroactive_change_and_negative_period_anomaly_healthy():
    """Periodos sin ajustes retroactivos no autorizados y con variaciones negativas justificadas -> HEALTHY."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_retroactive_change_and_negative_period_anomaly,
    )

    periods = [
        {
            "period_id": "2026-08",
            "period_pv": 25000.0,
            "period_ev": 24000.0,
            "period_ac": 23500.0,
            "prior_closed_period_adjusted": False,
            "authorized_reprogramming_cr_id": None,
            "justification_documented": False,
        },
        {
            "period_id": "2026-09",
            "period_pv": 20000.0,
            "period_ev": -1500.0,
            "period_ac": -500.0,
            "prior_closed_period_adjusted": True,
            "authorized_reprogramming_cr_id": "CR-EVM-104",
            "justification_documented": True,
        },
    ]
    res = evaluate_evm_retroactive_change_and_negative_period_anomaly(periods)
    assert res == {
        "total_periods_evaluated": 2,
        "compliant_periods_count": 2,
        "unauthorized_retroactive_periods_count": 0,
        "unexplained_negative_ev_pv_periods_count": 0,
        "unexplained_negative_ac_periods_count": 0,
        "period_accounting_integrity_status": "HEALTHY",
        "anomalies": [],
    }
    assert (
        ProjectEVMService.evaluate_evm_retroactive_change_and_negative_period_anomaly(
            periods
        )
        == res
    )


def test_evaluate_evm_retroactive_change_and_negative_period_anomaly_critical():
    """Detecta ajuste retroactivo sin CR o PV/EV negativo sin justificacion como CRITICAL."""
    from backend.services.project_evm_service import (
        evaluate_evm_retroactive_change_and_negative_period_anomaly,
    )

    res = evaluate_evm_retroactive_change_and_negative_period_anomaly(
        [
            {
                "period_id": "2026-05",
                "period_pv": 15000.0,
                "period_ev": 15000.0,
                "period_ac": 14000.0,
                "prior_closed_period_adjusted": True,
                "authorized_reprogramming_cr_id": "   ",
                "justification_documented": True,
            },
            {
                "period_id": "2026-06",
                "period_pv": 18000.0,
                "period_ev": -2000.0,
                "period_ac": 12000.0,
                "prior_closed_period_adjusted": False,
                "authorized_reprogramming_cr_id": None,
                "justification_documented": False,
            },
        ]
    )
    assert res["total_periods_evaluated"] == 2
    assert res["compliant_periods_count"] == 0
    assert res["unauthorized_retroactive_periods_count"] == 1
    assert res["unexplained_negative_ev_pv_periods_count"] == 1
    assert res["unexplained_negative_ac_periods_count"] == 0
    assert res["period_accounting_integrity_status"] == "CRITICAL"
    assert len(res["anomalies"]) == 2
    assert res["anomalies"][0]["period_id"] == "2026-05"
    assert "unauthorized_retroactive_baseline_change" in res["anomalies"][0]["reasons"]
    assert res["anomalies"][1]["period_id"] == "2026-06"
    assert "unexplained_negative_period_ev_or_pv" in res["anomalies"][1]["reasons"]


def test_evaluate_evm_retroactive_change_and_negative_period_anomaly_at_risk_negative_ac():
    """Detecta AC negativo sin justificacion (sin retroactivos ni EV/PV negativos) como AT_RISK."""
    from backend.services.project_evm_service import (
        evaluate_evm_retroactive_change_and_negative_period_anomaly,
    )

    res = evaluate_evm_retroactive_change_and_negative_period_anomaly(
        [
            {
                "period_id": "2026-07",
                "period_pv": 10000.0,
                "period_ev": 9500.0,
                "period_ac": -1200.0,
                "prior_closed_period_adjusted": False,
                "authorized_reprogramming_cr_id": None,
                "justification_documented": False,
            }
        ]
    )
    assert res["total_periods_evaluated"] == 1
    assert res["compliant_periods_count"] == 0
    assert res["unauthorized_retroactive_periods_count"] == 0
    assert res["unexplained_negative_ev_pv_periods_count"] == 0
    assert res["unexplained_negative_ac_periods_count"] == 1
    assert res["period_accounting_integrity_status"] == "AT_RISK"
    assert res["anomalies"] == [
        {
            "period_id": "2026-07",
            "reasons": ["unexplained_negative_period_ac"],
        }
    ]


def test_evaluate_evm_retroactive_change_and_negative_period_anomaly_empty_and_export():
    """Maneja entradas vacias o invalidas devolviendo HEALTHY y verifica exportacion en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_retroactive_change_and_negative_period_anomaly,
    )

    assert "evaluate_evm_retroactive_change_and_negative_period_anomaly" in _m.__all__
    for bad in ([], None, "invalid"):
        assert evaluate_evm_retroactive_change_and_negative_period_anomaly(bad) == {
            "total_periods_evaluated": 0,
            "compliant_periods_count": 0,
            "unauthorized_retroactive_periods_count": 0,
            "unexplained_negative_ev_pv_periods_count": 0,
            "unexplained_negative_ac_periods_count": 0,
            "period_accounting_integrity_status": "HEALTHY",
            "anomalies": [],
        }


def test_evaluate_evm_subcontractor_flowdown_and_invoice_overbilling_healthy():
    """Subcontratos con EV reclamado alineado al avance fisico y facturacion dentro de margen o respaldada por retencion -> HEALTHY."""
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_subcontractor_flowdown_and_invoice_overbilling,
    )

    subs = [
        {
            "subcontract_id": "SUB-01",
            "subcontract_bac": 100000.0,
            "claimed_ev": 50000.0,
            "physical_progress_verified_pct": 50.0,
            "billed_ac": 52000.0,
            "retention_withheld_amount": 0.0,
        },
        {
            "subcontract_id": "SUB-02",
            "subcontract_bac": 80000.0,
            "claimed_ev": 40000.0,
            "physical_progress_verified_pct": 50.0,
            "billed_ac": 48000.0,  # spread 10% > 5%, pero retencion 8000 cubre el exceso
            "retention_withheld_amount": 8000.0,
        },
    ]
    res = evaluate_evm_subcontractor_flowdown_and_invoice_overbilling(
        subs, max_advance_billing_spread_pct=5.0
    )
    assert res == {
        "total_subcontracts": 2,
        "compliant_subcontracts_count": 2,
        "ev_overstated_subcontracts_count": 0,
        "unbacked_overbilling_subcontracts_count": 0,
        "total_ev_overstatement_amount": 0.0,
        "subcontractor_evm_status": "HEALTHY",
        "discrepancies": [],
    }
    assert (
        ProjectEVMService.evaluate_evm_subcontractor_flowdown_and_invoice_overbilling(
            subs, max_advance_billing_spread_pct=5.0
        )
        == res
    )


def test_evaluate_evm_subcontractor_flowdown_and_invoice_overbilling_at_risk_ev_overstated():
    """Detecta sobredeclaracion de EV frente al avance fisico verificado sin sobrefacturacion AC como AT_RISK."""
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_flowdown_and_invoice_overbilling,
    )

    res = evaluate_evm_subcontractor_flowdown_and_invoice_overbilling(
        [
            {
                "subcontract_id": "SUB-EV-INFLATED",
                "subcontract_bac": 100000.0,
                "claimed_ev": 65000.0,
                "physical_progress_verified_pct": 50.0,
                "billed_ac": 50000.0,
                "retention_withheld_amount": 5000.0,
            }
        ],
        max_advance_billing_spread_pct=5.0,
    )
    assert res["total_subcontracts"] == 1
    assert res["compliant_subcontracts_count"] == 0
    assert res["ev_overstated_subcontracts_count"] == 1
    assert res["unbacked_overbilling_subcontracts_count"] == 0
    assert res["total_ev_overstatement_amount"] == 15000.0
    assert res["subcontractor_evm_status"] == "AT_RISK"
    assert res["discrepancies"] == [
        {
            "subcontract_id": "SUB-EV-INFLATED",
            "verified_ev": 50000.0,
            "ev_overstatement_amount": 15000.0,
            "reasons": ["claimed_ev_exceeds_verified_physical_progress"],
        }
    ]


def test_evaluate_evm_subcontractor_flowdown_and_invoice_overbilling_critical_overbilling():
    """Detecta sobrefacturacion AC por encima del avance fisico sin retencion suficiente como CRITICAL."""
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_flowdown_and_invoice_overbilling,
    )

    res = evaluate_evm_subcontractor_flowdown_and_invoice_overbilling(
        [
            {
                "subcontract_id": "SUB-OVERBILLED",
                "subcontract_bac": 100000.0,
                "claimed_ev": 40000.0,
                "physical_progress_verified_pct": 40.0,
                "billed_ac": 55000.0,  # spread 15% > 5%, exceso 15000 > retencion 5000
                "retention_withheld_amount": 5000.0,
            }
        ],
        max_advance_billing_spread_pct=5.0,
    )
    assert res["total_subcontracts"] == 1
    assert res["compliant_subcontracts_count"] == 0
    assert res["ev_overstated_subcontracts_count"] == 0
    assert res["unbacked_overbilling_subcontracts_count"] == 1
    assert res["subcontractor_evm_status"] == "CRITICAL"
    assert "unbacked_invoice_overbilling" in res["discrepancies"][0]["reasons"]


def test_evaluate_evm_subcontractor_flowdown_and_invoice_overbilling_empty_and_export():
    """Maneja entradas vacias o invalidas devolviendo HEALTHY y verifica exportacion en __all__."""
    import backend.services.project_evm_service as _m
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_flowdown_and_invoice_overbilling,
    )

    assert "evaluate_evm_subcontractor_flowdown_and_invoice_overbilling" in _m.__all__
    for bad in ([], None, "invalid"):
        assert evaluate_evm_subcontractor_flowdown_and_invoice_overbilling(bad) == {
            "total_subcontracts": 0,
            "compliant_subcontracts_count": 0,
            "ev_overstated_subcontracts_count": 0,
            "unbacked_overbilling_subcontracts_count": 0,
            "total_ev_overstatement_amount": 0.0,
            "subcontractor_evm_status": "HEALTHY",
            "discrepancies": [],
        }


def test_evaluate_evm_earning_rule_gaming_and_duration_split_healthy():
    """Paquetes saludables con 0_100 (1 período), 50_50 (<=2 períodos sin estancamiento) y weighted_milestones."""
    from backend.services.project_evm_service import (
        evaluate_evm_earning_rule_gaming_and_duration_split,
    )

    wps = [
        {
            "id": "WP-01",
            "earning_rule": "0_100",
            "planned_reporting_periods": 1,
            "periods_in_progress": 1,
            "claimed_ev_pct": 100.0,
            "bac": 10000.0,
        },
        {
            "id": "WP-02",
            "earning_rule": "50_50",
            "planned_reporting_periods": 2,
            "periods_in_progress": 1,
            "claimed_ev_pct": 50.0,
            "bac": 20000.0,
        },
        {
            "id": "WP-03",
            "earning_rule": "weighted_milestones",
            "planned_reporting_periods": 4,
            "periods_in_progress": 2,
            "claimed_ev_pct": 65.0,
            "bac": 50000.0,
        },
    ]
    res = evaluate_evm_earning_rule_gaming_and_duration_split(wps)
    assert res["total_work_packages"] == 3
    assert res["compliant_work_packages"] == 3
    assert res["inappropriate_0_100_duration_ids"] == []
    assert res["inappropriate_50_50_duration_ids"] == []
    assert res["stalled_50_50_opening_credit_ids"] == []
    assert res["rule_credit_violation_ids"] == []
    assert res["premature_ev_exposure_amount"] == 0.0
    assert res["evmt_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_evaluate_evm_earning_rule_gaming_and_duration_split_at_risk_duration():
    """Detecta inappropriate_0_100_duration_ids y inappropriate_50_50_duration_ids (at_risk)."""
    from backend.services.project_evm_service import (
        evaluate_evm_earning_rule_gaming_and_duration_split,
    )

    wps = [
        {
            "wp_id": "WP-10",
            "earning_rule": "0_100",
            "planned_reporting_periods": 3,
            "periods_in_progress": 1,
            "claimed_ev_pct": 0.0,
            "bac": 15000.0,
        },
        {
            "wp_id": "WP-11",
            "earning_rule": "50_50",
            "planned_reporting_periods": 4,
            "periods_in_progress": 1,
            "claimed_ev_pct": 50.0,
            "bac": 30000.0,
        },
    ]
    res = evaluate_evm_earning_rule_gaming_and_duration_split(wps)
    assert res["total_work_packages"] == 2
    assert res["compliant_work_packages"] == 0
    assert res["inappropriate_0_100_duration_ids"] == ["WP-10"]
    assert res["inappropriate_50_50_duration_ids"] == ["WP-11"]
    assert res["stalled_50_50_opening_credit_ids"] == []
    assert res["rule_credit_violation_ids"] == []
    assert res["premature_ev_exposure_amount"] == 15000.0
    assert res["evmt_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_earning_rule_gaming_and_duration_split_critical_stalled_and_violation():
    """Detecta stalled_50_50_opening_credit_ids y rule_credit_violation_ids (critical y premature_ev_exposure_amount)."""
    from backend.services.project_evm_service import (
        evaluate_evm_earning_rule_gaming_and_duration_split,
    )

    wps = [
        {
            "wp_id": "WP-20",
            "earning_rule": "50_50",
            "planned_reporting_periods": 2,
            "periods_in_progress": 3,
            "claimed_ev_pct": 50.0,
            "bac": 40000.0,
        },
        {
            "wp_id": "WP-21",
            "earning_rule": "0_100",
            "planned_reporting_periods": 1,
            "periods_in_progress": 1,
            "claimed_ev_pct": 40.0,
            "bac": 10000.0,
        },
        {
            "wp_id": "WP-22",
            "earning_rule": "50_50",
            "planned_reporting_periods": 2,
            "periods_in_progress": 1,
            "claimed_ev_pct": 75.0,
            "bac": 20000.0,
        },
    ]
    res = evaluate_evm_earning_rule_gaming_and_duration_split(wps)
    assert res["total_work_packages"] == 3
    assert res["compliant_work_packages"] == 0
    assert res["stalled_50_50_opening_credit_ids"] == ["WP-20"]
    assert res["rule_credit_violation_ids"] == ["WP-21", "WP-22"]
    assert res["premature_ev_exposure_amount"] == 39000.0
    assert res["evmt_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_earning_rule_gaming_and_duration_split_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectEVMService y __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_earning_rule_gaming_and_duration_split,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_earning_rule_gaming_and_duration_split(payload)  # type: ignore[arg-type]
        assert empty["total_work_packages"] == 0
        assert empty["compliant_work_packages"] == 0
        assert empty["premature_ev_exposure_amount"] == 0.0
        assert empty["evmt_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "WP-99",
            "earning_rule": "0_100",
            "planned_reporting_periods": 1,
            "periods_in_progress": 1,
            "claimed_ev_pct": 0.0,
            "bac": 5000.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_earning_rule_gaming_and_duration_split(sample)
        == evaluate_evm_earning_rule_gaming_and_duration_split(sample)
    )
    assert "evaluate_evm_earning_rule_gaming_and_duration_split" in mod.__all__


def test_evaluate_evm_cost_schedule_index_compound_degradation_healthy():
    """Cuentas de control con CPI y SPI equilibrados y CSI >= 0.90 (healthy)."""
    from backend.services.project_evm_service import (
        evaluate_evm_cost_schedule_index_compound_degradation,
    )

    cas = [
        {"id": "CA-01", "cpi": 1.02, "spi": 0.98, "pct_complete": 35.0},
        {"id": "CA-02", "cpi": 0.96, "spi": 0.95, "pct_complete": 50.0},
    ]
    res = evaluate_evm_cost_schedule_index_compound_degradation(cas)
    assert res["total_accounts"] == 2
    assert res["compliant_accounts"] == 2
    assert res["min_csi"] == 0.912
    assert res["tradeoff_masking_ids"] == []
    assert res["warning_compound_degradation_ids"] == []
    assert res["critical_compound_degradation_ids"] == []
    assert res["post_gate_irrecoverable_ids"] == []
    assert res["csi_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_evaluate_evm_cost_schedule_index_compound_degradation_at_risk_warning_and_tradeoff():
    """Detecta warning_compound_degradation_ids (0.80 <= CSI < 0.90) y tradeoff_masking_ids (at_risk)."""
    from backend.services.project_evm_service import (
        evaluate_evm_cost_schedule_index_compound_degradation,
    )

    cas = [
        {"ca_id": "CA-10", "cpi": 0.92, "spi": 0.92, "pct_complete": 25.0},  # csi=0.8464
        {"ca_id": "CA-11", "cpi": 0.85, "spi": 1.10, "pct_complete": 40.0},  # csi=0.935, tradeoff
    ]
    res = evaluate_evm_cost_schedule_index_compound_degradation(cas)
    assert res["total_accounts"] == 2
    assert res["compliant_accounts"] == 0
    assert res["warning_compound_degradation_ids"] == ["CA-10"]
    assert res["tradeoff_masking_ids"] == ["CA-11"]
    assert res["critical_compound_degradation_ids"] == []
    assert res["post_gate_irrecoverable_ids"] == []
    assert res["csi_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_cost_schedule_index_compound_degradation_critical_and_irrecoverable():
    """Detecta critical_compound_degradation_ids y post_gate_irrecoverable_ids (CSI < 0.80 con pct_complete >= 20%)."""
    from backend.services.project_evm_service import (
        evaluate_evm_cost_schedule_index_compound_degradation,
    )

    cas = [
        {"ca_id": "CA-20", "cpi": 0.85, "spi": 0.85, "pct_complete": 10.0},  # csi=0.7225 (<20%)
        {"ca_id": "CA-21", "cpi": 0.80, "spi": 0.85, "pct_complete": 30.0},  # csi=0.68 (>=20%)
    ]
    res = evaluate_evm_cost_schedule_index_compound_degradation(cas)
    assert res["total_accounts"] == 2
    assert res["compliant_accounts"] == 0
    assert res["min_csi"] == 0.68
    assert res["critical_compound_degradation_ids"] == ["CA-20", "CA-21"]
    assert res["post_gate_irrecoverable_ids"] == ["CA-21"]
    assert res["csi_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_cost_schedule_index_compound_degradation_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectEVMService y __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_cost_schedule_index_compound_degradation,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_cost_schedule_index_compound_degradation(payload)  # type: ignore[arg-type]
        assert empty["total_accounts"] == 0
        assert empty["compliant_accounts"] == 0
        assert empty["min_csi"] == 1.0
        assert empty["csi_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [{"id": "CA-99", "cpi": 1.0, "spi": 1.0, "pct_complete": 15.0}]
    assert (
        ProjectEVMService.evaluate_evm_cost_schedule_index_compound_degradation(
            sample
        )
        == evaluate_evm_cost_schedule_index_compound_degradation(sample)
    )
    assert "evaluate_evm_cost_schedule_index_compound_degradation" in mod.__all__


def test_evaluate_evm_undistributed_budget_and_planning_package_aging_healthy():
    """Valida partidas UB recientes y acotadas con alcance vinculado, PP lejanos y WP con EV legítimo."""
    from backend.services.project_evm_service import (
        evaluate_evm_undistributed_budget_and_planning_package_aging,
    )

    buckets = [
        {
            "id": "BKT-01",
            "bucket_type": "undistributed_budget",
            "amount": 5000.0,
            "pmb_total": 100000.0,
            "days_held_in_ub": 12,
            "scope_statement_linked": True,
            "ev_claimed": 0.0,
        },
        {
            "id": "BKT-02",
            "bucket_type": "planning_package",
            "amount": 25000.0,
            "pmb_total": 100000.0,
            "days_until_scheduled_start": 60,
            "scope_statement_linked": True,
            "ev_claimed": 0.0,
        },
        {
            "id": "BKT-03",
            "bucket_type": "work_package",
            "amount": 70000.0,
            "pmb_total": 100000.0,
            "scope_statement_linked": True,
            "ev_claimed": 35000.0,
        },
    ]
    res = evaluate_evm_undistributed_budget_and_planning_package_aging(buckets)
    assert res["total_buckets"] == 3
    assert res["compliant_buckets"] == 3
    assert res["total_ub_amount"] == 5000.0
    assert res["stale_or_unscoped_ub_ids"] == []
    assert res["unconverted_imminent_planning_package_ids"] == []
    assert res["illegal_ev_on_non_work_package_ids"] == []
    assert res["pmb_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_evaluate_evm_undistributed_budget_and_planning_package_aging_at_risk():
    """Detecta UB estancado/excesivo y Planning Package inminente sin convertir ('at_risk')."""
    from backend.services.project_evm_service import (
        evaluate_evm_undistributed_budget_and_planning_package_aging,
    )

    buckets = [
        {
            "bucket_id": "BKT-10",
            "bucket_type": "undistributed_budget",
            "amount": 15000.0,
            "pmb_total": 100000.0,
            "days_held_in_ub": 45,
            "scope_statement_linked": False,
            "ev_claimed": 0.0,
        },
        {
            "bucket_id": "BKT-11",
            "bucket_type": "planning_package",
            "amount": 20000.0,
            "pmb_total": 100000.0,
            "days_until_scheduled_start": 10,
            "scope_statement_linked": True,
            "ev_claimed": 0.0,
        },
    ]
    res = evaluate_evm_undistributed_budget_and_planning_package_aging(buckets)
    assert res["total_buckets"] == 2
    assert res["compliant_buckets"] == 0
    assert res["stale_or_unscoped_ub_ids"] == ["BKT-10"]
    assert res["unconverted_imminent_planning_package_ids"] == ["BKT-11"]
    assert res["illegal_ev_on_non_work_package_ids"] == []
    assert res["pmb_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_undistributed_budget_and_planning_package_aging_critical_illegal_ev():
    """Detecta reclamo ilegal de Earned Value sobre UB o Planning Package ('critical')."""
    from backend.services.project_evm_service import (
        evaluate_evm_undistributed_budget_and_planning_package_aging,
    )

    buckets = [
        {
            "id": "BKT-20",
            "bucket_type": "undistributed_budget",
            "amount": 4000.0,
            "pmb_total": 100000.0,
            "days_held_in_ub": 5,
            "scope_statement_linked": True,
            "ev_claimed": 1500.0,
        },
        {
            "id": "BKT-21",
            "bucket_type": "planning_package",
            "amount": 18000.0,
            "pmb_total": 100000.0,
            "days_until_scheduled_start": 45,
            "scope_statement_linked": True,
            "ev_claimed": 3000.0,
        },
    ]
    res = evaluate_evm_undistributed_budget_and_planning_package_aging(buckets)
    assert res["total_buckets"] == 2
    assert res["compliant_buckets"] == 0
    assert res["illegal_ev_on_non_work_package_ids"] == ["BKT-20", "BKT-21"]
    assert res["pmb_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_evaluate_evm_undistributed_budget_and_planning_package_aging_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectEVMService y __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_undistributed_budget_and_planning_package_aging,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_undistributed_budget_and_planning_package_aging(payload)  # type: ignore[arg-type]
        assert empty["total_buckets"] == 0
        assert empty["compliant_buckets"] == 0
        assert empty["total_ub_amount"] == 0.0
        assert empty["pmb_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "BKT-99",
            "bucket_type": "undistributed_budget",
            "amount": 2000.0,
            "pmb_total": 50000.0,
            "days_held_in_ub": 10,
            "scope_statement_linked": True,
            "ev_claimed": 0.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_undistributed_budget_and_planning_package_aging(
            sample
        )
        == evaluate_evm_undistributed_budget_and_planning_package_aging(sample)
    )
    assert (
        "evaluate_evm_undistributed_budget_and_planning_package_aging"
        in mod.__all__
    )








def test_evm_cv_decomposition_healthy_and_rate_breach():
    """Paquete conforme -> compliany; desvío de tarifa sobre umbral -> breach (acciones log OK evita regla 3)."""
    from backend.services.project_evm_service import (
        evaluate_evm_cost_variance_rate_vs_efficiency_decomposition,
    )

    healthy = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-1",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 52.0,
                "earned_hours": 100.0,
                "actual_hours": 95.0,
                "corrective_action_logged": False,
            }
        ]
    )
    assert healthy["total_packages"] == 1
    assert healthy["compliant_packages_count"] == 1
    assert healthy["adverse_rate_variance_breach_count"] == 0
    assert healthy["adverse_efficiency_variance_breach_count"] == 0
    assert healthy["unaddressed_negative_cv_count"] == 0
    assert healthy["total_rate_variance"] == -190.0
    assert healthy["total_efficiency_variance"] == 250.0
    assert healthy["cv_decomposition_status"] == "HEALTHY"
    assert healthy["violations"] == []

    # Brecha de tarifa: 20% desvío; CV negativo pero con acción logueada -> solo breach de tarifa.
    rate = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-2",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 60.0,
                "earned_hours": 100.0,
                "actual_hours": 100.0,
                "corrective_action_logged": True,
            }
        ]
    )
    assert rate["adverse_rate_variance_breach_count"] == 1
    assert rate["adverse_efficiency_variance_breach_count"] == 0
    assert rate["unaddressed_negative_cv_count"] == 0  # acción logueada
    assert rate["violations"][0]["reasons"] == ["adverse_rate_variance_breach"]
    assert rate["total_rate_variance"] == -1000.0
    assert rate["cv_decomposition_status"] == "AT_RISK"

    # Límite exacto: 10% de desvío no es breach (comparación estricta).
    at_limit = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-3",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 55.0,
                "earned_hours": 100.0,
                "actual_hours": 100.0,
                "corrective_action_logged": True,
            }
        ]
    )
    assert at_limit["adverse_rate_variance_breach_count"] == 0
    assert at_limit["cv_decomposition_status"] == "HEALTHY"


def test_evm_cv_decomposition_efficiency_and_negative_cv():
    """Exceso de horas 30% -> breach eficiencia; CV negativo sin acción -> CRITICAL."""
    from backend.services.project_evm_service import (
        evaluate_evm_cost_variance_rate_vs_efficiency_decomposition,
    )

    adverse_eff = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-4",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 50.0,
                "earned_hours": 100.0,
                "actual_hours": 130.0,
            }
        ]
    )
    assert adverse_eff["adverse_efficiency_variance_breach_count"] == 1
    assert adverse_eff["unaddressed_negative_cv_count"] == 1  # ev 5000 - ac 6500 < 0 sin acción
    assert adverse_eff["violations"][0]["reasons"] == [
        "adverse_efficiency_variance_breach",
        "unaddressed_negative_cv",
    ]
    assert adverse_eff["total_efficiency_variance"] == -1500.0
    assert adverse_eff["cv_decomposition_status"] == "CRITICAL"

    # Exceso exacto 15% no es breach; CV negativo sin acción -> CRITICAL solo por negCV.
    at_limit = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-5",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 50.0,
                "earned_hours": 100.0,
                "actual_hours": 115.0,
            }
        ]
    )
    assert at_limit["adverse_efficiency_variance_breach_count"] == 0
    assert at_limit["unaddressed_negative_cv_count"] == 1
    assert at_limit["cv_decomposition_status"] == "CRITICAL"

    # CV negativo con acción logueada -> sin hallazgos de negCV.
    logged = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-6",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 55.0,
                "earned_hours": 100.0,
                "actual_hours": 105.0,
                "corrective_action_logged": True,
            }
        ]
    )
    assert logged["unaddressed_negative_cv_count"] == 0
    assert logged["cv_decomposition_status"] == "HEALTHY"


def test_evm_cv_decomposition_status_precedence():
    """Doble breach -> CRITICAL; single breach -> AT_RISK; negativo importante domina."""
    from backend.services.project_evm_service import (
        evaluate_evm_cost_variance_rate_vs_efficiency_decomposition,
    )

    both = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-7",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 60.0,
                "earned_hours": 100.0,
                "actual_hours": 130.0,
                "corrective_action_logged": True,
            }
        ]
    )
    assert both["adverse_rate_variance_breach_count"] == 1
    assert both["adverse_efficiency_variance_breach_count"] == 1
    assert both["unaddressed_negative_cv_count"] == 0
    assert both["violations"][0]["reasons"] == [
        "adverse_rate_variance_breach",
        "adverse_efficiency_variance_breach",
    ]
    assert both["cv_decomposition_status"] == "CRITICAL"

    mixed_units = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            {
                "wp_id": "WP-8",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 60.0,
                "earned_hours": 100.0,
                "actual_hours": 100.0,
                "corrective_action_logged": True,
            },
            {
                "wp_id": "WP-9",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 50.0,
                "earned_hours": 100.0,
                "actual_hours": 130.0,
                "corrective_action_logged": True,
            },
        ]
    )
    assert mixed_units["adverse_rate_variance_breach_count"] == 1
    assert mixed_units["adverse_efficiency_variance_breach_count"] == 1
    # Doble breach a nivel agregado -> aunque packages distintos -> CRITICAL
    assert mixed_units["cv_decomposition_status"] == "CRITICAL"
    assert mixed_units["total_rate_variance"] == -1000.0
    assert mixed_units["total_efficiency_variance"] == -1500.0


def test_evm_cv_decomposition_neutral_and_binding():
    """No-lista/None -> vacío; no-dict ignorados; proxy @staticmethod y __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_cost_variance_rate_vs_efficiency_decomposition,
    )

    for payload in (None, "not-a-list", 42):
        empty = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(payload)
        assert empty["total_packages"] == 0
        assert empty["compliant_packages_count"] == 0
        assert empty["total_rate_variance"] == 0.0
        assert empty["total_efficiency_variance"] == 0.0
        assert empty["cv_decomposition_status"] == "HEALTHY"
        assert empty["violations"] == []

    mixed = evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(
        [
            "no-dict",
            42,
            None,
            {
                "wp_id": "WP-10",
                "planned_hourly_rate": 50.0,
                "actual_hourly_rate": 50.0,
                "earned_hours": 80.0,
                "actual_hours": 80.0,
                "corrective_action_logged": True,
            },
        ]
    )
    assert mixed["total_packages"] == 1
    assert mixed["compliant_packages_count"] == 1
    assert mixed["total_rate_variance"] == 0.0
    assert mixed["total_efficiency_variance"] == 0.0
    assert mixed["violations"] == []

    sample = [
        {
            "wp_id": "WP-11",
            "planned_hourly_rate": 50.0,
            "actual_hourly_rate": 60.0,
            "earned_hours": 100.0,
            "actual_hours": 130.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(sample)
        == evaluate_evm_cost_variance_rate_vs_efficiency_decomposition(sample)
    )
    assert "evaluate_evm_cost_variance_rate_vs_efficiency_decomposition" in mod.__all__


def test_evaluate_evm_contract_fee_and_pta_fpif_on_and_over_target():
    """Valida contrato FPIF bajo costo objetivo ('ON_OR_UNDER_TARGET') y con sobrecosto compartido antes del PTA ('COST_OVERRUN_SHARED')."""
    from backend.services.project_evm_service import (
        evaluate_evm_contract_fee_and_point_of_total_assumption,
    )

    under = evaluate_evm_contract_fee_and_point_of_total_assumption(
        contract_type="FPIF",
        target_cost=100000.0,
        target_price=115000.0,
        ceiling_price=136000.0,
        buyer_share_ratio=0.70,
        seller_share_ratio=0.30,
        estimated_actual_cost_eac=90000.0,
    )
    assert under["target_fee"] == 15000.0
    assert under["point_of_total_assumption_pta"] == 130000.0
    assert under["cost_overrun_or_underrun"] == -10000.0
    assert under["raw_fee"] == 18000.0
    assert under["projected_seller_fee"] == 18000.0
    assert under["projected_buyer_total_price"] == 108000.0
    assert under["has_breached_pta"] is False
    assert under["has_breached_ceiling"] is False
    assert under["contract_exposure_status"] == "ON_OR_UNDER_TARGET"
    assert under["issues"] == []

    shared = evaluate_evm_contract_fee_and_point_of_total_assumption(
        contract_type="FPIF",
        target_cost=100000.0,
        target_price=115000.0,
        ceiling_price=136000.0,
        buyer_share_ratio=0.70,
        seller_share_ratio=0.30,
        estimated_actual_cost_eac=110000.0,
    )
    assert shared["cost_overrun_or_underrun"] == 10000.0
    assert shared["raw_fee"] == 12000.0
    assert shared["projected_seller_fee"] == 12000.0
    assert shared["projected_buyer_total_price"] == 122000.0
    assert shared["has_breached_pta"] is False
    assert shared["contract_exposure_status"] == "COST_OVERRUN_SHARED"


def test_evaluate_evm_contract_fee_and_pta_fpif_pta_and_ceiling_breach():
    """Detecta cruce del PTA y del precio techo en FPIF ('PTA_OR_CEILING_BREACH')."""
    from backend.services.project_evm_service import (
        evaluate_evm_contract_fee_and_point_of_total_assumption,
    )

    pta_breach = evaluate_evm_contract_fee_and_point_of_total_assumption(
        contract_type="FPIF",
        target_cost=100000.0,
        target_price=115000.0,
        ceiling_price=136000.0,
        buyer_share_ratio=0.70,
        seller_share_ratio=0.30,
        estimated_actual_cost_eac=130000.0,
    )
    assert pta_breach["point_of_total_assumption_pta"] == 130000.0
    assert pta_breach["has_breached_pta"] is True
    assert pta_breach["has_breached_ceiling"] is False
    assert pta_breach["projected_buyer_total_price"] == 136000.0
    assert pta_breach["projected_seller_fee"] == 6000.0
    assert pta_breach["contract_exposure_status"] == "PTA_OR_CEILING_BREACH"
    assert len(pta_breach["issues"]) == 1

    ceiling_breach = evaluate_evm_contract_fee_and_point_of_total_assumption(
        contract_type="FPIF",
        target_cost=100000.0,
        target_price=115000.0,
        ceiling_price=136000.0,
        buyer_share_ratio=0.70,
        seller_share_ratio=0.30,
        estimated_actual_cost_eac=140000.0,
    )
    assert ceiling_breach["has_breached_pta"] is True
    assert ceiling_breach["has_breached_ceiling"] is True
    assert ceiling_breach["projected_buyer_total_price"] == 136000.0
    assert ceiling_breach["projected_seller_fee"] == -4000.0
    assert ceiling_breach["contract_exposure_status"] == "PTA_OR_CEILING_BREACH"
    assert len(ceiling_breach["issues"]) == 2


def test_evaluate_evm_contract_fee_and_pta_cpif_min_max_fee_clamping():
    """Valida límites min_fee y max_fee en contratos CPIF y ausencia de PTA."""
    from backend.services.project_evm_service import (
        evaluate_evm_contract_fee_and_point_of_total_assumption,
    )

    capped_max = evaluate_evm_contract_fee_and_point_of_total_assumption(
        contract_type="CPIF",
        target_cost=100000.0,
        target_price=110000.0,
        buyer_share_ratio=0.60,
        seller_share_ratio=0.40,
        estimated_actual_cost_eac=60000.0,
        min_fee=4000.0,
        max_fee=18000.0,
    )
    assert capped_max["point_of_total_assumption_pta"] is None
    assert capped_max["raw_fee"] == 26000.0
    assert capped_max["projected_seller_fee"] == 18000.0
    assert capped_max["projected_buyer_total_price"] == 78000.0
    assert capped_max["contract_exposure_status"] == "ON_OR_UNDER_TARGET"

    floored_min = evaluate_evm_contract_fee_and_point_of_total_assumption(
        contract_type="CPIF",
        target_cost=100000.0,
        target_price=110000.0,
        buyer_share_ratio=0.60,
        seller_share_ratio=0.40,
        estimated_actual_cost_eac=150000.0,
        min_fee=4000.0,
        max_fee=18000.0,
    )
    assert floored_min["raw_fee"] == -10000.0
    assert floored_min["projected_seller_fee"] == 4000.0
    assert floored_min["projected_buyer_total_price"] == 154000.0
    assert floored_min["contract_exposure_status"] == "COST_OVERRUN_SHARED"


def test_evaluate_evm_contract_fee_and_pta_invalid_share_ratio_and_binding():
    """Detecta suma inválida de share ratios y verifica binding en ProjectEVMService y __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_contract_fee_and_point_of_total_assumption,
    )

    bad_shares = evaluate_evm_contract_fee_and_point_of_total_assumption(
        contract_type="FPIF",
        target_cost=100000.0,
        target_price=115000.0,
        ceiling_price=135000.0,
        buyer_share_ratio=0.80,
        seller_share_ratio=0.30,
        estimated_actual_cost_eac=100000.0,
    )
    assert bad_shares["share_ratio_sum_valid"] is False
    assert bad_shares["contract_exposure_status"] == "PTA_OR_CEILING_BREACH"
    assert len(bad_shares["issues"]) == 1

    assert (
        ProjectEVMService.evaluate_evm_contract_fee_and_point_of_total_assumption(
            target_cost=50000.0,
            target_price=55000.0,
            ceiling_price=65000.0,
            estimated_actual_cost_eac=50000.0,
        )
        == evaluate_evm_contract_fee_and_point_of_total_assumption(
            target_cost=50000.0,
            target_price=55000.0,
            ceiling_price=65000.0,
            estimated_actual_cost_eac=50000.0,
        )
    )
    assert (
        "evaluate_evm_contract_fee_and_point_of_total_assumption"
        in mod.__all__
    )


def test_earned_schedule_eac_t_tspi_on_track_and_recoverable():
    """Proyecto en track -> ON_OR_AHEAD; desvío reciente <= TSPI tolerable -> BEHIND_RECOVERABLE."""
    from backend.services.project_evm_service import (
        evaluate_evm_earned_schedule_eac_t_and_tspi,
    )

    on_track = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=8.0,
        actual_time_months=8.0,
        planned_duration_months=12.0,
        target_completion_months=0.0,
    )
    assert on_track["time_variance_tv_months"] == 0.0
    assert on_track["spi_t"] == 1.0
    assert on_track["independent_eac_t_months"] == 12.0
    assert on_track["tspi"] == 1.0
    assert on_track["is_schedule_recoverable"] is True
    assert on_track["earned_schedule_status"] == "ON_OR_AHEAD_OF_TIME"

    recoverable = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=5.5,
        actual_time_months=6.0,
        planned_duration_months=12.0,
    )
    assert recoverable["time_variance_tv_months"] == -0.5
    assert recoverable["spi_t"] == round(5.5 / 6.0, 4)
    # remaining_work=6.5, remaining_time=6 -> tspi 1.0833 <= 1.10
    assert recoverable["tspi"] == round(6.5 / 6.0, 4)
    assert recoverable["is_schedule_recoverable"] is True
    assert recoverable["earned_schedule_status"] == "BEHIND_RECOVERABLE"

    # spi_t >= 0.95 con descarga sobre target custom más holgado.
    on_target = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=11.4,
        actual_time_months=12.0,
        planned_duration_months=12.0,
        target_completion_months=14.0,
    )
    assert on_target["spi_t"] == 0.95
    assert on_target["earned_schedule_status"] == "ON_OR_AHEAD_OF_TIME"


def test_earned_schedule_eac_t_tspi_unrecoverable_and_limits():
    """TSPI > max_feasible o remaining_time <= 0 -> UNRECOVERABLE_SLIP; bottleneck tspi=999."""
    from backend.services.project_evm_service import (
        evaluate_evm_earned_schedule_eac_t_and_tspi,
    )

    over = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=4.0,
        actual_time_months=6.0,
        planned_duration_months=12.0,
    )
    assert over["spi_t"] == round(4.0 / 6.0, 4)
    assert over["tspi"] == round(8.0 / 6.0, 4)          # 1.3333 > 1.10
    assert over["is_schedule_recoverable"] is False
    assert over["earned_schedule_status"] == "UNRECOVERABLE_SLIP"

    dead = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=5.0,
        actual_time_months=12.0,
        planned_duration_months=12.0,
    )
    # remaining_time = 12 - 12 = 0 -> tspi 999.0 (bottleneck)
    assert dead["tspi"] == 999.0
    assert dead["is_schedule_recoverable"] is False

    # max_feasible custom ensancha el umbral de recuperación.
    custom = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=4.0,
        actual_time_months=6.0,
        planned_duration_months=12.0,
        max_feasible_tspi=1.40,
    )
    assert custom["is_schedule_recoverable"] is True
    assert custom["earned_schedule_status"] == "BEHIND_RECOVERABLE"

    # default max 1.10: límite exacto 1.10 -> recuperable.
    at_limit = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=6.0,
        actual_time_months=6.1,
        planned_duration_months=12.0,
    )
    # remaining_work=6, remaining_time=5.9 -> ts=1.0169 <= 1.07 (recuperable, es menor)
    assert at_limit["is_schedule_recoverable"] is True
    assert at_limit["tspi"] == round(6.0 / 5.9, 4)


def test_earned_schedule_eac_t_tspi_boundary_zero_cases():
    """AT=0 -> spi_t=1.0; ES == PD -> tspi=0.0 recuperable; EAC(t) redondeo 2 dec."""
    from backend.services.project_evm_service import (
        evaluate_evm_earned_schedule_eac_t_and_tspi,
    )

    at_zero = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=5.0,
        actual_time_months=0.0,
        planned_duration_months=12.0,
    )
    assert at_zero["spi_t"] == 1.0
    assert at_zero["independent_eac_t_months"] == 12.0
    assert at_zero["time_variance_tv_months"] == 5.0
    assert at_zero["earned_schedule_status"] == "ON_OR_AHEAD_OF_TIME"

    completed = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=12.0,
        actual_time_months=12.0,
        planned_duration_months=12.0,
    )
    assert completed["tspi"] == 0.0
    assert completed["is_schedule_recoverable"] is True
    assert completed["earned_schedule_status"] == "ON_OR_AHEAD_OF_TIME"

    # EAC(t) con redondeo 2 decimales: ES=7, AT=9, PD=15 -> spi=0.7778, 15/0.7778=19.29.
    rounded = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=7.0,
        actual_time_months=9.0,
        planned_duration_months=15.0,
    )
    assert rounded["spi_t"] == round(7.0 / 9.0, 4)
    assert rounded["independent_eac_t_months"] == round(15.0 / (7.0 / 9.0), 2)
    assert isinstance(rounded["independent_eac_t_months"], float)

    # Target custom acota remaining_time.
    target_custom = evaluate_evm_earned_schedule_eac_t_and_tspi(
        earned_schedule_months=6.0,
        actual_time_months=8.0,
        planned_duration_months=12.0,
        target_completion_months=10.0,
    )
    # effective_target=10, remaining_time=2; remaining_work=6 -> tspi=3.0
    assert target_custom["tspi"] == 3.0
    assert target_custom["earned_schedule_status"] == "UNRECOVERABLE_SLIP"


def test_earned_schedule_eac_t_tspi_neutral_and_binding():
    """Default sin args: TV=0.0, spi=1.0, EAC=0.0, tspi=0.0, verificado via proxy y __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_earned_schedule_eac_t_and_tspi,
    )

    defaults = evaluate_evm_earned_schedule_eac_t_and_tspi()
    assert defaults["time_variance_tv_months"] == 0.0
    assert defaults["spi_t"] == 1.0
    assert defaults["independent_eac_t_months"] == 0.0
    assert defaults["tspi"] == 0.0
    assert defaults["is_schedule_recoverable"] is True
    assert defaults["earned_schedule_status"] == "ON_OR_AHEAD_OF_TIME"

    sample = {
        "earned_schedule_months": 6.0,
        "actual_time_months": 8.0,
        "planned_duration_months": 12.0,
    }
    assert (
        ProjectEVMService.evaluate_evm_earned_schedule_eac_t_and_tspi(**sample)
        == evaluate_evm_earned_schedule_eac_t_and_tspi(**sample)
    )
    assert "evaluate_evm_earned_schedule_eac_t_and_tspi" in mod.__all__


def test_evm_loe_contamination_clean():
    """Caso 1: LOE dentro de límite, EV_loe == PV_loe y sin enmascaramiento -> CLEAN."""
    from backend.services.project_evm_service import (
        evaluate_evm_loe_contamination_and_variance_masking,
    )

    cas = [
        {
            "ca_id": "CA-101",
            "discrete_bac": 90000.0,
            "loe_bac": 10000.0,
            "discrete_ev": 45000.0,
            "discrete_pv": 46000.0,
            "loe_ev": 5000.0,
            "loe_pv": 5000.0,
        },
        {
            "ca_id": "CA-102",
            "discrete_bac": 88000.0,
            "loe_bac": 12000.0,
            "discrete_ev": 44000.0,
            "discrete_pv": 44000.0,
            "loe_ev": 6000.0,
            "loe_pv": 6000.0,
        },
    ]
    res = evaluate_evm_loe_contamination_and_variance_masking(
        cas, max_loe_budget_share_pct=15.0
    )
    assert res["total_control_accounts"] == 2
    assert res["excessive_loe_ca_ids"] == []
    assert res["loe_pv_mismatch_ca_ids"] == []
    assert res["masked_schedule_delay_ca_ids"] == []
    assert res["project_loe_share_pct"] == 11.0
    assert res["loe_governance_status"] == "CLEAN"
    assert res["is_loe_compliant"] is True
    assert res["issues"] == []


def test_evm_loe_contamination_loe_heavy():
    """Caso 2: CA supera el porcentaje de LOE permitido sin enmascaramiento -> LOE_HEAVY."""
    from backend.services.project_evm_service import (
        evaluate_evm_loe_contamination_and_variance_masking,
    )

    cas = [
        {
            "ca_id": "CA-201",
            "discrete_bac": 70000.0,
            "loe_bac": 30000.0,
            "discrete_ev": 35000.0,
            "discrete_pv": 35000.0,
            "loe_ev": 15000.0,
            "loe_pv": 15000.0,
        }
    ]
    res = evaluate_evm_loe_contamination_and_variance_masking(
        cas, max_loe_budget_share_pct=15.0
    )
    assert res["total_control_accounts"] == 1
    assert res["excessive_loe_ca_ids"] == ["CA-201"]
    assert res["loe_pv_mismatch_ca_ids"] == []
    assert res["masked_schedule_delay_ca_ids"] == []
    assert res["project_loe_share_pct"] == 30.0
    assert res["loe_governance_status"] == "LOE_HEAVY"
    assert res["is_loe_compliant"] is False
    assert len(res["issues"]) >= 1


def test_evm_loe_contamination_masking_and_accounting_error():
    """Caso 3: SPI combinado >= 0.95 pero SPI discreto < 0.90 o LOE EV != PV -> MASKING_OR_ACCOUNTING_ERROR."""
    from backend.services.project_evm_service import (
        evaluate_evm_loe_contamination_and_variance_masking,
    )

    cas = [
        {
            "ca_id": "CA-MASK",
            "discrete_bac": 50000.0,
            "loe_bac": 50000.0,
            "discrete_ev": 8500.0,
            "discrete_pv": 10000.0,  # discrete SPI = 0.85 < 0.90
            "loe_ev": 20000.0,
            "loe_pv": 20000.0,  # combined SPI = 28500 / 30000 = 0.95 >= 0.95
        },
        {
            "ca_id": "CA-ERR",
            "discrete_bac": 90000.0,
            "loe_bac": 10000.0,
            "discrete_ev": 45000.0,
            "discrete_pv": 45000.0,
            "loe_ev": 5200.0,
            "loe_pv": 5000.0,  # mismatch > 0.01
        },
    ]
    res = evaluate_evm_loe_contamination_and_variance_masking(
        cas, max_loe_budget_share_pct=15.0
    )
    assert res["total_control_accounts"] == 2
    assert res["excessive_loe_ca_ids"] == ["CA-MASK"]
    assert res["loe_pv_mismatch_ca_ids"] == ["CA-ERR"]
    assert res["masked_schedule_delay_ca_ids"] == ["CA-MASK"]
    assert res["loe_governance_status"] == "MASKING_OR_ACCOUNTING_ERROR"
    assert res["is_loe_compliant"] is False
    assert len(res["issues"]) >= 2


def test_evm_loe_contamination_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_loe_contamination_and_variance_masking,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_loe_contamination_and_variance_masking(payload)  # type: ignore[arg-type]
        assert empty["total_control_accounts"] == 0
        assert empty["excessive_loe_ca_ids"] == []
        assert empty["loe_pv_mismatch_ca_ids"] == []
        assert empty["masked_schedule_delay_ca_ids"] == []
        assert empty["project_loe_share_pct"] == 0.0
        assert empty["loe_governance_status"] == "CLEAN"
        assert empty["is_loe_compliant"] is True
        assert empty["issues"] == []

    sample = [
        {
            "ca_id": "CA-99",
            "discrete_bac": 90000.0,
            "loe_bac": 10000.0,
            "discrete_ev": 45000.0,
            "discrete_pv": 45000.0,
            "loe_ev": 5000.0,
            "loe_pv": 5000.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_loe_contamination_and_variance_masking(sample)
        == evaluate_evm_loe_contamination_and_variance_masking(sample)
    )
    assert "evaluate_evm_loe_contamination_and_variance_masking" in mod.__all__


def test_evm_funding_limit_reconciliation_reconciled():
    """Caso 1: Todos los periodos dentro del límite de financiamiento y con headroom >= 5% -> RECONCILED."""
    from backend.services.project_evm_service import (
        evaluate_evm_funding_limit_reconciliation_and_liquidity,
    )

    periods = [
        {
            "period_id": "2026-Q1",
            "cumulative_funding_limit_usd": 100000.0,
            "cumulative_planned_outflow_pv_usd": 85000.0,
            "cumulative_actual_commitments_ac_usd": 82000.0,
            "management_reserve_earmarked_usd": 5000.0,  # peak=90000, headroom=10%
        },
        {
            "period_id": "2026-Q2",
            "cumulative_funding_limit_usd": 200000.0,
            "cumulative_planned_outflow_pv_usd": 170000.0,
            "cumulative_actual_commitments_ac_usd": 175000.0,
            "management_reserve_earmarked_usd": 5000.0,  # peak=175000, headroom=12.5%
        },
    ]
    res = evaluate_evm_funding_limit_reconciliation_and_liquidity(
        periods, min_liquidity_headroom_pct=5.0
    )
    assert res["total_periods"] == 2
    assert res["planned_breach_period_ids"] == []
    assert res["actual_commitment_breach_period_ids"] == []
    assert res["tight_headroom_period_ids"] == []
    assert res["max_funding_deficit_usd"] == 0.0
    assert res["funding_reconciliation_status"] == "RECONCILED"
    assert res["is_funding_reconciled"] is True
    assert res["issues"] == []


def test_evm_funding_limit_reconciliation_headroom_constrained():
    """Caso 2: Sin exceso de techo pero headroom < min_liquidity_headroom_pct -> HEADROOM_CONSTRAINED."""
    from backend.services.project_evm_service import (
        evaluate_evm_funding_limit_reconciliation_and_liquidity,
    )

    periods = [
        {
            "period_id": "2026-Q3",
            "cumulative_funding_limit_usd": 100000.0,
            "cumulative_planned_outflow_pv_usd": 94000.0,
            "cumulative_actual_commitments_ac_usd": 92000.0,
            "management_reserve_earmarked_usd": 3000.0,  # required=97000, headroom=3% < 5%
        }
    ]
    res = evaluate_evm_funding_limit_reconciliation_and_liquidity(
        periods, min_liquidity_headroom_pct=5.0
    )
    assert res["total_periods"] == 1
    assert res["planned_breach_period_ids"] == []
    assert res["actual_commitment_breach_period_ids"] == []
    assert res["tight_headroom_period_ids"] == ["2026-Q3"]
    assert res["max_funding_deficit_usd"] == 0.0
    assert res["funding_reconciliation_status"] == "HEADROOM_CONSTRAINED"
    assert res["is_funding_reconciled"] is False
    assert len(res["issues"]) >= 1


def test_evm_funding_limit_reconciliation_cap_breached():
    """Caso 3: PV + reserva o AC superan el límite de financiamiento -> FUNDING_CAP_BREACHED."""
    from backend.services.project_evm_service import (
        evaluate_evm_funding_limit_reconciliation_and_liquidity,
    )

    periods = [
        {
            "period_id": "2026-Q1",
            "cumulative_funding_limit_usd": 100000.0,
            "cumulative_planned_outflow_pv_usd": 95000.0,
            "cumulative_actual_commitments_ac_usd": 90000.0,
            "management_reserve_earmarked_usd": 10000.0,  # required=105000 > 100000 (deficit 5000)
        },
        {
            "period_id": "2026-Q2",
            "cumulative_funding_limit_usd": 200000.0,
            "cumulative_planned_outflow_pv_usd": 180000.0,
            "cumulative_actual_commitments_ac_usd": 212500.0,  # AC > 200000 (deficit 12500)
            "management_reserve_earmarked_usd": 0.0,
        },
    ]
    res = evaluate_evm_funding_limit_reconciliation_and_liquidity(
        periods, min_liquidity_headroom_pct=5.0
    )
    assert res["total_periods"] == 2
    assert res["planned_breach_period_ids"] == ["2026-Q1"]
    assert res["actual_commitment_breach_period_ids"] == ["2026-Q2"]
    assert res["tight_headroom_period_ids"] == []
    assert res["max_funding_deficit_usd"] == 12500.0
    assert res["funding_reconciliation_status"] == "FUNDING_CAP_BREACHED"
    assert res["is_funding_reconciled"] is False
    assert len(res["issues"]) >= 2


def test_evm_funding_limit_reconciliation_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_funding_limit_reconciliation_and_liquidity,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_funding_limit_reconciliation_and_liquidity(payload)  # type: ignore[arg-type]
        assert empty["total_periods"] == 0
        assert empty["planned_breach_period_ids"] == []
        assert empty["actual_commitment_breach_period_ids"] == []
        assert empty["tight_headroom_period_ids"] == []
        assert empty["max_funding_deficit_usd"] == 0.0
        assert empty["funding_reconciliation_status"] == "RECONCILED"
        assert empty["is_funding_reconciled"] is True
        assert empty["issues"] == []

    sample = [
        {
            "period_id": "2026-Q4",
            "cumulative_funding_limit_usd": 100000.0,
            "cumulative_planned_outflow_pv_usd": 80000.0,
            "cumulative_actual_commitments_ac_usd": 80000.0,
            "management_reserve_earmarked_usd": 0.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_funding_limit_reconciliation_and_liquidity(
            sample
        )
        == evaluate_evm_funding_limit_reconciliation_and_liquidity(sample)
    )
    assert (
        "evaluate_evm_funding_limit_reconciliation_and_liquidity" in mod.__all__
    )


def test_evm_subcontractor_retainage_and_progress_billing_compliant():
    """Caso 1: Facturación alineada con EV neto, retención >= 10% y lien waiver firmado -> COMPLIANT."""
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_retainage_and_progress_billing,
    )

    invoices = [
        {
            "invoice_id": "INV-101",
            "vendor_name": "Constructora Alfa",
            "billed_to_date": 100000.0,
            "verified_ev_to_date": 105000.0,
            "retainage_withheld": 10000.0,
            "lien_waiver_signed": True,
            "substantial_completion_reached": False,
            "retainage_released": 0.0,
            "defective_work_backcharge": 2000.0,  # net_ev = 103000
        },
        {
            "invoice_id": "INV-102",
            "vendor_name": "Instalaciones Beta",
            "billed_to_date": 50000.0,
            "verified_ev_to_date": 50000.0,
            "retainage_withheld": 0.0,
            "lien_waiver_signed": True,
            "substantial_completion_reached": True,
            "retainage_released": 5000.0,
            "defective_work_backcharge": 0.0,
        },
    ]
    res = evaluate_evm_subcontractor_retainage_and_progress_billing(
        invoices, standard_retainage_pct=10.0, overbilling_tolerance_pct=5.0
    )
    assert res["total_invoices"] == 2
    assert res["total_billed_to_date"] == 150000.0
    assert res["total_net_earned_value"] == 153000.0
    assert res["total_retainage_withheld"] == 10000.0
    assert res["overbilled_invoice_ids"] == []
    assert res["retainage_shortfall_invoice_ids"] == []
    assert res["premature_release_invoice_ids"] == []
    assert res["missing_lien_waiver_invoice_ids"] == []
    assert res["billing_governance_status"] == "COMPLIANT"
    assert res["recommendations"] == []


def test_evm_subcontractor_retainage_and_progress_billing_warning():
    """Caso 2: 1 factura con sobrefacturación (> 5%) o déficit de retención sin liberación prematura -> WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_retainage_and_progress_billing,
    )

    invoices = [
        {
            "invoice_id": "INV-201",
            "vendor_name": "Proveedor Gamma",
            "billed_to_date": 110000.0,
            "verified_ev_to_date": 100000.0,  # +10% > 5%
            "retainage_withheld": 8000.0,  # expected 11000 -> shortfall 3000
            "lien_waiver_signed": True,
            "substantial_completion_reached": False,
            "retainage_released": 0.0,
            "defective_work_backcharge": 0.0,
        }
    ]
    res = evaluate_evm_subcontractor_retainage_and_progress_billing(
        invoices, standard_retainage_pct=10.0, overbilling_tolerance_pct=5.0
    )
    assert res["total_invoices"] == 1
    assert res["overbilled_invoice_ids"] == ["INV-201"]
    assert res["retainage_shortfall_invoice_ids"] == ["INV-201"]
    assert res["premature_release_invoice_ids"] == []
    assert res["missing_lien_waiver_invoice_ids"] == []
    assert res["billing_governance_status"] == "WARNING"
    assert len(res["recommendations"]) >= 1


def test_evm_subcontractor_retainage_and_progress_billing_critical():
    """Caso 3: Liberación prematura de retención, falta de lien waiver o > 1 factura sobrefacturada -> CRITICAL."""
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_retainage_and_progress_billing,
    )

    invoices = [
        {
            "invoice_id": "INV-301",
            "vendor_name": "Subcontratista Delta",
            "billed_to_date": 80000.0,
            "verified_ev_to_date": 60000.0,
            "retainage_withheld": 4000.0,
            "lien_waiver_signed": False,
            "substantial_completion_reached": False,
            "retainage_released": 4000.0,  # prematuro
            "defective_work_backcharge": 5000.0,
        },
        {
            "invoice_id": "INV-302",
            "vendor_name": "Subcontratista Épsilon",
            "billed_to_date": 50000.0,
            "verified_ev_to_date": 0.0,  # net_ev=0, billed>0 -> 100% overbilled
            "retainage_withheld": 5000.0,
            "lien_waiver_signed": True,
            "substantial_completion_reached": False,
            "retainage_released": 0.0,
            "defective_work_backcharge": 0.0,
        },
    ]
    res = evaluate_evm_subcontractor_retainage_and_progress_billing(invoices)
    assert res["total_invoices"] == 2
    assert res["overbilled_invoice_ids"] == ["INV-301", "INV-302"]
    assert res["premature_release_invoice_ids"] == ["INV-301"]
    assert res["missing_lien_waiver_invoice_ids"] == ["INV-301"]
    assert res["billing_governance_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 2


def test_evm_subcontractor_retainage_and_progress_billing_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_subcontractor_retainage_and_progress_billing,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_subcontractor_retainage_and_progress_billing(payload)  # type: ignore[arg-type]
        assert empty["total_invoices"] == 0
        assert empty["total_billed_to_date"] == 0.0
        assert empty["total_net_earned_value"] == 0.0
        assert empty["total_retainage_withheld"] == 0.0
        assert empty["overbilled_invoice_ids"] == []
        assert empty["retainage_shortfall_invoice_ids"] == []
        assert empty["premature_release_invoice_ids"] == []
        assert empty["missing_lien_waiver_invoice_ids"] == []
        assert empty["billing_governance_status"] == "COMPLIANT"
        assert empty["recommendations"] == []

    sample = [
        {
            "invoice_id": "INV-99",
            "vendor_name": "Vendor",
            "billed_to_date": 10000.0,
            "verified_ev_to_date": 10000.0,
            "retainage_withheld": 1000.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_subcontractor_retainage_and_progress_billing(
            sample
        )
        == evaluate_evm_subcontractor_retainage_and_progress_billing(sample)
    )
    assert (
        "evaluate_evm_subcontractor_retainage_and_progress_billing" in mod.__all__
    )


def test_evm_fx_currency_volatility_and_hedging_coverage_hedged():
    """Caso 1: Tramos con cobertura suficiente y variación FX dentro de tolerancia ('HEDGED')."""
    from backend.services.project_evm_service import (
        evaluate_evm_fx_currency_volatility_and_hedging_coverage,
    )

    tranches = [
        {
            "tranche_id": "FX-01",
            "currency_code": "EUR",
            "baseline_amount_local": 100000.0,
            "baseline_fx_rate_to_base": 1.10,
            "spot_fx_rate_to_base": 1.12,
            "hedged_ratio_pct": 85.0,
        },
        {
            "tranche_id": "FX-02",
            "currency_code": "CAD",
            "baseline_amount_local": 50000.0,
            "baseline_fx_rate_to_base": 0.75,
            "spot_fx_rate_to_base": 0.74,
            "hedged_ratio_pct": 50.0,
        },
    ]
    res = evaluate_evm_fx_currency_volatility_and_hedging_coverage(
        tranches,
        fx_management_reserve=5000.0,
    )
    assert res["total_tranches"] == 2
    assert res["total_baseline_base_cost"] == 147500.0
    assert res["total_unhedged_base_exposure"] == 35250.0
    assert res["unhedged_exposure_share_pct"] == 23.9
    assert res["total_fx_loss_base"] == 300.0
    assert res["fx_reserve_coverage_ratio"] == 16.67
    assert res["volatile_tranche_ids"] == []
    assert res["underhedged_tranche_ids"] == []
    assert res["fx_governance_status"] == "HEDGED"
    assert res["recommendations"] == []


def test_evm_fx_currency_volatility_and_hedging_coverage_warning():
    """Caso 2: Un tramo sub-cubierto o con volatilidad > 5% cubierto por reserva ('WARNING')."""
    from backend.services.project_evm_service import (
        evaluate_evm_fx_currency_volatility_and_hedging_coverage,
    )

    tranches = [
        {
            "tranche_id": "FX-10",
            "currency_code": "GBP",
            "baseline_amount_local": 100000.0,
            "baseline_fx_rate_to_base": 1.25,
            "spot_fx_rate_to_base": 1.35,  # +8% drift > 5%
            "hedged_ratio_pct": 60.0,  # 40% unhedged > 20%
        },
    ]
    res = evaluate_evm_fx_currency_volatility_and_hedging_coverage(
        tranches,
        fx_management_reserve=10000.0,
    )
    assert res["total_tranches"] == 1
    assert res["total_baseline_base_cost"] == 125000.0
    assert res["total_unhedged_base_exposure"] == 50000.0
    assert res["unhedged_exposure_share_pct"] == 40.0
    assert res["total_fx_loss_base"] == 4000.0
    assert res["fx_reserve_coverage_ratio"] == 2.5
    assert res["volatile_tranche_ids"] == ["FX-10"]
    assert res["underhedged_tranche_ids"] == ["FX-10"]
    assert res["fx_governance_status"] == "WARNING"
    assert len(res["recommendations"]) >= 1


def test_evm_fx_currency_volatility_and_hedging_coverage_critical():
    """Caso 3: Pérdida FX supera la reserva o >=2 tramos volátiles ('CRITICAL')."""
    from backend.services.project_evm_service import (
        evaluate_evm_fx_currency_volatility_and_hedging_coverage,
    )

    tranches = [
        {
            "tranche_id": "FX-20",
            "currency_code": "BRL",
            "baseline_amount_local": 200000.0,
            "baseline_fx_rate_to_base": 0.20,
            "spot_fx_rate_to_base": 0.22,  # +10% drift
            "hedged_ratio_pct": 10.0,
        },
        {
            "tranche_id": "FX-21",
            "currency_code": "MXN",
            "baseline_amount_local": 500000.0,
            "baseline_fx_rate_to_base": 0.05,
            "spot_fx_rate_to_base": 0.055,  # +10% drift
            "hedged_ratio_pct": 0.0,
        },
    ]
    res = evaluate_evm_fx_currency_volatility_and_hedging_coverage(
        tranches,
        fx_management_reserve=2000.0,
    )
    assert res["total_tranches"] == 2
    assert res["volatile_tranche_ids"] == ["FX-20", "FX-21"]
    assert res["underhedged_tranche_ids"] == ["FX-20", "FX-21"]
    assert res["total_fx_loss_base"] == 6100.0
    assert res["fx_reserve_coverage_ratio"] == 0.33
    assert res["fx_governance_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 2


def test_evm_fx_currency_volatility_and_hedging_coverage_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_fx_currency_volatility_and_hedging_coverage,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_fx_currency_volatility_and_hedging_coverage(payload)  # type: ignore[arg-type]
        assert empty["total_tranches"] == 0
        assert empty["total_baseline_base_cost"] == 0.0
        assert empty["total_unhedged_base_exposure"] == 0.0
        assert empty["unhedged_exposure_share_pct"] == 0.0
        assert empty["total_fx_loss_base"] == 0.0
        assert empty["fx_reserve_coverage_ratio"] == 1.0
        assert empty["volatile_tranche_ids"] == []
        assert empty["underhedged_tranche_ids"] == []
        assert empty["fx_governance_status"] == "HEDGED"
        assert empty["recommendations"] == []

    sample = [
        {
            "tranche_id": "FX-99",
            "currency_code": "EUR",
            "baseline_amount_local": 10000.0,
            "baseline_fx_rate_to_base": 1.10,
            "spot_fx_rate_to_base": 1.10,
            "hedged_ratio_pct": 100.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_fx_currency_volatility_and_hedging_coverage(
            sample
        )
        == evaluate_evm_fx_currency_volatility_and_hedging_coverage(sample)
    )
    assert (
        "evaluate_evm_fx_currency_volatility_and_hedging_coverage" in mod.__all__
    )


def test_evaluate_evm_time_and_materials_nte_and_rate_blend_within_nte():
    """Caso 1: Contratos T&M con tarifa controlada y proyección EAC dentro de NTE -> WITHIN_NTE."""
    from backend.services.project_evm_service import (
        evaluate_evm_time_and_materials_nte_and_rate_blend,
    )

    contracts = [
        {
            "contract_id": "TM-01",
            "nte_ceiling_amount": 100000.0,
            "actual_hours_logged": 400.0,
            "actual_billed_amount": 40000.0,
            "baseline_blended_hourly_rate": 100.0,
            "pct_scope_completed": 50.0,
        },
        {
            "contract_id": "TM-02",
            "nte_ceiling_amount": 50000.0,
            "actual_hours_logged": 200.0,
            "actual_billed_amount": 20400.0,
            "baseline_blended_hourly_rate": 100.0,
            "pct_scope_completed": 45.0,
        },
    ]
    res = evaluate_evm_time_and_materials_nte_and_rate_blend(
        contracts, nte_warning_threshold_pct=85.0, max_rate_drift_pct=10.0
    )
    assert res["total_contracts"] == 2
    assert res["total_nte_ceiling"] == 150000.0
    assert res["total_actual_billed"] == 60400.0
    assert res["nte_breach_contract_ids"] == []
    assert res["nte_threshold_warning_contract_ids"] == []
    assert res["seniority_mix_rate_drift_contract_ids"] == []
    assert res["tm_governance_status"] == "WITHIN_NTE"
    assert res["recommendations"] == []


def test_evaluate_evm_time_and_materials_nte_and_rate_blend_warning():
    """Caso 2: Burn cercano al techo NTE (>=85%) o deriva de tarifa horaria (>10%) sin exceder NTE -> WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_time_and_materials_nte_and_rate_blend,
    )

    contracts = [
        {
            "contract_id": "TM-10",
            "nte_ceiling_amount": 100000.0,
            "actual_hours_logged": 880.0,
            "actual_billed_amount": 88000.0,
            "baseline_blended_hourly_rate": 100.0,
            "pct_scope_completed": 90.0,
        },
        {
            "contract_id": "TM-11",
            "nte_ceiling_amount": 80000.0,
            "actual_hours_logged": 200.0,
            "actual_billed_amount": 25000.0,
            "baseline_blended_hourly_rate": 100.0,
            "pct_scope_completed": 40.0,
        },
    ]
    res = evaluate_evm_time_and_materials_nte_and_rate_blend(
        contracts, nte_warning_threshold_pct=85.0, max_rate_drift_pct=10.0
    )
    assert res["total_contracts"] == 2
    assert res["nte_breach_contract_ids"] == []
    assert res["nte_threshold_warning_contract_ids"] == ["TM-10"]
    assert res["seniority_mix_rate_drift_contract_ids"] == ["TM-11"]
    assert res["tm_governance_status"] == "WARNING"
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_time_and_materials_nte_and_rate_blend_critical():
    """Caso 3: Facturación real o proyección EAC excede el techo NTE -> CRITICAL."""
    from backend.services.project_evm_service import (
        evaluate_evm_time_and_materials_nte_and_rate_blend,
    )

    contracts = [
        {
            "contract_id": "TM-20",
            "nte_ceiling_amount": 100000.0,
            "actual_hours_logged": 600.0,
            "actual_billed_amount": 75000.0,
            "baseline_blended_hourly_rate": 100.0,
            "pct_scope_completed": 50.0,
        },
        {
            "contract_id": "TM-21",
            "nte_ceiling_amount": 50000.0,
            "actual_hours_logged": 520.0,
            "actual_billed_amount": 55000.0,
            "baseline_blended_hourly_rate": 100.0,
            "pct_scope_completed": 95.0,
        },
    ]
    res = evaluate_evm_time_and_materials_nte_and_rate_blend(contracts)
    assert res["total_contracts"] == 2
    assert res["nte_breach_contract_ids"] == ["TM-20", "TM-21"]
    assert res["seniority_mix_rate_drift_contract_ids"] == ["TM-20"]
    assert res["tm_governance_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_time_and_materials_nte_and_rate_blend_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_time_and_materials_nte_and_rate_blend,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_time_and_materials_nte_and_rate_blend(payload)  # type: ignore[arg-type]
        assert empty["total_contracts"] == 0
        assert empty["total_nte_ceiling"] == 0.0
        assert empty["total_actual_billed"] == 0.0
        assert empty["nte_breach_contract_ids"] == []
        assert empty["nte_threshold_warning_contract_ids"] == []
        assert empty["seniority_mix_rate_drift_contract_ids"] == []
        assert empty["tm_governance_status"] == "WITHIN_NTE"
        assert empty["recommendations"] == []

    sample = [
        {
            "contract_id": "TM-99",
            "nte_ceiling_amount": 50000.0,
            "actual_hours_logged": 100.0,
            "actual_billed_amount": 10000.0,
            "baseline_blended_hourly_rate": 100.0,
            "pct_scope_completed": 25.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_time_and_materials_nte_and_rate_blend(sample)
        == evaluate_evm_time_and_materials_nte_and_rate_blend(sample)
    )
    assert (
        "evaluate_evm_time_and_materials_nte_and_rate_blend" in mod.__all__
    )


def test_evaluate_evm_epa_inflation_erosion_stable():
    """Caso 1: Inflación dentro del umbral de activación EPA ('STABLE')."""
    from backend.services.project_evm_service import (
        evaluate_evm_economic_price_adjustment_and_inflation_erosion,
    )

    wps = [
        {
            "wp_id": "WP-01",
            "remaining_bac": 100000.0,
            "baseline_cpi_index": 100.0,
            "current_cpi_index": 103.5,  # +3.5% <= 4.0%
            "has_epa_clause": True,
        },
        {
            "wp_id": "WP-02",
            "remaining_bac": 50000.0,
            "baseline_cpi_index": 100.0,
            "current_cpi_index": 102.0,
            "has_epa_clause": False,
        },
    ]
    res = evaluate_evm_economic_price_adjustment_and_inflation_erosion(
        wps,
        epa_escalation_reserve=5000.0,
    )
    assert res["total_work_packages"] == 2
    assert res["total_remaining_bac"] == 150000.0
    assert res["total_inflation_cost_impact"] == 0.0
    assert res["reserve_shortfall"] == 0.0
    assert res["epa_triggered_wp_ids"] == []
    assert res["epa_cap_breached_wp_ids"] == []
    assert res["unindexed_exposure_wp_ids"] == []
    assert res["epa_governance_status"] == "STABLE"
    assert res["recommendations"] == []


def test_evaluate_evm_epa_inflation_erosion_warning():
    """Caso 2: EPA activada (>4% y <=12%) con cláusula EPA y reserva suficiente ('WARNING')."""
    from backend.services.project_evm_service import (
        evaluate_evm_economic_price_adjustment_and_inflation_erosion,
    )

    wps = [
        {
            "wp_id": "WP-10",
            "remaining_bac": 200000.0,
            "baseline_cpi_index": 100.0,
            "current_cpi_index": 108.0,  # +8.0% > 4.0% -> impact 16000
            "has_epa_clause": True,
        }
    ]
    res = evaluate_evm_economic_price_adjustment_and_inflation_erosion(
        wps,
        epa_escalation_reserve=20000.0,
    )
    assert res["total_work_packages"] == 1
    assert res["total_remaining_bac"] == 200000.0
    assert res["total_inflation_cost_impact"] == 16000.0
    assert res["reserve_shortfall"] == 0.0
    assert res["epa_triggered_wp_ids"] == ["WP-10"]
    assert res["epa_cap_breached_wp_ids"] == []
    assert res["unindexed_exposure_wp_ids"] == []
    assert res["epa_governance_status"] == "WARNING"
    assert len(res["recommendations"]) >= 1


def test_evaluate_evm_epa_inflation_erosion_critical():
    """Caso 3: Ruptura de tope EPA (>12%), exposición sin cláusula EPA o déficit de reserva ('CRITICAL')."""
    from backend.services.project_evm_service import (
        evaluate_evm_economic_price_adjustment_and_inflation_erosion,
    )

    wps = [
        {
            "wp_id": "WP-20",
            "remaining_bac": 100000.0,
            "baseline_cpi_index": 100.0,
            "current_cpi_index": 115.0,  # +15% > 12% cap -> impact 15000
            "has_epa_clause": True,
        },
        {
            "wp_id": "WP-21",
            "remaining_bac": 100000.0,
            "baseline_cpi_index": 100.0,
            "current_cpi_index": 106.0,  # +6% > 4%, no EPA clause -> impact 6000
            "has_epa_clause": False,
        },
    ]
    res = evaluate_evm_economic_price_adjustment_and_inflation_erosion(
        wps,
        epa_escalation_reserve=10000.0,
    )
    assert res["total_work_packages"] == 2
    assert res["total_remaining_bac"] == 200000.0
    assert res["total_inflation_cost_impact"] == 21000.0
    assert res["reserve_shortfall"] == 11000.0
    assert res["epa_triggered_wp_ids"] == ["WP-20", "WP-21"]
    assert res["epa_cap_breached_wp_ids"] == ["WP-20"]
    assert res["unindexed_exposure_wp_ids"] == ["WP-21"]
    assert res["epa_governance_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 3


def test_evaluate_evm_epa_inflation_erosion_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_economic_price_adjustment_and_inflation_erosion,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_economic_price_adjustment_and_inflation_erosion(payload)  # type: ignore[arg-type]
        assert empty["total_work_packages"] == 0
        assert empty["total_remaining_bac"] == 0.0
        assert empty["total_inflation_cost_impact"] == 0.0
        assert empty["reserve_shortfall"] == 0.0
        assert empty["epa_triggered_wp_ids"] == []
        assert empty["epa_cap_breached_wp_ids"] == []
        assert empty["unindexed_exposure_wp_ids"] == []
        assert empty["epa_governance_status"] == "STABLE"
        assert empty["recommendations"] == []

    sample = [
        {
            "wp_id": "WP-99",
            "remaining_bac": 50000.0,
            "baseline_cpi_index": 100.0,
            "current_cpi_index": 101.0,
            "has_epa_clause": True,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_economic_price_adjustment_and_inflation_erosion(
            sample
        )
        == evaluate_evm_economic_price_adjustment_and_inflation_erosion(sample)
    )
    assert (
        "evaluate_evm_economic_price_adjustment_and_inflation_erosion" in mod.__all__
    )


def test_evaluate_evm_capex_opex_classification_and_amortization_compliant():
    """Caso 1: Entradas correctamente clasificadas ASC 350-40 / IAS 38 y CapEx válido >=50% -> COMPLIANT."""
    from backend.services.project_evm_service import (
        evaluate_evm_capex_opex_classification_and_amortization,
    )

    entries = [
        {
            "entry_id": "COST-DEV-01",
            "project_stage": "APPLICATION_DEVELOPMENT",
            "recorded_category": "CAPEX",
            "amount": 120000.0,
            "is_maintenance_or_training": False,
            "useful_life_months": 36,
        },
        {
            "entry_id": "COST-DISC-02",
            "project_stage": "PRELIMINARY",
            "recorded_category": "OPEX",
            "amount": 40000.0,
            "is_maintenance_or_training": False,
            "useful_life_months": 0,
        },
    ]
    res = evaluate_evm_capex_opex_classification_and_amortization(
        entries, min_capex_share_target_pct=50.0, max_misclassification_pct=5.0
    )
    assert res["total_entries"] == 2
    assert res["total_recorded_capex"] == 120000.0
    assert res["total_recorded_opex"] == 40000.0
    assert res["adjusted_valid_capex"] == 120000.0
    assert res["improper_capex_amount"] == 0.0
    assert res["valid_capex_share_pct"] == 75.0
    assert res["misclassification_share_pct"] == 0.0
    assert res["improper_capitalization_entry_ids"] == []
    assert res["unclaimed_capex_entry_ids"] == []
    assert res["accounting_governance_status"] == "COMPLIANT"
    assert res["recommendations"] == []


def test_evaluate_evm_capex_opex_classification_and_amortization_warning():
    """Caso 2: Oportunidad CapEx no reclamada (registrada como OPEX) o ratio CapEx bajo sin riesgo de auditoría -> WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_capex_opex_classification_and_amortization,
    )

    entries = [
        {
            "entry_id": "COST-DEV-CAP",
            "project_stage": "APPLICATION_DEVELOPMENT",
            "recorded_category": "CAPEX",
            "amount": 80000.0,
            "is_maintenance_or_training": False,
            "useful_life_months": 36,
        },
        {
            "entry_id": "COST-DEV-MISSED",
            "project_stage": "APPLICATION_DEVELOPMENT",
            "recorded_category": "OPEX",
            "amount": 40000.0,
            "is_maintenance_or_training": False,
            "useful_life_months": 24,
        },
    ]
    res = evaluate_evm_capex_opex_classification_and_amortization(
        entries, min_capex_share_target_pct=50.0, max_misclassification_pct=5.0
    )
    assert res["total_entries"] == 2
    assert res["improper_capitalization_entry_ids"] == []
    assert res["unclaimed_capex_entry_ids"] == ["COST-DEV-MISSED"]
    assert res["accounting_governance_status"] == "WARNING"
    assert len(res["recommendations"]) >= 1


def test_evaluate_evm_capex_opex_classification_and_amortization_audit_risk():
    """Caso 3: Sobre-capitalización indebida en etapa preliminar o entrenamiento (>5% del gasto) -> AUDIT_RISK."""
    from backend.services.project_evm_service import (
        evaluate_evm_capex_opex_classification_and_amortization,
    )

    entries = [
        {
            "entry_id": "COST-DEV-OK",
            "project_stage": "APPLICATION_DEVELOPMENT",
            "recorded_category": "CAPEX",
            "amount": 100000.0,
            "is_maintenance_or_training": False,
            "useful_life_months": 36,
        },
        {
            "entry_id": "COST-TRAIN-BAD",
            "project_stage": "POST_IMPLEMENTATION",
            "recorded_category": "CAPEX",
            "amount": 25000.0,
            "is_maintenance_or_training": True,
            "useful_life_months": 36,
        },
    ]
    res = evaluate_evm_capex_opex_classification_and_amortization(
        entries, min_capex_share_target_pct=50.0, max_misclassification_pct=5.0
    )
    assert res["total_entries"] == 2
    assert res["improper_capex_amount"] == 25000.0
    assert res["adjusted_valid_capex"] == 100000.0
    assert res["misclassification_share_pct"] == 20.0
    assert res["improper_capitalization_entry_ids"] == ["COST-TRAIN-BAD"]
    assert res["accounting_governance_status"] == "AUDIT_RISK"
    assert len(res["recommendations"]) >= 1


def test_evaluate_evm_capex_opex_classification_and_amortization_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_capex_opex_classification_and_amortization,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_capex_opex_classification_and_amortization(payload)  # type: ignore[arg-type]
        assert empty["total_entries"] == 0
        assert empty["total_recorded_capex"] == 0.0
        assert empty["total_recorded_opex"] == 0.0
        assert empty["adjusted_valid_capex"] == 0.0
        assert empty["improper_capex_amount"] == 0.0
        assert empty["valid_capex_share_pct"] == 100.0
        assert empty["misclassification_share_pct"] == 0.0
        assert empty["improper_capitalization_entry_ids"] == []
        assert empty["unclaimed_capex_entry_ids"] == []
        assert empty["accounting_governance_status"] == "COMPLIANT"
        assert empty["recommendations"] == []

    sample = [
        {
            "entry_id": "COST-99",
            "project_stage": "APPLICATION_DEVELOPMENT",
            "recorded_category": "CAPEX",
            "amount": 50000.0,
            "is_maintenance_or_training": False,
            "useful_life_months": 36,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_capex_opex_classification_and_amortization(
            sample
        )
        == evaluate_evm_capex_opex_classification_and_amortization(sample)
    )
    assert (
        "evaluate_evm_capex_opex_classification_and_amortization" in mod.__all__
    )


def test_evaluate_evm_learning_curve_cost_improvement_and_productivity_on_curve():
    """Caso 1: Lotes que cumplen la curva de aprendizaje de Wright al 85% dentro de tolerancia (<=10%) -> ON_CURVE."""
    from backend.services.project_evm_service import (
        evaluate_evm_learning_curve_cost_improvement_and_productivity,
    )

    batches = [
        {
            "batch_id": "BATCH-1",
            "doubling_step_index": 1,
            "first_batch_unit_hours": 100.0,
            "actual_unit_hours": 100.0,
        },
        {
            "batch_id": "BATCH-2",
            "doubling_step_index": 2,
            "first_batch_unit_hours": 100.0,
            "actual_unit_hours": 85.0,
        },
        {
            "batch_id": "BATCH-4",
            "doubling_step_index": 3,
            "first_batch_unit_hours": 100.0,
            "actual_unit_hours": 72.0,
        },
    ]
    res = evaluate_evm_learning_curve_cost_improvement_and_productivity(
        batches, target_learning_rate_pct=85.0, max_productivity_stall_pct=10.0
    )
    assert res["total_batches"] == 3
    assert res["stalled_learning_batch_ids"] == []
    assert res["regressed_batch_ids"] == []
    assert res["learning_governance_status"] == "ON_CURVE"
    assert res["is_on_learning_curve"] is True
    assert res["recommendations"] == []


def test_evaluate_evm_learning_curve_cost_improvement_and_productivity_warning():
    """Caso 2: 1 lote con estancamiento de aprendizaje (>10% sobre lo esperado) pero menor al primer lote -> WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_learning_curve_cost_improvement_and_productivity,
    )

    batches = [
        {
            "batch_id": "BATCH-1",
            "doubling_step_index": 1,
            "first_batch_unit_hours": 100.0,
            "actual_unit_hours": 100.0,
        },
        {
            "batch_id": "BATCH-2-STALL",
            "doubling_step_index": 2,
            "first_batch_unit_hours": 100.0,
            "actual_unit_hours": 96.0,  # expected 85.0 -> +12.94% > 10%
        },
    ]
    res = evaluate_evm_learning_curve_cost_improvement_and_productivity(
        batches, target_learning_rate_pct=85.0, max_productivity_stall_pct=10.0
    )
    assert res["total_batches"] == 2
    assert res["stalled_learning_batch_ids"] == ["BATCH-2-STALL"]
    assert res["regressed_batch_ids"] == []
    assert res["learning_governance_status"] == "WARNING"
    assert res["is_on_learning_curve"] is False
    assert len(res["recommendations"]) == 1


def test_evaluate_evm_learning_curve_cost_improvement_and_productivity_regressed():
    """Caso 3: Lote posterior supera las horas unitarias iniciales o >= 2 lotes estancados -> REGRESSED."""
    from backend.services.project_evm_service import (
        evaluate_evm_learning_curve_cost_improvement_and_productivity,
    )

    batches = [
        {
            "batch_id": "BATCH-2-REG",
            "doubling_step_index": 2,
            "first_batch_unit_hours": 100.0,
            "actual_unit_hours": 115.0,
        }
    ]
    res = evaluate_evm_learning_curve_cost_improvement_and_productivity(
        batches, target_learning_rate_pct=85.0, max_productivity_stall_pct=10.0
    )
    assert res["total_batches"] == 1
    assert res["stalled_learning_batch_ids"] == ["BATCH-2-REG"]
    assert res["regressed_batch_ids"] == ["BATCH-2-REG"]
    assert res["learning_governance_status"] == "REGRESSED"
    assert res["is_on_learning_curve"] is False
    assert len(res["recommendations"]) == 2


def test_evaluate_evm_learning_curve_cost_improvement_and_productivity_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_learning_curve_cost_improvement_and_productivity,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_learning_curve_cost_improvement_and_productivity(payload)  # type: ignore[arg-type]
        assert empty["total_batches"] == 0
        assert empty["stalled_learning_batch_ids"] == []
        assert empty["regressed_batch_ids"] == []
        assert empty["learning_governance_status"] == "ON_CURVE"
        assert empty["is_on_learning_curve"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "batch_id": "BATCH-99",
            "doubling_step_index": 2,
            "first_batch_unit_hours": 100.0,
            "actual_unit_hours": 85.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_learning_curve_cost_improvement_and_productivity(
            sample
        )
        == evaluate_evm_learning_curve_cost_improvement_and_productivity(sample)
    )
    assert (
        "evaluate_evm_learning_curve_cost_improvement_and_productivity" in mod.__all__
    )


def test_evaluate_evm_milestone_payment_holdback_and_acceptance_gate_disbursement_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_milestone_payment_holdback_and_acceptance_gate,
    )

    res = evaluate_evm_milestone_payment_holdback_and_acceptance_gate(
        [
            {
                "milestone_id": "MS-01",
                "scheduled_payment_amount": 100000.0,
                "disbursed_amount": 50000.0,
                "deliverable_formally_accepted": False,
                "open_punchlist_defects": 0,
                "warranty_holdback_retained": 0.0,
            },
            {
                "milestone_id": "MS-02",
                "scheduled_payment_amount": 80000.0,
                "disbursed_amount": 85000.0,
                "deliverable_formally_accepted": True,
                "open_punchlist_defects": 0,
                "warranty_holdback_retained": 5000.0,
            },
        ],
        max_advance_disbursement_pct=20.0,
    )
    assert res["total_milestones"] == 2
    assert res["total_scheduled_payments"] == 180000.0
    assert res["total_disbursed_amount"] == 135000.0
    assert res["unaccepted_disbursed_amount"] == 50000.0
    assert res["advance_disbursement_share_pct"] == 27.78
    assert res["premature_disbursement_milestone_ids"] == ["MS-01"]
    assert res["overpaid_milestone_ids"] == ["MS-02"]
    assert res["payment_gate_status"] == "DISBURSEMENT_BREACH"
    assert res["is_payment_gate_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_evaluate_evm_milestone_payment_holdback_and_acceptance_gate_warning_punchlist_bypass():
    from backend.services.project_evm_service import (
        evaluate_evm_milestone_payment_holdback_and_acceptance_gate,
    )

    res = evaluate_evm_milestone_payment_holdback_and_acceptance_gate(
        [
            {
                "milestone_id": "MS-10",
                "scheduled_payment_amount": 50000.0,
                "disbursed_amount": 50000.0,
                "deliverable_formally_accepted": True,
                "open_punchlist_defects": 3,
                "warranty_holdback_retained": 0.0,
            }
        ],
        max_advance_disbursement_pct=20.0,
    )
    assert res["premature_disbursement_milestone_ids"] == []
    assert res["overpaid_milestone_ids"] == []
    assert res["punchlist_bypass_milestone_ids"] == ["MS-10"]
    assert res["payment_gate_status"] == "WARNING"
    assert res["is_payment_gate_compliant"] is False


def test_evaluate_evm_milestone_payment_holdback_and_acceptance_gate_gated_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_milestone_payment_holdback_and_acceptance_gate,
    )

    empty = evaluate_evm_milestone_payment_holdback_and_acceptance_gate(
        [{"milestone_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_milestones"] == 0
    assert empty["total_scheduled_payments"] == 0.0
    assert empty["total_disbursed_amount"] == 0.0
    assert empty["unaccepted_disbursed_amount"] == 0.0
    assert empty["advance_disbursement_share_pct"] == 0.0
    assert empty["payment_gate_status"] == "GATED"
    assert empty["is_payment_gate_compliant"] is True
    assert empty["recommendations"] == []

    gated = evaluate_evm_milestone_payment_holdback_and_acceptance_gate(
        [
            {
                "milestone_id": "MS-20",
                "scheduled_payment_amount": 100000.0,
                "disbursed_amount": 90000.0,
                "deliverable_formally_accepted": True,
                "open_punchlist_defects": 2,
                "warranty_holdback_retained": 10000.0,
            },
            {
                "milestone_id": "MS-21",
                "scheduled_payment_amount": 100000.0,
                "disbursed_amount": 15000.0,
                "deliverable_formally_accepted": False,
                "open_punchlist_defects": 0,
                "warranty_holdback_retained": 0.0,
            },
        ],
        max_advance_disbursement_pct=20.0,
    )
    assert gated["total_milestones"] == 2
    assert gated["advance_disbursement_share_pct"] == 7.5
    assert gated["premature_disbursement_milestone_ids"] == []
    assert gated["punchlist_bypass_milestone_ids"] == []
    assert gated["overpaid_milestone_ids"] == []
    assert gated["payment_gate_status"] == "GATED"
    assert gated["is_payment_gate_compliant"] is True
    assert gated["recommendations"] == []


def test_evaluate_evm_milestone_payment_holdback_and_acceptance_gate_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_milestone_payment_holdback_and_acceptance_gate,
    )

    sample = [
        {
            "milestone_id": "MS-99",
            "scheduled_payment_amount": 40000.0,
            "disbursed_amount": 40000.0,
            "deliverable_formally_accepted": True,
            "open_punchlist_defects": 0,
            "warranty_holdback_retained": 0.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_milestone_payment_holdback_and_acceptance_gate(
            sample
        )
        == evaluate_evm_milestone_payment_holdback_and_acceptance_gate(sample)
    )
    assert (
        "evaluate_evm_milestone_payment_holdback_and_acceptance_gate"
        in mod.__all__
    )


def test_evaluate_evm_value_engineering_gold_plating_and_overrun_paths():
    """Caso 1: gold-plating o target cost excedido -> GOLD_PLATING_OR_SEVERE_OVERRUN."""
    from backend.services.project_evm_service import (
        evaluate_evm_value_engineering_target_costing_and_worth_index,
    )

    res = evaluate_evm_value_engineering_target_costing_and_worth_index(
        [
            {
                "function_id": "FN-01",
                "estimated_function_cost": 100.0,
                "essential_function_worth": 60.0,
                "target_allowable_cost": 80.0,
            },
            {
                "function_id": "FN-02",
                "estimated_function_cost": 50.0,
                "essential_function_worth": 10.0,
                "target_allowable_cost": 40.0,
                "is_gold_plated_non_essential": True,
            },
        ]
    )
    assert res["total_functions_evaluated"] == 2
    # FN-01: value_index 0.6 < 0.85 -> low value; target_ratio 1.25 no > 1.25.
    # FN-02: value_index 0.2 < 0.85 -> tambien low value.
    assert res["low_value_index_function_ids"] == ["FN-01", "FN-02"]
    assert res["target_cost_exceeded_function_ids"] == []
    assert res["gold_plating_function_ids"] == ["FN-02"]
    # Ahorros potenciales: (100-60) + (50-10) = 80.0.
    assert res["total_potential_cost_savings"] == 80.0
    assert res["value_engineering_status"] == "GOLD_PLATING_OR_SEVERE_OVERRUN"
    assert res["is_value_engineered_compliant"] is False

    res_overrun = evaluate_evm_value_engineering_target_costing_and_worth_index(
        [
            {
                "function_id": "FN-03",
                "estimated_function_cost": 130.0,
                "essential_function_worth": 120.0,
                "target_allowable_cost": 100.0,
            },
        ]
    )
    # value_index 0.92 >= 0.85; ratio 1.3 > 1.25 -> overrun severo.
    assert res_overrun["low_value_index_function_ids"] == []
    assert res_overrun["target_cost_exceeded_function_ids"] == ["FN-03"]
    assert res_overrun["value_engineering_status"] == "GOLD_PLATING_OR_SEVERE_OVERRUN"


def test_evaluate_evm_value_engineering_suboptimal_value_only():
    """Caso 2: solo índice de valor bajo, sin gold-plating ni overrun -> SUBOPTIMAL_VALUE_INDEX."""
    from backend.services.project_evm_service import (
        evaluate_evm_value_engineering_target_costing_and_worth_index,
    )

    res = evaluate_evm_value_engineering_target_costing_and_worth_index(
        [
            {
                "function_id": "FN-10",
                "estimated_function_cost": 200.0,
                "essential_function_worth": 140.0,
                "target_allowable_cost": 200.0,
            },
        ]
    )
    # value_index 0.7 < 0.85; ratio 1.0 <= 1.25.
    assert res["total_functions_evaluated"] == 1
    assert res["low_value_index_function_ids"] == ["FN-10"]
    assert res["target_cost_exceeded_function_ids"] == []
    assert res["gold_plating_function_ids"] == []
    assert res["total_potential_cost_savings"] == 60.0
    assert res["value_engineering_status"] == "SUBOPTIMAL_VALUE_INDEX"
    assert res["is_value_engineered_compliant"] is False


def test_evaluate_evm_value_engineering_optimized_and_boundaries():
    """Caso 3: fronteras exactas (value_index = min, ratio = max) y costos 0 -> VALUE_OPTIMIZED."""
    from backend.services.project_evm_service import (
        evaluate_evm_value_engineering_target_costing_and_worth_index,
    )

    res = evaluate_evm_value_engineering_target_costing_and_worth_index(
        [
            {
                "function_id": "FN-20",
                "estimated_function_cost": 100.0,
                "essential_function_worth": 85.0,
                "target_allowable_cost": 80.0,
            },
            {
                "function_id": "FN-21",
                "estimated_function_cost": 0.0,
                "essential_function_worth": 0.0,
                "target_allowable_cost": 0.0,
            },
        ]
    )
    # FN-20: value_index 0.85 no < 0.85; ratio 1.25 no > 1.25 -> dentro de frontera.
    # FN-21: costos 0 -> índices neutros 1.0.
    assert res["total_functions_evaluated"] == 2
    assert res["low_value_index_function_ids"] == []
    assert res["target_cost_exceeded_function_ids"] == []
    assert res["gold_plating_function_ids"] == []
    # Ahorros: FN-20 aporta 85-85? no: max(0, 100-85) = 15; FN-21 aporta 0.
    assert res["total_potential_cost_savings"] == 15.0
    assert res["value_engineering_status"] == "VALUE_OPTIMIZED"
    assert res["is_value_engineered_compliant"] is True


def test_evaluate_evm_value_engineering_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_value_engineering_target_costing_and_worth_index,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_value_engineering_target_costing_and_worth_index(payload)  # type: ignore[arg-type]
        assert empty["total_functions_evaluated"] == 0
        assert empty["low_value_index_function_ids"] == []
        assert empty["target_cost_exceeded_function_ids"] == []
        assert empty["gold_plating_function_ids"] == []
        assert empty["total_potential_cost_savings"] == 0.0
        assert empty["value_engineering_status"] == "VALUE_OPTIMIZED"
        assert empty["is_value_engineered_compliant"] is True

    sample = [
        {
            "function_id": "FN-30",
            "estimated_function_cost": 10.0,
            "essential_function_worth": 10.0,
            "target_allowable_cost": 10.0,
        },
    ]
    assert (
        ProjectEVMService.evaluate_evm_value_engineering_target_costing_and_worth_index(sample)
        == evaluate_evm_value_engineering_target_costing_and_worth_index(sample)
    )
    assert "evaluate_evm_value_engineering_target_costing_and_worth_index" in mod.__all__


def test_evaluate_evm_contingency_and_management_reserve_drawdown_governance_unauthorized_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_contingency_and_management_reserve_drawdown_governance,
    )

    res = evaluate_evm_contingency_and_management_reserve_drawdown_governance(
        [
            {
                "drawdown_id": "DD-01",
                "reserve_type": "CONTINGENCY",
                "amount": 3000.0,
                "has_linked_risk_id": False,
                "has_sponsor_bcr_approval": False,
            },
            {
                "drawdown_id": "DD-02",
                "reserve_type": "MANAGEMENT",
                "amount": 5000.0,
                "has_linked_risk_id": False,
                "has_sponsor_bcr_approval": False,
            },
        ],
        contingency_reserve_initial=10000.0,
        management_reserve_initial=10000.0,
        project_percent_complete=50.0,
    )
    assert res["total_drawdowns_evaluated"] == 2
    assert res["contingency_consumed"] == 3000.0
    assert res["management_consumed"] == 5000.0
    assert res["contingency_consumed_pct"] == 30.0
    assert res["reserve_burn_to_progress_ratio"] == 0.6
    assert res["unlinked_contingency_drawdown_ids"] == ["DD-01"]
    assert res["unauthorized_management_drawdown_ids"] == ["DD-02"]
    assert res["reserve_governance_status"] == "UNAUTHORIZED_OR_EXHAUSTED_BREACH"
    assert res["is_reserve_drawdown_compliant"] is False


def test_evaluate_evm_contingency_and_management_reserve_drawdown_governance_premature_burn_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_contingency_and_management_reserve_drawdown_governance,
    )

    res = evaluate_evm_contingency_and_management_reserve_drawdown_governance(
        [
            {
                "drawdown_id": "DD-10",
                "reserve_type": "CONTINGENCY",
                "amount": 7500.0,
                "has_linked_risk_id": True,
                "has_sponsor_bcr_approval": False,
            }
        ],
        contingency_reserve_initial=10000.0,
        management_reserve_initial=10000.0,
        project_percent_complete=40.0,
    )
    assert res["unlinked_contingency_drawdown_ids"] == []
    assert res["unauthorized_management_drawdown_ids"] == []
    assert res["contingency_consumed_pct"] == 75.0
    assert res["reserve_burn_to_progress_ratio"] == 1.88
    assert res["reserve_governance_status"] == "PREMATURE_BURN_WARNING"
    assert res["is_reserve_drawdown_compliant"] is False


def test_evaluate_evm_contingency_and_management_reserve_drawdown_governance_protected_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_contingency_and_management_reserve_drawdown_governance,
    )

    empty = evaluate_evm_contingency_and_management_reserve_drawdown_governance(
        [{"drawdown_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_drawdowns_evaluated"] == 0
    assert empty["contingency_consumed"] == 0.0
    assert empty["management_consumed"] == 0.0
    assert empty["reserve_governance_status"] == "RESERVE_PROTECTED"
    assert empty["is_reserve_drawdown_compliant"] is True

    protected = evaluate_evm_contingency_and_management_reserve_drawdown_governance(
        [
            {
                "drawdown_id": "DD-20",
                "reserve_type": "CONTINGENCY",
                "amount": 4000.0,
                "has_linked_risk_id": True,
            },
            {
                "drawdown_id": "DD-21",
                "reserve_type": "MANAGEMENT",
                "amount": 2000.0,
                "has_sponsor_bcr_approval": True,
            },
        ],
        contingency_reserve_initial=10000.0,
        management_reserve_initial=10000.0,
        project_percent_complete=50.0,
    )
    assert protected["total_drawdowns_evaluated"] == 2
    assert protected["reserve_burn_to_progress_ratio"] == 0.8
    assert protected["reserve_governance_status"] == "RESERVE_PROTECTED"
    assert protected["is_reserve_drawdown_compliant"] is True


def test_evaluate_evm_contingency_and_management_reserve_drawdown_governance_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_contingency_and_management_reserve_drawdown_governance,
    )

    sample = [
        {
            "drawdown_id": "DD-99",
            "reserve_type": "CONTINGENCY",
            "amount": 1000.0,
            "has_linked_risk_id": True,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_contingency_and_management_reserve_drawdown_governance(
            sample
        )
        == evaluate_evm_contingency_and_management_reserve_drawdown_governance(sample)
    )
    assert (
        "evaluate_evm_contingency_and_management_reserve_drawdown_governance"
        in mod.__all__
    )


def test_evaluate_evm_sla_penalty_service_credits_and_earn_back_balanced():
    """Caso 1: Periodos cumpliendo SLA (>=99.9%) y earn-back elegible (>=3 meses limpios) -> SLA_CREDITS_BALANCED."""
    from backend.services.project_evm_service import (
        evaluate_evm_sla_penalty_service_credits_and_earn_back,
    )

    periods = [
        {
            "period_id": "2026-01",
            "monthly_base_fee": 50000.0,
            "observed_uptime_pct": 99.95,
            "penalty_credit_claimed": 0.0,
            "earn_back_credit_applied": 0.0,
            "consecutive_clean_months_for_earn_back": 2,
        },
        {
            "period_id": "2026-02",
            "monthly_base_fee": 50000.0,
            "observed_uptime_pct": 99.98,
            "penalty_credit_claimed": 0.0,
            "earn_back_credit_applied": 1500.0,
            "consecutive_clean_months_for_earn_back": 3,
        },
    ]
    res = evaluate_evm_sla_penalty_service_credits_and_earn_back(
        periods, min_sla_uptime_pct=99.9, max_at_risk_fee_pool_pct=15.0
    )
    assert res["total_periods_evaluated"] == 2
    assert res["sla_breach_period_ids"] == []
    assert res["uncollected_penalty_period_ids"] == []
    assert res["premature_earn_back_period_ids"] == []
    assert res["fee_pool_cap_exceeded_period_ids"] == []
    assert res["net_service_credits_retained"] == -1500.0
    assert res["sla_financial_governance_status"] == "SLA_CREDITS_BALANCED"
    assert res["is_sla_credit_compliant"] is True


def test_evaluate_evm_sla_penalty_service_credits_and_earn_back_warning():
    """Caso 2: Incumplimiento de SLA con penalidad cobrada y/o superando el tope at-risk (>15%) -> AT_RISK_CAP_EXCEEDED_WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_sla_penalty_service_credits_and_earn_back,
    )

    periods = [
        {
            "period_id": "2026-03",
            "monthly_base_fee": 50000.0,
            "observed_uptime_pct": 99.5,  # < 99.9%
            "penalty_credit_claimed": 10000.0,  # 20% > 15% cap
            "earn_back_credit_applied": 0.0,
            "consecutive_clean_months_for_earn_back": 0,
        }
    ]
    res = evaluate_evm_sla_penalty_service_credits_and_earn_back(
        periods, min_sla_uptime_pct=99.9, max_at_risk_fee_pool_pct=15.0
    )
    assert res["total_periods_evaluated"] == 1
    assert res["sla_breach_period_ids"] == ["2026-03"]
    assert res["uncollected_penalty_period_ids"] == []
    assert res["premature_earn_back_period_ids"] == []
    assert res["fee_pool_cap_exceeded_period_ids"] == ["2026-03"]
    assert res["net_service_credits_retained"] == 10000.0
    assert res["sla_financial_governance_status"] == "AT_RISK_CAP_EXCEEDED_WARNING"
    assert res["is_sla_credit_compliant"] is False


def test_evaluate_evm_sla_penalty_service_credits_and_earn_back_leakage():
    """Caso 3: Brecha de SLA sin cobro de penalidad o earn-back prematuro (<3 meses limpios) -> PENALTY_OR_EARNBACK_LEAKAGE."""
    from backend.services.project_evm_service import (
        evaluate_evm_sla_penalty_service_credits_and_earn_back,
    )

    periods = [
        {
            "period_id": "2026-04-UNCOLLECTED",
            "monthly_base_fee": 50000.0,
            "observed_uptime_pct": 99.4,
            "penalty_credit_claimed": 0.0,
            "earn_back_credit_applied": 0.0,
            "consecutive_clean_months_for_earn_back": 0,
        },
        {
            "period_id": "2026-05-PREMATURE",
            "monthly_base_fee": 50000.0,
            "observed_uptime_pct": 99.95,
            "penalty_credit_claimed": 4000.0,
            "earn_back_credit_applied": 1500.0,
            "consecutive_clean_months_for_earn_back": 1,  # < 3
        },
    ]
    res = evaluate_evm_sla_penalty_service_credits_and_earn_back(
        periods, min_sla_uptime_pct=99.9, max_at_risk_fee_pool_pct=15.0
    )
    assert res["total_periods_evaluated"] == 2
    assert res["sla_breach_period_ids"] == ["2026-04-UNCOLLECTED"]
    assert res["uncollected_penalty_period_ids"] == ["2026-04-UNCOLLECTED"]
    assert res["premature_earn_back_period_ids"] == ["2026-05-PREMATURE"]
    assert res["net_service_credits_retained"] == 2500.0
    assert res["sla_financial_governance_status"] == "PENALTY_OR_EARNBACK_LEAKAGE"
    assert res["is_sla_credit_compliant"] is False


def test_evaluate_evm_sla_penalty_service_credits_and_earn_back_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectEVMService + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_sla_penalty_service_credits_and_earn_back,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_sla_penalty_service_credits_and_earn_back(payload)  # type: ignore[arg-type]
        assert empty["total_periods_evaluated"] == 0
        assert empty["sla_breach_period_ids"] == []
        assert empty["uncollected_penalty_period_ids"] == []
        assert empty["premature_earn_back_period_ids"] == []
        assert empty["fee_pool_cap_exceeded_period_ids"] == []
        assert empty["net_service_credits_retained"] == 0.0
        assert empty["sla_financial_governance_status"] == "SLA_CREDITS_BALANCED"
        assert empty["is_sla_credit_compliant"] is True

    sample = [
        {
            "period_id": "2026-99",
            "monthly_base_fee": 20000.0,
            "observed_uptime_pct": 99.99,
            "penalty_credit_claimed": 0.0,
            "earn_back_credit_applied": 0.0,
            "consecutive_clean_months_for_earn_back": 4,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_sla_penalty_service_credits_and_earn_back(
            sample
        )
        == evaluate_evm_sla_penalty_service_credits_and_earn_back(sample)
    )
    assert (
        "evaluate_evm_sla_penalty_service_credits_and_earn_back" in mod.__all__
    )



def test_evaluate_evm_cpif_pta_and_ceiling_breach_paths():
    """Caso 1: sobrecosto que cruza el PTA y el techo de precio -> CEILING_OR_PTA_BREACH."""
    from backend.services.project_evm_service import (
        evaluate_evm_cpif_share_ratio_and_point_of_total_assumption,
    )

    res = evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(
        [
            {
                "contract_id": "CPIF-01",
                "target_cost": 100000.0,
                "target_fee": 20000.0,
                "actual_or_forecast_cost": 130000.0,
                "min_fee_floor": 0.0,
                "max_fee_ceiling": 50000.0,
                "seller_cost_overrun_share_pct": 20.0,
                "ceiling_price": 140000.0,
            },
        ]
    )
    assert res["total_contracts_evaluated"] == 1
    # PTA = 100000 + (140000 - 120000) / 0.8 = 125000; actual 130000 > PTA -> breach.
    assert res["pta_breached_contract_ids"] == ["CPIF-01"]
    # raw_fee = 20000 + (-30000 * 0.2) = 14000 >= floor 0 -> sin hit.
    assert res["min_fee_floor_hit_contract_ids"] == []
    # total payable = actual 130000 + fee 14000 = 144000 > 140000 -> breach.
    assert res["ceiling_price_exceeded_contract_ids"] == ["CPIF-01"]
    assert res["total_final_fees_payable"] == 14000.0
    assert res["cpif_governance_status"] == "CEILING_OR_PTA_BREACH"
    assert res["is_cpif_compliant"] is False


def test_evaluate_evm_cpif_fee_floor_erosion_only():
    """Caso 2: sobrecosto erosiona el fee hasta el floor, sin ceiling_price -> WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_cpif_share_ratio_and_point_of_total_assumption,
    )

    res = evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(
        [
            {
                "contract_id": "CPIF-10",
                "target_cost": 100000.0,
                "target_fee": 20000.0,
                "actual_or_forecast_cost": 200000.0,
                "min_fee_floor": 5000.0,
                "max_fee_ceiling": 30000.0,
                "seller_cost_overrun_share_pct": 20.0,
            },
        ]
    )
    # raw_fee = 20000 + (-100000 * 0.2) = 0.0 < floor 5000 -> hit.
    assert res["min_fee_floor_hit_contract_ids"] == ["CPIF-10"]
    assert res["pta_breached_contract_ids"] == []
    assert res["ceiling_price_exceeded_contract_ids"] == []
    # final_fee clampeado al floor -> payable 5000.
    assert res["total_final_fees_payable"] == 5000.0
    assert res["cpif_governance_status"] == "FEE_FLOOR_EROSION_WARNING"
    assert res["is_cpif_compliant"] is False


def test_evaluate_evm_cpif_aligned_and_boundaries():
    """Caso 3: ahorro compartido, sin brechas ni hits -> INCENTIVE_ALIGNED; guard share 100%."""
    from backend.services.project_evm_service import (
        evaluate_evm_cpif_share_ratio_and_point_of_total_assumption,
    )

    res = evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(
        [
            {
                "contract_id": "CPIF-20",
                "target_cost": 100000.0,
                "target_fee": 20000.0,
                "actual_or_forecast_cost": 90000.0,
                "min_fee_floor": 0.0,
                "max_fee_ceiling": 50000.0,
                "seller_cost_overrun_share_pct": 20.0,
                "ceiling_price": 140000.0,
            },
        ]
    )
    # raw_fee = 20000 + (10000 * 0.2) = 22000; dentro del rango.
    assert res["pta_breached_contract_ids"] == []
    assert res["min_fee_floor_hit_contract_ids"] == []
    assert res["ceiling_price_exceeded_contract_ids"] == []
    assert res["total_final_fees_payable"] == 22000.0
    assert res["cpif_governance_status"] == "INCENTIVE_ALIGNED"
    assert res["is_cpif_compliant"] is True

    # Guard: share 100% debe usar PTA = target_cost sin dividir por 0; sin hits.
    res_share_100 = evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(
        [
            {
                "contract_id": "CPIF-21",
                "target_cost": 100000.0,
                "target_fee": 20000.0,
                "actual_or_forecast_cost": 80000.0,
                "min_fee_floor": 0.0,
                "max_fee_ceiling": 60000.0,
                "seller_cost_overrun_share_pct": 100.0,
                "ceiling_price": 140000.0,
            },
        ]
    )
    assert res_share_100["pta_breached_contract_ids"] == []
    assert res_share_100["cpif_governance_status"] == "INCENTIVE_ALIGNED"

    # Frontera del ceiling de precio: actual + fee == ceiling_price exacto no excede.
    res_boundary = evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(
        [
            {
                "contract_id": "CPIF-22",
                "target_cost": 100000.0,
                "target_fee": 20000.0,
                "actual_or_forecast_cost": 100000.0,
                "min_fee_floor": 0.0,
                "max_fee_ceiling": 40000.0,
                "seller_cost_overrun_share_pct": 20.0,
                "ceiling_price": 120000.0,
            },
        ]
    )
    # raw_fee = 20000; actual + fee = 120000 == ceiling_price -> no breach.
    assert res_boundary["ceiling_price_exceeded_contract_ids"] == []
    assert res_boundary["cpif_governance_status"] == "INCENTIVE_ALIGNED"


def test_evaluate_evm_cpif_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_cpif_share_ratio_and_point_of_total_assumption,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(payload)  # type: ignore[arg-type]
        assert empty["total_contracts_evaluated"] == 0
        assert empty["pta_breached_contract_ids"] == []
        assert empty["min_fee_floor_hit_contract_ids"] == []
        assert empty["ceiling_price_exceeded_contract_ids"] == []
        assert empty["total_final_fees_payable"] == 0.0
        assert empty["cpif_governance_status"] == "INCENTIVE_ALIGNED"
        assert empty["is_cpif_compliant"] is True

    sample = [
        {
            "contract_id": "CPIF-30",
            "target_cost": 100000.0,
            "target_fee": 20000.0,
            "actual_or_forecast_cost": 100000.0,
            "min_fee_floor": 0.0,
            "max_fee_ceiling": 30000.0,
        },
    ]
    assert (
        ProjectEVMService.evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(sample)
        == evaluate_evm_cpif_share_ratio_and_point_of_total_assumption(sample)
    )
    assert "evaluate_evm_cpif_share_ratio_and_point_of_total_assumption" in mod.__all__


def test_evaluate_evm_performance_bond_and_letter_of_credit_coverage_default_exposure():
    from backend.services.project_evm_service import (
        evaluate_evm_performance_bond_and_letter_of_credit_coverage,
    )

    res = evaluate_evm_performance_bond_and_letter_of_credit_coverage(
        [
            {
                "instrument_id": "LC-UNDERINSURED",
                "contract_total_value": 1000000.0,
                "bond_or_lc_face_amount": 50000.0,
                "days_valid_after_scheduled_completion": 60,
                "issuer_credit_rating_investment_grade": True,
                "is_irrevocable_on_demand": True,
            },
            {
                "instrument_id": "BOND-REVOCABLE",
                "contract_total_value": 500000.0,
                "bond_or_lc_face_amount": 75000.0,
                "days_valid_after_scheduled_completion": 90,
                "issuer_credit_rating_investment_grade": True,
                "is_irrevocable_on_demand": False,
            },
        ],
        min_coverage_pct_of_contract=10.0,
        min_days_beyond_completion_buffer=30,
    )
    assert res["total_instruments_evaluated"] == 2
    assert res["total_bonded_coverage_amount"] == 125000.0
    assert res["underinsured_instrument_ids"] == ["LC-UNDERINSURED"]
    assert res["premature_expiry_instrument_ids"] == []
    assert res["non_compliant_issuer_or_revocable_ids"] == ["BOND-REVOCABLE"]
    assert res["bond_governance_status"] == "COUNTERPARTY_DEFAULT_EXPOSURE"
    assert res["is_bond_coverage_compliant"] is False


def test_evaluate_evm_performance_bond_and_letter_of_credit_coverage_expiry_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_performance_bond_and_letter_of_credit_coverage,
    )

    res = evaluate_evm_performance_bond_and_letter_of_credit_coverage(
        [
            {
                "instrument_id": "LC-SHORT-TAIL",
                "contract_total_value": 200000.0,
                "bond_or_lc_face_amount": 30000.0,
                "days_valid_after_scheduled_completion": 10,
                "issuer_credit_rating_investment_grade": True,
                "is_irrevocable_on_demand": True,
            }
        ],
        min_coverage_pct_of_contract=10.0,
        min_days_beyond_completion_buffer=30,
    )
    assert res["underinsured_instrument_ids"] == []
    assert res["premature_expiry_instrument_ids"] == ["LC-SHORT-TAIL"]
    assert res["non_compliant_issuer_or_revocable_ids"] == []
    assert res["bond_governance_status"] == "EXPIRY_BUFFER_WARNING"
    assert res["is_bond_coverage_compliant"] is False


def test_evaluate_evm_performance_bond_and_letter_of_credit_coverage_sound_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_performance_bond_and_letter_of_credit_coverage,
    )

    empty = evaluate_evm_performance_bond_and_letter_of_credit_coverage(
        [{"instrument_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_instruments_evaluated"] == 0
    assert empty["total_bonded_coverage_amount"] == 0.0
    assert empty["bond_governance_status"] == "BOND_COVERAGE_SOUND"
    assert empty["is_bond_coverage_compliant"] is True

    sound = evaluate_evm_performance_bond_and_letter_of_credit_coverage(
        [
            {
                "instrument_id": "LC-SOLID-01",
                "contract_total_value": 400000.0,
                "bond_or_lc_face_amount": 60000.0,
                "days_valid_after_scheduled_completion": 45,
                "issuer_credit_rating_investment_grade": True,
                "is_irrevocable_on_demand": True,
            }
        ],
        min_coverage_pct_of_contract=10.0,
        min_days_beyond_completion_buffer=30,
    )
    assert sound["total_instruments_evaluated"] == 1
    assert sound["total_bonded_coverage_amount"] == 60000.0
    assert sound["bond_governance_status"] == "BOND_COVERAGE_SOUND"
    assert sound["is_bond_coverage_compliant"] is True


def test_evaluate_evm_performance_bond_and_letter_of_credit_coverage_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_performance_bond_and_letter_of_credit_coverage,
    )

    sample = [
        {
            "instrument_id": "LC-99",
            "contract_total_value": 100000.0,
            "bond_or_lc_face_amount": 15000.0,
            "days_valid_after_scheduled_completion": 60,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_performance_bond_and_letter_of_credit_coverage(
            sample
        )
        == evaluate_evm_performance_bond_and_letter_of_credit_coverage(sample)
    )
    assert (
        "evaluate_evm_performance_bond_and_letter_of_credit_coverage"
        in mod.__all__
    )


def test_evaluate_evm_fx_hedging_var_breach_paths():
    """Caso 1: VaR sin cubrir sobre el umbral del BAC -> FX_TRANSLATION_VAR_BREACH."""
    from backend.services.project_evm_service import (
        evaluate_evm_fx_hedging_collar_and_currency_exposure,
    )

    res = evaluate_evm_fx_hedging_collar_and_currency_exposure(
        [
            {
                "currency_code": "EUR",
                "exposure_in_base_currency": 200000.0,
                "hedged_amount_in_base_currency": 0.0,
                "spot_volatility_var_pct": 10.0,
                "has_active_fx_collar_or_forward": False,
                "total_project_bac": 500000.0,
            },
        ]
    )
    assert res["total_fx_exposure_base"] == 200000.0
    assert res["total_hedged_base"] == 0.0
    assert res["aggregate_hedge_coverage_pct"] == 0.0
    # VaR sin cubrir = 200000 * 10% = 20000; pct del BAC = 20000 / 500000 = 4.0% > 2.0%.
    assert res["total_unhedged_fx_var_amount"] == 20000.0
    assert res["unhedged_fx_var_pct_of_bac"] == 4.0
    assert res["underhedged_currency_codes"] == ["EUR"]
    assert res["fx_exposure_status"] == "FX_TRANSLATION_VAR_BREACH"
    assert res["is_fx_compliant"] is False

    # Precisión: FX_TRANSLATION_VAR_BREACH domina sobre FX_HEDGE_COVERAGE_WARNING.
    res_mixed = evaluate_evm_fx_hedging_collar_and_currency_exposure(
        [
            {
                "currency_code": "EUR",
                "exposure_in_base_currency": 200000.0,
                "hedged_amount_in_base_currency": 200000.0,
                "spot_volatility_var_pct": 10.0,
                "has_active_fx_collar_or_forward": False,
                "total_project_bac": 500000.0,
            },
        ]
    )
    # Coverage 100%, pero sin collar activo -> WARNING... el VaR es 0.0 <= 2.0.
    assert res_mixed["unhedged_fx_var_pct_of_bac"] == 0.0
    assert res_mixed["underhedged_currency_codes"] == ["EUR"]
    assert res_mixed["fx_exposure_status"] == "FX_HEDGE_COVERAGE_WARNING"


def test_evaluate_evm_fx_hedging_warning_only_paths():
    """Caso 2: sub-cobertura por collar ausente o ratio bajo con VaR en umbral -> WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_fx_hedging_collar_and_currency_exposure,
    )

    res = evaluate_evm_fx_hedging_collar_and_currency_exposure(
        [
            {
                "currency_code": "EUR",
                "exposure_in_base_currency": 100000.0,
                "hedged_amount_in_base_currency": 75000.0,
                "spot_volatility_var_pct": 5.0,
                "has_active_fx_collar_or_forward": True,
                "total_project_bac": 400000.0,
            },
        ]
    )
    # Coverage 75% < 80% -> underhedged; VaR = 25000 * 5% = 1250; / 400000 = 0.31% <= 2.0%.
    assert res["total_fx_exposure_base"] == 100000.0
    assert res["total_hedged_base"] == 75000.0
    assert res["aggregate_hedge_coverage_pct"] == 75.0
    assert res["total_unhedged_fx_var_amount"] == 1250.0
    assert res["unhedged_fx_var_pct_of_bac"] == 0.31
    assert res["underhedged_currency_codes"] == ["EUR"]
    assert res["fx_exposure_status"] == "FX_HEDGE_COVERAGE_WARNING"
    assert res["is_fx_compliant"] is False


def test_evaluate_evm_fx_hedging_optimal_and_boundaries():
    """Caso 3: cobertura completa y fronteras exactas (80% y 2.0% inclusive) -> FX_HEDGED_OPTIMAL."""
    from backend.services.project_evm_service import (
        evaluate_evm_fx_hedging_collar_and_currency_exposure,
    )

    res = evaluate_evm_fx_hedging_collar_and_currency_exposure(
        [
            {
                "currency_code": "EUR",
                "exposure_in_base_currency": 100000.0,
                "hedged_amount_in_base_currency": 100000.0,
                "spot_volatility_var_pct": 5.0,
                "has_active_fx_collar_or_forward": True,
                "total_project_bac": 400000.0,
            },
        ]
    )
    assert res["total_fx_exposure_base"] == 100000.0
    assert res["total_hedged_base"] == 100000.0
    assert res["aggregate_hedge_coverage_pct"] == 100.0
    assert res["total_unhedged_fx_var_amount"] == 0.0
    assert res["unhedged_fx_var_pct_of_bac"] == 0.0
    assert res["underhedged_currency_codes"] == []
    assert res["fx_exposure_status"] == "FX_HEDGED_OPTIMAL"
    assert res["is_fx_compliant"] is True

    # Fronteras: coverage 80.0% exacto y VaR 2.0% exacto no disparan nada.
    res_boundary = evaluate_evm_fx_hedging_collar_and_currency_exposure(
        [
            {
                "currency_code": "GBP",
                "exposure_in_base_currency": 50000.0,
                "hedged_amount_in_base_currency": 40000.0,
                "spot_volatility_var_pct": 8.0,
                "has_active_fx_collar_or_forward": True,
                "total_project_bac": 50000.0,
            },
        ]
    )
    # coverage 80.0% no < 80.0; VaR = 10000 * 8% = 800; / 50000 = 1.6% <= 2.0.
    assert res_boundary["underhedged_currency_codes"] == []
    assert res_boundary["unhedged_fx_var_pct_of_bac"] == 1.6
    assert res_boundary["fx_exposure_status"] == "FX_HEDGED_OPTIMAL"

    # Tranche sin exposición (exposure 0): coverage 100.0 por defecto y VaR 0.
    res_no_exposure = evaluate_evm_fx_hedging_collar_and_currency_exposure(
        [
            {"currency_code": "CHF", "exposure_in_base_currency": 0.0, "hedged_amount_in_base_currency": 0.0},
        ]
    )
    assert res_no_exposure["aggregate_hedge_coverage_pct"] == 100.0
    assert res_no_exposure["total_unhedged_fx_var_amount"] == 0.0
    assert res_no_exposure["underhedged_currency_codes"] == []
    assert res_no_exposure["fx_exposure_status"] == "FX_HEDGED_OPTIMAL"


def test_evaluate_evm_fx_hedging_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_fx_hedging_collar_and_currency_exposure,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = evaluate_evm_fx_hedging_collar_and_currency_exposure(payload)  # type: ignore[arg-type]
        assert empty["total_fx_exposure_base"] == 0.0
        assert empty["total_hedged_base"] == 0.0
        assert empty["aggregate_hedge_coverage_pct"] == 100.0
        assert empty["total_unhedged_fx_var_amount"] == 0.0
        assert empty["unhedged_fx_var_pct_of_bac"] == 0.0
        assert empty["underhedged_currency_codes"] == []
        assert empty["fx_exposure_status"] == "FX_HEDGED_OPTIMAL"
        assert empty["is_fx_compliant"] is True

    sample = [
        {
            "currency_code": "EUR",
            "exposure_in_base_currency": 10000.0,
            "hedged_amount_in_base_currency": 10000.0,
        },
    ]
    assert (
        ProjectEVMService.evaluate_evm_fx_hedging_collar_and_currency_exposure(sample)
        == evaluate_evm_fx_hedging_collar_and_currency_exposure(sample)
    )
    assert "evaluate_evm_fx_hedging_collar_and_currency_exposure" in mod.__all__


def test_evaluate_evm_time_and_materials_nte_ceiling_and_rate_card_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_time_and_materials_nte_ceiling_and_rate_card,
    )

    result = evaluate_evm_time_and_materials_nte_ceiling_and_rate_card(
        [
            {
                "contract_id": "TM-OVER-NTE",
                "not_to_exceed_ceiling": 100000.0,
                "cumulative_billed_amount": 105000.0,
                "work_completion_pct": 95.0,
                "unapproved_rate_card_overrides_count": 0,
                "timesheet_audit_verified": True,
            },
            {
                "contract_id": "TM-BAD-RATE",
                "not_to_exceed_ceiling": 100000.0,
                "cumulative_billed_amount": 50000.0,
                "work_completion_pct": 55.0,
                "unapproved_rate_card_overrides_count": 2,
                "timesheet_audit_verified": True,
            },
            {
                "contract_id": "TM-UNVERIFIED-TS",
                "not_to_exceed_ceiling": 100000.0,
                "cumulative_billed_amount": 40000.0,
                "work_completion_pct": 45.0,
                "unapproved_rate_card_overrides_count": 0,
                "timesheet_audit_verified": False,
            },
        ],
        nte_early_warning_threshold_pct=85.0,
    )
    assert result["evaluated_contracts_count"] == 3
    assert result["nte_breach_or_rate_violation_contract_ids"] == [
        "TM-OVER-NTE",
        "TM-BAD-RATE",
        "TM-UNVERIFIED-TS",
    ]
    assert result["burn_ahead_of_progress_contract_ids"] == []
    assert (
        result["tm_governance_status"]
        == "TM_NTE_CEILING_OR_RATE_CARD_BREACH"
    )
    assert result["is_tm_contract_compliant"] is False


def test_evaluate_evm_time_and_materials_nte_ceiling_and_rate_card_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_time_and_materials_nte_ceiling_and_rate_card,
    )

    result = evaluate_evm_time_and_materials_nte_ceiling_and_rate_card(
        [
            {
                "contract_id": "TM-BURN-AHEAD",
                "not_to_exceed_ceiling": 100000.0,
                "cumulative_billed_amount": 90000.0,
                "work_completion_pct": 65.0,
                "unapproved_rate_card_overrides_count": 0,
                "timesheet_audit_verified": True,
            }
        ],
        nte_early_warning_threshold_pct=85.0,
    )
    assert result["evaluated_contracts_count"] == 1
    assert result["nte_breach_or_rate_violation_contract_ids"] == []
    assert result["burn_ahead_of_progress_contract_ids"] == ["TM-BURN-AHEAD"]
    assert result["tm_governance_status"] == "TM_BURN_EXHAUSTION_WARNING"
    assert result["is_tm_contract_compliant"] is False


def test_evaluate_evm_time_and_materials_nte_ceiling_and_rate_card_optimal_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_time_and_materials_nte_ceiling_and_rate_card,
    )

    empty = evaluate_evm_time_and_materials_nte_ceiling_and_rate_card(
        [{"contract_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_contracts_count"] == 0
    assert empty["tm_governance_status"] == "TM_CONTRACT_CONTROL_OPTIMAL"
    assert empty["is_tm_contract_compliant"] is True

    optimal = evaluate_evm_time_and_materials_nte_ceiling_and_rate_card(
        [
            {
                "contract_id": "TM-GOLD-1",
                "not_to_exceed_ceiling": 100000.0,
                "cumulative_billed_amount": 88000.0,
                "work_completion_pct": 85.0,
                "unapproved_rate_card_overrides_count": 0,
                "timesheet_audit_verified": True,
            }
        ],
        nte_early_warning_threshold_pct=85.0,
    )
    assert optimal["evaluated_contracts_count"] == 1
    assert optimal["tm_governance_status"] == "TM_CONTRACT_CONTROL_OPTIMAL"
    assert optimal["is_tm_contract_compliant"] is True


def test_evaluate_evm_time_and_materials_nte_ceiling_and_rate_card_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_time_and_materials_nte_ceiling_and_rate_card,
    )

    sample = [
        {
            "contract_id": "TM-99",
            "not_to_exceed_ceiling": 100000.0,
            "cumulative_billed_amount": 50000.0,
            "work_completion_pct": 55.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_time_and_materials_nte_ceiling_and_rate_card(
            sample
        )
        == evaluate_evm_time_and_materials_nte_ceiling_and_rate_card(sample)
    )
    assert (
        "evaluate_evm_time_and_materials_nte_ceiling_and_rate_card"
        in mod.__all__
    )


def test_evaluate_evm_working_capital_cash_conversion_and_mobilization_advance_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_working_capital_cash_conversion_and_mobilization_advance,
    )

    result = evaluate_evm_working_capital_cash_conversion_and_mobilization_advance(
        [
            {
                "cycle_id": "CYC-RUNWAY-LOW",
                "days_sales_outstanding_dso": 30.0,
                "days_payable_outstanding_dpo": 35.0,
                "mobilization_advance_unamortized_balance": 10000.0,
                "remaining_contract_billings": 50000.0,
                "available_project_cash_runway_months": 1.5,
            },
            {
                "cycle_id": "CYC-UNAMORTIZED-ADV",
                "days_sales_outstanding_dso": 30.0,
                "days_payable_outstanding_dpo": 35.0,
                "mobilization_advance_unamortized_balance": 60000.0,
                "remaining_contract_billings": 40000.0,
                "available_project_cash_runway_months": 5.0,
            },
        ],
        max_dso_days=45.0,
        min_cash_runway_months=3.0,
    )
    assert result["evaluated_cycles_count"] == 2
    assert result["liquidity_crunch_or_unamortized_advance_cycle_ids"] == [
        "CYC-RUNWAY-LOW",
        "CYC-UNAMORTIZED-ADV",
    ]
    assert result["high_dso_or_positive_cash_gap_cycle_ids"] == []
    assert (
        result["working_capital_status"]
        == "WORKING_CAPITAL_LIQUIDITY_OR_ADVANCE_BREACH"
    )
    assert result["is_working_capital_compliant"] is False


def test_evaluate_evm_working_capital_cash_conversion_and_mobilization_advance_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_working_capital_cash_conversion_and_mobilization_advance,
    )

    result = evaluate_evm_working_capital_cash_conversion_and_mobilization_advance(
        [
            {
                "cycle_id": "CYC-DSO-GAP",
                "days_sales_outstanding_dso": 52.0,
                "days_payable_outstanding_dpo": 30.0,
                "mobilization_advance_unamortized_balance": 5000.0,
                "remaining_contract_billings": 80000.0,
                "available_project_cash_runway_months": 4.5,
            }
        ],
        max_dso_days=45.0,
        min_cash_runway_months=3.0,
    )
    assert result["evaluated_cycles_count"] == 1
    assert result["liquidity_crunch_or_unamortized_advance_cycle_ids"] == []
    assert result["high_dso_or_positive_cash_gap_cycle_ids"] == ["CYC-DSO-GAP"]
    assert (
        result["working_capital_status"]
        == "WORKING_CAPITAL_DSO_CASH_GAP_WARNING"
    )
    assert result["is_working_capital_compliant"] is False


def test_evaluate_evm_working_capital_cash_conversion_and_mobilization_advance_optimal_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_working_capital_cash_conversion_and_mobilization_advance,
    )

    empty = evaluate_evm_working_capital_cash_conversion_and_mobilization_advance(
        [{"cycle_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_cycles_count"] == 0
    assert empty["working_capital_status"] == "WORKING_CAPITAL_FLOW_OPTIMAL"
    assert empty["is_working_capital_compliant"] is True

    optimal = evaluate_evm_working_capital_cash_conversion_and_mobilization_advance(
        [
            {
                "cycle_id": "CYC-OPT-1",
                "days_sales_outstanding_dso": 35.0,
                "days_payable_outstanding_dpo": 30.0,
                "mobilization_advance_unamortized_balance": 20000.0,
                "remaining_contract_billings": 120000.0,
                "available_project_cash_runway_months": 6.0,
            }
        ],
        max_dso_days=45.0,
        min_cash_runway_months=3.0,
    )
    assert optimal["evaluated_cycles_count"] == 1
    assert optimal["working_capital_status"] == "WORKING_CAPITAL_FLOW_OPTIMAL"
    assert optimal["is_working_capital_compliant"] is True


def test_evaluate_evm_working_capital_cash_conversion_and_mobilization_advance_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_working_capital_cash_conversion_and_mobilization_advance,
    )

    sample = [
        {
            "cycle_id": "CYC-99",
            "days_sales_outstanding_dso": 30.0,
            "days_payable_outstanding_dpo": 35.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_working_capital_cash_conversion_and_mobilization_advance(
            sample
        )
        == evaluate_evm_working_capital_cash_conversion_and_mobilization_advance(
            sample
        )
    )
    assert (
        "evaluate_evm_working_capital_cash_conversion_and_mobilization_advance"
        in mod.__all__
    )


def test_evaluate_evm_liquidated_damages_cap_and_eot_relief_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_liquidated_damages_cap_and_eot_relief,
    )

    result = evaluate_evm_liquidated_damages_cap_and_eot_relief(
        [
            {
                "milestone_id": "MS-CAP-BREACH",
                "total_delay_days": 20,
                "grace_period_days": 5,
                "approved_eot_relief_days": 3,
                "daily_ld_rate": 1000.0,
                "contract_value": 100000.0,
            }
        ],
        max_ld_cap_pct_of_contract=10.0,
    )
    assert result["evaluated_milestones_count"] == 1
    assert result["net_chargeable_delay_days_by_milestone"] == {
        "MS-CAP-BREACH": 12.0
    }
    assert result["uncapped_ld_exposure_total"] == 12000.0
    assert result["ld_cap_breached_milestone_ids"] == ["MS-CAP-BREACH"]
    assert result["active_ld_accrual_milestone_ids"] == ["MS-CAP-BREACH"]
    assert (
        result["liquidated_damages_status"]
        == "LD_PENALTY_CAP_EXHAUSTED_BREACH"
    )
    assert result["is_ld_exposure_compliant"] is False


def test_evaluate_evm_liquidated_damages_cap_and_eot_relief_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_liquidated_damages_cap_and_eot_relief,
    )

    result = evaluate_evm_liquidated_damages_cap_and_eot_relief(
        [
            {
                "milestone_id": "MS-ACCRUAL-1",
                "total_delay_days": 10,
                "grace_period_days": 5,
                "approved_eot_relief_days": 2,
                "daily_ld_rate": 1000.0,
                "contract_value": 100000.0,
            }
        ],
        max_ld_cap_pct_of_contract=10.0,
    )
    assert result["evaluated_milestones_count"] == 1
    assert result["net_chargeable_delay_days_by_milestone"] == {
        "MS-ACCRUAL-1": 3.0
    }
    assert result["uncapped_ld_exposure_total"] == 3000.0
    assert result["ld_cap_breached_milestone_ids"] == []
    assert result["active_ld_accrual_milestone_ids"] == ["MS-ACCRUAL-1"]
    assert (
        result["liquidated_damages_status"]
        == "LD_DELAY_ACCRUAL_ACTIVE_WARNING"
    )
    assert result["is_ld_exposure_compliant"] is False


def test_evaluate_evm_liquidated_damages_cap_and_eot_relief_optimal_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_liquidated_damages_cap_and_eot_relief,
    )

    empty = evaluate_evm_liquidated_damages_cap_and_eot_relief(
        [{"milestone_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_milestones_count"] == 0
    assert empty["uncapped_ld_exposure_total"] == 0.0
    assert empty["liquidated_damages_status"] == "LD_ZERO_EXPOSURE_OPTIMAL"
    assert empty["is_ld_exposure_compliant"] is True

    optimal = evaluate_evm_liquidated_damages_cap_and_eot_relief(
        [
            {
                "milestone_id": "MS-RELIEVED",
                "total_delay_days": 12,
                "grace_period_days": 5,
                "approved_eot_relief_days": 8,
                "daily_ld_rate": 1500.0,
                "contract_value": 100000.0,
            }
        ],
        max_ld_cap_pct_of_contract=10.0,
    )
    assert optimal["evaluated_milestones_count"] == 1
    assert optimal["net_chargeable_delay_days_by_milestone"] == {
        "MS-RELIEVED": 0.0
    }
    assert optimal["uncapped_ld_exposure_total"] == 0.0
    assert optimal["liquidated_damages_status"] == "LD_ZERO_EXPOSURE_OPTIMAL"
    assert optimal["is_ld_exposure_compliant"] is True


def test_evaluate_evm_liquidated_damages_cap_and_eot_relief_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_liquidated_damages_cap_and_eot_relief,
    )

    sample = [
        {
            "milestone_id": "MS-99",
            "total_delay_days": 3,
            "grace_period_days": 5,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_liquidated_damages_cap_and_eot_relief(
            sample
        )
        == evaluate_evm_liquidated_damages_cap_and_eot_relief(sample)
    )
    assert (
        "evaluate_evm_liquidated_damages_cap_and_eot_relief"
        in mod.__all__
    )


def test_evaluate_evm_epa_inflation_indexation_and_escalation_cap_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_epa_inflation_indexation_and_escalation_cap,
    )

    result = evaluate_evm_epa_inflation_indexation_and_escalation_cap(
        [
            {
                "clause_id": "EPA-UNVERIFIED",
                "base_index_value": 100.0,
                "current_index_value": 103.5,
                "claimed_escalation_pct": 3.5,
                "contractual_cap_pct": 6.0,
                "deadband_threshold_pct": 2.0,
                "official_bls_or_cpi_source_verified": False,
            },
            {
                "clause_id": "EPA-OVER-CAP",
                "base_index_value": 100.0,
                "current_index_value": 108.0,
                "claimed_escalation_pct": 7.0,
                "contractual_cap_pct": 6.0,
                "deadband_threshold_pct": 2.0,
                "official_bls_or_cpi_source_verified": True,
            },
            {
                "clause_id": "EPA-OVERCLAIMED-FORMULA",
                "base_index_value": 100.0,
                "current_index_value": 103.0,
                "claimed_escalation_pct": 4.2,
                "contractual_cap_pct": 6.0,
                "deadband_threshold_pct": 2.0,
                "official_bls_or_cpi_source_verified": True,
            },
        ],
        max_annual_escalation_cap_pct=6.0,
    )
    assert result["evaluated_clauses_count"] == 3
    assert result["overclaimed_or_unverified_index_clause_ids"] == [
        "EPA-UNVERIFIED",
        "EPA-OVER-CAP",
        "EPA-OVERCLAIMED-FORMULA",
    ]
    assert result["within_deadband_or_near_cap_clause_ids"] == ["EPA-OVER-CAP"]
    assert (
        result["epa_escalation_status"]
        == "EPA_INDEX_OVERCLAIM_OR_UNVERIFIED_BREACH"
    )
    assert result["is_epa_escalation_compliant"] is False


def test_evaluate_evm_epa_inflation_indexation_and_escalation_cap_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_epa_inflation_indexation_and_escalation_cap,
    )

    result = evaluate_evm_epa_inflation_indexation_and_escalation_cap(
        [
            {
                "clause_id": "EPA-DEADBAND-CLAIM",
                "base_index_value": 100.0,
                "current_index_value": 101.5,
                "claimed_escalation_pct": 1.5,
                "contractual_cap_pct": 6.0,
                "deadband_threshold_pct": 2.0,
                "official_bls_or_cpi_source_verified": True,
            },
            {
                "clause_id": "EPA-NEAR-CAP",
                "base_index_value": 100.0,
                "current_index_value": 105.5,
                "claimed_escalation_pct": 5.5,
                "contractual_cap_pct": 6.0,
                "deadband_threshold_pct": 2.0,
                "official_bls_or_cpi_source_verified": True,
            },
        ],
        max_annual_escalation_cap_pct=6.0,
    )
    assert result["evaluated_clauses_count"] == 2
    assert result["overclaimed_or_unverified_index_clause_ids"] == []
    assert result["within_deadband_or_near_cap_clause_ids"] == [
        "EPA-DEADBAND-CLAIM",
        "EPA-NEAR-CAP",
    ]
    assert (
        result["epa_escalation_status"]
        == "EPA_DEADBAND_OR_CAP_PROXIMITY_WARNING"
    )
    assert result["is_epa_escalation_compliant"] is False


def test_evaluate_evm_epa_inflation_indexation_and_escalation_cap_optimal_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_epa_inflation_indexation_and_escalation_cap,
    )

    empty = evaluate_evm_epa_inflation_indexation_and_escalation_cap(
        [{"clause_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_clauses_count"] == 0
    assert empty["epa_escalation_status"] == "EPA_INDEXATION_COMPLIANT_OPTIMAL"
    assert empty["is_epa_escalation_compliant"] is True

    optimal = evaluate_evm_epa_inflation_indexation_and_escalation_cap(
        [
            {
                "clause_id": "EPA-OPT-1",
                "base_index_value": 100.0,
                "current_index_value": 103.5,
                "claimed_escalation_pct": 3.5,
                "contractual_cap_pct": 6.0,
                "deadband_threshold_pct": 2.0,
                "official_bls_or_cpi_source_verified": True,
            }
        ],
        max_annual_escalation_cap_pct=6.0,
    )
    assert optimal["evaluated_clauses_count"] == 1
    assert optimal["overclaimed_or_unverified_index_clause_ids"] == []
    assert optimal["within_deadband_or_near_cap_clause_ids"] == []
    assert optimal["epa_escalation_status"] == "EPA_INDEXATION_COMPLIANT_OPTIMAL"
    assert optimal["is_epa_escalation_compliant"] is True


def test_evaluate_evm_epa_inflation_indexation_and_escalation_cap_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_epa_inflation_indexation_and_escalation_cap,
    )

    sample = [
        {
            "clause_id": "EPA-99",
            "base_index_value": 100.0,
            "current_index_value": 103.0,
            "claimed_escalation_pct": 3.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_epa_inflation_indexation_and_escalation_cap(
            sample
        )
        == evaluate_evm_epa_inflation_indexation_and_escalation_cap(sample)
    )
    assert (
        "evaluate_evm_epa_inflation_indexation_and_escalation_cap"
        in mod.__all__
    )


def test_evaluate_evm_subcontractor_lien_waiver_and_flow_down_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_lien_waiver_and_flow_down,
    )

    result = evaluate_evm_subcontractor_lien_waiver_and_flow_down(
        [
            {
                "voucher_id": "VCH-NO-LIEN-WAIVER",
                "unconditional_lien_waiver_signed": False,
                "mandatory_flow_down_clauses_accepted": True,
                "days_since_prime_payment_received": 2,
                "subcontractor_paid": True,
                "certified_payroll_attached": True,
            },
            {
                "voucher_id": "VCH-NO-FLOW-DOWN",
                "unconditional_lien_waiver_signed": True,
                "mandatory_flow_down_clauses_accepted": False,
                "days_since_prime_payment_received": 2,
                "subcontractor_paid": True,
                "certified_payroll_attached": True,
            },
            {
                "voucher_id": "VCH-NO-PAYROLL",
                "unconditional_lien_waiver_signed": True,
                "mandatory_flow_down_clauses_accepted": True,
                "days_since_prime_payment_received": 2,
                "subcontractor_paid": True,
                "certified_payroll_attached": False,
            },
        ],
        max_payment_disbursement_lag_days=10,
    )
    assert result["evaluated_vouchers_count"] == 3
    assert result["missing_lien_waiver_or_flow_down_voucher_ids"] == [
        "VCH-NO-LIEN-WAIVER",
        "VCH-NO-FLOW-DOWN",
        "VCH-NO-PAYROLL",
    ]
    assert result["overdue_disbursement_voucher_ids"] == []
    assert (
        result["subcontractor_payment_status"]
        == "SUBCONTRACT_LIEN_OR_FLOW_DOWN_BREACH"
    )
    assert result["is_subcontract_payment_compliant"] is False


def test_evaluate_evm_subcontractor_lien_waiver_and_flow_down_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_lien_waiver_and_flow_down,
    )

    result = evaluate_evm_subcontractor_lien_waiver_and_flow_down(
        [
            {
                "voucher_id": "VCH-PAY-DELAYED",
                "unconditional_lien_waiver_signed": True,
                "mandatory_flow_down_clauses_accepted": True,
                "days_since_prime_payment_received": 16,
                "subcontractor_paid": False,
                "certified_payroll_attached": True,
            }
        ],
        max_payment_disbursement_lag_days=10,
    )
    assert result["evaluated_vouchers_count"] == 1
    assert result["missing_lien_waiver_or_flow_down_voucher_ids"] == []
    assert result["overdue_disbursement_voucher_ids"] == ["VCH-PAY-DELAYED"]
    assert (
        result["subcontractor_payment_status"]
        == "SUBCONTRACT_PAY_DISBURSEMENT_LAG_WARNING"
    )
    assert result["is_subcontract_payment_compliant"] is False


def test_evaluate_evm_subcontractor_lien_waiver_and_flow_down_optimal_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_lien_waiver_and_flow_down,
    )

    empty = evaluate_evm_subcontractor_lien_waiver_and_flow_down(
        [{"voucher_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_vouchers_count"] == 0
    assert (
        empty["subcontractor_payment_status"]
        == "SUBCONTRACT_FLOW_DOWN_COMPLIANT_OPTIMAL"
    )
    assert empty["is_subcontract_payment_compliant"] is True

    optimal = evaluate_evm_subcontractor_lien_waiver_and_flow_down(
        [
            {
                "voucher_id": "VCH-OPT-1",
                "unconditional_lien_waiver_signed": True,
                "mandatory_flow_down_clauses_accepted": True,
                "days_since_prime_payment_received": 4,
                "subcontractor_paid": True,
                "certified_payroll_attached": True,
            }
        ],
        max_payment_disbursement_lag_days=10,
    )
    assert optimal["evaluated_vouchers_count"] == 1
    assert optimal["missing_lien_waiver_or_flow_down_voucher_ids"] == []
    assert optimal["overdue_disbursement_voucher_ids"] == []
    assert (
        optimal["subcontractor_payment_status"]
        == "SUBCONTRACT_FLOW_DOWN_COMPLIANT_OPTIMAL"
    )
    assert optimal["is_subcontract_payment_compliant"] is True


def test_evaluate_evm_subcontractor_lien_waiver_and_flow_down_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_subcontractor_lien_waiver_and_flow_down,
    )

    sample = [
        {
            "voucher_id": "VCH-99",
            "days_since_prime_payment_received": 2,
            "subcontractor_paid": True,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_subcontractor_lien_waiver_and_flow_down(
            sample
        )
        == evaluate_evm_subcontractor_lien_waiver_and_flow_down(sample)
    )
    assert (
        "evaluate_evm_subcontractor_lien_waiver_and_flow_down"
        in mod.__all__
    )


def test_evaluate_evm_capex_opex_software_capitalization_gate_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_capex_opex_software_capitalization_gate,
    )

    result = evaluate_evm_capex_opex_software_capitalization_gate(
        [
            {
                "package_id": "PKG-PRELIM-CAPEX",
                "accounting_stage": "preliminary_project",
                "capitalized_capex_amount": 5000.0,
                "expensed_opex_amount": 15000.0,
                "management_authorization_signed": True,
                "amortization_useful_life_months": 36,
            },
            {
                "package_id": "PKG-MAINT-CAPEX",
                "accounting_stage": "post_implementation_maintenance",
                "capitalized_capex_amount": 2500.0,
                "expensed_opex_amount": 8000.0,
                "management_authorization_signed": True,
                "amortization_useful_life_months": 36,
            },
            {
                "package_id": "PKG-UNAUTHORIZED-CAPEX",
                "accounting_stage": "application_development",
                "capitalized_capex_amount": 18000.0,
                "expensed_opex_amount": 1000.0,
                "management_authorization_signed": False,
                "amortization_useful_life_months": 36,
            },
        ],
        max_preliminary_or_post_impl_capex_pct=0.0,
    )
    assert result["evaluated_packages_count"] == 3
    assert result["improper_capex_classification_package_ids"] == [
        "PKG-PRELIM-CAPEX",
        "PKG-MAINT-CAPEX",
        "PKG-UNAUTHORIZED-CAPEX",
    ]
    assert result["excessive_amortization_horizon_package_ids"] == []
    assert (
        result["capex_governance_status"]
        == "CAPEX_ASC350_MISCLASSIFICATION_BREACH"
    )
    assert result["is_capex_accounting_compliant"] is False


def test_evaluate_evm_capex_opex_software_capitalization_gate_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_capex_opex_software_capitalization_gate,
    )

    result = evaluate_evm_capex_opex_software_capitalization_gate(
        [
            {
                "package_id": "PKG-ZERO-LIFE",
                "accounting_stage": "application_development",
                "capitalized_capex_amount": 12000.0,
                "expensed_opex_amount": 1000.0,
                "management_authorization_signed": True,
                "amortization_useful_life_months": 0,
            },
            {
                "package_id": "PKG-LONG-LIFE",
                "accounting_stage": "application_development",
                "capitalized_capex_amount": 12000.0,
                "expensed_opex_amount": 1000.0,
                "management_authorization_signed": True,
                "amortization_useful_life_months": 84,
            },
        ],
        max_preliminary_or_post_impl_capex_pct=0.0,
    )
    assert result["evaluated_packages_count"] == 2
    assert result["improper_capex_classification_package_ids"] == []
    assert result["excessive_amortization_horizon_package_ids"] == [
        "PKG-ZERO-LIFE",
        "PKG-LONG-LIFE",
    ]
    assert (
        result["capex_governance_status"]
        == "CAPEX_AMORTIZATION_HORIZON_WARNING"
    )
    assert result["is_capex_accounting_compliant"] is False


def test_evaluate_evm_capex_opex_software_capitalization_gate_optimal_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_capex_opex_software_capitalization_gate,
    )

    empty = evaluate_evm_capex_opex_software_capitalization_gate(
        [{"package_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_packages_count"] == 0
    assert empty["capex_governance_status"] == "CAPEX_OPEX_ACCOUNTING_OPTIMAL"
    assert empty["is_capex_accounting_compliant"] is True

    optimal = evaluate_evm_capex_opex_software_capitalization_gate(
        [
            {
                "package_id": "PKG-DEV-CAPEX-01",
                "accounting_stage": "application_development",
                "capitalized_capex_amount": 25000.0,
                "expensed_opex_amount": 3000.0,
                "management_authorization_signed": True,
                "amortization_useful_life_months": 36,
            },
            {
                "package_id": "PKG-PRELIM-OPEX-01",
                "accounting_stage": "preliminary_project",
                "capitalized_capex_amount": 0.0,
                "expensed_opex_amount": 8000.0,
                "management_authorization_signed": False,
                "amortization_useful_life_months": 0,
            },
        ],
        max_preliminary_or_post_impl_capex_pct=0.0,
    )
    assert optimal["evaluated_packages_count"] == 2
    assert optimal["improper_capex_classification_package_ids"] == []
    assert optimal["excessive_amortization_horizon_package_ids"] == []
    assert (
        optimal["capex_governance_status"] == "CAPEX_OPEX_ACCOUNTING_OPTIMAL"
    )
    assert optimal["is_capex_accounting_compliant"] is True


def test_evaluate_evm_capex_opex_software_capitalization_gate_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_capex_opex_software_capitalization_gate,
    )

    sample = [
        {
            "package_id": "PKG-99",
            "accounting_stage": "application_development",
            "capitalized_capex_amount": 10000.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_capex_opex_software_capitalization_gate(
            sample
        )
        == evaluate_evm_capex_opex_software_capitalization_gate(sample)
    )
    assert (
        "evaluate_evm_capex_opex_software_capitalization_gate"
        in mod.__all__
    )


def test_evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare,
    )

    res = evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare(
        [
            {
                "vecp_id": "  VECP-01  ",
                "function_worth_index": 1.50,
                "implementation_payback_months": 6.0,
                "degrades_essential_quality_or_safety": True,
                "independent_cost_audit_verified": True,
            },
            {
                "vecp_id": "VECP-02",
                "function_worth_index": 1.10,
                "implementation_payback_months": 20.0,
                "degrades_essential_quality_or_safety": False,
                "independent_cost_audit_verified": False,
            },
            {
                "vecp_id": "VECP-03",
                "function_worth_index": 1.15,
                "implementation_payback_months": 18.0,
                "degrades_essential_quality_or_safety": False,
                "independent_cost_audit_verified": True,
            },
        ]
    )
    assert res["evaluated_proposals_count"] == 3
    assert res["quality_compromised_or_unaudited_vecp_ids"] == [
        "VECP-01",
        "VECP-02",
    ]
    assert res["low_worth_or_slow_payback_vecp_ids"] == ["VECP-02"]
    assert res["value_engineering_status"] == "VECP_QUALITY_OR_AUDIT_BREACH"
    assert res["is_value_engineering_compliant"] is False


def test_evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare,
    )

    res = evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare(
        [
            {
                "vecp_id": "VECP-LOW-WORTH",
                "function_worth_index": 1.14,
                "implementation_payback_months": 18.0,
                "degrades_essential_quality_or_safety": False,
                "independent_cost_audit_verified": True,
            },
            {
                "vecp_id": "VECP-SLOW-PAYBACK",
                "function_worth_index": 1.15,
                "implementation_payback_months": 18.1,
                "degrades_essential_quality_or_safety": False,
                "independent_cost_audit_verified": True,
            },
        ],
        min_function_worth_index=1.15,
        max_implementation_payback_months=18.0,
    )
    assert res["evaluated_proposals_count"] == 2
    assert res["quality_compromised_or_unaudited_vecp_ids"] == []
    assert res["low_worth_or_slow_payback_vecp_ids"] == [
        "VECP-LOW-WORTH",
        "VECP-SLOW-PAYBACK",
    ]
    assert (
        res["value_engineering_status"] == "VECP_LOW_WORTH_OR_PAYBACK_WARNING"
    )
    assert res["is_value_engineering_compliant"] is False


def test_evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare_optimal_and_defensive():
    from backend.services.project_evm_service import (
        evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare,
    )

    empty = evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare(None)
    assert empty["evaluated_proposals_count"] == 0
    assert empty["quality_compromised_or_unaudited_vecp_ids"] == []
    assert empty["low_worth_or_slow_payback_vecp_ids"] == []
    assert empty["value_engineering_status"] == "VECP_GAINSHARE_OPTIMAL"
    assert empty["is_value_engineering_compliant"] is True

    optimal = evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"vecp_id": "   "},
            {
                "vecp_id": "VECP-DEFAULTS",
                "function_worth_index": None,
                "implementation_payback_months": None,
                "degrades_essential_quality_or_safety": None,
                "independent_cost_audit_verified": None,
            },
        ]
    )
    assert optimal["evaluated_proposals_count"] == 1
    assert optimal["quality_compromised_or_unaudited_vecp_ids"] == []
    assert optimal["low_worth_or_slow_payback_vecp_ids"] == []
    assert optimal["value_engineering_status"] == "VECP_GAINSHARE_OPTIMAL"
    assert optimal["is_value_engineering_compliant"] is True


def test_evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare,
    )

    sample = [
        {
            "vecp_id": "VECP-99",
            "function_worth_index": 1.40,
            "implementation_payback_months": 9.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare(
            sample
        )
        == evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare(
            sample
        )
    )
    assert (
        "evaluate_evm_value_engineering_worth_ratio_and_vecp_gainshare"
        in mod.__all__
    )




def test_evm_cpaf_unpublished_plan_or_rollover_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_cpaf_award_fee_pool_and_rollover_governance,
    )

    res = evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
        [
            {
                "period_id": "P-NO-PLAN",
                "award_fee_plan_published_in_advance": False,
            },
            {
                "period_id": "P-ROLLOVER-HIGH-BASE",
                "unearned_fee_rolled_over": True,
                "base_fee_pct": 5.0,
            },
        ],
        max_base_fee_pct=3.0,
        allow_unearned_fee_rollover=False,
    )
    assert res["evaluated_periods_count"] == 2
    assert res["unauthorized_rollover_or_unpublished_plan_period_ids"] == [
        "P-NO-PLAN",
        "P-ROLLOVER-HIGH-BASE",
    ]
    assert res["excessive_base_or_overrun_rewarded_period_ids"] == [
        "P-ROLLOVER-HIGH-BASE"
    ]
    assert (
        res["cpaf_governance_status"]
        == "CPAF_UNPUBLISHED_PLAN_OR_ROLLOVER_BREACH"
    )
    assert res["is_cpaf_governance_compliant"] is False

    rollover_allowed = evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
        [
            {
                "period_id": "P-ROLLOVER-ALLOWED",
                "unearned_fee_rolled_over": True,
            }
        ],
        max_base_fee_pct=3.0,
        allow_unearned_fee_rollover=True,
    )
    assert (
        rollover_allowed["unauthorized_rollover_or_unpublished_plan_period_ids"]
        == []
    )


def test_evm_cpaf_base_fee_or_overrun_reward_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_cpaf_award_fee_pool_and_rollover_governance,
    )

    res = evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
        [
            {
                "period_id": "P-HIGH-BASE",
                "base_fee_pct": 4.0,
            },
            {
                "period_id": "P-OVERRUN-REWARDED",
                "cost_overrun_occurred": True,
                "award_fee_granted_pct": 90.0,
            },
        ],
        max_base_fee_pct=3.0,
        allow_unearned_fee_rollover=False,
    )
    assert res["evaluated_periods_count"] == 2
    assert res["unauthorized_rollover_or_unpublished_plan_period_ids"] == []
    assert res["excessive_base_or_overrun_rewarded_period_ids"] == [
        "P-HIGH-BASE",
        "P-OVERRUN-REWARDED",
    ]
    assert (
        res["cpaf_governance_status"]
        == "CPAF_BASE_FEE_OR_OVERRUN_REWARD_WARNING"
    )
    assert res["is_cpaf_governance_compliant"] is False


def test_evm_cpaf_boundaries_optimal_and_defaults():
    from backend.services.project_evm_service import (
        evaluate_evm_cpaf_award_fee_pool_and_rollover_governance,
    )

    res = evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
        [
            {
                "period_id": "P-BOUNDARY",
                "base_fee_pct": 3.0,
                "cost_overrun_occurred": True,
                "award_fee_granted_pct": 50.0,
            },
            {"period_id": "P-ALL-DEFAULTS"},
        ],
        max_base_fee_pct=3.0,
        allow_unearned_fee_rollover=False,
    )
    assert res["evaluated_periods_count"] == 2
    assert res["unauthorized_rollover_or_unpublished_plan_period_ids"] == []
    assert res["excessive_base_or_overrun_rewarded_period_ids"] == []
    assert (
        res["cpaf_governance_status"]
        == "CPAF_AWARD_FEE_GOVERNANCE_OPTIMAL"
    )
    assert res["is_cpaf_governance_compliant"] is True


def test_evm_cpaf_invalid_and_binding():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_cpaf_award_fee_pool_and_rollover_governance,
    )

    empty = evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(None)
    assert empty["evaluated_periods_count"] == 0
    assert empty["unauthorized_rollover_or_unpublished_plan_period_ids"] == []
    assert empty["excessive_base_or_overrun_rewarded_period_ids"] == []
    assert (
        empty["cpaf_governance_status"]
        == "CPAF_AWARD_FEE_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_cpaf_governance_compliant"] is True

    invalid = evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
        [42, "not-a-dict", None, {"period_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_periods_count"] == 0

    defaults = evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
        [
            {
                "period_id": "P-DEFAULTS",
                "base_fee_pct": None,
                "award_fee_plan_published_in_advance": None,
                "unearned_fee_rolled_over": None,
                "cost_overrun_occurred": None,
                "award_fee_granted_pct": None,
            }
        ]
    )
    assert defaults["evaluated_periods_count"] == 1
    assert (
        defaults["cpaf_governance_status"]
        == "CPAF_AWARD_FEE_GOVERNANCE_OPTIMAL"
    )
    assert defaults["is_cpaf_governance_compliant"] is True

    sample = [
        {
            "period_id": "P-1",
            "base_fee_pct": 2.0,
            "award_fee_granted_pct": 80.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(
            sample
        )
        == evaluate_evm_cpaf_award_fee_pool_and_rollover_governance(sample)
    )
    assert (
        "evaluate_evm_cpaf_award_fee_pool_and_rollover_governance"
        in mod.__all__
    )


def test_evaluate_evm_standby_demurrage_and_force_account_rates_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_standby_demurrage_and_force_account_rates,
    )

    res = evaluate_evm_standby_demurrage_and_force_account_rates(
        [
            {
                "claim_id": "  CLM-UNSIGNED-LOG  ",
                "daily_field_log_countersigned": False,
                "contractor_caused_idle_excluded": True,
                "standby_rate_of_active_pct": 35.0,
                "mob_demob_contract_share_pct": 6.0,
            },
            {
                "claim_id": "CLM-SELF-IDLE",
                "daily_field_log_countersigned": True,
                "contractor_caused_idle_excluded": False,
                "standby_rate_of_active_pct": 65.0,
                "mob_demob_contract_share_pct": 14.0,
            },
            {
                "claim_id": "CLM-CLEAN",
                "daily_field_log_countersigned": True,
                "contractor_caused_idle_excluded": True,
                "standby_rate_of_active_pct": 50.0,
                "mob_demob_contract_share_pct": 10.0,
            },
        ]
    )
    assert res["evaluated_claims_count"] == 3
    assert res["unverified_log_or_self_inflicted_idle_claim_ids"] == [
        "CLM-UNSIGNED-LOG",
        "CLM-SELF-IDLE",
    ]
    assert res["excessive_standby_rate_or_mob_cap_claim_ids"] == [
        "CLM-SELF-IDLE"
    ]
    assert (
        res["standby_demurrage_status"]
        == "DEMURRAGE_UNVERIFIED_LOG_OR_SELF_IDLE_BREACH"
    )
    assert res["is_standby_demurrage_compliant"] is False


def test_evaluate_evm_standby_demurrage_and_force_account_rates_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_standby_demurrage_and_force_account_rates,
    )

    res = evaluate_evm_standby_demurrage_and_force_account_rates(
        [
            {
                "claim_id": "CLM-HIGH-STANDBY",
                "daily_field_log_countersigned": True,
                "contractor_caused_idle_excluded": True,
                "standby_rate_of_active_pct": 50.1,
                "mob_demob_contract_share_pct": 10.0,
            },
            {
                "claim_id": "CLM-HIGH-MOB",
                "daily_field_log_countersigned": True,
                "contractor_caused_idle_excluded": True,
                "standby_rate_of_active_pct": 50.0,
                "mob_demob_contract_share_pct": 10.1,
            },
        ],
        max_standby_rate_of_active_pct=50.0,
        max_mob_demob_contract_share_pct=10.0,
    )
    assert res["evaluated_claims_count"] == 2
    assert res["unverified_log_or_self_inflicted_idle_claim_ids"] == []
    assert res["excessive_standby_rate_or_mob_cap_claim_ids"] == [
        "CLM-HIGH-STANDBY",
        "CLM-HIGH-MOB",
    ]
    assert (
        res["standby_demurrage_status"]
        == "DEMURRAGE_STANDBY_RATE_OR_MOB_CAP_WARNING"
    )
    assert res["is_standby_demurrage_compliant"] is False


def test_evaluate_evm_standby_demurrage_and_force_account_rates_optimal_and_defensive():
    from backend.services.project_evm_service import (
        evaluate_evm_standby_demurrage_and_force_account_rates,
    )

    empty = evaluate_evm_standby_demurrage_and_force_account_rates(None)
    assert empty["evaluated_claims_count"] == 0
    assert empty["unverified_log_or_self_inflicted_idle_claim_ids"] == []
    assert empty["excessive_standby_rate_or_mob_cap_claim_ids"] == []
    assert (
        empty["standby_demurrage_status"] == "DEMURRAGE_FORCE_ACCOUNT_OPTIMAL"
    )
    assert empty["is_standby_demurrage_compliant"] is True

    optimal = evaluate_evm_standby_demurrage_and_force_account_rates(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"claim_id": "   "},
            {
                "claim_id": "CLM-DEFAULTS",
                "daily_field_log_countersigned": None,
                "contractor_caused_idle_excluded": None,
                "standby_rate_of_active_pct": None,
                "mob_demob_contract_share_pct": None,
            },
        ]
    )
    assert optimal["evaluated_claims_count"] == 1
    assert optimal["unverified_log_or_self_inflicted_idle_claim_ids"] == []
    assert optimal["excessive_standby_rate_or_mob_cap_claim_ids"] == []
    assert (
        optimal["standby_demurrage_status"]
        == "DEMURRAGE_FORCE_ACCOUNT_OPTIMAL"
    )
    assert optimal["is_standby_demurrage_compliant"] is True


def test_evaluate_evm_standby_demurrage_and_force_account_rates_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_standby_demurrage_and_force_account_rates,
    )

    sample = [
        {
            "claim_id": "CLM-99",
            "standby_rate_of_active_pct": 30.0,
            "mob_demob_contract_share_pct": 5.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_standby_demurrage_and_force_account_rates(
            sample
        )
        == evaluate_evm_standby_demurrage_and_force_account_rates(sample)
    )
    assert (
        "evaluate_evm_standby_demurrage_and_force_account_rates"
        in mod.__all__
    )


def test_evaluate_evm_schedule_of_values_front_loading_and_stored_materials_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_schedule_of_values_front_loading_and_stored_materials,
    )

    result = evaluate_evm_schedule_of_values_front_loading_and_stored_materials(
        [
            {
                "item_id": "SOV-UNINSURED",
                "early_phase_markup_skew_pct": 6.0,
                "stored_materials_share_pct": 12.0,
                "bonded_warehouse_and_insurance_verified": False,
                "unconditional_title_transfer_bill_of_sale": True,
            },
            {
                "item_id": "SOV-NO-BILL-OF-SALE",
                "early_phase_markup_skew_pct": 4.0,
                "stored_materials_share_pct": 10.0,
                "bonded_warehouse_and_insurance_verified": True,
                "unconditional_title_transfer_bill_of_sale": False,
            },
        ],
        max_early_phase_markup_skew_pct=15.0,
        max_stored_materials_share_pct=20.0,
    )
    assert result["evaluated_items_count"] == 2
    assert result["uninsured_or_untitled_stored_material_item_ids"] == [
        "SOV-UNINSURED",
        "SOV-NO-BILL-OF-SALE",
    ]
    assert result["front_loaded_or_excess_stored_item_ids"] == []
    assert (
        result["sov_billing_status"]
        == "SOV_STORED_MATERIAL_TITLE_OR_INSURANCE_BREACH"
    )
    assert result["is_sov_billing_compliant"] is False


def test_evaluate_evm_schedule_of_values_front_loading_and_stored_materials_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_schedule_of_values_front_loading_and_stored_materials,
    )

    result = evaluate_evm_schedule_of_values_front_loading_and_stored_materials(
        [
            {
                "item_id": "SOV-FRONT-LOADED",
                "early_phase_markup_skew_pct": 24.5,
                "stored_materials_share_pct": 5.0,
                "bonded_warehouse_and_insurance_verified": True,
                "unconditional_title_transfer_bill_of_sale": True,
            },
            {
                "item_id": "SOV-EXCESS-STORED",
                "early_phase_markup_skew_pct": 4.0,
                "stored_materials_share_pct": 32.0,
                "bonded_warehouse_and_insurance_verified": True,
                "unconditional_title_transfer_bill_of_sale": True,
            },
        ],
        max_early_phase_markup_skew_pct=15.0,
        max_stored_materials_share_pct=20.0,
    )
    assert result["evaluated_items_count"] == 2
    assert result["uninsured_or_untitled_stored_material_item_ids"] == []
    assert result["front_loaded_or_excess_stored_item_ids"] == [
        "SOV-FRONT-LOADED",
        "SOV-EXCESS-STORED",
    ]
    assert (
        result["sov_billing_status"]
        == "SOV_FRONT_LOADING_OR_STORED_CAP_WARNING"
    )
    assert result["is_sov_billing_compliant"] is False


def test_evaluate_evm_schedule_of_values_front_loading_and_stored_materials_optimal_and_empty():
    from backend.services.project_evm_service import (
        evaluate_evm_schedule_of_values_front_loading_and_stored_materials,
    )

    empty = evaluate_evm_schedule_of_values_front_loading_and_stored_materials(
        [{"item_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_items_count"] == 0
    assert empty["sov_billing_status"] == "SOV_PROGRESS_BILLING_OPTIMAL"
    assert empty["is_sov_billing_compliant"] is True

    optimal = evaluate_evm_schedule_of_values_front_loading_and_stored_materials(
        [
            {
                "item_id": "SOV-STRUCTURAL-STEEL",
                "early_phase_markup_skew_pct": 6.0,
                "stored_materials_share_pct": 14.0,
                "bonded_warehouse_and_insurance_verified": True,
                "unconditional_title_transfer_bill_of_sale": True,
            },
            {
                "item_id": "SOV-ZERO-STORED",
                "early_phase_markup_skew_pct": 4.0,
                "stored_materials_share_pct": 0.0,
                "bonded_warehouse_and_insurance_verified": False,
                "unconditional_title_transfer_bill_of_sale": False,
            },
        ],
        max_early_phase_markup_skew_pct=15.0,
        max_stored_materials_share_pct=20.0,
    )
    assert optimal["evaluated_items_count"] == 2
    assert optimal["uninsured_or_untitled_stored_material_item_ids"] == []
    assert optimal["front_loaded_or_excess_stored_item_ids"] == []
    assert optimal["sov_billing_status"] == "SOV_PROGRESS_BILLING_OPTIMAL"
    assert optimal["is_sov_billing_compliant"] is True


def test_evaluate_evm_schedule_of_values_front_loading_and_stored_materials_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_schedule_of_values_front_loading_and_stored_materials,
    )

    sample = [
        {
            "item_id": "SOV-99",
            "early_phase_markup_skew_pct": 5.0,
            "stored_materials_share_pct": 10.0,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_schedule_of_values_front_loading_and_stored_materials(
            sample
        )
        == evaluate_evm_schedule_of_values_front_loading_and_stored_materials(
            sample
        )
    )
    assert (
        "evaluate_evm_schedule_of_values_front_loading_and_stored_materials"
        in mod.__all__
    )


def test_evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer_breach():
    from backend.services.project_evm_service import (
        evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer,
    )

    res = evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer(
        [
            {
                "lc_id": "  LC-REVOCABLE  ",
                "is_irrevocable_and_unconditional": False,
                "issuing_bank_investment_grade_verified": True,
                "days_until_expiry": 120,
                "undrawn_coverage_adequacy_pct": 105.0,
            },
            {
                "lc_id": "LC-SUBPRIME-BANK",
                "is_irrevocable_and_unconditional": True,
                "issuing_bank_investment_grade_verified": False,
                "days_until_expiry": 30,
                "undrawn_coverage_adequacy_pct": 90.0,
            },
            {
                "lc_id": "LC-EXPIRED",
                "is_irrevocable_and_unconditional": True,
                "issuing_bank_investment_grade_verified": True,
                "days_until_expiry": 0,
                "undrawn_coverage_adequacy_pct": 105.0,
            },
            {
                "lc_id": "LC-CLEAN",
                "is_irrevocable_and_unconditional": True,
                "issuing_bank_investment_grade_verified": True,
                "days_until_expiry": 60,
                "undrawn_coverage_adequacy_pct": 100.0,
            },
        ]
    )
    assert res["evaluated_letters_count"] == 4
    assert res["revocable_or_subprime_bank_lc_ids"] == [
        "LC-REVOCABLE",
        "LC-SUBPRIME-BANK",
        "LC-EXPIRED",
    ]
    assert res["expiring_buffer_or_underfunded_lc_ids"] == [
        "LC-SUBPRIME-BANK"
    ]
    assert (
        res["letter_of_credit_status"]
        == "LC_REVOCABLE_OR_BANK_SOLVENCY_BREACH"
    )
    assert res["is_letter_of_credit_compliant"] is False


def test_evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer,
    )

    res = evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer(
        [
            {
                "lc_id": "LC-EXPIRING-SOON",
                "is_irrevocable_and_unconditional": False,
                "issuing_bank_investment_grade_verified": False,
                "days_until_expiry": 59,
                "undrawn_coverage_adequacy_pct": 100.0,
            },
            {
                "lc_id": "LC-UNDERFUNDED",
                "is_irrevocable_and_unconditional": True,
                "issuing_bank_investment_grade_verified": True,
                "days_until_expiry": 60,
                "undrawn_coverage_adequacy_pct": 99.9,
            },
        ],
        min_expiry_buffer_days=60,
        require_tier1_bank_and_irrevocable=False,
    )
    assert res["evaluated_letters_count"] == 2
    assert res["revocable_or_subprime_bank_lc_ids"] == []
    assert res["expiring_buffer_or_underfunded_lc_ids"] == [
        "LC-EXPIRING-SOON",
        "LC-UNDERFUNDED",
    ]
    assert (
        res["letter_of_credit_status"]
        == "LC_EXPIRY_BUFFER_OR_COVERAGE_WARNING"
    )
    assert res["is_letter_of_credit_compliant"] is False


def test_evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer_optimal_and_defensive():
    from backend.services.project_evm_service import (
        evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer,
    )

    empty = evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer(None)
    assert empty["evaluated_letters_count"] == 0
    assert empty["letter_of_credit_status"] == "LC_DOCUMENTARY_SECURITY_OPTIMAL"
    assert empty["is_letter_of_credit_compliant"] is True

    defaults = evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"lc_id": "   "},
            {
                "lc_id": "LC-DEFAULTS",
                "is_irrevocable_and_unconditional": None,
                "issuing_bank_investment_grade_verified": None,
                "days_until_expiry": None,
                "undrawn_coverage_adequacy_pct": None,
            },
        ]
    )
    assert defaults["evaluated_letters_count"] == 1
    assert (
        defaults["letter_of_credit_status"]
        == "LC_DOCUMENTARY_SECURITY_OPTIMAL"
    )
    assert defaults["is_letter_of_credit_compliant"] is True


def test_evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer,
    )

    sample = [{"lc_id": "LC-99", "days_until_expiry": 90}]
    assert (
        ProjectEVMService.evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer(
            sample
        )
        == evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer(sample)
    )
    assert (
        "evaluate_evm_letter_of_credit_drawdown_and_evergreen_buffer"
        in mod.__all__
    )


def test_evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus_critical_breaches():
    from backend.services.project_evm_service import (
        evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus,
    )

    res = evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus(
        [
            {
                "milestone_id": "MS-LD-CAP",
                "contract_value": 100000.0,
                "baseline_duration_days": 100,
                "actual_duration_days": 130,
                "excusable_delay_days": 5,
                "concurrent_owner_delay_days": 0,
                "concurrent_delay_apportioned": True,
                "daily_ld_rate": 500.0,
                "accrued_ld_amount": 12500.0,
            },
            {
                "milestone_id": "MS-UNAPPORTIONED",
                "contract_value": 200000.0,
                "baseline_duration_days": 90,
                "actual_duration_days": 105,
                "excusable_delay_days": 0,
                "concurrent_owner_delay_days": 8,
                "concurrent_delay_apportioned": False,
                "daily_ld_rate": 400.0,
                "accrued_ld_amount": 6000.0,
            },
            {
                "milestone_id": "MS-EXCUSABLE-LD",
                "contract_value": 150000.0,
                "baseline_duration_days": 60,
                "actual_duration_days": 70,
                "excusable_delay_days": 12,
                "concurrent_owner_delay_days": 0,
                "concurrent_delay_apportioned": True,
                "daily_ld_rate": 300.0,
                "accrued_ld_amount": 3000.0,
            },
        ],
        max_ld_cap_pct_of_contract=10.0,
        require_concurrent_delay_apportionment=True,
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["milestones_evaluated"] == 3
    assert res["ld_cap_breach_milestone_ids"] == ["MS-LD-CAP"]
    assert res["unapportioned_delay_milestone_ids"] == ["MS-UNAPPORTIONED"]
    assert len(res["records"]) == 3
    assert res["records"][0]["adjusted_completion_days"] == 105
    assert res["records"][0]["net_unexcused_delay_days"] == 25
    assert res["records"][0]["ld_cap_exceeded"] is True
    assert res["records"][1]["concurrent_delay_unapportioned"] is True
    assert res["records"][2]["net_unexcused_delay_days"] == 0
    assert res["records"][2]["early_days"] == 2
    assert res["records"][2]["ld_assessed_during_excusable_delay"] is True
    assert len(res["violations"]) == 3


def test_evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus,
    )

    res = evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus(
        [
            {
                "milestone_id": "MS-BONUS-EXCESS",
                "contract_value": 100000.0,
                "baseline_duration_days": 100,
                "actual_duration_days": 80,
                "excusable_delay_days": 0,
                "daily_early_bonus_rate": 400.0,
                "accrued_bonus_amount": 8000.0,
            }
        ],
        max_early_bonus_cap_pct=5.0,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["milestones_evaluated"] == 1
    assert res["ld_cap_breach_milestone_ids"] == []
    assert res["unapportioned_delay_milestone_ids"] == []
    assert res["records"][0]["early_days"] == 20
    assert res["records"][0]["early_bonus_cap_exceeded"] is True
    assert len(res["violations"]) == 1


def test_evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus_compliant_and_boundaries():
    from backend.services.project_evm_service import (
        evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus,
    )

    res = evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus(
        [
            {
                "milestone_id": "MS-BOUNDARY-LD",
                "contract_value": 100000.0,
                "baseline_duration_days": 100,
                "actual_duration_days": 115,
                "excusable_delay_days": 5,
                "concurrent_owner_delay_days": 3,
                "concurrent_delay_apportioned": True,
                "daily_ld_rate": 1000.0,
                "accrued_ld_amount": 10000.0,
            },
            {
                "milestone_id": "MS-BOUNDARY-BONUS",
                "contract_value": 100000.0,
                "baseline_duration_days": 100,
                "actual_duration_days": 90,
                "excusable_delay_days": 0,
                "daily_early_bonus_rate": 500.0,
                "accrued_bonus_amount": 5000.0,
            },
        ],
        max_ld_cap_pct_of_contract=10.0,
        max_early_bonus_cap_pct=5.0,
    )
    assert res["status"] == "compliant"
    assert res["is_compliant"] is True
    assert res["milestones_evaluated"] == 2
    assert res["ld_cap_breach_milestone_ids"] == []
    assert res["unapportioned_delay_milestone_ids"] == []
    assert res["violations"] == []


def test_evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus_defensive_and_exports():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus,
    )

    empty = evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"milestone_id": "   "},
            {"milestone_id": "MS-ZERO-CV", "contract_value": 0.0},
        ]
    )
    assert empty["status"] == "compliant"
    assert empty["is_compliant"] is True
    assert empty["milestones_evaluated"] == 0

    sample = [
        {
            "milestone_id": "MS-99",
            "contract_value": 50000.0,
            "baseline_duration_days": 30,
            "actual_duration_days": 30,
        }
    ]
    assert (
        ProjectEVMService.evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus(
            sample
        )
        == evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus(
            sample
        )
    )
    assert (
        "evaluate_evm_liquidated_damages_excusable_delay_and_early_bonus"
        in mod.__all__
    )


def test_evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement_compliant():
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement,
    )

    res = evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement(
        [
            {
                "subcontract_id": "SUB-101",
                "subcontract_value": 200000.0,
                "backcharge_amount": 10000.0,
                "cure_notice_hours_given": 72.0,
                "photo_and_cost_substantiation_attached": True,
                "lower_tier_supplier_arrears_amount": 15000.0,
                "joint_check_agreement_active": True,
                "unconditional_lien_waiver_on_file": True,
            }
        ]
    )
    assert res["status"] == "compliant"
    assert res["is_compliant"] is True
    assert res["subcontracts_evaluated"] == 1
    assert res["improper_backcharge_subcontract_ids"] == []
    assert res["lien_risk_subcontract_ids"] == []
    assert res["records"][0]["backcharge_pct"] == 5.0
    assert res["Violations"] == []


def test_evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement_critical():
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement,
    )

    res = evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement(
        [
            {
                "subcontract_id": "SUB-BREACH",
                "subcontract_value": 100000.0,
                "backcharge_amount": 8000.0,
                "cure_notice_hours_given": 12.0,
                "photo_and_cost_substantiation_attached": False,
                "lower_tier_supplier_arrears_amount": 25000.0,
                "joint_check_agreement_active": False,
                "unconditional_lien_waiver_on_file": False,
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["improper_backcharge_subcontract_ids"] == ["SUB-BREACH"]
    assert res["lien_risk_subcontract_ids"] == ["SUB-BREACH"]
    assert len(res["Violations"]) >= 3


def test_evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement,
    )

    res = evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement(
        [
            {
                "id": "SUB-CAP-WARN",
                "subcontract_value": 100000.0,
                "backcharge_amount": 20000.0,
                "cure_notice_hours_given": 72.0,
                "photo_and_cost_substantiation_attached": True,
                "lower_tier_supplier_arrears_amount": 0.0,
                "joint_check_agreement_active": True,
                "unconditional_lien_waiver_on_file": True,
            }
        ],
        max_backcharge_pct_of_subcontract=15.0,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["improper_backcharge_subcontract_ids"] == ["SUB-CAP-WARN"]
    assert res["lien_risk_subcontract_ids"] == []
    assert res["records"][0]["backcharge_cap_exceeded"] is True


def test_evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement,
    )

    sample = [{"subcontract_id": "SUB-1", "subcontract_value": 50000.0}]
    assert (
        ProjectEVMService.evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement(
            sample
        )
        == evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement(
            sample
        )
    )
    assert (
        "evaluate_evm_subcontractor_backcharge_offset_and_joint_check_disbursement"
        in mod.__all__
    )



# ── evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate (PMBOK §7.4 & §12.3, pure helper) ──


def test_equipment_fleet_billing_optimal_rates():
    """Equipos con idle <= factor O&O, sin consumables en idle y fuel substantiado -> 'EQUIPMENT_FLEET_BILLING_OPTIMAL'."""
    import backend.services.project_evm_service as evm_module
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate,
    )

    equipment_logs = [
        {
            "equipment_id": "EQ-001",
            "ownership_hourly_rate": 100.0,
            "operating_consumables_charged_on_idle": False,
            "billed_idle_hourly_rate": 45.0,
            "fuel_surcharge_pct": 3.0,
            "fuel_index_invoice_attached": True,
        },
        {
            "equipment_id": "EQ-002",
            # Defaults implícitos por campo: 100.0 O&O, False, 45.0 idle, 3.0 fuel, invoice True.
        },
    ]
    res = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(equipment_logs)
    assert res == {
        "evaluated_equipment_count": 2,
        "overbilled_idle_or_consumables_equipment_ids": [],
        "unsubstantiated_fuel_surcharge_equipment_ids": [],
        "equipment_rate_status": "EQUIPMENT_FLEET_BILLING_OPTIMAL",
        "is_equipment_billing_compliant": True,
    }
    # Idle exactamente en ownership * 0.50 (50.0) no es overbill (comparación estricta >)
    at_factor = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [{"equipment_id": "EQ-003", "billed_idle_hourly_rate": 50.0}]
    )
    assert at_factor["equipment_rate_status"] == "EQUIPMENT_FLEET_BILLING_OPTIMAL"
    # Fuel surcharge alto con invoice adjunta no es warning (condición conjunta Y)
    fuel_with_invoice = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [{"equipment_id": "EQ-004", "fuel_surcharge_pct": 7.5}]
    )
    assert fuel_with_invoice["equipment_rate_status"] == "EQUIPMENT_FLEET_BILLING_OPTIMAL"
    assert (
        ProjectEVMService.evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
            equipment_logs
        )
        == res
    )
    assert "evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate" in evm_module.__all__


def test_equipment_fleet_idle_standby_overbill_breach():
    """Consumables en idle o idle > ownership * factor -> 'IDLE_STANDBY_OR_CONSUMABLES_OVERBILL_BREACH' con precedencia sobre WARNING."""
    from backend.services.project_evm_service import (
        evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate,
    )

    breach = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [
            {
                "equipment_id": "EQ-CONSUM",
                "operating_consumables_charged_on_idle": True,
                "billed_idle_hourly_rate": 40.0,
            },
            {
                "equipment_id": "EQ-EXPENSIVE-IDLE",
                "ownership_hourly_rate": 100.0,
                "billed_idle_hourly_rate": 55.0,
            },
        ]
    )
    assert breach["evaluated_equipment_count"] == 2
    assert breach["overbilled_idle_or_consumables_equipment_ids"] == [
        "EQ-CONSUM",
        "EQ-EXPENSIVE-IDLE",
    ]
    assert breach["equipment_rate_status"] == (
        "IDLE_STANDBY_OR_CONSUMABLES_OVERBILL_BREACH"
    )
    assert breach["is_equipment_billing_compliant"] is False

    # Breach tiene precedencia aunque también haya fuel surcharge sin substantiation
    mixed = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [
            {"equipment_id": "EQ-FUEL-NO-INV", "fuel_surcharge_pct": 8.0, "fuel_index_invoice_attached": False},
            {"equipment_id": "EQ-CONSUM-2", "operating_consumables_charged_on_idle": True},
        ]
    )
    assert mixed["equipment_rate_status"] == "IDLE_STANDBY_OR_CONSUMABLES_OVERBILL_BREACH"

    # Factor custom más permisivo (0.60) deja de marcar 55/100 como overbill
    relaxed = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [{"equipment_id": "EQ-REL", "ownership_hourly_rate": 100.0, "billed_idle_hourly_rate": 55.0}],
        max_idle_standby_rate_factor=0.60,
    )
    assert relaxed["equipment_rate_status"] == "EQUIPMENT_FLEET_BILLING_OPTIMAL"


def test_equipment_fleet_fuel_surcharge_substantiation_warning():
    """Fuel surcharge > 5.0 sin invoice del índice (con idle limpio) -> 'FUEL_SURCHARGE_SUBSTANTIATION_WARNING'."""
    from backend.services.project_evm_service import (
        evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate,
    )

    warning = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [
            {
                "equipment_id": "EQ-FUEL-A",
                "fuel_surcharge_pct": 5.5,
                "fuel_index_invoice_attached": False,
            },
            {
                "equipment_id": "EQ-FUEL-B",
                "fuel_surcharge_pct": 6.0,
                "fuel_index_invoice_attached": False,
            },
        ]
    )
    assert warning["evaluated_equipment_count"] == 2
    assert warning["overbilled_idle_or_consumables_equipment_ids"] == []
    assert warning["unsubstantiated_fuel_surcharge_equipment_ids"] == [
        "EQ-FUEL-A",
        "EQ-FUEL-B",
    ]
    assert warning["equipment_rate_status"] == "FUEL_SURCHARGE_SUBSTANTIATION_WARNING"
    assert warning["is_equipment_billing_compliant"] is False

    # Fuel exactamente en el umbral 5.0 sin invoice no es warning (comparación estricta >)
    at_threshold = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [{"equipment_id": "EQ-FUEL-C", "fuel_surcharge_pct": 5.0, "fuel_index_invoice_attached": False}]
    )
    assert at_threshold["equipment_rate_status"] == "EQUIPMENT_FLEET_BILLING_OPTIMAL"

    custom = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [{"equipment_id": "EQ-FUEL-D", "fuel_surcharge_pct": 3.5, "fuel_index_invoice_attached": False}],
        max_unsubstantiated_fuel_surcharge_pct=3.0,
    )
    assert custom["equipment_rate_status"] == "FUEL_SURCHARGE_SUBSTANTIATION_WARNING"
    assert custom["unsubstantiated_fuel_surcharge_equipment_ids"] == ["EQ-FUEL-D"]


def test_equipment_fleet_empty_invalid_and_field_reversion():
    """None / dicts inválidos se descartan; campos no numéricos/no bool revierten a defaults del spec."""
    from backend.services.project_evm_service import (
        evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate,
    )

    empty_res = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(None)
    assert empty_res == {
        "evaluated_equipment_count": 0,
        "overbilled_idle_or_consumables_equipment_ids": [],
        "unsubstantiated_fuel_surcharge_equipment_ids": [],
        "equipment_rate_status": "EQUIPMENT_FLEET_BILLING_OPTIMAL",
        "is_equipment_billing_compliant": True,
    }

    invalid_res = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        ["no-dict", None, {"equipment_id": "   "}, {"equipment_id": 45}, {"fuel_surcharge_pct": 9.0}]
    )
    assert invalid_res["evaluated_equipment_count"] == 0

    bad_fields = evaluate_evm_equipment_fleet_ownership_operating_and_idle_rate(
        [
            {
                "equipment_id": "EQ-BAD",
                "ownership_hourly_rate": "cien",
                "operating_consumables_charged_on_idle": "sí",
                "billed_idle_hourly_rate": None,
                "fuel_surcharge_pct": [9.0],
                "fuel_index_invoice_attached": 1,
            }
        ]
    )
    assert bad_fields == {
        "evaluated_equipment_count": 1,
        "overbilled_idle_or_consumables_equipment_ids": [],
        "unsubstantiated_fuel_surcharge_equipment_ids": [],
        "equipment_rate_status": "EQUIPMENT_FLEET_BILLING_OPTIMAL",
        "is_equipment_billing_compliant": True,
    }


def test_evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve_compliant():
    from backend.services.project_evm_service import (
        evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve,
    )

    res = evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve(
        [
            {
                "tranche_id": "FX-EUR-01",
                "total_foreign_commitment_usd": 1000000.0,
                "hedged_notional_usd": 900000.0,
                "baseline_fx_rate": 1.10,
                "spot_fx_rate": 1.12,
                "unrealized_fx_loss_usd": 18000.0,
                "fx_revaluation_reserve_usd": 25000.0,
            }
        ]
    )
    assert res["status"] == "compliant"
    assert res["is_compliant"] is True
    assert res["tranches_evaluated"] == 1
    assert res["unhedged_or_underreserved_tranche_ids"] == []
    assert res["collar_drift_tranche_ids"] == []
    assert res["records"][0]["unhedged_exposure_pct"] == 10.0
    assert res["records"][0]["fx_rate_drift_pct"] == 1.82
    assert res["Violations"] == []


def test_evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve_critical():
    from backend.services.project_evm_service import (
        evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve,
    )

    res = evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve(
        [
            {
                "tranche_id": "FX-UNHEDGED",
                "total_foreign_commitment_usd": 500000.0,
                "hedged_notional_usd": 200000.0,
                "baseline_fx_rate": 1.00,
                "spot_fx_rate": 1.03,
                "unrealized_fx_loss_usd": 45000.0,
                "fx_revaluation_reserve_usd": 10000.0,
            }
        ],
        max_unhedged_exposure_pct=15.0,
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["unhedged_or_underreserved_tranche_ids"] == ["FX-UNHEDGED"]
    assert len(res["Violations"]) >= 1


def test_evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve,
    )

    res = evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve(
        [
            {
                "id": "FX-COLLAR-DRIFT",
                "total_foreign_commitment_usd": 400000.0,
                "hedged_notional_usd": 380000.0,
                "baseline_fx_rate": 1.00,
                "spot_fx_rate": 1.09,
                "unrealized_fx_loss_usd": 10000.0,
                "fx_revaluation_reserve_usd": 20000.0,
            }
        ],
        max_fx_rate_collar_breach_pct=5.0,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["unhedged_or_underreserved_tranche_ids"] == []
    assert res["collar_drift_tranche_ids"] == ["FX-COLLAR-DRIFT"]
    assert res["records"][0]["fx_collar_band_exceeded"] is True


def test_evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve,
    )

    sample = [{"tranche_id": "FX-1", "total_foreign_commitment_usd": 0.0}]
    assert (
        ProjectEVMService.evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve(
            sample
        )
        == evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve(
            sample
        )
    )
    assert (
        "evaluate_evm_foreign_exchange_fx_hedging_collar_and_revaluation_reserve"
        in mod.__all__
    )


def test_evaluate_evm_economic_price_adjustment_epa_corridor_and_share_compliant():
    from backend.services.project_evm_service import (
        evaluate_evm_economic_price_adjustment_epa_corridor_and_share,
    )

    res = evaluate_evm_economic_price_adjustment_epa_corridor_and_share(
        [
            {
                "clause_id": "EPA-STEEL-01",
                "baseline_commodity_cost": 100000.0,
                "index_change_pct": 9.5,
                "billed_epa_adjustment_amount": 4500.0,
                "published_index_verified": True,
            }
        ]
    )
    assert res["status"] == "compliant"
    assert res["is_compliant"] is True
    assert res["clauses_evaluated"] == 1
    assert res["improper_deadband_or_index_clause_ids"] == []
    assert res["cap_exceeded_clause_ids"] == []
    assert res["Violations"] == []


def test_evaluate_evm_economic_price_adjustment_epa_corridor_and_share_critical():
    from backend.services.project_evm_service import (
        evaluate_evm_economic_price_adjustment_epa_corridor_and_share,
    )

    res = evaluate_evm_economic_price_adjustment_epa_corridor_and_share(
        [
            {
                "clause_id": "EPA-COPPER-DEADBAND",
                "baseline_commodity_cost": 50000.0,
                "index_change_pct": 3.2,
                "billed_epa_adjustment_amount": 1600.0,
                "published_index_verified": False,
            }
        ],
        deadband_corridor_pct=5.0,
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["improper_deadband_or_index_clause_ids"] == ["EPA-COPPER-DEADBAND"]
    assert res["records"][0]["unverified_index_or_within_deadband_billing"] is True
    assert len(res["Violations"]) >= 1


def test_evaluate_evm_economic_price_adjustment_epa_corridor_and_share_warning():
    from backend.services.project_evm_service import (
        evaluate_evm_economic_price_adjustment_epa_corridor_and_share,
    )

    res = evaluate_evm_economic_price_adjustment_epa_corridor_and_share(
        [
            {
                "id": "EPA-CEMENT-CAP",
                "baseline_commodity_cost": 100000.0,
                "index_change_pct": 22.0,
                "billed_epa_adjustment_amount": 18000.0,
                "published_index_verified": True,
            }
        ],
        max_owner_epa_payout_cap_pct=15.0,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["improper_deadband_or_index_clause_ids"] == []
    assert res["cap_exceeded_clause_ids"] == ["EPA-CEMENT-CAP"]
    assert res["records"][0]["epa_payout_cap_exceeded"] is True


def test_evaluate_evm_economic_price_adjustment_epa_corridor_and_share_staticmethod_and_dunder_all():
    import backend.services.project_evm_service as mod
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_economic_price_adjustment_epa_corridor_and_share,
    )

    sample = [{"clause_id": "EPA-01", "baseline_commodity_cost": 10000.0}]
    assert (
        ProjectEVMService.evaluate_evm_economic_price_adjustment_epa_corridor_and_share(
            sample
        )
        == evaluate_evm_economic_price_adjustment_epa_corridor_and_share(sample)
    )
    assert (
        "evaluate_evm_economic_price_adjustment_epa_corridor_and_share"
        in mod.__all__
    )




# ── evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi (PMBOK §7.4 & §12.2, pure helper) ──


def test_surety_bond_adequate_coverage_and_sdi_active_only():
    """Cobertura >= 100% de ambos fianzas, crecimiento <= 10% y solo subcontratistas activos -> 'BOND_ADEQUATE'."""
    import backend.services.project_evm_service as evm_module
    from backend.services.project_evm_service import (
        ProjectEVMService,
        evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi,
    )

    exposures = [{"subcontractor_id": "SUB-001", "status": "ACTIVE", "exposure_cost": 300000.0}]
    res = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        1000000.0, 1000000.0, 1000000.0, 1050000.0, exposures
    )
    assert res == {
        "bac_growth_pct": 0.0,
        "performance_bond_coverage_ratio_pct": 100.0,
        "payment_bond_coverage_ratio_pct": 105.0,
        "sdi_evaluated_subcontractors_count": 1,
        "sdi_defaulted_exposures_count": 0,
        "sdi_retained_loss_total": 0.0,
        "sdi_net_recoverable_total": 0.0,
        "bond_coverage_status": "BOND_ADEQUATE",
        "is_surety_coverage_adequate": True,
    }
    assert (
        ProjectEVMService.evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
            1000000.0, 1000000.0, 1000000.0, 1050000.0, exposures
        )
        == res
    )
    assert "evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi" in evm_module.__all__


def test_surety_rider_endorsement_required_growth():
    """Crecimiento de BAC 10.1% > 10.0% sin rider, con cobertura suficiente -> 'RIDER_ENDORSEMENT_REQUIRED'."""
    from backend.services.project_evm_service import (
        evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi,
    )

    res = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        1101000.0, 1000000.0, 1101000.0, 1150000.0, []
    )
    assert res["bac_growth_pct"] == 10.1
    assert res["performance_bond_coverage_ratio_pct"] == 100.0
    assert res["payment_bond_coverage_ratio_pct"] == 104.45
    assert res["bond_coverage_status"] == "RIDER_ENDORSEMENT_REQUIRED"
    assert res["is_surety_coverage_adequate"] is False

    # Crecimiento exactamente en 10.0 no exige rider (comparación estricta >)
    at_threshold = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        1100000.0, 1000000.0, 1100000.0, 1100000.0, []
    )
    assert at_threshold["bac_growth_pct"] == 10.0
    assert at_threshold["bond_coverage_status"] == "BOND_ADEQUATE"


def test_surety_critical_undercoverage_and_sdi_retention_math():
    """Performance bond 50% < 100% -> 'CRITICAL_BOND_UNDERCOVERAGE' (precedencia) con retención SDI (deducible + coaseguro) y neto recuperable."""
    from backend.services.project_evm_service import (
        evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi,
    )

    exposures = [
        {"subcontractor_id": "SUB-D1", "status": "DEFAULTED", "exposure_cost": 120000.0},
        {"subcontractor_id": "SUB-D2", "status": "DEFAULTED", "exposure_cost": 70000.0},
        {"subcontractor_id": "SUB-A1", "status": "ACTIVE", "exposure_cost": 200000.0},
        "no-dict",
        {"subcontractor_id": "   "},
    ]
    res = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        1000000.0, 1000000.0, 500000.0, 1000000.0, exposures
    )
    assert res["sdi_evaluated_subcontractors_count"] == 3
    assert res["sdi_defaulted_exposures_count"] == 2
    # SUB-D1: retencion = 50000 + 70000*10% = 57000 -> neto 63000
    # SUB-D2: retencion = 50000 + 20000*10% = 52000 -> neto 18000
    # SUB-A1 activo no genera perdida; invalidos se descartan
    assert res["sdi_retained_loss_total"] == 109000.0
    assert res["sdi_net_recoverable_total"] == 81000.0
    assert res["performance_bond_coverage_ratio_pct"] == 50.0
    assert res["bond_coverage_status"] == "CRITICAL_BOND_UNDERCOVERAGE"
    assert res["is_surety_coverage_adequate"] is False

    # Sin rider por debajo del min de cobertura: la subcobertura tiene precedencia
    under_with_growth = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        1200000.0, 1000000.0, 600000.0, 1200000.0, []
    )
    assert under_with_growth["bac_growth_pct"] == 20.0
    assert under_with_growth["bond_coverage_status"] == "CRITICAL_BOND_UNDERCOVERAGE"

    # Deducible y coaseguro custom: costo bajo el deducible se retiene completo
    under_deductible = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        1000000.0, 1000000.0, 1000000.0, 1000000.0,
        [{"subcontractor_id": "SUB-SMALL", "status": "DEFAULTED", "exposure_cost": 8000.0}],
        sdi_deductible_per_loss=20000.0,
        sdi_coinsurance_pct=20.0,
    )
    assert under_deductible["sdi_retained_loss_total"] == 8000.0
    assert under_deductible["sdi_net_recoverable_total"] == 0.0
    assert under_deductible["bond_coverage_status"] == "BOND_ADEQUATE"


def test_surety_bac_zero_none_and_invalid_exposures():
    """BAC <= 0 y suma original no positiva no subcobertizan ni exigen rider; exposiciones inválidas se descartan."""
    from backend.services.project_evm_service import (
        evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi,
    )

    res = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        0.0, 0.0, 0.0, 0.0, None
    )
    assert res == {
        "bac_growth_pct": 0.0,
        "performance_bond_coverage_ratio_pct": 100.0,
        "payment_bond_coverage_ratio_pct": 100.0,
        "sdi_evaluated_subcontractors_count": 0,
        "sdi_defaulted_exposures_count": 0,
        "sdi_retained_loss_total": 0.0,
        "sdi_net_recoverable_total": 0.0,
        "bond_coverage_status": "BOND_ADEQUATE",
        "is_surety_coverage_adequate": True,
    }

    invalid = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        1000000.0, 1000000.0, 1000000.0, 1000000.0,
        ["no-dict", None, {"subcontractor_id": ""}, {"subcontractor_id": 9}],
    )
    assert invalid["sdi_evaluated_subcontractors_count"] == 0

    bad_fields = evaluate_evm_surety_performance_bond_and_subcontractor_default_sdi(
        "millón", 1000000.0, None, True,
        [{"subcontractor_id": "SUB-BAD", "status": "ACTIVE", "exposure_cost": "mucho"}],
    )
    # current_bac no numerico -> neutral (cobertura 100.0, sin subcobertura ni rider)
    assert bad_fields["performance_bond_coverage_ratio_pct"] == 100.0
    assert bad_fields["payment_bond_coverage_ratio_pct"] == 100.0
    assert bad_fields["sdi_defaulted_exposures_count"] == 0
    assert bad_fields["bond_coverage_status"] == "BOND_ADEQUATE"

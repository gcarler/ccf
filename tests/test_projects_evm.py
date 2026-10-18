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

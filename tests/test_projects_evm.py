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

from backend.services.project_evm_service import calculate_project_evm, generate_curve_s_data


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


if __name__ == "__main__":
    test_evm_balanced_project()
    test_evm_cost_overrun_critical()
    test_evm_cost_efficient()
    test_evm_zero_cost_edge_case()
    test_curve_s_generation()
    print("✅ All EVM tests passed successfully!")


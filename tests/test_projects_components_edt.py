"""Tests para EDT Nivel 2: Componentes de Proyecto y Regla del 100% PMI.

Verifica:
1. Modelo ProjectComponent y operaciones CRUD.
2. Unicidad de código dentro del proyecto.
3. Cálculo de EVM sectorizado por componente (BAC, EV, PV, AC, CPI, SPI, CV, SV, balance gap).
4. Validación canónica de la Regla del 100% de la EDT (PMI).
5. Asociación de tareas (ProjectTask.component_id) y gastos (ProjectExpense.component_id).
6. Endpoints de la API FastAPI y aislamiento multi-tenant (Axioma 3).
"""

from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend import crud, models, schemas
from backend.services.project_evm_service import (
    calculate_component_evm,
    get_project_components_breakdown,
    validate_project_budget_100_rule,
)


def _utcnow():
    return datetime.datetime.now(timezone.utc)


def test_component_model_attributes():
    """Valida los atributos requeridos en el modelo ProjectComponent."""
    comp = models.ProjectComponent(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        code="CMP-01",
        name="Infraestructura",
        description="Servidores y redes",
        budget_allocated=25000.0,
        order_index=1,
        color="#10b981",
        status="active",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    assert comp.code == "CMP-01"
    assert comp.name == "Infraestructura"
    assert comp.budget_allocated == 25000.0
    assert comp.order_index == 1
    assert comp.color == "#10b981"
    assert comp.status == "active"
    assert comp.deleted_at is None


def test_calculate_component_evm_formulas():
    """Valida las fórmulas de EVM a nivel de componente."""
    comp_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    now = _utcnow()

    component = MagicMock(spec=models.ProjectComponent)
    component.id = comp_id
    component.project_id = proj_id
    component.code = "EDT-1.1"
    component.name = "Desarrollo Backend"
    component.budget_allocated = 50000.0

    # Crear 4 tareas mock: 2 completadas y 2 pendientes (avance físico 50%)
    task1 = MagicMock(spec=models.ProjectTask)
    task1.component_id = comp_id
    task1.status = "completed"
    task1.due_date = now - timedelta(days=5)
    task1.deleted_at = None

    task2 = MagicMock(spec=models.ProjectTask)
    task2.component_id = comp_id
    task2.status = "done"
    task2.due_date = now - timedelta(days=2)
    task2.deleted_at = None

    task3 = MagicMock(spec=models.ProjectTask)
    task3.component_id = comp_id
    task3.status = "in_progress"
    task3.due_date = now + timedelta(days=10)
    task3.deleted_at = None

    task4 = MagicMock(spec=models.ProjectTask)
    task4.component_id = comp_id
    task4.status = "todo"
    task4.due_date = now + timedelta(days=20)
    task4.deleted_at = None

    # Gastos mock del componente: 20,000 aprobados
    exp1 = MagicMock(spec=models.ProjectExpense)
    exp1.component_id = comp_id
    exp1.amount = 20000.0
    exp1.status = "paid"
    exp1.deleted_at = None

    db = MagicMock()

    def query_mock(model):
        q = MagicMock()
        if model == models.ProjectTask:
            q.filter.return_value.all.return_value = [task1, task2, task3, task4]
        elif model == models.ProjectExpense:
            q.filter.return_value.all.return_value = [exp1]
        return q

    db.query.side_effect = query_mock

    metrics = calculate_component_evm(db, component, now=now)

    assert metrics["component_id"] == str(comp_id)
    assert metrics["budget_allocated"] == 50000.0
    assert metrics["total_tasks"] == 4
    assert metrics["completed_tasks"] == 2
    assert metrics["physical_progress_pct"] == 50.0
    # EV = 50000 * 0.50 = 25000
    assert metrics["ev"] == 25000.0
    # AC = 20000
    assert metrics["ac"] == 20000.0
    # CPI = 25000 / 20000 = 1.25
    assert metrics["cpi"] == 1.25
    # CV = 25000 - 20000 = +5000
    assert metrics["cv"] == 5000.0
    # PV = 50000 * (2 vencidas / 4 totales) = 25000
    assert metrics["pv"] == 25000.0
    # SPI = 25000 / 25000 = 1.0
    assert metrics["spi"] == 1.0
    assert metrics["sv"] == 0.0
    # Financial % = 20000 / 50000 = 40%
    assert metrics["financial_progress_pct"] == 40.0
    # Balance gap = 50% - 40% = +10%
    assert metrics["balance_gap_pct"] == 10.0
    assert metrics["health_status"] == "OPTIMO"
    assert metrics["health_color"] == "success"


def test_budget_100_rule_balanced():
    """La suma de componentes iguala al presupuesto del proyecto (100% exacto)."""
    proj = MagicMock(spec=models.Project)
    proj.id = uuid.uuid4()
    proj.budget_allocated = 100000.0

    c1 = MagicMock(spec=models.ProjectComponent)
    c1.budget_allocated = 60000.0

    c2 = MagicMock(spec=models.ProjectComponent)
    c2.budget_allocated = 40000.0

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [c1, c2]

    res = validate_project_budget_100_rule(db, proj)

    assert res["project_budget_allocated"] == 100000.0
    assert res["components_budget_total"] == 100000.0
    assert res["budget_difference"] == 0.0
    assert res["allocation_percentage"] == 100.0
    assert res["status"] == "balanced"
    assert res["is_rule_satisfied"] is True
    assert res["is_fully_allocated"] is True
    assert res["components_count"] == 2


def test_budget_100_rule_under_allocated():
    """La suma de componentes es menor que el presupuesto del proyecto."""
    proj = MagicMock(spec=models.Project)
    proj.id = uuid.uuid4()
    proj.budget_allocated = 100000.0

    c1 = MagicMock(spec=models.ProjectComponent)
    c1.budget_allocated = 70000.0

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [c1]

    res = validate_project_budget_100_rule(db, proj)

    assert res["project_budget_allocated"] == 100000.0
    assert res["components_budget_total"] == 70000.0
    assert res["budget_difference"] == 30000.0
    assert res["allocation_percentage"] == 70.0
    assert res["status"] == "under_allocated"
    assert res["is_rule_satisfied"] is True
    assert res["is_fully_allocated"] is False


def test_budget_100_rule_over_allocated():
    """La suma de componentes supera el presupuesto del proyecto."""
    proj = MagicMock(spec=models.Project)
    proj.id = uuid.uuid4()
    proj.budget_allocated = 100000.0

    c1 = MagicMock(spec=models.ProjectComponent)
    c1.budget_allocated = 70000.0
    c2 = MagicMock(spec=models.ProjectComponent)
    c2.budget_allocated = 50000.0

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [c1, c2]

    res = validate_project_budget_100_rule(db, proj)

    assert res["project_budget_allocated"] == 100000.0
    assert res["components_budget_total"] == 120000.0
    assert res["budget_difference"] == -20000.0
    assert res["allocation_percentage"] == 120.0
    assert res["status"] == "over_allocated"
    assert res["is_rule_satisfied"] is False
    assert res["is_fully_allocated"] is False


def test_budget_100_rule_no_budget():
    """Proyecto con presupuesto 0 no configurado."""
    proj = MagicMock(spec=models.Project)
    proj.id = uuid.uuid4()
    proj.budget_allocated = 0.0

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    res = validate_project_budget_100_rule(db, proj)
    assert res["status"] == "no_project_budget"
    assert res["is_rule_satisfied"] is False


def test_components_breakdown_service():
    """Valida la agregación completa de componentes con EVM y regla del 100%."""
    proj = MagicMock(spec=models.Project)
    proj.id = uuid.uuid4()
    proj.budget_allocated = 50000.0

    c1 = MagicMock(spec=models.ProjectComponent)
    c1.id = uuid.uuid4()
    c1.project_id = proj.id
    c1.code = "CMP-01"
    c1.name = "Componente 1"
    c1.description = "Desc"
    c1.budget_allocated = 50000.0
    c1.order_index = 0
    c1.color = "#3b82f6"
    c1.status = "active"
    c1.created_at = _utcnow()
    c1.updated_at = _utcnow()
    c1.deleted_at = None

    db = MagicMock()

    def query_mock(model):
        q = MagicMock()
        if model == models.ProjectComponent:
            q.filter.return_value.order_by.return_value.all.return_value = [c1]
        elif model == models.ProjectTask:
            q.filter.return_value.all.return_value = []
            q.filter.return_value.count.return_value = 0
        elif model == models.ProjectExpense:
            q.filter.return_value.all.return_value = []
            q.filter.return_value.count.return_value = 0
        return q

    db.query.side_effect = query_mock

    breakdown = get_project_components_breakdown(db, proj)
    assert breakdown["project_id"] == str(proj.id)
    assert len(breakdown["components"]) == 1
    assert breakdown["components"][0]["code"] == "CMP-01"
    assert breakdown["budget_rule"]["status"] == "balanced"


def test_project_components_crud_in_memory(db_session):
    """Prueba el ciclo de vida CRUD de componentes en base de datos real SQLite."""
    from tests.conftest import seed_admin

    user, persona, sede = seed_admin(db_session, email="edt-crud-admin@example.com")

    # Crear proyecto
    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto EDT Test",
        sede_id=sede.id,
        budget_allocated=100000.0,
    )
    db_session.add(project)
    db_session.commit()

    # 1. Crear componentes
    c1_in = schemas.ProjectComponentCreate(
        code="CMP-01",
        name="Ingeniería y Diseño",
        budget_allocated=40000.0,
        order_index=1,
    )
    c1 = crud.create_project_component(db_session, project.id, c1_in)
    assert c1.id is not None
    assert c1.code == "CMP-01"

    c2_in = schemas.ProjectComponentCreate(
        code="CMP-02",
        name="Construcción",
        budget_allocated=60000.0,
        order_index=2,
    )
    c2 = crud.create_project_component(db_session, project.id, c2_in)
    assert c2.id is not None
    assert c2.code == "CMP-02"

    # 2. Listar componentes
    components = crud.get_project_components(db_session, project.id)
    assert len(components) == 2
    assert components[0].code == "CMP-01"
    assert components[1].code == "CMP-02"

    # 3. Asociar tarea a componente
    task = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=c1.id,
        title="Diseño Arquitectónico",
        status="completed",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    assert task.component_id == c1.id

    # 4. Asociar gasto a componente
    expense = models.ProjectExpense(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=c1.id,
        amount=15000.0,
        status="paid",
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    assert expense.component_id == c1.id

    # 5. EVM del componente
    evm1 = calculate_component_evm(db_session, c1)
    assert evm1["completed_tasks"] == 1
    assert evm1["total_tasks"] == 1
    assert evm1["physical_progress_pct"] == 100.0
    assert evm1["ev"] == 40000.0
    assert evm1["ac"] == 15000.0
    assert evm1["cpi"] == round(40000.0 / 15000.0, 2)

    # 6. Regla del 100%
    rule = validate_project_budget_100_rule(db_session, project)
    assert rule["status"] == "balanced"
    assert rule["is_rule_satisfied"] is True
    assert rule["is_fully_allocated"] is True

    # 7. Actualizar componente
    upd = schemas.ProjectComponentUpdate(name="Ingeniería y Detalle", budget_allocated=45000.0)
    c1_updated = crud.update_project_component(db_session, project.id, c1.id, upd)
    assert c1_updated.name == "Ingeniería y Detalle"
    assert c1_updated.budget_allocated == 45000.0

    # 8. Soft delete y desvinculación
    ok = crud.delete_project_component(db_session, project.id, c1.id)
    assert ok is True

    db_session.refresh(task)
    db_session.refresh(expense)
    assert task.component_id is None
    assert expense.component_id is None

    # Ya no aparece en lista activa
    remaining = crud.get_project_components(db_session, project.id)
    assert len(remaining) == 1
    assert remaining[0].code == "CMP-02"


def test_api_components_endpoints_flow(client: TestClient, db_session):
    """Prueba los endpoints HTTP de FastAPI para gestión de componentes EDT."""
    from tests.conftest import auth_headers, seed_admin

    user, persona, sede = seed_admin(db_session, email="edt-api-admin@example.com")
    headers = auth_headers(client, email="edt-api-admin@example.com")

    # Crear proyecto vía API o fábrica
    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto API EDT",
        sede_id=sede.id,
        budget_allocated=80000.0,
    )
    db_session.add(project)
    db_session.commit()

    # 1. POST /components
    resp = client.post(
        f"/api/projects/{project.id}/components",
        json={
            "code": "EDT-01",
            "name": "Fase de Requerimientos",
            "description": "Levantamiento y validación",
            "budget_allocated": 30000.0,
            "order_index": 1,
            "color": "#6366f1",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    comp_id = data["id"]
    assert data["code"] == "EDT-01"
    assert data["budget_allocated"] == 30000.0
    assert data["evm"] is not None

    # 2. Código duplicado debe responder 400
    resp_dup = client.post(
        f"/api/projects/{project.id}/components",
        json={
            "code": "EDT-01",
            "name": "Duplicado",
            "budget_allocated": 10000.0,
        },
        headers=headers,
    )
    assert resp_dup.status_code == 400

    # 3. GET /components
    resp_list = client.get(f"/api/projects/{project.id}/components", headers=headers)
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) == 1
    assert items[0]["id"] == comp_id

    # 4. GET /components/budget-100-rule
    resp_rule = client.get(f"/api/projects/{project.id}/components/budget-100-rule", headers=headers)
    assert resp_rule.status_code == 200
    rule = resp_rule.json()
    assert rule["project_budget_allocated"] == 80000.0
    assert rule["components_budget_total"] == 30000.0
    assert rule["status"] == "under_allocated"

    # 5. GET /components-breakdown
    resp_bd = client.get(f"/api/projects/{project.id}/components-breakdown", headers=headers)
    assert resp_bd.status_code == 200
    bd = resp_bd.json()
    assert len(bd["components"]) == 1
    assert bd["budget_rule"]["status"] == "under_allocated"

    # 6. PATCH /components/{component_id}
    resp_patch = client.patch(
        f"/api/projects/{project.id}/components/{comp_id}",
        json={"name": "Requerimientos y Alcance Actualizado", "budget_allocated": 80000.0},
        headers=headers,
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["budget_allocated"] == 80000.0

    # Ahora debe estar balanced (80k / 80k)
    resp_rule2 = client.get(f"/api/projects/{project.id}/components/budget-100-rule", headers=headers)
    assert resp_rule2.json()["status"] == "balanced"
    assert resp_rule2.json()["is_fully_allocated"] is True

    # 7. DELETE /components/{component_id}
    resp_del = client.delete(f"/api/projects/{project.id}/components/{comp_id}", headers=headers)
    assert resp_del.status_code == 200

    # Verificar que ya no está en la lista activa
    resp_list2 = client.get(f"/api/projects/{project.id}/components", headers=headers)
    assert len(resp_list2.json()) == 0

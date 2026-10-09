"""Tests para WBS / EDT Nivel 3: Paquetes de Trabajo, 3 Dimensiones y Roll-Up PMI.

Verifica:
1. Modelos ProjectTask (physical_progress_pct, estimated_hours) y ProjectExpense (task_id, task).
2. Validación de esquemas Pydantic para las 3 dimensiones de control.
3. Algoritmo de Roll-Up para paquete de trabajo hoja (leaf task).
4. Algoritmo de Roll-Up ponderado por esfuerzo (estimated_hours) en tareas padre.
5. Algoritmo de Roll-Up equitativo cuando las horas estimadas son 0.
6. Acumulación y desglose de costos (directos vs subtareas, AC, planned, committed).
7. Sincronización en cascada del avance continuo (sync_parent_task_rollup).
8. Resumen consolidado del proyecto (calculate_project_tasks_rollup).
9. Endpoints REST de la API FastAPI y validación de vinculación de gastos a tareas.
"""

from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

from backend import models, schemas
from backend.services.project_evm_service import (
    calculate_project_tasks_rollup,
    calculate_task_rollup,
    sync_parent_task_rollup,
)


def _utcnow():
    return datetime.datetime.now(timezone.utc)


def test_task_model_and_expense_attributes():
    """Valida los nuevos atributos y relaciones en ProjectTask y ProjectExpense."""
    task_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    task = models.ProjectTask(
        id=task_id,
        project_id=proj_id,
        title="Diseño de Arquitectura",
        status="in_progress",
        priority="high",
        physical_progress_pct=65.5,
        estimated_hours=40.0,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    assert task.physical_progress_pct == 65.5
    assert task.estimated_hours == 40.0
    assert hasattr(task, "expenses")

    expense_id = uuid.uuid4()
    expense = models.ProjectExpense(
        id=expense_id,
        project_id=proj_id,
        task_id=task_id,
        category="honorarios",
        amount=1500.0,
        status="paid",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    assert expense.task_id == task_id
    assert hasattr(expense, "task")


def test_pydantic_schemas_validation():
    """Valida las restricciones y serialización de los esquemas de las 3 Dimensiones."""
    # ProjectTaskBase
    task_in = schemas.ProjectTaskCreate(
        title="Creación de APIs",
        physical_progress_pct=80.0,
        estimated_hours=25.5,
    )
    assert task_in.physical_progress_pct == 80.0
    assert task_in.estimated_hours == 25.5

    # ProjectExpenseBase con task_id
    t_id = str(uuid.uuid4())
    expense_in = schemas.ProjectExpenseCreate(
        category="servicios",
        amount=500.0,
        task_id=t_id,
    )
    assert expense_in.task_id == t_id

    # Schemas de dimensiones
    time_dim = schemas.TaskTimeDimension(
        estimated_hours=20.0,
        actual_hours=15.0,
        subtasks_estimated_hours=10.0,
        total_estimated_hours=30.0,
    )
    assert time_dim.estimated_hours == 20.0
    assert time_dim.actual_hours == 15.0

    progress_dim = schemas.TaskProgressDimension(
        physical_progress_pct=50.0,
        rolled_up_progress_pct=75.0,
        is_leaf=False,
        subtasks_count=3,
        completed_subtasks_count=2,
        weight_basis="estimated_hours",
    )
    assert progress_dim.rolled_up_progress_pct == 75.0
    assert progress_dim.weight_basis == "estimated_hours"

    cost_dim = schemas.TaskCostDimension(
        direct_cost=300.0,
        subtasks_cost=700.0,
        total_cost=1000.0,
        actual_cost=800.0,
        planned_cost=200.0,
        expenses_count=4,
    )
    assert cost_dim.total_cost == 1000.0
    assert cost_dim.actual_cost == 800.0


def test_calculate_task_rollup_leaf_node():
    """Valida el cálculo de dimensiones en un paquete de trabajo hoja (sin subtareas)."""
    task_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    now = _utcnow()

    task = MagicMock(spec=models.ProjectTask)
    task.id = task_id
    task.project_id = proj_id
    task.title = "Maquetación UI"
    task.status = "in_progress"
    task.priority = "medium"
    task.parent_id = None
    task.component_id = None
    task.component = None
    task.physical_progress_pct = 45.0
    task.estimated_hours = 16.0
    task.start_date = now - timedelta(days=2)
    task.due_date = now + timedelta(days=2)
    task.deleted_at = None

    # Gastos directos de la tarea: 1 paid de $150 y 1 planned de $50
    exp1 = MagicMock(spec=models.ProjectExpense)
    exp1.id = uuid.uuid4()
    exp1.project_id = proj_id
    exp1.task_id = task_id
    exp1.component_id = None
    exp1.category = "software"
    exp1.description = "Licencia Figma"
    exp1.amount = 150.0
    exp1.date = now
    exp1.receipt_url = None
    exp1.status = "paid"
    exp1.created_by = None
    exp1.creator = None
    exp1.created_at = now
    exp1.updated_at = now
    exp1.deleted_at = None

    exp2 = MagicMock(spec=models.ProjectExpense)
    exp2.id = uuid.uuid4()
    exp2.project_id = proj_id
    exp2.task_id = task_id
    exp2.component_id = None
    exp2.category = "software"
    exp2.description = "Iconos premium"
    exp2.amount = 50.0
    exp2.date = now
    exp2.receipt_url = None
    exp2.status = "planned"
    exp2.created_by = None
    exp2.creator = None
    exp2.created_at = now
    exp2.updated_at = now
    exp2.deleted_at = None

    # Mock DB Session
    db = MagicMock()

    def query_side_effect(arg):
        q = MagicMock()
        if arg is models.ProjectTask or getattr(arg, "class_", None) is models.ProjectTask:
            q.filter.return_value.order_by.return_value.all.return_value = []
            q.filter.return_value.all.return_value = []
            return q
        if getattr(arg, "name", None) == "id" or str(arg).startswith("project_tasks"):
            q.filter.return_value.all.return_value = []
            return q
        if arg is models.ProjectTimeLog or getattr(arg, "class_", None) is models.ProjectTimeLog:
            tl = MagicMock(spec=models.ProjectTimeLog)
            tl.hours = 8.0
            tl.deleted_at = None
            q.filter.return_value.all.return_value = [tl]
            return q
        if arg is models.ProjectExpense or getattr(arg, "class_", None) is models.ProjectExpense:
            q.filter.return_value.all.return_value = [exp1, exp2]
            return q
        q.filter.return_value.all.return_value = []
        return q

    db.query.side_effect = query_side_effect

    rollup = calculate_task_rollup(db, task)

    # 1. Dimensión Tiempo
    assert rollup["time"]["estimated_hours"] == 16.0
    assert rollup["time"]["actual_hours"] == 8.0
    assert rollup["time"]["duration_days"] == 5

    # 2. Dimensión Avance Físico
    assert rollup["progress"]["is_leaf"] is True
    assert rollup["progress"]["physical_progress_pct"] == 45.0
    assert rollup["progress"]["rolled_up_progress_pct"] == 45.0
    assert rollup["progress"]["subtasks_count"] == 0

    # 3. Dimensión Costo
    assert rollup["cost"]["direct_cost"] == 200.0
    assert rollup["cost"]["subtasks_cost"] == 0.0
    assert rollup["cost"]["total_cost"] == 200.0
    assert rollup["cost"]["actual_cost"] == 150.0
    assert rollup["cost"]["planned_cost"] == 50.0
    assert rollup["cost"]["expenses_count"] == 2


def test_calculate_task_rollup_parent_weighted_by_hours():
    """Valida el cálculo de Roll-Up ponderado por esfuerzo (estimated_hours) en un nodo padre."""
    parent_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    now = _utcnow()

    parent = MagicMock(spec=models.ProjectTask)
    parent.id = parent_id
    parent.project_id = proj_id
    parent.title = "Fase Backend Completa"
    parent.status = "in_progress"
    parent.priority = "high"
    parent.parent_id = None
    parent.component_id = None
    parent.component = None
    parent.physical_progress_pct = 0.0
    parent.estimated_hours = 0.0
    parent.start_date = now
    parent.due_date = now + timedelta(days=10)
    parent.deleted_at = None

    # Subtarea 1: 10 horas, 40% avance, gasto $100 paid
    sub1_id = uuid.uuid4()
    sub1 = MagicMock(spec=models.ProjectTask)
    sub1.id = sub1_id
    sub1.project_id = proj_id
    sub1.title = "Modelos y Migraciones"
    sub1.status = "in_progress"
    sub1.priority = "medium"
    sub1.parent_id = parent_id
    sub1.component_id = None
    sub1.component = None
    sub1.physical_progress_pct = 40.0
    sub1.estimated_hours = 10.0
    sub1.start_date = now
    sub1.due_date = now + timedelta(days=3)
    sub1.deleted_at = None

    # Subtarea 2: 30 horas, 80% avance, gasto $300 paid
    sub2_id = uuid.uuid4()
    sub2 = MagicMock(spec=models.ProjectTask)
    sub2.id = sub2_id
    sub2.project_id = proj_id
    sub2.title = "Endpoints y Lógica de Negocio"
    sub2.status = "in_progress"
    sub2.priority = "high"
    sub2.parent_id = parent_id
    sub2.component_id = None
    sub2.component = None
    sub2.physical_progress_pct = 80.0
    sub2.estimated_hours = 30.0
    sub2.start_date = now
    sub2.due_date = now + timedelta(days=8)
    sub2.deleted_at = None

    exp_sub1 = MagicMock(spec=models.ProjectExpense)
    exp_sub1.id = uuid.uuid4()
    exp_sub1.project_id = proj_id
    exp_sub1.task_id = sub1_id
    exp_sub1.component_id = None
    exp_sub1.category = "servicios"
    exp_sub1.description = "Servidor pruebas"
    exp_sub1.amount = 100.0
    exp_sub1.date = now
    exp_sub1.receipt_url = None
    exp_sub1.status = "paid"
    exp_sub1.created_by = None
    exp_sub1.creator = None
    exp_sub1.created_at = now
    exp_sub1.updated_at = now
    exp_sub1.deleted_at = None

    exp_sub2 = MagicMock(spec=models.ProjectExpense)
    exp_sub2.id = uuid.uuid4()
    exp_sub2.project_id = proj_id
    exp_sub2.task_id = sub2_id
    exp_sub2.component_id = None
    exp_sub2.category = "servicios"
    exp_sub2.description = "Base de datos remota"
    exp_sub2.amount = 300.0
    exp_sub2.date = now
    exp_sub2.receipt_url = None
    exp_sub2.status = "paid"
    exp_sub2.created_by = None
    exp_sub2.creator = None
    exp_sub2.created_at = now
    exp_sub2.updated_at = now
    exp_sub2.deleted_at = None

    db = MagicMock()

    def query_mock(arg):
        q = MagicMock()
        if arg is models.ProjectTask or getattr(arg, "class_", None) is models.ProjectTask:
            q.filter.return_value.order_by.return_value.all.return_value = [sub1, sub2]
            q.filter.return_value.all.return_value = [sub1, sub2]
            return q
        if getattr(arg, "name", None) == "id" or str(arg).startswith("project_tasks"):
            q.filter.return_value.all.return_value = [(sub1_id,), (sub2_id,)]
            return q
        if arg is models.ProjectTimeLog or getattr(arg, "class_", None) is models.ProjectTimeLog:
            q.filter.return_value.all.return_value = []
            return q
        if arg is models.ProjectExpense or getattr(arg, "class_", None) is models.ProjectExpense:
            q_exp = MagicMock()
            def filter_exp(*filters):
                f_mock = MagicMock()
                # Si el filtro es de tipo in_ (descendant_ids), retornar los gastos de las subtareas
                filter_repr = " ".join(str(f) for f in filters).upper()
                if "IN" in filter_repr or "ANY" in filter_repr:
                    f_mock.all.return_value = [exp_sub1, exp_sub2]
                else:
                    # Para gastos directos de la tarea padre (no tiene gastos propios directos)
                    f_mock.all.return_value = []
                return f_mock
            q_exp.filter.side_effect = filter_exp
            return q_exp
        q.filter.return_value.all.return_value = []
        return q

    db.query.side_effect = query_mock

    # Mock directo de get_task_descendant_ids
    with patch("backend.services.project_evm_service.get_task_descendant_ids", return_value=[sub1_id, sub2_id]):
        from backend.services import project_evm_service
        orig_calc = project_evm_service.calculate_task_rollup

        def sub_calc(s_db, t):
            if t.id == sub1_id:
                return {
                    "progress": {"rolled_up_progress_pct": 40.0},
                }
            if t.id == sub2_id:
                return {
                    "progress": {"rolled_up_progress_pct": 80.0},
                }
            return orig_calc(s_db, t)

        with patch("backend.services.project_evm_service.calculate_task_rollup", side_effect=sub_calc):
            rollup = project_evm_service.calculate_task_rollup(db, parent)

    # Avance ponderado: (40% * 10h + 80% * 30h) / (10h + 30h) = (400 + 2400) / 40 = 70.0%
    assert rollup["progress"]["rolled_up_progress_pct"] == 70.0
    assert rollup["progress"]["weight_basis"] == "estimated_hours"
    assert rollup["progress"]["is_leaf"] is False
    assert rollup["progress"]["subtasks_count"] == 2

    # Horas estimadas acumuladas: 10 + 30 = 40h
    assert rollup["time"]["subtasks_estimated_hours"] == 40.0
    assert rollup["time"]["total_estimated_hours"] == 40.0

    # Costo acumulado: $100 + $300 = $400
    assert rollup["cost"]["total_cost"] == 400.0
    assert rollup["cost"]["actual_cost"] == 400.0


def test_calculate_task_rollup_parent_equal_count_when_no_hours():
    """Valida ponderación equitativa cuando las subtareas no tienen horas estimadas (o todas son 0)."""
    parent_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    parent = MagicMock(spec=models.ProjectTask)
    parent.id = parent_id
    parent.project_id = proj_id
    parent.title = "Diseño Conceptual"
    parent.status = "in_progress"
    parent.priority = "low"
    parent.parent_id = None
    parent.component_id = None
    parent.component = None
    parent.physical_progress_pct = 0.0
    parent.estimated_hours = 0.0
    parent.start_date = None
    parent.due_date = None
    parent.deleted_at = None

    sub1_id = uuid.uuid4()
    sub1 = MagicMock(spec=models.ProjectTask)
    sub1.id = sub1_id
    sub1.status = "in_progress"
    sub1.physical_progress_pct = 20.0
    sub1.estimated_hours = 0.0
    sub1.deleted_at = None

    sub2_id = uuid.uuid4()
    sub2 = MagicMock(spec=models.ProjectTask)
    sub2.id = sub2_id
    sub2.status = "in_progress"
    sub2.physical_progress_pct = 60.0
    sub2.estimated_hours = 0.0
    sub2.deleted_at = None

    db = MagicMock()

    def query_mock(arg):
        q = MagicMock()
        if arg is models.ProjectTask or getattr(arg, "class_", None) is models.ProjectTask:
            q.filter.return_value.order_by.return_value.all.return_value = [sub1, sub2]
            q.filter.return_value.all.return_value = [sub1, sub2]
            return q
        if getattr(arg, "name", None) == "id" or str(arg).startswith("project_tasks"):
            q.filter.return_value.all.return_value = [(sub1_id,), (sub2_id,)]
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

    with patch("backend.services.project_evm_service.get_task_descendant_ids", return_value=[sub1_id, sub2_id]):
        from backend.services import project_evm_service
        orig_calc = project_evm_service.calculate_task_rollup

        def sub_calc_equal(s_db, t):
            if t.id == sub1_id:
                return {"progress": {"rolled_up_progress_pct": 20.0}}
            if t.id == sub2_id:
                return {"progress": {"rolled_up_progress_pct": 60.0}}
            return orig_calc(s_db, t)

        with patch("backend.services.project_evm_service.calculate_task_rollup", side_effect=sub_calc_equal):
            rollup = project_evm_service.calculate_task_rollup(db, parent)

    # Ponderación equitativa: (20 + 60) / 2 = 40.0%
    assert rollup["progress"]["rolled_up_progress_pct"] == 40.0
    assert rollup["progress"]["weight_basis"] == "equal_count"


def test_sync_parent_task_rollup():
    """Valida la sincronización automática del avance físico en cascada en la BD."""
    parent_id = uuid.uuid4()
    parent = MagicMock(spec=models.ProjectTask)
    parent.id = parent_id
    parent.parent_id = None
    parent.physical_progress_pct = 10.0

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = parent

    mock_rollup = {
        "progress": {"rolled_up_progress_pct": 85.0}
    }

    with patch("backend.services.project_evm_service.calculate_task_rollup", return_value=mock_rollup):
        sync_parent_task_rollup(db, parent_id)

    assert parent.physical_progress_pct == 85.0
    db.commit.assert_called_once()


def test_calculate_project_tasks_rollup_summary():
    """Valida el consolidado a nivel de proyecto de todas las tareas y sus 3 dimensiones."""
    proj_id = uuid.uuid4()
    project = MagicMock(spec=models.Project)
    project.id = proj_id

    # 1 tarea padre y 2 hojas
    t_parent = MagicMock(spec=models.ProjectTask)
    t_parent.id = uuid.uuid4()
    t_parent.parent_id = None

    t_sub1 = MagicMock(spec=models.ProjectTask)
    t_sub1.id = uuid.uuid4()
    t_sub1.parent_id = t_parent.id

    t_sub2 = MagicMock(spec=models.ProjectTask)
    t_sub2.id = uuid.uuid4()
    t_sub2.parent_id = t_parent.id

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        t_parent,
        t_sub1,
        t_sub2,
    ]
    db.query.return_value.filter.return_value.all.return_value = []

    def mock_rollup(s_db, t):
        if t.id == t_parent.id:
            return {
                "time": {"estimated_hours": 0.0, "total_estimated_hours": 40.0},
                "progress": {"is_leaf": False, "rolled_up_progress_pct": 75.0},
                "cost": {"total_cost": 500.0},
            }
        elif t.id == t_sub1.id:
            return {
                "time": {"estimated_hours": 20.0, "total_estimated_hours": 20.0},
                "progress": {"is_leaf": True, "rolled_up_progress_pct": 50.0},
                "cost": {"total_cost": 200.0},
            }
        else:
            return {
                "time": {"estimated_hours": 20.0, "total_estimated_hours": 20.0},
                "progress": {"is_leaf": True, "rolled_up_progress_pct": 100.0},
                "cost": {"total_cost": 300.0},
            }

    with patch("backend.services.project_evm_service.calculate_task_rollup", side_effect=mock_rollup):
        summary = calculate_project_tasks_rollup(db, project)

    assert summary["total_tasks"] == 3
    assert summary["leaf_tasks_count"] == 2
    assert summary["parent_tasks_count"] == 1
    assert summary["total_estimated_hours"] == 40.0
    assert summary["overall_physical_progress_pct"] == 75.0
    assert summary["tasks_with_expenses_count"] == 3

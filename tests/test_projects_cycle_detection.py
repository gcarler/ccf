"""Tests unitarios para la detección de dependencias circulares (DFS)
y validación de fechas de tareas en límites de fase.

Cumple los criterios de aceptación de TKT-PROJECTS-CYCLE-DETECTION-01:
1. Algoritmo de detección de ciclos en backend/api/projects.py y crud
2. Rechazo HTTP 422 ante dependencias circulares con mensaje claro
3. Validación de fechas de tarea dentro de los límites de la fase
4. Tests unitarios en pytest con cobertura de grafos acíclicos y cíclicos
5. Cero regresiones en Gantt
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.crud.projects import (
    CircularDependencyError,
    TaskDateOutOfBoundsError,
    create_project_task,
    create_task_dependency,
    detect_cycle_in_dependencies,
    set_project_phases,
    update_project_task,
    validate_task_dates_within_phase,
)
from backend.models_projects import Project, ProjectPhase, ProjectTask, ProjectTaskDependency
from backend.schemas.projects import (
    ProjectPhaseInput,
    ProjectTaskCreate,
    ProjectTaskDependencyCreate,
    ProjectTaskUpdate,
)


# ── 1. Pure Algorithm Tests: detect_cycle_in_dependencies (DFS) ───────────────


def test_dfs_empty_and_single_edge_acyclic():
    """Grafo vacío o con una sola arista es acíclico."""
    has_cycle, path = detect_cycle_in_dependencies([])
    assert not has_cycle
    assert path == []

    has_cycle, path = detect_cycle_in_dependencies([("A", "B")])
    assert not has_cycle
    assert path == []


def test_dfs_detects_self_loop():
    """Detecta bucle directo hacia sí mismo (A -> A)."""
    has_cycle, path = detect_cycle_in_dependencies([], new_edge=("A", "A"))
    assert has_cycle
    assert "A" in path


def test_dfs_detects_two_node_cycle():
    """Detecta ciclo de 2 nodos (A -> B y B -> A)."""
    edges = [("A", "B")]
    has_cycle, path = detect_cycle_in_dependencies(edges, new_edge=("B", "A"))
    assert has_cycle
    assert len(path) >= 2


def test_dfs_detects_multi_node_indirect_cycle():
    """Detecta ciclo indirecto de 3 o más nodos (A -> B -> C -> A)."""
    edges = [("A", "B"), ("B", "C")]
    has_cycle, path = detect_cycle_in_dependencies(edges, new_edge=("C", "A"))
    assert has_cycle
    assert "A" in path and "B" in path and "C" in path


def test_dfs_complex_diamond_dag_is_acyclic():
    """Grafo diamante (A -> B, A -> C, B -> D, C -> D) es acíclico."""
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    has_cycle, path = detect_cycle_in_dependencies(edges)
    assert not has_cycle
    assert path == []

    # Añadir un nodo sucesor a D tampoco crea ciclo
    has_cycle, path = detect_cycle_in_dependencies(edges, new_edge=("D", "E"))
    assert not has_cycle
    assert path == []


def test_dfs_diamond_with_back_edge_detects_cycle():
    """Añadir una arista de retorno en un diamante crea ciclo (D -> A)."""
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    has_cycle, path = detect_cycle_in_dependencies(edges, new_edge=("D", "A"))
    assert has_cycle


def test_dfs_disconnected_components_cycle_detection():
    """Detecta ciclo que une dos componentes antes independientes."""
    edges = [("A", "B"), ("C", "D"), ("B", "C")]
    has_cycle, _ = detect_cycle_in_dependencies(edges, new_edge=("D", "A"))
    assert has_cycle


# ── 2. CRUD Dependency Integration Tests ──────────────────────────────────────


def test_crud_create_dependency_rejects_self_dependency(db_session, test_project):
    """create_task_dependency rechaza una tarea dependiendo de sí misma con CircularDependencyError."""
    t1 = ProjectTask(
        project_id=test_project.id,
        title="Tarea 1",
        status="todo",
    )
    db_session.add(t1)
    db_session.commit()

    payload = ProjectTaskDependencyCreate(
        predecessor_id=t1.id,
        successor_id=t1.id,
        dependency_type="FS",
    )

    with pytest.raises(CircularDependencyError) as exc_info:
        create_task_dependency(db_session, test_project.id, payload)
    assert "Dependencia circular detectada" in str(exc_info.value)


def test_crud_create_dependency_rejects_circular_cycle(db_session, test_project):
    """create_task_dependency rechaza ciclo A -> B -> C -> A."""
    t1 = ProjectTask(project_id=test_project.id, title="Tarea 1", status="todo")
    t2 = ProjectTask(project_id=test_project.id, title="Tarea 2", status="todo")
    t3 = ProjectTask(project_id=test_project.id, title="Tarea 3", status="todo")
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    # A -> B
    create_task_dependency(
        db_session,
        test_project.id,
        ProjectTaskDependencyCreate(predecessor_id=t1.id, successor_id=t2.id),
    )
    # B -> C
    create_task_dependency(
        db_session,
        test_project.id,
        ProjectTaskDependencyCreate(predecessor_id=t2.id, successor_id=t3.id),
    )

    # Intento de C -> A debe ser rechazado
    with pytest.raises(CircularDependencyError) as exc_info:
        create_task_dependency(
            db_session,
            test_project.id,
            ProjectTaskDependencyCreate(predecessor_id=t3.id, successor_id=t1.id),
        )
    assert "Dependencia circular detectada" in str(exc_info.value)
    assert "Gantt" in str(exc_info.value)


# ── 3. Phase Date Range & Task Date Validation ────────────────────────────────


def test_task_dates_within_phase_bounds_success(db_session, test_project):
    """Una tarea dentro del rango estricto de la fase se crea correctamente."""
    base_time = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    phase_start = base_time
    phase_end = base_time + timedelta(days=30)

    phases = set_project_phases(
        db_session,
        test_project.id,
        [
            {
                "name": "Fase 1",
                "slug": "fase-1",
                "color": "#3b82f6",
                "start_date": phase_start,
                "end_date": phase_end,
            }
        ],
    )
    assert phases[0].start_date == phase_start
    assert phases[0].end_date == phase_end

    # Tarea con fechas dentro de la fase
    task_in = ProjectTaskCreate(
        project_id=test_project.id,
        title="Tarea en rango",
        status="fase-1",
        start_date=phase_start + timedelta(days=2),
        due_date=phase_start + timedelta(days=10),
    )
    created = create_project_task(db_session, task_in)
    assert created.id is not None


def test_task_start_date_before_phase_start_rejected(db_session, test_project):
    """Una tarea cuya fecha de inicio es anterior a la fase se rechaza con TaskDateOutOfBoundsError."""
    base_time = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    set_project_phases(
        db_session,
        test_project.id,
        [
            {
                "name": "Fase 1",
                "slug": "fase-1",
                "color": "#3b82f6",
                "start_date": base_time,
                "end_date": base_time + timedelta(days=30),
            }
        ],
    )

    task_in = ProjectTaskCreate(
        project_id=test_project.id,
        title="Tarea antes de fase",
        status="fase-1",
        start_date=base_time - timedelta(days=2),  # 2 días antes de la fase
        due_date=base_time + timedelta(days=5),
    )

    with pytest.raises(TaskDateOutOfBoundsError) as exc_info:
        create_project_task(db_session, task_in)
    assert "no puede ser anterior al inicio de la fase" in str(exc_info.value)


def test_task_due_date_after_phase_end_rejected(db_session, test_project):
    """Una tarea cuya fecha límite excede el fin de la fase se rechaza con TaskDateOutOfBoundsError."""
    base_time = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    phase_end = base_time + timedelta(days=15)
    set_project_phases(
        db_session,
        test_project.id,
        [
            {
                "name": "Fase 1",
                "slug": "fase-1",
                "color": "#3b82f6",
                "start_date": base_time,
                "end_date": phase_end,
            }
        ],
    )

    task_in = ProjectTaskCreate(
        project_id=test_project.id,
        title="Tarea después de fase",
        status="fase-1",
        start_date=base_time + timedelta(days=2),
        due_date=phase_end + timedelta(days=1),  # Excede fin de fase
    )

    with pytest.raises(TaskDateOutOfBoundsError) as exc_info:
        create_project_task(db_session, task_in)
    assert "no puede ser posterior al fin de la fase" in str(exc_info.value)


def test_task_start_after_due_date_rejected():
    """Pydantic rechaza start_date posterior a due_date."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        ProjectTaskCreate(
            title="Tarea invertida",
            start_date=now + timedelta(days=5),
            due_date=now,
        )


def test_update_task_validates_phase_bounds(db_session, test_project):
    """Actualizar una tarea con fechas fuera del rango de la fase se rechaza."""
    base_time = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    phase_end = base_time + timedelta(days=20)
    set_project_phases(
        db_session,
        test_project.id,
        [
            {
                "name": "Fase Sprint",
                "slug": "sprint",
                "color": "#3b82f6",
                "start_date": base_time,
                "end_date": phase_end,
            }
        ],
    )

    task = create_project_task(
        db_session,
        ProjectTaskCreate(
            project_id=test_project.id,
            title="Tarea Sprint",
            status="sprint",
            start_date=base_time + timedelta(days=1),
            due_date=base_time + timedelta(days=5),
        ),
    )

    # Intento de mover due_date después del fin de fase
    with pytest.raises(TaskDateOutOfBoundsError):
        update_project_task(
            db_session,
            task.id,
            ProjectTaskUpdate(due_date=phase_end + timedelta(days=5)),
        )

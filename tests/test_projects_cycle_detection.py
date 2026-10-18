"""Tests unitarios para la detección de dependencias circulares (DFS)
y validación de fechas de tareas en límites de fase.

Cumple los criterios de aceptación de TKT-PROJECTS-CYCLE-DETECTION-01:
1. Algoritmo de detección de ciclos en backend/api/projects.py y crud
2. Rechazo HTTP 422 ante dependencias circulares con mensaje claro
3. Validación de fechas de tarea dentro de los límites de la fase
4. Tests unitarios en pytest con cobertura de grafos acíclicos y cíclicos
5. Cero regresiones en Gantt
"""

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
)
from backend.models_projects import ProjectTask
from backend.schemas.projects import (
    ProjectTaskCreate,
    ProjectTaskDependencyCreate,
    ProjectTaskUpdate,
)
from tests.factories_projects import create_project_factory


@pytest.fixture
def test_project(db_session):
    return create_project_factory(db_session)


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
    p_start = phases[0].start_date if phases[0].start_date.tzinfo else phases[0].start_date.replace(tzinfo=timezone.utc)
    p_end = phases[0].end_date if phases[0].end_date.tzinfo else phases[0].end_date.replace(tzinfo=timezone.utc)
    assert p_start == phase_start
    assert p_end == phase_end

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


# ── PDM Network Topology Analyzer (PMI 6.3) ───────────────────────────────────


def test_pdm_topology_empty_graph():
    """Grafo vacío: sin nodos ni aristas, clasificación 'linear_or_empty'."""
    from backend.crud.projects import analyze_pdm_network_topology

    result = analyze_pdm_network_topology([])
    assert result == {
        "total_nodes": 0,
        "total_edges": 0,
        "has_cycle": False,
        "max_in_degree": 0,
        "max_out_degree": 0,
        "merge_nodes_count": 0,
        "burst_nodes_count": 0,
        "network_complexity_level": "linear_or_empty",
    }
    assert result["merge_nodes_count"] == 0
    assert result["burst_nodes_count"] == 0


def test_pdm_topology_linear_chain():
    """Cadena lineal A -> B -> C: sin convergencia ni divergencia."""
    from backend.crud.projects import analyze_pdm_network_topology

    result = analyze_pdm_network_topology([("A", "B"), ("B", "C")])
    assert result["total_nodes"] == 3
    assert result["total_edges"] == 2
    assert result["has_cycle"] is False
    assert result["max_in_degree"] == 1
    assert result["max_out_degree"] == 1
    assert result["merge_nodes_count"] == 0
    assert result["burst_nodes_count"] == 0
    assert result["network_complexity_level"] == "linear_or_empty"


def test_pdm_topology_diamond_dag_moderate():
    """Diamante DAG: 1 punto de convergencia (D) y 1 de divergencia (A) → 'moderate'."""
    from backend.crud.projects import analyze_pdm_network_topology

    result = analyze_pdm_network_topology([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])
    assert result["total_nodes"] == 4
    assert result["total_edges"] == 4
    assert result["has_cycle"] is False
    assert result["max_in_degree"] == 2
    assert result["max_out_degree"] == 2
    assert result["merge_nodes_count"] == 1
    assert result["burst_nodes_count"] == 1
    assert result["network_complexity_level"] == "moderate"


def test_pdm_topology_high_convergence():
    """Convergencia alta: 3 predecesores hacia D → max_in_degree 3, 'high_convergence'."""
    from backend.crud.projects import analyze_pdm_network_topology

    result = analyze_pdm_network_topology([("A", "D"), ("B", "D"), ("C", "D")])
    assert result["total_nodes"] == 4
    assert result["total_edges"] == 3
    assert result["has_cycle"] is False
    assert result["max_in_degree"] == 3
    assert result["max_out_degree"] == 1
    assert result["merge_nodes_count"] == 1
    assert result["network_complexity_level"] == "high_convergence"


def test_pdm_topology_cyclic_graph_invalid():
    """Ciclo A -> B -> A: clasificación 'cyclic_invalid' con has_cycle True."""
    from backend.crud.projects import analyze_pdm_network_topology

    result = analyze_pdm_network_topology([("A", "B"), ("B", "A")])
    assert result["has_cycle"] is True
    assert result["network_complexity_level"] == "cyclic_invalid"
    assert result["total_nodes"] == 2
    assert result["total_edges"] == 2


def test_pdm_topology_normalizes_uuid_like_nodes():
    """Nodos no string (UUIDs) se normalizan a str; aristas duplicadas suman grado."""
    import uuid as _uuid

    from backend.crud.projects import analyze_pdm_network_topology

    a, b = _uuid.uuid4(), _uuid.uuid4()
    result = analyze_pdm_network_topology([(a, b), (a, b)])
    assert result["total_nodes"] == 2
    # Duplicada: b recibe 2 entradas → 1 punto de convergencia → 'moderate'
    assert result["max_in_degree"] == 2
    assert result["max_out_degree"] == 2
    assert result["merge_nodes_count"] == 1
    assert result["burst_nodes_count"] == 1
    assert result["total_edges"] == 2
    assert result["network_complexity_level"] == "moderate"

    # Sin duplicar, la misma topología con UUID es lineal
    a2, b2 = _uuid.uuid4(), _uuid.uuid4()
    result_linear = analyze_pdm_network_topology([(a2, b2)])
    assert result_linear["total_nodes"] == 2
    assert result_linear["max_in_degree"] == 1
    assert result_linear["network_complexity_level"] == "linear_or_empty"


# ── classify_cpm_float_risk_profile (PMBOK §6.5.2.2, pure helper) ─────────


def _cpm_rows(idx: int):
    """Genera filas CPM: mayoría críticas + near-critical + con buffer."""
    rows = [
        {"is_critical": True, "total_float": 0},
        {"is_critical": False, "total_float": 0},   # float 0 → crítica por float
        {"is_critical": True, "total_float": 5},    # is_critical manda
        {"is_critical": False, "total_float": 1},   # near-critical (<= 2)
        {"is_critical": False, "total_float": 2},   # near-critical (== threshold)
        {"is_critical": False, "total_float": 9},   # con holgura (buffered)
        {"is_critical": False, "total_float": 15},  # con holgura (buffered)
    ]
    return rows[:idx]


def test_cpm_float_risk_empty_schedule():
    """None, {} y tasks vacío → 'empty_schedule' con densidad 0.0."""
    from backend.crud.projects import classify_cpm_float_risk_profile

    for metrics in (None, {}, {"tasks": []}, {"tasks": {}}):
        result = classify_cpm_float_risk_profile(metrics)
        assert result == {
            "total_scheduled_tasks": 0,
            "critical_tasks_count": 0,
            "near_critical_tasks_count": 0,
            "buffered_tasks_count": 0,
            "critical_density_pct": 0.0,
            "schedule_rigidity_status": "empty_schedule",
        }


def test_cpm_float_risk_hyper_rigid_dict_nodes():
    """≥ 75% críticas+near sobre dict {task_id: task} → 'hyper_rigid'."""
    from backend.crud.projects import classify_cpm_float_risk_profile

    rows = [
        {"is_critical": True, "total_float": 0},
        {"is_critical": False, "total_float": 0},   # float 0 → crítica
        {"is_critical": True, "total_float": 5},    # is_critical manda sobre float
        {"is_critical": False, "total_float": 1},   # near-critical
        {"is_critical": False, "total_float": 2},   # near-critical (== threshold)
        {"is_critical": False, "total_float": 2},   # near-critical (== threshold)
        {"is_critical": False, "total_float": 7},   # buffered
        {"is_critical": False, "total_float": 9},   # buffered
    ]
    # 3 críticas + 3 near = 6/8 = 0.75 >= 0.75
    metrics = {"tasks": {f"t{i}": row for i, row in enumerate(rows)}}
    result = classify_cpm_float_risk_profile(metrics)

    assert result["total_scheduled_tasks"] == 8
    assert result["critical_tasks_count"] == 3
    assert result["near_critical_tasks_count"] == 3
    assert result["buffered_tasks_count"] == 2
    assert result["critical_density_pct"] == 37.5
    assert result["schedule_rigidity_status"] == "hyper_rigid"


def test_cpm_float_risk_moderate_float_list_tasks():
    """Densidad crítica <= 50% sin ser hyper_rigid → 'moderate_float' (lista)."""
    from backend.crud.projects import classify_cpm_float_risk_profile

    rows = [
        {"is_critical": True, "total_float": 0},
        {"is_critical": False, "total_float": 1},   # near-critical
        {"is_critical": False, "total_float": 7},   # buffered
        {"is_critical": False, "total_float": 8},   # buffered
        {"is_critical": False, "total_float": 9},   # buffered
        {"is_critical": False, "total_float": None},  # float nulo → crítica
    ]
    result = classify_cpm_float_risk_profile({"tasks": rows})

    assert result["total_scheduled_tasks"] == 6
    # float None cuenta como 0 → crítica (2 críticas = 33.33% <= 50)
    assert result["critical_tasks_count"] == 2
    assert result["near_critical_tasks_count"] == 1
    assert result["buffered_tasks_count"] == 3
    assert result["critical_density_pct"] == 33.33
    assert result["schedule_rigidity_status"] == "moderate_float"


def test_cpm_float_risk_tight_schedule():
    """Densidad crítica > 50% (pero < 75% de críticas+near) → 'tight_schedule'."""
    from backend.crud.projects import classify_cpm_float_risk_profile

    rows = [
        {"is_critical": True, "total_float": 0},
        {"is_critical": True, "total_float": 3},    # 2/4 críticas = 50%... usar 5 filas
        {"is_critical": True, "total_float": 0},
        {"is_critical": False, "total_float": 4},   # holgura > threshold
        {"is_critical": False, "total_float": 2},   # near-critical
    ]
    # 3 críticas de 5 = 60% > 50; críticas+near = 4/5 = 0.8 → hyper_rigid. Ajustar:
    rows[2] = {"is_critical": False, "total_float": 6}  # ahora 2 críticas de 5 = 40%
    # críticas+near = 3/5 = 0.6 < 0.75; densidad 40% <= 50 → moderate_float
    result_half = classify_cpm_float_risk_profile({"tasks": rows})
    assert result_half["schedule_rigidity_status"] == "moderate_float"

    # Para 'tight_schedule': densidad 60% con críticas+near = 3/5 (60%) < 75%
    tight_rows = [
        {"is_critical": True, "total_float": 0},
        {"is_critical": True, "total_float": 1},
        {"is_critical": True, "total_float": 2},    # 3 críticas de 5 = 60%
        {"is_critical": False, "total_float": 7},   # buffered
        {"is_critical": False, "total_float": 9},   # buffered
    ]
    result = classify_cpm_float_risk_profile({"tasks": tight_rows}, near_critical_threshold_days=4)
    assert result["critical_tasks_count"] == 3
    assert result["near_critical_tasks_count"] == 0  # floats 7 y 9 > threshold 4
    assert result["buffered_tasks_count"] == 2
    assert result["critical_density_pct"] == 60.0
    assert result["schedule_rigidity_status"] == "tight_schedule"


# ── evaluate_dependency_network_bottlenecks (PMBOK §6.3, pure helper) ────


def test_dependency_bottlenecks_linear_chain():
    """Cadena lineal A->B->C con threshold=3 → 'linear_chain' sin hubs."""
    from backend.crud.projects import evaluate_dependency_network_bottlenecks

    result = evaluate_dependency_network_bottlenecks(
        [("A", "B"), ("B", "C")], high_degree_threshold=3
    )

    assert result == {
        "total_nodes": 3,
        "total_unique_edges": 2,
        "max_in_degree": 1,
        "max_out_degree": 1,
        "merge_point_nodes": [],
        "burst_point_nodes": [],
        "bottleneck_nodes": [],
        "network_complexity_status": "linear_chain",
    }


def test_dependency_bottlenecks_merge_and_burst_nodes():
    """Diamante A->B, A->C, B->D, C->D: merge en D y burst en A → 'convergent_divergent'."""
    from backend.crud.projects import evaluate_dependency_network_bottlenecks

    result = evaluate_dependency_network_bottlenecks(
        [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    )

    assert result["total_nodes"] == 4
    assert result["total_unique_edges"] == 4
    assert result["max_in_degree"] == 2
    assert result["max_out_degree"] == 2
    assert result["merge_point_nodes"] == ["D"]
    assert result["burst_point_nodes"] == ["A"]
    # Con threshold 3 (default), in+out de A (2) y D (2) no alcanzan → sin hubs
    assert result["bottleneck_nodes"] == []
    assert result["network_complexity_status"] == "convergent_divergent"

    # Con threshold 2, los 4 nodos (B y C: in 1 + out 1 = 2) son hubs
    tight = evaluate_dependency_network_bottlenecks(
        [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")], high_degree_threshold=2
    )
    assert tight["bottleneck_nodes"] == ["A", "B", "C", "D"]
    assert tight["network_complexity_status"] == "high_congestion_hubs"


def test_dependency_bottlenecks_dedup_and_selfloops():
    """Aristas duplicadas se colapsan, self-loops y extremos vacíos se ignoran."""
    from backend.crud.projects import evaluate_dependency_network_bottlenecks

    edges = [
        ("A", "B"),   # válida
        (" A ", "B"),   # duplicada tras strip (colapsa)
        ("A", "B "),   # duplicada (colapsa)
        ("A", "A"),   # self-loop ignorado
        ("", "B"),    # u vacío ignorado
        ("A", ""),    # v vacío ignorado
        ("A", "C"),   # segunda válida → A acumula out=2
        ("X", "C"),   # X otra entrada a C → merge
        ("Y", "  "),  # v vacío tras strip ignorado
    ]
    result = evaluate_dependency_network_bottlenecks(edges, high_degree_threshold=3)

    assert result["total_nodes"] == 4  # A, B, C, X
    assert result["total_unique_edges"] == 3  # (A,B), (A,C), (X,C)
    assert result["max_in_degree"] == 2  # C recibe de A y X
    assert result["max_out_degree"] == 2  # A emite a B y C
    assert result["merge_point_nodes"] == ["C"]
    assert result["burst_point_nodes"] == ["A"]
    # A: in 0 + out 2 = 2 < 3; C: in 2 + out 0 = 2 < 3 → sin hubs
    assert result["bottleneck_nodes"] == []
    assert result["network_complexity_status"] == "convergent_divergent"

    # Threshold 2: A y C superan in+out >= 2 → hubs
    tight = evaluate_dependency_network_bottlenecks(edges, high_degree_threshold=2)
    assert tight["bottleneck_nodes"] == ["A", "C"]
    assert tight["network_complexity_status"] == "high_congestion_hubs"


def test_dependency_bottlenecks_none_and_empty_graph():
    """None, [] y solo aristas inválidas → 'disconnected' con vacíos en 0."""
    from backend.crud.projects import evaluate_dependency_network_bottlenecks

    for edges_arg in (None, [], [("A", "A")], [("", "")]):
        result = evaluate_dependency_network_bottlenecks(edges_arg)
        assert result == {
            "total_nodes": 0,
            "total_unique_edges": 0,
            "max_in_degree": 0,
            "max_out_degree": 0,
            "merge_point_nodes": [],
            "burst_point_nodes": [],
            "bottleneck_nodes": [],
            "network_complexity_status": "disconnected",
        }

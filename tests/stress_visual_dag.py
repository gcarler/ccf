"""
Empirical stress-test suite for Visual Workflow Builder DAG cycle detection.
Adversarial tests on backend DAG algorithms:
- Direct self-loops
- Simple 2-node and 3-node cycles
- Disconnected graphs with isolated cycles
- Multi-branch complex cycles
- Diamond DAGs (false positive check)
- Multi-layer dense DAGs (scalability)
- 1,000-node linear and branching DAGs (performance < 50ms)
- Malformed inputs & payload edge cases
"""

import time
import pytest
from backend.api.crm.pipelines import check_for_cycles_dfs, get_graph_from_payload_or_db


def test_dag_empty_graph():
    has_cycle, cycles = check_for_cycles_dfs([], [])
    assert not has_cycle
    assert cycles == []


def test_dag_single_node_no_edges():
    has_cycle, cycles = check_for_cycles_dfs(["node1"], [])
    assert not has_cycle
    assert cycles == []


def test_dag_self_loop():
    nodes = ["node1"]
    edges = [{"source": "node1", "target": "node1"}]
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    assert has_cycle
    assert len(cycles) >= 1
    assert cycles[0] == ["node1", "node1"]


def test_dag_simple_2node_cycle():
    nodes = ["A", "B"]
    edges = [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "A"},
    ]
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    assert has_cycle
    assert any("A" in c and "B" in c for c in cycles)


def test_dag_3node_cycle():
    nodes = ["A", "B", "C"]
    edges = [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "A"},
    ]
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    assert has_cycle
    assert len(cycles) >= 1


def test_dag_disconnected_components_with_isolated_cycle():
    """
    Component 1 (acyclic): A1 -> A2 -> A3
    Component 2 (cyclic): C1 -> C2 -> C3 -> C1
    Component 3 (isolated): I1, I2
    """
    nodes = ["A1", "A2", "A3", "C1", "C2", "C3", "I1", "I2"]
    edges = [
        {"source": "A1", "target": "A2"},
        {"source": "A2", "target": "A3"},
        {"source": "C1", "target": "C2"},
        {"source": "C2", "target": "C3"},
        {"source": "C3", "target": "C1"},
    ]
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    assert has_cycle
    # Verify the cycle found involves C1/C2/C3 and NOT A1/A2/A3
    for cycle in cycles:
        assert any(x in ["C1", "C2", "C3"] for x in cycle)
        assert not any(x in ["A1", "A2", "A3", "I1", "I2"] for x in cycle)


def test_dag_diamond_is_acyclic():
    """
    Diamond graph (A -> B -> D, A -> C -> D) must NOT be detected as a cycle.
    """
    nodes = ["A", "B", "C", "D"]
    edges = [
        {"source": "A", "target": "B"},
        {"source": "A", "target": "C"},
        {"source": "B", "target": "D"},
        {"source": "C", "target": "D"},
    ]
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    assert not has_cycle
    assert cycles == []


def test_dag_multibranch_cycle():
    """
    A -> B -> C -> F
    A -> D -> E -> F
    F -> B (creates cycle through B -> C -> F -> B)
    """
    nodes = ["A", "B", "C", "D", "E", "F"]
    edges = [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "F"},
        {"source": "A", "target": "D"},
        {"source": "D", "target": "E"},
        {"source": "E", "target": "F"},
        {"source": "F", "target": "B"},  # back-edge
    ]
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    assert has_cycle
    assert len(cycles) >= 1


def test_dag_large_scale_performance():
    """
    Stress test 500 nodes and 1,500 edges forward-directed.
    Must complete in < 50ms.
    """
    N = 500
    nodes = [f"node_{i}" for i in range(N)]
    edges = []
    for i in range(N - 1):
        edges.append({"source": f"node_{i}", "target": f"node_{i+1}"})
        if i + 5 < N:
            edges.append({"source": f"node_{i}", "target": f"node_{i+5}"})
        if i + 10 < N:
            edges.append({"source": f"node_{i}", "target": f"node_{i+10}"})

    start = time.perf_counter()
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    duration_ms = (time.perf_counter() - start) * 1000

    assert not has_cycle
    assert cycles == []
    assert duration_ms < 50, f"Performance exceeded limit: {duration_ms:.2f}ms"


def test_dag_large_scale_cycle_detection():
    """
    Stress test 500 nodes with a deep back-edge from node_499 to node_50.
    Must detect cycle in < 50ms.
    """
    N = 500
    nodes = [f"node_{i}" for i in range(N)]
    edges = [{"source": f"node_{i}", "target": f"node_{i+1}"} for i in range(N - 1)]
    edges.append({"source": "node_499", "target": "node_50"})  # deep cycle

    start = time.perf_counter()
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    duration_ms = (time.perf_counter() - start) * 1000

    assert has_cycle
    assert len(cycles) >= 1
    assert duration_ms < 50, f"Cycle detection exceeded limit: {duration_ms:.2f}ms"


def test_get_graph_from_payload_edge_cases():
    """
    Test get_graph_from_payload_or_db edge cases (empty IDs, string vs dict, etc.)
    """
    # 1. Valid dict nodes and edges
    payload = {
        "flow_data": {
            "nodes": [{"id": "n1"}, {"id": "n2"}],
            "edges": [{"source": "n1", "target": "n2"}],
        }
    }
    nodes, edges = get_graph_from_payload_or_db(payload, None)
    assert nodes == ["n1", "n2"]
    assert edges == [{"source": "n1", "target": "n2"}]

    # 2. String nodes
    payload = {
        "flow_data": {
            "nodes": ["n1", "n2"],
            "edges": [{"source": "n1", "target": "n2"}],
        }
    }
    nodes, edges = get_graph_from_payload_or_db(payload, None)
    assert nodes == ["n1", "n2"]

    # 3. Missing/malformed node ID
    with pytest.raises(ValueError, match="Node ID is missing"):
        get_graph_from_payload_or_db({"flow_data": {"nodes": [{"id": ""}]}}, None)

    # 4. Missing/malformed edge source/target
    with pytest.raises(ValueError, match="Source or target in edge is missing"):
        get_graph_from_payload_or_db({"flow_data": {"nodes": [{"id": "n1"}], "edges": [{"source": "n1", "target": ""}]}}, None)

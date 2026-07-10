import pytest
from backend.api.crm.pipelines import check_for_cycles_dfs
from backend.models_crm import validate_three_node_path

def test_check_for_cycles_dfs_direct():
    # 1. Empty graph
    has_cycle, cycles = check_for_cycles_dfs([], [])
    assert not has_cycle
    assert cycles == []

    # 2. Single node, no edges
    has_cycle, cycles = check_for_cycles_dfs(["A"], [])
    assert not has_cycle
    assert cycles == []

    # 3. Self-referencing node (self-loop)
    has_cycle, cycles = check_for_cycles_dfs(["A"], [{"source": "A", "target": "A"}])
    assert has_cycle
    assert ["A", "A"] in cycles

    # 4. Simple cycle
    has_cycle, cycles = check_for_cycles_dfs(["A", "B"], [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "A"}
    ])
    assert has_cycle
    assert ["A", "B", "A"] in cycles or ["B", "A", "B"] in cycles

    # 5. Simple path (no cycle)
    has_cycle, cycles = check_for_cycles_dfs(["A", "B", "C"], [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"}
    ])
    assert not has_cycle
    assert cycles == []

    # 6. Branching and merging (DAG, no cycle)
    has_cycle, cycles = check_for_cycles_dfs(["A", "B", "C", "D"], [
        {"source": "A", "target": "B"},
        {"source": "A", "target": "C"},
        {"source": "B", "target": "D"},
        {"source": "C", "target": "D"}
    ])
    assert not has_cycle
    assert cycles == []

    # 7. Complex cycle (inner loop)
    # A -> B -> C -> D -> B
    has_cycle, cycles = check_for_cycles_dfs(["A", "B", "C", "D"], [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "D"},
        {"source": "D", "target": "B"}
    ])
    assert has_cycle
    assert len(cycles) > 0
    # The cycle path should contain B, C, D
    found_bcd = False
    for c in cycles:
        if "B" in c and "C" in c and "D" in c:
            found_bcd = True
    assert found_bcd

    # 8. Multiple cycles
    # A -> B -> A and C -> D -> C
    has_cycle, cycles = check_for_cycles_dfs(["A", "B", "C", "D"], [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "A"},
        {"source": "C", "target": "D"},
        {"source": "D", "target": "C"}
    ])
    assert has_cycle
    assert len(cycles) >= 2

    # 9. Disconnected components (one clean path, one with cycle)
    # Component 1: A -> B -> C
    # Component 2: D -> E -> D
    has_cycle, cycles = check_for_cycles_dfs(["A", "B", "C", "D", "E"], [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "D", "target": "E"},
        {"source": "E", "target": "D"}
    ])
    assert has_cycle
    assert len(cycles) == 1
    assert ["D", "E", "D"] in cycles or ["E", "D", "E"] in cycles

    # 10. Deep/long cycle
    # A -> B -> C -> D -> E -> F -> G -> A
    nodes = ["A", "B", "C", "D", "E", "F", "G"]
    edges = [{"source": nodes[i], "target": nodes[i+1]} for i in range(len(nodes)-1)] + [{"source": "G", "target": "A"}]
    has_cycle, cycles = check_for_cycles_dfs(nodes, edges)
    assert has_cycle
    assert len(cycles) > 0


def test_validate_three_node_path_direct():
    assert validate_three_node_path(None) is False
    assert validate_three_node_path([]) is False
    assert validate_three_node_path(["n1"]) is False
    assert validate_three_node_path(["n1", "n2"]) is False
    assert validate_three_node_path(["n1", "n2", "n3"]) is True
    assert validate_three_node_path(["n1", "n2", "n3", "n4"]) is True


def test_validate_path_api_scenarios(client):
    # Less than 3 nodes
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [{"source": "n1", "target": "n2"}]
    }
    response = client.post("/api/crm/automations/flows/validate-path", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False

    # Valid linear 3 nodes path
    payload = {
        "nodes": ["n1", "n2", "n3"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"}
        ]
    }
    response = client.post("/api/crm/automations/flows/validate-path", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["max_path_length"] == 3

    # Complex DAG with branching paths:
    # n1 -> n2 -> n4 -> n5 (len 4)
    # n1 -> n3 -> n5 (len 3)
    # Expected max path length: 4
    payload = {
        "nodes": ["n1", "n2", "n3", "n4", "n5"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n1", "target": "n3"},
            {"source": "n2", "target": "n4"},
            {"source": "n4", "target": "n5"},
            {"source": "n3", "target": "n5"}
        ]
    }
    response = client.post("/api/crm/automations/flows/validate-path", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["max_path_length"] == 4


def test_validate_node_api_scenarios(client):
    # Normal node without self-reference
    payload = {
        "nodes": ["n1", "n2"],
        "node_id": "n1",
        "edges": [{"source": "n1", "target": "n2"}]
    }
    response = client.post("/api/crm/automations/flows/validate-node", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True

    # Node with self-reference
    payload = {
        "nodes": ["n1"],
        "node_id": "n1",
        "edges": [{"source": "n1", "target": "n1"}]
    }
    response = client.post("/api/crm/automations/flows/validate-node", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False

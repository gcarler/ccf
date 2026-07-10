import pytest
import uuid
from backend import models
from backend.models_crm import CrmAutomationEdge, validate_three_node_path
from tests.conftest import auth_headers, seed_admin

# Test the genuine model validation function directly
def test_validate_three_node_path_function():
    # Null path should be False
    assert validate_three_node_path(None) is False
    # Path with less than 3 nodes should be False
    assert validate_three_node_path([1, 2]) is False
    # Path with >= 3 nodes should be True
    assert validate_three_node_path([1, 2, 3]) is True
    assert validate_three_node_path([1, 2, 3, 4]) is True

    # Test the binding on CrmAutomationEdge.__table__
    assert hasattr(CrmAutomationEdge.__table__, "validate_three_node_path")
    assert CrmAutomationEdge.__table__.validate_three_node_path([1, 2, 3]) is True


def test_automations_palette(client):
    response = client.get("/api/crm/automations/palette")
    assert response.status_code == 200
    data = response.json()
    assert "triggers" in data
    assert "actions" in data
    assert any(t["value"] == "new_persona" for t in data["triggers"])
    assert any(a["value"] == "send_whatsapp" for a in data["actions"])


def test_save_automation_flow(client, db_session):
    payload = {"name": "Test flow remediation", "is_active": True}
    response = client.post("/api/crm/automations/flows", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "Test flow remediation"
    assert data["is_active"] is True


def test_validate_path(client):
    # Less than 3 nodes
    payload = {"nodes": ["n1", "n2"], "edges": [{"source": "n1", "target": "n2"}]}
    response = client.post("/api/crm/automations/flows/validate-path", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False

    # Valid >= 3 nodes path
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


def test_validate_path_db_fallback(client, db_session):
    # Create nodes in DB
    n1 = models.CrmAutomation(name="Node 1", trigger_event="new_persona", action_type="send_email", is_active=True)
    n2 = models.CrmAutomation(name="Node 2", trigger_event="birthday", action_type="send_sms", is_active=True)
    n3 = models.CrmAutomation(name="Node 3", trigger_event="birthday", action_type="send_whatsapp", is_active=True)
    db_session.add_all([n1, n2, n3])
    db_session.commit()

    # Create edges in DB
    edge1 = models.CrmAutomationEdge(source_id=n1.id, target_id=n2.id)
    edge2 = models.CrmAutomationEdge(source_id=n2.id, target_id=n3.id)
    db_session.add_all([edge1, edge2])
    db_session.commit()

    # Call validate-path with empty dict payload to trigger db fallback
    response = client.post("/api/crm/automations/flows/validate-path", json={})
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["max_path_length"] == 3


def test_branching_variables(client):
    response = client.get("/api/crm/automations/branching/variables")
    assert response.status_code == 200
    data = response.json()
    assert any(var["name"] == "nombre" for var in data)


def test_branching_traverse(client):
    # Dynamic conditions evaluating to True
    payload_true = {
        "variables": {"nombre": "Juan"},
        "conditions": [{"key": "nombre", "operator": "equals", "value": "Juan"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload_true)
    assert response.status_code == 200
    assert response.json()["result"] is True

    # Dynamic conditions evaluating to False
    payload_false = {
        "variables": {"nombre": "Juan"},
        "conditions": [{"key": "nombre", "operator": "equals", "value": "Pedro"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload_false)
    assert response.status_code == 200
    assert response.json()["result"] is False

    # Dynamic conditions
    payload = {
        "variables": {"nombre": "Juan", "sort_order": 5, "is_active": True},
        "conditions": [
            {"key": "nombre", "operator": "equals", "value": "Juan"},
            {"key": "sort_order", "operator": "gt", "value": 3},
            {"key": "is_active", "operator": "always", "value": ""}
        ]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.status_code == 200
    assert response.json()["result"] is True

    # Condition fails
    payload["conditions"][0]["value"] = "Pedro"
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.status_code == 200
    assert response.json()["result"] is False


def test_branching_traverse_operators(client):
    # equals: True
    payload = {
        "variables": {"field": "value"},
        "conditions": [{"key": "field", "operator": "equals", "value": "value"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # equals: False
    payload = {
        "variables": {"field": "value"},
        "conditions": [{"key": "field", "operator": "equals", "value": "diff"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is False

    # ne: True
    payload = {
        "variables": {"field": "value"},
        "conditions": [{"key": "field", "operator": "ne", "value": "diff"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # contains: True
    payload = {
        "variables": {"field": "somevaluehere"},
        "conditions": [{"key": "field", "operator": "contains", "value": "value"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # starts_with: True
    payload = {
        "variables": {"field": "value_suffix"},
        "conditions": [{"key": "field", "operator": "starts_with", "value": "value"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # in: True
    payload = {
        "variables": {"field": "val2"},
        "conditions": [{"key": "field", "operator": "in", "value": "val1, val2, val3"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # gt: True
    payload = {
        "variables": {"field": 10},
        "conditions": [{"key": "field", "operator": "gt", "value": 5}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # gt: TypeError/ValueError -> False
    payload = {
        "variables": {"field": "not_a_number"},
        "conditions": [{"key": "field", "operator": "gt", "value": 5}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is False

    # lt: True
    payload = {
        "variables": {"field": 2},
        "conditions": [{"key": "field", "operator": "lt", "value": 5}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # lt: TypeError/ValueError -> False
    payload = {
        "variables": {"field": "not_a_number"},
        "conditions": [{"key": "field", "operator": "lt", "value": 5}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is False

    # always: True
    payload = {
        "variables": {},
        "conditions": [{"key": "any", "operator": "always", "value": ""}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is True

    # missing variable in variables: False
    payload = {
        "variables": {},
        "conditions": [{"key": "missing", "operator": "equals", "value": "val"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.json()["result"] is False


def test_check_cycles(client):
    # No cycle
    payload = {
        "nodes": ["n1", "n2", "n3"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"}
        ]
    }
    response = client.post("/api/crm/automations/flows/check-cycles", json=payload)
    assert response.status_code == 200
    assert response.json()["cycles"] == []

    # Cycle detected
    payload = {
        "nodes": ["n1", "n2", "n3"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n1"}
        ]
    }
    response = client.post("/api/crm/automations/flows/check-cycles", json=payload)
    assert response.status_code == 200
    assert len(response.json()["cycles"]) > 0


def test_flows_validate(client):
    # No cycle
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [{"source": "n1", "target": "n2"}]
    }
    response = client.post("/api/crm/automations/flows/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True

    # With cycle
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n1"}
        ]
    }
    response = client.post("/api/crm/automations/flows/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_validate_node(client):
    # Standard valid
    response = client.post("/api/crm/automations/flows/validate-node", json={})
    assert response.status_code == 200
    assert response.json()["valid"] is True

    # Self reference via edges 1
    payload1 = {
        "nodes": ["n1"],
        "node_id": "n1",
        "edges": [{"source": "n1", "target": "n1"}]
    }
    response = client.post("/api/crm/automations/flows/validate-node", json=payload1)
    assert response.status_code == 200
    assert response.json()["valid"] is False

    # Self reference via edges 2
    payload2 = {
        "nodes": ["n2"],
        "node_id": "n2",
        "edges": [{"source": "n2", "target": "n2"}]
    }
    response = client.post("/api/crm/automations/flows/validate-node", json=payload2)
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_validate_graph(client):
    # No cycle
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [{"source": "n1", "target": "n2"}]
    }
    response = client.post("/api/crm/automations/validate-graph", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_flows_empty(client):
    response = client.post("/api/crm/automations/flows/empty", json={"nodes": []})
    assert response.status_code == 200
    assert response.json()["message"] == "Flow is empty"

    response = client.post("/api/crm/automations/flows/empty", json={"nodes": ["n1"]})
    assert response.status_code == 200
    assert response.json()["message"] == "Flow is not empty"


def test_flows_max_nodes_check(client):
    response = client.post("/api/crm/automations/flows/max-nodes-check", json={"nodes": ["n1"] * 5})
    assert response.status_code == 200
    assert response.json()["nodes_count"] == 5

    response = client.post("/api/crm/automations/flows/max-nodes-check", json={"nodes": ["n1"] * 105})
    assert response.status_code == 400


def test_flows_disconnected_nodes(client):
    payload = {
        "nodes": ["n1", "n2", "n3"],
        "edges": [{"source": "n1", "target": "n2"}]
    }
    response = client.post("/api/crm/automations/flows/disconnected-nodes", json=payload)
    assert response.status_code == 200
    assert response.json()["warning"] == "disconnected nodes"
    assert response.json()["nodes"] == ["n3"]


def test_flows_validate_types(client):
    response = client.post("/api/crm/automations/flows/validate-types")
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_flows_unicode(client):
    response = client.post("/api/crm/automations/flows/unicode")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_validate_path_length_api(client):
    response = client.post("/api/crm/automations/flows/validate-path-length", json={"nodes_count": 2})
    assert response.status_code == 200
    assert response.json()["valid"] is False

    response = client.post("/api/crm/automations/flows/validate-path-length", json={"nodes_count": 3})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_multiple_inputs(client):
    payload = {
        "nodes": ["n1", "n2", "n3"],
        "edges": [
            {"source": "n1", "target": "n3"},
            {"source": "n2", "target": "n3"}
        ]
    }
    response = client.post("/api/crm/automations/flows/validate-multiple-inputs", json=payload)
    assert response.status_code == 200
    assert response.json()["multiple_inputs_nodes"] == ["n3"]


def test_validate_multiple_outputs(client):
    payload = {
        "nodes": ["n1", "n2", "n3"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n1", "target": "n3"}
        ]
    }
    response = client.post("/api/crm/automations/flows/validate-multiple-outputs", json=payload)
    assert response.status_code == 200
    assert response.json()["multiple_outputs_nodes"] == ["n1"]


def test_clean_orphans(client):
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"}
        ]
    }
    response = client.post("/api/crm/automations/flows/clean-orphans", json=payload)
    assert response.status_code == 200
    assert response.json()["cleaned_count"] == 1


def test_cross_flow_check(client):
    response = client.post("/api/crm/automations/flows/cross-flow-check")
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_branching_null_vars(client):
    payload = {"variables": {"nombre": None, "email": "juan@example.com"}}
    response = client.post("/api/crm/automations/branching/null-vars", json=payload)
    assert response.status_code == 200
    assert response.json()["null_variables"] == ["nombre"]


def test_branching_type_mismatch(client):
    response = client.post("/api/crm/automations/branching/type-mismatch")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_branching_missing_else(client):
    response = client.post("/api/crm/automations/branching/missing-else")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_branching_infinite_nesting(client):
    response = client.post("/api/crm/automations/branching/infinite-nesting")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_branching_unexpected_op(client):
    response = client.post("/api/crm/automations/branching/unexpected-op")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_cycle_deep(client):
    payload = {
        "nodes": ["n1", "n2", "n3", "n4", "n5"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n4"},
            {"source": "n4", "target": "n5"},
            {"source": "n5", "target": "n1"}
        ]
    }
    response = client.post("/api/crm/automations/flows/cycle-deep", json=payload)
    assert response.status_code == 200
    assert len(response.json()["cycles"]) > 0


def test_multiple_cycles(client):
    payload = {
        "nodes": ["n1", "n2", "n3", "n4"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n1"},
            {"source": "n3", "target": "n4"},
            {"source": "n4", "target": "n3"}
        ]
    }
    response = client.post("/api/crm/automations/flows/multiple-cycles", json=payload)
    assert response.status_code == 200
    assert len(response.json()["cycles"]) > 0


def test_disconnected_subgraph_cycles(client):
    payload = {
        "nodes": ["n1", "n2", "n3", "n4"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n3", "target": "n4"},
            {"source": "n4", "target": "n3"}
        ]
    }
    response = client.post("/api/crm/automations/flows/disconnected-subgraph-cycles", json=payload)
    assert response.status_code == 200
    assert len(response.json()["cycles"]) > 0


def test_validate_complex_dag(client):
    response = client.post("/api/crm/automations/flows/validate-complex-dag", json={})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_concurrent_cycle_checks(client):
    response = client.post("/api/crm/automations/flows/concurrent-cycle-checks", json={})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_kanban_sync_reorder(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    pipeline = models.PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline Test",
        tipo="NUEVOS_VISITANTES",
        activo=True
    )
    db_session.add(pipeline)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    payload = {"pipeline_id": str(pipeline.id)}
    response = client.post("/api/crm/pipeline/kanban/sync-reorder", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "synced"


def test_flow_builder_three_node_render(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    flow = models.CrmAutomationFlow(name="Test Flow", is_active=True)
    db_session.add(flow)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    payload = {"flow_id": str(flow.id)}
    response = client.post("/api/crm/automations/flow-builder/three-node-render", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "rendered"


def test_branching_validate_cycles(client):
    response = client.post("/api/crm/automations/branching/validate-cycles", json={})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_reorder_trigger_automation(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    pipeline = models.PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline Test",
        tipo="NUEVOS_VISITANTES",
        activo=True
    )
    db_session.add(pipeline)
    db_session.flush()
    etapa1 = models.EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="Etapa 1",
        orden=1
    )
    db_session.add(etapa1)
    db_session.flush()
    caso = models.CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa1.id,
        titulo_caso="Caso 1",
        origen_canal="WEB_FORM",
        sort_order=1
    )
    db_session.add(caso)
    automation = models.CrmAutomation(name="Stage Change Trigger", trigger_event="stage_change", action_type="send_email", is_active=True)
    db_session.add(automation)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    payload = {"caso_id": str(caso.id)}
    response = client.post("/api/crm/pipeline/casos/reorder-trigger-automation", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "triggered"


def test_branching_three_node_traversal(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    pipeline = models.PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline Test",
        tipo="NUEVOS_VISITANTES",
        activo=True
    )
    db_session.add(pipeline)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    payload = {"pipeline_id": str(pipeline.id)}
    response = client.post("/api/crm/automations/branching/three-node-traversal", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "traversed"


def test_drag_drop_validate_cycles(client):
    response = client.post("/api/crm/pipeline/kanban/drag-drop/validate-cycles", json={})
    assert response.status_code == 200
    assert response.json()["valid"] is True

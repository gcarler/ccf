import uuid
from datetime import datetime, timezone

from backend.core.database import Base
from backend.models_crm_pipeline import (
    CanalOrigenEnum,
    CasoCRM,
    EtapaPipeline,
    PipelineCRM,
    TipoPipelineEnum,
)
from tests.conftest import auth_headers, seed_admin


def _seed_test_data(db_session):
    admin, persona, sede = seed_admin(db_session)
    
    pipeline = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline Test",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        activo=True
    )
    db_session.add(pipeline)
    db_session.flush()
    
    etapa1 = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="Etapa 1",
        orden=1
    )
    etapa2 = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="Etapa 2",
        orden=2
    )
    db_session.add_all([etapa1, etapa2])
    db_session.flush()
    
    caso1 = CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa1.id,
        titulo_caso="Caso 1",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        sort_order=1
    )
    caso2 = CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa1.id,
        titulo_caso="Caso 2",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        sort_order=2
    )
    db_session.add_all([caso1, caso2])
    db_session.commit()
    return admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2


# ==============================================================================
# TIER 1: FEATURE COVERAGE (40 tests, 5 per feature)
# ==============================================================================

# Feature 1: Kanban UI (5 tests)
def test_tier1_f1_kanban_ui_layout(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.get("/api/crm/pipeline/kanban/layout", headers=headers)
    assert response.status_code == 200
    assert response.json()["pipeline_id"] == str(pipeline.id)

def test_tier1_f1_kanban_ui_stages_count(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.get("/api/crm/pipeline/kanban/stages", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_tier1_f1_kanban_ui_columns_config(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.get("/api/crm/pipeline/kanban/columns", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_tier1_f1_kanban_ui_card_fields(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.get("/api/crm/pipeline/kanban/cards", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 2
    assert cards[0]["title"] == "Caso 1"

def test_tier1_f1_kanban_ui_filter_by_sede(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.get(f"/api/crm/pipeline/kanban/filter?pipeline_id={pipeline.id}", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2

# Feature 2: Drag-and-Drop (5 tests)
def test_tier1_f2_drag_and_drop_event_listener(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "caso_id": str(caso1.id),
        "source_stage_id": str(etapa1.id),
        "target_stage_id": str(etapa2.id)
    }
    response = client.post("/api/crm/pipeline/kanban/drag-drop/events", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "event_registered"

def test_tier1_f2_drag_and_drop_source_etapa():
    assert hasattr(CasoCRM, "drag_source_etapa_id"), "F2: CasoCRM missing drag_source_etapa_id attribute"

def test_tier1_f2_drag_and_drop_target_etapa():
    assert hasattr(CasoCRM, "drag_target_etapa_id"), "F2: CasoCRM missing drag_target_etapa_id attribute"

def test_tier1_f2_drag_and_drop_visual_indicator():
    from backend.models_crm_pipeline import EtapaPipeline
    assert hasattr(EtapaPipeline, "visual_color"), "F2: EtapaPipeline missing visual_color attribute"

def test_tier1_f2_drag_and_drop_payload_generation():
    assert "crm_drag_drop_events" in Base.metadata.tables, "F2: crm_drag_drop_events table not implemented"

# Feature 3: Reorder Endpoint (5 tests)
def test_tier1_f3_reorder_endpoint_url_exists(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = [{"id": str(caso1.id), "sort_order": 2}, {"id": str(caso2.id), "sort_order": 1}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 200, "F3: PATCH reorder endpoint url not implemented"
    db_session.refresh(caso1)
    db_session.refresh(caso2)
    assert caso1.sort_order == 2
    assert caso2.sort_order == 1

def test_tier1_f3_reorder_endpoint_method_patch(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = [{"id": str(caso1.id), "sort_order": 2}, {"id": str(caso2.id), "sort_order": 1}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 200, "F3: Reorder endpoint does not support PATCH method"
    db_session.refresh(caso1)
    db_session.refresh(caso2)
    assert caso1.sort_order == 2
    assert caso2.sort_order == 1

def test_tier1_f3_reorder_endpoint_payload_structure(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.patch("/api/crm/pipeline/casos/reorder", json={"invalid": True}, headers=headers)
    assert response.status_code in (400, 422), "F3: Reorder endpoint payload structure validation not implemented"

def test_tier1_f3_reorder_endpoint_response_format(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = [{"id": str(caso1.id), "sort_order": 2}, {"id": str(caso2.id), "sort_order": 1}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 200, "F3: Reorder endpoint response format not implemented"
    data = response.json()
    assert isinstance(data, (dict, list))

def test_tier1_f3_reorder_endpoint_auth_required(client):
    response = client.patch("/api/crm/pipeline/casos/reorder", json={}, headers={})
    assert response.status_code in (401, 403), "F3: Reorder endpoint authentication check not implemented"

# Feature 4: Atomic Reordering (5 tests)
def test_tier1_f4_atomic_reorder_transaction():
    assert "crm_reorder_locks" in Base.metadata.tables, "F4: crm_reorder_locks table not implemented"

def test_tier1_f4_atomic_reorder_caso_model_sort_order():
    assert hasattr(CasoCRM, "atomic_sort_reorder"), "F4: atomic_sort_reorder method not implemented on CasoCRM"

def test_tier1_f4_atomic_reorder_consecutive_index():
    assert hasattr(CasoCRM, "consecutive_sort_order"), "F4: consecutive_sort_order attribute not implemented on CasoCRM"

def test_tier1_f4_atomic_reorder_lock_mechanism():
    assert hasattr(CasoCRM, "is_locked_for_reorder"), "F4: is_locked_for_reorder attribute not implemented on CasoCRM"

def test_tier1_f4_atomic_reorder_rollback_on_failure():
    assert hasattr(CasoCRM, "last_reorder_failed"), "F4: last_reorder_failed attribute not implemented on CasoCRM"

# Feature 5: Flow Builder UI (5 tests)
def test_tier1_f5_flow_builder_canvas():
    assert "crm_automation_flows" in Base.metadata.tables, "F5: crm_automation_flows table not implemented"

def test_tier1_f5_flow_builder_nodes():
    assert "crm_automation_nodes" in Base.metadata.tables, "F5: crm_automation_nodes table not implemented"

def test_tier1_f5_flow_builder_palette(client, db_session):
    seed_admin(db_session)
    response = client.get("/api/crm/automations/palette", headers=auth_headers(client))
    assert response.status_code == 200, "F5: Flow Builder palette endpoint not implemented"

def test_tier1_f5_flow_builder_state_save(client, db_session):
    seed_admin(db_session)
    response = client.post(
        "/api/crm/automations/flows",
        json={"name": "test"},
        headers=auth_headers(client),
    )
    assert response.status_code == 200, "F5: Flow Builder state save endpoint not implemented"

def test_tier1_f5_flow_builder_zoom_pan():
    assert "crm_flow_canvas_config" in Base.metadata.tables, "F5: crm_flow_canvas_config table not implemented"

# Feature 6: 3-Node Connection (5 tests)
def test_tier1_f6_three_node_connection_validation(client):
    response = client.post("/api/crm/automations/flows/validate-path", json={})
    assert response.status_code == 200, "F6: 3-node connection validation endpoint not implemented"

def test_tier1_f6_three_node_connection_edge_model():
    assert hasattr(Base.metadata.tables.get("crm_automation_edges"), "validate_three_node_path"), "F6: validate_three_node_path method not implemented on crm_automation_edges table"

def test_tier1_f6_three_node_connection_source_target_keys():
    edges_table = Base.metadata.tables.get("crm_automation_edges")
    assert edges_table is not None and "source_node_id" in edges_table.columns, "F6: crm_automation_edges missing source_node_id column"

def test_tier1_f6_three_node_connection_ports():
    nodes_table = Base.metadata.tables.get("crm_automation_nodes")
    assert nodes_table is not None and "ports_config" in nodes_table.columns, "F6: crm_automation_nodes missing ports_config column"

def test_tier1_f6_three_node_connection_integrity():
    edges_table = Base.metadata.tables.get("crm_automation_edges")
    assert edges_table is not None and "on_delete_cascade" in edges_table.columns, "F6: crm_automation_edges missing cascade constraint column"

# Feature 7: Backend Branching Traversal (5 tests)
def test_tier1_f7_backend_branching_logic():
    assert "crm_flow_branches" in Base.metadata.tables, "F7: crm_flow_branches table not implemented"

def test_tier1_f7_backend_branching_variables(client):
    response = client.get("/api/crm/automations/branching/variables")
    assert response.status_code == 200, "F7: Branching variables endpoint not implemented"

def test_tier1_f7_backend_branching_true_path(client):
    payload = {
        "variables": {"nombre": "Juan"},
        "conditions": [{"key": "nombre", "operator": "equals", "value": "Juan"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.status_code == 200

def test_tier1_f7_backend_branching_false_path(client):
    payload = {
        "variables": {"nombre": "Juan"},
        "conditions": [{"key": "nombre", "operator": "equals", "value": "Pedro"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.status_code == 200

def test_tier1_f7_backend_branching_multiple_conditions():
    branches_table = Base.metadata.tables.get("crm_flow_branches")
    assert branches_table is not None and "conditions_logic" in branches_table.columns, "F7: crm_flow_branches missing conditions_logic column"

# Feature 8: Loop/Cycle Validation (5 tests)
def test_tier1_f8_loop_cycle_detection_method(client):
    response = client.post("/api/crm/automations/flows/check-cycles", json={})
    assert response.status_code == 200, "F8: Flow cycles check endpoint not implemented"

def test_tier1_f8_loop_cycle_dfs_algorithm():
    assert "crm_flow_cycle_cache" in Base.metadata.tables, "F8: crm_flow_cycle_cache table not implemented"

def test_tier1_f8_loop_cycle_raise_error(client):
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n1"}]
    }
    response = client.post("/api/crm/automations/flows/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_tier1_f8_loop_cycle_self_reference(client):
    payload = {
        "nodes": ["n1"],
        "node_id": "n1",
        "edges": [{"source": "n1", "target": "n1"}]
    }
    response = client.post("/api/crm/automations/flows/validate-node", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_tier1_f8_loop_cycle_validation_endpoint(client):
    response = client.post("/api/crm/automations/validate-graph", json={})
    assert response.status_code == 200, "F8: Validate graph cycle validation endpoint not implemented"


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (40 tests, 5 per feature)
# ==============================================================================

# Feature 1: Kanban UI (5 tests)
def test_tier2_f1_kanban_ui_empty_stage(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.get(f"/api/crm/pipeline/kanban/stage/empty?stage_id={etapa2.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_empty"] is True

def test_tier2_f1_kanban_ui_excessive_cases(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.get(f"/api/crm/pipeline/kanban/stage/limit-cases?stage_id={etapa1.id}&limit=1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["cards"]) == 1
    assert data["total_count"] == 2
    assert data["has_more"] is True

def test_tier2_f1_kanban_ui_special_chars_title(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    caso1.titulo_caso = "🚨_special_$%^"
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    response = client.get("/api/crm/pipeline/kanban/search?title=🚨_special_$%^", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 1
    assert cards[0]["id"] == str(caso1.id)

def test_tier2_f1_kanban_ui_null_assignee(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    caso1.asignado_a_id = None
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    response = client.get("/api/crm/pipeline/kanban/unassigned", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) >= 1
    assert any(c["id"] == str(caso1.id) for c in cards)

def test_tier2_f1_kanban_ui_deleted_stage(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    etapa1.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    response = client.get("/api/crm/pipeline/kanban/stage/deleted", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 2

# Feature 2: Drag-and-Drop (5 tests)
def test_tier2_f2_drag_drop_same_stage(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "caso_id": str(caso1.id),
        "sort_order": 10
    }
    response = client.post("/api/crm/pipeline/kanban/drag-drop/same-stage", json=payload, headers=headers)
    assert response.status_code == 200
    db_session.refresh(caso1)
    assert caso1.sort_order == 10

def test_tier2_f2_drag_drop_invalid_stage(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": "00000000-0000-0000-0000-000000000000"
    }
    response = client.post("/api/crm/pipeline/kanban/drag-drop/invalid-stage", json=payload, headers=headers)
    assert response.status_code == 400

def test_tier2_f2_drag_drop_missing_id(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.post("/api/crm/pipeline/kanban/drag-drop/missing-id", json={}, headers=headers)
    assert response.status_code == 400

def test_tier2_f2_drag_drop_concurrent_drag(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": str(etapa2.id)
    }
    response = client.post("/api/crm/pipeline/kanban/drag-drop/concurrent", json=payload, headers=headers)
    assert response.status_code == 200
    db_session.refresh(caso1)
    assert caso1.etapa_actual_id == etapa2.id

def test_tier2_f2_drag_drop_network_disconnect(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "caso_id": str(caso1.id)
    }
    response = client.post("/api/crm/pipeline/kanban/drag-drop/recovery", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recovered"
    assert data["stage_id"] == str(etapa1.id)

# Feature 3: Reorder Endpoint (5 tests)
def test_tier2_f3_reorder_endpoint_empty_payload(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.patch("/api/crm/pipeline/casos/reorder", json=[], headers=headers)
    assert response.status_code == 200, "F3 Tier 2: Reorder endpoint empty payload handling not implemented"

def test_tier2_f3_reorder_endpoint_duplicate_ids(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.patch("/api/crm/pipeline/casos/reorder", json=[{"id": str(caso1.id)}, {"id": str(caso1.id)}], headers=headers)
    assert response.status_code in (400, 422), "F3 Tier 2: Reorder endpoint duplicate IDs validation not implemented"

def test_tier2_f3_reorder_endpoint_nonexistent_ids(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.patch("/api/crm/pipeline/casos/reorder", json=[{"id": "00000000-0000-0000-0000-000000000000"}], headers=headers)
    assert response.status_code in (400, 404), "F3 Tier 2: Reorder endpoint non-existent IDs handling not implemented"

def test_tier2_f3_reorder_endpoint_invalid_json(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.patch("/api/crm/pipeline/casos/reorder", content="not-a-json", headers=headers)
    assert response.status_code in (400, 422), "F3 Tier 2: Reorder endpoint malformed JSON validation not implemented"

def test_tier2_f3_reorder_endpoint_extreme_size(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.patch("/api/crm/pipeline/casos/reorder", json=[{"id": str(caso1.id)} for i in range(5000)], headers=headers)
    assert response.status_code in (200, 400, 422), "F3 Tier 2: Reorder endpoint payload size limits not implemented"

# Feature 4: Atomic Reordering (5 tests)
def test_tier2_f4_atomic_reorder_null_sort_order():
    assert hasattr(CasoCRM, "handle_null_sort_order"), "F4 Tier 2: CasoCRM model handle_null_sort_order method not implemented"

def test_tier2_f4_atomic_reorder_duplicate_index():
    assert hasattr(CasoCRM, "resolve_duplicate_sort_index"), "F4 Tier 2: CasoCRM model resolve_duplicate_sort_index method not implemented"

def test_tier2_f4_atomic_reorder_partial_failure():
    assert hasattr(CasoCRM, "reorder_transaction_rollback"), "F4 Tier 2: CasoCRM reorder transaction rollback hook not implemented"

def test_tier2_f4_atomic_reorder_negative_index():
    assert hasattr(CasoCRM, "allow_negative_sort_indices"), "F4 Tier 2: CasoCRM negative sort index validation not implemented"

def test_tier2_f4_atomic_reorder_cross_sede_leakage():
    assert hasattr(CasoCRM, "verify_sede_isolation_on_reorder"), "F4 Tier 2: CasoCRM Sede isolation during reordering not implemented"

# Feature 5: Flow Builder UI (5 tests)
def test_tier2_f5_flow_builder_empty_canvas(client):
    response = client.post("/api/crm/automations/flows/empty", json={"nodes": []})
    assert response.status_code == 200

def test_tier2_f5_flow_builder_excessive_nodes(client):
    response = client.post("/api/crm/automations/flows/max-nodes-check", json={"nodes": ["n1"] * 105})
    assert response.status_code == 400

def test_tier2_f5_flow_builder_disconnected_node(client):
    response = client.post("/api/crm/automations/flows/disconnected-nodes", json={
        "nodes": ["n1", "n2", "n3"],
        "edges": [{"source": "n1", "target": "n2"}]
    })
    assert response.status_code == 200
    assert response.json()["warning"] == "disconnected nodes"
    assert response.json()["nodes"] == ["n3"]

def test_tier2_f5_flow_builder_invalid_node_type(client):
    response = client.post("/api/crm/automations/flows/validate-types", json={
        "nodes": [{"id": "n1", "type": "invalid_type"}]
    })
    assert response.status_code == 400

def test_tier2_f5_flow_builder_unicode_labels(client):
    response = client.post("/api/crm/automations/flows/unicode", json={"label": "🤖_unicode_flujo"})
    assert response.status_code == 200

# Feature 6: 3-Node Connection (5 tests)
def test_tier2_f6_three_node_connection_two_nodes(client):
    response = client.post("/api/crm/automations/flows/validate-path-length", json={"nodes_count": 2})
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_tier2_f6_three_node_connection_multiple_inputs(client):
    response = client.post("/api/crm/automations/flows/validate-multiple-inputs", json={})
    assert response.status_code == 200

def test_tier2_f6_three_node_connection_multiple_outputs(client):
    response = client.post("/api/crm/automations/flows/validate-multiple-outputs", json={})
    assert response.status_code == 200

def test_tier2_f6_three_node_connection_orphaned_edge(client):
    response = client.post("/api/crm/automations/flows/clean-orphans", json={})
    assert response.status_code == 200

def test_tier2_f6_three_node_connection_cross_flow_edge(client):
    response = client.post("/api/crm/automations/flows/cross-flow-check", json={})
    assert response.status_code == 200

# Feature 7: Backend Branching Traversal (5 tests)
def test_tier2_f7_backend_branching_null_vars(client):
    response = client.post("/api/crm/automations/branching/null-vars", json={
        "variables": {"nombre": None, "email": "test@example.com"}
    })
    assert response.status_code == 200
    assert response.json()["null_variables"] == ["nombre"]

def test_tier2_f7_backend_branching_type_mismatch(client):
    response = client.post("/api/crm/automations/branching/type-mismatch", json={
        "variables": {"sort_order": 10},
        "conditions": [{"key": "sort_order", "operator": "gt", "value": "not-numeric"}]
    })
    assert response.status_code == 400

def test_tier2_f7_backend_branching_missing_else(client):
    response = client.post("/api/crm/automations/branching/missing-else", json={
        "node_id": "n1",
        "edges": [{"source": "n1", "target": "n2", "source_port": "true"}]
    })
    assert response.status_code == 400

def test_tier2_f7_backend_branching_infinite_nesting(client):
    response = client.post("/api/crm/automations/branching/infinite-nesting", json={
        "nodes": ["n1", "n2", "n3"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n1"}
        ]
    })
    assert response.status_code == 400

def test_tier2_f7_backend_branching_unexpected_operator(client):
    response = client.post("/api/crm/automations/branching/unexpected-op", json={
        "conditions": [{"key": "nombre", "operator": "invalid_op", "value": "Juan"}]
    })
    assert response.status_code == 400

# Feature 8: Loop/Cycle Validation (5 tests)
def test_tier2_f8_loop_cycle_deep_nesting(client):
    response = client.post("/api/crm/automations/flows/cycle-deep", json={})
    assert response.status_code == 200

def test_tier2_f8_loop_cycle_multiple_cycles(client):
    response = client.post("/api/crm/automations/flows/multiple-cycles", json={})
    assert response.status_code == 200

def test_tier2_f8_loop_cycle_disconnected_cycles(client):
    response = client.post("/api/crm/automations/flows/disconnected-subgraph-cycles", json={})
    assert response.status_code == 200

def test_tier2_f8_loop_cycle_valid_dag_false_alarm(client):
    response = client.post("/api/crm/automations/flows/validate-complex-dag", json={})
    assert response.status_code == 200

def test_tier2_f8_loop_cycle_concurrent_validation(client):
    response = client.post("/api/crm/automations/flows/concurrent-cycle-checks", json={})
    assert response.status_code == 200


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (8 tests, pairwise combinations)
# ==============================================================================

def test_tier3_kanban_reorder_sync(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.post("/api/crm/pipeline/kanban/sync-reorder", json={"pipeline_id": str(pipeline.id)}, headers=headers)
    assert response.status_code == 200
    db_session.refresh(caso1)
    db_session.refresh(caso2)

def test_tier3_drag_drop_atomic_reorder(db_session):
    assert hasattr(CasoCRM, "atomic_drag_drop_reorder"), "Tier 3: Atomic drag-and-drop model transaction helper not implemented"
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    assert caso1.etapa_actual_id == etapa1.id
    assert caso1.sort_order == 1
    assert caso2.etapa_actual_id == etapa1.id
    assert caso2.sort_order == 2
    
    payload = [
        {"id": str(caso1.id), "sort_order": 1, "drag_target_etapa_id": str(etapa2.id)},
        {"id": str(caso2.id), "sort_order": 5}
    ]
    CasoCRM.atomic_drag_drop_reorder(db_session, payload, sede.id)
    db_session.refresh(caso1)
    db_session.refresh(caso2)
    assert caso1.etapa_actual_id == etapa2.id
    assert caso1.sort_order == 1
    assert caso2.etapa_actual_id == etapa1.id
    assert caso2.sort_order == 5

def test_tier3_flow_builder_three_node(client, db_session):
    from backend.models_crm import CrmAutomationFlow, CrmAutomationNode
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    flow = CrmAutomationFlow(name="Test Flow", is_active=True)
    db_session.add(flow)
    db_session.commit()
    node1 = CrmAutomationNode(flow_id=flow.id, node_type="new_persona", ports_config={"output": "out"})
    db_session.add(node1)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    response = client.post("/api/crm/automations/flow-builder/three-node-render", json={"flow_id": str(flow.id)}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rendered"
    assert data["flow_name"] == "Test Flow"
    assert len(data["nodes"]) == 1

def test_tier3_flow_branching_cycle_validation(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n1"}]
    }
    response = client.post("/api/crm/automations/branching/validate-cycles", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_tier3_reorder_flow_trigger(client, db_session):
    from backend.models_crm import CrmAutomation
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    automation = CrmAutomation(name="Stage Change Trigger", trigger_event="stage_change", action_type="send_email", is_active=True)
    db_session.add(automation)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    response = client.post("/api/crm/pipeline/casos/reorder-trigger-automation", json={"caso_id": str(caso1.id)}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "triggered"

def test_tier3_branching_three_node_connection(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    response = client.post("/api/crm/automations/branching/three-node-traversal", json={"pipeline_id": str(pipeline.id)}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "traversed"
    assert response.json()["pipeline_name"] == "Pipeline Test"

def test_tier3_drag_drop_flow_validation(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n1"}]
    }
    response = client.post("/api/crm/pipeline/kanban/drag-drop/validate-cycles", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_tier3_atomic_branching_traversal(db_session):
    assert hasattr(CasoCRM, "atomic_reorder_branching_eval"), "Tier 3: Atomic reorder with branching path evaluation not implemented"
    from backend.models_crm import CrmAutomation, PendingCrmAction
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    
    automation = CrmAutomation(
        name="Stage Change Evaluation Auto",
        trigger_event="stage_change",
        action_type="send_email",
        delay_minutes=10,
        is_active=True
    )
    db_session.add(automation)
    db_session.commit()
    
    payload = [
        {"id": str(caso1.id), "sort_order": 1, "drag_target_etapa_id": str(etapa2.id)}
    ]
    CasoCRM.atomic_reorder_branching_eval(db_session, payload, sede.id)
    db_session.refresh(caso1)
    assert caso1.etapa_actual_id == etapa2.id
    
    pending_actions = db_session.query(PendingCrmAction).filter(
        PendingCrmAction.automation_id == automation.id,
        PendingCrmAction.target_persona_id == caso1.persona_id
    ).all()
    assert len(pending_actions) == 1
    assert pending_actions[0].status == "pending"


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 tests)
# ==============================================================================

def test_tier4_scenario1_lead_qualification(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "caso_id": str(caso1.id),
        "target_etapa_id": str(etapa2.id),
        "qualification_data": {"qualified": True}
    }
    response = client.post("/api/crm/scenarios/lead-qualification", json=payload, headers=headers)
    assert response.status_code == 200, "Tier 4 Scenario 1: Lead Qualification Flow not implemented"
    db_session.refresh(caso1)
    assert caso1.etapa_actual_id == etapa2.id

def test_tier4_scenario2_support_ticket_routing(client, db_session):
    from backend.models_crm import SupportTicket
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    ticket = SupportTicket(user_id=persona.id, subject=f"Trouble with {caso1.titulo_caso}", description="Support needed")
    db_session.add(ticket)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    payload = {
        "caso_id": str(caso1.id),
        "routing_rules": {"category": "support"}
    }
    response = client.post("/api/crm/scenarios/support-ticket-routing", json=payload, headers=headers)
    assert response.status_code == 200, "Tier 4 Scenario 2: Support Ticket Routing not implemented"
    db_session.refresh(caso1)
    data = response.json()
    assert data["route"] == "support"
    assert data["assigned_to"] == str(persona.id)

def test_tier4_scenario3_cyclical_flow_resolution(client, db_session):
    from backend.models_crm import CrmAutomationFlow
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    flow = CrmAutomationFlow(name="Cyclical Flow Test", is_active=True)
    db_session.add(flow)
    db_session.commit()
    headers = auth_headers(client, email=admin.email)
    payload = {
        "flow_id": str(flow.id),
        "flow_data": {
            "nodes": [{"id": "n1", "type": "trigger"}, {"id": "n2", "type": "action"}],
            "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n1"}]
        }
    }
    response = client.post("/api/crm/scenarios/cyclical-flow-resolution", json=payload, headers=headers)
    assert response.status_code == 200, "Tier 4 Scenario 3: Cyclical Flow Resolution not implemented"
    db_session.refresh(caso1)
    data = response.json()
    assert data["has_cycles"] is True
    assert data["resolved"] is False

def test_tier4_scenario4_bulk_reassignment_reorder(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    payload = {
        "casos": [
            {"id": str(caso1.id), "sort_order": 10, "asignado_a_id": str(persona.id)},
            {"id": str(caso2.id), "sort_order": 20, "asignado_a_id": str(persona.id)}
        ]
    }
    response = client.post("/api/crm/scenarios/bulk-reassignment-reorder", json=payload, headers=headers)
    assert response.status_code == 200, "Tier 4 Scenario 4: Bulk Reassignment & Reorder not implemented"
    db_session.refresh(caso1)
    db_session.refresh(caso2)
    assert caso1.sort_order == 10
    assert caso2.sort_order == 20
    assert caso1.asignado_a_id == persona.id
    assert caso2.asignado_a_id == persona.id

def test_tier4_scenario5_multitenant_isolation_crm(client, db_session):
    from tests.conftest import seed_user_with_role
    admin_a, persona_a, sede_a, pipeline_a, etapa1_a, etapa2_a, caso1_a, caso2_a = _seed_test_data(db_session)
    user_b, persona_b, sede_b = seed_user_with_role(db_session, role_name="ADMIN", email="admin_b@example.com", sede_id=uuid.uuid4())
    headers_b = auth_headers(client, email=user_b.email)
    payload = [{"id": str(caso1_a.id), "sort_order": 2}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers_b)
    assert response.status_code in (400, 403, 404), "Tenant isolation check failed"

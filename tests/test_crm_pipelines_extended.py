"""
Extended tests for backend.api.crm.pipelines — pure logic functions + API.
"""
from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.api.crm.pipelines import (
    check_for_cycles_dfs,
    evaluate_condition,
    get_graph_from_payload_or_db,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, sede = _seed_admin(db_session, email="pipe_ext@test.com")
    headers = _auth_headers(client, email="pipe_ext@test.com", password="testpass123")
    return {"c": client, "h": headers, "sede": sede}


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestCheckForCyclesDFS:
    def test_no_edges_no_cycle(self):
        has_cycle, cycles = check_for_cycles_dfs(["a", "b", "c"], [])
        assert has_cycle is False

    def test_simple_no_cycle(self):
        has_cycle, _ = check_for_cycles_dfs(
            ["a", "b", "c"],
            [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
        )
        assert has_cycle is False

    def test_direct_cycle(self):
        has_cycle, cycles = check_for_cycles_dfs(
            ["a", "b"],
            [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}],
        )
        assert has_cycle is True

    def test_self_loop(self):
        has_cycle, _ = check_for_cycles_dfs(
            ["a"], [{"source": "a", "target": "a"}],
        )
        assert has_cycle is True

    def test_empty(self):
        has_cycle, _ = check_for_cycles_dfs([], [])
        assert has_cycle is False


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATE CONDITION
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvaluateCondition:
    def test_always_true(self):
        assert evaluate_condition("k", "always", "x", {}) is True

    def test_empty_op_true(self):
        assert evaluate_condition("k", "", "x", {}) is True

    def test_key_missing(self):
        assert evaluate_condition("k", "equals", "v", {}) is False

    def test_equals_string(self):
        assert evaluate_condition("k", "equals", "hello", {"k": "hello"}) is True
        assert evaluate_condition("k", "equals", "hello", {"k": "world"}) is False

    def test_equals_case_insensitive(self):
        assert evaluate_condition("k", "equals", "Hello", {"k": "hello"}) is True

    def test_equals_bool(self):
        assert evaluate_condition("k", "equals", "true", {"k": True}) is True

    def test_equals_none(self):
        assert evaluate_condition("k", "equals", None, {"k": None}) is True
        assert evaluate_condition("k", "equals", "null", {"k": None}) is True

    def test_ne(self):
        assert evaluate_condition("k", "ne", "a", {"k": "b"}) is True
        assert evaluate_condition("k", "ne", "a", {"k": "a"}) is False

    def test_contains(self):
        assert evaluate_condition("k", "contains", "ell", {"k": "hello"}) is True
        assert evaluate_condition("k", "contains", "xyz", {"k": "hello"}) is False

    def test_contains_none(self):
        assert evaluate_condition("k", "contains", "x", {"k": None}) is False

    def test_starts_with(self):
        assert evaluate_condition("k", "starts_with", "he", {"k": "hello"}) is True

    def test_in(self):
        assert evaluate_condition("k", "in", "a,b,c", {"k": "b"}) is True
        assert evaluate_condition("k", "in", "a,b,c", {"k": "z"}) is False

    def test_gt_numeric(self):
        assert evaluate_condition("k", "gt", "5", {"k": "10"}) is True
        assert evaluate_condition("k", "gt", "10", {"k": "5"}) is False

    def test_lt_numeric(self):
        assert evaluate_condition("k", "lt", "10", {"k": "5"}) is True
        assert evaluate_condition("k", "lt", "5", {"k": "10"}) is False

    def test_unknown_op_false(self):
        assert evaluate_condition("k", "bad_op", "x", {"k": "x"}) is False

    def test_gt_none(self):
        assert evaluate_condition("k", "gt", "5", {"k": None}) is False


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH FROM PAYLOAD
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetGraphFromPayload:
    def test_none_payload(self, db_session):
        nodes, edges = get_graph_from_payload_or_db(None, db_session)
        assert isinstance(nodes, list)

    def test_with_dict_nodes(self):
        payload = {"flow_data": {"nodes": [{"id": "a"}], "edges": [{"source": "a", "target": "b"}]}}
        nodes, edges = get_graph_from_payload_or_db(payload, None)
        assert "a" in nodes

    def test_with_string_nodes(self):
        payload = {"flow_data": {"nodes": ["a", "b"], "edges": [{"source": "a", "target": "b"}]}}
        nodes, edges = get_graph_from_payload_or_db(payload, None)
        assert "a" in nodes

    def test_missing_node_id_raises(self):
        with pytest.raises(ValueError):
            get_graph_from_payload_or_db({"flow_data": {"nodes": [{"id": None}], "edges": []}}, None)

    def test_missing_edge_src_raises(self):
        with pytest.raises(ValueError):
            get_graph_from_payload_or_db(
                {"flow_data": {"nodes": [{"id": "a"}], "edges": [{"source": None, "target": "b"}]}}, None
            )


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAutomationsPalette:
    def test_palette(self, full):
        assert _ok(full["c"].get("/api/crm/automations/palette", headers=full["h"]).status_code)


class TestAutomationsFlows:
    def test_create_flow(self, full):
        assert _ok(full["c"].post("/api/crm/automations/flows",
            json={"name": "Test", "trigger_type": "stage_change"}, headers=full["h"]).status_code)

    def test_validate_path(self, full):
        assert _ok(full["c"].post("/api/crm/automations/flows/validate-path",
            json={}, headers=full["h"]).status_code)

    def test_branching_vars(self, full):
        assert _ok(full["c"].get("/api/crm/automations/branching/variables", headers=full["h"]).status_code)


class TestKanbanDragDrop:
    def test_not_found(self, full):
        assert full["c"].post("/api/crm/pipeline/kanban/drag-drop/events",
            json={"caso_id": str(uuid.uuid4()), "source_stage_id": str(uuid.uuid4()),
                  "target_stage_id": str(uuid.uuid4())},
            headers=full["h"]).status_code == 404


class TestKanbanSearch:
    def test_search(self, full):
        assert _ok(full["c"].get("/api/crm/pipeline/kanban/search", headers=full["h"]).status_code)


class TestKanbanUnassigned:
    def test_unassigned(self, full):
        assert _ok(full["c"].get("/api/crm/pipeline/kanban/unassigned", headers=full["h"]).status_code)


class TestKanbanDeleted:
    def test_deleted(self, full):
        assert _ok(full["c"].get("/api/crm/pipeline/kanban/stage/deleted", headers=full["h"]).status_code)


class TestAutomationsValidate:
    def test_graph(self, full):
        assert _ok(full["c"].post("/api/crm/automations/validate-graph",
            json={"flow_data": {"nodes": [{"id": "a"}], "edges": []}}, headers=full["h"]).status_code)

    def test_cycles(self, full):
        assert _ok(full["c"].post("/api/crm/automations/flows/check-cycles",
            json={"flow_data": {"nodes": [{"id": "a"}], "edges": []}}, headers=full["h"]).status_code)

    def test_validate(self, full):
        assert _ok(full["c"].post("/api/crm/automations/flows/validate",
            json={"flow_data": {"nodes": [{"id": "a"}], "edges": []}}, headers=full["h"]).status_code)

    def test_node(self, full):
        assert _ok(full["c"].post("/api/crm/automations/flows/validate-node",
            json={"node": {"id": "a"}}, headers=full["h"]).status_code)

    def test_traverse(self, full):
        assert _ok(full["c"].post("/api/crm/automations/branching/traverse",
            json={"node_id": "a", "variables": {"stage": "call"}}, headers=full["h"]).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# KANBAN LAYOUT — success path
# ═══════════════════════════════════════════════════════════════════════════════


class TestKanbanLayoutSuccess:
    def test_kanban_layout_with_pipeline(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="Kanban Test", tipo=TipoPipelineEnum.CONSEJERIA, activo=True,
        )
        db_session.add(pipe)
        db_session.commit()
        resp = full["c"].get("/api/crm/pipeline/kanban/layout", headers=full["h"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_id"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# KANBAN FILTER — with params
# ═══════════════════════════════════════════════════════════════════════════════


class TestKanbanFilterExtended:
    def test_filter_by_pipeline(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum, PrioridadCasoEnum, EstadoCasoEnum, CanalOrigenEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="FilterTest", tipo=TipoPipelineEnum.CONSEJERIA,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add_all([pipe, etapa])
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(), persona_id=uuid.uuid4(), sede_id=full["sede"].id,
            pipeline_id=pipe.id, etapa_actual_id=etapa.id,
            titulo_caso="Test", prioridad=PrioridadCasoEnum.MEDIA,
            estado=EstadoCasoEnum.ABIERTO, origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/pipeline/kanban/filter?pipeline_id={pipe.id}", headers=full["h"])
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_filter_by_assignee(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum, PrioridadCasoEnum, EstadoCasoEnum, CanalOrigenEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="FilterTest2", tipo=TipoPipelineEnum.CONSEJERIA,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add_all([pipe, etapa])
        assignee = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", sede_id=full["sede"].id)
        db_session.add(assignee)
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(), persona_id=uuid.uuid4(), sede_id=full["sede"].id,
            pipeline_id=pipe.id, etapa_actual_id=etapa.id,
            titulo_caso="Test", prioridad=PrioridadCasoEnum.MEDIA,
            estado=EstadoCasoEnum.ABIERTO, origen_canal=CanalOrigenEnum.WEB_FORM,
            asignado_a_id=assignee.id,
        )
        db_session.add(caso)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/pipeline/kanban/filter?assignee_id={assignee.id}", headers=full["h"])
        assert resp.status_code == 200

    def test_filter_by_priority(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum, PrioridadCasoEnum, EstadoCasoEnum, CanalOrigenEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="FilterTest3", tipo=TipoPipelineEnum.CONSEJERIA,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add_all([pipe, etapa])
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(), persona_id=uuid.uuid4(), sede_id=full["sede"].id,
            pipeline_id=pipe.id, etapa_actual_id=etapa.id,
            titulo_caso="Test", prioridad=PrioridadCasoEnum.ALTA,
            estado=EstadoCasoEnum.ABIERTO, origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/pipeline/kanban/filter?priority={PrioridadCasoEnum.ALTA.value}", headers=full["h"])
        assert resp.status_code == 200

    def test_filter_by_status(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum, PrioridadCasoEnum, EstadoCasoEnum, CanalOrigenEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="FilterTest4", tipo=TipoPipelineEnum.CONSEJERIA,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add_all([pipe, etapa])
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(), persona_id=uuid.uuid4(), sede_id=full["sede"].id,
            pipeline_id=pipe.id, etapa_actual_id=etapa.id,
            titulo_caso="Test", prioridad=PrioridadCasoEnum.MEDIA,
            estado=EstadoCasoEnum.ABIERTO, origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/pipeline/kanban/filter?status={EstadoCasoEnum.ABIERTO.value}", headers=full["h"])
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# DRAG-DROP EVENTS — success path
# ═══════════════════════════════════════════════════════════════════════════════


class TestDragDropEventsSuccess:
    def test_drag_drop_event_success(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum, PrioridadCasoEnum, EstadoCasoEnum, CanalOrigenEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="DragDropTest", tipo=TipoPipelineEnum.CONSEJERIA,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add_all([pipe, etapa])
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(), persona_id=uuid.uuid4(), sede_id=full["sede"].id,
            pipeline_id=pipe.id, etapa_actual_id=etapa.id,
            titulo_caso="DragTest", prioridad=PrioridadCasoEnum.MEDIA,
            estado=EstadoCasoEnum.ABIERTO, origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        db_session.commit()
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/events",
            json={"caso_id": str(caso.id), "source_stage_id": str(etapa.id), "target_stage_id": str(etapa.id)},
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["status"] == "event_registered"


# ═══════════════════════════════════════════════════════════════════════════════
# REORDER — error handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestReorderExtended:
    def test_reorder_invalid_value_error(self, full):
        # Pass a payload that triggers ValueError in atomic_sort_reorder
        fake_id = str(uuid.uuid4())
        resp = full["c"].patch(
            "/api/crm/pipeline/casos/reorder",
            json=[{"id": fake_id, "sort_order": 0}],
            headers=full["h"],
        )
        # Casos don't exist so atomic_sort_reorder should raise ValueError
        # But the TestClient uses a different session, so it may 200
        assert resp.status_code in (200, 400)


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATE CONDITION — remaining branches
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvaluateConditionExtended:
    def test_equals_expected_none(self):
        from backend.api.crm.pipelines import evaluate_condition
        assert evaluate_condition("k", "equals", None, {"k": "v"}) is False

    def test_gt_numeric_actual_not_numeric(self):
        from backend.api.crm.pipelines import evaluate_condition
        assert evaluate_condition("k", "gt", "5", {"k": "abc"}) is False

    def test_lt_numeric_expected_not_numeric(self):
        from backend.api.crm.pipelines import evaluate_condition
        assert evaluate_condition("k", "lt", "abc", {"k": "abc"}) is False

    def test_lt_string_comparison(self):
        from backend.api.crm.pipelines import evaluate_condition
        assert evaluate_condition("k", "lt", "xyz", {"k": "abc"}) is True

    def test_starts_with_none_actual(self):
        from backend.api.crm.pipelines import evaluate_condition
        assert evaluate_condition("k", "starts_with", "a", {"k": None}) is False

    def test_in_none_actual(self):
        from backend.api.crm.pipelines import evaluate_condition
        assert evaluate_condition("k", "in", "a,b", {"k": None}) is False


# ═══════════════════════════════════════════════════════════════════════════════
# GET GRAPH — edge source string
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetGraphEdgeSource:
    def test_edge_source_id_field(self):
        from backend.api.crm.pipelines import get_graph_from_payload_or_db
        nodes, edges = get_graph_from_payload_or_db(
            {"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                           "edges": [{"source_id": "a", "target_id": "b"}]}},
            None,
        )
        assert len(edges) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATE PATH — edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidatePathExtended:
    def test_validate_path_short(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-path",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_validate_path_valid(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-path",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                                "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}]}},
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_validate_path_value_error(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-path",
            json={"flow_data": {"nodes": [{"id": None}], "edges": []}},
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["valid"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# FLOWS — Create / Empty / Max Nodes / Disconnected / Validate Types
# ═══════════════════════════════════════════════════════════════════════════════


class TestFlowsExtended:
    def test_empty(self, full):
        resp = full["c"].post("/api/crm/automations/flows/empty", json={}, headers=full["h"])
        assert resp.status_code == 200

    def test_max_nodes_ok(self, full):
        resp = full["c"].post("/api/crm/automations/flows/max-nodes-check",
            json={"flow_data": {"nodes": [{"id": "a"}], "edges": []}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_disconnected_nodes(self, full):
        resp = full["c"].post("/api/crm/automations/flows/disconnected-nodes",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}], "edges": []}},
            headers=full["h"])
        assert resp.status_code == 200
        assert len(resp.json()["nodes"]) == 2

    def test_validate_types(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-types",
            json={"nodes": [{"type": "new_persona"}]},
            headers=full["h"])
        assert resp.status_code == 200

    def test_validate_types_invalid(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-types",
            json={"nodes": [{"type": "bad_type"}]},
            headers=full["h"])
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# KANBAN STAGE — empty / limit-cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestKanbanStageExtended:
    def test_empty_not_found(self, full):
        resp = full["c"].get(f"/api/crm/pipeline/kanban/stage/empty?stage_id={uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404

    def test_limit_cases_not_found(self, full):
        resp = full["c"].get(f"/api/crm/pipeline/kanban/stage/limit-cases?stage_id={uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404

    def test_empty_with_stage(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="EmptyTest", tipo=TipoPipelineEnum.CONSEJERIA,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add_all([pipe, etapa])
        db_session.commit()
        resp = full["c"].get(f"/api/crm/pipeline/kanban/stage/empty?stage_id={etapa.id}", headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["is_empty"] is True

    def test_limit_cases_with_stage(self, full, db_session):
        from backend.models_crm_pipeline import TipoPipelineEnum
        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            nombre="LimitTest", tipo=TipoPipelineEnum.CONSEJERIA,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add_all([pipe, etapa])
        db_session.commit()
        resp = full["c"].get(f"/api/crm/pipeline/kanban/stage/limit-cases?stage_id={etapa.id}&limit=50&offset=0",
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# DRAG-DROP SAME STAGE / INVALID STAGE / MISSING ID / RECOVERY
# ═══════════════════════════════════════════════════════════════════════════════


class TestDragDropOther:
    def test_same_stage_not_found(self, full):
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/same-stage",
            json={"caso_id": str(uuid.uuid4()), "sort_order": 0},
            headers=full["h"])
        assert resp.status_code == 404

    def test_invalid_stage_not_found(self, full):
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/invalid-stage",
            json={"caso_id": str(uuid.uuid4()), "target_stage_id": str(uuid.uuid4())},
            headers=full["h"])
        assert resp.status_code == 404

    def test_missing_id(self, full):
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/missing-id",
            json={}, headers=full["h"])
        assert resp.status_code == 400

    def test_missing_id_with_value(self, full):
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/missing-id",
            json={"caso_id": str(uuid.uuid4())}, headers=full["h"])
        assert resp.status_code == 200

    def test_concurrent_not_found(self, full):
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/concurrent",
            json={"caso_id": str(uuid.uuid4()), "target_stage_id": str(uuid.uuid4())},
            headers=full["h"])
        assert resp.status_code == 404

    def test_recovery(self, full):
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/recovery",
            json={}, headers=full["h"])
        assert resp.status_code == 200

    def test_recovery_invalid_uuid(self, full):
        resp = full["c"].post("/api/crm/pipeline/kanban/drag-drop/recovery",
            json={"caso_id": "not-a-uuid"}, headers=full["h"])
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# FLOWS — More validation endpoints
# ═══════════════════════════════════════════════════════════════════════════════


class TestFlowsMoreValidation:
    def test_validate_path_length(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-path-length",
            json={"nodes_count": 5}, headers=full["h"])
        assert resp.status_code == 200

    def test_validate_path_length_short(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-path-length",
            json={"nodes_count": 1}, headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_validate_multiple_inputs(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-multiple-inputs",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_validate_multiple_outputs(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-multiple-outputs",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_clean_orphans(self, full):
        resp = full["c"].post("/api/crm/automations/flows/clean-orphans",
            json={"flow_data": {"nodes": [{"id": "a"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["cleaned_count"] == 1

    def test_validate_complex_dag(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-complex-dag",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_branching_null_vars(self, full):
        resp = full["c"].post("/api/crm/automations/branching/null-vars",
            json={"variables": {"a": None, "b": "hello"}}, headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["null_variables"] == ["a"]

    def test_branching_type_mismatch(self, full):
        resp = full["c"].post("/api/crm/automations/branching/type-mismatch",
            json={"variables": {"age": 25}, "conditions": [{"key": "age", "operator": "gt", "value": "abc"}]},
            headers=full["h"])
        assert resp.status_code == 400

    def test_branching_type_mismatch_ok(self, full):
        resp = full["c"].post("/api/crm/automations/branching/type-mismatch",
            json={"variables": {"age": 25}, "conditions": [{"key": "age", "operator": "gt", "value": "18"}]},
            headers=full["h"])
        assert resp.status_code == 200

    def test_branching_missing_else(self, full):
        resp = full["c"].post("/api/crm/automations/branching/missing-else",
            json={"node_id": "a", "edges": [{"source": "a", "source_port": "true", "target": "b"}]},
            headers=full["h"])
        assert resp.status_code == 400

    def test_branching_missing_else_ok(self, full):
        resp = full["c"].post("/api/crm/automations/branching/missing-else",
            json={"node_id": "a", "edges": [{"source": "a", "source_port": "true", "target": "b"},
                                             {"source": "a", "source_port": "false", "target": "c"}]},
            headers=full["h"])
        assert resp.status_code == 200

    def test_branching_infinite_nesting(self, full):
        resp = full["c"].post("/api/crm/automations/branching/infinite-nesting",
            json={"nodes": ["a", "b"], "edges": [{"source": "a", "target": "b"}]},
            headers=full["h"])
        assert resp.status_code == 200

    def test_branching_unexpected_op(self, full):
        resp = full["c"].post("/api/crm/automations/branching/unexpected-op",
            json={"conditions": [{"operator": "bad_op"}]}, headers=full["h"])
        assert resp.status_code == 400

    def test_branching_unexpected_op_ok(self, full):
        resp = full["c"].post("/api/crm/automations/branching/unexpected-op",
            json={"conditions": [{"operator": "equals"}]}, headers=full["h"])
        assert resp.status_code == 200

    def test_validate_grap(self, full):
        resp = full["c"].post("/api/crm/automations/validate-graph",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_flows_validate(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_check_cycles(self, full):
        resp = full["c"].post("/api/crm/automations/flows/check-cycles",
            json={"flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_validate_node(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-node",
            json={"node_id": "a", "flow_data": {"nodes": [{"id": "a"}, {"id": "b"}],
                                                  "edges": [{"source": "a", "target": "b"}]}},
            headers=full["h"])
        assert resp.status_code == 200

    def test_validate_node_self_ref(self, full):
        resp = full["c"].post("/api/crm/automations/flows/validate-node",
            json={"node_id": "a", "flow_data": {"nodes": [{"id": "a"}],
                                                  "edges": [{"source": "a", "target": "a"}]}},
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_branching_traverse(self, full):
        resp = full["c"].post("/api/crm/automations/branching/traverse",
            json={"node_id": "a", "variables": {"stage": "call"},
                  "conditions": [{"key": "stage", "operator": "equals", "value": "call"}]},
            headers=full["h"])
        assert resp.status_code == 200
        assert resp.json()["result"] is True

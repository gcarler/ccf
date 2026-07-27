"""
Extended tests for backend.api.crm.pipelines — pure logic functions + API.
"""
from __future__ import annotations

import uuid

import pytest

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
    admin, _, _ = _seed_admin(db_session, email="pipe_ext@test.com")
    headers = _auth_headers(client, email="pipe_ext@test.com", password="testpass123")
    return {"c": client, "h": headers}


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

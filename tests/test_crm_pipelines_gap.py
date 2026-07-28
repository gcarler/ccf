"""
CRM Pipelines API Coverage Tests — targets the uncovered regions in pipelines.py.

Covers:
- Pipeline CRUD via API (lines 81-147)
- Stage CRUD via API (lines 150-218)
- Kanban layout/stages (lines 274-299)
- Drag-drop events (lines 258-272)
- Reorder casos (lines 227-250)
- Automation flows (lines 35-54, 400+)
"""
import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="pipeline@test.com")
    headers = _auth_headers(client, email="pipeline@test.com", password="testpass123")
    return {"c": client, "h": headers}


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE CRUD
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipelineCRUD:
    def test_list_pipelines(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/pipelines", headers=h)
        assert _ok(resp.status_code)

    def test_create_pipeline(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipelines",
            json={
                "name": "Test Pipeline",
                "pipeline_type": "CONSEJERIA",
                "description": "Test description",
                "is_active": True,
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"
        body = resp.json()
        assert body["name"] == "Test Pipeline"
        assert body["pipeline_type"] == "CONSEJERIA"

    def test_get_pipeline(self, full):
        c, h = full["c"], full["h"]
        # Create first
        resp = c.post(
            "/api/crm/pipelines",
            json={"name": "Get Me", "pipeline_type": "CONSEJERIA"},
            headers=h,
        )
        assert _ok(resp.status_code)
        pid = resp.json()["id"]
        # Get
        resp = c.get(f"/api/crm/pipelines/{pid}", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["name"] == "Get Me"

    def test_update_pipeline(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipelines",
            json={"name": "Original", "pipeline_type": "CONSEJERIA"},
            headers=h,
        )
        assert _ok(resp.status_code)
        pid = resp.json()["id"]
        resp = c.put(
            f"/api/crm/pipelines/{pid}",
            json={"name": "Updated", "pipeline_type": "RETENCION"},
            headers=h,
        )
        assert _ok(resp.status_code)
        assert resp.json()["name"] == "Updated"

    def test_delete_pipeline(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipelines",
            json={"name": "Delete Me", "pipeline_type": "CONSEJERIA"},
            headers=h,
        )
        assert _ok(resp.status_code)
        pid = resp.json()["id"]
        resp = c.delete(f"/api/crm/pipelines/{pid}", headers=h)
        assert resp.status_code == 204

    def test_get_pipeline_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/crm/pipelines/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE CRUD
# ═══════════════════════════════════════════════════════════════════════════════


class TestStageCRUD:
    def test_list_stages(self, full):
        c, h = full["c"], full["h"]
        # Create pipeline first
        resp = c.post(
            "/api/crm/pipelines",
            json={"name": "Stage Pipeline", "pipeline_type": "CONSEJERIA"},
            headers=h,
        )
        assert _ok(resp.status_code)
        pid = resp.json()["id"]
        # List stages
        resp = c.get(f"/api/crm/pipelines/{pid}/stages", headers=h)
        assert _ok(resp.status_code)

    def test_create_stage(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipelines",
            json={"name": "Stage Pipeline", "pipeline_type": "CONSEJERIA"},
            headers=h,
        )
        assert _ok(resp.status_code)
        pid = resp.json()["id"]
        resp = c.post(
            f"/api/crm/pipelines/{pid}/stages",
            json={"name": "New Stage", "order_index": 1, "requires_action": False},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_stage: {resp.status_code} {resp.text}"
        assert resp.json()["name"] == "New Stage"

    def test_update_stage(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipelines",
            json={"name": "Stage Pipeline", "pipeline_type": "CONSEJERIA"},
            headers=h,
        )
        assert _ok(resp.status_code)
        pid = resp.json()["id"]
        resp = c.post(
            f"/api/crm/pipelines/{pid}/stages",
            json={"name": "Original Stage", "order_index": 1},
            headers=h,
        )
        assert _ok(resp.status_code)
        sid = resp.json()["id"]
        resp = c.put(
            f"/api/crm/pipeline-stages/{sid}",
            json={"name": "Updated Stage", "order_index": 2},
            headers=h,
        )
        assert _ok(resp.status_code)
        assert resp.json()["name"] == "Updated Stage"

    def test_delete_stage(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipelines",
            json={"name": "Stage Pipeline", "pipeline_type": "CONSEJERIA"},
            headers=h,
        )
        assert _ok(resp.status_code)
        pid = resp.json()["id"]
        resp = c.post(
            f"/api/crm/pipelines/{pid}/stages",
            json={"name": "Delete Stage", "order_index": 1},
            headers=h,
        )
        assert _ok(resp.status_code)
        sid = resp.json()["id"]
        resp = c.delete(f"/api/crm/pipeline-stages/{sid}", headers=h)
        assert resp.status_code == 204

    def test_update_stage_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(
            f"/api/crm/pipeline-stages/{uuid.uuid4()}",
            json={"name": "X", "order_index": 1},
            headers=h,
        )
        assert resp.status_code == 404

    def test_delete_stage_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/crm/pipeline-stages/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# KANBAN
# ═══════════════════════════════════════════════════════════════════════════════


class TestKanban:
    def test_kanban_layout(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/pipeline/kanban/layout", headers=h)
        assert _ok(resp.status_code)

    def test_kanban_stages(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/pipeline/kanban/stages", headers=h)
        assert _ok(resp.status_code)

    def test_kanban_columns(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/pipeline/kanban/columns", headers=h)
        assert _ok(resp.status_code)

    def test_kanban_cards(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/pipeline/kanban/cards", headers=h)
        assert _ok(resp.status_code)

    def test_kanban_filter(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/pipeline/kanban/filter", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# REORDER
# ═══════════════════════════════════════════════════════════════════════════════


class TestReorder:
    def test_reorder_casos_empty(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(
            "/api/crm/pipeline/casos/reorder",
            json=[],
            headers=h,
        )
        assert _ok(resp.status_code)

    def test_reorder_casos_duplicate_ids_400(self, full):
        c, h = full["c"], full["h"]
        fake_id = str(uuid.uuid4())
        resp = c.patch(
            "/api/crm/pipeline/casos/reorder",
            json=[{"id": fake_id, "sort_order": 1}, {"id": fake_id, "sort_order": 2}],
            headers=h,
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# DRAG-DROP
# ═══════════════════════════════════════════════════════════════════════════════


class TestDragDrop:
    def test_drag_drop_event(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipeline/kanban/drag-drop",
            json={
                "caso_id": str(uuid.uuid4()),
                "source_stage_id": str(uuid.uuid4()),
                "target_stage_id": str(uuid.uuid4()),
            },
            headers=h,
        )
        # May succeed or 404 depending on whether caso exists
        assert resp.status_code in (200, 404)

    def test_move_stage(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/pipeline/kanban/move-stage",
            json={
                "caso_id": str(uuid.uuid4()),
                "target_stage_id": str(uuid.uuid4()),
            },
            headers=h,
        )
        assert resp.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOMATION FLOWS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAutomationFlows:
    def test_automations_palette(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/automations/palette", headers=h)
        assert _ok(resp.status_code)

    def test_create_flow(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/automations/flows",
            json={
                "name": "Test Flow",
                "trigger_type": "stage_change",
                "is_active": True,
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_flow: {resp.status_code} {resp.text}"

    def test_validate_flow_path(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/crm/automations/flows/validate-path",
            json={"path": []},
            headers=h,
        )
        assert _ok(resp.status_code)

    def test_branching_variables(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/automations/branching/variables", headers=h)
        assert _ok(resp.status_code)

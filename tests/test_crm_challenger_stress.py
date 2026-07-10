import uuid
from datetime import datetime, timezone, timedelta
import pytest
from backend import models
from backend.models_crm_pipeline import CasoCRM, EtapaPipeline, PipelineCRM, CrmReorderLock
from tests.conftest import auth_headers, seed_admin, seed_user_with_role
from tests.test_crm_visual import _seed_test_data

def test_concurrency_same_stage_bypass_reorder_lock(client, db_session):
    """
    Critique/Challenge: Same-stage reordering bypasses the CRM reorder locks.
    If a stage is locked (e.g., during cross-stage drag-drop), same-stage reordering
    ignores this lock and can proceed, potentially causing index corruption or race conditions.
    """
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)

    # Manually lock the stage by adding an entry in CrmReorderLock
    lock = CrmReorderLock(stage_id=etapa1.id)
    db_session.add(lock)
    db_session.commit()

    # Reorder payload for same-stage reorder
    payload = {
        "caso_id": str(caso1.id),
        "sort_order": 10
    }

    # Verify that same-stage reordering ignores the CrmReorderLock and returns 200
    response = client.post("/api/crm/pipeline/kanban/drag-drop/same-stage", json=payload, headers=headers)
    assert response.status_code == 200

    db_session.refresh(caso1)
    assert caso1.sort_order == 10


def test_lock_recovery_boundary_exactly_ten_seconds(client, db_session):
    """
    Verify boundary behavior: lock created exactly 10 seconds ago should be considered stale and cleared.
    """
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)

    # Lock created exactly 10 seconds ago
    lock_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    lock = CrmReorderLock(stage_id=etapa1.id, locked_at=lock_time)
    db_session.add(lock)
    db_session.commit()

    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": str(etapa2.id)
    }

    response = client.post("/api/crm/pipeline/kanban/drag-drop/concurrent", json=payload, headers=headers)
    assert response.status_code == 200

    db_session.refresh(caso1)
    assert caso1.etapa_actual_id == etapa2.id

    # Verify lock was deleted
    assert db_session.query(CrmReorderLock).filter(CrmReorderLock.stage_id == etapa1.id).count() == 0


def test_cycle_detection_multiple_subgraph_isolated_cycles(client):
    """
    Boundary case: check cycle detection when the graph has multiple disconnected components,
    each containing a cycle (e.g., n1<->n2 and n3<->n4).
    """
    payload = {
        "nodes": ["n1", "n2", "n3", "n4", "n5"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n1"},
            {"source": "n3", "target": "n4"},
            {"source": "n4", "target": "n3"},
        ]
    }
    response = client.post("/api/crm/automations/flows/check-cycles", json=payload)
    assert response.status_code == 200
    cycles = response.json()["cycles"]
    # Should detect both cycles
    assert len(cycles) >= 2


def test_branching_traverse_missing_and_mismatched_types(client):
    """
    Boundary case: branching traverse with missing variables, null values, or unexpected operators.
    """
    # 1. Missing variable in conditions
    payload = {
        "variables": {"nombre": "Juan"},
        "conditions": [{"key": "nonexistent", "operator": "equals", "value": "Juan"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.status_code == 200
    assert response.json()["result"] is False

    # 2. Unexpected operator
    payload = {
        "variables": {"sort_order": 5},
        "conditions": [{"key": "sort_order", "operator": "unknown_op", "value": "5"}]
    }
    response = client.post("/api/crm/automations/branching/traverse", json=payload)
    assert response.status_code == 200
    assert response.json()["result"] is False


def test_sede_isolation_on_invalid_transition(client, db_session):
    """
    Critique/Challenge: Verify that the system prevents moving a case to a stage belonging
    to a pipeline of a different Sede, preserving tenant isolation.
    """
    admin_a, persona_a, sede_a, pipeline_a, etapa1_a, etapa2_a, caso1_a, caso2_a = _seed_test_data(db_session)
    
    # Create another Sede and pipeline
    sede_b = models.Sede(id=uuid.uuid4(), nombre="Sede B", ciudad="Ciudad B")
    db_session.add(sede_b)
    db_session.flush()

    pipeline_b = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede_b.id,
        nombre="Pipeline B",
        tipo="CONSEJERIA",
        activo=True
    )
    db_session.add(pipeline_b)
    db_session.flush()

    etapa_b = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline_b.id,
        nombre="Etapa B",
        orden=1
    )
    db_session.add(etapa_b)
    db_session.commit()

    headers_a = auth_headers(client, email=admin_a.email)

    # Attempt to transition Caso A (Sede A) to Etapa B (Sede B)
    payload = {
        "caso_id": str(caso1_a.id),
        "target_stage_id": str(etapa_b.id)
    }

    # Should be rejected with 400 since stage B doesn't belong to Sede A or pipeline A
    response = client.post("/api/crm/pipeline/kanban/drag-drop/invalid-stage", json=payload, headers=headers_a)
    assert response.status_code == 400
    assert "Invalid stage transition" in response.json()["detail"]

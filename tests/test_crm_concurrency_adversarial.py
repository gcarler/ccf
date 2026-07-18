import uuid
from datetime import datetime, timezone, timedelta
import pytest
from backend import models
from backend.models_crm_pipeline import CasoCRM, EtapaPipeline, PipelineCRM, CrmReorderLock
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

def _seed_test_data(db_session):
    admin, persona, sede = seed_admin(db_session)
    
    pipeline = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline Test",
        tipo="NUEVOS_VISITANTES",
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
        origen_canal="WEB_FORM",
        sort_order=1
    )
    caso2 = CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa1.id,
        titulo_caso="Caso 2",
        origen_canal="WEB_FORM",
        sort_order=2
    )
    db_session.add_all([caso1, caso2])
    db_session.commit()
    return admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2


def _crm_admin_headers(client, db_session, email: str = "automation-admin@example.com"):
    admin, _, _ = seed_admin(db_session, email=email, password="testpass123")
    return auth_headers(client, email=admin.email)

# ==============================================================================
# CONCURRENCY & LOCKS
# ==============================================================================

def test_concurrent_drag_drop_stage_locked(client, db_session):
    """Test that a drag-and-drop move fails (409) if the stage is locked."""
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)

    # Manually acquire lock on stage1 (etapa1.id)
    lock = CrmReorderLock(stage_id=etapa1.id)
    db_session.add(lock)
    db_session.commit()

    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": str(etapa2.id)
    }
    
    # Try to drag-drop and check that it's blocked with a 409
    response = client.post("/api/crm/pipeline/kanban/drag-drop/concurrent", json=payload, headers=headers)
    assert response.status_code == 409
    assert "Stage is locked for concurrent reordering" in response.json()["detail"]

    # Verify that stage transition didn't happen
    db_session.refresh(caso1)
    assert caso1.etapa_actual_id == etapa1.id


def test_concurrent_drag_drop_lock_recovery(client, db_session):
    """Test lock recovery: a stale lock (>10s) is automatically cleared on drag-drop."""
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)

    # Manually create a stale lock (locked 15 seconds ago)
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=15)
    lock = CrmReorderLock(stage_id=etapa1.id, locked_at=stale_time)
    db_session.add(lock)
    db_session.commit()

    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": str(etapa2.id)
    }

    # Drag-drop should clear the stale lock and succeed
    response = client.post("/api/crm/pipeline/kanban/drag-drop/concurrent", json=payload, headers=headers)
    assert response.status_code == 200

    db_session.refresh(caso1)
    assert caso1.etapa_actual_id == etapa2.id

    # Verify that the lock table no longer has the stale lock
    remaining_locks = db_session.query(CrmReorderLock).filter(CrmReorderLock.stage_id == etapa1.id).all()
    assert len(remaining_locks) == 0


def test_lock_recovery_endpoint_stale_lock(client, db_session):
    """Test lock recovery endpoint directly clears stale locks."""
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)

    # Manually create a stale lock
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=15)
    lock = CrmReorderLock(stage_id=etapa1.id, locked_at=stale_time)
    db_session.add(lock)
    db_session.commit()

    payload = {
        "caso_id": str(caso1.id)
    }

    response = client.post("/api/crm/pipeline/kanban/drag-drop/recovery", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "recovered"

    # Lock table should be cleared
    remaining_locks = db_session.query(CrmReorderLock).filter(CrmReorderLock.stage_id == etapa1.id).all()
    assert len(remaining_locks) == 0


# ==============================================================================
# INVALID STAGE TRANSITIONS & SEDE ISOLATION
# ==============================================================================

def test_drag_drop_nonexistent_stage(client, db_session):
    """Test moving case to non-existent stage ID is rejected."""
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)

    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": str(uuid.uuid4())
    }

    response = client.post("/api/crm/pipeline/kanban/drag-drop/invalid-stage", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Invalid stage transition" in response.json()["detail"]


def test_drag_drop_stage_different_pipeline(client, db_session):
    """Test moving case to a stage belonging to a different pipeline is rejected."""
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)

    # Create another pipeline
    pipeline2 = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline Test 2",
        tipo="CONSEJERIA",
        activo=True
    )
    db_session.add(pipeline2)
    db_session.flush()

    # Stage of pipeline 2
    etapa_diff = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline2.id,
        nombre="Etapa Diff",
        orden=1
    )
    db_session.add(etapa_diff)
    db_session.commit()

    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": str(etapa_diff.id)
    }

    response = client.post("/api/crm/pipeline/kanban/drag-drop/invalid-stage", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Invalid stage transition" in response.json()["detail"]


def test_drag_drop_stage_different_sede_tenant(client, db_session):
    """Test moving case to a stage belonging to a pipeline of a different Sede/tenant is rejected."""
    admin_a, persona_a, sede_a, pipeline_a, etapa1_a, etapa2_a, caso1_a, caso2_a = _seed_test_data(db_session)
    
    # Create user B in a different Sede
    user_b, persona_b, sede_b = seed_user_with_role(db_session, role_name="ADMIN", email="admin_b@example.com", sede_id=uuid.uuid4())
    headers_b = auth_headers(client, email=user_b.email)

    # Try to drag-drop Case A (from Sede A) using credentials of User B (Sede B)
    payload = {
        "caso_id": str(caso1_a.id),
        "target_stage_id": str(etapa2_a.id)
    }

    # Should fail as Case A is not found or not accessible (404) for User B
    response = client.post("/api/crm/pipeline/kanban/drag-drop/concurrent", json=payload, headers=headers_b)
    assert response.status_code == 404
    assert "Caso no encontrado" in response.json()["detail"]


# ==============================================================================
# AUTOMATION FLOW CYCLES & LOOP DETECTION
# ==============================================================================

def test_cycle_detection_self_loop(client, db_session):
    """Check self loop (n1 -> n1) cycle detection."""
    headers = _crm_admin_headers(client, db_session)
    payload = {
        "nodes": ["n1"],
        "edges": [{"source": "n1", "target": "n1"}]
    }
    response = client.post("/api/crm/automations/flows/check-cycles", json=payload, headers=headers)
    assert response.status_code == 200
    cycles = response.json()["cycles"]
    assert len(cycles) > 0
    assert "n1" in cycles[0]


def test_cycle_detection_disconnected_subgraph_cycle(client, db_session):
    """Check cycle detection in disconnected subgraphs."""
    headers = _crm_admin_headers(client, db_session, email="automation-admin-2@example.com")
    payload = {
        "nodes": ["n1", "n2", "n3", "n4"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n3", "target": "n4"},
            {"source": "n4", "target": "n3"} # Cycle here
        ]
    }
    response = client.post("/api/crm/automations/flows/check-cycles", json=payload, headers=headers)
    assert response.status_code == 200
    cycles = response.json()["cycles"]
    assert len(cycles) > 0
    assert "n3" in cycles[0]
    assert "n4" in cycles[0]


def test_validate_graph_endpoint_rejects_cycle(client, db_session):
    """Test validate-graph endpoint returns valid=False for a cyclic graph."""
    headers = _crm_admin_headers(client, db_session, email="automation-admin-3@example.com")
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n1"}
        ]
    }
    response = client.post("/api/crm/automations/validate-graph", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "cycle detected" in data["error"]


def test_validate_path_insufficient_nodes(client, db_session):
    """Test path validation fails if path has less than 3 nodes."""
    headers = _crm_admin_headers(client, db_session, email="automation-admin-4@example.com")
    payload = {
        "nodes": ["n1", "n2"],
        "edges": [{"source": "n1", "target": "n2"}]
    }
    response = client.post("/api/crm/automations/flows/validate-path", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "at least 3 nodes" in response.json()["error"]

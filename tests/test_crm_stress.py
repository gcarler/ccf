import uuid
import pytest
from backend.core.database import Base
from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum
from tests.conftest import auth_headers, seed_admin
from tests.test_crm_visual import _seed_test_data

def _seed_massive_data(db_session, num_cases=500):
    admin, persona, sede = seed_admin(db_session)
    
    pipeline = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Massive Pipeline",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        activo=True
    )
    db_session.add(pipeline)
    db_session.flush()
    
    etapa = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="Etapa Massive",
        orden=1
    )
    db_session.add(etapa)
    db_session.flush()
    
    cases = []
    for i in range(num_cases):
        caso = CasoCRM(
            id=uuid.uuid4(),
            persona_id=persona.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso=f"Caso Massive {i}",
            origen_canal=CanalOrigenEnum.WEB_FORM,
            sort_order=i
        )
        cases.append(caso)
    
    db_session.add_all(cases)
    db_session.commit()
    return admin, pipeline, etapa, cases

def test_stress_reorder_massive_payload(client, db_session):
    # Test performance and correctness under large payload (500 cases)
    admin, pipeline, etapa, cases = _seed_massive_data(db_session, num_cases=500)
    headers = auth_headers(client, email=admin.email)
    
    # Reverse the order of all cases
    payload = [{"id": str(c.id), "sort_order": 500 - idx} for idx, c in enumerate(cases)]
    
    import time
    start_time = time.time()
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    print(f"\n[Massive Payload Stress] Time taken for 500 items reorder: {elapsed:.4f}s")
    
    # Refresh and check first and last
    db_session.refresh(cases[0])
    db_session.refresh(cases[-1])
    assert cases[0].sort_order == 500
    assert cases[-1].sort_order == 1

def test_stress_nonexistent_ids_error_message(client, db_session):
    # Verify how the system handles non-existent IDs
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    
    non_existent_id = str(uuid.uuid4())
    payload = [{"id": non_existent_id, "sort_order": 5}]
    
    # Reordering a non-existent ID should return 400/404, but let's check the error message
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code in (400, 404)
    data = response.json()
    print(f"\n[Error Handling] Non-existent ID detail: {data.get('detail')}")
    # Note: It raises "Sede isolation violation: some cases do not belong to user's Sede." instead of "Some case IDs do not exist."

def test_stress_null_sort_order_backfill(client, db_session):
    # Demonstrate that null sort order cannot even be committed/flushed to the DB
    # due to the NOT NULL constraint on crm_casos.sort_order, rendering handle_null_sort_order dead code.
    from sqlalchemy.exc import IntegrityError
    
    admin, pipeline, etapa, cases = _seed_massive_data(db_session, num_cases=5)
    
    # Attempting to assign None to sort_order and flushing/committing triggers IntegrityError
    cases[1].sort_order = None
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "NOT NULL constraint failed" in str(exc_info.value) or "null value in column" in str(exc_info.value)
    print(f"\n[Null Resolution Bug Verified] Confirmed that handle_null_sort_order is unreachable because the DB schema enforces nullable=False: {exc_info.value}")


def test_stress_stable_sorting_tiebreaker(client, db_session):
    # Verify that tie-breaker resolves duplicate indexes based on UUID string order,
    # causing arbitrary sorting order (UUID dependency) rather than user-intended position
    admin, pipeline, etapa, cases = _seed_massive_data(db_session, num_cases=3)
    # Assign same sort_order to all three cases
    for c in cases:
        c.sort_order = 5
    db_session.commit()
    
    headers = auth_headers(client, email=admin.email)
    # Send a request to trigger duplicate resolution
    payload = [{"id": str(cases[0].id), "sort_order": 5}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 200
    
    for c in cases:
        db_session.refresh(c)
    
    # Assert they are resolved to consecutive index 0, 1, 2
    resolved_orders = [c.sort_order for c in cases]
    assert sorted(resolved_orders) == [0, 1, 2]
    
    # Verify they were sorted by UUID order in the db
    sorted_by_uuid = sorted(cases, key=lambda c: (c.sort_order, c.id))
    # Since they are in database, the final sort_order must match the index of the UUID sorting
    sorted_cases = sorted(cases, key=lambda c: c.id)
    for idx, c in enumerate(sorted_cases):
        assert c.sort_order == idx
    print(f"\n[Tie-breaker UUID Bias] Verified that duplicate sort orders are resolved solely by UUID order: "
          f"{[(str(c.id)[:8], c.sort_order) for c in sorted_cases]}")

def test_stress_transaction_rollback_and_lock_states(client, db_session):
    # Test that when a reorder fails, the transaction rolls back successfully,
    # locks are released, and all changes (including lock and failure flags) are reverted.
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    
    # Store initial sort orders
    orig_order_1 = caso1.sort_order
    orig_order_2 = caso2.sort_order
    
    # Send a payload containing negative sort order, which should fail validation inside CasoCRM.atomic_sort_reorder
    payload = [{"id": str(caso1.id), "sort_order": -10}, {"id": str(caso2.id), "sort_order": 5}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 400
    
    db_session.refresh(caso1)
    db_session.refresh(caso2)
    
    # Verify rollback: sort orders should not have changed
    assert caso1.sort_order == orig_order_1
    assert caso2.sort_order == orig_order_2
    
    # Verify failure flags and lock release
    assert caso1.is_locked_for_reorder is False
    assert caso1.last_reorder_failed is False
    assert caso2.is_locked_for_reorder is False
    assert caso2.last_reorder_failed is False
    print("\n[Rollback & Flags] Verified that failed transaction rolls back sort orders and reverts all changes")


def test_stress_recursion_depth_limit(db_session):
    from backend.services.automation_engine import AutomationEngine
    from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction
    from backend.models_shared import _utcnow
    from tests.test_crm_visual import _seed_test_data
    import uuid as _uuid

    # Seed basic admin / persona / database elements to have a target persona
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)

    # 1. Create a chain of 150 nodes (acyclic)
    nodes = []
    for i in range(150):
        node = CrmAutomation(
            id=_uuid.uuid4(),
            name=f"Node {i}",
            trigger_event="manual",
            action_type="send_email",
            is_active=True
        )
        db_session.add(node)
        nodes.append(node)
    
    # Commit nodes to DB first so they have IDs
    db_session.flush()

    # Create edges in a chain: 0 -> 1 -> 2 -> ... -> 149
    edges = []
    for i in range(149):
        edge = CrmAutomationEdge(
            id=_uuid.uuid4(),
            source_id=nodes[i].id,
            target_id=nodes[i+1].id
        )
        db_session.add(edge)
        edges.append(edge)
    
    # Create a pending action on the start node (node 0)
    action = PendingCrmAction(
        id=_uuid.uuid4(),
        automation_id=nodes[0].id,
        target_persona_id=persona.id,
        execute_at=_utcnow(),
        status="pending"
    )
    db_session.add(action)
    db_session.commit()

    # Run the engine processor
    engine = AutomationEngine()
    engine._process_crm_pending_actions(db_session)
    db_session.commit()

    # Refresh the action and verify it succeeded (or executed), and not failed
    db_session.refresh(action)
    assert action.status == "executed"

    # 2. Add an edge from 149 back to 0 to form a cycle
    cycle_edge = CrmAutomationEdge(
        id=_uuid.uuid4(),
        source_id=nodes[-1].id,
        target_id=nodes[0].id
    )
    db_session.add(cycle_edge)

    # Reset action status to pending to test again
    action.status = "pending"
    action.execute_at = _utcnow()
    db_session.commit()

    # Run the engine processor again
    engine._process_crm_pending_actions(db_session)
    db_session.commit()

    # Refresh the action and verify it failed due to cycle detection
    db_session.refresh(action)
    assert action.status == "failed"


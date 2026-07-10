import uuid
import pytest
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.dialects.postgresql import ARRAY

# Patch ARRAY for SQLite
_orig_array_bind = ARRAY.bind_processor
def patched_array_bind(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                return json.dumps(value)
            return str(value)
        return process
    return _orig_array_bind(self, dialect)
ARRAY.bind_processor = patched_array_bind

_orig_array_result = ARRAY.result_processor
def patched_array_result(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return []
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return [value]
            return value
        return process
    return _orig_array_result(self, dialect, coltype)
ARRAY.result_processor = patched_array_result

from backend.core.database import Base
from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum, CrmReorderLock
from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction
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

# Adversarial Test 1: Cross-Pipeline Stage Reorder Leak within Same Sede
def test_reorder_cross_pipeline_leak_within_same_sede(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    
    # Create Pipeline A
    pipeline_a = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline A",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        activo=True
    )
    # Create Pipeline B
    pipeline_b = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline B",
        tipo=TipoPipelineEnum.CONSEJERIA,
        activo=True
    )
    db_session.add_all([pipeline_a, pipeline_b])
    db_session.flush()
    
    etapa_a = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline_a.id,
        nombre="Etapa A",
        orden=1
    )
    etapa_b = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline_b.id,
        nombre="Etapa B",
        orden=1
    )
    db_session.add_all([etapa_a, etapa_b])
    db_session.flush()
    
    caso = CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline_a.id,
        etapa_actual_id=etapa_a.id,
        titulo_caso="Caso A",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        sort_order=1
    )
    db_session.add(caso)
    db_session.commit()
    
    headers = auth_headers(client, email=admin.email)
    payload = [{"id": str(caso.id), "etapa_actual_id": str(etapa_b.id)}]
    
    # Call the API to reorder
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 400
    
    db_session.refresh(caso)
    # Case stage must not be updated to a different pipeline's stage
    assert caso.etapa_actual_id == etapa_a.id
    assert caso.pipeline_id == pipeline_a.id


# Adversarial Test 2: Validate Empty Graph Fallback to DB Cycles
def test_validate_empty_graph_fallback_to_db_cycles(client, db_session):
    # Seed a cyclic automation in the database
    auto1 = CrmAutomation(id=uuid.uuid4(), name="Auto 1", trigger_event="birthday", action_type="send_email", is_active=True)
    auto2 = CrmAutomation(id=uuid.uuid4(), name="Auto 2", trigger_event="birthday", action_type="send_email", is_active=True)
    db_session.add_all([auto1, auto2])
    db_session.flush()
    
    edge1 = CrmAutomationEdge(id=uuid.uuid4(), source_id=auto1.id, target_id=auto2.id)
    edge2 = CrmAutomationEdge(id=uuid.uuid4(), source_id=auto2.id, target_id=auto1.id)
    db_session.add_all([edge1, edge2])
    db_session.commit()
    
    payload = {"flow_data": {"nodes": [], "edges": []}}
    response = client.post("/api/crm/automations/flows/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Should be valid and not fall back to database
    assert data["valid"] is True
    assert data.get("error") is None


# Adversarial Test 3: Empty string cycle on malformed node IDs
def test_malformed_node_ids_empty_string_cycle(client):
    payload = {
        "nodes": [
            {"name": "Missing ID Node 1"},
            {"name": "Missing ID Node 2"}
        ],
        "edges": [
            {"source": "", "target": ""}
        ]
    }
    response = client.post("/api/crm/automations/flows/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "missing" in data["error"].lower() or "malformed" in data["error"].lower()


# Adversarial Test 4: Long path false cycle detection
def test_long_path_false_cycle_detection(db_session):
    from backend.services.automation_engine import engine
    from backend.models_crm import Persona
    
    persona = Persona(id=uuid.uuid4(), first_name="Juan", last_name="Test", email="test@example.com")
    db_session.add(persona)
    db_session.flush()
    
    # Create 905 sequential nodes with no cycles
    nodes = []
    for i in range(905):
        nodes.append(CrmAutomation(id=uuid.uuid4(), name=f"Auto {i}", trigger_event="stage_change", action_type="send_email", is_active=True))
    db_session.add_all(nodes)
    db_session.flush()
    
    for i in range(904):
        db_session.add(CrmAutomationEdge(id=uuid.uuid4(), source_id=nodes[i].id, target_id=nodes[i+1].id))
    db_session.flush()
    
    action = PendingCrmAction(
        automation_id=nodes[0].id,
        target_persona_id=persona.id,
        execute_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        status="pending"
    )
    db_session.add(action)
    db_session.flush()  # Use flush instead of commit to keep the session transaction active
    
    engine._process_crm_pending_actions(db_session)
    db_session.commit()
    
    db_session.refresh(action)
    assert action.status == "executed"


# Adversarial Test 5: Infinite nesting stack overflow on long acyclic paths
def test_infinite_nesting_stack_overflow(client):
    nodes = [f"n{i}" for i in range(1500)]
    edges = [{"source": f"n{i}", "target": f"n{i+1}"} for i in range(1499)]
    
    payload = {"nodes": nodes, "edges": edges}
    
    response = client.post("/api/crm/automations/branching/infinite-nesting", json=payload)
    assert response.status_code == 400
    assert "depth" in response.json()["detail"].lower()


# Adversarial Test 6: Lack of Atomicity in atomic_reorder_branching_eval
def test_atomic_reorder_branching_eval_lacks_atomicity(db_session, monkeypatch):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    caso1_id = caso1.id
    etapa2_id = etapa2.id
    sede_id = sede.id
    
    automation = CrmAutomation(
        name="Stage Change Evaluation Auto",
        trigger_event="stage_change",
        action_type="send_email",
        delay_minutes=10,
        is_active=True
    )
    db_session.add(automation)
    db_session.commit()
    
    assert caso1.etapa_actual_id == etapa1.id
    
    payload = [
        {"id": str(caso1_id), "sort_order": 1, "drag_target_etapa_id": str(etapa2_id)}
    ]
    
    original_add = db_session.add
    def mock_add(instance):
        if isinstance(instance, PendingCrmAction):
            raise Exception("Simulated DB error during pending action insertion")
        original_add(instance)
        
    monkeypatch.setattr(db_session, "add", mock_add)
    
    with pytest.raises(Exception, match="Simulated DB error during pending action insertion"):
        CasoCRM.atomic_reorder_branching_eval(db_session, payload, sede_id)
        
    etapa1_id = etapa1.id
    db_session.rollback()
    db_session.close()
    
    # Verify the rollback occurred and no partial commit exists
    from tests.conftest import TestingSessionLocal
    new_db = TestingSessionLocal()
    try:
        updated_case = new_db.query(CasoCRM).filter(CasoCRM.id == caso1_id).one()
        assert updated_case.etapa_actual_id == etapa1_id
        
        actions = new_db.query(PendingCrmAction).all()
        assert len(actions) == 0
    finally:
        new_db.close()


# Adversarial Test 7: Concurrency lock cleanup deletes other locks
def test_concurrent_lock_release_deletes_other_locks(client, db_session, monkeypatch):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    headers = auth_headers(client, email=admin.email)
    
    original_commit = db_session.commit
    
    def mock_commit():
        # Inject another lock on the source stage concurrently
        lock = CrmReorderLock(stage_id=etapa1.id)
        db_session.add(lock)
        original_commit()
        
    monkeypatch.setattr(db_session, "commit", mock_commit)
    
    payload = {
        "caso_id": str(caso1.id),
        "target_stage_id": str(etapa2.id)
    }
    response = client.post("/api/crm/pipeline/kanban/drag-drop/concurrent", json=payload, headers=headers)
    assert response.status_code == 200
    
    # The other concurrent lock must not be deleted
    db_session.commit()
    locks = db_session.query(CrmReorderLock).filter(CrmReorderLock.stage_id == etapa1.id).all()
    assert len(locks) == 1


# Adversarial Test 8: Discrepancy in evaluate_condition case sensitivity between API and background engine
def test_evaluate_condition_case_sensitivity_discrepancy(client, db_session):
    from backend.api.crm.pipelines import evaluate_condition as evaluate_condition_api

    # 1. API evaluates contains case-insensitively now: "nombre" contains "juan" for "Juan" is True
    res_api = evaluate_condition_api("nombre", "contains", "juan", {"nombre": "Juan"})
    assert res_api is True, "API condition evaluation contains should be case-insensitive, expected True"

    # 2. Let's test the background engine behavior using actual pending action with a case-insensitive check
    from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction, Persona
    from backend.services.automation_engine import engine
    
    # Seed persona with first_name="Juan" and email
    persona = Persona(id=uuid.uuid4(), first_name="Juan", last_name="Test", email="juan@example.com")
    db_session.add(persona)
    db_session.flush()
    
    auto1 = CrmAutomation(id=uuid.uuid4(), name="Auto 1", trigger_event="stage_change", action_type="send_email", delay_minutes=0, is_active=True)
    auto2 = CrmAutomation(id=uuid.uuid4(), name="Auto 2", trigger_event="stage_change", action_type="send_email", delay_minutes=0, is_active=True)
    db_session.add_all([auto1, auto2])
    db_session.flush()
    
    # Create edge with condition: first_name contains "juan" (lowercase).
    # Since actual first_name is "Juan", it should match in the background engine because it uses .lower()!
    edge = CrmAutomationEdge(
        id=uuid.uuid4(),
        source_id=auto1.id,
        target_id=auto2.id,
        condition_type="contains",
        condition_key="first_name",
        condition_value="juan"
    )
    db_session.add(edge)
    
    action = PendingCrmAction(
        id=uuid.uuid4(),
        automation_id=auto1.id,
        target_persona_id=persona.id,
        execute_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        status="pending"
    )
    db_session.add(action)
    db_session.commit()
    
    engine._process_crm_pending_actions(db_session)
    db_session.commit()
    
    # If the background engine successfully matched the case-insensitive condition, it would queue the next action (for auto2)
    next_actions = db_session.query(PendingCrmAction).filter(
        PendingCrmAction.automation_id == auto2.id,
        PendingCrmAction.target_persona_id == persona.id
    ).all()
    
    # Background engine successfully matched "Juan" with "juan" (contains) case-insensitively, so next action is queued!
    assert len(next_actions) == 1


# Adversarial Test 9: Exception leakage in enviar_plantilla endpoint
def test_enviar_plantilla_exception_leakage(client, db_session, monkeypatch):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    
    from backend.models_crm import CategoriaRecurso, PlantillaMensaje, CanalEnvio
    
    cat = CategoriaRecurso(id=uuid.uuid4(), nombre="Adv Cat", activo=True)
    db_session.add(cat)
    db_session.flush()
    
    plantilla = PlantillaMensaje(
        id=uuid.uuid4(),
        sede_id=sede.id,
        categoria_id=cat.id,
        titulo="Adv Template",
        canal=CanalEnvio.WHATSAPP,
        contenido_texto="Hello {{name}}",
        creado_por_id=persona.id,
        activo=True
    )
    db_session.add(plantilla)
    db_session.commit()
    
    from backend.services.messaging import MessagingGateway
    
    # Mock send_whatsapp to raise a RuntimeError (not ValueError)
    async def mock_send_whatsapp(self, db, persona_id, content, leader_id, campaign_name=None, external_id=None):
        raise RuntimeError("SMTP/Network service completely down")
        
    monkeypatch.setattr(MessagingGateway, "send_whatsapp", mock_send_whatsapp)
    
    headers = auth_headers(client, email=admin.email)
    payload = {
        "destinatario_id": str(persona.id),
        "caso_id": str(caso1.id),
        "variables": {"name": "Juan"}
    }
    
    # Call endpoint: it should log as FALLIDO and return 201
    response = client.post(f"/api/crm/resources/plantillas/{plantilla.id}/enviar", json=payload, headers=headers)
    assert response.status_code == 201
    
    # Verify a BitacoraEnvioPlantilla record is created and marked as FALLIDO
    from backend.models_crm import BitacoraEnvioPlantilla
    logs = db_session.query(BitacoraEnvioPlantilla).filter(BitacoraEnvioPlantilla.plantilla_id == plantilla.id).all()
    assert len(logs) == 1
    assert logs[0].estado.value == "FALLIDO" if hasattr(logs[0].estado, "value") else logs[0].estado == "FALLIDO"


# Adversarial Test 10: Background engine silently simulates action execution without sending anything
def test_background_engine_simulated_actions(db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, caso1, caso2 = _seed_test_data(db_session)
    
    # Create automation flow: stage_change -> send_email
    automation = CrmAutomation(
        id=uuid.uuid4(),
        name="Adv Automation",
        trigger_event="stage_change",
        action_type="send_email",
        action_payload={"plantilla_id": str(uuid.uuid4()), "canal": "email"},
        delay_minutes=0,
        is_active=True
    )
    db_session.add(automation)
    db_session.flush()
    
    # Queue pending action
    action = PendingCrmAction(
        id=uuid.uuid4(),
        automation_id=automation.id,
        target_persona_id=persona.id,
        execute_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        status="pending"
    )
    db_session.add(action)
    db_session.commit()
    
    # Run the background engine loop
    from backend.services.automation_engine import engine
    engine._process_crm_pending_actions(db_session)
    db_session.commit()
    
    db_session.refresh(action)
    assert action.status == "executed"
    
    # Ensure messaging gateway is called and communication logs are created
    from backend.models_crm import BitacoraEnvioPlantilla, CommunicationLog
    bitacora_logs = db_session.query(BitacoraEnvioPlantilla).filter(BitacoraEnvioPlantilla.caso_id == caso1.id).all()
    assert len(bitacora_logs) == 1, "Should have one plantilla transmission logged"
    
    comms_logs = db_session.query(CommunicationLog).filter(CommunicationLog.persona_id == persona.id).all()
    assert len(comms_logs) == 1, "Should have one messaging gateway transmission logged"


# Adversarial Test 11: KeyError in branching infinite-nesting due to missing source node in nodes list
def test_infinite_nesting_missing_source_keyerror(client):
    payload = {
        "nodes": ["n1"],
        "edges": [{"source": "n2", "target": "n1"}]
    }
    response = client.post("/api/crm/automations/branching/infinite-nesting", json=payload)
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


# Adversarial Test 12: Sede Isolation Breach in Template Operations
def test_cross_sede_template_access_isolation_breach(client, db_session):
    from tests.conftest import seed_user_with_role
    from backend.models_crm import PlantillaMensaje, CategoriaRecurso, CanalEnvio
    
    admin_a, persona_a, sede_a = seed_admin(db_session)
    user_b, persona_b, sede_b = seed_user_with_role(db_session, role_name="ADMIN", email="admin_b@example.com", sede_id=uuid.uuid4())
    
    # Create CategoriaRecurso
    cat = CategoriaRecurso(id=uuid.uuid4(), nombre="Cat A", activo=True)
    db_session.add(cat)
    db_session.flush()
    
    # Create Template in Sede A
    plantilla = PlantillaMensaje(
        id=uuid.uuid4(),
        sede_id=sede_a.id,
        categoria_id=cat.id,
        titulo="Template A",
        canal=CanalEnvio.EMAIL,
        contenido_texto="Hello {{nombre}}",
        variables_requeridas=["nombre"],
        activo=True
    )
    db_session.add(plantilla)
    db_session.commit()
    
    # Authenticate as User B (Sede B)
    headers_b = auth_headers(client, email=user_b.email)
    
    # User B should receive 403 Forbidden when trying to access Sede A's template
    response = client.get(f"/api/crm/resources/plantillas/{plantilla.id}", headers=headers_b)
    assert response.status_code == 403

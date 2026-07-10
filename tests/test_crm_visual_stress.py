import uuid
import pytest
import json
from datetime import datetime, timezone
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


from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

def _seed_test_data_for_stress(db_session, num_cases=5):
    admin, persona, sede = seed_admin(db_session)
    
    pipeline = PipelineCRM(
        id=uuid.uuid4(),
        sede_id=sede.id,
        nombre="Pipeline Stress",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        activo=True
    )
    db_session.add(pipeline)
    db_session.flush()
    
    etapa1 = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="Etapa Stress 1",
        orden=1
    )
    etapa2 = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="Etapa Stress 2",
        orden=2
    )
    db_session.add_all([etapa1, etapa2])
    db_session.flush()
    
    cases = []
    for i in range(num_cases):
        caso = CasoCRM(
            id=uuid.uuid4(),
            persona_id=persona.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa1.id,
            titulo_caso=f"Caso Stress {i}",
            origen_canal=CanalOrigenEnum.WEB_FORM,
            sort_order=i
        )
        cases.append(caso)
        db_session.add(caso)
    db_session.commit()
    return admin, persona, sede, pipeline, etapa1, etapa2, cases


# 1. Test extreme sort order values (e.g. huge, negative)
def test_reorder_extreme_values(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, cases = _seed_test_data_for_stress(db_session, 2)
    headers = auth_headers(client, email=admin.email)
    
    # Negative sort indices are not allowed (returns 400 Bad Request)
    payload_neg = [{"id": str(cases[0].id), "sort_order": -5}]
    response_neg = client.patch("/api/crm/pipeline/casos/reorder", json=payload_neg, headers=headers)
    assert response_neg.status_code == 400
    
    # Huge sort indices are allowed
    payload_huge = [{"id": str(cases[0].id), "sort_order": 9999999}]
    response_huge = client.patch("/api/crm/pipeline/casos/reorder", json=payload_huge, headers=headers)
    assert response_huge.status_code == 200
    
    db_session.refresh(cases[0])
    assert cases[0].sort_order == 9999999


# 2. Test large batch reorder (e.g. 50 items)
def test_reorder_large_batch(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, cases = _seed_test_data_for_stress(db_session, 50)
    headers = auth_headers(client, email=admin.email)
    
    payload = []
    for idx, c in enumerate(cases):
        payload.append({"id": str(c.id), "sort_order": 100 - idx})
        
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 200
    
    for c in cases:
        db_session.refresh(c)
    
    # Ensure they are reordered
    sorted_cases = sorted(cases, key=lambda x: x.sort_order)
    assert sorted_cases[0].id == cases[-1].id  # The last case now has sort_order 50, which is smallest (100 - 50 = 50 vs 100 - 0 = 100)


# 3. Test cross-sede isolation reorder leak prevention
def test_reorder_cross_sede_leak_prevention(client, db_session):
    admin_a, persona_a, sede_a, pipeline_a, etapa1_a, etapa2_a, cases_a = _seed_test_data_for_stress(db_session, 2)
    
    # Create user B in Sede B
    user_b, persona_b, sede_b = seed_user_with_role(db_session, role_name="ADMIN", email="admin_b_stress@example.com", sede_id=uuid.uuid4())
    headers_b = auth_headers(client, email=user_b.email)
    
    # Sede B user tries to reorder cases from Sede A
    payload = [{"id": str(cases_a[0].id), "sort_order": 10}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers_b)
    # Should fail with 400 Bad Request because cases do not belong to user B's sede
    assert response.status_code == 400
    assert "sede isolation violation" in response.json()["detail"].lower()


# 4. Test reorder to non-existent target stage
def test_reorder_missing_etapa(client, db_session):
    admin, persona, sede, pipeline, etapa1, etapa2, cases = _seed_test_data_for_stress(db_session, 2)
    headers = auth_headers(client, email=admin.email)
    
    payload = [{"id": str(cases[0].id), "etapa_actual_id": str(uuid.uuid4())}]
    response = client.patch("/api/crm/pipeline/casos/reorder", json=payload, headers=headers)
    assert response.status_code == 400
    assert "sede isolation violation" in response.json()["detail"].lower() or "stage not found" in response.json()["detail"].lower()


# 5. Test flow validator with a massive graph
def test_validate_extreme_nodes_edges(client):
    nodes = []
    edges = []
    # Create a complex graph of 100 nodes and 100 edges
    for i in range(100):
        nodes.append({"id": f"node_{i}", "name": f"Node {i}"})
    for i in range(99):
        edges.append({"id": f"edge_{i}", "source": f"node_{i}", "target": f"node_{i+1}"})
        
    payload = {"flow_data": {"nodes": nodes, "edges": edges}}
    response = client.post("/api/crm/automations/flows/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True


# 6. Test flow validator with highly cyclic graph
def test_validate_highly_cyclic_graph(client):
    nodes = [{"id": "n1", "name": "N1"}, {"id": "n2", "name": "N2"}, {"id": "n3", "name": "N3"}]
    # n1 -> n2 -> n3 -> n1
    edges = [
        {"id": "e1", "source": "n1", "target": "n2"},
        {"id": "e2", "source": "n2", "target": "n3"},
        {"id": "e3", "source": "n3", "target": "n1"}
    ]
    payload = {"flow_data": {"nodes": nodes, "edges": edges}}
    response = client.post("/api/crm/automations/flows/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "cycl" in response.json()["error"].lower() or "loop" in response.json()["error"].lower()


# 7. Test infinite nesting stack overflow on extreme depth
def test_infinite_nesting_massive_depth(client):
    # depth of 2500
    nodes = [f"n{i}" for i in range(2500)]
    edges = [{"source": f"n{i}", "target": f"n{i+1}"} for i in range(2499)]
    payload = {"nodes": nodes, "edges": edges}
    response = client.post("/api/crm/automations/branching/infinite-nesting", json=payload)
    assert response.status_code == 400
    assert "depth" in response.json()["detail"].lower()


# 8. Test cross-sede resource template deletion rejection
def test_cross_sede_template_deletion(client, db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session)
    user_b, persona_b, sede_b = seed_user_with_role(db_session, role_name="ADMIN", email="admin_b_del_stress@example.com", sede_id=uuid.uuid4())
    
    from backend.models_crm import PlantillaMensaje, CategoriaRecurso, CanalEnvio
    
    cat = CategoriaRecurso(id=uuid.uuid4(), nombre="Cat A Stress", activo=True)
    db_session.add(cat)
    db_session.flush()
    
    plantilla = PlantillaMensaje(
        id=uuid.uuid4(),
        sede_id=sede_a.id,
        categoria_id=cat.id,
        titulo="Template A Stress",
        canal=CanalEnvio.EMAIL,
        contenido_texto="Hello {{nombre}}",
        variables_requeridas=["nombre"],
        activo=True
    )
    db_session.add(plantilla)
    db_session.commit()
    
    headers_b = auth_headers(client, email=user_b.email)
    response = client.delete(f"/api/crm/resources/plantillas/{plantilla.id}", headers=headers_b)
    # Should reject with 403 Forbidden
    assert response.status_code == 403

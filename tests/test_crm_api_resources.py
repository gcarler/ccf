"""API tests for backend.api.crm.resources (categories, templates, adjuntos)."""

from __future__ import annotations

import uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, sede = _seed_admin(db_session, email="res@test.com")
    headers = _auth_headers(client, email="res@test.com", password="testpass123")
    return {"c": client, "h": headers, "sede": sede}


class TestCategorias:
    def test_list(self, full):
        resp = full["c"].get("/api/crm/resources/categorias", headers=full["h"])
        assert _ok(resp.status_code)

    def test_create(self, full):
        name = f"Cat-{uuid.uuid4().hex[:6]}"
        resp = full["c"].post("/api/crm/resources/categorias",
            json={"nombre": name}, headers=full["h"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == name
        assert data["activo"] is True

    def test_update(self, full):
        name = f"Cat-{uuid.uuid4().hex[:6]}"
        r = full["c"].post("/api/crm/resources/categorias",
            json={"nombre": name}, headers=full["h"])
        cat_id = r.json()["id"]
        new_name = f"{name}-upd"
        resp = full["c"].patch(f"/api/crm/resources/categorias/{cat_id}",
            json={"nombre": new_name}, headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()["nombre"] == new_name

    def test_update_not_found(self, full):
        resp = full["c"].patch(f"/api/crm/resources/categorias/{uuid.uuid4()}",
            json={"nombre": "Nope"}, headers=full["h"])
        assert resp.status_code == 404

    def test_delete(self, full):
        name = f"Cat-{uuid.uuid4().hex[:6]}"
        r = full["c"].post("/api/crm/resources/categorias",
            json={"nombre": name}, headers=full["h"])
        cat_id = r.json()["id"]
        resp = full["c"].delete(f"/api/crm/resources/categorias/{cat_id}", headers=full["h"])
        assert resp.status_code == 204

    def test_delete_not_found(self, full):
        resp = full["c"].delete(f"/api/crm/resources/categorias/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404


class TestPlantillas:
    def test_list(self, full):
        resp = full["c"].get("/api/crm/resources/plantillas", headers=full["h"])
        assert _ok(resp.status_code)

    def test_create(self, full, db_session):
        cat = models.CategoriaRecurso(id=uuid.uuid4(), nombre=f"Cat-{uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()
        resp = full["c"].post("/api/crm/resources/plantillas",
            json={
                "categoria_id": str(cat.id),
                "titulo": "Test Plantilla",
                "canal": "WHATSAPP",
                "contenido_texto": "Hola {{nombre}}",
            },
            headers=full["h"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["titulo"] == "Test Plantilla"
        assert data["canal"] == "WHATSAPP"

    def test_get_one(self, full, db_session):
        cat = models.CategoriaRecurso(id=uuid.uuid4(), nombre=f"Cat-{uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()
        r = full["c"].post("/api/crm/resources/plantillas",
            json={
                "categoria_id": str(cat.id),
                "titulo": "Get Test",
                "canal": "EMAIL",
                "contenido_texto": "Test body",
            },
            headers=full["h"])
        pid = r.json()["id"]
        resp = full["c"].get(f"/api/crm/resources/plantillas/{pid}", headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()["titulo"] == "Get Test"

    def test_get_one_not_found(self, full):
        resp = full["c"].get(f"/api/crm/resources/plantillas/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404

    def test_update(self, full, db_session):
        cat = models.CategoriaRecurso(id=uuid.uuid4(), nombre=f"Cat-{uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()
        r = full["c"].post("/api/crm/resources/plantillas",
            json={
                "categoria_id": str(cat.id),
                "titulo": "Update Test",
                "canal": "SMS",
                "contenido_texto": "Original",
            },
            headers=full["h"])
        pid = r.json()["id"]
        resp = full["c"].patch(f"/api/crm/resources/plantillas/{pid}",
            json={"titulo": "Updated Title"}, headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()["titulo"] == "Updated Title"

    def test_update_not_found(self, full):
        resp = full["c"].patch(f"/api/crm/resources/plantillas/{uuid.uuid4()}",
            json={"titulo": "Nope"}, headers=full["h"])
        assert resp.status_code == 404

    def test_delete(self, full, db_session):
        cat = models.CategoriaRecurso(id=uuid.uuid4(), nombre=f"Cat-{uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()
        r = full["c"].post("/api/crm/resources/plantillas",
            json={
                "categoria_id": str(cat.id),
                "titulo": "Delete Test",
                "canal": "WHATSAPP",
                "contenido_texto": "To be deleted",
            },
            headers=full["h"])
        pid = r.json()["id"]
        resp = full["c"].delete(f"/api/crm/resources/plantillas/{pid}", headers=full["h"])
        assert resp.status_code == 204

    def test_delete_not_found(self, full):
        resp = full["c"].delete(f"/api/crm/resources/plantillas/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404


class TestAdjuntos:
    def test_list(self, full, db_session):
        cat = models.CategoriaRecurso(id=uuid.uuid4(), nombre=f"Cat-{uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()
        r = full["c"].post("/api/crm/resources/plantillas",
            json={
                "categoria_id": str(cat.id),
                "titulo": "Adj Test",
                "canal": "EMAIL",
                "contenido_texto": "Body",
            },
            headers=full["h"])
        pid = r.json()["id"]
        resp = full["c"].get(f"/api/crm/resources/plantillas/{pid}/adjuntos", headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json() == []

    def test_list_plantilla_not_found(self, full):
        resp = full["c"].get(f"/api/crm/resources/plantillas/{uuid.uuid4()}/adjuntos", headers=full["h"])
        assert resp.status_code == 404

    def test_delete_adjunto(self, full, db_session):
        plantilla = models.PlantillaMensaje(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            categoria_id=uuid.uuid4(), titulo="AdjDel",
            canal="WHATSAPP", contenido_texto="Body",
        )
        db_session.add(plantilla)
        adj = models.RecursoAdjunto(
            id=uuid.uuid4(), sede_id=full["sede"].id,
            plantilla_id=plantilla.id, nombre_recurso="test",
            seaweed_fid=None, url_acceso="http://example.com",
            nombre_archivo="test.txt", tipo_mime="text/plain",
            peso_bytes=100, activo=True,
        )
        db_session.add(adj)
        db_session.commit()
        resp = full["c"].delete(f"/api/crm/resources/adjuntos/{adj.id}", headers=full["h"])
        assert resp.status_code == 204

    def test_delete_adjunto_not_found(self, full):
        resp = full["c"].delete(f"/api/crm/resources/adjuntos/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404


class TestBitacora:
    def test_list_sede(self, full):
        resp = full["c"].get("/api/crm/resources/bitacora", headers=full["h"])
        assert _ok(resp.status_code)

    def test_list_plantilla(self, full, db_session):
        cat = models.CategoriaRecurso(id=uuid.uuid4(), nombre=f"Cat-{uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()
        r = full["c"].post("/api/crm/resources/plantillas",
            json={
                "categoria_id": str(cat.id),
                "titulo": "Bitacora Plant",
                "canal": "EMAIL",
                "contenido_texto": "Body",
            },
            headers=full["h"])
        pid = r.json()["id"]
        resp = full["c"].get(f"/api/crm/resources/plantillas/{pid}/bitacora", headers=full["h"])
        assert _ok(resp.status_code)

    def test_list_plantilla_not_found(self, full):
        resp = full["c"].get(f"/api/crm/resources/plantillas/{uuid.uuid4()}/bitacora", headers=full["h"])
        assert resp.status_code == 404


class TestSystemTemplates:
    def test_list(self, full):
        resp = full["c"].get("/api/crm/resources/system-templates", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert "categorias" in data
        assert "plantillas" in data

    def test_apply_system_template(self, full):
        resp = full["c"].get("/api/crm/resources/system-templates", headers=full["h"])
        templates = resp.json()["plantillas"]
        if not templates:
            pytest.skip("No system templates available")
        tid = templates[0]["id"]
        resp = full["c"].post("/api/crm/resources/system-templates/apply",
            json={"template_id": tid}, headers=full["h"])
        assert resp.status_code == 201


class TestAutomations:
    def test_list(self, full):
        resp = full["c"].get("/api/crm/resources/automations", headers=full["h"])
        assert _ok(resp.status_code)

    def test_create(self, full):
        resp = full["c"].post("/api/crm/resources/automations",
            json={
                "name": "Test Auto",
                "trigger_event": "persona.created",
                "action_type": "send_plantilla",
                "action_payload": {"plantilla_id": str(uuid.uuid4())},
            },
            headers=full["h"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Auto"

    def test_get_one(self, full):
        r = full["c"].post("/api/crm/resources/automations",
            json={"name": "Get Auto", "trigger_event": "persona.created", "action_type": "notify"},
            headers=full["h"])
        aid = r.json()["id"]
        resp = full["c"].get(f"/api/crm/resources/automations/{aid}", headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()["name"] == "Get Auto"

    def test_get_one_not_found(self, full):
        resp = full["c"].get(f"/api/crm/resources/automations/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404

    def test_update(self, full):
        r = full["c"].post("/api/crm/resources/automations",
            json={"name": "Upd Auto", "trigger_event": "persona.created", "action_type": "notify"},
            headers=full["h"])
        aid = r.json()["id"]
        resp = full["c"].patch(f"/api/crm/resources/automations/{aid}",
            json={"name": "Updated Auto"}, headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()["name"] == "Updated Auto"

    def test_update_not_found(self, full):
        resp = full["c"].patch(f"/api/crm/resources/automations/{uuid.uuid4()}",
            json={"name": "Nope"}, headers=full["h"])
        assert resp.status_code == 404

    def test_delete(self, full):
        r = full["c"].post("/api/crm/resources/automations",
            json={"name": "Del Auto", "trigger_event": "persona.created", "action_type": "notify"},
            headers=full["h"])
        aid = r.json()["id"]
        resp = full["c"].delete(f"/api/crm/resources/automations/{aid}", headers=full["h"])
        assert resp.status_code == 204

    def test_delete_not_found(self, full):
        resp = full["c"].delete(f"/api/crm/resources/automations/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404

    def test_list_edges(self, full):
        resp = full["c"].get("/api/crm/resources/automation-edges", headers=full["h"])
        assert _ok(resp.status_code)

    def test_list_edges_fallback(self, full):
        resp = full["c"].get("/api/crm/resources/automations/edges", headers=full["h"])
        assert _ok(resp.status_code)

    def test_create_edge_fallback(self, full):
        r1 = full["c"].post("/api/crm/resources/automations",
            json={"name": "SrcFb", "trigger_event": "e1", "action_type": "notify"},
            headers=full["h"])
        r2 = full["c"].post("/api/crm/resources/automations",
            json={"name": "TgtFb", "trigger_event": "e2", "action_type": "notify"},
            headers=full["h"])
        resp = full["c"].post("/api/crm/resources/automations/edges",
            json={"source_id": r1.json()["id"], "target_id": r2.json()["id"]},
            headers=full["h"])
        assert resp.status_code == 201

    def test_delete_edge_fallback(self, full):
        r1 = full["c"].post("/api/crm/resources/automations",
            json={"name": "SrcFb2", "trigger_event": "e1", "action_type": "notify"},
            headers=full["h"])
        r2 = full["c"].post("/api/crm/resources/automations",
            json={"name": "TgtFb2", "trigger_event": "e2", "action_type": "notify"},
            headers=full["h"])
        re = full["c"].post("/api/crm/resources/automations/edges",
            json={"source_id": r1.json()["id"], "target_id": r2.json()["id"]},
            headers=full["h"])
        eid = re.json()["id"]
        resp = full["c"].delete(f"/api/crm/resources/automations/edges/{eid}", headers=full["h"])
        assert resp.status_code == 204

    def test_trigger_no_automations(self, full):
        resp = full["c"].post("/api/crm/resources/automations/trigger",
            json={"trigger_event": "nonexistent.event", "context": {"persona_id": str(uuid.uuid4())}},
            headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json() == []

    def test_trigger_skipped_no_plantilla_id(self, full):
        full["c"].post("/api/crm/resources/automations",
            json={
                "name": "TriggerNoPlantilla",
                "trigger_event": "test.skip",
                "action_type": "send_plantilla",
                "action_payload": {},
            },
            headers=full["h"])
        resp = full["c"].post("/api/crm/resources/automations/trigger",
            json={"trigger_event": "test.skip", "context": {"persona_id": str(uuid.uuid4())}},
            headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()[0]["status"] == "skipped"

    def test_trigger_skipped_no_persona_id(self, full):
        full["c"].post("/api/crm/resources/automations",
            json={
                "name": "TriggerNoPersona",
                "trigger_event": "test.nop",
                "action_type": "send_plantilla",
                "action_payload": {"plantilla_id": str(uuid.uuid4())},
            },
            headers=full["h"])
        resp = full["c"].post("/api/crm/resources/automations/trigger",
            json={"trigger_event": "test.nop", "context": {}},
            headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()[0]["status"] == "skipped"

    def test_trigger_skipped_wrong_action_type(self, full):
        full["c"].post("/api/crm/resources/automations",
            json={
                "name": "TriggerWrongAction",
                "trigger_event": "test.wrong",
                "action_type": "some_unknown_action",
            },
            headers=full["h"])
        resp = full["c"].post("/api/crm/resources/automations/trigger",
            json={"trigger_event": "test.wrong", "context": {"persona_id": str(uuid.uuid4())}},
            headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()[0]["status"] == "skipped"

    def test_create_edge(self, full):
        r1 = full["c"].post("/api/crm/resources/automations",
            json={"name": "Src Auto", "trigger_event": "e1", "action_type": "notify"},
            headers=full["h"])
        r2 = full["c"].post("/api/crm/resources/automations",
            json={"name": "Tgt Auto", "trigger_event": "e2", "action_type": "notify"},
            headers=full["h"])
        resp = full["c"].post("/api/crm/resources/automation-edges",
            json={"source_id": r1.json()["id"], "target_id": r2.json()["id"]},
            headers=full["h"])
        assert resp.status_code == 201

    def test_create_edge_source_not_found(self, full):
        r2 = full["c"].post("/api/crm/resources/automations",
            json={"name": "Tgt2 Auto", "trigger_event": "e2", "action_type": "notify"},
            headers=full["h"])
        resp = full["c"].post("/api/crm/resources/automation-edges",
            json={"source_id": str(uuid.uuid4()), "target_id": r2.json()["id"]},
            headers=full["h"])
        assert resp.status_code == 404

    def test_delete_edge(self, full):
        r1 = full["c"].post("/api/crm/resources/automations",
            json={"name": "Src2 Auto", "trigger_event": "e1", "action_type": "notify"},
            headers=full["h"])
        r2 = full["c"].post("/api/crm/resources/automations",
            json={"name": "Tgt2 Auto", "trigger_event": "e2", "action_type": "notify"},
            headers=full["h"])
        re = full["c"].post("/api/crm/resources/automation-edges",
            json={"source_id": r1.json()["id"], "target_id": r2.json()["id"]},
            headers=full["h"])
        eid = re.json()["id"]
        resp = full["c"].delete(f"/api/crm/resources/automation-edges/{eid}", headers=full["h"])
        assert resp.status_code == 204

    def test_delete_edge_not_found(self, full):
        resp = full["c"].delete(f"/api/crm/resources/automation-edges/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404

    def test_list_edges_with_data(self, full):
        r1 = full["c"].post("/api/crm/resources/automations",
            json={"name": "SrcL", "trigger_event": "e1", "action_type": "notify"},
            headers=full["h"])
        r2 = full["c"].post("/api/crm/resources/automations",
            json={"name": "TgtL", "trigger_event": "e2", "action_type": "notify"},
            headers=full["h"])
        full["c"].post("/api/crm/resources/automation-edges",
            json={"source_id": r1.json()["id"], "target_id": r2.json()["id"]},
            headers=full["h"])
        resp = full["c"].get("/api/crm/resources/automation-edges", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert len(data) > 0

    def test_list_edges_with_source_filter(self, full):
        r1 = full["c"].post("/api/crm/resources/automations",
            json={"name": "SrcF", "trigger_event": "e1", "action_type": "notify"},
            headers=full["h"])
        r2 = full["c"].post("/api/crm/resources/automations",
            json={"name": "TgtF", "trigger_event": "e2", "action_type": "notify"},
            headers=full["h"])
        full["c"].post("/api/crm/resources/automation-edges",
            json={"source_id": r1.json()["id"], "target_id": r2.json()["id"]},
            headers=full["h"])
        resp = full["c"].get(f"/api/crm/resources/automation-edges?source_id={r1.json()['id']}", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert len(data) > 0

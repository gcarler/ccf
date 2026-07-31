"""API tests for backend.api.crm.pastoral — cases, tasks, messaging, counseling, etc."""

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
    admin, _, sede = _seed_admin(db_session, email="pastv2@test.com")
    headers = _auth_headers(client, email="pastv2@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": sede}


@pytest.fixture
def caso(full, db_session):
    from backend.models_crm_pipeline import CanalOrigenEnum, EstadoCasoEnum, PrioridadCasoEnum, TipoPipelineEnum

    pipe = models.PipelineCRM(
        id=uuid.uuid4(),
        sede_id=full["s"].id,
        nombre="PastTest",
        tipo=TipoPipelineEnum.CONSEJERIA,
    )
    etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
    p = models.Persona(id=uuid.uuid4(), first_name="C", last_name="P", sede_id=full["s"].id)
    db_session.add_all([pipe, etapa, p])
    db_session.commit()
    caso = models.CasoCRM(
        id=uuid.uuid4(),
        persona_id=p.id,
        sede_id=full["s"].id,
        pipeline_id=pipe.id,
        etapa_actual_id=etapa.id,
        titulo_caso="Test Case",
        prioridad=PrioridadCasoEnum.MEDIA,
        estado=EstadoCasoEnum.ABIERTO,
        origen_canal=CanalOrigenEnum.WEB_FORM,
    )
    db_session.add(caso)
    db_session.commit()
    return caso


class TestCasos:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/casos", headers=full["h"]).status_code)

    def test_list_with_case(self, full, caso):
        resp = full["c"].get("/api/crm/casos", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert data["total"] >= 1

    def test_get(self, full, caso):
        resp = full["c"].get(f"/api/crm/casos/{caso.id}", headers=full["h"])
        assert _ok(resp.status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_patch(self, full, caso):
        resp = full["c"].patch(f"/api/crm/casos/{caso.id}", json={"notes": "Updated notes"}, headers=full["h"])
        assert _ok(resp.status_code)

    def test_patch_not_found(self, full):
        assert (
            full["c"].patch(f"/api/crm/casos/{uuid.uuid4()}", json={"notes": "Nope"}, headers=full["h"]).status_code
            == 404
        )

    def test_audit(self, full, caso):
        resp = full["c"].get(f"/api/crm/casos/{caso.id}/audit", headers=full["h"])
        assert _ok(resp.status_code)

    def test_delete(self, full, caso):
        resp = full["c"].delete(f"/api/crm/casos/{caso.id}", headers=full["h"])
        assert resp.status_code == 204

    def test_calls(self, full, caso):
        resp = full["c"].get(f"/api/crm/casos/{caso.id}/calls", headers=full["h"])
        assert _ok(resp.status_code)

    def test_create_call(self, full, caso):
        resp = full["c"].post(
            f"/api/crm/casos/{caso.id}/calls", json={"outcome": "contacted", "notes": "Test call"}, headers=full["h"]
        )
        assert resp.status_code in (200, 201), resp.text


class TestCasoInteractions:
    def test_list(self, full, caso):
        resp = full["c"].get(f"/api/crm/casos/{caso.id}/interactions", headers=full["h"])
        assert _ok(resp.status_code)

    def test_list_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}/interactions", headers=full["h"]).status_code == 404

    def test_create(self, full, caso):
        resp = full["c"].post(
            f"/api/crm/casos/{caso.id}/interactions",
            json={"interaction_type": "llamada", "notes": "Interaction test"},
            headers=full["h"],
        )
        assert resp.status_code in (200, 201), resp.text

    def test_create_not_found(self, full):
        assert (
            full["c"]
            .post(
                f"/api/crm/casos/{uuid.uuid4()}/interactions",
                json={"interaction_type": "llamada", "notes": "Nope"},
                headers=full["h"],
            )
            .status_code
            == 404
        )


class TestCasoTasks:
    def test_list(self, full, caso):
        resp = full["c"].get(f"/api/crm/casos/{caso.id}/tasks", headers=full["h"])
        assert _ok(resp.status_code)

    def test_list_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}/tasks", headers=full["h"]).status_code == 404

    def test_create(self, full, caso):
        resp = full["c"].post(
            f"/api/crm/casos/{caso.id}/tasks", json={"title": "Caso Task", "status": "pending"}, headers=full["h"]
        )
        assert resp.status_code in (200, 201)

    def test_update(self, full, db_session):
        from backend.models_crm_pipeline import CanalOrigenEnum, EstadoCasoEnum, PrioridadCasoEnum, TipoPipelineEnum

        pipe = models.PipelineCRM(
            id=uuid.uuid4(), sede_id=full["s"].id, nombre="TaskUpd", tipo=TipoPipelineEnum.CONSEJERIA
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        p = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=full["s"].id)
        db_session.add_all([pipe, etapa, p])
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(),
            persona_id=p.id,
            sede_id=full["s"].id,
            pipeline_id=pipe.id,
            etapa_actual_id=etapa.id,
            titulo_caso="T",
            prioridad=PrioridadCasoEnum.MEDIA,
            estado=EstadoCasoEnum.ABIERTO,
            origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        db_session.commit()
        r = full["c"].post(
            f"/api/crm/casos/{caso.id}/tasks", json={"title": "UpdateMe", "status": "pending"}, headers=full["h"]
        )
        assert r.status_code in (200, 201), r.text
        tid = r.json()["id"]
        resp = full["c"].patch(f"/api/crm/casos/{caso.id}/tasks/{tid}", json={"status": "completed"}, headers=full["h"])
        assert _ok(resp.status_code)


class TestTasks:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/tasks", headers=full["h"]).status_code)

    def test_mine(self, full):
        assert _ok(full["c"].get("/api/crm/tasks/mine", headers=full["h"]).status_code)

    def test_create(self, full):
        resp = full["c"].post("/api/crm/tasks/", json={"title": "New Task", "status": "pending"}, headers=full["h"])
        assert resp.status_code in (200, 201), resp.text

    def test_get(self, full):
        r = full["c"].post("/api/crm/tasks/", json={"title": "GetTask", "status": "pending"}, headers=full["h"])
        assert r.status_code in (200, 201), r.text
        tid = r.json()["id"]
        resp = full["c"].get(f"/api/crm/tasks/{tid}", headers=full["h"])
        assert _ok(resp.status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_update(self, full):
        r = full["c"].post("/api/crm/tasks/", json={"title": "UpdTask", "status": "pending"}, headers=full["h"])
        assert r.status_code in (200, 201), r.text
        tid = r.json()["id"]
        resp = full["c"].patch(f"/api/crm/tasks/{tid}", json={"title": "Updated"}, headers=full["h"])
        assert _ok(resp.status_code)

    def test_delete(self, full):
        r = full["c"].post("/api/crm/tasks/", json={"title": "DelTask", "status": "pending"}, headers=full["h"])
        assert r.status_code in (200, 201), r.text
        tid = r.json()["id"]
        resp = full["c"].delete(f"/api/crm/tasks/{tid}", headers=full["h"])
        assert resp.status_code == 204


class TestMessaging:
    def test_history(self, full):
        assert _ok(full["c"].get("/api/crm/messaging/history", headers=full["h"]).status_code)


class TestSettings:
    def test_get(self, full):
        assert _ok(full["c"].get("/api/crm/settings", headers=full["h"]).status_code)

    def test_save(self, full):
        resp = full["c"].post("/api/crm/settings", json={"congregation_name": "Test"}, headers=full["h"])
        assert _ok(resp.status_code)


class TestRoles:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/roles", headers=full["h"]).status_code)

    def test_create(self, full):
        resp = full["c"].post("/api/crm/roles", json={"name": "TestRole", "color": "blue"}, headers=full["h"])
        assert resp.status_code in (200, 201), resp.text

    def test_update(self, full):
        r = full["c"].post("/api/crm/roles", json={"name": "UpdRole", "color": "blue"}, headers=full["h"])
        assert r.status_code in (200, 201), r.text
        rid = r.json()["id"]
        resp = full["c"].put(f"/api/crm/roles/{rid}", json={"name": "UpdatedRole", "color": "blue"}, headers=full["h"])
        assert _ok(resp.status_code)

    def test_delete(self, full):
        r = full["c"].post("/api/crm/roles", json={"name": "DelRole", "color": "blue"}, headers=full["h"])
        assert r.status_code in (200, 201), r.text
        rid = r.json()["id"]
        r2 = full["c"].post("/api/crm/roles", json={"name": "ReplaceRole", "color": "red"}, headers=full["h"])
        assert r2.status_code in (200, 201), r2.text
        fallback = r2.json()["id"]
        resp = full["c"].delete(f"/api/crm/roles/{rid}", params={"fallback_id": str(fallback)}, headers=full["h"])
        assert _ok(resp.status_code)


class TestCounseling:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/counseling/", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/counseling/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestPrayerRequests:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/prayer-requests", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/prayer-requests/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestGroups:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/groups", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestVolunteers:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/volunteers", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/crm/volunteers/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_create(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="V", last_name="T", sede_id=full["s"].id)
        db_session.add(p)
        db_session.commit()
        resp = full["c"].post(
            "/api/crm/volunteers",
            json={
                "name": "Vol Test",
                "role_name": "Usher",
                "persona_id": str(p.id),
                "team_name": "Greeting",
                "shift_start": "2026-07-01T08:00:00Z",
                "shift_end": "2026-07-01T12:00:00Z",
            },
            headers=full["h"],
        )
        assert resp.status_code in (200, 201), resp.text


class TestAnalytics:
    def test_summary(self, full):
        assert _ok(full["c"].get("/api/crm/analytics", headers=full["h"]).status_code)


class TestRadar:
    def test_radar(self, full):
        assert _ok(full["c"].get("/api/crm/radar", headers=full["h"]).status_code)

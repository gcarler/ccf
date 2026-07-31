"""
Extended API tests for backend.api.crm.persona_relations.
Covers remaining coverage gaps: positions update, ministries update,
crm-profile/consolidation with data, families success, departments success.
"""

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
    admin, _, _ = _seed_admin(db_session, email="pr@test.com")
    headers = _auth_headers(client, email="pr@test.com", password="testpass123")
    return {"c": client, "h": headers, "sede": db_session.query(models.Sede).first()}


class TestPositions:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/positions", headers=full["h"]).status_code)

    def test_create(self, full):
        name = f"Pos-{uuid.uuid4().hex[:6]}"
        resp = full["c"].post("/api/crm/positions", json={"name": name}, headers=full["h"])
        assert _ok(resp.status_code)
        assert resp.json()["name"] == name

    def test_create_duplicate_409(self, full):
        name = f"DP-{uuid.uuid4().hex[:6]}"
        full["c"].post("/api/crm/positions", json={"name": name}, headers=full["h"])
        resp = full["c"].post("/api/crm/positions", json={"name": name}, headers=full["h"])
        assert resp.status_code == 409

    def test_update(self, full):
        name = f"UP-{uuid.uuid4().hex[:6]}"
        r = full["c"].post("/api/crm/positions", json={"name": name}, headers=full["h"])
        pid = r.json()["id"]
        resp = full["c"].patch(f"/api/crm/positions/{pid}", json={"name": f"{name}x"}, headers=full["h"])
        assert _ok(resp.status_code)

    def test_update_not_found(self, full):
        resp = full["c"].patch(f"/api/crm/positions/{uuid.uuid4()}", json={"name": "X"}, headers=full["h"])
        assert resp.status_code == 404


class TestPersonaPositions:
    def test_list(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        assert _ok(full["c"].get(f"/api/crm/personas/{p.id}/positions", headers=full["h"]).status_code)

    def test_assign(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        r = full["c"].post("/api/crm/positions", json={"name": f"R-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
        db_session.commit()
        resp = full["c"].post(
            f"/api/crm/personas/{p.id}/positions",
            json={"persona_id": str(p.id), "position_id": r.json()["id"], "start_date": "2026-01-01"},
            headers=full["h"],
        )
        assert _ok(resp.status_code)


class TestPersonaMinistries:
    def test_list(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="M", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        assert _ok(full["c"].get(f"/api/crm/personas/{p.id}/ministries", headers=full["h"]).status_code)

    def test_assign(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="M", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        m = models.Ministry(id=uuid.uuid4(), name=f"Min-{uuid.uuid4().hex[:6]}")
        db_session.add(m)
        db_session.commit()
        resp = full["c"].post(
            f"/api/crm/personas/{p.id}/ministries",
            json={"persona_id": str(p.id), "ministry_id": str(m.id), "role": "leader"},
            headers=full["h"],
        )
        assert _ok(resp.status_code)


class TestCrmProfile:
    def test_get(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/personas/{p.id}/crm-perfil", headers=full["h"])
        assert _ok(resp.status_code)
        assert "persona" in resp.json()

    def test_not_found(self, full):
        assert full["c"].get(f"/api/crm/personas/{uuid.uuid4()}/crm-perfil", headers=full["h"]).status_code == 404


class TestConsolidation:
    def test_get(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="C", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/personas/{p.id}/consolidation", headers=full["h"])
        assert _ok(resp.status_code)
        assert "persona" in resp.json()

    def test_not_found(self, full):
        assert full["c"].get(f"/api/crm/personas/{uuid.uuid4()}/consolidation", headers=full["h"]).status_code == 404


class TestFamilies:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/families/", headers=full["h"]).status_code)

    def test_create(self, full):
        name = f"Fam-{uuid.uuid4().hex[:6]}"
        resp = full["c"].post("/api/crm/families/", json={"name": name}, headers=full["h"])
        assert _ok(resp.status_code) and resp.json()["name"] == name

    def test_create_no_name_400(self, full):
        assert full["c"].post("/api/crm/families/", json={}, headers=full["h"]).status_code == 400

    def test_not_found(self, full):
        assert full["c"].get(f"/api/crm/family/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestColombianData:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/crm/colombian-departments", headers=full["h"]).status_code)

    def test_cities_not_found(self, full):
        assert (
            full["c"].get(f"/api/crm/colombian-departments/{uuid.uuid4()}/cities", headers=full["h"]).status_code == 404
        )


class TestCommunications:
    def test_not_found(self, full):
        assert full["c"].get(f"/api/crm/personas/{uuid.uuid4()}/communications", headers=full["h"]).status_code == 404

    def test_with_persona(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="C", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        assert _ok(full["c"].get(f"/api/crm/personas/{p.id}/communications", headers=full["h"]).status_code)


class TestPersonaPositionsExtended:
    def test_assign_position_not_found(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="X", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        resp = full["c"].post(
            f"/api/crm/personas/{p.id}/positions",
            json={"persona_id": str(p.id), "position_id": str(uuid.uuid4()), "start_date": "2026-01-01"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_assign_existing(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="Y", sede_id=full["sede"].id)
        db_session.add(p)
        name = f"Pos-{uuid.uuid4().hex[:6]}"
        r = full["c"].post("/api/crm/positions", json={"name": name}, headers=full["h"])
        pos_id = r.json()["id"]
        db_session.commit()
        full["c"].post(
            f"/api/crm/personas/{p.id}/positions",
            json={"persona_id": str(p.id), "position_id": pos_id, "start_date": "2026-01-01"},
            headers=full["h"],
        )
        resp = full["c"].post(
            f"/api/crm/personas/{p.id}/positions",
            json={"persona_id": str(p.id), "position_id": pos_id, "start_date": "2026-01-01", "notes": "updated"},
            headers=full["h"],
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    def test_update_persona_position(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="Z", sede_id=full["sede"].id)
        db_session.add(p)
        name = f"Pos-{uuid.uuid4().hex[:6]}"
        r = full["c"].post("/api/crm/positions", json={"name": name}, headers=full["h"])
        pos_id = r.json()["id"]
        db_session.commit()
        r2 = full["c"].post(
            f"/api/crm/personas/{p.id}/positions",
            json={"persona_id": str(p.id), "position_id": pos_id, "start_date": "2026-01-01"},
            headers=full["h"],
        )
        pp_id = r2.json()["id"]
        resp = full["c"].patch(
            f"/api/crm/personas/{p.id}/positions/{pp_id}", json={"notes": "updated note"}, headers=full["h"]
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    def test_list_after_assign(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="L", sede_id=full["sede"].id)
        db_session.add(p)
        name = f"Pos-{uuid.uuid4().hex[:6]}"
        r = full["c"].post("/api/crm/positions", json={"name": name}, headers=full["h"])
        pos_id = r.json()["id"]
        db_session.commit()
        full["c"].post(
            f"/api/crm/personas/{p.id}/positions",
            json={"persona_id": str(p.id), "position_id": pos_id, "start_date": "2026-01-01"},
            headers=full["h"],
        )
        resp = full["c"].get(f"/api/crm/personas/{p.id}/positions", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert len(data) > 0
        assert data[0]["position_name"] is not None

    def test_update_persona_position_not_found(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="P", last_name="N", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        resp = full["c"].patch(
            f"/api/crm/personas/{p.id}/positions/{uuid.uuid4()}", json={"notes": "x"}, headers=full["h"]
        )
        assert resp.status_code == 404


class TestPersonaMinistriesExtended:
    def test_ministries_with_ministry(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="M", last_name="R", sede_id=full["sede"].id)
        m = models.Ministry(id=uuid.uuid4(), name=f"Min-{uuid.uuid4().hex[:6]}")
        db_session.add_all([p, m])
        db_session.commit()
        full["c"].post(
            f"/api/crm/personas/{p.id}/ministries",
            json={"persona_id": str(p.id), "ministry_id": str(m.id), "role": "leader"},
            headers=full["h"],
        )
        resp = full["c"].get(f"/api/crm/personas/{p.id}/ministries", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert len(data) > 0
        assert data[0]["ministry_name"] is not None
        assert data[0]["ministry"] is not None

    def test_assign_ministry_existing(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="M", last_name="S", sede_id=full["sede"].id)
        db_session.add(p)
        m = models.Ministry(id=uuid.uuid4(), name=f"Min-{uuid.uuid4().hex[:6]}")
        db_session.add(m)
        db_session.commit()
        full["c"].post(
            f"/api/crm/personas/{p.id}/ministries",
            json={"persona_id": str(p.id), "ministry_id": str(m.id), "role": "leader"},
            headers=full["h"],
        )
        resp = full["c"].post(
            f"/api/crm/personas/{p.id}/ministries",
            json={"persona_id": str(p.id), "ministry_id": str(m.id), "role": "updated-role"},
            headers=full["h"],
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    def test_update_ministry(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="M", last_name="U", sede_id=full["sede"].id)
        db_session.add(p)
        m = models.Ministry(id=uuid.uuid4(), name=f"Min-{uuid.uuid4().hex[:6]}")
        db_session.add(m)
        db_session.commit()
        r = full["c"].post(
            f"/api/crm/personas/{p.id}/ministries",
            json={"persona_id": str(p.id), "ministry_id": str(m.id), "role": "leader"},
            headers=full["h"],
        )
        mm_id = r.json()["id"]
        resp = full["c"].patch(
            f"/api/crm/personas/{p.id}/ministries/{mm_id}", json={"role": "coordinator"}, headers=full["h"]
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    def test_update_ministry_all_fields(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="M", last_name="F", sede_id=full["sede"].id)
        db_session.add(p)
        m = models.Ministry(id=uuid.uuid4(), name=f"Min-{uuid.uuid4().hex[:6]}")
        db_session.add(m)
        db_session.commit()
        r = full["c"].post(
            f"/api/crm/personas/{p.id}/ministries",
            json={"persona_id": str(p.id), "ministry_id": str(m.id), "role": "leader"},
            headers=full["h"],
        )
        mm_id = r.json()["id"]
        resp = full["c"].patch(
            f"/api/crm/personas/{p.id}/ministries/{mm_id}",
            json={"is_active": False, "end_date": "2026-06-01", "notes": "finished"},
            headers=full["h"],
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    def test_update_ministry_not_found(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="M", last_name="V", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        resp = full["c"].patch(
            f"/api/crm/personas/{p.id}/ministries/{uuid.uuid4()}", json={"role": "coordinator"}, headers=full["h"]
        )
        assert resp.status_code == 404


class TestCrmProfileExtended:
    def test_get_with_cases(self, full, db_session):
        from backend.models_crm_pipeline import CanalOrigenEnum, EstadoCasoEnum, PrioridadCasoEnum, TipoPipelineEnum

        p = models.Persona(id=uuid.uuid4(), first_name="C", last_name="W", sede_id=full["sede"].id)
        pipeline = models.PipelineCRM(
            id=uuid.uuid4(),
            nombre=f"Pipe-{uuid.uuid4().hex[:6]}",
            sede_id=full["sede"].id,
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipeline.id, nombre="Etapa1", orden=1)
        db_session.add_all([p, pipeline, etapa])
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(),
            persona_id=p.id,
            sede_id=full["sede"].id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso="Test",
            prioridad=PrioridadCasoEnum.MEDIA,
            estado=EstadoCasoEnum.ABIERTO,
            origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/personas/{p.id}/crm-perfil", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert len(data["cases"]) > 0


class TestConsolidationExtended:
    def test_get_with_data(self, full, db_session):
        from backend.models_crm_pipeline import CanalOrigenEnum, EstadoCasoEnum, PrioridadCasoEnum, TipoPipelineEnum

        p = models.Persona(id=uuid.uuid4(), first_name="C2", last_name="W2", sede_id=full["sede"].id)
        pipeline = models.PipelineCRM(
            id=uuid.uuid4(),
            nombre=f"Pipe-{uuid.uuid4().hex[:6]}",
            sede_id=full["sede"].id,
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        )
        etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipeline.id, nombre="E1", orden=1)
        db_session.add_all([p, pipeline, etapa])
        db_session.commit()
        caso = models.CasoCRM(
            id=uuid.uuid4(),
            persona_id=p.id,
            sede_id=full["sede"].id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso="Test",
            prioridad=PrioridadCasoEnum.MEDIA,
            estado=EstadoCasoEnum.ABIERTO,
            origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        tarea = models.TareaCRM(
            id=uuid.uuid4(),
            persona_id=p.id,
            titulo="T1",
            estado="pending",
        )
        db_session.add(tarea)
        comm = models.CommunicationLog(
            id=uuid.uuid4(),
            persona_id=p.id,
            channel="email",
            content="test",
        )
        db_session.add(comm)
        db_session.commit()
        resp = full["c"].get(f"/api/crm/personas/{p.id}/consolidation", headers=full["h"])
        assert _ok(resp.status_code)
        data = resp.json()
        assert data["summary"]["cases_count"] >= 1
        assert data["summary"]["tasks_count"] >= 1

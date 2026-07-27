"""
Extended API tests for backend.api.crm.persona_relations.
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
        resp = full["c"].post(f"/api/crm/personas/{p.id}/positions",
            json={"persona_id": str(p.id), "position_id": r.json()["id"], "start_date": "2026-01-01"},
            headers=full["h"])
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
        resp = full["c"].post(f"/api/crm/personas/{p.id}/ministries",
            json={"persona_id": str(p.id), "ministry_id": str(m.id), "role": "leader"},
            headers=full["h"])
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
        assert full["c"].get(f"/api/crm/colombian-departments/{uuid.uuid4()}/cities", headers=full["h"]).status_code == 404


class TestCommunications:
    def test_not_found(self, full):
        assert full["c"].get(f"/api/crm/personas/{uuid.uuid4()}/communications", headers=full["h"]).status_code == 404

    def test_with_persona(self, full, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="C", last_name="T", sede_id=full["sede"].id)
        db_session.add(p)
        db_session.commit()
        assert _ok(full["c"].get(f"/api/crm/personas/{p.id}/communications", headers=full["h"]).status_code)

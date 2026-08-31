"""Comprehensive tests for crm/pastoral.py — cases, tasks, interactions, messaging."""
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
    admin, _, _ = _seed_admin(db_session, email="past@test.com")
    headers = _auth_headers(client, email="past@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestCasosCRUD:
    def _create_persona(self, db_session, s):
        p = models.Persona(id=uuid.uuid4(), first_name="Past", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        return p

    def test_create_caso(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = self._create_persona(db_session, s)
        resp = c.post("/api/crm/casos",
            json={"persona_id": str(p.id), "stage": "new", "notes": "Test note"},
            headers=h)
        assert _ok(resp.status_code), f"create caso: {resp.status_code} {resp.text[:200]}"
        assert resp.json()["persona_id"] == str(p.id)

    def test_create_prospecto_creates_persona_and_case(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        resp = c.post(
            "/api/crm/casos",
            json={
                "first_name": "Prospecto",
                "last_name": "Nuevo",
                "phone": "3001234567",
                "source": "Visitante",
                "stage": "new",
                "notes": "Registro desde contactos",
                "spiritual_status": "Prospecto",
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create prospecto: {resp.status_code} {resp.text[:300]}"
        created = resp.json()
        assert created["persona_id"]
        case_response = c.get(f"/api/crm/casos/{created['id']}", headers=h)
        assert case_response.status_code == 200
        assert case_response.json()["nombre_completo"] == "Prospecto Nuevo"

        listed = c.get("/api/crm/casos", headers=h)
        assert listed.status_code == 200
        assert any(case["id"] == created["id"] for case in listed.json()["cases"])

    def test_create_prospecto_requires_identity_fields(self, full):
        resp = full["c"].post(
            "/api/crm/casos",
            json={"phone": "3007654321", "source": "Visitante"},
            headers=full["h"],
        )
        assert resp.status_code == 422

    def test_get_caso(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = self._create_persona(db_session, s)
        created = c.post("/api/crm/casos",
            json={"persona_id": str(p.id), "stage": "new"}, headers=h).json()
        resp = c.get(f"/api/crm/casos/{created['id']}", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["id"] == created["id"]

    def test_get_caso_not_found(self, full):
        assert full["c"].get(f"/api/crm/casos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_list_casos(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = self._create_persona(db_session, s)
        c.post("/api/crm/casos", json={"persona_id": str(p.id)}, headers=h)
        resp = c.get("/api/crm/casos", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["total"] >= 1

    def test_update_caso_patch(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = self._create_persona(db_session, s)
        created = c.post("/api/crm/casos",
            json={"persona_id": str(p.id), "stage": "new"}, headers=h).json()
        resp = c.patch(f"/api/crm/casos/{created['id']}",
            json={"notes": "Updated note"}, headers=h)
        assert _ok(resp.status_code)

    def test_delete_caso(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = self._create_persona(db_session, s)
        created = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)}, headers=h).json()
        resp = c.delete(f"/api/crm/casos/{created['id']}", headers=h)
        assert resp.status_code == 204

    def test_caso_audit(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = self._create_persona(db_session, s)
        created = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)}, headers=h).json()
        resp = c.get(f"/api/crm/casos/{created['id']}/audit", headers=h)
        assert _ok(resp.status_code)


class TestCasoInteractions:
    def test_create_interaction(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Int", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        caso = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)}, headers=h).json()
        resp = c.post(f"/api/crm/casos/{caso['id']}/interactions",
            json={"interaction_type": "call", "notes": "Called"},
            headers=h)
        assert _ok(resp.status_code), f"create interaction: {resp.status_code} {resp.text[:200]}"

    def test_list_interactions(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Lst", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        caso = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)}, headers=h).json()
        c.post(f"/api/crm/casos/{caso['id']}/interactions",
            json={"interaction_type": "call"}, headers=h)
        resp = c.get(f"/api/crm/casos/{caso['id']}/interactions", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["total"] >= 1


class TestCasoTaskCRUD:
    def test_create_caso_task(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Tsk", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        caso = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)}, headers=h).json()
        resp = c.post(f"/api/crm/casos/{caso['id']}/tasks",
            json={"title": "Follow up", "due_date": "2026-08-01T00:00:00Z"},
            headers=h)
        assert _ok(resp.status_code), f"create caso task: {resp.status_code} {resp.text[:200]}"

    def test_list_caso_tasks(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="LTS", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        caso = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)}, headers=h).json()
        c.post(f"/api/crm/casos/{caso['id']}/tasks",
            json={"title": "Task"}, headers=h)
        resp = c.get(f"/api/crm/casos/{caso['id']}/tasks", headers=h)
        assert _ok(resp.status_code)

    def test_update_caso_task(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="UTS", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        caso = c.post("/api/crm/casos",
            json={"persona_id": str(p.id)}, headers=h).json()
        created = c.post(f"/api/crm/casos/{caso['id']}/tasks",
            json={"title": "Old title"}, headers=h).json()
        resp = c.patch(f"/api/crm/casos/{caso['id']}/tasks/{created['id']}",
            json={"title": "New title"}, headers=h)
        assert _ok(resp.status_code)


class TestCrmTasks:
    def test_list_crm_tasks(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="CTL", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        resp = c.get("/api/crm/tasks", headers=h)
        assert _ok(resp.status_code)

    def test_create_crm_task(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="CTC", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        resp = c.post("/api/crm/tasks/",
            json={"title": "CRM Task", "description": "Desc", "persona_id": str(p.id),
                  "due_date": "2026-08-01T00:00:00Z", "category": "seguimiento"},
            headers=h)
        assert _ok(resp.status_code), f"create crm task: {resp.status_code} {resp.text[:200]}"


class TestMessaging:
    def test_messaging_history(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/messaging/history", headers=h)
        assert _ok(resp.status_code)

    def test_messaging_history_item_not_found(self, full):
        assert full["c"].get(f"/api/crm/messaging/history/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404

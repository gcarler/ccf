"""Continue covering crm/pastoral.py — remaining CRUD endpoints."""
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
    admin, _, _ = _seed_admin(db_session, email="pas2@test.com")
    headers = _auth_headers(client, email="pas2@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestTasksExtended:
    def test_tasks_mine(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="MyT", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        # Create a CRM task assigned to the current user
        resp = c.post("/api/crm/tasks/",
            json={"title": "My Task", "persona_id": str(p.id),
                  "due_date": "2026-08-01T00:00:00Z"},
            headers=h)
        assert _ok(resp.status_code)

        resp = c.get("/api/crm/tasks/mine", headers=h)
        assert _ok(resp.status_code), f"mine: {resp.status_code}"
        data = resp.json()
        assert data["total"] >= 1

    def test_task_detail(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Dtl", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        created = c.post("/api/crm/tasks/",
            json={"title": "Detail Test", "persona_id": str(p.id)}, headers=h).json()
        resp = c.get(f"/api/crm/tasks/{created['id']}", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["title"] == "Detail Test"

    def test_task_detail_not_found(self, full):
        assert full["c"].get(f"/api/crm/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_task_update(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Upd", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        created = c.post("/api/crm/tasks/",
            json={"title": "Old Title", "persona_id": str(p.id)}, headers=h).json()
        resp = c.patch(f"/api/crm/tasks/{created['id']}",
            json={"title": "New Title"}, headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["title"] == "New Title"

    def test_task_delete(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Del", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        created = c.post("/api/crm/tasks/",
            json={"title": "To Delete", "persona_id": str(p.id)}, headers=h).json()
        resp = c.delete(f"/api/crm/tasks/{created['id']}", headers=h)
        assert resp.status_code == 204

    def test_task_delete_not_found(self, full):
        assert full["c"].delete(f"/api/crm/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestMessagingHistoryItem:
    def test_get_messaging_history_item_not_found(self, full):
        assert full["c"].get(f"/api/crm/messaging/history/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404

    def test_get_messaging_history_item_with_data(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Msg", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        # Use raw insert to avoid NOT NULL constraints
        from sqlalchemy import text
        db_session.execute(
            text("""INSERT INTO communication_logs (id, persona_id, channel, content)
                     VALUES (:id, :pid, :chan, :content)"""),
            {"id": str(uuid.uuid4()), "pid": str(p.id), "chan": "sms", "content": "Test"},
        )
        db_session.commit()

        log = db_session.query(models.CommunicationLog).first()
        resp = c.get(f"/api/crm/messaging/history/{log.id}", headers=h)
        assert _ok(resp.status_code), f"log: {resp.status_code} {resp.text[:100]}"


class TestGruposCRM:
    def test_list_grupos(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Grp", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="CRM Group", sede_id=s.id, lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.commit()
        resp = c.get("/api/crm/grupos", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["total"] >= 1

    def test_get_grupo_detail(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Gd", last_name="Test",
                           sede_id=s.id, church_role="miembro")
        db_session.add(p)
        db_session.commit()
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Detail Group", sede_id=s.id, lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.commit()
        resp = c.get(f"/api/crm/grupos/{g.id}", headers=h)
        assert _ok(resp.status_code), f"grupo detail: {resp.status_code} {resp.text[:200]}"

    def test_get_grupo_not_found(self, full):
        assert full["c"].get(f"/api/crm/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

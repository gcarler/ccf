"""
Tests for chat.py — conversations and messaging endpoints.
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
    admin, _, _ = _seed_admin(db_session, email="chat@test.com")
    headers = _auth_headers(client, email="chat@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestChat:
    def test_search(self, full):
        assert _ok(full["c"].get("/api/chat/users/search?q=test", headers=full["h"]).status_code)
    def test_list_convs(self, full):
        assert _ok(full["c"].get("/api/chat/conversations", headers=full["h"]).status_code)
    def test_create_conv(self, full, db_session):
        s = db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="C", last_name="U", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        assert _ok(full["c"].post("/api/chat/conversations",
            json={"participant_ids": [str(p.id)]}, headers=full["h"]).status_code)
    def test_create_and_msg(self, full, db_session):
        c, h, s = full["c"], full["h"], db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="C2", last_name="U", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        conv = c.post("/api/chat/conversations", json={"participant_ids": [str(p.id)]}, headers=h).json()
        assert _ok(c.post(f"/api/chat/conversations/{conv['id']}/messages",
            json={"content": "Hi"}, headers=h).status_code)
    def test_get_msgs(self, full, db_session):
        c, h, s = full["c"], full["h"], db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="C3", last_name="U", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        conv = c.post("/api/chat/conversations", json={"participant_ids": [str(p.id)]}, headers=h).json()
        assert _ok(c.get(f"/api/chat/conversations/{conv['id']}/messages", headers=h).status_code)
    def test_mark_read(self, full, db_session):
        c, h, s = full["c"], full["h"], db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="C4", last_name="U", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        conv = c.post("/api/chat/conversations", json={"participant_ids": [str(p.id)]}, headers=h).json()
        assert _ok(c.post(f"/api/chat/conversations/{conv['id']}/read", headers=h).status_code)
    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/chat/messages/{uuid.uuid4()}", headers=full["h"]).status_code == 404

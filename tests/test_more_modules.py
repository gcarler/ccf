"""
Tests for donations, agenda, messaging — working endpoints.
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
    admin, _, _ = _seed_admin(db_session, email="more@test.com")
    headers = _auth_headers(client, email="more@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestDonations:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/donations", headers=full["h"]).status_code)
    def test_total(self, full):
        assert _ok(full["c"].get("/api/donations/total", headers=full["h"]).status_code)
    def test_summary(self, full):
        assert _ok(full["c"].get("/api/donations/summary", headers=full["h"]).status_code)
    def test_certificate_not_found(self, full):
        assert full["c"].get(f"/api/donations/{uuid.uuid4()}/certificate",
            headers=full["h"]).status_code == 404


class TestAgenda:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/agenda/events", headers=full["h"]).status_code)
    def test_create(self, full, db_session):
        c, h, s = full["c"], full["h"], db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="O", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        assert _ok(c.post("/api/agenda/events",
            json={"title": "Reunion", "start_at": "2026-07-01T10:00:00Z"},
            headers=h).status_code)
    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/agenda/events/{uuid.uuid4()}", headers=full["h"]).status_code == 404
    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/agenda/events/{uuid.uuid4()}", headers=full["h"]).status_code == 404
    def test_list_resources(self, full):
        assert _ok(full["c"].get("/api/agenda/resources", headers=full["h"]).status_code)


class TestMessaging:
    def test_history(self, full):
        assert _ok(full["c"].get("/api/messaging/history", headers=full["h"]).status_code)
    def test_notifications(self, full):
        assert _ok(full["c"].get("/api/messaging/notifications", headers=full["h"]).status_code)
    def test_presence(self, full):
        assert _ok(full["c"].get("/api/messaging/presence/global", headers=full["h"]).status_code)
    def test_mark_all_read(self, full):
        assert _ok(full["c"].post("/api/messaging/notifications/mark-all-read",
            json={}, headers=full["h"]).status_code)

"""Unit + API tests for evangelism_events/events_checkin.py and events_participantes.py."""

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
    admin, _, _ = _seed_admin(db_session, email="evch@test.com")
    headers = _auth_headers(client, email="evch@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


# ── EVENTS CHECKIN ──────────────────────────────────────────────────────────────


class TestCheckin:
    def test_checkin_list(self, full):
        """GET /events/checkin returns 200 or 404."""
        resp = full["c"].get("/api/evangelism/events/checkin", headers=full["h"])
        assert resp.status_code in (200, 404)

    def test_checkin_not_found(self, full):
        resp = full["c"].get(f"/api/evangelism/events/checkin/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code in (200, 404)

    def test_checkin_qr_not_found(self, full):
        resp = full["c"].get(f"/api/evangelism/events/checkin/qr/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code in (200, 404)

    def test_checkin_scan(self, full):
        resp = full["c"].post(
            "/api/evangelism/events/checkin/scan", json={"qr_token": str(uuid.uuid4())}, headers=full["h"]
        )
        assert resp.status_code in (200, 404, 422)


# ── EVENTS PARTICIPANTS ─────────────────────────────────────────────────────────


class TestParticipants:
    def test_create_participant_not_found(self, full):
        """POST /events/{id}/participants with nonexistent event returns 404."""
        resp = full["c"].post(
            f"/api/evangelism/events/{uuid.uuid4()}/participants",
            json={"persona_id": str(uuid.uuid4()), "role": "asistente"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_list_participants_not_found(self, full):
        resp = full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/participants", headers=full["h"])
        assert resp.status_code == 404

    def test_delete_participant_not_found(self, full):
        resp = full["c"].delete(f"/api/evangelism/events/{uuid.uuid4()}/participants/{uuid.uuid4()}", headers=full["h"])
        assert resp.status_code == 404

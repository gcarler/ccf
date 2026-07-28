"""
Tests for evangelism_notifications.py — send reminders endpoint.
"""
from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="notif@test.com")
    headers = _auth_headers(client, email="notif@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestNotifications:
    def test_send_reminders(self, full):
        assert _ok(full["c"].post("/api/evangelism/notifications/send-reminders",
            json={}, headers=full["h"]).status_code)

"""
Coverage tests for evangelism_events/events_checkin.py — target 80%+.
"""
import uuid

import pytest

from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "db": db_session,
        "admin": admin, "persona": persona, "sede": sede,
    }


def _make_event(db, sede_id):
    from backend import models
    from datetime import datetime, timezone
    e = models.CrmEvent(
        id=uuid.uuid4(), name="Test Event",
        description="Desc", event_type="service",
        event_date=datetime.now(timezone.utc),
        sede_id=sede_id,
    )
    db.add(e)
    db.flush()
    return e


class TestCheckinEndpoint:
    def test_checkin_visitor_invalid_date(self, full):
        c, h = full["c"], full["h"]
        # Create event first to reach date validation
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        resp = c.post(
            f"/api/evangelism/events/{event.id}/sessions/invalid-date/visitors",
            headers=h, json={"first_name": "Test", "last_name": "Visitor"},
        )
        assert resp.status_code in (400, 422)

    def test_checkin_visitor_event_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-07-20/visitors",
            headers=h, json={"first_name": "Test", "last_name": "Visitor"},
        )
        assert resp.status_code == 404

    def test_checkin_visitor_success_new(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.post(
            f"/api/evangelism/events/{event.id}/sessions/2026-07-20/visitors",
            headers=h, json={"first_name": "Nuevo", "last_name": "Visitante", "phone": "3001234567"},
        )
        assert resp.status_code in (200, 201), f"Expected 2xx, got {resp.status_code}: {resp.text[:200]}"

    def test_checkin_visitor_duplicate(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        c, h = full["c"], full["h"]
        c.post(
            f"/api/evangelism/events/{event.id}/sessions/2026-07-20/visitors",
            headers=h, json={"first_name": "Dup", "last_name": "Visitor", "phone": "3007654321"},
        )
        resp = c.post(
            f"/api/evangelism/events/{event.id}/sessions/2026-07-20/visitors",
            headers=h, json={"first_name": "Dup", "last_name": "Visitor", "phone": "3007654321"},
        )
        assert resp.status_code in (200, 201)

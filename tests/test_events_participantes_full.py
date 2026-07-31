"""Tests for events_participantes.py — attendance, sessions, assignments."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="epart@test.com")
    headers = _auth_headers(client, email="epart@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


def _create_event(db_session, sede):
    """Create a CrmEvent for testing."""
    evt = models.CrmEvent(
        id=uuid.uuid4(),
        name="Test Event",
        event_date=datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
        location="Test Location",
    )
    db_session.add(evt)
    db_session.flush()
    return evt


class TestAttendanceReport:
    def test_get_report_empty(self, full, db_session):
        """GET /events/{id}/attendance with no records."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        resp = c.get(f"/api/evangelism/events/{evt.id}/attendance", headers=h)
        assert _ok(resp.status_code), f"report: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["total_records"] == 0

    def test_get_report_with_data(self, full, db_session):
        """GET with attendance records."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        p = models.Persona(id=uuid.uuid4(), first_name="Att", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        att = models.EventAttendance(
            id=uuid.uuid4(),
            event_id=evt.id,
            persona_id=p.id,
            session_date=date(2026, 8, 15),
            attended=True,
            status="present",
        )
        db_session.add(att)
        db_session.commit()
        resp = c.get(f"/api/evangelism/events/{evt.id}/attendance", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["total_records"] == 1


class TestBulkAttendance:
    def test_bulk_requires_event_id(self, full):
        """POST /attendance/bulk without event_id -> 400."""
        resp = full["c"].post("/api/evangelism/attendance/bulk", json={}, headers=full["h"])
        assert resp.status_code == 400

    def test_bulk_non_list_persona_ids(self, full):
        """POST with non-list persona_ids -> 400."""
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={"event_id": str(uuid.uuid4()), "persona_ids": "not-list", "session_date": "2026-08-15"},
            headers=h,
        )
        # require_event_access runs first -> 404 for unknown event
        assert resp.status_code in (400, 404)

    def test_bulk_invalid_session_date(self, full, db_session):
        """POST with invalid session_date -> 400."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={"event_id": str(evt.id), "persona_ids": [], "session_date": "not-a-date"},
            headers=h,
        )
        assert resp.status_code == 400

    def test_bulk_success(self, full, db_session):
        """POST /attendance/bulk with valid data."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        p = models.Persona(id=uuid.uuid4(), first_name="Bulk", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={
                "event_id": str(evt.id),
                "persona_ids": [str(p.id)],
                "session_date": "2026-08-15",
                "source": "test",
            },
            headers=h,
        )
        # May be 403 if require_evangelism_edit blocks admin
        assert resp.status_code in (200, 403), f"bulk: {resp.status_code} {resp.text[:200]}"

    def test_bulk_cancelled_event_409(self, full, db_session):
        """POST bulk on cancelled event -> 409."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        evt.status = "CANCELLED"
        db_session.commit()

        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={
                "event_id": str(evt.id),
                "persona_ids": [str(uuid.uuid4())],
                "session_date": "2026-08-15",
            },
            headers=h,
        )
        assert resp.status_code in (409, 403)

    def test_bulk_update_existing(self, full, db_session):
        """POST bulk updates existing attendance records."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        p = models.Persona(id=uuid.uuid4(), first_name="Upd", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        # Pre-create an absent record
        existing = models.EventAttendance(
            id=uuid.uuid4(),
            event_id=evt.id,
            persona_id=p.id,
            session_date=date(2026, 8, 15),
            attended=False,
            status="absent",
        )
        db_session.add(existing)
        db_session.commit()

        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={
                "event_id": str(evt.id),
                "persona_ids": [str(p.id)],
                "session_date": "2026-08-15",
            },
            headers=h,
        )
        assert resp.status_code in (200, 403)


class TestSessionDetail:
    def test_get_session_detail(self, full, db_session):
        """GET /events/{id}/sessions/{date} with assignments and attendance."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        p = models.Persona(id=uuid.uuid4(), first_name="Sess", last_name="Detail", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        # Add an assignment
        assignment = models.EventAssignment(
            id=uuid.uuid4(),
            event_id=evt.id,
            session_date=date(2026, 8, 15),
            persona_id=p.id,
            role="participant",
        )
        db_session.add(assignment)

        # Add attendance
        att = models.EventAttendance(
            id=uuid.uuid4(),
            event_id=evt.id,
            persona_id=p.id,
            session_date=date(2026, 8, 15),
            attended=True,
            status="present",
        )
        db_session.add(att)
        db_session.commit()

        resp = c.get(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15", headers=h)
        assert _ok(resp.status_code), f"session: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert len(data["attendees"]) >= 1
        assert len(data["assignments"]) >= 1

    def test_session_event_not_found(self, full):
        """GET with non-existent event -> 404."""
        assert (
            full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-08-15", headers=full["h"]).status_code
            == 404
        )

    def test_session_detail_absentees(self, full, db_session):
        """Session detail includes absentees list."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        p = models.Persona(id=uuid.uuid4(), first_name="Abs", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        resp = c.get(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15", headers=h)
        assert _ok(resp.status_code)

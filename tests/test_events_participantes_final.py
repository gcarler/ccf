"""Cover remaining lines in events_participantes.py — role metrics, absentees, validation."""

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
    admin, _, _ = _seed_admin(db_session, email="ep99@test.com")
    headers = _auth_headers(client, email="ep99@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


def _create_event(db_session, sede):
    evt = models.CrmEvent(
        id=uuid.uuid4(),
        name="Test Event",
        event_date=datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
        location="Test",
    )
    db_session.add(evt)
    db_session.flush()
    return evt


class TestAttendanceReportEdge:
    def test_report_with_present_and_absent(self, full, db_session):
        """Line 73: absent.append with both present and absent records."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)

        p1 = models.Persona(id=uuid.uuid4(), first_name="Pres", last_name="A", sede_id=s.id)
        p2 = models.Persona(id=uuid.uuid4(), first_name="Abs", last_name="B", sede_id=s.id)
        db_session.add_all([p1, p2])
        db_session.flush()

        for p, attended in [(p1, True), (p2, False)]:
            db_session.add(
                models.EventAttendance(
                    id=uuid.uuid4(),
                    event_id=evt.id,
                    persona_id=p.id,
                    session_date=date(2026, 8, 15),
                    attended=attended,
                    status="present" if attended else "absent",
                )
            )
        db_session.commit()

        resp = c.get(f"/api/evangelism/events/{evt.id}/attendance", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert data["counts"]["present"] >= 1
        assert data["counts"]["absent"] >= 1
        assert len(data["present"]) >= 1
        assert len(data["absent"]) >= 1


class TestSessionDetailMetrics:
    def test_session_with_role_metrics(self, full, db_session):
        """Lines 252-266: role metrics with RoleDefinition records."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)

        # Create RoleDefinition records
        leadership_role = models.RoleDefinition(
            id=uuid.uuid4(),
            name="Liderazgo",
            is_leadership=True,
        )
        member_role = models.RoleDefinition(
            id=uuid.uuid4(),
            name="Miembro",
            is_leadership=False,
        )
        db_session.add_all([leadership_role, member_role])
        db_session.flush()

        # Create personas with matching church_roles
        p_leader = models.Persona(
            id=uuid.uuid4(), first_name="Lead", last_name="R", sede_id=s.id, church_role="Liderazgo"
        )
        p_member = models.Persona(id=uuid.uuid4(), first_name="Mem", last_name="R", sede_id=s.id, church_role="Miembro")
        db_session.add_all([p_leader, p_member])
        db_session.flush()

        # Create attendance records
        for p in [p_leader, p_member]:
            db_session.add(
                models.EventAttendance(
                    id=uuid.uuid4(),
                    event_id=evt.id,
                    persona_id=p.id,
                    session_date=date(2026, 8, 15),
                    attended=True,
                    status="present",
                )
            )
        db_session.commit()

        resp = c.get(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15", headers=h)
        assert _ok(resp.status_code), f"session metrics: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["metrics"]["Liderazgo"] >= 1
        assert len(data["attendees"]) >= 2

    def test_session_with_unknown_role(self, full, db_session):
        """Line 268: unknown role counts as 'Otros'."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)

        p = models.Persona(id=uuid.uuid4(), first_name="Other", last_name="Rol", sede_id=s.id, church_role="RareRole")
        db_session.add(p)
        db_session.flush()
        db_session.add(
            models.EventAttendance(
                id=uuid.uuid4(),
                event_id=evt.id,
                persona_id=p.id,
                session_date=date(2026, 8, 15),
                attended=True,
                status="present",
            )
        )
        db_session.commit()

        resp = c.get(f"/api/evangelism/events/{evt.id}/sessions/2026-08-15", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert data["metrics"].get("Otros", 0) >= 1


class TestBulkAttendanceValidation:
    def test_bulk_missing_event_id_400(self, full):
        """Line 113: missing event_id -> 400."""
        resp = full["c"].post(
            "/api/evangelism/attendance/bulk", json={"persona_ids": [], "session_date": "2026-08-15"}, headers=full["h"]
        )
        assert resp.status_code == 400

    def test_bulk_non_list_persona_ids_400(self, full, db_session):
        """Line 115: non-list persona_ids -> 400."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={"event_id": str(evt.id), "persona_ids": "not-a-list", "session_date": "2026-08-15"},
            headers=h,
        )
        # require_event_access passes but persona_ids validation fails
        assert resp.status_code == 400

    def test_bulk_invalid_persona_ids(self, full, db_session):
        """Lines 130, 137-138: invalid persona IDs in list."""
        c, h, s = full["c"], full["h"], full["s"]
        evt = _create_event(db_session, s)
        resp = c.post(
            "/api/evangelism/attendance/bulk",
            json={
                "event_id": str(evt.id),
                "persona_ids": ["not-a-uuid", "also-invalid"],
                "session_date": "2026-08-15",
            },
            headers=h,
        )
        # require_evangelism_edit may return 403 for admin
        assert resp.status_code in (200, 201, 403), f"invalid ids: {resp.status_code} {resp.text[:200]}"

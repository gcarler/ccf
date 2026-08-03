"""Tests for crud/crm_/support.py and timeline.py."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend import models, schemas
from backend.crud.crm_ import support, timeline

# ── Support ────────────────────────────────────────────────────────────────


class TestCreateSupportTicket:
    def test_create(self, db_session):
        payload = schemas.SupportTicketCreate(
            user_id=str(uuid.uuid4()),
            subject="Test ticket",
            description="A test",
            priority="media",
        )
        row = support.create_support_ticket(db_session, payload)
        assert row.id is not None
        assert row.subject == "Test ticket"


class TestGetSupportTickets:
    def test_empty(self, db_session):
        assert support.get_support_tickets(db_session) == []

    def test_filter_by_user(self, db_session):
        uid = uuid.uuid4()
        t1 = models.SupportTicket(id=uuid.uuid4(), user_id=uid, subject="Mine")
        t2 = models.SupportTicket(id=uuid.uuid4(), user_id=uuid.uuid4(), subject="Other")
        db_session.add_all([t1, t2])
        db_session.commit()

        result = support.get_support_tickets(db_session, user_id=uid)
        assert len(result) == 1
        assert result[0].id == t1.id

    def test_pagination(self, db_session):
        for i in range(5):
            db_session.add(models.SupportTicket(id=uuid.uuid4(), user_id=uuid.uuid4(), subject=f"T{i}"))
        db_session.commit()

        result = support.get_support_tickets(db_session, skip=0, limit=3)
        assert len(result) == 3

    def test_excludes_deleted(self, db_session):
        from backend.crud._utils import _utcnow
        t1 = models.SupportTicket(id=uuid.uuid4(), user_id=uuid.uuid4(), subject="Alive")
        t2 = models.SupportTicket(id=uuid.uuid4(), user_id=uuid.uuid4(), subject="Dead", deleted_at=_utcnow())
        db_session.add_all([t1, t2])
        db_session.commit()

        result = support.get_support_tickets(db_session)
        assert len(result) == 1
        assert result[0].id == t1.id


class TestGetSupportTicket:
    def test_get(self, db_session):
        t = models.SupportTicket(id=uuid.uuid4(), user_id=uuid.uuid4(), subject="Find me")
        db_session.add(t)
        db_session.commit()

        row = support.get_support_ticket(db_session, t.id)
        assert row is not None
        assert row.id == t.id

    def test_get_nonexistent(self, db_session):
        assert support.get_support_ticket(db_session, "nonexistent") is None


class TestUpdateSupportTicket:
    def test_update_status(self, db_session):
        t = models.SupportTicket(id=uuid.uuid4(), user_id=uuid.uuid4(), subject="Fix", status="abierto")
        db_session.add(t)
        db_session.commit()

        row = support.update_support_ticket(db_session, t.id, "resuelto")
        assert row.status == "resuelto"

    def test_update_nonexistent(self, db_session):
        assert support.update_support_ticket(db_session, "nope", "cerrado") is None


class TestDeleteSupportTicket:
    def test_delete_soft(self, db_session):
        t = models.SupportTicket(id=uuid.uuid4(), user_id=uuid.uuid4(), subject="Del")
        db_session.add(t)
        db_session.commit()

        result = support.delete_support_ticket(db_session, t.id)
        assert result is True

    def test_delete_nonexistent(self, db_session):
        assert support.delete_support_ticket(db_session, "nope") is False


# ── Timeline ───────────────────────────────────────────────────────────────


class TestGetPersonaTimeline:
    def test_empty_for_nonexistent_persona(self, db_session):
        result = timeline.get_persona_timeline(db_session, str(uuid.uuid4()))
        assert result == []

    def test_basic_persona_timeline(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Timeline", last_name="Test")
        db_session.add(p)
        db_session.commit()

        result = timeline.get_persona_timeline(db_session, str(p.id))
        assert len(result) >= 1
        assert result[0]["type"] == "participation"

    def test_timeline_with_counseling(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Counsel", last_name="Session")
        db_session.add(p)
        db_session.commit()

        ticket = models.CounselingTicket(id=uuid.uuid4(), persona_id=p.id, subject="Test session")
        db_session.add(ticket)
        db_session.commit()

        result = timeline.get_persona_timeline(db_session, str(p.id))
        counseling_events = [e for e in result if e["type"] == "counseling"]
        assert len(counseling_events) >= 1

    def test_timeline_with_communication(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Comm", last_name="Log")
        db_session.add(p)
        db_session.commit()

        log = models.CommunicationLog(id=uuid.uuid4(), persona_id=p.id, channel="email", content="Hello")
        db_session.add(log)
        db_session.commit()

        result = timeline.get_persona_timeline(db_session, str(p.id))
        comm_events = [e for e in result if e["type"] == "communication"]
        assert len(comm_events) >= 1

    def test_timeline_with_milestone(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Milestone", last_name="Test")
        db_session.add(p)
        db_session.commit()

        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=p.id, type="baptism",
            event_date=datetime(2024, 1, 1, tzinfo=timezone.utc), notes="Water baptism"
        )
        db_session.add(milestone)
        db_session.commit()

        result = timeline.get_persona_timeline(db_session, str(p.id))
        milestone_events = [e for e in result if e["type"] == "spiritual_milestone"]
        assert len(milestone_events) >= 1

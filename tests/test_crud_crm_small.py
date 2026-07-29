"""Tests for small CRUD CRM modules."""

from __future__ import annotations

import uuid

import pytest

from backend import models, schemas
from backend.crud.crm_ import (
    communication,
    community,
    counseling,
    donations,
    events,
    families,
    milestones,
    notifications,
    pipeline,
    prayer,
    volunteers,
)
from backend.crud.crm_.shared import resolve_persona_id_for_user


def _make_sede(db):
    s = models.Sede(id=uuid.uuid4(), nombre="CRUD Test Sede", ciudad="Test City")
    db.add(s)
    db.commit()
    return s


def _make_persona(db, sede_id) -> models.Persona:
    p = models.Persona(id=uuid.uuid4(), first_name="CRUD", last_name="Test", sede_id=sede_id)
    db.add(p)
    db.commit()
    return p


# ── Pipeline ─────────────────────────────────────────────────────────────
class TestCrudPipeline:
    def test_create_list_get_update_archive_pipeline(self, db_session):
        sede_id = uuid.uuid4()
        from backend.models_crm_pipeline import TipoPipelineEnum
        data = {"id": uuid.uuid4(), "sede_id": sede_id, "nombre": "Test Pipe", "tipo": TipoPipelineEnum.CONSEJERIA}
        row = pipeline.create_pipeline(db_session, data)
        assert row.id == data["id"]

        lst = pipeline.list_pipelines(db_session, sede_id)
        assert len(lst) == 1

        got = pipeline.get_pipeline(db_session, row.id)
        assert got is not None

        updated = pipeline.update_pipeline(db_session, row, {"nombre": "Updated"})
        assert updated.nombre == "Updated"

        pipeline.archive_pipeline(db_session, row)
        assert pipeline.get_pipeline(db_session, row.id) is None

    def test_create_list_get_update_archive_stage(self, db_session):
        pipe_id = uuid.uuid4()
        data = {"id": uuid.uuid4(), "pipeline_id": pipe_id, "nombre": "E1", "orden": 1}
        row = pipeline.create_stage(db_session, data)
        assert row.id == data["id"]

        lst = pipeline.list_stages(db_session, pipe_id)
        assert len(lst) == 1

        got = pipeline.get_stage(db_session, row.id)
        assert got is not None

        updated = pipeline.update_stage(db_session, row, {"nombre": "E2"})
        assert updated.nombre == "E2"

        pipeline.archive_stage(db_session, row)
        assert pipeline.get_stage(db_session, row.id) is None


# ── Prayer ───────────────────────────────────────────────────────────────
class TestCrudPrayer:
    def test_create_list_get_update_delete(self, db_session):
        sede = _make_sede(db_session)
        payload = schemas.PrayerRequestCreate(
            requester_name="Prayer Man", request_text="Pray for me", source="test"
        )
        row = prayer.create_prayer_request(db_session, payload)
        assert row.requester_name == "Prayer Man"
        row.sede_id = sede.id
        db_session.commit()

        lst = prayer.get_prayer_requests(db_session, sede_id=sede.id)
        assert len(lst) >= 1

        got = prayer.get_prayer_request(db_session, row.id)
        assert got is not None

        upd = prayer.update_prayer_request(
            db_session, row.id, schemas.PrayerRequestUpdate(status="answered")
        )
        assert upd.status == "answered"

        assert prayer.delete_prayer_request(db_session, row.id) is True
        assert prayer.delete_prayer_request(db_session, uuid.uuid4()) is False

    def test_create_raises_on_bad_data(self, db_session):
        with pytest.raises(ValueError):
            prayer.create_prayer_request(db_session, None)


# ── Volunteers ───────────────────────────────────────────────────────────
class TestCrudVolunteers:
    def test_create_list_get_update_delete(self, db_session):
        sede = _make_sede(db_session)
        p = _make_persona(db_session, sede.id)
        payload = schemas.VolunteerShiftCreate(
            persona_id=p.id, role_name="Usher", team_name="Greeting",
            shift_start="2026-07-01T08:00:00Z", shift_end="2026-07-01T12:00:00Z",
        )
        shift = volunteers.create_volunteer_shift(db_session, payload)
        assert shift.persona_id == p.id

        lst = volunteers.get_volunteer_shifts(db_session)
        assert len(lst) >= 1

        got = volunteers.get_volunteer_shift(db_session, shift.id)
        assert got is not None

        upd = volunteers.update_volunteer_shift(
            db_session, shift.id, schemas.VolunteerShiftUpdate(status="cancelled")
        )
        assert upd.status == "cancelled"

        assert volunteers.delete_volunteer_shift(db_session, shift.id) is True
        assert volunteers.delete_volunteer_shift(db_session, uuid.uuid4()) is False


# ── Communication (requires real user for sede check) ────────────────────
class TestCrudCommunication:
    def _make_admin_user(self, db_session):
        from tests.conftest import seed_admin
        admin, _, sede = seed_admin(db_session, email=f"comm_{uuid.uuid4().hex[:8]}@test.com")
        return admin, sede

    def _create_log(self, db_session, admin, persona_id):
        payload = schemas.CommunicationLogCreate(
            persona_id=persona_id, channel="call", content="Test call"
        )
        return communication.create_communication_log(db_session, payload, actor_user_id=admin.id)

    def test_create_list_get_update_delete(self, db_session):
        from backend.schemas.notifications import CommunicationLogUpdate
        admin, sede = self._make_admin_user(db_session)
        p = _make_persona(db_session, sede.id)

        row = self._create_log(db_session, admin, p.id)
        assert row.persona_id == p.id

        lst = communication.get_communication_logs(db_session, sede_id=sede.id)
        assert len(lst) >= 1

        got = communication.get_communication_log(db_session, str(row.id))
        assert got is not None

        upd = communication.update_communication_log(
            db_session, str(row.id), CommunicationLogUpdate(content="Updated")
        )
        assert upd.content == "Updated"

        assert communication.delete_communication_log(db_session, str(row.id)) is True
        assert communication.delete_communication_log(db_session, str(uuid.uuid4())) is False

    def test_create_rejects_cross_sede(self, db_session):
        admin, sede = self._make_admin_user(db_session)
        other_sede = uuid.uuid4()
        p = models.Persona(id=uuid.uuid4(), first_name="Cross", last_name="S", sede_id=other_sede)
        db_session.add(p)
        db_session.commit()
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            self._create_log(db_session, admin, p.id)


# ── Community ────────────────────────────────────────────────────────────
class TestCrudCommunity:
    def test_create_list_get_update_delete(self, db_session):
        from backend.schemas.operational import CommunityBoardCardUpdate
        sede = _make_sede(db_session)
        payload = schemas.CommunityBoardCardCreate(title="Card 1", content="Hello")
        row = community.create_community_card(db_session, payload, actor_sede=sede.id)
        assert row.title == "Card 1"
        assert row.sede_id == sede.id

        lst = community.get_community_cards(db_session)
        assert len(lst) >= 1

        got = community.get_community_card(db_session, row.id)
        assert got is not None

        upd = community.update_community_card(
            db_session, row.id, CommunityBoardCardUpdate(title="Updated")
        )
        assert upd.title == "Updated"

        assert community.delete_community_card(db_session, row.id) is True
        assert community.delete_community_card(db_session, uuid.uuid4()) is False


# ── Donations ────────────────────────────────────────────────────────────
class TestCrudDonations:
    def test_create_list_sum_get_update_delete(self, db_session):
        sede = _make_sede(db_session)
        payload = schemas.DonationCreate(amount=100.0, donation_type="Diezmo")
        row = donations.create_donation(db_session, payload)
        assert row.amount == 100.0
        row.sede_id = sede.id
        db_session.commit()

        lst = donations.get_donations(db_session, sede_id=sede.id)
        assert len(lst) >= 1

        total = donations.get_total_donations_amount(db_session, sede_id=sede.id)
        assert total >= 100.0

        got = donations.get_donation(db_session, row.id)
        assert got is not None

        upd = donations.update_donation(
            db_session, row.id, schemas.DonationUpdate(amount=50.0)
        )
        assert upd.amount == 50.0

        assert donations.delete_donation(db_session, row.id) is True
        assert donations.delete_donation(db_session, uuid.uuid4()) is False


# ── Events ───────────────────────────────────────────────────────────────
class TestCrudEvents:
    def test_create_list_get_update_delete(self, db_session):
        sede = _make_sede(db_session)
        payload = schemas.CrmEventCreate(
            name="Evento Test", event_date="2026-08-01T10:00:00Z",
            target_audience="ALL",
        )
        row = events.create_crm_event(db_session, payload)
        assert row.name == "Evento Test"
        row.sede_id = sede.id
        db_session.commit()

        lst = events.get_crm_events(db_session, sede_id=sede.id)
        assert len(lst) >= 1

        got = events.get_crm_event(db_session, row.id)
        assert got is not None

        upd = events.update_crm_event(
            db_session, row.id, schemas.CrmEventUpdate(name="Updated")
        )
        assert upd.name == "Updated"

        assert events.delete_crm_event(db_session, row.id) is True
        assert events.delete_crm_event(db_session, uuid.uuid4()) is False

    def test_event_attendance_create_get_delete(self, db_session):
        sede = _make_sede(db_session)
        payload = schemas.CrmEventCreate(
            name="Event Attend", event_date="2026-08-01T10:00:00Z",
            target_audience="ALL",
        )
        evt = events.create_crm_event(db_session, payload)
        att = events.create_event_attendance(
            db_session, schemas.EventAttendanceCreate(
                event_id=evt.id, persona_id=_make_persona(db_session, sede.id).id
            )
        )
        assert att.event_id == evt.id

        lst = events.get_event_attendance(db_session, evt.id)
        assert len(lst) >= 1

        assert events.delete_event_attendance(db_session, att.id) is True
        assert events.delete_event_attendance(db_session, uuid.uuid4()) is False

    def test_create_event_raises_on_bad_data(self, db_session):
        with pytest.raises(ValueError):
            events.create_crm_event(db_session, None)

    def test_create_attendance_raises_on_bad_data(self, db_session):
        with pytest.raises(ValueError):
            events.create_event_attendance(db_session, None)


# ── Families ─────────────────────────────────────────────────────────────
class TestCrudFamilies:
    def test_create_list_get_update_delete_personas(self, db_session):
        sede = _make_sede(db_session)
        fam = families.create_family(db_session, "Los Perez")
        assert fam.name == "Los Perez"

        lst = families.get_families(db_session, sede_id=sede.id)
        assert isinstance(lst, list)

        got = families.get_family(db_session, fam.id)
        assert got is not None

        p = _make_persona(db_session, sede.id)
        p.family_id = fam.id
        db_session.commit()

        lst2 = families.get_families(db_session, sede_id=sede.id)
        assert len(lst2) >= 1

        persona_lst = families.get_family_personas(db_session, fam.id)
        assert len(persona_lst) == 1

        upd = families.update_family(db_session, fam.id, "Los García")
        assert upd.name == "Los García"

        assert families.delete_family(db_session, fam.id) is True
        assert families.delete_family(db_session, uuid.uuid4()) is False


# ── Milestones ───────────────────────────────────────────────────────────
class TestCrudMilestones:
    def test_create_list_get_update_delete(self, db_session):
        sede = _make_sede(db_session)
        p = _make_persona(db_session, sede.id)
        from datetime import datetime, timezone
        ms = milestones.create_milestone(
            db_session, p.id, "BAPTISM", datetime.now(timezone.utc), sede_id=sede.id
        )
        assert ms.type == "BAPTISM"

        lst1 = milestones.get_milestones(db_session, p.id)
        assert len(lst1) == 1

        lst2 = milestones.list_milestones(db_session, sede_id=sede.id)
        assert len(lst2) >= 1

        got = milestones.get_milestone(db_session, ms.id)
        assert got is not None

        upd = milestones.update_milestone(db_session, ms.id, notes="Updated")
        assert upd.notes == "Updated"

        assert milestones.delete_milestone(db_session, ms.id) is True
        assert milestones.delete_milestone(db_session, uuid.uuid4()) is False


# ── Notifications ────────────────────────────────────────────────────────
class TestCrudNotifications:
    def test_crud_cycle(self, db_session):
        from tests.conftest import seed_admin
        admin, _, _ = seed_admin(db_session, email=f"notif_{uuid.uuid4().hex[:8]}@test.com")
        p = resolve_persona_id_for_user(db_session, admin.id)
        n = models.Notification(id=uuid.uuid4(), user_id=p, title="Test", content="Hello")
        db_session.add(n)
        db_session.commit()

        lst = notifications.get_user_notifications(db_session, admin.id)
        assert len(lst) >= 1

        marked = notifications.mark_notification_as_read(db_session, n.id, owner_persona_id=p)
        assert marked.is_read is True

        cnt = notifications.mark_all_notifications_read(db_session, admin.id)
        assert cnt >= 0

    def test_mark_read_wrong_owner_returns_none(self, db_session):
        n = models.Notification(id=uuid.uuid4(), user_id=uuid.uuid4(), title="T", content="M")
        db_session.add(n)
        db_session.commit()
        result = notifications.mark_notification_as_read(db_session, n.id, owner_persona_id=uuid.uuid4())
        assert result is None

    def test_user_notifications_empty_for_unknown_user(self, db_session):
        lst = notifications.get_user_notifications(db_session, uuid.uuid4())
        assert lst == []

    def test_mark_all_read_empty_for_unknown_user(self, db_session):
        cnt = notifications.mark_all_notifications_read(db_session, uuid.uuid4())
        assert cnt == 0


# ── Counseling ───────────────────────────────────────────────────────────
class TestCrudCounseling:
    def test_create_list_get_update_delete(self, db_session):
        sede = _make_sede(db_session)
        p = _make_persona(db_session, sede.id)
        payload = schemas.CounselingTicketCreate(
            persona_id=p.id, subject="Need help", notes="Crisis"
        )
        ticket = counseling.create_counseling_ticket(db_session, payload)
        assert ticket.subject == "Need help"

        lst = counseling.get_counseling_tickets(db_session, sede_id=sede.id)
        assert len(lst) >= 1

        got = counseling.get_counseling_ticket(db_session, ticket.id)
        assert got is not None

        upd = counseling.update_counseling_ticket(
            db_session, ticket.id, schemas.CounselingTicketUpdate(status="closed")
        )
        assert upd.status == "closed"

        assert counseling.delete_counseling_ticket(db_session, ticket.id) is True
        assert counseling.delete_counseling_ticket(db_session, uuid.uuid4()) is False

    def test_create_raises_on_bad_data(self, db_session):
        with pytest.raises(ValueError):
            counseling.create_counseling_ticket(db_session, None)

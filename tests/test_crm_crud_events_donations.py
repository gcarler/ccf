"""Direct unit tests for `backend.crud.crm_.events` + `donations` (QC-18 módulo C).

QC-18 closure (errorescrm.md): both modules had 0 direct tests — covered
only transitively via API integration tests. This file covers all 14
public functions:
  * events.py (8): CrmEvent CRUD + EventAttendance CRUD, both soft-deleted
    via `deleted_at` timestamp.
  * donations.py (6): Donation CRUD, soft-deleted via `deleted_at`; sum
    aggregation with scope.

Posture mirrors `tests/test_crm_crud_personas.py`: SQLite in-memory via the
`db_session` fixture, direct row inserts, no HTTP layer. We exercise:
  * Soft-delete by `deleted_at` (list/get/delete must filter `IS NULL`).
  * Sede-scope (Axioma 3): cross-tenant events / donations must not leak.
  * `create_crm_event` shape mutation for ROLE-target audience (test the
    branch that copies role_ids[0] → target_role_id).
  * `get_total_donations_amount` aggregates only live (non-deleted) rows.
"""
from __future__ import annotations

import uuid as _uuid
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud.crm_ import donations as crud_donations
from backend.crud.crm_ import events as crud_events


# ─── Fixtures local ────────────────────────────────────────────────────────────

def _seed_sede(db: Session, name: str = "Sede QC-18.C") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="QC18 City", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_persona(db: Session, sede_id: _uuid.UUID, first: str = "P") -> models.Persona:
    p = models.Persona(
        id=_uuid.uuid4(), first_name=first, last_name="T", sede_id=sede_id, estado_vital="ACTIVO",
        email=f"{first.lower()}{_uuid.uuid4().hex[:6]}@example.com",
    )
    db.add(p)
    db.flush()
    return p


def _seed_event(
    db: Session, *, sede_id: _uuid.UUID, name: str = "Evento", deleted_at=None,
) -> models.CrmEvent:
    import datetime as dt
    e = models.CrmEvent(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        name=name,
        event_date=dt.datetime(2026, 7, 1, 10, 0, tzinfo=dt.timezone.utc),
        event_type="ONCE",
        target_audience="ALL",
        deleted_at=deleted_at,
    )
    db.add(e)
    db.flush()
    return e


def _seed_attendance(
    db: Session, *, event: models.CrmEvent, persona: models.Persona, deleted_at=None,
    session_date=None,
) -> models.EventAttendance:
    import datetime as dt
    a = models.EventAttendance(
        id=_uuid.uuid4(),
        event_id=event.id,
        persona_id=persona.id,
        session_date=session_date or dt.date(2026, 7, 1),
        attended=True,
        deleted_at=deleted_at,
    )
    db.add(a)
    db.flush()
    return a


def _seed_donation(
    db: Session, *, sede_id: _uuid.UUID, persona: Optional[models.Persona] = None,
    amount: float = 100.0, donation_type: str = "DIEZMO", deleted_at=None,
) -> models.Donation:
    d = models.Donation(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        persona_id=persona.id if persona else None,
        amount=amount,
        currency="COP",
        donation_type=donation_type,
        status="CONFIRMADO",
        donor_name=persona.first_name if persona else "Anon",
    )
    if deleted_at is not None:
        d.deleted_at = deleted_at
    db.add(d)
    db.flush()
    return d


def _commit(db: Session) -> None:
    db.commit()


# ─── CrmEvent ──────────────────────────────────────────────────────────────────


def test_get_crm_events_scoped_by_sede(db_session):
    """Axioma 3: get_crm_events(env=SedeA) must NOT return SedeB events."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    e_a = _seed_event(db_session, sede_id=sede_a.id, name="EA")
    e_b = _seed_event(db_session, sede_id=sede_b.id, name="EB")
    _commit(db_session)

    out_a = crud_events.get_crm_events(db_session, sede_id=sede_a.id)
    ids = {e.id for e in out_a}
    assert e_a.id in ids
    assert e_b.id not in ids


def test_get_crm_events_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    e_live = _seed_event(db_session, sede_id=sede.id, name="Live")
    _seed_event(db_session, sede_id=sede.id, name="Dead", deleted_at=crud_events._utcnow())
    _commit(db_session)

    ids = {e.id for e in crud_events.get_crm_events(db_session, sede_id=sede.id)}
    assert e_live.id in ids
    assert len(ids) == 1


def test_get_crm_event_returns_none_for_missing(db_session):
    assert crud_events.get_crm_event(db_session, _uuid.uuid4()) is None


def test_get_crm_event_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    e = _seed_event(db_session, sede_id=sede.id, deleted_at=crud_events._utcnow())
    _commit(db_session)
    assert crud_events.get_crm_event(db_session, e.id) is None


def test_create_crm_event_role_audience_stores_target_role_id(db_session):
    """Branch contract: when target_audience=ROLE, target_role_id = role_ids[0]."""
    sede = _seed_sede(db_session)
    role_id = _uuid.uuid4()
    _commit(db_session)

    payload = schemas.CrmEventCreate(
        name="E",
        description=None,
        event_type=schemas.EventType.ONCE,
        target_audience=schemas.EventAudienceType.ROLE,
        target_role_id=None,
        target_role_ids=[str(role_id)],
        target_persona_ids=None,
        event_date="2026-07-01T10:00",
        start_time=None,
        end_time=None,
        day_of_week=None,
        month_day=None,
        fixed_date=None,
        location="Loc",
        status="PROGRAMADO",
        cancellation_reason=None,
    )
    row = crud_events.create_crm_event(db_session, payload)
    assert row.id is not None
    # ORM persists the enum as its .value (the DB column is VARCHAR(50)).
    assert (row.target_audience.value if hasattr(row.target_audience, "value") else row.target_audience) == "ROLE"
    assert row.target_role_id == role_id, "create_crm_event did not copy role_ids[0] → target_role_id"


def test_create_crm_event_non_role_audience_nulls_role_ids(db_session):
    """Branch contract: non-ROLE audience must null out target_role_id *and* _ids.

    The non-ROLE branch zeroes both fields regardless of input shape, so a
    well-formed UUID input still gets nullified when target_audience isn't ROLE.
    """
    _seed_sede(db_session)
    _commit(db_session)
    role_uuid = _uuid.uuid4()
    payload = schemas.CrmEventCreate(
        name="E",
        description=None,
        event_type=schemas.EventType.ONCE,
        target_audience=schemas.EventAudienceType.ALL,
        target_role_id=None,
        target_role_ids=[role_uuid],  # gets nullified by the non-ROLE branch
        target_persona_ids=None,
        event_date="2026-07-01T10:00",
        start_time=None,
        end_time=None,
        day_of_week=None,
        month_day=None,
        fixed_date=None,
        location="Loc",
        status="PROGRAMADO",
        cancellation_reason=None,
    )
    row = crud_events.create_crm_event(db_session, payload)
    assert row.target_role_id is None
    assert row.target_role_ids is None, "create_crm_event kept target_role_ids for non-ROLE audience"


def test_update_crm_event_returns_none_for_missing(db_session):
    out = crud_events.update_crm_event(db_session, _uuid.uuid4(), schemas.CrmEventUpdate(name="x"))
    assert out is None


def test_update_crm_event_updates_provided_fields_only(db_session):
    sede = _seed_sede(db_session)
    e = _seed_event(db_session, sede_id=sede.id, name="Orig", )
    _commit(db_session)
    out = crud_events.update_crm_event(db_session, e.id, schemas.CrmEventUpdate(name="Renombrado"))
    assert out.name == "Renombrado"


def test_delete_crm_event_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    e = _seed_event(db_session, sede_id=sede.id)
    _commit(db_session)
    assert crud_events.delete_crm_event(db_session, e.id) is True
    db_session.expire_all()
    row = db_session.query(models.CrmEvent).filter(models.CrmEvent.id == e.id).first()
    assert row is not None and row.deleted_at is not None
    assert crud_events.get_crm_event(db_session, e.id) is None


def test_delete_crm_event_returns_false_for_missing(db_session):
    assert crud_events.delete_crm_event(db_session, _uuid.uuid4()) is False


# ─── EventAttendance ───────────────────────────────────────────────────────────


def test_get_event_attendance_excludes_soft_deleted(db_session):
    """QC-07 closure guard: soft-deleted attendance must NOT appear in list.

    Note: EventAttendance has a UNIQUE constraint on (event_id, session_date,
    persona_id) — live + dead rows need distinct session_dates to coexist
    (the cross-Tenant dedup invariant would otherwise block our seed).
    """
    import datetime as dt
    sede = _seed_sede(db_session)
    e = _seed_event(db_session, sede_id=sede.id)
    p = _seed_persona(db_session, sede_id=sede.id)
    a_live = _seed_attendance(db_session, event=e, persona=p, session_date=dt.date(2026, 7, 1))
    a_dead = _seed_attendance(
        db_session, event=e, persona=p, deleted_at=crud_events._utcnow(),
        session_date=dt.date(2026, 7, 8),
    )
    _commit(db_session)

    ids = {a.id for a in crud_events.get_event_attendance(db_session, event_id=e.id)}
    assert a_live.id in ids
    assert a_dead.id not in ids


def test_create_event_attendance_persists_fields(db_session):
    sede = _seed_sede(db_session)
    e = _seed_event(db_session, sede_id=sede.id)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)

    payload = schemas.EventAttendanceCreate(
        event_id=e.id, persona_id=p.id, session_date="2026-07-01",
        attended=True, status="CONFIRMADO",
        # role_at_event + source are NON-Optional str on EventAttendanceCreate,
        # so we provide explicit values (DB column allows anythingvable str).
        role_at_event="attendee",
        source="MANUAL",
        check_in_at=None, check_out_at=None, notes=None, scanned_at=None,
    )
    row = crud_events.create_event_attendance(db_session, payload)
    assert row.id is not None
    assert row.event_id == e.id
    assert row.persona_id == p.id
    assert row.attended is True


def test_delete_event_attendance_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    e = _seed_event(db_session, sede_id=sede.id)
    p = _seed_persona(db_session, sede_id=sede.id)
    a = _seed_attendance(db_session, event=e, persona=p)
    _commit(db_session)

    assert crud_events.delete_event_attendance(db_session, a.id) is True
    db_session.expire_all()
    row = db_session.query(models.EventAttendance).filter(models.EventAttendance.id == a.id).first()
    assert row is not None and row.deleted_at is not None


def test_delete_event_attendance_returns_false_for_missing(db_session):
    assert crud_events.delete_event_attendance(db_session, _uuid.uuid4()) is False


def test_delete_event_attendance_returns_false_for_already_deleted(db_session):
    """Already-soft-deleted attendance found via filter(deleted_at IS NULL) = None → False."""
    sede = _seed_sede(db_session)
    e = _seed_event(db_session, sede_id=sede.id)
    p = _seed_persona(db_session, sede_id=sede.id)
    a = _seed_attendance(db_session, event=e, persona=p, deleted_at=crud_events._utcnow())
    _commit(db_session)
    assert crud_events.delete_event_attendance(db_session, a.id) is False


# ─── Donations ─────────────────────────────────────────────────────────────────


def test_get_donations_scoped_by_sede(db_session):
    """Axioma 3: get_donations(sede=SedeA) must NOT leak SedeB donations."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    pa = _seed_persona(db_session, sede_id=sede_a.id, first="A")
    pb = _seed_persona(db_session, sede_id=sede_b.id, first="B")
    d_a = _seed_donation(db_session, sede_id=sede_a.id, persona=pa)
    d_b = _seed_donation(db_session, sede_id=sede_b.id, persona=pb)
    _commit(db_session)

    ids = {d.id for d in crud_donations.get_donations(db_session, sede_id=sede_a.id)}
    assert d_a.id in ids and d_b.id not in ids


def test_get_donations_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    d_live = _seed_donation(db_session, sede_id=sede.id, persona=p)
    d_dead = _seed_donation(db_session, sede_id=sede.id, persona=p)
    d_dead.deleted_at = crud_donations._utcnow()
    _commit(db_session)

    ids = {d.id for d in crud_donations.get_donations(db_session, sede_id=sede.id)}
    assert d_live.id in ids and d_dead.id not in ids


def test_get_donation_returns_none_for_missing(db_session):
    assert crud_donations.get_donation(db_session, _uuid.uuid4()) is None


def test_get_donation_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    d = _seed_donation(db_session, sede_id=sede.id, persona=p)
    d.deleted_at = crud_donations._utcnow()
    _commit(db_session)
    assert crud_donations.get_donation(db_session, d.id) is None


def test_create_donation_persists_fields(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)
    payload = schemas.DonationCreate(
        persona_id=p.id, amount=500.0, donation_type="OFRENDA", fund_id=None, donor_name=p.first_name,
    )
    row = crud_donations.create_donation(db_session, payload)
    assert row.id is not None
    assert row.amount == 500.0
    assert row.donation_type == "OFRENDA"
    assert row.deleted_at is None


def test_update_donation_returns_none_for_missing(db_session):
    assert crud_donations.update_donation(db_session, _uuid.uuid4(), schemas.DonationUpdate(status="x")) is None


def test_update_donation_updates_provided_fields_only(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    d = _seed_donation(db_session, sede_id=sede.id, persona=p, amount=100.0)
    _commit(db_session)
    out = crud_donations.update_donation(db_session, d.id, schemas.DonationUpdate(status="PENDIENTE"))
    assert out.status == "PENDIENTE"
    assert out.amount == 100.0, "neighboring field clobbered"


def test_delete_donation_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    d = _seed_donation(db_session, sede_id=sede.id, persona=p)
    _commit(db_session)
    assert crud_donations.delete_donation(db_session, d.id) is True
    db_session.expire_all()
    assert crud_donations.get_donation(db_session, d.id) is None


def test_delete_donation_returns_false_for_missing(db_session):
    assert crud_donations.delete_donation(db_session, _uuid.uuid4()) is False


def test_get_total_donations_amount_sums_only_live_rows(db_session):
    """Aggregation must exclude soft-deleted donations (deleted_at IS NULL filter)."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _seed_donation(db_session, sede_id=sede.id, persona=p, amount=100.0)
    _seed_donation(db_session, sede_id=sede.id, persona=p, amount=200.0)
    d_dead = _seed_donation(db_session, sede_id=sede.id, persona=p, amount=999.0)
    d_dead.deleted_at = crud_donations._utcnow()
    _commit(db_session)

    total = crud_donations.get_total_donations_amount(db_session, sede_id=sede.id)
    assert total == 300.0, f"get_total_donations_amount included soft-deleted row → {total}"


def test_get_total_donations_amount_returns_zero_when_empty(db_session):
    sede = _seed_sede(db_session)
    _commit(db_session)
    assert crud_donations.get_total_donations_amount(db_session, sede_id=sede.id) == 0


def test_get_total_donations_amount_scoped_by_sede(db_session):
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    pa = _seed_persona(db_session, sede_id=sede_a.id, first="A")
    pb = _seed_persona(db_session, sede_id=sede_b.id, first="B")
    _seed_donation(db_session, sede_id=sede_a.id, persona=pa, amount=150.0)
    _seed_donation(db_session, sede_id=sede_b.id, persona=pb, amount=9999.0)
    _commit(db_session)

    assert crud_donations.get_total_donations_amount(db_session, sede_id=sede_a.id) == 150.0

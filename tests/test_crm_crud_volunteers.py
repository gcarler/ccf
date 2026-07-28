"""Direct unit tests for `backend.crud.crm_.volunteers`.

`volunteers.py` implements volunteer-shift CRUD. It is exercised indirectly in
`test_crm_extended_coverage.py` and `test_crm_projects_final.py`, but it lacked a
dedicated test file. This module covers all public functions directly.
"""
from __future__ import annotations

import datetime as dt
import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud.crm_.volunteers import (
    create_volunteer_shift,
    delete_volunteer_shift,
    get_volunteer_shift,
    get_volunteer_shifts,
    update_volunteer_shift,
)


def _seed_persona(db: Session, *, first: str = "P") -> models.Persona:
    sede = models.Sede(id=_uuid.uuid4(), nombre="Sede", ciudad="Bogota", es_activa=True)
    db.add(sede)
    db.flush()
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=first,
        last_name="T",
        sede_id=sede.id,
        estado_vital="ACTIVO",
        email=f"{first.lower()}{_uuid.uuid4().hex[:6]}@example.com",
    )
    db.add(p)
    db.flush()
    return p


def _commit(db: Session) -> None:
    db.commit()


def test_get_volunteer_shifts_empty(db_session):
    assert get_volunteer_shifts(db_session) == []


def test_create_volunteer_shift_persists(db_session):
    persona = _seed_persona(db_session)
    start = dt.datetime(2026, 1, 1, 8, tzinfo=dt.timezone.utc)
    end = dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc)
    payload = schemas.VolunteerShiftCreate(
        persona_id=str(persona.id),
        shift_start=start,
        shift_end=end,
        role_name="usher",
        team_name="hospitality",
        notes="morning",
    )
    row = create_volunteer_shift(db_session, payload)
    assert row.id is not None
    assert str(row.persona_id) == str(persona.id)
    # SQLite strips timezone info on storage; compare naive datetimes.
    assert row.shift_start.replace(tzinfo=None) == start.replace(tzinfo=None)
    assert row.shift_end.replace(tzinfo=None) == end.replace(tzinfo=None)
    assert row.role_name == "usher"


def test_get_volunteer_shift_returns_created_row(db_session):
    persona = _seed_persona(db_session)
    payload = schemas.VolunteerShiftCreate(
        persona_id=str(persona.id),
        shift_start=dt.datetime(2026, 1, 1, 8, tzinfo=dt.timezone.utc),
        shift_end=dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc),
        role_name="greeter",
        team_name="team",
    )
    created = create_volunteer_shift(db_session, payload)
    fetched = get_volunteer_shift(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.role_name == "greeter"


def test_get_volunteer_shift_returns_none_for_missing(db_session):
    assert get_volunteer_shift(db_session, _uuid.uuid4()) is None


def test_get_volunteer_shifts_filters_by_persona(db_session):
    p1 = _seed_persona(db_session, first="A")
    p2 = _seed_persona(db_session, first="B")
    s1 = create_volunteer_shift(
        db_session,
        schemas.VolunteerShiftCreate(
            persona_id=str(p1.id),
            shift_start=dt.datetime(2026, 1, 1, 8, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc),
            role_name="r1",
            team_name="t1",
        ),
    )
    create_volunteer_shift(
        db_session,
        schemas.VolunteerShiftCreate(
            persona_id=str(p2.id),
            shift_start=dt.datetime(2026, 1, 2, 8, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 1, 2, 12, tzinfo=dt.timezone.utc),
            role_name="r2",
            team_name="t2",
        ),
    )
    _commit(db_session)
    rows = get_volunteer_shifts(db_session, persona_id=str(p1.id))
    assert len(rows) == 1
    assert rows[0].id == s1.id


def test_update_volunteer_shift_changes_role(db_session):
    persona = _seed_persona(db_session)
    created = create_volunteer_shift(
        db_session,
        schemas.VolunteerShiftCreate(
            persona_id=str(persona.id),
            shift_start=dt.datetime(2026, 1, 1, 8, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc),
            role_name="old",
            team_name="team",
        ),
    )
    out = update_volunteer_shift(
        db_session,
        created.id,
        schemas.VolunteerShiftUpdate(role_name="new"),
    )
    assert out is not None
    assert out.role_name == "new"
    db_session.expire_all()
    fetched = get_volunteer_shift(db_session, created.id)
    assert fetched.role_name == "new"


def test_update_volunteer_shift_returns_none_for_missing(db_session):
    assert update_volunteer_shift(db_session, _uuid.uuid4(), schemas.VolunteerShiftUpdate(role_name="x")) is None


def test_delete_volunteer_shift_soft_deletes(db_session):
    persona = _seed_persona(db_session)
    created = create_volunteer_shift(
        db_session,
        schemas.VolunteerShiftCreate(
            persona_id=str(persona.id),
            shift_start=dt.datetime(2026, 1, 1, 8, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc),
            role_name="x",
            team_name="team",
        ),
    )
    assert delete_volunteer_shift(db_session, created.id) is True
    db_session.expire_all()
    assert get_volunteer_shift(db_session, created.id) is None
    assert get_volunteer_shifts(db_session, persona_id=str(persona.id)) == []


def test_delete_volunteer_shift_returns_false_for_missing(db_session):
    assert delete_volunteer_shift(db_session, _uuid.uuid4()) is False

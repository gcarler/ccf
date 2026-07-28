"""Direct unit tests for core CRUD functions in `backend.crud.crm_.extended`.

Covers automations (with sede scoping), event assignments (soft-delete),
positions, ministries, role definitions, funds, volunteer skills, and
persona-level associations.
"""
from __future__ import annotations

import datetime as dt
import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm_.extended import (
    CrmAutomationCreate,
    CrmAutomationUpdate,
    EventAssignmentCreate,
    EventAssignmentUpdate,
    FundCreate,
    FundUpdate,
    MinistryCreate,
    MinistryUpdate,
    PersonaMinistryAssignmentCreate,
    PersonaMinistryAssignmentUpdate,
    PersonaPositionCreate,
    PersonaPositionUpdate,
    PositionCreate,
    PositionUpdate,
    RoleDefinitionCreate,
    RoleDefinitionUpdate,
    VolunteerSkillCreate,
    VolunteerSkillUpdate,
    create_crm_automation,
    create_event_assignment,
    create_fund,
    create_ministry,
    create_persona_ministry_assignment,
    create_persona_position,
    create_position,
    create_role_definition,
    create_volunteer_skill,
    delete_crm_automation,
    delete_event_assignment,
    delete_fund,
    delete_ministry,
    delete_persona_ministry_assignment,
    delete_persona_position,
    delete_position,
    delete_role_definition,
    delete_volunteer_skill,
    get_crm_automation,
    get_crm_automations,
    get_event_assignment,
    get_event_assignments,
    get_fund,
    get_funds,
    get_ministries,
    get_ministry,
    get_persona_ministry_assignment,
    get_persona_ministry_assignments,
    get_persona_position,
    get_persona_positions,
    get_position,
    get_positions,
    get_role_definition,
    get_role_definitions,
    get_volunteer_skill,
    get_volunteer_skills,
    update_crm_automation,
    update_event_assignment,
    update_fund,
    update_ministry,
    update_persona_ministry_assignment,
    update_persona_position,
    update_position,
    update_role_definition,
    update_volunteer_skill,
)


def _seed_sede(db: Session, name: str = "Sede") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="Bogota", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_persona(db: Session, *, sede_id: _uuid.UUID | None = None, first: str = "P") -> models.Persona:
    sede_id = sede_id or _seed_sede(db).id
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=first,
        last_name="T",
        sede_id=sede_id,
        estado_vital="ACTIVO",
        email=f"{first.lower()}{_uuid.uuid4().hex[:6]}@example.com",
    )
    db.add(p)
    db.flush()
    return p


def _seed_event(db: Session, *, sede_id: _uuid.UUID) -> models.CrmEvent:
    event = models.CrmEvent(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        name="Evento",
        event_type="PERMANENT",
        status="SCHEDULED",
    )
    db.add(event)
    db.flush()
    return event


def _commit(db: Session) -> None:
    db.commit()


# ── Positions ──────────────────────────────────────────────────────────────────


def test_position_crud(db_session):
    pos = create_position(db_session, PositionCreate(name="Líder", category="ministry"))
    assert pos.name == "Líder"

    fetched = get_position(db_session, pos.id)
    assert fetched is not None
    assert fetched.name == "Líder"

    updated = update_position(db_session, pos.id, PositionUpdate(name="Líder Senior"))
    assert updated.name == "Líder Senior"

    assert delete_position(db_session, pos.id) is True
    db_session.expire_all()
    assert get_position(db_session, pos.id) is None


def test_get_positions_filter_category_and_active(db_session):
    a = create_position(db_session, PositionCreate(name="A", category="c1"))
    create_position(db_session, PositionCreate(name="B", category="c2"))
    _commit(db_session)
    # PositionCreate does not expose is_active; use update to deactivate A.
    update_position(db_session, a.id, PositionUpdate(is_active=False))
    _commit(db_session)

    active = get_positions(db_session, category="c1")
    assert len(active) == 0

    all_c1 = get_positions(db_session, category="c1", only_active=False)
    assert len(all_c1) == 1
    assert all_c1[0].name == "A"


# ── Persona Positions ──────────────────────────────────────────────────────────


def test_persona_position_crud(db_session):
    persona = _seed_persona(db_session)
    pos = create_position(db_session, PositionCreate(name="P"))
    _commit(db_session)

    pp = create_persona_position(
        db_session,
        PersonaPositionCreate(persona_id=str(persona.id), position_id=pos.id, notes="x"),
    )
    assert str(pp.persona_id) == str(persona.id)

    fetched = get_persona_position(db_session, pp.id)
    assert fetched is not None

    updated = update_persona_position(db_session, pp.id, PersonaPositionUpdate(notes="y"))
    assert updated.notes == "y"

    assert delete_persona_position(db_session, pp.id) is True
    assert get_persona_position(db_session, pp.id) is None


def test_get_persona_positions_filters(db_session):
    persona = _seed_persona(db_session)
    pos = create_position(db_session, PositionCreate(name="P"))
    _commit(db_session)
    create_persona_position(
        db_session,
        PersonaPositionCreate(persona_id=str(persona.id), position_id=pos.id, is_active=True),
    )
    _commit(db_session)

    rows = get_persona_positions(db_session, persona_id=str(persona.id), only_active=True)
    assert len(rows) == 1

    rows_all = get_persona_positions(db_session, persona_id=str(persona.id))
    assert len(rows_all) == 1


# ── Event Assignments ──────────────────────────────────────────────────────────


def test_event_assignment_crud(db_session):
    sede = _seed_sede(db_session)
    persona = _seed_persona(db_session, sede_id=sede.id)
    event = _seed_event(db_session, sede_id=sede.id)
    session_date = dt.date(2026, 1, 1)

    ea = create_event_assignment(
        db_session,
        EventAssignmentCreate(
            event_id=event.id,
            persona_id=str(persona.id),
            session_date=session_date,
            role="MC",
        ),
    )
    assert ea.role == "MC"

    fetched = get_event_assignment(db_session, ea.id)
    assert fetched is not None

    updated = update_event_assignment(db_session, ea.id, EventAssignmentUpdate(role="PREACHER"))
    assert updated.role == "PREACHER"

    assert delete_event_assignment(db_session, ea.id) is True
    assert get_event_assignment(db_session, ea.id) is None


def test_get_event_assignments_hides_deleted_and_filters(db_session):
    sede = _seed_sede(db_session)
    persona = _seed_persona(db_session, sede_id=sede.id)
    event = _seed_event(db_session, sede_id=sede.id)
    ea = create_event_assignment(
        db_session,
        EventAssignmentCreate(
            event_id=event.id,
            persona_id=str(persona.id),
            session_date=dt.date(2026, 1, 1),
            role="MC",
        ),
    )
    _commit(db_session)

    assert len(get_event_assignments(db_session, event_id=event.id)) == 1
    delete_event_assignment(db_session, ea.id)
    _commit(db_session)
    assert get_event_assignments(db_session, event_id=event.id) == []


# ── Ministries ────────────────────────────────────────────────────────────────


def test_ministry_crud(db_session):
    ministry = create_ministry(db_session, MinistryCreate(name="Alabanza"))
    assert ministry.name == "Alabanza"

    assert get_ministry(db_session, ministry.id) is not None

    updated = update_ministry(db_session, ministry.id, MinistryUpdate(name="Alabanza 2"))
    assert updated.name == "Alabanza 2"

    assert delete_ministry(db_session, ministry.id) is True
    db_session.expire_all()
    assert get_ministry(db_session, ministry.id) is None


def test_get_ministries_ordered(db_session):
    create_ministry(db_session, MinistryCreate(name="Z"))
    create_ministry(db_session, MinistryCreate(name="A"))
    _commit(db_session)

    names = [m.name for m in get_ministries(db_session)]
    assert names == sorted(names)


# ── Persona Ministry Assignments ──────────────────────────────────────────────


def test_persona_ministry_assignment_crud(db_session):
    persona = _seed_persona(db_session)
    ministry = create_ministry(db_session, MinistryCreate(name="M"))
    _commit(db_session)

    pma = create_persona_ministry_assignment(
        db_session,
        PersonaMinistryAssignmentCreate(persona_id=str(persona.id), ministry_id=ministry.id, role="Líder"),
    )
    assert pma.role == "Líder"

    fetched = get_persona_ministry_assignment(db_session, pma.id)
    assert fetched is not None

    updated = update_persona_ministry_assignment(db_session, pma.id, PersonaMinistryAssignmentUpdate(role="Asistente"))
    assert updated.role == "Asistente"

    assert delete_persona_ministry_assignment(db_session, pma.id) is True
    db_session.expire_all()
    assert get_persona_ministry_assignment(db_session, pma.id) is None


def test_get_persona_ministry_assignments_filters(db_session):
    persona = _seed_persona(db_session)
    ministry = create_ministry(db_session, MinistryCreate(name="M"))
    _commit(db_session)
    create_persona_ministry_assignment(
        db_session,
        PersonaMinistryAssignmentCreate(persona_id=str(persona.id), ministry_id=ministry.id, is_active=True),
    )
    _commit(db_session)

    rows = get_persona_ministry_assignments(db_session, persona_id=str(persona.id), only_active=True)
    assert len(rows) == 1


# ── CRM Automations ────────────────────────────────────────────────────────────


def test_crm_automation_crud(db_session):
    auto = create_crm_automation(
        db_session,
        CrmAutomationCreate(name="A", trigger_event="signup", action_type="email"),
    )
    assert auto.name == "A"

    fetched = get_crm_automation(db_session, auto.id)
    assert fetched is not None

    updated = update_crm_automation(db_session, auto.id, CrmAutomationUpdate(name="B"))
    assert updated.name == "B"

    assert delete_crm_automation(db_session, auto.id) is True
    assert get_crm_automation(db_session, auto.id).is_active is False


def test_get_crm_automations_scoped_by_sede(db_session):
    sede = _seed_sede(db_session)
    create_crm_automation(
        db_session,
        CrmAutomationCreate(name="Global", trigger_event="x", action_type="y"),
    )
    create_crm_automation(
        db_session,
        CrmAutomationCreate(name="Scoped", trigger_event="x", action_type="y"),
        sede_id=sede.id,
    )
    inactive = create_crm_automation(
        db_session,
        CrmAutomationCreate(name="Inactive", trigger_event="x", action_type="y", is_active=False),
    )
    _commit(db_session)

    rows = get_crm_automations(db_session, sede_id=sede.id)
    names = {a.name for a in rows}
    assert "Global" in names
    assert "Scoped" in names
    assert inactive.name not in names


def test_get_crm_automations_filtered_by_trigger(db_session):
    create_crm_automation(db_session, CrmAutomationCreate(name="A", trigger_event="signup", action_type="x"))
    create_crm_automation(db_session, CrmAutomationCreate(name="B", trigger_event="visit", action_type="x"))
    _commit(db_session)

    rows = get_crm_automations(db_session, trigger_event="signup")
    assert len(rows) == 1
    assert rows[0].name == "A"


# ── Role Definitions ───────────────────────────────────────────────────────────


def test_role_definition_crud(db_session):
    role = create_role_definition(db_session, RoleDefinitionCreate(name="Pastor", is_leadership=True))
    assert role.is_leadership is True

    fetched = get_role_definition(db_session, role.id)
    assert fetched is not None

    updated = update_role_definition(db_session, role.id, RoleDefinitionUpdate(name="Pastor Principal"))
    assert updated.name == "Pastor Principal"

    assert delete_role_definition(db_session, role.id) is True
    db_session.expire_all()
    assert get_role_definition(db_session, role.id) is None


def test_get_role_definitions_leadership_filter(db_session):
    create_role_definition(db_session, RoleDefinitionCreate(name="L", is_leadership=True))
    create_role_definition(db_session, RoleDefinitionCreate(name="M", is_leadership=False))
    _commit(db_session)

    rows = get_role_definitions(db_session, only_leadership=True)
    assert len(rows) == 1
    assert rows[0].name == "L"


# ── Funds ───────────────────────────────────────────────────────────────────────


def test_fund_crud(db_session):
    fund = create_fund(db_session, FundCreate(name="Misiones", is_public=True, current_balance=100.0))
    assert fund.name == "Misiones"
    assert fund.is_public is True

    fetched = get_fund(db_session, fund.fund_id)
    assert fetched is not None

    updated = update_fund(db_session, fund.fund_id, FundUpdate(current_balance=200.0))
    assert updated.current_balance == 200.0

    assert delete_fund(db_session, fund.fund_id) is True
    db_session.expire_all()
    assert get_fund(db_session, fund.fund_id) is None


def test_get_funds_public_filter(db_session):
    create_fund(db_session, FundCreate(name="Public", is_public=True))
    create_fund(db_session, FundCreate(name="Private", is_public=False))
    _commit(db_session)

    public = get_funds(db_session, only_public=True)
    assert len(public) == 1
    assert public[0].name == "Public"


# ── Volunteer Skills ───────────────────────────────────────────────────────────


def test_volunteer_skill_crud(db_session):
    skill = create_volunteer_skill(db_session, VolunteerSkillCreate(name="Guitarra", category="Music"))
    assert skill.name == "Guitarra"

    fetched = get_volunteer_skill(db_session, skill.id)
    assert fetched is not None

    updated = update_volunteer_skill(db_session, skill.id, VolunteerSkillUpdate(category="Worship"))
    assert updated.category == "Worship"

    assert delete_volunteer_skill(db_session, skill.id) is True
    db_session.expire_all()
    assert get_volunteer_skill(db_session, skill.id) is None


def test_get_volunteer_skills_filter_category(db_session):
    create_volunteer_skill(db_session, VolunteerSkillCreate(name="A", category="c1"))
    create_volunteer_skill(db_session, VolunteerSkillCreate(name="B", category="c2"))
    _commit(db_session)

    rows = get_volunteer_skills(db_session, category="c1")
    assert len(rows) == 1
    assert rows[0].name == "A"

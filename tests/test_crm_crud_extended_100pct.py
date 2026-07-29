"""
Comprehensive unit tests for backend/crud/crm_/extended.py to drive coverage to 100%.
"""
import uuid
import pytest
from datetime import datetime, date, timezone

from backend import models, schemas
from backend.crud.crm_ import extended as extended_crud
from backend.crud.crm_.extended import (
    PositionCreate, PositionUpdate,
    PersonaPositionCreate, PersonaPositionUpdate,
    EventAssignmentCreate, EventAssignmentUpdate,
    MinistryCreate, MinistryUpdate,
    PersonaMinistryAssignmentCreate, PersonaMinistryAssignmentUpdate,
    CrmAutomationCreate, CrmAutomationUpdate,
    CrmAutomationEdgeCreate, CrmAutomationEdgeUpdate,
    RoleDefinitionCreate, RoleDefinitionUpdate,
    PersonaRoleLinkCreate,
    FundCreate, FundUpdate,
    VolunteerSkillCreate, VolunteerSkillUpdate,
    ChatMessageCreate
)

@pytest.fixture
def sample_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(),
        nombre=f"Sede Ext {uuid.uuid4().hex[:6]}",
        ciudad="Bogota",
        es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede

@pytest.fixture
def sample_persona(db_session, sample_sede):
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="ExtTest",
        last_name="User",
        email=f"ext_{uuid.uuid4().hex[:6]}@example.com",
        sede_id=sample_sede.id
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return persona


def test_extended_positions(db_session, sample_persona):
    # Position
    pos = extended_crud.create_position(db_session, PositionCreate(name="Leader"))
    assert pos is not None
    assert extended_crud.get_position(db_session, pos.id) is not None
    assert len(extended_crud.get_positions(db_session)) >= 1

    pos_up = extended_crud.update_position(db_session, pos.id, PositionUpdate(name="Senior Leader"))
    assert pos_up.name == "Senior Leader"

    # PersonaPosition
    pp = extended_crud.create_persona_position(db_session, PersonaPositionCreate(persona_id=str(sample_persona.id), position_id=str(pos.id)))
    assert pp is not None
    assert extended_crud.get_persona_position(db_session, pp.id) is not None
    assert len(extended_crud.get_persona_positions(db_session, persona_id=str(sample_persona.id))) >= 1

    pp_up = extended_crud.update_persona_position(db_session, pp.id, PersonaPositionUpdate(notes="Updated position"))
    assert pp_up.notes == "Updated position"

    extended_crud.delete_persona_position(db_session, pp.id)
    extended_crud.delete_position(db_session, pos.id)


def test_extended_ministries(db_session, sample_persona):
    minis = extended_crud.create_ministry(db_session, MinistryCreate(name="Alabanza"))
    assert minis is not None
    assert extended_crud.get_ministry(db_session, minis.id) is not None
    assert len(extended_crud.get_ministries(db_session)) >= 1

    minis_up = extended_crud.update_ministry(db_session, minis.id, MinistryUpdate(name="Worship"))
    assert minis_up.name == "Worship"

    pma = extended_crud.create_persona_ministry_assignment(db_session, PersonaMinistryAssignmentCreate(persona_id=str(sample_persona.id), ministry_id=str(minis.id)))
    assert pma is not None
    assert extended_crud.get_persona_ministry_assignment(db_session, pma.id) is not None
    assert len(extended_crud.get_persona_ministry_assignments(db_session, persona_id=str(sample_persona.id))) >= 1

    pma_up = extended_crud.update_persona_ministry_assignment(db_session, pma.id, PersonaMinistryAssignmentUpdate(role="Lider"))
    assert pma_up.role == "Lider"

    extended_crud.delete_persona_ministry_assignment(db_session, pma.id)
    extended_crud.delete_ministry(db_session, minis.id)


def test_extended_event_assignments(db_session, sample_persona, sample_sede):
    # CrmEvent
    event = models.CrmEvent(id=uuid.uuid4(), sede_id=sample_sede.id, name="Conferencia")
    db_session.add(event)
    db_session.commit()

    ea = extended_crud.create_event_assignment(db_session, EventAssignmentCreate(event_id=str(event.id), persona_id=str(sample_persona.id), session_date=date.today(), role="Staff"))
    assert ea is not None
    assert extended_crud.get_event_assignment(db_session, ea.id) is not None
    assert len(extended_crud.get_event_assignments(db_session, event_id=event.id)) >= 1

    ea_up = extended_crud.update_event_assignment(db_session, ea.id, EventAssignmentUpdate(role="Coordinator"))
    assert ea_up.role == "Coordinator"

    extended_crud.delete_event_assignment(db_session, ea.id)


def test_extended_automations(db_session, sample_sede):
    auto = extended_crud.create_crm_automation(db_session, CrmAutomationCreate(name="Bienvenida Auto", trigger_event="persona_created", action_type="send_email"))
    assert auto is not None
    assert extended_crud.get_crm_automation(db_session, auto.id) is not None
    assert len(extended_crud.get_crm_automations(db_session)) >= 1

    auto_up = extended_crud.update_crm_automation(db_session, auto.id, CrmAutomationUpdate(name="Updated Auto"))
    assert auto_up.name == "Updated Auto"

    s1 = uuid.uuid4()
    t1 = uuid.uuid4()
    edge = extended_crud.create_crm_automation_edge(db_session, CrmAutomationEdgeCreate(automation_id=auto.id, source_id=s1, target_id=t1, source_node_id=s1, target_node_id=t1))
    assert edge is not None
    assert extended_crud.get_crm_automation_edge(db_session, edge.id) is not None
    assert len(extended_crud.get_crm_automation_edges(db_session, source_id=None)) >= 1

    edge_up = extended_crud.update_crm_automation_edge(db_session, edge.id, CrmAutomationEdgeUpdate(condition_value="yes"))
    assert edge_up.condition_value == "yes"

    extended_crud.delete_crm_automation_edge(db_session, edge.id)
    extended_crud.delete_crm_automation(db_session, auto.id)


def test_extended_roles(db_session, sample_persona):
    role_def = extended_crud.create_role_definition(db_session, RoleDefinitionCreate(name="Admin"))
    assert role_def is not None
    assert extended_crud.get_role_definition(db_session, role_def.id) is not None
    assert len(extended_crud.get_role_definitions(db_session)) >= 1

    role_up = extended_crud.update_role_definition(db_session, role_def.id, RoleDefinitionUpdate(name="Super Admin"))
    assert role_up.name == "Super Admin"

    link = extended_crud.create_persona_role_link(db_session, PersonaRoleLinkCreate(persona_id=str(sample_persona.id), role_id=str(role_def.id)))
    assert link is not None
    assert len(extended_crud.get_persona_role_links(db_session, persona_id=sample_persona.id)) >= 1

    extended_crud.delete_persona_role_link(db_session, link.id)
    extended_crud.delete_role_definition(db_session, role_def.id)


def test_extended_funds_skills_chat(db_session, sample_persona, sample_sede):
    # Fund
    fund = extended_crud.create_fund(db_session, FundCreate(name="Fondo Misiones", description="Misiones"))
    assert fund is not None
    assert extended_crud.get_fund(db_session, fund.fund_id) is not None
    assert len(extended_crud.get_funds(db_session)) >= 1

    fund_up = extended_crud.update_fund(db_session, fund.fund_id, FundUpdate(name="Fondo General"))
    assert fund_up.name == "Fondo General"
    extended_crud.delete_fund(db_session, fund.fund_id)

    # Volunteer Skill
    skill = extended_crud.create_volunteer_skill(db_session, VolunteerSkillCreate(name="Musica", category="Arte"))
    assert skill is not None
    assert extended_crud.get_volunteer_skill(db_session, skill.id) is not None
    assert len(extended_crud.get_volunteer_skills(db_session)) >= 1

    skill_up = extended_crud.update_volunteer_skill(db_session, skill.id, VolunteerSkillUpdate(name="Sonido"))
    assert skill_up.name == "Sonido"
    extended_crud.delete_volunteer_skill(db_session, skill.id)

    # Conversation & Chat Messages
    conv = extended_crud.create_conversation(db_session, participant_ids=[sample_persona.id])
    assert conv is not None
    assert extended_crud.get_conversation(db_session, conv.id) is not None

    conv2 = extended_crud.create_conversation_by_persona(db_session, persona_ids=[sample_persona.id])
    assert conv2 is not None

    msg = extended_crud.create_chat_message(db_session, ChatMessageCreate(sender_id=sample_persona.id, content="Hola"))
    assert msg is not None
    assert extended_crud.get_chat_message(db_session, msg.id) is not None
    assert len(extended_crud.get_chat_messages(db_session)) >= 1

    dm1 = extended_crud.create_direct_message(db_session, conversation_id=conv.id, sender_id=sample_persona.id, content="DM test")
    assert dm1 is not None

    dm2 = extended_crud.create_direct_message_by_persona(db_session, conversation_id=conv.id, sender_id=sample_persona.id, content="DM persona test")
    assert dm2 is not None

    conv_msgs = extended_crud.get_conversation_messages(db_session, conversation_id=conv.id)
    assert len(conv_msgs) >= 2

    extended_crud.delete_chat_message(db_session, msg.id)

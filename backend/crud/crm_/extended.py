"""CRUD for models missing dedicated functions:
positions, event_assignments, ministries, persona_ministry_assignments,
crm_automations, role_definitions, persona_role_links, funds,
volunteer_skills, chat_messages.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models
from backend.models_shared import _utcnow

# ── Inline Schemas ────────────────────────────────────────────────────────


class PositionCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None


class PositionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    is_active: bool | None = None


class PersonaPositionCreate(BaseModel):
    persona_id: str
    position_id: UUID
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool = True
    notes: str | None = None


class PersonaPositionUpdate(BaseModel):
    end_date: datetime | None = None
    is_active: bool | None = None
    notes: str | None = None


class EventAssignmentCreate(BaseModel):
    event_id: UUID
    persona_id: str
    session_date: datetime
    role: str


class EventAssignmentUpdate(BaseModel):
    role: str | None = None


class MinistryCreate(BaseModel):
    name: str
    description: str | None = None
    leader_persona_id: UUID | None = None


class MinistryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    leader_persona_id: UUID | None = None


class PersonaMinistryAssignmentCreate(BaseModel):
    persona_id: str
    ministry_id: UUID
    role: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool = True
    notes: str | None = None


class PersonaMinistryAssignmentUpdate(BaseModel):
    role: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool | None = None
    notes: str | None = None


class CrmAutomationCreate(BaseModel):
    name: str
    trigger_event: str
    action_type: str
    action_payload: dict | None = None
    is_active: bool = True
    delay_minutes: int = 0
    ui_graph_state: dict | None = None


class CrmAutomationUpdate(BaseModel):
    name: str | None = None
    trigger_event: str | None = None
    action_type: str | None = None
    action_payload: dict | None = None
    is_active: bool | None = None
    delay_minutes: int | None = None
    ui_graph_state: dict | None = None


class CrmAutomationEdgeCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    condition_type: str | None = None
    condition_key: str | None = None
    condition_value: str | None = None
    source_node_id: UUID | None = None
    target_node_id: UUID | None = None


class CrmAutomationEdgeUpdate(BaseModel):
    source_id: UUID | None = None
    target_id: UUID | None = None
    condition_type: str | None = None
    condition_key: str | None = None
    condition_value: str | None = None
    source_node_id: UUID | None = None
    target_node_id: UUID | None = None


class RoleDefinitionCreate(BaseModel):
    name: str
    color: str = "blue"
    is_leadership: bool = False


class RoleDefinitionUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_leadership: bool | None = None
    is_system_locked: bool | None = None


class PersonaRoleLinkCreate(BaseModel):
    persona_id: str
    role_id: UUID


class FundCreate(BaseModel):
    name: str
    description: str | None = None
    is_public: bool = False
    current_balance: float = 0.0
    target_amount: float | None = None


class FundUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    current_balance: float | None = None
    target_amount: float | None = None


class VolunteerSkillCreate(BaseModel):
    name: str
    category: str | None = None


class VolunteerSkillUpdate(BaseModel):
    name: str | None = None
    category: str | None = None


class ChatMessageCreate(BaseModel):
    sender_id: UUID
    room_id: str | None = None
    content: str


# ── Positions ─────────────────────────────────────────────────────────────


def get_positions(
    db: Session,
    category: str | None = None,
    only_active: bool = True,
) -> List[models.Position]:
    q = db.query(models.Position)
    if category:
        q = q.filter(models.Position.category == category)
    if only_active:
        q = q.filter(models.Position.is_active)
    return q.order_by(models.Position.name).all()


def get_position(db: Session, position_id: UUID) -> Optional[models.Position]:
    return db.query(models.Position).filter(models.Position.id == position_id).first()


def create_position(db: Session, payload: PositionCreate) -> models.Position:
    row = models.Position(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_position(
    db: Session, position_id: UUID, payload: PositionUpdate
) -> Optional[models.Position]:
    row = db.query(models.Position).filter(models.Position.id == position_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_position(db: Session, position_id: UUID) -> bool:
    row = db.query(models.Position).filter(models.Position.id == position_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Persona Positions ─────────────────────────────────────────────────────


def get_persona_positions(
    db: Session,
    persona_id: str | None = None,
    only_active: bool = False,
) -> List[models.PersonaPosition]:
    q = db.query(models.PersonaPosition)
    if persona_id is not None:
        q = q.filter(models.PersonaPosition.persona_id == persona_id)
    if only_active:
        q = q.filter(models.PersonaPosition.is_active)
    return q.order_by(models.PersonaPosition.created_at.desc()).all()


def get_persona_position(db: Session, mp_id: UUID) -> Optional[models.PersonaPosition]:
    return (
        db.query(models.PersonaPosition)
        .filter(models.PersonaPosition.id == mp_id)
        .first()
    )


def create_persona_position(
    db: Session, payload: PersonaPositionCreate
) -> models.PersonaPosition:
    row = models.PersonaPosition(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_persona_position(
    db: Session, mp_id: UUID, payload: PersonaPositionUpdate
) -> Optional[models.PersonaPosition]:
    row = (
        db.query(models.PersonaPosition)
        .filter(models.PersonaPosition.id == mp_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_persona_position(db: Session, mp_id: UUID) -> bool:
    row = (
        db.query(models.PersonaPosition)
        .filter(models.PersonaPosition.id == mp_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Event Assignments ────────────────────────────────────────────────────


def get_event_assignments(
    db: Session,
    event_id: UUID | None = None,
    persona_id: str | None = None,
    role: str | None = None,
) -> List[models.EventAssignment]:
    q = db.query(models.EventAssignment).filter(models.EventAssignment.deleted_at.is_(None))
    if event_id is not None:
        q = q.filter(models.EventAssignment.event_id == event_id)
    if persona_id is not None:
        q = q.filter(models.EventAssignment.persona_id == persona_id)
    if role:
        q = q.filter(models.EventAssignment.role == role)
    return q.order_by(models.EventAssignment.session_date.desc()).all()


def get_event_assignment(db: Session, ea_id: UUID) -> Optional[models.EventAssignment]:
    return (
        db.query(models.EventAssignment)
        .filter(
            models.EventAssignment.id == ea_id,
            models.EventAssignment.deleted_at.is_(None),
        )
        .first()
    )


def create_event_assignment(
    db: Session, payload: EventAssignmentCreate
) -> models.EventAssignment:
    row = models.EventAssignment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_event_assignment(
    db: Session, ea_id: UUID, payload: EventAssignmentUpdate
) -> Optional[models.EventAssignment]:
    row = (
        db.query(models.EventAssignment)
        .filter(
            models.EventAssignment.id == ea_id,
            models.EventAssignment.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_event_assignment(db: Session, ea_id: UUID) -> bool:
    row = (
        db.query(models.EventAssignment)
        .filter(
            models.EventAssignment.id == ea_id,
            models.EventAssignment.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Ministries ───────────────────────────────────────────────────────────


def get_ministries(db: Session) -> List[models.Ministry]:
    return db.query(models.Ministry).order_by(models.Ministry.name).all()


def get_ministry(db: Session, ministry_id: UUID) -> Optional[models.Ministry]:
    return db.query(models.Ministry).filter(models.Ministry.id == ministry_id).first()


def create_ministry(db: Session, payload: MinistryCreate) -> models.Ministry:
    row = models.Ministry(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_ministry(
    db: Session, ministry_id: UUID, payload: MinistryUpdate
) -> Optional[models.Ministry]:
    row = db.query(models.Ministry).filter(models.Ministry.id == ministry_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_ministry(db: Session, ministry_id: UUID) -> bool:
    row = db.query(models.Ministry).filter(models.Ministry.id == ministry_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Persona Ministries ────────────────────────────────────────────────────


def get_persona_ministry_assignments(
    db: Session,
    persona_id: str | None = None,
    ministry_id: UUID | None = None,
    only_active: bool = False,
) -> List[models.PersonaMinistryAssignment]:
    q = db.query(models.PersonaMinistryAssignment)
    if persona_id is not None:
        q = q.filter(models.PersonaMinistryAssignment.persona_id == persona_id)
    if ministry_id is not None:
        q = q.filter(models.PersonaMinistryAssignment.ministry_id == ministry_id)
    if only_active:
        q = q.filter(models.PersonaMinistryAssignment.is_active)
    return q.all()


def get_persona_ministry_assignment(db: Session, mm_id: UUID) -> Optional[models.PersonaMinistryAssignment]:
    return (
        db.query(models.PersonaMinistryAssignment)
        .filter(models.PersonaMinistryAssignment.id == mm_id)
        .first()
    )


def create_persona_ministry_assignment(
    db: Session, payload: PersonaMinistryAssignmentCreate
) -> models.PersonaMinistryAssignment:
    row = models.PersonaMinistryAssignment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_persona_ministry_assignment(
    db: Session, mm_id: UUID, payload: PersonaMinistryAssignmentUpdate
) -> Optional[models.PersonaMinistryAssignment]:
    row = (
        db.query(models.PersonaMinistryAssignment)
        .filter(models.PersonaMinistryAssignment.id == mm_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_persona_ministry_assignment(db: Session, mm_id: UUID) -> bool:
    row = (
        db.query(models.PersonaMinistryAssignment)
        .filter(models.PersonaMinistryAssignment.id == mm_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── CRM Automations ──────────────────────────────────────────────────────


def get_crm_automations(
    db: Session,
    only_active: bool = True,
    trigger_event: str | None = None,
) -> List[models.CrmAutomation]:
    q = db.query(models.CrmAutomation)
    if only_active:
        q = q.filter(models.CrmAutomation.is_active)
    if trigger_event:
        q = q.filter(models.CrmAutomation.trigger_event == trigger_event)
    return q.order_by(models.CrmAutomation.name).all()


def get_crm_automation(
    db: Session, automation_id: UUID
) -> Optional[models.CrmAutomation]:
    return (
        db.query(models.CrmAutomation)
        .filter(models.CrmAutomation.id == automation_id)
        .first()
    )


def create_crm_automation(
    db: Session, payload: CrmAutomationCreate
) -> models.CrmAutomation:
    row = models.CrmAutomation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_crm_automation(
    db: Session,
    automation_id: UUID,
    payload: CrmAutomationUpdate,
) -> Optional[models.CrmAutomation]:
    row = (
        db.query(models.CrmAutomation)
        .filter(models.CrmAutomation.id == automation_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_crm_automation(db: Session, automation_id: UUID) -> bool:
    row = (
        db.query(models.CrmAutomation)
        .filter(models.CrmAutomation.id == automation_id)
        .first()
    )
    if not row:
        return False
    row.is_active = False
    db.commit()
    return True


# ── CRM Automation Edges ──────────────────────────────────────────────────


def get_crm_automation_edges(
    db: Session,
    source_id: UUID | None = None,
    target_id: UUID | None = None,
) -> List[models.CrmAutomationEdge]:
    q = db.query(models.CrmAutomationEdge)
    if source_id is not None:
        q = q.filter(models.CrmAutomationEdge.source_id == source_id)
    if target_id is not None:
        q = q.filter(models.CrmAutomationEdge.target_id == target_id)
    return q.all()


def get_crm_automation_edge(db: Session, edge_id: UUID) -> Optional[models.CrmAutomationEdge]:
    return (
        db.query(models.CrmAutomationEdge)
        .filter(models.CrmAutomationEdge.id == edge_id)
        .first()
    )


def create_crm_automation_edge(
    db: Session, payload: CrmAutomationEdgeCreate
) -> models.CrmAutomationEdge:
    row = models.CrmAutomationEdge(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_crm_automation_edge(
    db: Session,
    edge_id: UUID,
    payload: CrmAutomationEdgeUpdate,
) -> Optional[models.CrmAutomationEdge]:
    row = (
        db.query(models.CrmAutomationEdge)
        .filter(models.CrmAutomationEdge.id == edge_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_crm_automation_edge(db: Session, edge_id: UUID) -> bool:
    row = (
        db.query(models.CrmAutomationEdge)
        .filter(models.CrmAutomationEdge.id == edge_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Role Definitions ─────────────────────────────────────────────────────


def get_role_definitions(
    db: Session, only_leadership: bool = False
) -> List[models.RoleDefinition]:
    q = db.query(models.RoleDefinition)
    if only_leadership:
        q = q.filter(models.RoleDefinition.is_leadership)
    return q.order_by(models.RoleDefinition.name).all()


def get_role_definition(db: Session, role_id: UUID) -> Optional[models.RoleDefinition]:
    return (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == role_id)
        .first()
    )


def create_role_definition(
    db: Session, payload: RoleDefinitionCreate
) -> models.RoleDefinition:
    row = models.RoleDefinition(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_role_definition(
    db: Session, role_id: UUID, payload: RoleDefinitionUpdate
) -> Optional[models.RoleDefinition]:
    row = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == role_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_role_definition(db: Session, role_id: UUID) -> bool:
    row = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == role_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Persona Roles ─────────────────────────────────────────────────────────


def get_persona_role_links(
    db: Session,
    persona_id: str | None = None,
    role_id: UUID | None = None,
) -> List[models.PersonaRoleLink]:
    q = db.query(models.PersonaRoleLink)
    if persona_id is not None:
        q = q.filter(models.PersonaRoleLink.persona_id == persona_id)
    if role_id is not None:
        q = q.filter(models.PersonaRoleLink.role_id == role_id)
    return q.order_by(models.PersonaRoleLink.created_at.desc()).all()


def create_persona_role_link(db: Session, payload: PersonaRoleLinkCreate) -> models.PersonaRoleLink:
    row = models.PersonaRoleLink(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_persona_role_link(db: Session, mr_id: UUID) -> bool:
    row = db.query(models.PersonaRoleLink).filter(models.PersonaRoleLink.id == mr_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Funds ────────────────────────────────────────────────────────────────


def get_funds(db: Session, only_public: bool = False) -> List[models.Fund]:
    q = db.query(models.Fund)
    if only_public:
        q = q.filter(models.Fund.is_public)
    return q.order_by(models.Fund.name).all()


def get_fund(db: Session, fund_id: UUID) -> Optional[models.Fund]:
    return db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()


def create_fund(db: Session, payload: FundCreate) -> models.Fund:
    row = models.Fund(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_fund(
    db: Session, fund_id: UUID, payload: FundUpdate
) -> Optional[models.Fund]:
    row = db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_fund(db: Session, fund_id: UUID) -> bool:
    row = db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Volunteer Skills ─────────────────────────────────────────────────────


def get_volunteer_skills(
    db: Session, category: str | None = None
) -> List[models.VolunteerSkill]:
    q = db.query(models.VolunteerSkill)
    if category:
        q = q.filter(models.VolunteerSkill.category == category)
    return q.order_by(models.VolunteerSkill.name).all()


def get_volunteer_skill(db: Session, skill_id: UUID) -> Optional[models.VolunteerSkill]:
    return (
        db.query(models.VolunteerSkill)
        .filter(models.VolunteerSkill.id == skill_id)
        .first()
    )


def create_volunteer_skill(
    db: Session, payload: VolunteerSkillCreate
) -> models.VolunteerSkill:
    row = models.VolunteerSkill(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_volunteer_skill(
    db: Session, skill_id: UUID, payload: VolunteerSkillUpdate
) -> Optional[models.VolunteerSkill]:
    row = (
        db.query(models.VolunteerSkill)
        .filter(models.VolunteerSkill.id == skill_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_volunteer_skill(db: Session, skill_id: UUID) -> bool:
    row = (
        db.query(models.VolunteerSkill)
        .filter(models.VolunteerSkill.id == skill_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Chat Messages ────────────────────────────────────────────────────────


def get_chat_messages(
    db: Session,
    room_id: str | None = None,
    sender_id: UUID | None = None,
    limit: int = 50,
) -> List[models.ChatMessage]:
    q = db.query(models.ChatMessage).filter(models.ChatMessage.deleted_at.is_(None))
    if room_id:
        q = q.filter(models.ChatMessage.room_id == room_id)
    if sender_id is not None:
        q = q.filter(models.ChatMessage.sender_id == sender_id)
    return q.order_by(models.ChatMessage.created_at.desc()).limit(limit).all()


def get_chat_message(db: Session, message_id: UUID) -> Optional[models.ChatMessage]:
    return (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.id == message_id,
            models.ChatMessage.deleted_at.is_(None),
        )
        .first()
    )


def create_chat_message(db: Session, payload: ChatMessageCreate) -> models.ChatMessage:
    row = models.ChatMessage(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_chat_message(db: Session, message_id: UUID) -> bool:
    row = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.id == message_id,
            models.ChatMessage.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Conversations (DMs) ──────────────────────────────────────────────


def create_conversation(db: Session, participant_ids: list[uuid.UUID]) -> models.Conversation:
    conv = models.Conversation()
    db.add(conv)
    db.flush()
    for uid in participant_ids:
        cp = models.ConversationParticipant(conversation_id=conv.id, user_id=uid)
        db.add(cp)
    db.commit()
    db.refresh(conv)
    return conv


def create_conversation_by_persona(db: Session, persona_ids: list[uuid.UUID]) -> models.Conversation:
    """Versión de create_conversation que acepta UUID de personas (FK personas.id)."""
    return create_conversation(db, persona_ids)


def get_user_conversations(db: Session, user_id: uuid.UUID) -> list[models.Conversation]:
    return (
        db.query(models.Conversation)
        .join(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.user_id == user_id,
            models.ConversationParticipant.is_archived.is_(False),
        )
        .order_by(models.Conversation.last_message_at.desc().nullslast())
        .all()
    )


def get_user_conversations_by_persona(db: Session, persona_id: uuid.UUID) -> list[models.Conversation]:
    """Versión de get_user_conversations que acepta persona_id UUID (FK personas.id)."""
    return get_user_conversations(db, persona_id)


def get_conversation(db: Session, conversation_id: UUID) -> Optional[models.Conversation]:
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )


def get_conversation_messages(
    db: Session,
    conversation_id: UUID,
    limit: int = 50,
    before_id: Optional[UUID] = None,
) -> list[models.ChatMessage]:
    q = db.query(models.ChatMessage).filter(
        models.ChatMessage.room_id == f"dm_{conversation_id}",
        models.ChatMessage.deleted_at.is_(None),
    )
    if before_id:
        q = q.filter(models.ChatMessage.id < before_id)
    return q.order_by(models.ChatMessage.created_at.desc()).limit(limit).all()


def create_direct_message(
    db: Session, conversation_id: UUID, sender_id: uuid.UUID, content: str
) -> models.ChatMessage:
    msg = models.ChatMessage(
        sender_id=sender_id,
        room_id=f"dm_{conversation_id}",
        content=content,
    )
    db.add(msg)
    conv = get_conversation(db, conversation_id)
    if conv:
        conv.last_message_content = content
        conv.last_message_at = _utcnow()
        conv.last_sender_id = sender_id
    db.commit()
    db.refresh(msg)
    return msg


def create_direct_message_by_persona(
    db: Session, conversation_id: UUID, sender_id: uuid.UUID, content: str
) -> models.ChatMessage:
    """Versión de create_direct_message que acepta sender_id UUID (FK personas.id)."""
    return create_direct_message(db, conversation_id, sender_id, content)


def mark_conversation_read(
    db: Session, conversation_id: UUID, user_id: uuid.UUID
) -> None:
    cp = (
        db.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conversation_id,
            models.ConversationParticipant.user_id == user_id,
        )
        .first()
    )
    if cp:
        cp.last_read_at = _utcnow()
    else:
        cp = models.ConversationParticipant(
            conversation_id=conversation_id,
            user_id=user_id,
            last_read_at=_utcnow(),
        )
        db.add(cp)
    db.commit()


def mark_conversation_read_by_persona(
    db: Session, conversation_id: UUID, persona_id: uuid.UUID
) -> None:
    """Versión de mark_conversation_read que acepta persona_id UUID (FK personas.id)."""
    return mark_conversation_read(db, conversation_id, persona_id)


def get_unread_count_for_conversation(
    db: Session, conversation_id: UUID, user_id: uuid.UUID
) -> int:
    cp = (
        db.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conversation_id,
            models.ConversationParticipant.user_id == user_id,
        )
        .first()
    )
    since = (cp.last_read_at if cp and cp.last_read_at else _utcnow())
    return (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.room_id == f"dm_{conversation_id}",
            models.ChatMessage.sender_id != user_id,
            models.ChatMessage.created_at > since,
        )
        .count()
    )


def get_unread_count_for_conversation_by_persona(
    db: Session, conversation_id: UUID, persona_id: uuid.UUID
) -> int:
    """Versión de get_unread_count_for_conversation que acepta persona_id UUID (FK personas.id)."""
    return get_unread_count_for_conversation(db, conversation_id, persona_id)

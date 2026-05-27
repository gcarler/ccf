"""CRUD for models missing dedicated functions:
positions, event_assignments, ministries, member_ministries,
crm_automations, role_definitions, member_roles, funds,
volunteer_skills, chat_messages.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models

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


class MemberPositionCreate(BaseModel):
    member_id: int
    position_id: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool = True
    notes: str | None = None


class MemberPositionUpdate(BaseModel):
    end_date: datetime | None = None
    is_active: bool | None = None
    notes: str | None = None


class EventAssignmentCreate(BaseModel):
    event_id: int
    member_id: int
    session_date: datetime
    role: str


class EventAssignmentUpdate(BaseModel):
    role: str | None = None


class MinistryCreate(BaseModel):
    name: str
    description: str | None = None
    leader_id: int | None = None


class MinistryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    leader_id: int | None = None


class MemberMinistryCreate(BaseModel):
    member_id: int
    ministry_id: int
    role: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool = True
    notes: str | None = None


class MemberMinistryUpdate(BaseModel):
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


class CrmAutomationUpdate(BaseModel):
    name: str | None = None
    trigger_event: str | None = None
    action_type: str | None = None
    action_payload: dict | None = None
    is_active: bool | None = None


class RoleDefinitionCreate(BaseModel):
    name: str
    color: str = "blue"
    is_leadership: bool = False


class RoleDefinitionUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_leadership: bool | None = None
    is_system_locked: bool | None = None


class MemberRoleCreate(BaseModel):
    member_id: int
    role_id: int


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
    sender_id: int
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


def get_position(db: Session, position_id: int) -> Optional[models.Position]:
    return db.query(models.Position).filter(models.Position.id == position_id).first()


def create_position(db: Session, payload: PositionCreate) -> models.Position:
    row = models.Position(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_position(
    db: Session, position_id: int, payload: PositionUpdate
) -> Optional[models.Position]:
    row = db.query(models.Position).filter(models.Position.id == position_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_position(db: Session, position_id: int) -> bool:
    row = db.query(models.Position).filter(models.Position.id == position_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Persona Positions ─────────────────────────────────────────────────────


def get_member_positions(
    db: Session,
    member_id: int | None = None,
    only_active: bool = False,
) -> List[models.MemberPosition]:
    q = db.query(models.MemberPosition)
    if member_id is not None:
        q = q.filter(models.MemberPosition.persona_id == member_id)
    if only_active:
        q = q.filter(models.MemberPosition.is_active)
    return q.order_by(models.MemberPosition.created_at.desc()).all()


def get_member_position(db: Session, mp_id: int) -> Optional[models.MemberPosition]:
    return (
        db.query(models.MemberPosition)
        .filter(models.MemberPosition.id == mp_id)
        .first()
    )


def create_member_position(
    db: Session, payload: MemberPositionCreate
) -> models.MemberPosition:
    row = models.MemberPosition(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_member_position(
    db: Session, mp_id: int, payload: MemberPositionUpdate
) -> Optional[models.MemberPosition]:
    row = (
        db.query(models.MemberPosition)
        .filter(models.MemberPosition.id == mp_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_member_position(db: Session, mp_id: int) -> bool:
    row = (
        db.query(models.MemberPosition)
        .filter(models.MemberPosition.id == mp_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Event Assignments ────────────────────────────────────────────────────


def get_event_assignments(
    db: Session,
    event_id: int | None = None,
    member_id: int | None = None,
    role: str | None = None,
) -> List[models.EventAssignment]:
    q = db.query(models.EventAssignment)
    if event_id is not None:
        q = q.filter(models.EventAssignment.event_id == event_id)
    if member_id is not None:
        q = q.filter(models.EventAssignment.persona_id == member_id)
    if role:
        q = q.filter(models.EventAssignment.role == role)
    return q.order_by(models.EventAssignment.session_date.desc()).all()


def get_event_assignment(db: Session, ea_id: int) -> Optional[models.EventAssignment]:
    return (
        db.query(models.EventAssignment)
        .filter(models.EventAssignment.id == ea_id)
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
    db: Session, ea_id: int, payload: EventAssignmentUpdate
) -> Optional[models.EventAssignment]:
    row = (
        db.query(models.EventAssignment)
        .filter(models.EventAssignment.id == ea_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_event_assignment(db: Session, ea_id: int) -> bool:
    row = (
        db.query(models.EventAssignment)
        .filter(models.EventAssignment.id == ea_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Ministries ───────────────────────────────────────────────────────────


def get_ministries(db: Session) -> List[models.Ministry]:
    return db.query(models.Ministry).order_by(models.Ministry.name).all()


def get_ministry(db: Session, ministry_id: int) -> Optional[models.Ministry]:
    return db.query(models.Ministry).filter(models.Ministry.id == ministry_id).first()


def create_ministry(db: Session, payload: MinistryCreate) -> models.Ministry:
    row = models.Ministry(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_ministry(
    db: Session, ministry_id: int, payload: MinistryUpdate
) -> Optional[models.Ministry]:
    row = db.query(models.Ministry).filter(models.Ministry.id == ministry_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_ministry(db: Session, ministry_id: int) -> bool:
    row = db.query(models.Ministry).filter(models.Ministry.id == ministry_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Persona Ministries ────────────────────────────────────────────────────


def get_member_ministries(
    db: Session,
    member_id: int | None = None,
    ministry_id: int | None = None,
    only_active: bool = False,
) -> List[models.MemberMinistry]:
    q = db.query(models.MemberMinistry)
    if member_id is not None:
        q = q.filter(models.MemberMinistry.persona_id == member_id)
    if ministry_id is not None:
        q = q.filter(models.MemberMinistry.ministry_id == ministry_id)
    if only_active:
        q = q.filter(models.MemberMinistry.is_active)
    return q.all()


def get_member_ministry(db: Session, mm_id: int) -> Optional[models.MemberMinistry]:
    return (
        db.query(models.MemberMinistry)
        .filter(models.MemberMinistry.id == mm_id)
        .first()
    )


def create_member_ministry(
    db: Session, payload: MemberMinistryCreate
) -> models.MemberMinistry:
    row = models.MemberMinistry(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_member_ministry(
    db: Session, mm_id: int, payload: MemberMinistryUpdate
) -> Optional[models.MemberMinistry]:
    row = (
        db.query(models.MemberMinistry)
        .filter(models.MemberMinistry.id == mm_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_member_ministry(db: Session, mm_id: int) -> bool:
    row = (
        db.query(models.MemberMinistry)
        .filter(models.MemberMinistry.id == mm_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
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
    db: Session, automation_id: int
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
    automation_id: int,
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


def delete_crm_automation(db: Session, automation_id: int) -> bool:
    row = (
        db.query(models.CrmAutomation)
        .filter(models.CrmAutomation.id == automation_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
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


def get_role_definition(db: Session, role_id: int) -> Optional[models.RoleDefinition]:
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
    db: Session, role_id: int, payload: RoleDefinitionUpdate
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


def delete_role_definition(db: Session, role_id: int) -> bool:
    row = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == role_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Persona Roles ─────────────────────────────────────────────────────────


def get_member_roles(
    db: Session,
    member_id: int | None = None,
    role_id: int | None = None,
) -> List[models.MemberRole]:
    q = db.query(models.MemberRole)
    if member_id is not None:
        q = q.filter(models.MemberRole.persona_id == member_id)
    if role_id is not None:
        q = q.filter(models.MemberRole.role_id == role_id)
    return q.order_by(models.MemberRole.created_at.desc()).all()


def create_member_role(db: Session, payload: MemberRoleCreate) -> models.MemberRole:
    row = models.MemberRole(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_member_role(db: Session, mr_id: int) -> bool:
    row = db.query(models.MemberRole).filter(models.MemberRole.id == mr_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Funds ────────────────────────────────────────────────────────────────


def get_funds(db: Session, only_public: bool = False) -> List[models.Fund]:
    q = db.query(models.Fund)
    if only_public:
        q = q.filter(models.Fund.is_public)
    return q.order_by(models.Fund.name).all()


def get_fund(db: Session, fund_id: int) -> Optional[models.Fund]:
    return db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()


def create_fund(db: Session, payload: FundCreate) -> models.Fund:
    row = models.Fund(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_fund(
    db: Session, fund_id: int, payload: FundUpdate
) -> Optional[models.Fund]:
    row = db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_fund(db: Session, fund_id: int) -> bool:
    row = db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()
    if not row:
        return False
    db.delete(row)
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


def get_volunteer_skill(db: Session, skill_id: int) -> Optional[models.VolunteerSkill]:
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
    db: Session, skill_id: int, payload: VolunteerSkillUpdate
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


def delete_volunteer_skill(db: Session, skill_id: int) -> bool:
    row = (
        db.query(models.VolunteerSkill)
        .filter(models.VolunteerSkill.id == skill_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Chat Messages ────────────────────────────────────────────────────────


def get_chat_messages(
    db: Session,
    room_id: str | None = None,
    sender_id: int | None = None,
    limit: int = 50,
) -> List[models.ChatMessage]:
    q = db.query(models.ChatMessage)
    if room_id:
        q = q.filter(models.ChatMessage.room_id == room_id)
    if sender_id is not None:
        q = q.filter(models.ChatMessage.sender_id == sender_id)
    return q.order_by(models.ChatMessage.created_at.desc()).limit(limit).all()


def get_chat_message(db: Session, message_id: int) -> Optional[models.ChatMessage]:
    return (
        db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    )


def create_chat_message(db: Session, payload: ChatMessageCreate) -> models.ChatMessage:
    row = models.ChatMessage(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_chat_message(db: Session, message_id: int) -> bool:
    row = (
        db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True

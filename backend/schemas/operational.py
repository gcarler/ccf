from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.schemas._common import orm_config


class MilestoneCreate(BaseModel):
    persona_id: UUID
    type: str
    event_date: date
    minister_id: Optional[UUID] = None


class Milestone(BaseModel):
    id: UUID
    persona_id: UUID
    type: str
    event_date: date
    minister_id: Optional[UUID] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    user_id: Optional[UUID] = None


class SupportTicket(BaseModel):
    id: UUID
    user_id: UUID
    subject: str
    description: str
    status: str = "open"
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = orm_config


class CommunityBoardCardCreate(BaseModel):
    title: str
    body: Optional[str] = None


class CommunityBoardCardUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None


class CommunityBoardCard(BaseModel):
    id: UUID
    title: str
    body: Optional[str] = None
    created_at: datetime
    model_config = orm_config


class PastorRadarSchema(BaseModel):
    membresia_viva: int = 0
    bautismos_este_anio: int = 0
    estudiantes_activos: int = 0
    recaudacion_mes: float = 0


class PublicRegistrationCreate(BaseModel):
    event_id: UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    accept_contact: bool = True

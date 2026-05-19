from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from backend.schemas._common import orm_config


class MilestoneCreate(BaseModel):
    person_id: int
    type: str
    event_date: date
    minister_id: Optional[int] = None


class Milestone(BaseModel):
    id: int
    person_id: int
    type: str
    event_date: date
    minister_id: Optional[int] = None
    created_at: datetime
    model_config = orm_config


class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    user_id: Optional[int] = None


class SupportTicket(BaseModel):
    id: int
    user_id: int
    subject: str
    description: str
    status: str = "open"
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = orm_config


class CommunityBoardCardCreate(BaseModel):
    title: str
    body: Optional[str] = None


class CommunityBoardCard(BaseModel):
    id: int
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
    event_id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    accept_contact: bool = True

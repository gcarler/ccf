from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AgendaEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    location: str | None = None
    is_all_day: bool = True

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_at and self.end_at < self.start_at:
            raise ValueError("end_at must be greater than or equal to start_at")
        return self


class AgendaEvent(AgendaEventCreate):
    id: UUID
    created_by_persona_id: UUID
    created_at: datetime
    updated_at: datetime


class PhysicalResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    resource_type: str = Field(min_length=1, max_length=50)
    capacity: int | None = Field(default=None, ge=1)
    is_active: bool = True


class PhysicalResource(PhysicalResourceCreate):
    id: UUID
    sede_id: UUID


class EventParticipantCreate(BaseModel):
    event_id: UUID
    persona_id: UUID
    confirmation_status: str = "PENDIENTE"
    is_required: bool = True
    confirmed_at: datetime | None = None


class EventParticipant(EventParticipantCreate):
    id: UUID


class ResourceReservationCreate(BaseModel):
    event_id: UUID
    resource_id: UUID
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_range(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        return self


class ResourceReservation(ResourceReservationCreate):
    id: UUID

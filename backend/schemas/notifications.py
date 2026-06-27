from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from backend.services.messaging_outcomes import CommunicationOutcome
from backend.schemas._common import orm_config


class Notification(BaseModel):
    id: UUID
    persona_id: UUID = Field(validation_alias=AliasChoices("persona_id", "user_id"), serialization_alias="persona_id")
    title: str
    content: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    model_config = orm_config


class CommunicationLogCreate(BaseModel):
    persona_id: UUID
    channel: str
    content: str
    leader_id: Optional[UUID] = None
    outcome: str = CommunicationOutcome.INTERNAL_LOG.value


class CommunicationLogUpdate(BaseModel):
    channel: Optional[str] = None
    content: Optional[str] = None
    outcome: Optional[str] = None


class CommunicationLog(BaseModel):
    id: UUID
    persona_id: UUID
    channel: str
    content: str
    leader_id: Optional[UUID] = None
    outcome: str = CommunicationOutcome.INTERNAL_LOG.value
    created_at: datetime
    model_config = orm_config

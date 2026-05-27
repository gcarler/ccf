from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.schemas._common import orm_config


class Notification(BaseModel):
    id: int
    user_id: int
    title: str
    content: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    model_config = orm_config


class CommunicationLogCreate(BaseModel):
    persona_id: str
    channel: str
    content: str
    leader_id: Optional[int] = None
    outcome: str = "sent"


class CommunicationLogUpdate(BaseModel):
    channel: Optional[str] = None
    content: Optional[str] = None
    outcome: Optional[str] = None


class CommunicationLog(BaseModel):
    id: int
    persona_id: str
    channel: str
    content: str
    leader_id: Optional[int] = None
    outcome: str = "sent"
    created_at: datetime
    model_config = orm_config

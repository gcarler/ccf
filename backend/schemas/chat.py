from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import List, Optional

from pydantic import BaseModel

from backend.schemas._common import orm_config


class ConversationCreate(BaseModel):
    participant_ids: List[UUID]


class ConversationParticipantRead(BaseModel):
    persona_id: UUID
    username: str = ""
    last_read_at: Optional[datetime] = None
    model_config = orm_config


class ConversationRead(BaseModel):
    id: UUID
    participants: List[ConversationParticipantRead] = []
    last_message_content: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_sender_id: Optional[UUID] = None
    unread_count: int = 0
    created_at: datetime
    model_config = orm_config


class DirectMessageCreate(BaseModel):
    content: str


class DirectMessageItem(BaseModel):
    id: UUID
    sender_id: UUID
    sender_name: str = ""
    content: str
    created_at: datetime
    is_read: bool = False
    model_config = orm_config

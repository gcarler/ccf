from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.schemas._common import orm_config


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_ids: List[UUID]

    def deduplicate_participants(self) -> "ConversationCreate":
        return ConversationCreate(participant_ids=list(dict.fromkeys(self.participant_ids)))


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
    model_config = ConfigDict(extra="forbid")

    content: str

    def model_post_init(self, __context) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if len(self.content) > 5000:
            raise ValueError("Message content exceeds 5000 characters")


class DirectMessageItem(BaseModel):
    id: UUID
    sender_id: UUID
    sender_name: str = ""
    content: str
    created_at: datetime
    is_read: bool = False
    model_config = orm_config

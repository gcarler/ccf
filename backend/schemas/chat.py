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
    content: str = ""
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None
    reply_to_id: Optional[UUID] = None
    mentions: Optional[List[UUID]] = None

    def model_post_init(self, __context) -> None:
        has_content = bool(self.content and self.content.strip())
        has_attachment = bool(self.attachment_url)
        if not has_content and not has_attachment:
            raise ValueError("El mensaje debe tener contenido o adjunto")
        if self.content and len(self.content) > 5000:
            raise ValueError("Message content exceeds 5000 characters")


class ReplyPreview(BaseModel):
    id: UUID
    sender_name: str = ""
    content: str = ""
    attachment_type: Optional[str] = None
    model_config = orm_config


class DirectMessageItem(BaseModel):
    id: UUID
    sender_id: UUID
    sender_name: str = ""
    content: str
    created_at: datetime
    is_read: bool = False
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None
    reply_to_id: Optional[UUID] = None
    reply_preview: Optional[ReplyPreview] = None
    mentions: Optional[List[str]] = None
    model_config = orm_config


class ChatMessageAdminRead(BaseModel):
    """Read model used by the message admin center (sent messages and mentions)."""

    id: UUID
    conversation_id: UUID
    conversation_name: str = ""
    sender_id: UUID
    sender_name: str = ""
    content: str
    created_at: datetime
    is_read: bool = False
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None
    reply_to_id: Optional[UUID] = None
    mentions: Optional[List[str]] = None
    model_config = orm_config

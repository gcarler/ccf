from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config

RESOURCE_TYPES = ("message", "script", "quick_reply")
RESOURCE_CHANNELS = ("whatsapp", "email", "sms", "general")
RESOURCE_CATEGORIES = (
    "bienvenida", "seguimiento", "invitacion", "pastoral",
    "consolidacion", "anuncio", "general",
)


class CrmResourceCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    type: str = Field("message")
    channel: Optional[str] = Field(None)
    category: str = Field("general")
    subject: Optional[str] = Field(None, max_length=500)
    body: str = Field("", description="Cuerpo del mensaje o guión")
    steps: Optional[List[dict]] = None
    variables: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class CrmResourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    type: Optional[str] = None
    channel: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    steps: Optional[List[dict]] = None
    variables: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CrmResourceOut(BaseModel):
    id: str
    sede_id: Optional[str] = None
    created_by: Optional[str] = None
    name: str
    description: Optional[str] = None
    type: str
    channel: Optional[str] = None
    category: str
    subject: Optional[str] = None
    body: str
    steps: Optional[List[Any]] = None
    variables: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    usage_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = orm_config

    @classmethod
    def from_orm_safe(cls, row: Any) -> "CrmResourceOut":
        return cls(
            id=str(row.id),
            sede_id=str(row.sede_id) if row.sede_id else None,
            created_by=str(row.created_by) if row.created_by else None,
            name=row.name,
            description=row.description,
            type=row.type,
            channel=row.channel,
            category=row.category,
            subject=row.subject,
            body=row.body or "",
            steps=row.steps,
            variables=row.variables,
            tags=row.tags,
            usage_count=row.usage_count or 0,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

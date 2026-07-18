from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WikiPageCreate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field("", description="HTML content")


class WikiPageUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[list[str]] = None


class WikiPageRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    page_key: str
    title: str
    content: str
    version: int = 1
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    sede_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class WikiPageVersionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    wiki_page_id: UUID
    version_number: int
    title: str
    content: str
    created_by_persona_id: Optional[UUID] = None
    created_at: datetime

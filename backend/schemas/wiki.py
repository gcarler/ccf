from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class WikiPageBase(BaseModel):
    page_key: str
    title: str
    content: Optional[str] = ""


class WikiPageCreate(WikiPageBase):
    pass


class WikiPageUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class WikiPageRead(BaseModel):
    id: UUID
    page_key: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

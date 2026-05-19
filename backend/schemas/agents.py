from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.schemas._common import orm_config


class AgentTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    source: Optional[str] = None


class AgentTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class AgentTask(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    source: Optional[str] = None
    created_at: datetime
    model_config = orm_config


class AgentInsightCreate(BaseModel):
    title: str
    insight_type: str
    payload: str


class AgentInsight(BaseModel):
    id: int
    title: str
    insight_type: str
    payload: str
    acknowledged: bool = False
    created_at: datetime
    model_config = orm_config

"""Pydantic schemas for Agent identity system."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class AgentBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    spiritual_stage: str = "visitor"


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    spiritual_stage: Optional[str] = None
    is_active: Optional[bool] = None


class AgentResponse(AgentBase):
    id: int
    code: str
    full_name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class AgentRoleCreate(BaseModel):
    role_type: str
    role_value: str
    context_id: Optional[int] = None
    context_type: Optional[str] = None
    is_primary: bool = False


class AgentRoleResponse(BaseModel):
    id: int
    agent_id: int
    role_type: str
    role_value: str
    context_id: Optional[int] = None
    context_type: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_primary: bool

    model_config = {"from_attributes": True}


class AgentActivityCreate(BaseModel):
    activity_type: str
    source_type: str
    source_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    occurred_at: Optional[datetime] = None


class AgentActivityResponse(BaseModel):
    id: int
    agent_id: int
    activity_type: str
    source_type: str
    source_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    occurred_at: datetime

    model_config = {"from_attributes": True}


class AgentTimelineItem(BaseModel):
    activity_type: str
    source_type: str
    source_id: Optional[int]
    status: Optional[str]
    notes: Optional[str]
    occurred_at: datetime


class AgentProfileResponse(BaseModel):
    agent: AgentResponse
    roles: List[AgentRoleResponse]
    activities: List[AgentTimelineItem]
    total_activities: int

    model_config = {"from_attributes": True}


class AgentSearchResult(BaseModel):
    id: int
    code: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    spiritual_stage: str
    is_active: bool

    model_config = {"from_attributes": True}


class StageTransition(BaseModel):
    to_stage: str
    reason: Optional[str] = None


# ── Legacy AgentTask/Insight (backwards compat with existing system) ──
class AgentTaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = "pending"
    source: Optional[str] = None
    assigned_to: Optional[str] = None
    agent_type: Optional[str] = None
    metadata: Optional[dict] = None


class AgentTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    metadata: Optional[dict] = None

    model_config = {"from_attributes": True}


class AgentTask(BaseModel):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class AgentInsightCreate(BaseModel):
    title: str
    description: str = ""
    insight_type: str = "observation"
    confidence: float = 0.5
    source_agent: Optional[str] = None
    payload: Optional[dict] = None
    metadata: Optional[dict] = None


class AgentInsight(AgentInsightCreate):
    id: int
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

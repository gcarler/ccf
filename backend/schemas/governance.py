from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config


class AdminAuditLog(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    severity: str = "info"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    model_config = orm_config


class AutomationRuleRead(BaseModel):
    id: int
    name: str
    trigger_type: str
    action_type: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    last_run: Optional[datetime] = None
    model_config = orm_config


class AutomationRuleCreate(BaseModel):
    name: str
    trigger_type: str
    action_type: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

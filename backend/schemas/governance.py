from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict

from backend.schemas._common import orm_config


class AdminAuditLog(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    actor_user_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    severity: str = "info"
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    created_at: datetime


class AutomationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    trigger_type: str
    action_type: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    last_run: Optional[datetime] = None


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

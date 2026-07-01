from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminAuditLog(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    actor_persona_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    severity: str = "info"
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    created_at: datetime

    @field_validator("actor_persona_id", mode="before")
    @classmethod
    def _actor_persona_id_to_str(cls, value):
        return str(value) if value is not None else None


class AutomationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
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

"""Schemas para CrmAutomation (automatizaciones de mensajes)."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class CrmAutomationCreate(BaseModel):
    name: str
    trigger_event: str
    action_type: str
    action_payload: Optional[Dict[str, Any]] = None
    is_active: bool = True


class CrmAutomationUpdate(BaseModel):
    name: Optional[str] = None
    trigger_event: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class CrmAutomationOut(BaseModel):
    id: UUID
    name: str
    trigger_event: str
    action_type: str
    action_payload: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: str

    @classmethod
    def from_orm_safe(cls, obj) -> "CrmAutomationOut":
        return cls(
            id=obj.id,
            name=obj.name,
            trigger_event=obj.trigger_event,
            action_type=obj.action_type,
            action_payload=obj.action_payload or {},
            is_active=obj.is_active,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
        )


class AutomationTriggerPayload(BaseModel):
    trigger_event: str
    context: Dict[str, Any] = {}


class AutomationTriggerResult(BaseModel):
    automation_id: UUID
    automation_name: str
    status: str  # "triggered" | "skipped" | "failed"
    detail: Optional[str] = None

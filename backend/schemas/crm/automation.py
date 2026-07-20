"""Schemas para CrmAutomation (automatizaciones de mensajes)."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CrmAutomationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    trigger_event: str
    action_type: str
    action_payload: Optional[Dict[str, Any]] = None
    is_active: bool = True
    delay_minutes: int = 0
    ui_graph_state: Optional[Dict[str, Any]] = None


class CrmAutomationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    trigger_event: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    delay_minutes: Optional[int] = None
    ui_graph_state: Optional[Dict[str, Any]] = None


class CrmAutomationOut(BaseModel):
    id: UUID
    name: str
    trigger_event: str
    action_type: str
    action_payload: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: str
    delay_minutes: int
    ui_graph_state: Optional[Dict[str, Any]] = None

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
            delay_minutes=getattr(obj, "delay_minutes", 0),
            ui_graph_state=getattr(obj, "ui_graph_state", None),
        )


class CrmAutomationEdgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    target_id: UUID
    condition_type: Optional[str] = None
    condition_key: Optional[str] = None
    condition_value: Optional[str] = None
    source_node_id: Optional[UUID] = None
    target_node_id: Optional[UUID] = None


class CrmAutomationEdgeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: Optional[UUID] = None
    target_id: Optional[UUID] = None
    condition_type: Optional[str] = None
    condition_key: Optional[str] = None
    condition_value: Optional[str] = None
    source_node_id: Optional[UUID] = None
    target_node_id: Optional[UUID] = None


class CrmAutomationEdgeOut(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    condition_type: Optional[str] = None
    condition_key: Optional[str] = None
    condition_value: Optional[str] = None
    source_node_id: Optional[UUID] = None
    target_node_id: Optional[UUID] = None

    @classmethod
    def from_orm_safe(cls, obj) -> "CrmAutomationEdgeOut":
        return cls(
            id=obj.id,
            source_id=obj.source_id,
            target_id=obj.target_id,
            condition_type=obj.condition_type,
            condition_key=obj.condition_key,
            condition_value=obj.condition_value,
            source_node_id=obj.source_node_id,
            target_node_id=obj.target_node_id,
        )


class AutomationTriggerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_event: str
    context: Dict[str, Any] = {}


class AutomationTriggerResult(BaseModel):
    automation_id: UUID
    automation_name: str
    status: str  # "triggered" | "skipped" | "failed"
    detail: Optional[str] = None

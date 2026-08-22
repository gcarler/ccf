from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    sede_id: Optional[UUID] = None
    name: str
    trigger_type: str
    action_type: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    last_run: Optional[datetime] = None


class AutomationRuleCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    trigger_type: str
    action_type: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AutomationRuleUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


# ══════════════════════════════════════════════════════════════════════════════
# CANONICAL GOVERNANCE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class PolicyBase(BaseModel):
    code: str = Field(..., max_length=50)
    title: str = Field(..., max_length=255)
    category: str = Field(default="OPERACIONAL")  # DOCTRINAL, OPERACIONAL, ADMINISTRATIVA, MINISTERIAL
    content: str
    status: str = Field(default="BORRADOR")  # BORRADOR, EN_REVISION, APROBADA, PUBLICADA, ARCHIVADA
    version: int = Field(default=1)
    effective_date: Optional[datetime] = None


class PolicyCreate(PolicyBase):
    sede_id: Optional[UUID] = None


class PolicyUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    version: Optional[int] = None
    effective_date: Optional[datetime] = None


class PolicyRead(PolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sede_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None
    approved_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ResolutionBase(BaseModel):
    number: str = Field(..., max_length=50)
    title: str = Field(..., max_length=255)
    summary: Optional[str] = None
    content: str
    status: str = Field(default="BORRADOR")  # BORRADOR, APROBADA, FIRMADA, ARCHIVADA
    session_date: Optional[datetime] = None


class ResolutionCreate(ResolutionBase):
    sede_id: Optional[UUID] = None


class ResolutionUpdate(BaseModel):
    number: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    session_date: Optional[datetime] = None


class SignatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resolution_id: UUID
    persona_id: UUID
    persona_name: Optional[str] = None
    signature_hash: Optional[str] = None
    status: str
    observations: Optional[str] = None
    signed_at: Optional[datetime] = None
    created_at: datetime


class SignatureCreate(BaseModel):
    persona_id: UUID
    observations: Optional[str] = None


class SignatureSign(BaseModel):
    signature_hash: str
    observations: Optional[str] = None


class ResolutionRead(ResolutionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sede_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    signatures: List[SignatureRead] = Field(default_factory=list)


class CommitteeMemberBase(BaseModel):
    persona_id: UUID
    role: str = Field(default="VOCAL")  # PRESIDENTE, SECRETARIO, VOCAL, ASESOR
    is_active: bool = True


class CommitteeMemberCreate(CommitteeMemberBase):
    pass


class CommitteeMemberRead(CommitteeMemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    committee_id: UUID
    persona_name: Optional[str] = None
    joined_at: datetime


class CommitteeBase(BaseModel):
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    committee_type: str = Field(default="PASTORAL")  # PASTORAL, FINANCIERO, DISCIPLINARIO, EVENTOS, AUDITORIA
    is_active: bool = True


class CommitteeCreate(CommitteeBase):
    sede_id: Optional[UUID] = None


class CommitteeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    committee_type: Optional[str] = None
    is_active: Optional[bool] = None


class CommitteeRead(CommitteeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sede_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    members: List[CommitteeMemberRead] = Field(default_factory=list)


class GovernanceStats(BaseModel):
    total_policies: int = 0
    published_policies: int = 0
    total_resolutions: int = 0
    signed_resolutions: int = 0
    total_committees: int = 0
    active_committee_members: int = 0

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas._common import orm_config


class PipelineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    pipeline_type: str
    description: str | None = None
    sede_id: UUID | None = None
    is_active: bool = True


class PipelineResponse(BaseModel):
    model_config = orm_config

    id: UUID
    sede_id: UUID
    name: str
    pipeline_type: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PipelineStageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_id: UUID | None = None
    name: str = Field(min_length=1, max_length=100)
    order_index: int = Field(ge=0)
    requires_action: bool = True


class PipelineStageResponse(BaseModel):
    model_config = orm_config

    id: UUID
    pipeline_id: UUID
    name: str
    order_index: int
    requires_action: bool
    created_at: datetime

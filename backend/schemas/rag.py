"""Schemas for Pastoral RAG Hybrid Search."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PastoralSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query text for pastoral search")
    limit: int = Field(10, ge=1, le=100, description="Max number of results to return")
    category: Optional[str] = Field(None, description="Optional category filter (e.g. teologia, biblia, pastoral)")
    alpha: float = Field(0.5, ge=0.0, le=1.0, description="Weight between FTS (0.0) and vector cosine similarity (1.0)")


class PastoralSearchResult(BaseModel):
    id: UUID
    source: str = Field(..., description="Source table/module: 'knowledge_base', 'wiki', or 'sermon'")
    title: str
    content: str
    score: float = Field(..., description="Hybrid fused relevance score")
    sede_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

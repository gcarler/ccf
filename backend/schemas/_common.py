from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

orm_config: ConfigDict = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    Usage:
        return PaginatedResponse[MySchema](
            items=[...],
            total=42,
            skip=0,
            limit=20,
        )
    """

    items: List[T]
    total: int
    skip: int = 0
    limit: int = 20

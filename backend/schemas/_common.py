from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Generic, List, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict

T = TypeVar("T")

orm_config: ConfigDict = ConfigDict(from_attributes=True)


def _ensure_utc(value: Any) -> Any:
    """Axioma — parche SQLite tz-info loss (REGLAS.md §6: fechas persistidas en UTC).

    SQLAlchemy persiste ``DateTime(timezone=True)`` columns a SQLite como
    datetimes NAIVE (sin tzinfo) aún cuando el ORM declara timezone-aware.
    En read-back via ``Session.query(...)`` retorna naive datetimes, lo que
    rompe comparaciones contra ``datetime.now(timezone.utc)`` y serializa como
    naive en JSON. Este helper atacha UTC cuando tzinfo es None.

    Reuso del patrón ``_as_aware_utc`` documentado en MEMORY.md (ses_07a7a9fe,
    aplicado en ``crud/crm_/personas.py:_volunteer_commitment_map``).
    """
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# Campo datetime-aware: atacha UTC a naive datetimes en validation.
# Usar como ``created_at: AwareDateTime`` en lugar de ``datetime`` en read
# schemas que provienen de filas SQLite-stored.
AwareDateTime = Annotated[datetime, BeforeValidator(_ensure_utc)]


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

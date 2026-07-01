from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    cast,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship

from backend.core.database import Base


def _utcnow() -> dt.datetime:
    """Return timezone-aware UTC now. Use this for all DateTime columns."""
    return dt.datetime.now(dt.timezone.utc)

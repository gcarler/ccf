from __future__ import annotations
import datetime as dt
import uuid

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, JSON, Table, UniqueConstraint,
    PrimaryKeyConstraint, func, cast, Index, Float
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import UUID

from backend.core.database import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)

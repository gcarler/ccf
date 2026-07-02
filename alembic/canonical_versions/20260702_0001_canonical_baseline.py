"""Canonical baseline for the current CCF schema.

Revision ID: 20260702_0001_canonical_baseline
Revises: None
Create Date: 2026-07-02 00:00:00

This is the new active baseline after archiving the historical migration
chain as legacy. It materializes the current ORM metadata in one shot so
fresh databases can be brought to head without replaying the old chain.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20260702_0001_canonical_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import backend.models  # noqa: F401
    from backend.core.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import backend.models  # noqa: F401
    from backend.core.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

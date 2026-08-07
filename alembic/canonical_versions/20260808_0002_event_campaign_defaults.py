"""Stable keys for the default event campaign catalog."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0002_event_campaign_defaults"
down_revision: Union[str, None] = "20260808_0001_event_crm_task_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(c["name"] == column for c in _inspector().get_columns(table))


def _has_index(table: str, name: str) -> bool:
    return _has_table(table) and any(i.get("name") == name for i in _inspector().get_indexes(table))


def upgrade() -> None:
    if not _has_table("event_campaigns"):
        raise RuntimeError("La tabla event_campaigns debe existir antes de aplicar esta migración")
    if not _has_column("event_campaigns", "default_key"):
        with op.batch_alter_table("event_campaigns") as batch:
            batch.add_column(sa.Column("default_key", sa.String(60), nullable=True))
    if not _has_index("event_campaigns", "ix_event_campaign_default_key"):
        op.create_index("ix_event_campaign_default_key", "event_campaigns", ["default_key"], unique=False)
    if not _has_index("event_campaigns", "uq_event_campaign_default_key"):
        op.create_index(
            "uq_event_campaign_default_key",
            "event_campaigns",
            ["event_id", "default_key"],
            unique=True,
            postgresql_where=sa.text("default_key IS NOT NULL AND deleted_at IS NULL"),
            sqlite_where=sa.text("default_key IS NOT NULL AND deleted_at IS NULL"),
        )


def downgrade() -> None:
    if not _has_table("event_campaigns"):
        return
    if _has_index("event_campaigns", "uq_event_campaign_default_key"):
        op.drop_index("uq_event_campaign_default_key", table_name="event_campaigns")
    if _has_index("event_campaigns", "ix_event_campaign_default_key"):
        op.drop_index("ix_event_campaign_default_key", table_name="event_campaigns")
    if _has_column("event_campaigns", "default_key"):
        with op.batch_alter_table("event_campaigns") as batch:
            batch.drop_column("default_key")

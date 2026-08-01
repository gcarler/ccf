"""Add tenant scope to campaign seasons.

The original migration was stored under ``alembic/versions`` while this
project's ``alembic.ini`` loads only ``alembic/canonical_versions``. Keep this
migration idempotent so databases that already received the legacy migration
can safely converge without duplicate-column/index errors.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260801_0001_campaign_seasons_sede_id"
down_revision: Union[str, None] = "b26ea7484114"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(item["name"] == column for item in _inspector().get_columns(table))


def _has_index(table: str, index: str) -> bool:
    return _has_table(table) and any(item.get("name") == index for item in _inspector().get_indexes(table))


def _uuid_type() -> sa.types.TypeEngine:
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    if not _has_table("campaign_seasons"):
        return

    if not _has_column("campaign_seasons", "sede_id"):
        with op.batch_alter_table("campaign_seasons") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "sede_id",
                    _uuid_type(),
                    sa.ForeignKey(
                        "sedes.id",
                        name="fk_campaign_seasons_sede_id",
                        ondelete="SET NULL",
                    ),
                    nullable=True,
                )
            )

    if not _has_index("campaign_seasons", "ix_campaign_seasons_sede_id"):
        op.create_index("ix_campaign_seasons_sede_id", "campaign_seasons", ["sede_id"], unique=False)


def downgrade() -> None:
    if not _has_table("campaign_seasons"):
        return

    if _has_index("campaign_seasons", "ix_campaign_seasons_sede_id"):
        op.drop_index("ix_campaign_seasons_sede_id", table_name="campaign_seasons")

    if _has_column("campaign_seasons", "sede_id"):
        inspector = _inspector()
        sede_foreign_keys = [
            fk.get("name")
            for fk in inspector.get_foreign_keys("campaign_seasons")
            if fk.get("referred_table") == "sedes"
            and fk.get("constrained_columns") == ["sede_id"]
            and fk.get("name")
        ]
        with op.batch_alter_table(
            "campaign_seasons",
            naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"},
        ) as batch_op:
            for constraint_name in sede_foreign_keys:
                batch_op.drop_constraint(constraint_name, type_="foreignkey")
            # Batch mode recreates SQLite tables and removes unnamed legacy FKs.
            batch_op.drop_column("sede_id")

"""Persist the end time for Evangelism groups.

The public group contract already accepts and returns ``end_time``. Older
models kept it only as an in-memory compatibility property, so values were
lost after a transaction committed. This migration adds the nullable column
without changing existing rows.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0004_add_evangelism_group_end_time"
down_revision: Union[str, None] = "20260801_0003_name_campaign_seasons_sede_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "grupos_evangelismo"
_COLUMN = "end_time"


def _has_table() -> bool:
    return sa.inspect(op.get_bind()).has_table(_TABLE)


def _has_column() -> bool:
    return _has_table() and any(
        column["name"] == _COLUMN for column in sa.inspect(op.get_bind()).get_columns(_TABLE)
    )


def upgrade() -> None:
    if not _has_table() or _has_column():
        return

    bind = op.get_bind()
    column = sa.Column(_COLUMN, sa.String(length=50), nullable=True)
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(_TABLE) as batch_op:
            batch_op.add_column(column)
    else:
        op.add_column(_TABLE, column)


def downgrade() -> None:
    # Monotonic compatibility migration: the column may have been created by
    # the archived legacy chain before this canonical revision was applied.
    # Never remove it during downgrade because its provenance is unknowable.
    pass

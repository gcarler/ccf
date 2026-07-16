"""Backfill ``projects.sede_id`` where NULL.

Revision ID: 20260716_0001
Revises: 20260715_0001
Create Date: 2026-07-16

This migration repairs legacy projects that still have ``sede_id = NULL``.
That backfill is required because ``backend.api.projects._ensure_project``
now treats seated actors as strictly scoped, so NULL projects would become
invisible without a one-time data repair.
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260716_0001"
down_revision = "20260715_0001"
branch_labels = None
depends_on = None


BACKFILL_QUERY = """
WITH resolved AS (
    SELECT
        p.id,
        COALESCE(
            NULLIF(:env_sede_id, '')::uuid,
            per.sede_id,
            (
                SELECT sede_id
                FROM projects
                WHERE sede_id IS NOT NULL
                GROUP BY sede_id
                ORDER BY COUNT(*) DESC, sede_id
                LIMIT 1
            )
        ) AS new_sede_id
    FROM projects p
    LEFT JOIN personas per ON per.id = p.owner_id
    WHERE p.sede_id IS NULL
)
UPDATE projects
SET sede_id = resolved.new_sede_id
FROM resolved
WHERE projects.id = resolved.id
  AND resolved.new_sede_id IS NOT NULL
"""


def upgrade() -> None:
    """Backfill NULL ``sede_id`` on projects."""
    bind = op.get_bind()
    env_sede_id = os.environ.get("CCF_DEFAULT_SEDE_ID", "")

    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM projects WHERE sede_id IS NULL")
    ).scalar_one()
    print(f"[20260716_0001] projects with NULL sede_id found: {null_count}")

    if null_count == 0:
        print("[20260716_0001] nothing to backfill, skipping UPDATE.")
        return

    result = bind.execute(
        sa.text(BACKFILL_QUERY).bindparams(env_sede_id=env_sede_id)
    )
    print(f"[20260716_0001] rows updated: {result.rowcount}")

    remaining_nulls = bind.execute(
        sa.text("SELECT COUNT(*) FROM projects WHERE sede_id IS NULL")
    ).scalar_one()
    if remaining_nulls:
        print(
            f"[20260716_0001] WARNING: {remaining_nulls} rows still NULL after "
            "backfill. Configure CCF_DEFAULT_SEDE_ID or assign manually."
        )


def downgrade() -> None:
    """No-op downgrade.

    Without an audit trail we cannot deterministically identify which rows
    were backfilled, so reverting the migration is intentionally manual.
    """
    print(
        "[20260716_0001] downgrade is a no-op: this migration does not "
        "remember which rows it updated."
    )

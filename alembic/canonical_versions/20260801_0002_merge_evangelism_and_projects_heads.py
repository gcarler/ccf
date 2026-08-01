"""Merge Evangelism and Projects migration heads.

Revision ID: 20260801_0002_merge_evangelism_and_projects_heads
Revises: 20260801_0001_campaign_seasons_sede_id, a9b3c4d5e6f7
Create Date: 2026-08-01 00:00:00.000000

This is a graph-only merge. The two parent migrations retain their own
upgrade/downgrade operations; this revision only makes ``alembic upgrade
head`` unambiguous for databases that converge both branches.
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "20260801_0002_merge_evangelism_and_projects_heads"
down_revision: Union[str, tuple[str, str]] = (
    "20260801_0001_campaign_seasons_sede_id",
    "a9b3c4d5e6f7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

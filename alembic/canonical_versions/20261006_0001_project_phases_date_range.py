"""Add start_date and end_date columns to project_phases table.

Revision ID: 20261006_0001_project_phases_date_range
Revises: 20261005_0003_auth_notification_target_url

Enables strict date boundary enforcement for project phases and their tasks,
preventing task schedules from drifting outside phase boundaries.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261006_0001_project_phases_date_range"
down_revision: Union[str, None] = "20261005_0003_auth_notification_target_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_phases",
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "project_phases",
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_phases", "end_date")
    op.drop_column("project_phases", "start_date")

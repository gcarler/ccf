"""Add same-origin deep links to in-app notifications.

Revision ID: 20261005_0003_auth_notification_target_url
Revises: 20261005_0002_projects_timelog_persona_fk_restrict

Projects comment mentions already computed a destination, but the shared
notification row and API contract discarded it. This nullable column is
additive: existing notification producers and stored rows remain compatible.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261005_0003_auth_notification_target_url"
down_revision: Union[str, None] = "20261005_0002_projects_timelog_persona_fk_restrict"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auth_notifications",
        sa.Column("target_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("auth_notifications", "target_url")

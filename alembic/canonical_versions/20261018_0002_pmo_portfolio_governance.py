"""Add PMI development approach and PMO typology to project charters."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261018_0002_pmo_portfolio_governance"
down_revision: Union[str, None] = "20261018_0001_projects_pmi_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_lifecycles",
        sa.Column("development_approach", sa.String(length=20), server_default="hybrid", nullable=False),
    )
    op.add_column(
        "project_lifecycles",
        sa.Column("pmo_type", sa.String(length=20), server_default="controlling", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("project_lifecycles", "pmo_type")
    op.drop_column("project_lifecycles", "development_approach")

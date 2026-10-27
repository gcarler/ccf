"""Add coq_amount to project_dod_acceptances table for PMI Cost of Quality tracking."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261024_0001_add_coq_amount_to_project_dod_acceptances"
down_revision: Union[str, None] = "20261018_0002_pmo_portfolio_governance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_dod_acceptances",
        sa.Column("coq_amount", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_dod_acceptances", "coq_amount")

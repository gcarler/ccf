"""add sede_id to campaign_seasons for tenant scoping

Revision ID: 20260726_0002
Revises: 20260726_0001
Create Date: 2026-07-26

Adds nullable sede_id FK to campaign_seasons so seasons can be scoped
per tenant.  Existing rows retain NULL (global/backward-compatible).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260726_0002"
down_revision: Union[str, None] = "20260726_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_seasons",
        sa.Column("sede_id", UUID(as_uuid=True), sa.ForeignKey("sedes.id"), nullable=True),
    )
    op.create_index("ix_campaign_seasons_sede_id", "campaign_seasons", ["sede_id"])


def downgrade() -> None:
    op.drop_index("ix_campaign_seasons_sede_id", table_name="campaign_seasons")
    op.drop_column("campaign_seasons", "sede_id")

"""0039_rename_faro_to_campaign

Revision ID: 20260527_0039
Revises: 20260527_0038
Create Date: 2026-05-27

Renames faro_seasons → campaign_seasons for church-agnostic platform.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260527_0039"
down_revision: Union[str, None] = "20260527_0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("faro_seasons", "campaign_seasons")


def downgrade() -> None:
    op.rename_table("campaign_seasons", "faro_seasons")

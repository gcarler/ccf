"""merge_heads

Revision ID: 575eec15ec67
Revises: 20260730_0001_cms_sections_m1_blocks, 20260730_0006_add_cms_newsletter, 20260731_0008_add_cms_post_comments, f91e628eb3a0
Create Date: 2026-07-31 13:54:37.712549

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "575eec15ec67"
down_revision: Union[str, None] = (
    "20260730_0001_cms_sections_m1_blocks",
    "20260730_0006_add_cms_newsletter",
    "20260731_0008_add_cms_post_comments",
    "f91e628eb3a0",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

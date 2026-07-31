"""merge heads

Revision ID: 0461885be9c9
Revises: 20260730_0001_drop_legacy_testimonials_table, 20260730_0002_migrate_announcements_to_cms_posts
Create Date: 2026-07-30 03:19:53.702924

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0461885be9c9"
down_revision: Union[str, None] = (
    "20260730_0001_drop_legacy_testimonials_table",
    "20260730_0002_migrate_announcements_to_cms_posts",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

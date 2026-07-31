"""Add M1 section block types to cms_section_types

Revision ID: 20260730_0001_cms_sections_m1_blocks
Revises: 20260706_0003_cms_sections_phase2
Create Date: 2026-07-30 00:01:00

Inserts 4 section block types into `cms_section_types`:
- animated_counter
- video_embed
- gallery_masonry
- map_embed
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "20260730_0001_cms_sections_m1_blocks"
down_revision: Union[str, None] = "20260706_0003_cms_sections_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

M1_SECTION_TYPES = [
    "animated_counter",
    "video_embed",
    "gallery_masonry",
    "map_embed",
]


def _has_table(table: str) -> bool:
    return table in set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _has_table("cms_section_types"):
        for name in M1_SECTION_TYPES:
            op.execute(
                sa.text(
                    "INSERT INTO cms_section_types (name, is_active) VALUES (:name, true) "
                    "ON CONFLICT (name) DO NOTHING"
                ).bindparams(name=name)
            )


def downgrade() -> None:
    if _has_table("cms_section_types"):
        op.execute(
            sa.text(
                "DELETE FROM cms_section_types WHERE name = ANY(:names)"
            ).bindparams(names=M1_SECTION_TYPES)
        )

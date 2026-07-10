"""cms_sections soft-delete + Phase 2 section types

Revision ID: 20260706_0003_cms_sections_phase2
Revises: 20260706_0002
create Date: 2026-07-06 12:00:00

1. Adds ``cms_sections.deleted_at`` (nullable) with index for soft-delete.
2. Seeds the section types introduced in Phase 2 so the public pages can
   reference them from CMS sections.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "20260706_0003_cms_sections_phase2"
down_revision: Union[str, None] = "20260706_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Section types added during Phase 2 (public-page content migration).
PHASE2_SECTION_TYPES = [
    "events_calendar",
    "video_grid",
    "locations_list",
    "contact_form",
    "prayer_form",
    "course_grid",
    "book_shop",
    "testimonials_masonry",
    "policy_document",
    "footer_config",
    "mobile_menu_config",
]


def _has_table(table: str) -> bool:
    return table in set(sa.inspect(op.get_bind()).get_table_names())


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col.get("name") == column for col in sa.inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    # 1. Soft-delete support on cms_sections
    if _has_table("cms_sections") and not _has_column("cms_sections", "deleted_at"):
        op.add_column(
            "cms_sections",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_cms_sections_deleted_at", "cms_sections", ["deleted_at"])

    # 2. Seed Phase 2 section types
    if _has_table("cms_section_types"):
        for name in PHASE2_SECTION_TYPES:
            op.execute(
                sa.text(
                    "INSERT INTO cms_section_types (name, is_active) VALUES (:name, true) "
                    "ON CONFLICT (name) DO NOTHING"
                ).bindparams(name=name)
            )


def downgrade() -> None:
    if _has_table("cms_sections") and _has_column("cms_sections", "deleted_at"):
        op.drop_index("ix_cms_sections_deleted_at", "cms_sections")
        op.drop_column("cms_sections", "deleted_at")

    if _has_table("cms_section_types"):
        op.execute(
            sa.text(
                "DELETE FROM cms_section_types WHERE name = ANY(:names)"
            ).bindparams(names=PHASE2_SECTION_TYPES)
        )

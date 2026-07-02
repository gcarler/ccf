"""Add cms_section_types table and deleted_at index on cms_sections

Revision ID: 20260702_0001_cms_section_types
Revises: 20260701_0003_crm_events_uuid
Create Date: 2026-07-02 12:00:00

This migration:
1. Creates the ``cms_section_types`` table to store allowed section types
   in the database instead of hardcoding them in the application.
2. Adds a ``deleted_at`` column with index to ``cms_sections`` for
   soft-delete support.

The section_types table is seeded with all currently supported section types.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "20260702_0001_cms_section_types"
down_revision: Union[str, None] = "20260701_0003_crm_events_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All supported section types (from cms_v2.py ALLOWED_SECTION_TYPES)
SECTION_TYPES = [
    # Existing 19
    "hero",
    "video_hero",
    "rich_text",
    "rich_text_columns",
    "cards",
    "cta_banner",
    "gallery",
    "faq",
    "embed",
    "testimonials",
    "stats",
    "team",
    "countdown",
    "pricing",
    "image_text",
    "timeline",
    "icon_grid",
    "newsletter",
    "popup_banner",
    # New 11
    "button",
    "toc",
    "divider",
    "collapsible",
    "social_links",
    "spacer",
    "calendar",
    "map",
    "document_upload",
    "content_blocks",
    "accordion",
]


def _has_table(table: str) -> bool:
    """Check if a table exists."""
    return table in set(sa.inspect(op.get_bind()).get_table_names())


def _has_column(table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    if not _has_table(table):
        return False
    return any(col.get("name") == column for col in sa.inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    # 1. Create cms_section_types table
    if not _has_table("cms_section_types"):
        op.create_table(
            "cms_section_types",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("name", sa.String(80), nullable=False, unique=True, index=True),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean, default=True, index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

        # Seed with all current section types
        for name in SECTION_TYPES:
            op.execute(
                sa.text(
                    "INSERT INTO cms_section_types (name, is_active) VALUES (:name, true) "
                    "ON CONFLICT (name) DO NOTHING"
                ).bindparams(name=name)
            )

    # 2. Add deleted_at column to cms_sections if not present
    if _has_table("cms_sections") and not _has_column("cms_sections", "deleted_at"):
        op.add_column(
            "cms_sections",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_cms_sections_deleted_at", "cms_sections", ["deleted_at"])


def downgrade() -> None:
    # Remove deleted_at from cms_sections
    if _has_table("cms_sections") and _has_column("cms_sections", "deleted_at"):
        op.drop_index("ix_cms_sections_deleted_at", "cms_sections")
        op.drop_column("cms_sections", "deleted_at")

    # Drop section types table
    op.drop_table("cms_section_types")

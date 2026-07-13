"""Rename cms_sites site_key from 'faro' to 'ccf' (FARO → CCF migration)

Revision ID: 20260703_0002_rename_faro_site_key
Revises: 20260703_0001_cms_sites_sede_id
Create Date: 2026-07-03 12:00:00

Rename the site_key 'faro' to 'ccf' across all CMS tables:
- cms_sites.site_key
- cms_menus (via site_id FK)
- cms_pages (via site_id FK)
- cms_themes (via site_id FK)

Also updates cms_section_types to ensure all current types are present.

Idempotent: safe to re-run without side effects.
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260703_0002_rename_faro_site_key"
down_revision: Union[str, None] = "20260703_0001_add_cms_posts_categories_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return table in set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _has_table("cms_sites"):
        return

    conn = op.get_bind()

    # Rename site_key from 'faro' to 'ccf' if it exists
    result = conn.execute(
        sa.text("SELECT id FROM cms_sites WHERE site_key = :old_key"),
        {"old_key": "faro"},
    ).fetchone()

    if result:
        conn.execute(
            sa.text("UPDATE cms_sites SET site_key = :new_key WHERE site_key = :old_key"),
            {"new_key": "ccf", "old_key": "faro"},
        )
        # Also update name if it's 'FARO'
        conn.execute(
            sa.text("UPDATE cms_sites SET name = :new_name WHERE name = :old_name"),
            {"new_name": "CCF", "old_name": "FARO"},
        )

    # Ensure cms_section_types has all current types
    if _has_table("cms_section_types"):
        current_types = {
            "hero", "video_hero", "rich_text", "rich_text_columns",
            "cards", "cta_banner", "gallery", "faq", "embed",
            "testimonials", "stats", "team", "countdown", "pricing",
            "image_text", "timeline", "icon_grid", "newsletter",
            "popup_banner", "button", "toc", "divider", "collapsible",
            "social_links", "spacer", "calendar", "map",
            "document_upload", "content_blocks", "accordion",
        }

        existing = {
            row[0]
            for row in conn.execute(
                sa.text("SELECT name FROM cms_section_types")
            ).fetchall()
        }

        for name in current_types - existing:
            conn.execute(
                sa.text(
                    "INSERT INTO cms_section_types (id, name, is_active) "
                    "VALUES (:id, :name, true) ON CONFLICT (name) DO NOTHING"
                ),
                {"id": str(uuid.uuid4()), "name": name},
            )


def downgrade() -> None:
    if not _has_table("cms_sites"):
        return

    conn = op.get_bind()

    # Revert site_key back to 'faro'
    conn.execute(
        sa.text("UPDATE cms_sites SET site_key = :old_key WHERE site_key = :new_key"),
        {"new_key": "ccf", "old_key": "faro"},
    )
    conn.execute(
        sa.text("UPDATE cms_sites SET name = :old_name WHERE name = :new_name"),
        {"new_name": "CCF", "old_name": "FARO"},
    )

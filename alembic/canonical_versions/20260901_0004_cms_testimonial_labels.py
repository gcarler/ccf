"""Add the remaining testimonial list label to published CMS content."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0004"
down_revision: Union[str, None] = "20260901_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s
           SET props_json = jsonb_set(
             s.props_json::jsonb, '{content}',
             (((s.props_json->>'content')::jsonb || '{"read_more_label":"Leer más"}'::jsonb)::text)::jsonb
           )::json,
               updated_at = CURRENT_TIMESTAMP
          FROM cms_pages p
          JOIN cms_sites st ON st.id = p.site_id
         WHERE p.id = s.page_id AND st.site_key = 'ccf'
           AND p.slug = 'testimonials' AND s.section_key = 'feed'
           AND s.props_json->'content' IS NOT NULL
    """)
    op.execute("""
        UPDATE cms_page_versions v
           SET snapshot_json = jsonb_set(
             v.snapshot_json::jsonb, '{sections}',
             (SELECT jsonb_agg(jsonb_build_object(
                 'id', s.id::text, 'section_key', s.section_key, 'type', s.type,
                 'props_json', s.props_json::jsonb, 'sort_order', s.sort_order,
                 'is_visible', s.is_visible, 'status', COALESCE(s.status, 'active')
             ) ORDER BY s.sort_order NULLS LAST, s.section_key)::jsonb
                FROM cms_sections s
               WHERE s.page_id = p.id AND s.deleted_at IS NULL)::jsonb
           )::json
          FROM cms_pages p
          JOIN cms_sites st ON st.id = p.site_id
         WHERE v.id = p.published_version_id
           AND st.site_key = 'ccf' AND p.slug = 'testimonials'
    """)


def downgrade() -> None:
    pass

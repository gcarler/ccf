"""Move remaining visible media labels into CMS feeds."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0008"
down_revision: Union[str, None] = "20260901_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s SET props_json=(s.props_json::jsonb || '{"lessons_label":"clases"}'::jsonb)::json, updated_at=CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='courses' AND s.section_key='feed'
    """)
    op.execute("""
        UPDATE cms_sections s SET props_json=jsonb_set(s.props_json::jsonb,'{content}',(((s.props_json->>'content')::jsonb || '{"media_video_label":"Video","media_podcast_label":"Podcast","media_image_label":"Imagen"}'::jsonb)::text)::jsonb)::json, updated_at=CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='testimonials' AND s.section_key='feed'
    """)
    op.execute("""
        UPDATE cms_sections s SET props_json=jsonb_set(s.props_json::jsonb,'{content}',(((s.props_json->>'content')::jsonb || '{"watched_label":"Visto"}'::jsonb)::text)::jsonb)::json, updated_at=CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='sermons' AND s.section_key='feed'
    """)


def downgrade() -> None:
    pass

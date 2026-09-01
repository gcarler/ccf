"""Move calendar weekday labels into the published events CMS feed."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0006"
down_revision: Union[str, None] = "20260901_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s
           SET props_json = jsonb_set(
             s.props_json::jsonb, '{content}',
             (((s.props_json->>'content')::jsonb || '{
               "weekday_short_names":["D","L","M","X","J","V","S"],
               "weekday_names":["Dom","Lun","Mar","Mie","Jue","Vie","Sab"]
             }'::jsonb)::text)::jsonb
           )::json,
               updated_at = CURRENT_TIMESTAMP
          FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
         WHERE p.id=s.page_id AND st.site_key='ccf'
           AND p.slug='events' AND s.section_key='feed'
    """)


def downgrade() -> None:
    pass

"""Move relative sermon time labels into the CMS feed."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0009"
down_revision: Union[str, None] = "20260901_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s SET props_json=jsonb_set(s.props_json::jsonb,'{content}',(((s.props_json->>'content')::jsonb || '{
          "time_today":"hoy","time_yesterday":"ayer","time_days":"hace {count} días",
          "time_weeks":"hace {count} sem.","time_months":"hace {count} meses",
          "time_year":"hace {count} año","time_years":"hace {count} años"
        }'::jsonb)::text)::jsonb)::json,updated_at=CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='sermons' AND s.section_key='feed'
    """)


def downgrade() -> None:
    pass

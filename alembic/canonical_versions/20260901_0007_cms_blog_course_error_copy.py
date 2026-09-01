"""Move public blog/course error copy into CMS feed sections."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0007"
down_revision: Union[str, None] = "20260901_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s
           SET props_json = (s.props_json::jsonb || '{
             "not_found_title":"Artículo no encontrado",
             "not_found_description":"El post que buscas no existe o no está publicado.",
             "back_to_blog_label":"Volver al blog"
           }'::jsonb)::json,
               updated_at = CURRENT_TIMESTAMP
          FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
         WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='blog' AND s.section_key='feed'
    """)
    op.execute("""
        UPDATE cms_sections s
           SET props_json = (s.props_json::jsonb || '{
             "load_error_title":"No pudimos cargar los cursos",
             "load_error_description":"Intenta recargar la página en unos segundos.",
             "retry_label":"Reintentar"
           }'::json)::json,
               updated_at = CURRENT_TIMESTAMP
          FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
         WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='courses' AND s.section_key='feed'
    """)


def downgrade() -> None:
    pass

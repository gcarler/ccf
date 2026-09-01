"""Create CMS-owned templates for public course and pastor detail pages."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0005"
down_revision: Union[str, None] = "20260901_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO cms_sections (id,page_id,section_key,type,props_json,sort_order,is_visible,status,is_global,locale,created_at,updated_at)
        SELECT gen_random_uuid(),p.id,'detail_template','rich_text','{
          "course_tag_fallback":"Academia",
          "course_modality_fallback":"Online",
          "course_lessons_fallback":"Programa de Formación CCF",
          "course_lessons_suffix":"Semanas de Formación",
          "course_featured_modality_fallback":"Acceso Gratuito",
          "course_featured_cta_fallback":"Inscribirme Gratis",
          "course_card_modality_fallback":"Gratuito",
          "back_to_courses_label":"Volver a Academia"
        }'::json,99,true,'active',false,'es',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE st.site_key='ccf' AND p.slug='courses'
          AND NOT EXISTS (SELECT 1 FROM cms_sections x WHERE x.page_id=p.id AND x.section_key='detail_template')
    """)
    op.execute("""
        INSERT INTO cms_sections (id,page_id,section_key,type,props_json,sort_order,is_visible,status,is_global,locale,created_at,updated_at)
        SELECT gen_random_uuid(),p.id,'detail_template','rich_text','{
          "not_found_title":"Pastor no encontrado",
          "not_found_description":"El enlace que buscas no existe o ha sido movido.",
          "role_fallback":"Pastor",
          "social_follow_label":"Síguelo en"
          ,"back_to_pastors_label":"Todos los pastores"
        }'::json,99,true,'active',false,'es',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE st.site_key='ccf' AND p.slug='pastors'
          AND NOT EXISTS (SELECT 1 FROM cms_sections x WHERE x.page_id=p.id AND x.section_key='detail_template')
    """)


def downgrade() -> None:
    pass

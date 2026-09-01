"""Add CMS-owned copy used by home and testimonial detail routes."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0003"
down_revision: Union[str, None] = "20260901_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s
           SET props_json = ((s.props_json::jsonb || '{
             "newsletter_sending_label": "Enviando...",
             "newsletter_success_toast": "¡Suscrito al boletín de El Faro!",
             "newsletter_error_toast": "No se pudo suscribir. Intenta de nuevo."
           }'::jsonb)::text)::json,
               updated_at = CURRENT_TIMESTAMP
          FROM cms_pages p
          JOIN cms_sites st ON st.id = p.site_id
         WHERE p.id = s.page_id AND st.site_key = 'ccf'
           AND p.slug = 'home' AND s.section_key = 'feed'
    """)
    op.execute("""
        INSERT INTO cms_sections (
            id, page_id, section_key, type, props_json, sort_order,
            is_visible, status, is_global, locale, created_at, updated_at
        )
        SELECT gen_random_uuid(), p.id, 'detail_template', 'rich_text',
               '{
                 "back_label": "Volver a testimonios",
                 "not_found_title": "Testimonio no encontrado",
                 "not_found_description": "Parece que la historia que buscas ya no está disponible o el enlace es incorrecto.",
                 "not_found_cta": "Ver más testimonios"
               }'::json, 99, true, 'active', false, 'es', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
          FROM cms_pages p
          JOIN cms_sites st ON st.id = p.site_id
         WHERE st.site_key = 'ccf' AND p.slug = 'testimonials'
           AND NOT EXISTS (
               SELECT 1 FROM cms_sections existing
                WHERE existing.page_id = p.id AND existing.section_key = 'detail_template'
           )
    """)
    # Public API serves the published snapshot. Rebuild only these snapshots
    # from their CMS rows so no section can be duplicated or left stale.
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
           AND st.site_key = 'ccf' AND p.slug IN ('home', 'testimonials')
    """)


def downgrade() -> None:
    # Editorial values may be changed after deployment; restore from the
    # content backup rather than deleting an editor's later work.
    pass

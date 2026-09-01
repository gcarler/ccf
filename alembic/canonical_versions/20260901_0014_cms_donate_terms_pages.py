"""Create the missing CMS pages used by the public donate and terms routes.

The current public pages are the source material for these initial records.  The
records are intentionally idempotent so a deployment cannot overwrite later
editorial changes made in the CMS.
"""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260901_0014"
down_revision: Union[str, None] = "20260901_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DONATE_HERO = {
    "header_label": "Generosidad",
    "badge": "Tu siembra tiene propósito",
    "title": "Honramos a Dios",
    "title_connector": "con nuestra",
    "title_accent": "generosidad.",
    "description": "Cada ofrenda y diezmo fortalece la misión de transformar vidas y comunidades a través del evangelio.",
    "benefit1_title": "Seguridad Total",
    "benefit1_desc": "Tus transacciones están protegidas con encriptación de nivel bancario.",
    "benefit2_title": "Impacto Global",
    "benefit2_desc": "Apoyas misiones y ayuda social en toda la región.",
}

DONATE_FEED = {
    "amounts": ["20", "50", "100", "200"],
    "default_amount": "50",
    "amounts_label": "Selecciona un monto",
    "custom_amount_label": "Otra cantidad personalizada",
    "type_label": "Destino de la semilla",
    "diezmo_value": "Diezmo",
    "diezmo_label": "Diezmo",
    "ofrenda_value": "Ofrenda",
    "ofrenda_label": "Ofrenda",
    "pay_button_label": "Pagar con MercadoPago",
    "connecting_label": "Conectando...",
    "manual_button_label": "Registrar como recibido",
    "manual_divider_label": "O registra manualmente",
    "ssl_label": "Secure SSL",
    "verified_label": "Verified Merchant",
    "success_title_approved": "¡Ofrenda Recibida!",
    "success_title_pending": "Pago Pendiente",
    "success_desc_approved": "Tu generosidad permite que el ministerio siga creciendo y alcanzando más vidas.",
    "success_desc_pending": "Tu pago está siendo procesado. Te notificaremos cuando se confirme.",
    "amount_label": "Monto Sembrado",
    "category_label": "Categoría",
    "back_home_label": "Volver al Inicio",
    "toast_success": "¡Gracias por tu generosidad!",
    "toast_error": "Error al procesar",
    "toast_mp_error": "Error al iniciar pago con MercadoPago",
    "toast_mp_pending": "Tu pago está siendo procesado.",
    "toast_mp_failure": "El pago no pudo completarse. Intenta de nuevo.",
}

TERMS_HERO = {
    "title": "Términos de Servicio",
    "subtitle": "Última actualización: 12 de Marzo, 2026",
    "body": "Los términos de servicio de la plataforma se encuentran en construcción. Para dudas, contacta al equipo pastoral.",
}


def _ensure_page(bind: sa.Connection, slug: str, title: str) -> None:
    page_id = bind.execute(
        sa.text("SELECT id FROM cms_pages WHERE site_id=(SELECT id FROM cms_sites WHERE site_key='ccf') AND slug=:slug"),
        {"slug": slug},
    ).scalar_one_or_none()
    if page_id is None:
        bind.execute(
            sa.text("""
                INSERT INTO cms_pages (id, site_id, slug, title, status, seo_json, locale, created_at, updated_at)
                VALUES (gen_random_uuid(), (SELECT id FROM cms_sites WHERE site_key='ccf'), :slug, :title,
                        'published', '{}'::json, 'es', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {"slug": slug, "title": title},
        )


def _ensure_section(bind: sa.Connection, slug: str, key: str, section_type: str, props: dict, order: int) -> None:
    bind.execute(
        sa.text("""
            INSERT INTO cms_sections (id, page_id, section_key, type, props_json, sort_order, is_visible, status, locale, created_at, updated_at)
            SELECT gen_random_uuid(), p.id, :section_key, :section_type, CAST(:props AS json), :sort_order, TRUE, 'active', 'es', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM cms_pages p JOIN cms_sites s ON s.id=p.site_id
            WHERE s.site_key='ccf' AND p.slug=:slug
              AND NOT EXISTS (SELECT 1 FROM cms_sections x WHERE x.page_id=p.id AND x.section_key=:section_key)
        """),
        {"slug": slug, "section_key": key, "section_type": section_type, "props": json.dumps(props, ensure_ascii=False), "sort_order": order},
    )


def _ensure_published_snapshot(bind: sa.Connection, slug: str) -> None:
    bind.execute(sa.text("""
        INSERT INTO cms_page_versions (id, page_id, version_number, snapshot_json, notes, created_at)
        SELECT gen_random_uuid(), p.id, 1,
               json_build_object(
                 'page', json_build_object('id', p.id, 'slug', p.slug, 'title', p.title, 'status', p.status, 'seo_json', COALESCE(p.seo_json, '{}'::json)),
                 'sections', COALESCE((SELECT json_agg(json_build_object(
                   'id', s.id, 'section_key', s.section_key, 'type', s.type, 'props_json', COALESCE(s.props_json, '{}'::json),
                   'sort_order', s.sort_order, 'is_visible', s.is_visible, 'status', s.status
                 ) ORDER BY s.sort_order) FROM cms_sections s WHERE s.page_id=p.id AND s.deleted_at IS NULL), '[]'::json)
               ),
               'Initial migration from the published public route', CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE st.site_key='ccf' AND p.slug=:slug AND p.published_version_id IS NULL
    """), {"slug": slug})
    bind.execute(sa.text("""
        UPDATE cms_pages p SET published_version_id=(
          SELECT v.id FROM cms_page_versions v WHERE v.page_id=p.id ORDER BY v.version_number DESC LIMIT 1
        ), updated_at=CURRENT_TIMESTAMP
        FROM cms_sites st
        WHERE st.id=p.site_id AND st.site_key='ccf' AND p.slug=:slug AND p.published_version_id IS NULL
    """), {"slug": slug})


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_page(bind, "donate", "Generosidad")
    _ensure_section(bind, "donate", "hero", "hero", DONATE_HERO, 0)
    _ensure_section(bind, "donate", "feed", "feed", DONATE_FEED, 1)
    _ensure_published_snapshot(bind, "donate")

    _ensure_page(bind, "terms", "Términos de Servicio")
    _ensure_section(bind, "terms", "hero", "rich_text", TERMS_HERO, 0)
    _ensure_published_snapshot(bind, "terms")


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        DELETE FROM cms_pages
        WHERE site_id=(SELECT id FROM cms_sites WHERE site_key='ccf') AND slug IN ('donate', 'terms')
    """))

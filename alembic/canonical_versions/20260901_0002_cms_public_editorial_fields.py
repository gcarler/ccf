"""Promote visible public fallback copy into the canonical CMS pages.

The values below are the copy already used by the public renderers.  Keeping
them in the published CMS snapshot makes the editor able to change what the
visitor sees without changing frontend code.
"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260901_0002"
down_revision: Union[str, None] = "20260901_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EVENT_EDITORIAL = {
    "filters_title": "Filtrar por categoría",
    "sync_calendar_cta": "Sincronizar calendario",
    "sync_calendar_toast": "Calendario sincronizado",
    "notifications_title": "Mantente al día",
    "notifications_desc": "Recibe avisos de nuestras próximas actividades.",
    "notifications_toast": "Notificaciones activadas",
    "highlights_title": "Destacados",
    "highlights_empty": "No hay eventos destacados por ahora.",
    "no_upcoming_label": "No hay próximos eventos",
    "no_location": "Ubicación por confirmar",
    "month_names": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
    "week_view_label": "Semanal",
    "month_view_label": "Mensual",
    "year_view_label": "Anual",
}

NEWSLETTER_EDITORIAL = {
    "description": "Meditaciones semanales, eventos exclusivos y más.\nDirecto a tu correo.",
    "cta_text": "Suscribirme",
    "success_message": "¡Gracias por suscribirte!",
    "email_placeholder": "Tu correo electrónico",
    "sending_label": "Enviando...",
    "success_toast": "¡Suscrito al boletín de El Faro!",
    "error_message": "No se pudo suscribir. Intenta de nuevo.",
}

BLOG_FEED_EDITORIAL = {"read_more_label": "Leer más"}
BLOG_ARCHIVE_EDITORIAL = {
    "back_to_blog_label": "Volver al blog",
    "empty_category_title": "Sin artículos en esta categoría",
    "empty_category_description": "No hay posts publicados en esta categoría todavía.",
    "back_to_blog_label_tag": "Volver al blog",
    "empty_tag_title": "Sin artículos con esta etiqueta",
    "empty_tag_description": "No hay posts publicados con esta etiqueta todavía.",
}


def _merge_section(bind: Any, slug: str, section_key: str, additions: dict[str, Any]) -> None:
    page = bind.execute(
        sa.text("""
            SELECT p.id, p.published_version_id
              FROM cms_pages p
              JOIN cms_sites s ON s.id = p.site_id
             WHERE s.site_key = 'ccf' AND p.slug = :slug
             ORDER BY p.updated_at DESC, p.id DESC
             LIMIT 1
        """),
        {"slug": slug},
    ).mappings().first()
    if not page:
        return

    section = bind.execute(
        sa.text("SELECT id, props_json FROM cms_sections WHERE page_id = :page_id AND section_key = :section_key LIMIT 1"),
        {"page_id": page["id"], "section_key": section_key},
    ).mappings().first()
    if not section:
        return

    props = dict(section["props_json"] or {})
    changed = False
    for key, value in additions.items():
        if key == "content" and isinstance(props.get(key), str):
            try:
                nested = json.loads(props[key])
            except (TypeError, json.JSONDecodeError):
                nested = None
            if isinstance(nested, dict) and isinstance(value, str):
                additions_nested = json.loads(value)
                for nested_key, nested_value in additions_nested.items():
                    if nested_key not in nested:
                        nested[nested_key] = nested_value
                        changed = True
                props[key] = json.dumps(nested, ensure_ascii=False)
            continue
        if key not in props:
            props[key] = value
            changed = True
    if not changed:
        return

    bind.execute(
        sa.text("UPDATE cms_sections SET props_json = CAST(:props AS json), updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
        {"id": section["id"], "props": json.dumps(props, ensure_ascii=False)},
    )

    version_id = page["published_version_id"]
    if not version_id:
        return
    version = bind.execute(sa.text("SELECT snapshot_json FROM cms_page_versions WHERE id = :id"), {"id": version_id}).scalar_one_or_none()
    if not version:
        return
    snapshot = dict(version)
    for snapshot_section in snapshot.get("sections", []):
        if snapshot_section.get("section_key") == section_key:
            snapshot_props = dict(snapshot_section.get("props_json") or {})
            for key, value in additions.items():
                if key == "content" and isinstance(snapshot_props.get(key), str):
                    try:
                        nested = json.loads(snapshot_props[key])
                    except (TypeError, json.JSONDecodeError):
                        nested = None
                    if isinstance(nested, dict) and isinstance(value, str):
                        for nested_key, nested_value in json.loads(value).items():
                            nested.setdefault(nested_key, nested_value)
                        snapshot_props[key] = json.dumps(nested, ensure_ascii=False)
                else:
                    snapshot_props.setdefault(key, value)
            snapshot_section["props_json"] = snapshot_props
    bind.execute(
        sa.text("UPDATE cms_page_versions SET snapshot_json = CAST(:snapshot AS json) WHERE id = :id"),
        {"id": version_id, "snapshot": json.dumps(snapshot, ensure_ascii=False)},
    )


def upgrade() -> None:
    bind = op.get_bind()
    _merge_section(bind, "events", "feed", {"content": json.dumps(EVENT_EDITORIAL, ensure_ascii=False)})
    _merge_section(bind, "newsletter", "hero", NEWSLETTER_EDITORIAL)
    _merge_section(bind, "blog", "feed", BLOG_FEED_EDITORIAL)
    _merge_section(bind, "blog", "archive_template", BLOG_ARCHIVE_EDITORIAL)


def downgrade() -> None:
    # The migration only fills absent keys; removing them blindly could erase
    # an editor's later changes.  Restore from the pre-alignment backup when a
    # full rollback of editorial copy is required.
    pass

#!/usr/bin/env python3
"""Merge secondary public texts (read_more, calendar labels, archive labels)
into existing published CMS sections.

The canonical seeds in ``seed_public_cms_v2_sections.py`` only initialise pages
without sections, so keys added later would never reach pages already managed
by the CMS. This script is the non-destructive migration for those cases: it
adds the new keys when they are missing (keeping every other editor value) and
republishes only the pages whose snapshot actually changed.

Usage:
    cd /root/ccf && source venv/bin/activate && python scripts/seed_public_secondary_texts.py
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import backend.models as models  # noqa: E402
from backend.core.cache_v2 import invalidate_cached_public  # noqa: E402

try:
    from backend.database import SessionLocal  # noqa: E402
except Exception:
    from backend.core.database import SessionLocal  # noqa: E402

# ── Canonical values for the secondary texts ─────────────────────────────────
DEFAULT_MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

BLOG_FEED_KEYS: dict[str, Any] = {"read_more_label": "Leer más"}

BLOG_ARCHIVE_KEYS: dict[str, Any] = {
    "back_to_blog_label": "Volver al blog",
    "empty_tag_title": "Sin artículos con esta etiqueta",
    "empty_tag_description": "No hay posts publicados con esta etiqueta todavía.",
    "empty_category_title": "Sin artículos en esta categoría",
    "empty_category_description": "No hay posts publicados en esta categoría todavía.",
}

EVENTS_FEED_KEYS: dict[str, Any] = {
    "month_names": DEFAULT_MONTH_NAMES,
    "week_view_label": "Semanal",
    "month_view_label": "Mensual",
    "year_view_label": "Anual",
}

TESTIMONIALS_FEED_KEYS: dict[str, Any] = {"read_more_label": "Leer más"}

CONTACT_FORM_KEYS: dict[str, Any] = {
    "reset_label": "Enviar otro mensaje",
    "email_label": "Correo electrónico",
    "email_placeholder": "tu@email.com (opcional)",
}

HOME_FEED_KEYS: dict[str, Any] = {
    "activities_view_all_href": "/eventos",
    "newsletter_sending_label": "Enviando...",
    "newsletter_success_toast": "¡Suscrito al boletín!",
    "newsletter_error_toast": "No se pudo suscribir. Intenta de nuevo.",
}

FOOTER_TOP_LEVEL_KEYS: dict[str, Any] = {"privacy_href": "/privacy"}
FOOTER_CONTACT_KEYS: dict[str, Any] = {
    "email": "contactenos@ministerioselfaro.org",
    "location_href": "/sedes",
    "newsletter_href": "/boletin",
}

# page slug -> (section_key, keys to merge)
MERGES: list[tuple[str, str, dict[str, Any]]] = [
    ("home", "feed", HOME_FEED_KEYS),
    ("blog", "feed", BLOG_FEED_KEYS),
    ("blog", "archive_template", BLOG_ARCHIVE_KEYS),
    ("events", "feed", EVENTS_FEED_KEYS),
    ("testimonials", "feed", TESTIMONIALS_FEED_KEYS),
    ("contact", "contact", CONTACT_FORM_KEYS),
    ("contacto", "contact", CONTACT_FORM_KEYS),
]

# Footer page merges top-level keys AND nested ``contact`` (email + hrefs).
FOOTER_MERGES: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = [
    ("footer", "footer_config", FOOTER_TOP_LEVEL_KEYS, FOOTER_CONTACT_KEYS),
]


def _merge_missing(props: dict[str, Any], keys: dict[str, Any]) -> bool:
    """Add missing ``keys`` into ``props`` and into a nested ``content`` JSON
    envelope (the shape used by feed sections). Returns True if anything changed."""
    changed = False

    def apply(target: dict[str, Any]) -> bool:
        local_changed = False
        for key, value in keys.items():
            if key not in target:
                target[key] = deepcopy(value)
                local_changed = True
        return local_changed

    changed |= apply(props)

    content = props.get("content")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            if apply(parsed):
                props["content"] = json.dumps(parsed, ensure_ascii=False)
                changed = True
    elif isinstance(content, dict):
        changed |= apply(content)

    return changed


def _merge_footer(props: dict[str, Any], top_keys: dict[str, Any], contact_keys: dict[str, Any]) -> bool:
    """Merge top-level ``footer_config`` keys and the nested ``contact`` record
    (email, location/newsletter hrefs) without touching editor values."""
    changed = _merge_missing(props, top_keys)

    contact = props.get("contact")
    if not isinstance(contact, dict):
        contact = {}
        props["contact"] = contact
        changed = True
    for key, value in contact_keys.items():
        if key not in contact:
            contact[key] = deepcopy(value)
            changed = True
    return changed


def _snapshot(page: models.CmsPage, sections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": "published",
            "seo_json": page.seo_json or {},
            "locale": page.locale,
        },
        "sections": [
            {
                "section_key": s["key"],
                "type": s["type"],
                "props_json": s["props"],
                "sort_order": s["sort"],
                "is_visible": True,
                "status": "active",
            }
            for s in sections
        ],
    }


def _publish_if_changed(db: Any, site_key: str, page: models.CmsPage, sections: list[dict[str, Any]]) -> bool:
    new_snapshot = _snapshot(page, sections)
    current_version = None
    if page.published_version_id:
        current_version = db.query(models.CmsPageVersion).filter_by(id=page.published_version_id).first()

    if page.status == "published" and current_version is not None and current_version.snapshot_json == new_snapshot:
        return False

    max_version = (
        db.query(models.CmsPageVersion)
        .filter_by(page_id=page.id)
        .order_by(models.CmsPageVersion.version_number.desc())
        .first()
    )
    next_version = (max_version.version_number + 1) if max_version else 1

    version = models.CmsPageVersion(
        page_id=page.id,
        version_number=next_version,
        snapshot_json=new_snapshot,
        notes="Seed public secondary texts",
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    page.published_version_id = version.id
    page.status = "published"
    db.add(page)
    db.commit()

    # The public endpoint caches pages (``@cached_public``); drop the entry
    # for this slug so the published snapshot is served immediately (the CRUD
    # layer does the same on every page mutation).
    invalidate_cached_public("public_page", site_key=site_key, slug=page.slug)
    return True


def main() -> int:
    db = SessionLocal()
    try:
        site = db.query(models.CmsSite).filter(models.CmsSite.is_active.is_(True)).first()
        if site is None:
            site = db.query(models.CmsSite).filter_by(site_key="ccf").first()
        if site is None:
            raise RuntimeError("No active CmsSite found")

        republished = 0
        for slug, section_key, keys in MERGES:
            page = db.query(models.CmsPage).filter_by(site_id=site.id, slug=slug).first()
            if page is None:
                print(f"Skip {slug}: page not found")
                continue

            section = (
                db.query(models.CmsSection)
                .filter_by(page_id=page.id, section_key=section_key)
                .filter(models.CmsSection.deleted_at.is_(None), models.CmsSection.status != "archived")
                .first()
            )
            if section is None:
                print(f"Skip {slug}/{section_key}: section not found")
                continue

            props = deepcopy(section.props_json) if isinstance(section.props_json, dict) else {}
            if not _merge_missing(props, keys):
                print(f"{slug}/{section_key}: already up to date")
                continue

            section.props_json = props
            db.add(section)
            db.commit()

            sections = [
                {
                    "key": s.section_key,
                    "type": s.type,
                    "sort": s.sort_order,
                    "props": s.props_json,
                }
                for s in db.query(models.CmsSection)
                .filter_by(page_id=page.id)
                .filter(models.CmsSection.deleted_at.is_(None), models.CmsSection.status != "archived")
                .order_by(models.CmsSection.sort_order)
                .all()
            ]
            if _publish_if_changed(db, site.site_key, page, sections):
                republished += 1
                print(f"{slug}/{section_key}: merged keys {sorted(keys)} and republished")

        for slug, section_key, top_keys, contact_keys in FOOTER_MERGES:
            page = db.query(models.CmsPage).filter_by(site_id=site.id, slug=slug).first()
            if page is None:
                print(f"Skip {slug}: page not found")
                continue

            section = (
                db.query(models.CmsSection)
                .filter_by(page_id=page.id, section_key=section_key)
                .filter(models.CmsSection.deleted_at.is_(None), models.CmsSection.status != "archived")
                .first()
            )
            if section is None:
                print(f"Skip {slug}/{section_key}: section not found")
                continue

            props = deepcopy(section.props_json) if isinstance(section.props_json, dict) else {}
            if not _merge_footer(props, top_keys, contact_keys):
                print(f"{slug}/{section_key}: already up to date")
                continue

            section.props_json = props
            db.add(section)
            db.commit()

            sections = [
                {
                    "key": s.section_key,
                    "type": s.type,
                    "sort": s.sort_order,
                    "props": s.props_json,
                }
                for s in db.query(models.CmsSection)
                .filter_by(page_id=page.id)
                .filter(models.CmsSection.deleted_at.is_(None), models.CmsSection.status != "archived")
                .order_by(models.CmsSection.sort_order)
                .all()
            ]
            if _publish_if_changed(db, site.site_key, page, sections):
                republished += 1
                print(f"{slug}/{section_key}: merged footer keys and republished")

        print(f"\nDone: {republished} pages republished")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Seed public CMS menus (main, mobile) and the dedicated footer page.

This script is idempotent: rerunning it updates rows only when the canonical
payload changes, and it publishes a new page version only when the footer
snapshot differs from the live CMS state.
"""
from __future__ import annotations

import json
import sys
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

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402

SITE_KEY = "ccf"

MAIN_MENU_ITEMS: list[dict[str, Any]] = [
    {"label": "Inicio", "href": "/", "icon": None},
    {"label": "Quiénes Somos", "href": "/nosotros", "icon": None},
    {"label": "Pastores", "href": "/pastores", "icon": None},
    {"label": "Eventos", "href": "/eventos", "icon": None},
    {"label": "Prédicas", "href": "/predicas", "icon": None},
    {"label": "Cursos", "href": "/cursos", "icon": None},
    {"label": "Sedes", "href": "/sedes", "icon": None},
]

MOBILE_MENU_ITEMS: list[dict[str, Any]] = [
    {"label": "Inicio", "href": "/", "icon": "Home"},
    {"label": "Eventos", "href": "/eventos", "icon": "CalendarDays"},
    {"label": "Prédicas", "href": "/predicas", "icon": "PlayCircle"},
    {"label": "Sedes", "href": "/sedes", "icon": "MapPin"},
    {"label": "Conocer a Jesús", "href": "/conocer-a-jesus", "icon": "Menu"},
]

FOOTER_PAGE_SLUG = "footer"
FOOTER_PAGE_TITLE = "Footer"
FOOTER_SECTION_KEY = "footer_config"
FOOTER_SECTION_TYPE = "footer_config"

FOOTER_PROPS: dict[str, Any] = {
    "description": (
        "Iluminando el camino hacia una conexión profunda con lo divino a través "
        "de la comunidad y la guía espiritual. Una casa de fe abierta para toda la familia."
    ),
    "nav_links": [
        {"href": "/", "label": "Inicio"},
        {"href": "/nosotros", "label": "Quiénes Somos"},
        {"href": "/pastores", "label": "Pastores"},
        {"href": "/eventos", "label": "Eventos"},
        {"href": "/predicas", "label": "Prédicas"},
        {"href": "/cursos", "label": "Cursos"},
    ],
    "resource_links": [
        {"href": "/conocer-a-jesus", "label": "Conocer a Jesús"},
        {"href": "/testimonios", "label": "Testimonios"},
        {"href": "/sedes", "label": "Sedes"},
        {"href": "/boletin", "label": "Boletín"},
    ],
    "social_links": [
        {"href": "https://facebook.com/comunidadccf", "label": "Facebook", "kind": "facebook"},
        {"href": "https://instagram.com/comunidadccf", "label": "Instagram", "kind": "instagram"},
        {"href": "https://youtube.com/comunidadccf", "label": "YouTube", "kind": "youtube"},
    ],
    "section_titles": {
        "nav": "Navegación",
        "resources": "Recursos",
        "contact": "Contáctanos",
    },
    "contact": {
        "location_label": "Cartagena, Colombia",
        "newsletter_label": "Boletín semanal",
    },
    "copyright": {
        "company": "PLES SAS",
        "company_url": "https://ples.com.co",
        "text": "El uso inteligente de la experiencia. Todos los derechos reservados.",
    },
    "privacy_label": "Política de Privacidad",
}


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _menu_item_spec(item: dict[str, Any], sort_order: int) -> dict[str, Any]:
    href = item["href"]
    meta: dict[str, Any] = {}
    if item.get("icon"):
        meta["icon"] = item["icon"]
    return {
        "label": item["label"],
        "href": href,
        "target": "_self",
        "is_external": href.startswith(("http://", "https://")),
        "visibility": "public",
        "sort_order": sort_order,
        "meta_json": meta,
    }


def _ensure_menu(
    db,
    site: models.CmsSite,
    menu_key: str,
    menu_name: str,
    desired_specs: list[dict[str, Any]],
) -> tuple[bool, bool]:
    menu = (
        db.query(models.CmsMenu)
        .filter(models.CmsMenu.site_id == site.id, models.CmsMenu.menu_key == menu_key)
        .first()
    )
    created = False
    changed = False
    if menu is None:
        menu = models.CmsMenu(
            site_id=site.id,
            menu_key=menu_key,
            name=menu_name,
            is_active=True,
        )
        db.add(menu)
        db.flush()
        created = True
        changed = True
    else:
        if menu.name != menu_name or not menu.is_active:
            menu.name = menu_name
            menu.is_active = True
            changed = True

    desired_items = [_menu_item_spec(spec, idx) for idx, spec in enumerate(desired_specs)]
    desired_hrefs = {item["href"] for item in desired_items}

    current_items = (
        db.query(models.CmsMenuItem)
        .filter(models.CmsMenuItem.menu_id == menu.id)
        .order_by(models.CmsMenuItem.sort_order.asc(), models.CmsMenuItem.id.asc())
        .all()
    )

    current_by_href = {item.href: item for item in current_items}

    # Update or create items in the canonical order.
    final_items: list[models.CmsMenuItem] = []
    for index, desired in enumerate(desired_items):
        existing = current_by_href.get(desired["href"])
        if existing is None:
            existing = models.CmsMenuItem(menu_id=menu.id, **desired)
            db.add(existing)
            db.flush()
            changed = True
        else:
            if (
                existing.label != desired["label"]
                or existing.target != desired["target"]
                or existing.is_external != desired["is_external"]
                or existing.visibility != desired["visibility"]
                or existing.sort_order != desired["sort_order"]
                or (existing.meta_json or {}) != desired["meta_json"]
            ):
                existing.label = desired["label"]
                existing.target = desired["target"]
                existing.is_external = desired["is_external"]
                existing.visibility = desired["visibility"]
                existing.sort_order = desired["sort_order"]
                existing.meta_json = desired["meta_json"]
                db.add(existing)
                changed = True
            # Remove from mapping so we can delete leftovers afterwards.
            del current_by_href[desired["href"]]
        final_items.append(existing)

    # Remove any items whose href is no longer in the canonical list.
    for leftover in current_by_href.values():
        db.delete(leftover)
        changed = True

    # Re-sort final items to guarantee order matches the canonical list.
    for index, item in enumerate(final_items):
        if item.sort_order != index:
            item.sort_order = index
            db.add(item)
            changed = True

    return created, changed


def _section_payload(props: dict[str, Any], sort_order: int) -> dict[str, Any]:
    return {
        "section_key": FOOTER_SECTION_KEY,
        "type": FOOTER_SECTION_TYPE,
        "props_json": props,
        "sort_order": sort_order,
        "is_visible": True,
        "status": "active",
    }


def _ensure_footer_page(db, site: models.CmsSite) -> tuple[bool, bool]:
    page = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == FOOTER_PAGE_SLUG)
        .first()
    )
    created = False
    changed = False

    if page is None:
        page = models.CmsPage(
            site_id=site.id,
            slug=FOOTER_PAGE_SLUG,
            title=FOOTER_PAGE_TITLE,
            status="draft",
            seo_json={},
            locale="es",
        )
        db.add(page)
        db.flush()
        created = True
        changed = True
    else:
        if page.title != FOOTER_PAGE_TITLE:
            page.title = FOOTER_PAGE_TITLE
            changed = True
        if page.status != "published":
            changed = True
        if (page.seo_json or {}) != {}:
            page.seo_json = {}
            changed = True
        if page.locale != "es":
            page.locale = "es"
            changed = True

    desired_section = _section_payload(FOOTER_PROPS, 0)
    current_sections = (
        db.query(models.CmsSection)
        .filter(models.CmsSection.page_id == page.id)
        .order_by(models.CmsSection.sort_order.asc(), models.CmsSection.id.asc())
        .all()
    )

    # We keep only the canonical footer_config section on this page.
    current_serialized = [
        {
            "section_key": section.section_key,
            "type": section.type,
            "props_json": section.props_json or {},
            "sort_order": section.sort_order,
            "is_visible": section.is_visible,
            "status": section.status or "active",
        }
        for section in current_sections
    ]
    desired_sections = [desired_section]

    if current_serialized != desired_sections:
        db.query(models.CmsSection).filter(models.CmsSection.page_id == page.id).delete(
            synchronize_session=False
        )
        for section in desired_sections:
            db.add(models.CmsSection(page_id=page.id, **section))
        changed = True

    db.flush()

    desired_snapshot = {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": "published",
            "seo_json": page.seo_json or {},
            "locale": page.locale,
        },
        "sections": desired_sections,
    }

    current_version = None
    if page.published_version_id:
        current_version = (
            db.query(models.CmsPageVersion)
            .filter(models.CmsPageVersion.id == page.published_version_id)
            .first()
        )

    current_snapshot = current_version.snapshot_json if current_version else None
    if page.status != "published" or current_snapshot != desired_snapshot:
        from sqlalchemy import func

        next_version = (
            db.query(func.max(models.CmsPageVersion.version_number))
            .filter(models.CmsPageVersion.page_id == page.id)
            .scalar()
            or 0
        )
        version = models.CmsPageVersion(
            page_id=page.id,
            version_number=int(next_version) + 1,
            snapshot_json=desired_snapshot,
            notes="Seed public menus and footer",
        )
        db.add(version)
        db.flush()
        page.status = "published"
        page.published_version_id = version.id
        db.add(page)
        changed = True

    return created, changed


def main() -> int:
    with SessionLocal() as db:
        site = (
            db.query(models.CmsSite)
            .filter(models.CmsSite.site_key == SITE_KEY)
            .first()
        )
        if site is None:
            raise RuntimeError(f"CMS site {SITE_KEY!r} not found")

        main_created, main_changed = _ensure_menu(
            db, site, "main", "Menú principal", MAIN_MENU_ITEMS
        )
        mobile_created, mobile_changed = _ensure_menu(
            db, site, "mobile", "Menú móvil", MOBILE_MENU_ITEMS
        )
        footer_created, footer_changed = _ensure_footer_page(db, site)

        db.commit()

        print(f"Site: {SITE_KEY}")
        print(
            f"Menu main: {'created' if main_created else 'exists'}; "
            f"{'updated' if main_changed else 'unchanged'}"
        )
        print(
            f"Menu mobile: {'created' if mobile_created else 'exists'}; "
            f"{'updated' if mobile_changed else 'unchanged'}"
        )
        print(
            f"Page {FOOTER_PAGE_SLUG}: {'created' if footer_created else 'exists'}; "
            f"{'updated/published' if footer_changed else 'unchanged'}"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations
# ruff: noqa: I001

"""Ensure the public pastors page exists in CMS v2 with live content.

This script migrates the legacy page_content payloads for the public pastors
route into the canonical CMS v2 tables:

- page slug: ``pastors``
- sections: ``hero``, ``feed``, ``pastors``
- public menu: ``main``

It is idempotent: rerunning it updates rows only when the canonical payload
changes, and it publishes a new page version only when the page snapshot
differs from the live CMS state.

The script runs against every site key listed in ``TARGET_SITES`` (default
``["ccf", "faro"]``). This immunizes the platform against site-key drift
between the frontend SITE_KEY env var and the canonical backend identifiers,
which previously caused ``GET /cms/v2/public/sites/faro/theme`` to return
``404 active theme not found`` for every ``/faro/*`` public route.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
import ensure_public_content_blocks as public_blocks  # noqa: E402


# Sites that must always have an active CmsTheme + CmsMenu("main") +
# CmsPage("pastors"). The smoke-report surfaced ``404 active theme not found``
# on every ``/faro/*`` route because only ``"ccf"`` was seeded; the frontend
# can resolve to either key depending on ``NEXT_PUBLIC_SITE_KEY`` so we ensure
# BOTH without renaming the canonical backend identifier.
# Operator override (e.g. deployments that only ever serve a subset) can be
# set via the ``CCF_PUBLIC_SITE_KEYS`` env var as a comma-separated string.
TARGET_SITES = [
    key.strip().lower()
    for key in os.environ.get("CCF_PUBLIC_SITE_KEYS", "ccf,faro").split(",")
    if key.strip()
]
PAGE_SLUG = "pastors"
MENU_KEY = "main"
THEME_NAME = "Tema institucional CCF"
THEME_TOKENS = {
    "--site-background": "#f8f9ff",
    "--site-on-background": "#101828",
    "--site-surface": "#ffffff",
    "--site-surface-container": "#ffffff",
    "--site-surface-container-low": "#f0f4ff",
    "--site-surface-container-high": "#e6ecff",
    "--site-surface-container-highest": "#d9e2ff",
    "--site-on-surface": "#101828",
    "--site-on-surface-variant": "#475467",
    "--site-primary": "#3155d4",
    "--site-on-primary": "#ffffff",
    "--site-primary-container": "#e1e8ff",
    "--site-on-primary-container": "#001a66",
    "--site-secondary": "#e0a931",
    "--site-cta-gradient": "linear-gradient(135deg,#3155d4,#1a3ab8)",
    "--site-outline-variant": "rgba(0,0,0,0.1)",
}

PASTORS_PAGE_META = {
    "title": "Liderazgo Pastoral",
    "description": "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.",
}
PASTORS_PAGE_HERO = {
    "eyebrow": "Nuestro Equipo",
    "title": "Liderazgo Pastoral",
    "description": "Personas llamadas a servir y guiar a la comunidad.",
}


def _content_block(key: str) -> dict[str, Any]:
    block = public_blocks.BLOCKS.get(key)
    if not isinstance(block, dict):
        raise RuntimeError(f"canonical block {key!r} not found")
    content = block.get("content")
    if not isinstance(content, dict):
        raise RuntimeError(f"canonical block {key!r} must contain an object content payload")
    return content


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _section_payload(section_key: str, section_type: str, props: dict[str, Any], sort_order: int) -> dict[str, Any]:
    return {
        "section_key": section_key,
        "type": section_type,
        "props_json": props,
        "sort_order": sort_order,
        "is_visible": True,
        "status": "active",
    }


def _public_menu_items(nav_payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = nav_payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError("ccf_nav_items.content.items must be a list")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        href = str(item.get("href") or "").strip()
        if not label or not href:
            continue
        normalized.append(
            {
                "label": label,
                "href": href,
                "target": "_self",
                "is_external": href.startswith(("http://", "https://")),
                "visibility": "public",
                "sort_order": index,
                "meta_json": {},
            }
        )
    return normalized


def _ensure_menu(db, site: models.CmsSite, nav_payload: dict[str, Any]) -> tuple[bool, bool]:
    menu = (
        db.query(models.CmsMenu)
        .filter(models.CmsMenu.site_id == site.id, models.CmsMenu.menu_key == MENU_KEY)
        .first()
    )
    created = False
    changed = False
    if menu is None:
        menu = models.CmsMenu(
            site_id=site.id,
            menu_key=MENU_KEY,
            name="Menú principal",
            is_active=True,
        )
        db.add(menu)
        db.flush()
        created = True
        changed = True
    elif menu.name != "Menú principal" or not menu.is_active:
        menu.name = "Menú principal"
        menu.is_active = True
        changed = True

    desired_items = _public_menu_items(nav_payload)
    current_items = (
        db.query(models.CmsMenuItem)
        .filter(models.CmsMenuItem.menu_id == menu.id)
        .order_by(models.CmsMenuItem.sort_order.asc(), models.CmsMenuItem.id.asc())
        .all()
    )
    current_serialized = [
        {
            "label": item.label,
            "href": item.href,
            "target": item.target,
            "is_external": item.is_external,
            "visibility": item.visibility,
            "sort_order": item.sort_order,
            "meta_json": item.meta_json or {},
        }
        for item in current_items
    ]
    if current_serialized != desired_items:
        db.query(models.CmsMenuItem).filter(models.CmsMenuItem.menu_id == menu.id).delete(
            synchronize_session=False
        )
        for item in desired_items:
            db.add(models.CmsMenuItem(menu_id=menu.id, **item))
        changed = True

    return created, changed


def _ensure_theme(db, site: models.CmsSite) -> tuple[bool, bool]:
    theme = (
        db.query(models.CmsTheme)
        .filter(models.CmsTheme.site_id == site.id, models.CmsTheme.name == THEME_NAME)
        .first()
    )
    created = False
    changed = False
    if theme is None:
        theme = models.CmsTheme(
            site_id=site.id,
            name=THEME_NAME,
            tokens_json=THEME_TOKENS,
            is_active=True,
            status="active",
        )
        db.add(theme)
        db.flush()
        db.query(models.CmsTheme).filter(
            models.CmsTheme.site_id == site.id,
            models.CmsTheme.id != theme.id,
        ).update({"is_active": False})
        created = True
        changed = True
    else:
        if theme.tokens_json != THEME_TOKENS:
            theme.tokens_json = THEME_TOKENS
            changed = True
        if not theme.is_active or theme.status != "active":
            db.query(models.CmsTheme).filter(models.CmsTheme.site_id == site.id).update(
                {"is_active": False}
            )
            theme.is_active = True
            theme.status = "active"
            changed = True
    return created, changed


def _ensure_page(db, site: models.CmsSite) -> tuple[bool, bool]:
    hero = dict(PASTORS_PAGE_HERO)
    feed = _content_block("ccf_pastores_index")
    pastors = _content_block("ccf_pastores_feed")
    first_image = next(
        (
            str(item.get("image"))
            for item in pastors.get("pastors", [])
            if isinstance(item, dict) and isinstance(item.get("image"), str) and item.get("image")
        ),
        "",
    )
    meta = dict(PASTORS_PAGE_META)
    if first_image:
        meta["image"] = first_image
        hero["bg_image"] = first_image

    desired_sections = [
        _section_payload(
            "hero",
            "hero",
            {
                "content": _stable_json({**hero, "bg_image": meta.get("image")}),
                **hero,
                "bg_image": meta.get("image"),
            },
            0,
        ),
        _section_payload(
            "feed",
            "feed",
            {
                "content": _stable_json(feed),
                **feed,
            },
            1,
        ),
        _section_payload(
            "pastors",
            "feed",
            {
                "content": _stable_json(pastors),
                **pastors,
            },
            2,
        ),
    ]

    page = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == PAGE_SLUG)
        .first()
    )
    created = False
    changed = False
    if page is None:
        page = models.CmsPage(
            site_id=site.id,
            slug=PAGE_SLUG,
            title=meta.get("title") or PASTORS_PAGE_META["title"],
            status="draft",
            seo_json=meta,
        )
        db.add(page)
        db.flush()
        created = True
        changed = True
    else:
        if page.title != (meta.get("title") or PASTORS_PAGE_META["title"]):
            page.title = meta.get("title") or PASTORS_PAGE_META["title"]
            changed = True
        if (page.seo_json or {}) != meta:
            page.seo_json = meta
            changed = True

    current_sections = (
        db.query(models.CmsSection)
        .filter(models.CmsSection.page_id == page.id)
        .order_by(models.CmsSection.sort_order.asc(), models.CmsSection.id.asc())
        .all()
    )
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
            notes="Seed public CMS pastors page",
        )
        db.add(version)
        db.flush()
        page.status = "published"
        page.published_version_id = version.id
        db.add(
            models.CmsPublishLog(
                site_id=site.id,
                page_id=page.id,
                entity_type="page",
                entity_id=str(page.id),
                action="publish",
                from_status="draft",
                to_status="published",
                metadata_json={"source": "ensure_public_cms_pastors"},
            )
        )
        changed = True

    return created, changed


def _ensure_site(db, site_key: str) -> tuple[models.CmsSite, bool]:
    """Return the CmsSite row for ``site_key``, creating it when missing.

    Axioma 3 — Multi-Tenant (REGLAS.md §4): CmsSite is the only legitimate
    exception to the multi-tenant rule (editorial content shared
    cross-sede by design). The new site intentionally has no ``sede_id``,
    matching the documented exception in
    ``backend/api/_cms_helpers/_shared.py``. Do NOT add ``sede_id`` here.
    """
    site = (
        db.query(models.CmsSite)
        .filter(models.CmsSite.site_key == site_key)
        .first()
    )
    if site is not None:
        if not site.is_active:
            site.is_active = True
        return site, False
    site = models.CmsSite(
        site_key=site_key,
        name=site_key.upper(),
        base_path="/",
        is_active=True,
    )
    db.add(site)
    db.flush()
    return site, True


def main() -> int:
    with SessionLocal() as db:
        nav_payload = _content_block("ccf_nav_items")
        menu_title = str(public_blocks.BLOCKS.get("ccf_nav_items", {}).get("title", "Menú de Navegación"))

        themes_active = 0
        for site_key in TARGET_SITES:
            site, site_created = _ensure_site(db, site_key)
            menu_created, menu_changed = _ensure_menu(db, site, nav_payload)
            theme_created, theme_changed = _ensure_theme(db, site)
            if theme_created or theme_changed:
                themes_active += 1
            page_created, page_changed = _ensure_page(db, site)
            page_status = (
                f"{'created' if page_created else 'exists'}; "
                f"{'updated/published' if page_changed else 'unchanged'}"
            )

            print(f"--- Site: {site_key} ---")
            print(f"Site: {'created' if site_created else 'exists'}")
            print(
                f"Menu {MENU_KEY}: {'created' if menu_created else 'exists'}; "
                f"{'updated' if menu_changed else 'unchanged'}"
            )
            print(
                f"Theme: {'created' if theme_created else 'exists'}; "
                f"{'updated/activated' if theme_changed else 'unchanged'}"
            )
            print(f"Page {PAGE_SLUG}: {page_status}")

        db.commit()
        print(
            f"Summary: {len(TARGET_SITES)} sites touched; "
            f"{themes_active} theme activations/updates."
        )
        print(f"Menu source: {menu_title}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
"""

import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, text

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402


SITE_KEY = "faro"
PAGE_SLUG = "pastors"
MENU_KEY = "main"


def _load_page_content(db, page_key: str) -> tuple[str, dict[str, Any]]:
    row = db.execute(
        text("SELECT title, content FROM page_contents WHERE page_key = :page_key"),
        {"page_key": page_key},
    ).fetchone()
    if row is None:
        raise RuntimeError(f"page_contents row not found for {page_key!r}")
    try:
        payload = json.loads(row.content or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"page_contents row {page_key!r} has invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"page_contents row {page_key!r} must decode to an object")
    return str(row.title or page_key), payload


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
        raise RuntimeError("faro_nav_items.content.items must be a list")

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


def _ensure_page(db, site: models.CmsSite) -> tuple[bool, bool]:
    meta_title, meta = _load_page_content(db, "faro_pastores_meta")
    hero_title, hero = _load_page_content(db, "faro_pastores_hero")
    feed_title, feed = _load_page_content(db, "faro_pastores_index")
    pastors_title, pastors = _load_page_content(db, "faro_pastores_feed")

    desired_sections = [
        _section_payload(
            "hero",
            "hero",
            {
                "content": _stable_json(hero),
                **hero,
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
            title=meta.get("title") or meta_title,
            status="draft",
            seo_json=meta,
        )
        db.add(page)
        db.flush()
        created = True
        changed = True
    else:
        if page.title != (meta.get("title") or meta_title):
            page.title = meta.get("title") or meta_title
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


def main() -> int:
    with SessionLocal() as db:
        site = (
            db.query(models.CmsSite)
            .filter(models.CmsSite.site_key == SITE_KEY)
            .first()
        )
        if site is None:
            raise RuntimeError(f"CMS site {SITE_KEY!r} not found")

        menu_title, nav_payload = _load_page_content(db, "faro_nav_items")
        menu_created, menu_changed = _ensure_menu(db, site, nav_payload)
        page_created, page_changed = _ensure_page(db, site)
        db.commit()

        print(f"Site: {SITE_KEY}")
        print(f"Menu {MENU_KEY}: {'created' if menu_created else 'exists'}; {'updated' if menu_changed else 'unchanged'}")
        print(f"Page {PAGE_SLUG}: {'created' if page_created else 'exists'}; {'updated/published' if page_changed else 'unchanged'}")
        print(f"Menu source: {menu_title}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

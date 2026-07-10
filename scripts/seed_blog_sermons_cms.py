#!/usr/bin/env python3
"""Seed CMS pages for the public blog and sermons sections.

Creates / updates:
* ``blog`` page with ``hero``, ``feed`` and ``archive_template`` sections.
* ``sermons`` page feed section with the canonical YouTube channel URL.

Usage:
    cd /root/ccf && source venv/bin/activate && python scripts/seed_blog_sermons_cms.py
"""
from __future__ import annotations

import json
import sys
import uuid
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

# Use the same import dance as the rest of the seed scripts.
try:
    from backend.database import SessionLocal  # noqa: E402
except Exception:
    from backend.core.database import SessionLocal  # noqa: E402

YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@Ministeriosfarooficial"

BLOG_SECTIONS: list[dict[str, Any]] = [
    {
        "key": "hero",
        "type": "hero",
        "sort": 0,
        "props": {
            "eyebrow": "Blog",
            "title": "Artículos y Noticias",
            "description": "Reflexiones, enseñanzas y actualizaciones de nuestra comunidad.",
        },
    },
    {
        "key": "feed",
        "type": "cards",
        "sort": 1,
        "props": {
            "search_placeholder": "Buscar artículos...",
            "empty_title": "Sin artículos publicados",
            "empty_description": "Cuando se publiquen posts en el CMS, aparecerán aquí.",
        },
    },
    {
        "key": "archive_template",
        "type": "rich_text",
        "sort": 2,
        "props": {
            "category_title_prefix": "Categoría",
            "category_description_template": 'Artículos en la categoría "{categoryName}".',
            "tag_title_prefix": "Etiqueta",
            "tag_description_template": 'Artículos etiquetados con "{tagName}".',
        },
    },
]


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


def _get_or_create_page(
    db: Any, site: models.CmsSite, slug: str, title: str
) -> models.CmsPage:
    page = db.query(models.CmsPage).filter_by(site_id=site.id, slug=slug).first()
    if page is None:
        page = models.CmsPage(
            site_id=site.id,
            slug=slug,
            title=title,
            status="draft",
            seo_json={},
            locale="es",
        )
        db.add(page)
        db.commit()
        db.refresh(page)
        print(f"Created page: {slug}")
    else:
        print(f"Updating page: {slug}")
    return page


def _upsert_sections(
    db: Any, page: models.CmsPage, sections: list[dict[str, Any]]
) -> None:
    existing = {
        s.section_key: s
        for s in db.query(models.CmsSection).filter_by(page_id=page.id).all()
    }
    desired_keys = {s["key"] for s in sections}

    for key in list(existing):
        if key not in desired_keys:
            db.delete(existing[key])
    db.commit()

    for spec in sections:
        key = spec["key"]
        if key in existing:
            section = existing[key]
            section.type = spec["type"]
            section.props_json = deepcopy(spec["props"])
            section.sort_order = spec["sort"]
            section.is_visible = True
            section.status = "active"
            section.deleted_at = None
        else:
            section = models.CmsSection(
                page_id=page.id,
                section_key=key,
                type=spec["type"],
                props_json=deepcopy(spec["props"]),
                sort_order=spec["sort"],
                is_visible=True,
                status="active",
            )
            db.add(section)
    db.commit()


def _publish_if_changed(
    db: Any, site: models.CmsSite, page: models.CmsPage, sections: list[dict[str, Any]]
) -> None:
    new_snapshot = _snapshot(page, sections)
    current_version = None
    if page.published_version_id:
        current_version = (
            db.query(models.CmsPageVersion)
            .filter_by(id=page.published_version_id)
            .first()
        )

    if (
        page.status == "published"
        and current_version is not None
        and current_version.snapshot_json == new_snapshot
    ):
        print(f"  → unchanged (published v{current_version.version_number})")
        return

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
        notes="Seed blog & sermons CMS content",
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    page.published_version_id = version.id
    page.status = "published"
    db.add(page)
    db.commit()

    log = models.CmsPublishLog(
        site_id=site.id,
        page_id=page.id,
        entity_type="page",
        entity_id=str(page.id),
        action="publish",
        from_status=current_version and "published" or "draft",
        to_status="published",
        metadata_json={"version_id": str(version.id), "version_number": next_version},
    )
    db.add(log)
    db.commit()
    print(f"  → published version {next_version}")


def _ensure_sermons_youtube_url(db: Any, page: models.CmsPage) -> bool:
    """Merge the YouTube channel URL into the sermons feed section.

    Returns ``True`` if the section was changed.
    """
    section = (
        db.query(models.CmsSection)
        .filter_by(page_id=page.id, section_key="feed")
        .first()
    )

    if section is None:
        section = models.CmsSection(
            page_id=page.id,
            section_key="feed",
            type="feed",
            props_json={},
            sort_order=0,
            is_visible=True,
            status="active",
        )
        db.add(section)
        db.commit()
        db.refresh(section)

    props = deepcopy(section.props_json) if isinstance(section.props_json, dict) else {}
    parsed: dict[str, Any] = {}
    content_json = props.get("content")
    if isinstance(content_json, str):
        try:
            parsed = json.loads(content_json)
        except json.JSONDecodeError:
            parsed = {}
    elif isinstance(content_json, dict):
        parsed = content_json

    changed = False
    if props.get("youtube_channel_url") != YOUTUBE_CHANNEL_URL:
        props["youtube_channel_url"] = YOUTUBE_CHANNEL_URL
        changed = True
    if parsed.get("youtube_channel_url") != YOUTUBE_CHANNEL_URL:
        parsed["youtube_channel_url"] = YOUTUBE_CHANNEL_URL
        changed = True

    new_content = json.dumps(parsed, ensure_ascii=False)
    if props.get("content") != new_content:
        props["content"] = new_content
        changed = True

    if changed:
        section.props_json = props
        db.add(section)
        db.commit()
        db.refresh(section)
        print("  → merged youtube_channel_url into sermons feed")
    else:
        print("  → sermons feed already contains youtube_channel_url")
    return changed


def main() -> int:
    db = SessionLocal()
    try:
        site = db.query(models.CmsSite).filter(models.CmsSite.is_active.is_(True)).first()
        if site is None:
            site = db.query(models.CmsSite).filter_by(site_key="ccf").first()
        if site is None:
            raise RuntimeError("No active CmsSite found")

        print(f"Using CmsSite: {site.site_key} ({site.id})")

        # ── Blog page ───────────────────────────────────────────────────────
        blog_page = _get_or_create_page(db, site, "blog", "Blog")
        _upsert_sections(db, blog_page, BLOG_SECTIONS)
        db.refresh(blog_page)
        _publish_if_changed(db, site, blog_page, BLOG_SECTIONS)

        # ── Sermons page YouTube channel URL ────────────────────────────────
        sermons_page = db.query(models.CmsPage).filter_by(
            site_id=site.id, slug="sermons"
        ).first()
        if sermons_page is None:
            print("Warning: sermons page not found; skipping sermons update")
        else:
            print("Updating page: sermons")
            _ensure_sermons_youtube_url(db, sermons_page)
            db.refresh(sermons_page)
            sermons_sections = [
                {
                    "key": s.section_key,
                    "type": s.type,
                    "sort": s.sort_order,
                    "props": s.props_json,
                }
                for s in db.query(models.CmsSection)
                .filter_by(page_id=sermons_page.id)
                .order_by(models.CmsSection.sort_order)
                .all()
            ]
            _publish_if_changed(db, site, sermons_page, sermons_sections)

        print("\nDone")
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

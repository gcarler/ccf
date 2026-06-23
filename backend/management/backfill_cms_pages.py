from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import models
from backend.core.database import SessionLocal
from backend.crud.cms import list_cms_sections, list_cms_page_versions

ALLOWED_STATUSES = {"draft", "in_review", "approved", "published", "archived"}


def _normalize_status(value: str | None) -> str:
    status = (value or "draft").strip().lower()
    return status if status in ALLOWED_STATUSES else "draft"


def _parse_compat_content(raw_content: str | None) -> Any:
    if not raw_content:
        return ""
    text = raw_content.strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except Exception:
        return text


def _pretty_label(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def _render_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return f"<p>{escape(value).replace(chr(10), '<br />')}</p>"
    if isinstance(value, bool):
        return "<p>Sí</p>" if value else "<p>No</p>"
    if isinstance(value, (int, float)):
        return f"<p>{escape(str(value))}</p>"
    if isinstance(value, list):
        if not value:
            return "<p>Sin elementos.</p>"
        items = "".join(f"<li>{_render_inline(item)}</li>" for item in value)
        return f"<ul>{items}</ul>"
    if isinstance(value, dict):
        if not value:
            return "<p>Sin datos.</p>"
        items = []
        for key, nested in value.items():
            rendered_nested = _render_value(nested)
            items.append(
                "<div>"
                f"<strong>{escape(_pretty_label(str(key)))}</strong>"
                f"{rendered_nested}"
                "</div>"
            )
        return "".join(items)
    return f"<pre>{escape(json.dumps(value, ensure_ascii=False, indent=2))}</pre>"


def _render_inline(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return escape("" if value is None else str(value))
    return escape(json.dumps(value, ensure_ascii=False))


def _compat_content_to_html(page_key: str, title: str, raw_content: str | None) -> str:
    parsed = _parse_compat_content(raw_content)
    body = _render_value(parsed)
    return (
        "<div>"
        f"<h3>{escape(title or page_key)}</h3>"
        f"{body}"
        "</div>"
    )


def _compat_page_sections_payload(page_key: str, title: str, raw_content: str | None) -> dict[str, Any]:
    return {
        "layout": "grid",
        "columns": "1",
        "items": [
            {
                "type": "text",
                "content": _compat_content_to_html(page_key, title, raw_content),
            }
        ],
    }


def _build_snapshot(page: models.CmsPage, sections: list[models.CmsSection]) -> dict[str, Any]:
    return {
        "page": {
            "id": page.id,
            "slug": page.slug,
            "title": page.title,
            "status": page.status,
            "seo_json": page.seo_json or {},
        },
        "sections": [
            {
                "id": section.id,
                "section_key": section.section_key,
                "type": section.type,
                "props_json": section.props_json or {},
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
                "status": getattr(section, "status", "active") or "active",
            }
            for section in sections
        ],
    }


def backfill_cms_pages(db: Session, site_key: str = "faro") -> dict[str, int]:
    site = (
        db.query(models.CmsSite)
        .filter(models.CmsSite.site_key == site_key.strip().lower())
        .first()
    )
    if not site:
        raise RuntimeError(f"CMS site not found: {site_key}")

    compat_rows = [
        row
        for row in db.query(models.PageContent)
        .order_by(models.PageContent.updated_at.desc())
        .all()
        if not str(getattr(row, "page_key", "")).endswith("_wiki_notes")
    ]
    publications = {
        row.page_key: row
        for row in db.query(models.ContentPublication).all()
        if getattr(row, "page_key", None)
    }

    created_pages = 0
    created_sections = 0
    created_versions = 0
    linked_published_versions = 0

    for compat in compat_rows:
        publication = publications.get(compat.page_key)
        desired_status = _normalize_status(getattr(publication, "status", None))

        page = (
            db.query(models.CmsPage)
            .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == compat.page_key)
            .first()
        )
        if not page:
            page = models.CmsPage(
                site_id=site.id,
                slug=compat.page_key.strip().lower(),
                title=compat.title.strip(),
                status=desired_status,
                seo_json={},
            )
            db.add(page)
            db.flush()
            created_pages += 1
        elif page.status != desired_status:
            page.status = desired_status

        sections = list_cms_sections(db, page.id)
        if not sections:
            section = models.CmsSection(
                page_id=page.id,
                section_key=f"{page.slug}-compat-content",
                type="content_blocks",
                props_json=_compat_page_sections_payload(compat.page_key, compat.title, compat.content),
                sort_order=0,
                is_visible=True,
                status="active",
            )
            db.add(section)
            db.flush()
            sections = [section]
            created_sections += 1

        versions = list_cms_page_versions(db, page.id)
        if not versions:
            version = models.CmsPageVersion(
                page_id=page.id,
                version_number=1,
                snapshot_json=_build_snapshot(page, sections),
                notes="Backfilled from compat page_contents",
            )
            db.add(version)
            db.flush()
            created_versions += 1
            if page.status == "published":
                page.published_version_id = version.id
                linked_published_versions += 1
        elif page.status == "published" and page.published_version_id is None:
            page.published_version_id = versions[0].id
            linked_published_versions += 1

    db.commit()
    return {
        "site_id": site.id,
        "pages_seen": len(compat_rows),
        "pages_created": created_pages,
        "sections_created": created_sections,
        "versions_created": created_versions,
        "published_versions_linked": linked_published_versions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill CMS v2 pages from compat content")
    parser.add_argument("--site", default="faro", help="CMS site key to backfill")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = backfill_cms_pages(db, site_key=args.site)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    main()

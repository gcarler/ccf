#!/usr/bin/env python3
"""Republish CMS pages with updated hero images.

Creates new page versions and publishes them so the public site reflects
the updated hero images from convention photos.

Usage:
    cd /root/ccf && python3 scripts/publish_updated_pages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend import models
from backend.core.database import SessionLocal
from sqlalchemy import text

# Pages to republish (updated with convention photos)
PAGES_TO_REPUBLISH = [
    "home",
    "about",
    "events",
    "courses",
    "sermons",
    "testimonials",
    "locations",
    "newsletter",
    "welcome",
    "discover",
]


def main() -> int:
    db = SessionLocal()
    try:
        updated = 0
        skipped = 0

        for page_slug in PAGES_TO_REPUBLISH:
            # Get page
            result = db.execute(text('''
                SELECT p.id, p.site_id, p.title, p.slug, p.seo_json,
                       p.published_version_id
                FROM cms_pages p
                JOIN cms_sites st ON st.id = p.site_id
                WHERE st.site_key = 'ccf' AND p.slug = :slug
            '''), {'slug': page_slug})
            page_row = result.fetchone()
            if not page_row:
                print(f"  {page_slug}: page not found, skipping")
                skipped += 1
                continue

            page_id, site_id, title, slug, seo_json, pub_version_id = page_row

            # Get current sections
            sections_result = db.execute(text('''
                SELECT section_key, type, props_json, sort_order, is_visible, status
                FROM cms_sections
                WHERE page_id = :page_id
                ORDER BY sort_order ASC, id ASC
            '''), {'page_id': page_id})
            sections = sections_result.fetchall()

            # Build snapshot
            current_sections = []
            for section_key, sec_type, props_json, sort_order, is_visible, status in sections:
                props = props_json if isinstance(props_json, dict) else (props_json or {})
                current_sections.append({
                    "section_key": section_key,
                    "type": sec_type,
                    "props_json": props,
                    "sort_order": sort_order,
                    "is_visible": is_visible,
                    "status": status or "active",
                })

            snapshot = {
                "page": {
                    "id": str(page_id),
                    "slug": slug,
                    "title": title,
                    "status": "published",
                    "seo_json": seo_json or {},
                },
                "sections": current_sections,
            }

            # Get next version number
            version_result = db.execute(text('''
                SELECT COALESCE(MAX(version_number), 0) + 1
                FROM cms_page_versions WHERE page_id = :page_id
            '''), {'page_id': page_id})
            version_number = version_result.scalar_one()

            # Create new version
            version = models.CmsPageVersion(
                page_id=page_id,
                version_number=int(version_number),
                snapshot_json=snapshot,
                notes="Updated hero image with convention 2026 photo",
            )
            db.add(version)
            db.flush()

            # Update page to point to new version
            db.execute(text('''
                UPDATE cms_pages
                SET published_version_id = :version_id,
                    updated_at = NOW()
                WHERE id = :page_id
            '''), {'version_id': version.id, 'page_id': page_id})

            updated += 1
            print(f"  {page_slug}: published v{version_number}")

        db.commit()
        print(f"\nResults:")
        print(f"  Published: {updated}")
        print(f"  Skipped: {skipped}")
        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

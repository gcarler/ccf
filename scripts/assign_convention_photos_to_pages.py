#!/usr/bin/env python3
"""Assign convention photos to public pages that need hero images.

Updates hero sections of CMS pages (except pastors) to use convention 2026 photos.

Usage:
    cd /root/ccf && python3 scripts/assign_convention_photos_to_pages.py
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

from backend.core.database import SessionLocal
from sqlalchemy import text

# Pages to update (exclude pastors, _global, _platform, inicio, privacy)
PAGES_TO_UPDATE = [
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

# Map pages to specific convention photos for variety
PAGE_PHOTO_MAP = {
    "home": "DSC_6980.jpg",           # Main church photo
    "about": "DCA_0710.jpg",          # Group photo
    "events": "DSC_7011.jpg",         # Event scene
    "courses": "DSC_7039.jpg",        # Classroom/study
    "sermons": "DSC_7055.jpg",        # Worship/preaching
    "testimonials": "DSC_7085.jpg",   # Fellowship
    "locations": "DSC_7116.jpg",      # Building/exterior
    "newsletter": "DSC_7144.jpg",     # Community
    "welcome": "IMG_6291.jpg",        # Welcome scene
    "discover": "DCA_0774.jpg",       # Discovery/exploration
}

SECTION = "convenccion"


def get_convention_url(db, filename: str) -> str | None:
    result = db.execute(text('''
        SELECT url FROM cms_media_items
        WHERE filename = :filename AND section = :section
        LIMIT 1
    '''), {'filename': filename, 'section': SECTION})
    row = result.fetchone()
    return row[0] if row else None


def get_all_convention_urls(db) -> list[str]:
    result = db.execute(text('''
        SELECT url FROM cms_media_items
        WHERE section = :section
        ORDER BY filename
    '''), {'section': SECTION})
    return [row[0] for row in result.fetchall()]


def main() -> int:
    db = SessionLocal()
    try:
        # Get all convention URLs for fallback
        all_urls = get_all_convention_urls(db)
        if not all_urls:
            print("Error: No convention photos found in CMS media")
            return 1

        print(f"Found {len(all_urls)} convention photos")

        updated = 0
        skipped = 0

        for page_slug in PAGES_TO_UPDATE:
            # Get page ID
            result = db.execute(text('''
                SELECT p.id FROM cms_pages p
                JOIN cms_sites st ON st.id = p.site_id
                WHERE st.site_key = 'ccf' AND p.slug = :slug
            '''), {'slug': page_slug})
            page = result.fetchone()
            if not page:
                print(f"  {page_slug}: page not found, skipping")
                skipped += 1
                continue

            page_id = page[0]

            # Get hero section
            result = db.execute(text('''
                SELECT id, props_json FROM cms_sections
                WHERE page_id = :page_id AND section_key = 'hero'
                LIMIT 1
            '''), {'page_id': page_id})
            hero = result.fetchone()
            if not hero:
                print(f"  {page_slug}: no hero section, skipping")
                skipped += 1
                continue

            section_id, props_json = hero
            import json
            props = props_json if isinstance(props_json, dict) else json.loads(props_json if props_json else '{}')

            # Get the assigned photo or use fallback
            assigned_filename = PAGE_PHOTO_MAP.get(page_slug)
            if assigned_filename:
                new_url = get_convention_url(db, assigned_filename)
                if not new_url:
                    # Use a fallback from available URLs
                    idx = hash(page_slug) % len(all_urls)
                    new_url = all_urls[idx]
            else:
                idx = hash(page_slug) % len(all_urls)
                new_url = all_urls[idx]

            # Update hero bg_image
            old_url = props.get('bg_image', 'NONE')
            props['bg_image'] = new_url

            # Also update nested content.bg_image if exists
            if 'content' in props:
                try:
                    content = json.loads(props['content']) if isinstance(props['content'], str) else props['content']
                    if isinstance(content, dict):
                        content['bg_image'] = new_url
                        props['content'] = json.dumps(content, ensure_ascii=False, separators=(',', ':'))
                except:
                    pass

            # Save updated props
            db.execute(text('''
                UPDATE cms_sections
                SET props_json = :props, updated_at = NOW()
                WHERE id = :section_id
            '''), {'props': json.dumps(props, ensure_ascii=False), 'section_id': section_id})

            updated += 1
            photo_name = Path(new_url).name if new_url else 'unknown'
            print(f"  {page_slug}: updated ({photo_name})")

        db.commit()
        print(f"\nResults:")
        print(f"  Updated: {updated}")
        print(f"  Skipped: {skipped}")
        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

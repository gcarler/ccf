#!/usr/bin/env python3
"""Update CMS pages to use optimized image URLs.

Replaces original convention photo URLs with optimized WebP URLs in hero sections.

Usage:
    cd /root/ccf && python3 scripts/update_pages_to_optimized_urls.py
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
import json

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

OLD_PREFIX = "/api/static/images/drive/FOTOS CONVENCIÓN 2026/"
NEW_PREFIX = "/api/static/images/optimized/convenccion/"


def main() -> int:
    db = SessionLocal()
    try:
        updated = 0

        for page_slug in PAGES_TO_UPDATE:
            # Get page ID
            result = db.execute(text('''
                SELECT p.id FROM cms_pages p
                JOIN cms_sites st ON st.id = p.site_id
                WHERE st.site_key = 'ccf' AND p.slug = :slug
            '''), {'slug': page_slug})
            page = result.fetchone()
            if not page:
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
                continue

            section_id, props_json = hero
            props = props_json if isinstance(props_json, dict) else json.loads(props_json if props_json else '{}')

            bg_image = props.get('bg_image', '')
            if OLD_PREFIX in bg_image:
                # Replace with optimized URL
                new_bg = bg_image.replace(OLD_PREFIX, NEW_PREFIX).replace('.jpg', '.webp').replace('.png', '.webp')
                props['bg_image'] = new_bg

                # Update nested content if exists
                if 'content' in props:
                    try:
                        content = json.loads(props['content']) if isinstance(props['content'], str) else props['content']
                        if isinstance(content, dict) and 'bg_image' in content:
                            content['bg_image'] = new_bg
                            props['content'] = json.dumps(content, ensure_ascii=False, separators=(',', ':'))
                    except:
                        pass

                db.execute(text('''
                    UPDATE cms_sections
                    SET props_json = :props, updated_at = NOW()
                    WHERE id = :section_id
                '''), {'props': json.dumps(props, ensure_ascii=False), 'section_id': section_id})

                updated += 1
                print(f"  {page_slug}: {Path(new_bg).name}")

        db.commit()
        print(f"\nUpdated {updated} pages to use optimized URLs")
        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

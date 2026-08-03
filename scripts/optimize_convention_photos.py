#!/usr/bin/env python3
"""Optimize convention photos for web use.

Converts large JPEG photos to optimized WebP format, resizing to max 1920px width.
Updates CMS media URLs to point to optimized versions.

Usage:
    cd /root/ccf && python3 scripts/optimize_convention_photos.py
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
from backend.services.image_optimizer import ImageOptimizer
from sqlalchemy import text

CONVENTION_DIR = _PROJECT_ROOT / "uploads" / "images" / "drive" / "FOTOS CONVENCIÓN 2026"
OPTIMIZED_DIR = _PROJECT_ROOT / "uploads" / "images" / "optimized" / "convenccion"
SECTION = "convenccion"

optimizer = ImageOptimizer(max_width=1920, quality=82)


def main() -> int:
    if not CONVENTION_DIR.exists():
        print(f"Error: Convention dir not found: {CONVENTION_DIR}")
        return 1

    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)

    images = [
        p for p in CONVENTION_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    print(f"Found {len(images)} convention photos to optimize")

    db = SessionLocal()
    try:
        optimized = 0
        skipped = 0
        failed = 0

        for img in sorted(images):
            webp_name = img.stem + ".webp"
            webp_path = OPTIMIZED_DIR / webp_name

            # Skip if already optimized and smaller than original
            if webp_path.exists() and webp_path.stat().st_size < img.stat().st_size:
                # Update URL in DB if not already updated
                old_url = f"/api/static/images/drive/FOTOS CONVENCIÓN 2026/{img.name}"
                new_url = f"/api/static/images/optimized/convenccion/{webp_name}"

                result = db.execute(text('''
                    SELECT id, url FROM cms_media_items
                    WHERE url = :old_url OR url = :new_url
                    LIMIT 1
                '''), {'old_url': old_url, 'new_url': new_url})
                row = result.fetchone()

                if row and row[1] != new_url:
                    db.execute(text('''
                        UPDATE cms_media_items
                        SET url = :new_url, filename = :filename, mime_type = 'image/webp'
                        WHERE id = :id
                    '''), {'new_url': new_url, 'filename': webp_name, 'id': row[0]})
                    optimized += 1
                elif row:
                    skipped += 1
                else:
                    skipped += 1
                continue

            # Read original
            try:
                original_bytes = img.read_bytes()
            except Exception as e:
                print(f"  {img.name}: read error: {e}")
                failed += 1
                continue

            # Optimize
            try:
                webp_bytes, ext, width, height = optimizer.optimize(original_bytes, img.name)
            except Exception as e:
                print(f"  {img.name}: optimize error: {e}")
                failed += 1
                continue

            # Save optimized
            try:
                webp_path.write_bytes(webp_bytes)
            except Exception as e:
                print(f"  {img.name}: write error: {e}")
                failed += 1
                continue

            # Update URL in DB
            old_url = f"/api/static/images/drive/FOTOS CONVENCIÓN 2026/{img.name}"
            new_url = f"/api/static/images/optimized/convenccion/{webp_name}"

            result = db.execute(text('''
                SELECT id FROM cms_media_items WHERE url = :url
            '''), {'url': old_url})
            row = result.fetchone()

            if row:
                db.execute(text('''
                    UPDATE cms_media_items
                    SET url = :new_url, filename = :filename, mime_type = 'image/webp'
                    WHERE id = :id
                '''), {'new_url': new_url, 'filename': webp_name, 'id': row[0]})

            orig_size = len(original_bytes)
            new_size = len(webp_bytes)
            ratio = orig_size / max(new_size, 1)
            optimized += 1

        db.commit()

        # Print summary
        print(f"\nResults:")
        print(f"  Optimized: {optimized}")
        print(f"  Skipped (already done): {skipped}")
        print(f"  Failed: {failed}")

        # Count total optimized files
        webp_files = list(OPTIMIZED_DIR.glob("*.webp"))
        total_size = sum(f.stat().st_size for f in webp_files)
        print(f"\nOptimized files: {len(webp_files)}")
        print(f"Total size: {total_size / (1024*1024):.1f} MB")

        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

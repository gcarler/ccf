#!/usr/bin/env python3
"""Sync convention photos from local storage to CMS media library.

Registers all images from the convention photos folder into the CMS media
table so they are available for use in public pages via the MediaPicker.

Usage:
    cd /root/ccf && python3 scripts/sync_convention_photos_to_cms.py
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

import mimetypes
from backend import models
from backend.core.database import SessionLocal

CONVENTION_DIR = _PROJECT_ROOT / "uploads" / "images" / "drive" / "FOTOS CONVENCIÓN 2026"
SECTION = "convenccion"
TAGS = ["convenccion", "2026", "evento", "iglesia"]

ADMIN_PERSONA_ID = None
ADMIN_SEDE_ID = None


def _init_defaults(db):
    global ADMIN_PERSONA_ID, ADMIN_SEDE_ID
    persona = db.query(models.Persona).first()
    if persona:
        ADMIN_PERSONA_ID = persona.id
        ADMIN_SEDE_ID = persona.sede_id
    else:
        raise RuntimeError("No persona found in database")


def _uploads_url(filename: str) -> str:
    """URL path for images served from uploads directory via /api/static mount."""
    return f"/api/static/images/drive/FOTOS CONVENCIÓN 2026/{filename}"


def _mime_for_file(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/jpeg"


def _alt_text_from_filename(name: str) -> str:
    stem = Path(name).stem
    return stem.replace("_", " ").replace("-", " ").title()


def main() -> int:
    if not CONVENTION_DIR.exists():
        print(f"Error: Convention dir not found: {CONVENTION_DIR}")
        return 1

    images = [
        p for p in CONVENTION_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    print(f"Found {len(images)} convention photos")

    db = SessionLocal()
    try:
        _init_defaults(db)
        print(f"Using persona: {ADMIN_PERSONA_ID}, sede: {ADMIN_SEDE_ID}")

        created = 0
        skipped = 0
        for img in sorted(images):
            url = _uploads_url(img.name)
            existing = db.query(models.CmsMediaItem).filter(
                models.CmsMediaItem.url == url
            ).first()
            if existing:
                skipped += 1
                continue

            media = models.CmsMediaItem(
                url=url,
                filename=img.name,
                mime_type=_mime_for_file(img),
                file_size=img.stat().st_size,
                alt_text=_alt_text_from_filename(img.name),
                section=SECTION,
                tags=TAGS,
                status="active",
                created_by_persona_id=ADMIN_PERSONA_ID,
                sede_id=ADMIN_SEDE_ID,
            )
            db.add(media)
            created += 1

        db.commit()
        print(f"\nResults:")
        print(f"  Created: {created}")
        print(f"  Skipped (already exists): {skipped}")
        print(f"  Total in CMS: {db.query(models.CmsMediaItem).filter(models.CmsMediaItem.section == SECTION).count()}")
        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

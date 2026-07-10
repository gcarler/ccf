from __future__ import annotations

import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

"""Register external public-site images in the CMS media library.

Local content images are now migrated into the CMS uploads directory via
``scripts/migrate_public_images_to_cms.py`` and should not live in
``frontend/public/``. This script only keeps references to external assets
(Unsplash, Picsum) tracked in ``CmsMediaItem`` so the audit stays accurate.
"""

import mimetypes
from urllib.parse import urlparse

from backend import models
from backend.core.database import SessionLocal

EXTERNAL_PUBLIC_IMAGES = {
    "home": [
        "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&q=80",
        "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&q=80",
        "https://images.unsplash.com/photo-1438032005730-c779502df39b?w=600&q=80",
        "https://picsum.photos/seed/1506905925346-21bda4d32df4/800/600",
    ],
    "cursos": [
        "https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080",
        "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600",
        "https://picsum.photos/seed/academia1/800/800",
        "https://picsum.photos/seed/academia2/800/800",
        "https://picsum.photos/seed/default-course/800/800",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1476611338391-6f395a0ebc7b?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&h=600&fit=crop",
        "https://picsum.photos/seed/tozer-book/400/600",
        "https://picsum.photos/seed/cslewis-book/400/600",
        "https://picsum.photos/seed/bonhoeffer-book/400/600",
        "https://picsum.photos/seed/yoder-book/400/600",
        "https://picsum.photos/",
    ],
    "conocer-a-jesus": [
        "https://picsum.photos/seed/1518623489648-a173ef7824f3/800/600",
    ],
    "eventos": [
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=600&q=80",
        "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=600&q=80",
        "https://images.unsplash.com/photo-1447690709975-318628b14c57?w=600&q=80",
        "https://images.unsplash.com/photo-1542614482-eb06198f3b14?w=800&q=80",
        "https://images.unsplash.com/photo-1483808161634-29aa1b1ecfc9?w=800&q=80",
        "https://images.unsplash.com/photo-1511895426328-dc8714191300?w=800&q=80",
        "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=500&q=80",
        "https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=500&q=80",
    ],
}


def _section_for_url(url: str, default: str = "public") -> str:
    if "/pastores" in url:
        return "pastores"
    if "curso" in url or "academia" in url or "book" in url:
        return "cursos"
    if "testimonio" in url:
        return "testimonios"
    if "event" in url or "evento" in url:
        return "eventos"
    return default


def _filename_for_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or parsed.netloc.replace(".", "_")


def _mime_for_url(url: str) -> str:
    mime, _ = mimetypes.guess_type(urlparse(url).path)
    if mime:
        return mime
    if "picsum.photos" in url or "images.unsplash.com" in url:
        return "image/jpeg"
    return "application/octet-stream"


def upsert_media(db, *, url: str, section: str, tags: list[str], file_size: int = 0) -> bool:
    row = db.query(models.CmsMediaItem).filter(models.CmsMediaItem.url == url).first()
    created = row is None
    if created:
        row = models.CmsMediaItem(url=url)
        db.add(row)
    row.filename = _filename_for_url(url)
    row.mime_type = _mime_for_url(url)
    row.file_size = file_size
    row.section = section
    row.tags = sorted(set([*tags, "public-site"]))
    row.status = "active"
    if not row.alt_text:
        row.alt_text = Path(row.filename or "Imagen").stem.replace("_", " ").replace("-", " ").title()
    return created


def register_external_public_images(db) -> tuple[int, int]:
    created = 0
    updated = 0
    for section, urls in EXTERNAL_PUBLIC_IMAGES.items():
        for url in urls:
            was_created = upsert_media(
                db,
                url=url,
                section=section,
                tags=["external-asset"],
            )
            created += int(was_created)
            updated += int(not was_created)
    return created, updated


def main() -> None:
    db = SessionLocal()
    try:
        external_created, external_updated = register_external_public_images(db)
        db.commit()
        print(f"External media: {external_created} created, {external_updated} updated")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

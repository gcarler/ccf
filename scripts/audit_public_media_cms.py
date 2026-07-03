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

"""Audit public-site image references against the CMS media library."""

import re
import sys
from pathlib import Path

from sync_public_media_to_cms import EXTERNAL_PUBLIC_IMAGES, PUBLIC_DIR, PUBLIC_IMAGE_EXTS, ROOT

sys.path.insert(0, str(ROOT))

from backend import models
from backend.core.database import SessionLocal

SCAN_ROOTS = [
    ROOT / "frontend" / "src" / "app" / "(public)",
    ROOT / "frontend" / "src" / "components" / "public",
    ROOT / "frontend" / "src" / "lib" / "data",
    ROOT / "frontend" / "src" / "data",
    ROOT / "scripts",
]

IMAGE_REF_RE = re.compile(
    r"(?:https://(?:images\.unsplash\.com|picsum\.photos)[^\"'`\\s)]+|/(?:images|pastores)/[^\"'`\\s)]+\\.(?:avif|jpe?g|png|svg|webp))"
)


def referenced_images() -> set[str]:
    refs: set[str] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            refs.update(IMAGE_REF_RE.findall(path.read_text(errors="ignore")))
    return refs


def public_file_images() -> set[str]:
    refs: set[str] = set()
    for path in PUBLIC_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in PUBLIC_IMAGE_EXTS:
            refs.add("/" + path.relative_to(PUBLIC_DIR).as_posix())
    return refs


def cms_media_urls() -> set[str]:
    db = SessionLocal()
    try:
        return {row.url for row in db.query(models.CmsMediaItem).all()}
    finally:
        db.close()


def main() -> None:
    refs = referenced_images() | public_file_images()
    cms = cms_media_urls()
    missing = sorted(refs - cms)
    print(f"Referenced/public images: {len(refs)}")
    print(f"CMS media URLs: {len(cms)}")
    if missing:
        print("Missing CMS media records:")
        for item in missing:
            print(f"  {item}")
        raise SystemExit(1)
    print("All referenced public images are registered in CMS media.")


if __name__ == "__main__":
    main()

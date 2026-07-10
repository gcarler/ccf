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

"""Audit that public-site images live in the CMS, not in frontend/public/."""

import re

ROOT = _PROJECT_ROOT
PUBLIC_DIR = ROOT / "frontend" / "public"

# Assets that legitimately stay as static system files (PWA, UI chrome).
ALLOWED_STATIC_FILES = {
    "icons/icon-192x192.png",
    "icons/icon-512x512.png",
    "manifest.json",
    "noise.svg",
}

SCAN_ROOTS = [
    ROOT / "frontend" / "src" / "app" / "(public)",
    ROOT / "frontend" / "src" / "components" / "public",
    ROOT / "frontend" / "src" / "lib" / "data",
    ROOT / "frontend" / "src" / "data",
    ROOT / "scripts",
]

LOCAL_IMAGE_REF_RE = re.compile(
    r"/(?:images|pastores)/[^\"'`\s)]+\.(?:avif|jpe?g|png|svg|webp)"
)


def local_images_in_public() -> set[str]:
    """Return content images still present in frontend/public/."""
    found: set[str] = set()
    for path in PUBLIC_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(PUBLIC_DIR).as_posix()
        if rel in ALLOWED_STATIC_FILES:
            continue
        found.add("/" + rel)
    return found


def local_image_references_in_code() -> set[str]:
    """Return hardcoded references to /images/ or /pastores/ in public code."""
    refs: set[str] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            text = path.read_text(errors="ignore")
            for match in LOCAL_IMAGE_REF_RE.finditer(text):
                start = match.start()
                # Require the match to be preceded by start-of-text, quote, or whitespace.
                # This avoids matching "images/pastores/..." inside migration script strings.
                if start > 0 and text[start - 1] not in {'"', "'", '`', ' ', '\n', '\t'}:
                    continue
                refs.add(match.group())
    return refs


def main() -> None:
    in_public = local_images_in_public()
    in_code = local_image_references_in_code()

    if in_public:
        print("Content images still present in frontend/public/:")
        for item in sorted(in_public):
            print(f"  {item}")

    if in_code:
        print("Hardcoded references to local /images/ or /pastores/ found:")
        for item in sorted(in_code):
            print(f"  {item}")

    if in_public or in_code:
        raise SystemExit(1)

    print("OK: all public-site images are served from the CMS.")


if __name__ == "__main__":
    main()

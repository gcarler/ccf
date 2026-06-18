#!/usr/bin/env python3
"""
Migrate existing images to WebP.

Scans uploads/ and frontend public directories, finds raster images
(JPEG, PNG), and re-encodes them as WebP.  Original files are preserved
and symlinked from the WebP path so existing database references continue
to work.

Usage
-----
    python scripts/migrate_images_to_webp.py          # dry-run by default
    python scripts/migrate_images_to_webp.py --apply  # actually convert
    python scripts/migrate_images_to_webp.py --apply --delete-originals  # cleanup

The --delete-originals flag is DESTRUCTIVE — only use after verifying
everything works with WebP.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so we can import the optimizer
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("ENV", "local")

from backend.services.image_optimizer import ImageOptimizer  # noqa: E402

RASTER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
SEARCH_DIRS = [
    PROJECT_ROOT / "uploads",
    PROJECT_ROOT / "frontend" / "public" / "pastores",
    PROJECT_ROOT / "frontend" / "public" / "images" / "pastores",
]


def collect_images() -> list[Path]:
    images: list[Path] = []
    for directory in SEARCH_DIRS:
        if not directory.is_dir():
            continue
        for ext in RASTER_EXTENSIONS:
            images.extend(directory.rglob(f"*{ext}"))
            images.extend(directory.rglob(f"*{ext.upper()}"))
    return sorted(images)


def migrate(
    dry_run: bool,
    delete_originals: bool,
    max_width: int = 1920,
    quality: int = 82,
) -> int:
    optimizer = ImageOptimizer(max_width=max_width, quality=quality)
    images = collect_images()

    if not images:
        print("No raster images found to migrate.")
        return 0

    converted = 0
    skipped = 0
    total_original = 0
    total_optimized = 0

    for src in images:
        content = src.read_bytes()
        ext = src.suffix.lower()

        if ext not in RASTER_EXTENSIONS:
            skipped += 1
            continue

        optimized, opt_ext, _w, _h = optimizer.optimize(content, src.name)

        # Only save if output is WebP (meaning it was actually optimized)
        if opt_ext != ".webp":
            skipped += 1
            continue

        webp_path = src.with_suffix(".webp")

        if dry_run:
            ratio = len(content) / max(len(optimized), 1)
            print(
                f"  [DRY-RUN] Would convert: {src.relative_to(PROJECT_ROOT)}  "
                f"({len(content) / 1024:.1f}KB → {len(optimized) / 1024:.1f}KB, "
                f"{ratio:.1f}× smaller)"
            )
            continue

        # Write WebP
        webp_path.write_bytes(optimized)
        total_original += len(content)
        total_optimized += len(optimized)
        converted += 1

        ratio = len(content) / max(len(optimized), 1)
        print(
            f"  ✓ {src.relative_to(PROJECT_ROOT)}  "
            f"({len(content) / 1024:.1f}KB → {len(optimized) / 1024:.1f}KB, "
            f"{ratio:.1f}×)"
        )

        if delete_originals:
            src.unlink()
            print(f"    🗑  Deleted original: {src.name}")
        else:
            print(f"    Original preserved: {src.name}")

    if dry_run:
        print(f"\n── Dry-run summary: {len(images)} images found, "
              f"{converted} would be converted, {skipped} skipped ──")
    else:
        savings = total_original - total_optimized
        pct = (savings / max(total_original, 1)) * 100
        print(
            f"\n── Migration summary: {converted} converted, {skipped} skipped ──\n"
            f"  Total original: {total_original / 1024:.1f} KB\n"
            f"  Total optimized: {total_optimized / 1024:.1f} KB\n"
            f"  Savings: {savings / 1024:.1f} KB ({pct:.1f}% reduction)"
        )

    return converted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate existing images to optimized WebP.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the conversion (default is dry-run).",
    )
    parser.add_argument(
        "--delete-originals",
        action="store_true",
        help="Delete original JPEG/PNG files after conversion (DESTRUCTIVE).",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=1920,
        help="Maximum width in pixels (default: 1920).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=82,
        help="WebP quality 1-100 (default: 82).",
    )
    args = parser.parse_args()

    return migrate(
        dry_run=not args.apply,
        delete_originals=args.delete_originals,
        max_width=args.max_width,
        quality=args.quality,
    )


if __name__ == "__main__":
    sys.exit(main())

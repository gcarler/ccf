from __future__ import annotations

"""Migrate archived public-site content images into the CMS media library.

The command is intentionally dry-run by default.  Use ``--apply`` to write
media rows and update references, and add ``--remove-source`` only after the
local/public URLs have been verified.  The migration source is versioned outside the public web root at
``scripts/assets/public-site``. System assets (favicon, PWA icons, manifest,
noise texture and the generic OG fallback) remain in ``frontend/public`` by design.

Examples::

    python scripts/migrate_public_images_to_cms.py
    python scripts/migrate_public_images_to_cms.py --apply
    python scripts/migrate_public_images_to_cms.py --apply --remove-source
"""

import argparse
import hashlib
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import inspect as sqlalchemy_inspect

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend import crud, models  # noqa: E402
from backend.core.config import get_settings  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
from backend.core.storage import storage_service  # noqa: E402

MIGRATION_SOURCE_DIR = _PROJECT_ROOT / "scripts" / "assets" / "public-site"
IMAGE_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
SOURCE_TAG_PREFIX = "public-source:"

# These are application chrome or generic fallbacks, not editorial content.
SYSTEM_ASSETS = {
    "favicon.ico",
    "manifest.json",
    "noise.svg",
    "og-default.png",
    "icons/icon-192x192.png",
    "icons/icon-512x512.png",
}


def is_content_image(relative_path: str | Path) -> bool:
    """Return whether a public asset is an editorial image to migrate."""
    rel = Path(relative_path).as_posix()
    return rel not in SYSTEM_ASSETS and Path(rel).suffix.lower() in IMAGE_SUFFIXES


def iter_content_images(public_dir: Path = MIGRATION_SOURCE_DIR) -> Iterable[Path]:
    """Yield all content images below ``public_dir`` in stable order."""
    if not public_dir.exists():
        return
    for path in sorted(public_dir.rglob("*")):
        if path.is_file() and is_content_image(path.relative_to(public_dir)):
            yield path


def source_url(relative_path: str | Path) -> str:
    """Convert a public-relative path into the URL used by the frontend."""
    return "/" + Path(relative_path).as_posix().lstrip("/")


def source_tag(relative_path: str | Path) -> str:
    return SOURCE_TAG_PREFIX + Path(relative_path).as_posix()


def replace_image_urls(value: Any, replacements: dict[str, str]) -> tuple[Any, int]:
    """Recursively replace image URLs in JSON-compatible CMS payloads."""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        count = 0
        for key, child in value.items():
            result[key], changed = replace_image_urls(child, replacements)
            count += changed
        return result, count
    if isinstance(value, list):
        result = []
        count = 0
        for child in value:
            replaced, changed = replace_image_urls(child, replacements)
            result.append(replaced)
            count += changed
        return result, count
    if isinstance(value, str):
        result = value
        count = 0
        for old, new in replacements.items():
            if old in result:
                result = result.replace(old, new)
                count += 1
        return result, count
    return value, 0


def _find_admin_user(db) -> models.Usuario:
    user = db.query(models.Usuario).filter(models.Usuario.email == "gscarlosernesto@gmail.com").first()
    if user is None:
        user = (
            db.query(models.Usuario)
            .filter(models.Usuario.is_active.is_(True), models.Usuario.sede_id.isnot(None))
            .first()
        )
    if user is None:
        raise RuntimeError("No active admin/user with sede found to own CMS media items")
    return user


def _media_by_source(db) -> dict[str, models.CmsMediaItem]:
    """Build the idempotency index from source tags and legacy URLs."""
    result: dict[str, models.CmsMediaItem] = {}
    for item in db.query(models.CmsMediaItem).all():
        tags = item.tags if isinstance(item.tags, list) else []
        for tag in tags:
            if isinstance(tag, str) and tag.startswith(SOURCE_TAG_PREFIX):
                result[tag[len(SOURCE_TAG_PREFIX) :]] = item
        if isinstance(item.url, str) and item.url.startswith("/images/"):
            result[item.url.lstrip("/")] = item
    return result


def _alt_text(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip().title() or path.name


def _register_image(db, user, path: Path, existing: dict[str, models.CmsMediaItem]) -> tuple[str, bool]:
    relative = path.relative_to(MIGRATION_SOURCE_DIR).as_posix()
    current = existing.get(relative)
    old_url = source_url(relative)
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()[:16]
    current_tags = current.tags if current is not None and isinstance(current.tags, list) else []
    current_hash = next(
        (tag.removeprefix("source-sha256:") for tag in current_tags if isinstance(tag, str) and tag.startswith("source-sha256:")),
        None,
    )
    if current is not None and current.status != "archived" and current.url != old_url and current_hash == digest:
        return current.url, False

    mime_type = mimetypes.guess_type(path.name)[0] or "image/webp"
    # Keep storage names collision-safe when two archived directories contain
    # the same basename but different bytes. Identical bytes may share a blob.
    storage_filename = f"{digest}-{path.name}"
    url = storage_service.save_file(content, storage_filename, subfolder="cms/public-site")
    tags = ["public-site", "migrated", source_tag(relative), f"source-sha256:{digest}"]
    if current is not None and current.status != "archived":
        # A legacy row may still point at /images/...; reuse its identity while
        # moving the blob, so foreign references do not accumulate duplicates.
        current.url = url
        current.alt_text = _alt_text(path)
        current.section = "public-site"
        current.tags = tags
        current.filename = path.name
        current.mime_type = mime_type
        current.file_size = len(content)
        current.status = "active"
        return url, False

    row = crud.create_cms_media_item(
        db,
        url=url,
        alt_text=_alt_text(path),
        section="public-site",
        tags=tags,
        created_by=user.id,
        filename=path.name,
        mime_type=mime_type,
        file_size=len(content),
        actor_user_id=user.id,
    )
    existing[relative] = row
    return row.url, True


def _rewrite_model_field(rows: Iterable[Any], field_name: str, replacements: dict[str, str]) -> int:
    changed = 0
    for row in rows:
        value = getattr(row, field_name, None)
        if not isinstance(value, str):
            continue
        updated, count = replace_image_urls(value, replacements)
        if count:
            setattr(row, field_name, updated)
            changed += count
    return changed


def rewrite_cms_references(
    db,
    replacements: dict[str, str],
    affected_page_ids: set[Any] | None = None,
) -> int:
    """Rewrite live rows while preserving immutable version history.

    Published pages are re-versioned by ``run`` after this function returns;
    historical ``CmsPageVersion.snapshot_json`` rows are deliberately left
    untouched so editorial history remains auditable.
    """
    changed = 0

    sections = db.query(models.CmsSection).all()
    for row in sections:
        updated, count = replace_image_urls(row.props_json or {}, replacements)
        if count:
            row.props_json = updated
            changed += count
            if affected_page_ids is not None:
                affected_page_ids.add(row.page_id)

    changed += _rewrite_model_field(db.query(models.CmsPost).all(), "featured_image_url", replacements)

    # Theme tokens and page SEO are live configuration rather than historical
    # snapshots, so they must follow the migrated media URL too.
    for row in db.query(models.CmsTheme).all():
        updated, count = replace_image_urls(row.tokens_json or {}, replacements)
        if count:
            row.tokens_json = updated
            changed += count

    for row in db.query(models.CmsPage).all():
        updated, count = replace_image_urls(row.seo_json or {}, replacements)
        if count:
            row.seo_json = updated
            changed += count

    # Pastoral profiles are consumed by the public pastoral-team projection.
    persona_model = getattr(models, "Persona", None)
    if persona_model is not None:
        changed += _rewrite_model_field(db.query(persona_model).all(), "photo_url", replacements)

    # Announcements are optional across deployments; keep this migration
    # compatible with databases that do not load that legacy model.
    announcement_model = getattr(models, "Announcement", None)
    announcements_table_exists = sqlalchemy_inspect(db.bind).has_table("announcements")
    if announcement_model is not None and announcements_table_exists and hasattr(announcement_model, "image_url"):
        changed += _rewrite_model_field(db.query(announcement_model).all(), "image_url", replacements)

    return changed


def _live_source_references(db, replacements: dict[str, str]) -> set[str]:
    """Find old URLs that would break if source files were removed."""
    unresolved: set[str] = set()
    rows: list[Any] = []
    rows.extend(db.query(models.CmsSection).all())
    rows.extend(db.query(models.CmsPost).all())
    rows.extend(db.query(models.CmsPage).all())
    rows.extend(db.query(models.CmsTheme).all())
    persona_model = getattr(models, "Persona", None)
    if persona_model is not None:
        rows.extend(db.query(persona_model).all())
    for row in rows:
        for field_name in ("props_json", "featured_image_url", "seo_json", "tokens_json", "photo_url"):
            value = getattr(row, field_name, None)
            encoded = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value or "")
            unresolved.update(old for old in replacements if old in encoded)

    # The public endpoint reads only the current published snapshot. Historical
    # versions are intentionally allowed to retain legacy URLs, but a current
    # published snapshot must never point at a source that is about to vanish.
    for page in db.query(models.CmsPage).filter(models.CmsPage.status == "published").all():
        version = getattr(page, "published_version", None)
        snapshot = getattr(version, "snapshot_json", None) if version is not None else None
        encoded = json.dumps(snapshot, ensure_ascii=False) if isinstance(snapshot, (dict, list)) else str(snapshot or "")
        unresolved.update(old for old in replacements if old in encoded)
    return unresolved


def _media_file_exists(url: str) -> bool:
    if not url.startswith("/api/static/"):
        return False
    relative = url.removeprefix("/api/static/")
    path = Path(get_settings().uploads_dir) / relative
    return path.is_file()


def _remove_sources(paths: list[Path]) -> int:
    removed = 0
    for path in paths:
        if path.exists():
            path.unlink()
            removed += 1
    # Remove empty editorial directories without touching public root/system dirs.
    for directory in sorted({path.parent for path in paths}, key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    return removed


def run(*, apply: bool, remove_source: bool) -> int:
    paths = list(iter_content_images())
    print(f"Editorial public images discovered: {len(paths)}")
    for path in paths:
        print(f"  {path.relative_to(MIGRATION_SOURCE_DIR).as_posix()}")

    if not apply:
        print("DRY RUN: no database, storage or source files were modified.")
        return 0

    with SessionLocal() as db:
        user = _find_admin_user(db)
        existing = _media_by_source(db)
        replacements: dict[str, str] = {}
        created = 0
        for path in paths:
            relative = path.relative_to(MIGRATION_SOURCE_DIR).as_posix()
            url, was_created = _register_image(db, user, path, existing)
            replacements[source_url(relative)] = url
            created += int(was_created)

        affected_page_ids: set[Any] = set()
        rewritten = rewrite_cms_references(db, replacements, affected_page_ids)
        db.commit()

        # A public endpoint serves the published snapshot, not the mutable
        # draft rows. Create a fresh version for affected published pages;
        # leave all older snapshots untouched.
        from backend.crud.cms.pages import transition_cms_page_status

        published_pages = (
            db.query(models.CmsPage)
            .filter(models.CmsPage.id.in_(affected_page_ids), models.CmsPage.status == "published")
            .all()
            if affected_page_ids
            else []
        )
        for page in published_pages:
            transition_cms_page_status(
                db,
                page,
                "publish",
                user.id,
                notes="Migración de imágenes públicas al CMS",
            )

        print(f"CMS media items created/updated: {created}")
        print(f"CMS live references rewritten: {rewritten}")
        print(f"Published pages re-versioned: {len(published_pages)}")

        if remove_source:
            unresolved = _live_source_references(db, replacements)
            missing = [url for url in replacements.values() if not _media_file_exists(url)]
            if unresolved:
                raise RuntimeError(f"Cannot remove sources; live references remain: {sorted(unresolved)[:5]}")
            if missing:
                raise RuntimeError(f"Cannot remove sources; CMS files are missing: {missing[:5]}")

    if remove_source:
        removed = _remove_sources(paths)
        print(f"Editorial source files removed: {removed}")
    else:
        print("Source files retained. Re-run with --remove-source after URL verification.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write media rows and rewrite CMS references")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="explicitly select the default read-only mode",
    )
    parser.add_argument(
        "--remove-source",
        action="store_true",
        help="remove migrated files from the versioned migration archive (requires --apply)",
    )
    args = parser.parse_args()
    if args.remove_source and not args.apply:
        parser.error("--remove-source requires --apply")
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run are mutually exclusive")
    return run(apply=args.apply, remove_source=args.remove_source)


if __name__ == "__main__":
    raise SystemExit(main())

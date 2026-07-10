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

"""Migrate public-site images from frontend/public/ to CMS media library.

Copies content images into the configured uploads directory and registers each
one as a CmsMediaItem with proper sede_id and created_by_persona_id (Axioma 3).

Run:
    cd /root/ccf && source venv/bin/activate && python scripts/migrate_public_images_to_cms.py
"""

import mimetypes
import uuid
from datetime import datetime, timezone

from backend import crud, models
from backend.core.database import SessionLocal
from backend.core.storage import storage_service

PUBLIC_DIR = _PROJECT_ROOT / "frontend" / "public"
UPLOADS_DIR = _PROJECT_ROOT / "uploads"

# Images that are part of the public site content and should be CMS-managed.
# Format: relative path from frontend/public -> CMS section name.
CONTENT_IMAGES: dict[str, str] = {
    "images/iglesia-logo.png": "site_logo",
    "images/pastores-banner.jpg": "home_banner",
    "images/pastores/luis_ricardo_meza.webp": "pastores",
    "images/pastores/histar_ariza.webp": "pastores",
    "images/pastores/alex_elvia.webp": "pastores",
    "images/pastores/camilo_alba.webp": "pastores",
    "images/pastores/fernando_monica.webp": "pastores",
    "images/pastores/nehemias_morales.webp": "pastores",
    "images/pastores/yair_macea.webp": "pastores",
    "images/pastores/yanedith_wilches.webp": "pastores",
    "images/pastores/martina_herrera.webp": "pastores",
}


def _find_admin_user(db) -> models.Usuario:
    """Return the canonical admin user used for CMS seeds/migrations."""
    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == "gscarlosernesto@gmail.com")
        .first()
    )
    if user is None:
        # Fallback to the first active user with a sede.
        user = (
            db.query(models.Usuario)
            .filter(models.Usuario.is_active.is_(True), models.Usuario.sede_id.isnot(None))
            .first()
        )
    if user is None:
        raise RuntimeError("No active admin/user with sede found to own CMS media items")
    return user


def _ensure_site(db) -> models.CmsSite:
    site = db.query(models.CmsSite).filter(models.CmsSite.site_key == "ccf").first()
    if site is None:
        raise RuntimeError("CMS site 'ccf' not found")
    return site


def _url_already_registered(db, url: str) -> bool:
    return db.query(models.CmsMediaItem).filter(models.CmsMediaItem.url == url).first() is not None


def migrate_image(db, user: models.Usuario, rel_path: str, section: str) -> tuple[bool, str]:
    source = PUBLIC_DIR / rel_path
    if not source.is_file():
        print(f"  SKIP (missing): {rel_path}")
        return False, ""

    content = source.read_bytes()
    filename = source.name
    ext = source.suffix.lower().lstrip(".")

    # Use original quality for SVGs; optimize raster images.
    if ext == "svg":
        storage_path = storage_service.save_file_original(content, filename, subfolder=f"cms/{section}")
    else:
        storage_path = storage_service.save_file(content, filename, subfolder=f"cms/{section}")

    # StorageService returns /static/..., but the public frontend serves
    # CMS assets from /api/static/...
    public_url = f"/api/static{storage_path}"

    if _url_already_registered(db, public_url):
        print(f"  SKIP (already registered): {public_url}")
        return False, public_url

    mime, _ = mimetypes.guess_type(str(source))
    alt_text = Path(filename).stem.replace("_", " ").replace("-", " ").title()

    crud.create_cms_media_item(
        db,
        url=public_url,
        alt_text=alt_text,
        section=section,
        tags=["public-site", "auto-migrated"],
        created_by=user.id,
        filename=filename,
        mime_type=mime or "image/webp",
        file_size=len(content),
        actor_user_id=user.id,
    )
    print(f"  CREATED: {rel_path} -> {public_url}")
    return True, public_url


def update_site_logo_token(db: SessionLocal, site: models.CmsSite, logo_url: str) -> bool:
    """Point the active theme's --site-logo-url to the migrated logo."""
    theme = (
        db.query(models.CmsTheme)
        .filter(models.CmsTheme.site_id == site.id, models.CmsTheme.is_active.is_(True))
        .first()
    )
    if theme is None:
        print("  No active theme found; logo token not updated")
        return False
    tokens = dict(theme.tokens_json or {})
    if tokens.get("--site-logo-url") == logo_url:
        return False
    tokens["--site-logo-url"] = logo_url
    theme.tokens_json = tokens
    theme.updated_at = datetime.now(timezone.utc)
    db.add(theme)
    db.commit()
    print(f"  UPDATED theme --site-logo-url -> {logo_url}")
    return True


def main() -> int:
    db = SessionLocal()
    try:
        site = _ensure_site(db)
        user = _find_admin_user(db)
        print(f"Using site 'ccf' ({site.id}) and user {user.email} ({user.id})")

        created_total = 0
        logo_url = ""
        for rel_path, section in CONTENT_IMAGES.items():
            created, url = migrate_image(db, user, rel_path, section)
            created_total += int(created)
            if section == "site_logo" and url:
                logo_url = url

        if logo_url:
            update_site_logo_token(db, site, logo_url)

        db.commit()
        print(f"\n✅ Migration complete. {created_total} new media items registered.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

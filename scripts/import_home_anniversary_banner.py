#!/usr/bin/env python3
"""Import the 40th-anniversary banner into CMS media and the home hero."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import requests

_HERE = Path(__file__).resolve()
_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _ROOT is None:
    raise RuntimeError("backend package not found")
sys.path.insert(0, str(_ROOT))

from backend import crud, models  # noqa: E402
from backend.core.cache_v2 import invalidate_cached_public  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
from backend.core.storage import storage_service  # noqa: E402

DRIVE_FILE_ID = "1O1o6b8ES-NItkkvrkCpqKOv8s-K89UkA"
SITE_KEY = "ccf"
PAGE_SLUG = "home"
FILENAME = "aniversario40-home-banner.png"
TARGET_HREF = "/aniversario40"


def _admin_user(db: object) -> models.Usuario:
    user = db.query(models.Usuario).filter(models.Usuario.email == "gscarlosernesto@gmail.com").first()
    if user is None:
        user = (
            db.query(models.Usuario)
            .filter(models.Usuario.is_active.is_(True), models.Usuario.sede_id.isnot(None))
            .first()
        )
    if user is None:
        raise RuntimeError("No active CMS user found")
    return user


def main() -> int:
    response = requests.get(
        f"https://drive.google.com/uc?export=download&id={DRIVE_FILE_ID}",
        timeout=120,
    )
    response.raise_for_status()
    content = response.content

    with SessionLocal() as db:
        user = _admin_user(db)
        media = (
            db.query(models.CmsMediaItem)
            .filter(models.CmsMediaItem.filename == FILENAME)
            .first()
        )
        if media is None:
            public_url = storage_service.save_file(content, FILENAME, subfolder="cms/home")
            media = crud.create_cms_media_item(
                db,
                url=public_url,
                alt_text="Banner 40 años CCF",
                section="home",
                tags=["public-site", "anniversary40", "home-hero"],
                created_by=user.id,
                filename=FILENAME,
                mime_type="image/webp",
                file_size=len(content),
                actor_user_id=user.id,
            )
        public_url = media.url

        site = db.query(models.CmsSite).filter(models.CmsSite.site_key == SITE_KEY).first()
        if site is None:
            raise RuntimeError(f"CMS site {SITE_KEY!r} not found")
        page = db.query(models.CmsPage).filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == PAGE_SLUG).first()
        if page is None:
            raise RuntimeError("Home CMS page not found")
        hero = (
            db.query(models.CmsSection)
            .filter(models.CmsSection.page_id == page.id, models.CmsSection.type == "hero")
            .order_by(models.CmsSection.sort_order.asc())
            .first()
        )
        if hero is None:
            raise RuntimeError("Home hero section not found")

        props = dict(hero.props_json or {})
        slides = [slide for slide in (props.get("slides") or []) if isinstance(slide, dict)]
        slides = [slide for slide in slides if slide.get("href") != TARGET_HREF]
        slides.insert(
            0,
            {
                "src": public_url,
                "alt": "40 años iluminando generaciones — CCF",
                "title": "40 años iluminando generaciones",
                "caption": "Celebra con nosotros la historia de Comunidad Cristiana Faro.",
                "href": TARGET_HREF,
                "status": "published",
            },
        )
        props["slides"] = slides
        hero.props_json = props
        db.commit()
        invalidate_cached_public("public_page", site_key=SITE_KEY, slug=PAGE_SLUG)
        print(f"Home hero updated with {public_url}")

    # Rebuild the published snapshot so the public endpoint serves the CMS edit.
    from scripts.republish_home_cms_snapshot import republish  # noqa: E402

    republish(SITE_KEY, PAGE_SLUG, actor="scripts/import_home_anniversary_banner.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

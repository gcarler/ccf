"""Ensure public route slugs exist as published CMS v2 pages.

These pages are intentionally created without sections. Public routes keep their
current fallback rendering until editors publish real CMS sections, but the CMS
public page contract returns 200 instead of producing browser 404 noise.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func  # noqa: E402

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402


PUBLIC_PAGES = {
    "home": "Inicio",
    "nosotros": "Quienes Somos",
    "eventos": "Eventos",
    "predicas": "Predicas",
    "cursos": "Cursos",
    "sedes": "Sedes",
    "testimonios": "Testimonios",
    "conocer-a-jesus": "Conocer a Jesus",
    "boletin": "Boletin",
    "privacidad": "Politica de Privacidad",
    "bienvenida": "Bienvenida",
}


def ensure_page(db, site, slug: str, title: str) -> tuple[bool, bool]:
    created = False
    published = False
    page = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == slug)
        .first()
    )
    if page is None:
        page = models.CmsPage(
            site_id=site.id,
            slug=slug,
            title=title,
            status="draft",
            seo_json={},
        )
        db.add(page)
        db.flush()
        created = True
    elif page.title != title:
        page.title = title

    if page.status != "published" or page.published_version_id is None:
        max_version = (
            db.query(func.max(models.CmsPageVersion.version_number))
            .filter(models.CmsPageVersion.page_id == page.id)
            .scalar()
            or 0
        )
        version = models.CmsPageVersion(
            page_id=page.id,
            version_number=int(max_version) + 1,
            snapshot_json={
                "page": {
                    "id": str(page.id),
                    "slug": page.slug,
                    "title": page.title,
                    "seo_json": page.seo_json or {},
                    "status": "published",
                },
                "sections": [],
            },
            notes="Ensure public CMS page contract for production fallback route",
        )
        db.add(version)
        db.flush()
        page.status = "published"
        page.published_version_id = version.id
        db.add(
            models.CmsPublishLog(
                site_id=site.id,
                page_id=page.id,
                entity_type="page",
                entity_id=page.id,
                action="publish",
                from_status="draft",
                to_status="published",
                metadata_json={"source": "ensure_public_cms_pages"},
            )
        )
        published = True

    return created, published


def main() -> int:
    with SessionLocal() as db:
        site = db.query(models.CmsSite).filter(models.CmsSite.site_key == "faro").first()
        if site is None:
            raise RuntimeError("CMS site 'faro' not found")

        created = 0
        published = 0
        for slug, title in PUBLIC_PAGES.items():
            did_create, did_publish = ensure_page(db, site, slug, title)
            created += int(did_create)
            published += int(did_publish)
        db.commit()
        print(f"Public CMS pages ensured: {len(PUBLIC_PAGES)}")
        print(f"Created: {created}")
        print(f"Published or republished: {published}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

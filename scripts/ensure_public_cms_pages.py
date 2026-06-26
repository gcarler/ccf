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

    # Obtener secciones actuales en db
    sections = (
        db.query(models.CmsSection)
        .filter(models.CmsSection.page_id == page.id)
        .order_by(models.CmsSection.sort_order.asc())
        .all()
    )
    sections_data = [
        {
            "id": str(sec.id),
            "section_key": sec.section_key,
            "type": sec.type,
            "props_json": sec.props_json or {},
            "sort_order": sec.sort_order,
            "is_visible": sec.is_visible,
            "status": getattr(sec, "status", "active") or "active",
        }
        for sec in sections
    ]

    # Verificar si necesitamos publicar
    needs_publish = False
    if page.status != "published" or page.published_version_id is None:
        needs_publish = True
    else:
        current_version = db.query(models.CmsPageVersion).filter(models.CmsPageVersion.id == page.published_version_id).first()
        if not current_version or not current_version.snapshot_json:
            needs_publish = True
        else:
            snapshot_sections = current_version.snapshot_json.get("sections", [])
            if len(snapshot_sections) != len(sections_data):
                needs_publish = True
            else:
                for s1, s2 in zip(snapshot_sections, sections_data):
                    if s1.get("section_key") != s2.get("section_key") or s1.get("props_json") != s2.get("props_json"):
                        needs_publish = True
                        break

    if needs_publish:
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
                "sections": sections_data,
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

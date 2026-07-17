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

"""Ensure public route slugs exist as published CMS v2 pages.

These pages are intentionally created without sections. Public routes keep their
current fallback rendering until editors publish real CMS sections, but the CMS
public page contract returns 200 instead of producing browser 404 noise.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func  # noqa: E402
from sqlalchemy import text  # noqa: E402

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


def _load_site_id(db, site_key: str):
    row = db.execute(
        text(
            """
            SELECT id
            FROM cms_sites
            WHERE site_key = :site_key
            LIMIT 1
            """
        ),
        {"site_key": site_key},
    ).mappings().first()
    if row is None:
        raise RuntimeError(f"CMS site {site_key!r} not found")
    return row["id"]


def _load_page_row(db, site_id, slug: str):
    row = db.execute(
        text(
            """
            SELECT id, site_id, slug, title, status, seo_json, published_version_id
            FROM cms_pages
            WHERE site_id = :site_id AND slug = :slug
            LIMIT 1
            """
        ),
        {"site_id": str(site_id), "slug": slug},
    ).mappings().first()
    return dict(row) if row is not None else None


def ensure_page(db, site_id, slug: str, title: str) -> tuple[bool, bool]:
    created = False
    published = False
    page = _load_page_row(db, site_id, slug)
    if page is None:
        page = models.CmsPage(
            site_id=site_id,
            slug=slug,
            title=title,
            status="draft",
            seo_json={},
        )
        db.add(page)
        db.flush()
        created = True
    elif page["title"] != title:
        db.execute(
            text(
                """
                UPDATE cms_pages
                SET title = :title
                WHERE id = :id
                """
            ),
            {"title": title, "id": str(page["id"])},
        )
        page["title"] = title

    # Obtener secciones actuales en db
    sections = (
        db.query(models.CmsSection)
        .filter(models.CmsSection.page_id == (page.id if hasattr(page, "id") else page["id"]))
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
    page_status = page.status if hasattr(page, "status") else page["status"]
    page_published_version_id = (
        page.published_version_id if hasattr(page, "published_version_id") else page["published_version_id"]
    )
    page_id = page.id if hasattr(page, "id") else page["id"]
    page_seo_json = page.seo_json if hasattr(page, "seo_json") else page["seo_json"]
    page_slug = page.slug if hasattr(page, "slug") else page["slug"]

    if page_status != "published" or page_published_version_id is None:
        needs_publish = True
    else:
        current_version = (
            db.query(models.CmsPageVersion)
            .filter(models.CmsPageVersion.id == page_published_version_id)
            .first()
        )
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
            .filter(models.CmsPageVersion.page_id == page_id)
            .scalar()
            or 0
        )
        version = models.CmsPageVersion(
            page_id=page_id,
            version_number=int(max_version) + 1,
            snapshot_json={
                "page": {
                    "id": str(page_id),
                    "slug": page_slug,
                    "title": title,
                    "seo_json": page_seo_json or {},
                    "status": "published",
                },
                "sections": sections_data,
            },
            notes="Ensure public CMS page contract for production fallback route",
        )
        db.add(version)
        db.flush()
        if hasattr(page, "published_version_id"):
            page.status = "published"
            page.published_version_id = version.id
            db.add(page)
        else:
            db.execute(
                text(
                    """
                    UPDATE cms_pages
                    SET status = 'published',
                        published_version_id = :published_version_id
                    WHERE id = :id
                    """
                ),
                {"published_version_id": str(version.id), "id": str(page_id)},
            )
        db.add(
            models.CmsPublishLog(
                site_id=site_id,
                page_id=page_id,
                entity_type="page",
                entity_id=str(page_id),
                action="publish",
                from_status=page_status,
                to_status="published",
                metadata_json={"source": "ensure_public_cms_pages"},
            )
        )
        published = True

    return created, published


def main() -> int:
    with SessionLocal() as db:
        site_id = _load_site_id(db, "ccf")

        created = 0
        published = 0
        for slug, title in PUBLIC_PAGES.items():
            did_create, did_publish = ensure_page(db, site_id, slug, title)
            created += int(did_create)
            published += int(did_publish)
        db.commit()
        print(f"Public CMS pages ensured: {len(PUBLIC_PAGES)}")
        print(f"Created: {created}")
        print(f"Published or republished: {published}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

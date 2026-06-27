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

#!/usr/bin/env python3
"""Migrate page_contents → cms_sites / cms_pages / cms_sections.

Run once:
    cd /root/ccf && source venv/bin/activate && python scripts/seed_cms.py
"""
import json
import sys
import os

sys.path.insert(0, "/root/ccf")
os.environ.setdefault("DATABASE_URL", "")

from backend.core.database import SessionLocal
from backend import models

# page_key → (page_slug, sort_order_within_page)
SECTION_MAP: dict[str, tuple[str, int]] = {
    "faro_home_hero":        ("inicio",           0),
    "faro_about_hero":       ("nosotros",          0),
    "faro_about_feed":       ("nosotros",          1),
    "faro_pastores_feed":     ("nosotros",          2),
    "faro_events_hero":      ("eventos",           0),
    "faro_public_events":    ("eventos",           1),
    "faro_sermons_hero":     ("predicas",          0),
    "faro_sermons_feed":     ("predicas",          1),
    "faro_courses_hero":     ("cursos",            0),
    "faro_courses_feed":     ("cursos",            1),
    "faro_locations_hero":   ("sedes",             0),
    "faro_locations_feed":   ("sedes",             1),
    "faro_discover_hero":    ("conocer-a-jesus",   0),
    "faro_discover_feed":    ("conocer-a-jesus",   1),
    "faro_testimonios_hero": ("testimonios",       0),
    "faro_privacidad":       ("privacidad",        0),
    "faro_nav_items":        ("_global",           0),
    "navbar_items":          ("_global",           1),
    "evangelism_events_wiki_notes": ("_platform",  0),
}

PAGE_TITLES: dict[str, str] = {
    "inicio":          "Inicio",
    "nosotros":        "Nosotros",
    "eventos":         "Eventos",
    "predicas":        "Prédicas",
    "cursos":          "Cursos",
    "sedes":           "Sedes",
    "conocer-a-jesus": "Conocer a Jesús",
    "testimonios":     "Testimonios",
    "privacidad":      "Privacidad",
    "_global":         "Global (nav / shared)",
    "_platform":       "Platform (internal)",
}


def run():
    db = SessionLocal()
    try:
        # ── 1. cms_sites ───────────────────────────────────────────
        site = db.query(models.CmsSite).filter_by(site_key="faro").first()
        if not site:
            site = models.CmsSite(
                site_key="faro",
                name="FARO",
                base_path="/",
                is_active=True,
            )
            db.add(site)
            db.commit()
            db.refresh(site)
            print(f"✓ cms_sites: created 'faro' (id={site.id})")
        else:
            print(f"  cms_sites: 'faro' already exists (id={site.id})")

        # ── 2. cms_pages ───────────────────────────────────────────
        page_objs: dict[str, models.CmsPage] = {}
        slugs = set(v[0] for v in SECTION_MAP.values())
        for slug in sorted(slugs):
            existing = (
                db.query(models.CmsPage)
                .filter_by(site_id=site.id, slug=slug)
                .first()
            )
            if existing:
                page_objs[slug] = existing
                print(f"  cms_pages: '{slug}' already exists (id={existing.id})")
            else:
                page = models.CmsPage(
                    site_id=site.id,
                    slug=slug,
                    title=PAGE_TITLES.get(slug, slug),
                    status="published",
                    seo_json={},
                )
                db.add(page)
                db.commit()
                db.refresh(page)
                page_objs[slug] = page
                print(f"✓ cms_pages: created '{slug}' (id={page.id})")

        # ── 3. cms_sections ────────────────────────────────────────
        page_contents = {
            r.page_key: r
            for r in db.query(models.PageContent).all()
        }

        for section_key, (slug, sort_order) in SECTION_MAP.items():
            page = page_objs[slug]
            pc = page_contents.get(section_key)
            if pc:
                try:
                    props = json.loads(pc.content) if pc.content else {}
                except (json.JSONDecodeError, TypeError):
                    props = {"content": pc.content}
                title = pc.title
            else:
                props = {}
                title = section_key.replace("_", " ").title()

            section_type = "hero" if section_key.endswith("_hero") else "feed"

            existing = (
                db.query(models.CmsSection)
                .filter_by(page_id=page.id, section_key=section_key)
                .first()
            )
            if existing:
                existing.props_json = props
                existing.type = section_type
                existing.sort_order = sort_order
                db.add(existing)
                print(f"✓ cms_sections: updated existing '{section_key}'")
            else:
                section = models.CmsSection(
                    page_id=page.id,
                    section_key=section_key,
                    type=section_type,
                    props_json=props,
                    sort_order=sort_order,
                    is_visible=True,
                    status="active",
                )
                db.add(section)
                print(f"✓ cms_sections: created '{section_key}' → page '{slug}'")
            db.commit()

        print("\n✅ Migration complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()

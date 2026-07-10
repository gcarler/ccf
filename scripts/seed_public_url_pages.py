#!/usr/bin/env python3
"""Create Spanish URL-slug CMS pages that mirror the English CMS pages.

These pages power the dynamic ``[...slug]`` route (PublicSectionRenderer)
with standard section types, while the dedicated page components continue to
consume the English-slug pages with their richer section keys.
"""
from __future__ import annotations

import json
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import backend.models as models  # noqa: E402
from backend.core.config import get_settings  # noqa: E402

try:
    from backend.database import SessionLocal  # noqa: E402
except Exception:
    from backend.core.database import SessionLocal  # noqa: E402

# Mapping from Spanish URL slug -> English CMS page slug and public title.
SPANISH_PAGES: dict[str, tuple[str, str]] = {
    "nosotros": ("about", "Quiénes Somos"),
    "pastores": ("pastors", "Liderazgo Pastoral"),
    "eventos": ("events", "Eventos"),
    "predicas": ("sermons", "Prédicas"),
    "cursos": ("courses", "Cursos"),
    "sedes": ("locations", "Sedes"),
    "testimonios": ("testimonials", "Testimonios"),
    "conocer-a-jesus": ("discover", "Conocer a Jesús"),
    "bienvenida": ("welcome", "Bienvenida"),
    "privacidad": ("privacy", "Política de Privacidad"),
    "inicio": ("home", "Inicio"),
}


def _hero_props_from_english(en_props: dict[str, Any]) -> dict[str, Any]:
    """Build a standard hero section from the English page hero data."""
    title = (
        en_props.get("title")
        or f"{en_props.get('title_lead', '')} {en_props.get('title_accent', '')}".strip()
        or "Bienvenidos"
    )
    return {
        "title": title,
        "body": en_props.get("description", ""),
        "cta_label": en_props.get("cta") or en_props.get("primary_cta", ""),
        "cta_href": "/",
        "image_url": en_props.get("bg_image", ""),
        "image_alt": title,
    }


def _extract_parsed(props: Any) -> dict[str, Any]:
    """Return the parsed dict if the section stores JSON in 'parsed' or 'content'."""
    if isinstance(props, dict):
        if isinstance(props.get("parsed"), dict):
            return props["parsed"]
        if isinstance(props.get("content"), str):
            try:
                return json.loads(props["content"])
            except json.JSONDecodeError:
                return {}
        return props
    return {}


def _normalize_props(section_type: str, props: Any) -> dict[str, Any]:
    """Convert rich/feed props into the shape expected by PublicSectionRenderer."""
    data = _extract_parsed(props) if isinstance(props, dict) else {}
    if not data and isinstance(props, dict):
        data = props

    if section_type == "newsletter":
        return {
            "title": data.get("title", "Mantente conectado"),
            "body": data.get("description", ""),
            "cta_label": data.get("cta_text", "Suscribirse"),
        }
    if section_type == "cards":
        items = []
        if isinstance(data.get("highlights"), list):
            items = data["highlights"]
        elif isinstance(data.get("cards"), list):
            items = data["cards"]
        return {
            "title": data.get("title", ""),
            "body": data.get("description", ""),
            "items": items,
        }
    if section_type == "contact_form":
        return {
            "title": data.get("contact_title", "Hablemos"),
            "body": data.get("contact_description", ""),
        }
    if section_type == "policy_document":
        sections = data.get("sections") or []
        intro = data.get("summary") or data.get("intro", "")
        return {
            "title": data.get("title", "Política de Privacidad"),
            "last_update": data.get("last_update", ""),
            "intro": intro,
            "sections": sections,
        }
    if section_type in ("rich_text", "team", "events_calendar", "course_grid", "locations_list", "testimonials_masonry"):
        # Most renderer components accept these common keys.
        return data if isinstance(data, dict) else {}
    return data if isinstance(data, dict) else {}


def _snapshot(page: models.CmsPage, sections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": "published",
            "seo_json": page.seo_json or {},
            "locale": page.locale,
        },
        "sections": [
            {
                "section_key": s["key"],
                "type": s["type"],
                "props_json": s["props"],
                "sort_order": s["sort"],
                "is_visible": True,
                "status": "active",
            }
            for s in sections
        ],
    }


def main() -> int:
    db = SessionLocal()
    try:
        site = db.query(models.CmsSite).filter(models.CmsSite.is_active.is_(True)).first()
        if site is None:
            site = db.query(models.CmsSite).filter_by(site_key="ccf").first()
        if site is None:
            raise RuntimeError("No active CmsSite found")

        created_pages = 0
        published = 0

        for es_slug, (en_slug, title) in SPANISH_PAGES.items():
            en_page = (
                db.query(models.CmsPage)
                .filter_by(site_id=site.id, slug=en_slug)
                .first()
            )
            if en_page is None:
                print(f"Skip {es_slug}: English page {en_slug} not found")
                continue

            es_page = (
                db.query(models.CmsPage)
                .filter_by(site_id=site.id, slug=es_slug)
                .first()
            )
            if es_page is None:
                es_page = models.CmsPage(
                    site_id=site.id,
                    slug=es_slug,
                    title=title,
                    status="draft",
                    seo_json={},
                    locale="es",
                )
                db.add(es_page)
                db.commit()
                db.refresh(es_page)
                created_pages += 1
                print(f"Created page: {es_slug}")
            else:
                print(f"Updating page: {es_slug}")

            # Collect source sections from the English page.
            en_sections = (
                db.query(models.CmsSection)
                .filter_by(page_id=en_page.id)
                .order_by(models.CmsSection.sort_order)
                .all()
            )

            new_sections: list[dict[str, Any]] = []
            for idx, sec in enumerate(en_sections):
                props = deepcopy(sec.props_json or {})
                section_type = sec.type

                # Richer section keys used by dedicated components become
                # standard types for the dynamic renderer.
                if sec.section_key == "hero":
                    section_type = "hero"
                    props = _hero_props_from_english(props)
                elif sec.section_key == "about":
                    section_type = "rich_text"
                elif sec.section_key == "pastors":
                    section_type = "team"
                    if "pastors" in props:
                        props = {"items": props["pastors"]}
                elif sec.section_key == "events":
                    section_type = "events_calendar"
                    if "parsed" in props:
                        props = {"items": props["parsed"]}
                elif sec.section_key == "feed":
                    # Map generic feeds to a reasonable public renderer type.
                    if en_slug in ("courses",):
                        section_type = "course_grid"
                    elif en_slug in ("testimonials",):
                        section_type = "testimonials_masonry"
                    elif en_slug in ("locations",):
                        section_type = "locations_list"
                    elif en_slug in ("welcome",):
                        section_type = "cards"
                    elif en_slug in ("privacy",):
                        section_type = "policy_document"
                    elif en_slug == "boletin":
                        section_type = "newsletter"
                    elif en_slug == "discover":
                        section_type = "contact_form"
                    else:
                        section_type = "rich_text"
                elif sec.section_key == "welcome":
                    section_type = "cards"
                elif sec.section_key == "privacy":
                    section_type = "policy_document"

                # Normalize props to the shape expected by the renderer.
                props = _normalize_props(section_type, props)

                new_sections.append(
                    {
                        "key": sec.section_key,
                        "type": section_type,
                        "props": props,
                        "sort": idx,
                    }
                )

            # Remove old sections and insert new ones.
            db.query(models.CmsSection).filter_by(page_id=es_page.id).delete()
            db.commit()

            for spec in new_sections:
                section = models.CmsSection(
                    page_id=es_page.id,
                    section_key=spec["key"],
                    type=spec["type"],
                    props_json=spec["props"],
                    sort_order=spec["sort"],
                    is_visible=True,
                    status="active",
                )
                db.add(section)
            db.commit()

            # Publish a new version.
            max_version = (
                db.query(models.CmsPageVersion)
                .filter_by(page_id=es_page.id)
                .order_by(models.CmsPageVersion.version_number.desc())
                .first()
            )
            next_version = (max_version.version_number + 1) if max_version else 1

            version = models.CmsPageVersion(
                page_id=es_page.id,
                version_number=next_version,
                snapshot_json=_snapshot(es_page, new_sections),
                notes="Seed Spanish URL-slug page",
            )
            db.add(version)
            db.commit()
            db.refresh(version)

            es_page.published_version_id = version.id
            es_page.status = "published"
            db.add(es_page)
            db.commit()
            published += 1
            print(f"  → published version {next_version}")

        print(f"\nDone: {created_pages} pages created, {published} pages published")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

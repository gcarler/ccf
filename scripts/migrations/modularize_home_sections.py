#!/usr/bin/env python3
"""Migration: Decouple monolithic 'feed' section on CCF Home page into atomic sections.

Transforms:
  - hero: sort_order=0, type='hero' (preserved)
  - feed: converted in-place to 'welcome' (sort_order=1, type='feed')
  - activities: new row (sort_order=2, type='events_calendar')
  - newsletter: new row (sort_order=3, type='newsletter')
  - discover_cta: sort_order=4, type='cta_block' (preserved)

Guarantees:
  - Atomic transaction (db.commit / db.rollback)
  - Idempotent execution (safe to rerun; exits cleanly if already modularized)
  - Zero data loss (preserves custom editor props, provides dual normalized/prefixed keys)
  - Synchronous Redis cache invalidation
  - Snapshot republishing via republish_home_cms_snapshot.py

Usage:
    /root/ccf/venv/bin/python scripts/migrations/modularize_home_sections.py
    /root/ccf/venv/bin/python scripts/migrations/modularize_home_sections.py --dry-run
    /root/ccf/venv/bin/python scripts/migrations/modularize_home_sections.py ccf home
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

# Locate project root and scripts directories
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

import backend.models  # noqa: F401  # registers all models
import backend.models_cms as m
from backend.core.cache_v2 import invalidate_cached_public, invalidate_cached_public_pattern
from backend.core.database import SessionLocal
from backend.crud.cms.pages import _invalidate_public_page_sections_cache
from backend.models_shared import _utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("modularize_home_sections")


def extract_section_props(feed_props: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Extract atomic props for welcome, activities, and newsletter from the monolithic feed section."""
    # 1. Welcome (Bento grid) props
    welcome_props: dict[str, Any] = {}
    for k, v in feed_props.items():
        if not k.startswith("activities_") and not k.startswith("newsletter_"):
            welcome_props[k] = v
    welcome_props.setdefault("eyebrow", "Nuestra esencia")
    welcome_props.setdefault("section_title", "Bienvenidos a Casa")
    welcome_props.setdefault("title", welcome_props.get("section_title", "Bienvenidos a Casa"))
    welcome_props.setdefault("section_description", "Rutas públicas para conocer la comunidad, profundizar en la fe y encontrar dónde dar el siguiente paso.")
    welcome_props.setdefault("description", welcome_props.get("section_description", ""))
    welcome_props.setdefault("scroll_indicator", "Descubrir")

    # 2. Activities props (dual normalized + prefixed keys for backward compatibility)
    act_eyebrow = feed_props.get("activities_eyebrow", "Actualidad")
    act_title = feed_props.get("activities_title", "Actividades Recientes")
    act_view_all = feed_props.get("activities_view_all", "Ver calendario →")
    act_view_all_href = feed_props.get("activities_view_all_href", "/eventos")
    act_empty = feed_props.get("activities_empty", "Próximamente encontrarás aquí nuestras actividades. Mientras tanto, síguenos en redes sociales.")

    activities_props: dict[str, Any] = {
        "eyebrow": act_eyebrow,
        "activities_eyebrow": act_eyebrow,
        "title": act_title,
        "activities_title": act_title,
        "view_all": act_view_all,
        "activities_view_all": act_view_all,
        "view_all_href": act_view_all_href,
        "activities_view_all_href": act_view_all_href,
        "empty": act_empty,
        "activities_empty": act_empty,
    }
    for k, v in feed_props.items():
        if k.startswith("activities_") and k not in activities_props:
            activities_props[k] = v

    # 3. Newsletter props (dual normalized + prefixed keys for backward compatibility)
    nl_eyebrow = feed_props.get("newsletter_eyebrow", "Boletín semanal")
    nl_title = feed_props.get("newsletter_title", "¿Quieres recibir nuestras novedades?")
    nl_desc = feed_props.get("newsletter_description", "Meditaciones semanales, eventos exclusivos y más.\nDirecto a tu correo.")
    nl_placeholder = feed_props.get("newsletter_placeholder", "Tu correo electrónico")
    nl_submit = feed_props.get("newsletter_submit", "Suscribirme")
    nl_sending = feed_props.get("newsletter_sending_label", "Enviando...")
    nl_succ_title = feed_props.get("newsletter_success_title", "¡Gracias por suscribirte!")
    nl_succ_desc = feed_props.get("newsletter_success_desc", "Recibirás meditaciones y novedades semanales.")
    nl_succ_toast = feed_props.get("newsletter_success_toast", "¡Suscrito al boletín de El Faro!")
    nl_err_toast = feed_props.get("newsletter_error_toast", "No se pudo suscribir. Intenta de nuevo.")

    newsletter_props: dict[str, Any] = {
        "eyebrow": nl_eyebrow,
        "newsletter_eyebrow": nl_eyebrow,
        "title": nl_title,
        "newsletter_title": nl_title,
        "description": nl_desc,
        "newsletter_description": nl_desc,
        "placeholder": nl_placeholder,
        "newsletter_placeholder": nl_placeholder,
        "submit": nl_submit,
        "newsletter_submit": nl_submit,
        "sending_label": nl_sending,
        "newsletter_sending_label": nl_sending,
        "success_title": nl_succ_title,
        "newsletter_success_title": nl_succ_title,
        "success_desc": nl_succ_desc,
        "newsletter_success_desc": nl_succ_desc,
        "success_toast": nl_succ_toast,
        "newsletter_success_toast": nl_succ_toast,
        "error_toast": nl_err_toast,
        "newsletter_error_toast": nl_err_toast,
    }
    for k, v in feed_props.items():
        if k.startswith("newsletter_") and k not in newsletter_props:
            newsletter_props[k] = v

    return welcome_props, activities_props, newsletter_props


def modularize_home_sections(site_key: str = "ccf", slug: str = "home", *, dry_run: bool = False) -> bool:
    """Perform atomic and idempotent modularization of home page sections."""
    db = SessionLocal()
    try:
        site = db.query(m.CmsSite).filter(m.CmsSite.site_key == site_key.strip().lower()).first()
        if not site:
            logger.error("CMS site %r not found", site_key)
            return False

        page = db.query(m.CmsPage).filter(
            m.CmsPage.site_id == site.id,
            m.CmsPage.slug == slug,
            m.CmsPage.deleted_at.is_(None),
        ).first()
        if not page:
            logger.error("CmsPage slug=%r not found for site %r", slug, site_key)
            return False

        sections = db.query(m.CmsSection).filter(
            m.CmsSection.page_id == page.id,
            m.CmsSection.deleted_at.is_(None),
        ).all()

        by_key = {s.section_key: s for s in sections}

        has_welcome = "welcome" in by_key
        has_activities = "activities" in by_key
        has_newsletter = "newsletter" in by_key
        has_feed = "feed" in by_key

        # Idempotency check: Already modularized
        if has_welcome and has_activities and has_newsletter:
            changed = False
            # Clean up obsolete feed if still active alongside welcome
            if has_feed:
                feed_sec = by_key["feed"]
                logger.info("Soft-deleting redundant feed section (id=%s)", feed_sec.id)
                feed_sec.deleted_at = _utcnow()
                changed = True

            expected_orders = {
                "hero": 0,
                "welcome": 1,
                "activities": 2,
                "newsletter": 3,
                "discover_cta": 4,
            }
            for k, order in expected_orders.items():
                sec = by_key.get(k)
                if sec and sec.sort_order != order:
                    logger.info("Normalizing sort_order for %s from %s to %s", k, sec.sort_order, order)
                    sec.sort_order = order
                    changed = True

            if changed:
                if dry_run:
                    logger.info("[DRY RUN] Would commit normalized sort orders / cleanup")
                    db.rollback()
                else:
                    db.commit()
                    _invalidate_public_page_sections_cache(db, page.id)
                    invalidate_cached_public("public_page", site_key=site_key, slug=slug)
                    from republish_home_cms_snapshot import republish
                    republish(site_key, slug, actor="modularize_home_sections.py:normalize")
            logger.info("Page %r is already fully modularized into 5 atomic sections. Idempotent no-op.", slug)
            return True

        feed_section = by_key.get("feed")
        feed_props = feed_section.props_json or {} if feed_section else {}
        welcome_props, activities_props, newsletter_props = extract_section_props(feed_props)

        # Mutate feed -> welcome in place, or insert welcome
        welcome_sec = by_key.get("welcome")
        if not welcome_sec and feed_section:
            logger.info("Converting feed section (id=%s) to 'welcome' (sort_order=1)", feed_section.id)
            feed_section.section_key = "welcome"
            feed_section.type = "feed"
            feed_section.sort_order = 1
            feed_section.props_json = welcome_props
            feed_section.updated_at = _utcnow()
            welcome_sec = feed_section
        elif not welcome_sec:
            logger.info("Inserting new 'welcome' section (sort_order=1)")
            welcome_sec = m.CmsSection(
                id=uuid.uuid4(),
                page_id=page.id,
                section_key="welcome",
                type="feed",
                props_json=welcome_props,
                sort_order=1,
                is_visible=True,
                status="published",
                locale="es",
                is_global=False,
            )
            db.add(welcome_sec)
        else:
            welcome_sec.sort_order = 1

        # Soft-delete redundant feed if distinct from welcome
        if feed_section and welcome_sec and feed_section.id != welcome_sec.id:
            logger.info("Soft-deleting redundant feed section (id=%s)", feed_section.id)
            feed_section.deleted_at = _utcnow()

        # Activities section
        act_sec = by_key.get("activities")
        if not act_sec:
            logger.info("Inserting new 'activities' section (sort_order=2)")
            act_sec = m.CmsSection(
                id=uuid.uuid4(),
                page_id=page.id,
                section_key="activities",
                type="events_calendar",
                props_json=activities_props,
                sort_order=2,
                is_visible=True,
                status="published",
                locale="es",
                is_global=False,
            )
            db.add(act_sec)
        else:
            act_sec.sort_order = 2

        # Newsletter section
        nl_sec = by_key.get("newsletter")
        if not nl_sec:
            logger.info("Inserting new 'newsletter' section (sort_order=3)")
            nl_sec = m.CmsSection(
                id=uuid.uuid4(),
                page_id=page.id,
                section_key="newsletter",
                type="newsletter",
                props_json=newsletter_props,
                sort_order=3,
                is_visible=True,
                status="published",
                locale="es",
                is_global=False,
            )
            db.add(nl_sec)
        else:
            nl_sec.sort_order = 3

        # Hero (sort_order = 0)
        hero_sec = by_key.get("hero")
        if hero_sec:
            hero_sec.sort_order = 0
            logger.info("Ensured 'hero' section (id=%s) sort_order=0", hero_sec.id)

        # Discover CTA (sort_order = 4)
        cta_sec = by_key.get("discover_cta")
        if cta_sec:
            cta_sec.sort_order = 4
            logger.info("Ensured 'discover_cta' section (id=%s) sort_order=4", cta_sec.id)

        if dry_run:
            logger.info("[DRY RUN] Transaction rolled back. Zero database changes saved.")
            db.rollback()
            return True

        # Commit transaction atomically
        db.commit()
        logger.info("Modularization transaction committed successfully.")

        # Cache invalidation
        _invalidate_public_page_sections_cache(db, page.id)
        invalidate_cached_public("public_page", site_key=site_key, slug=slug)
        invalidate_cached_public_pattern("public_pages_list")
        logger.info("Redis cache invalidated for site_key=%r, slug=%r", site_key, slug)

        # Snapshot republish
        from republish_home_cms_snapshot import republish
        v_num = republish(site_key, slug, actor="scripts/migrations/modularize_home_sections.py")
        logger.info("Published fresh CmsPageVersion snapshot v#%s", v_num)

        return True

    except Exception as exc:
        db.rollback()
        logger.exception("Error during modularization transaction; rolled back: %s", exc)
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_key", nargs="?", default="ccf", help="CMS site_key (default: ccf).")
    parser.add_argument("slug", nargs="?", default="home", help="CmsPage slug (default: home).")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without committing.")
    args = parser.parse_args()

    success = modularize_home_sections(args.site_key, args.slug, dry_run=args.dry_run)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

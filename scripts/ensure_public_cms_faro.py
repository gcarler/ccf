"""Re-seed the public ``faro`` site so the ``/faro/*`` routes resolve.

Operational script (REGLAS.md §11). Idempotent — runs ``check-and-skip``:

* If a CmsPage already has a ``published_version_id`` the editor's
  content is left intact (no section rewrite, no new version).
* If a CmsTheme with the canonical name exists, only its
  ``tokens_json``/``is_active``/``status`` are reconciled.
* If a CmsMenu already has items, the items are NOT rebuilt.

What it creates when missing:

* ``CmsSite(site_key='faro')`` — Axioma 3 exception, ``sede_id=None``
  (cross-sede editorial by design; see
  ``backend/api/_cms_helpers/_shared.py``).
* ``CmsTheme(name='Tema institucional Faro')`` active.
* ``CmsMenu('main')`` with two seed items (Inicio, Boletín).
* ``CmsPage(slug='home')`` populated with a ``hero`` section (the new
  8-key shape consumed by ``PublicHeroWithSlides``: ``eyebrow``,
  ``title_lead``, ``title_accent``, ``title_tail``, ``description``,
  ``primary_cta``, ``secondary_cta``, ``bg_image``) and a ``feed``
  section with a minimal ``parsed`` payload.
* Stub ``CmsPage`` rows for the other public slugs (no sections, just
  title + status='published' + v#1 snapshot) so the catch-all route
  ``(public)/[...slug]/page.tsx`` returns 200 instead of producing
  browser 404 noise for legitimate URLs like ``/faro/boletin``.

Run::

    python3 ccf/scripts/ensure_public_cms_faro.py
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import func

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import backend.models  # noqa: E402  — registers every model
import backend.models_cms as m  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402


# ── Canonical site_key for this script (single-site operational) ────────────
SITE_KEY = "faro"
SITE_NAME = "Faro"
# CmsSite.base_path is UNIQUE NOT NULL (see models_cms.py line 35). The ccf
# site already owns ``/``, so the faro site takes a non-conflicting path
# prefix. Routing is site_key-driven (the public handler looks up by
# site_key, not base_path), so this value is metadata + serves as a
# canonical URL prefix for the tenant.
SITE_BASE_PATH = "/faro"
THEME_NAME = "Tema institucional Faro"
MENU_KEY = "main"
HOME_SLUG = "home"

THEME_TOKENS: dict[str, str] = {
    "--site-background": "#f6f8ff",
    "--site-on-background": "#0d1730",
    "--site-surface": "#ffffff",
    "--site-surface-container": "#ffffff",
    "--site-surface-container-low": "#eef2ff",
    "--site-surface-container-high": "#e3e9ff",
    "--site-surface-container-highest": "#d3deff",
    "--site-on-surface": "#0d1730",
    "--site-on-surface-variant": "#45506b",
    "--site-primary": "#3a5cd4",
    "--site-on-primary": "#ffffff",
    "--site-primary-container": "#dde6ff",
    "--site-on-primary-container": "#001046",
    "--site-secondary": "#e0a931",
    "--site-cta-gradient": "linear-gradient(135deg,#3a5cd4,#1a3ab8)",
    "--site-outline-variant": "rgba(0,0,0,0.1)",
}

# Minimal-but-realistic menu items so the public header doesn't look
# broken. The full nav surface is owned by the editor; we just give the
# menu enough entries to render a recognizable top bar. Editors can
# extend later via the CMS admin. The ccf site loads a fuller nav from
# the legacy ``ccf_nav_items`` page_contents row (see
# ``ensure_public_cms_pastors.py``); we keep this self-contained so the
# script doesn't depend on legacy bootstrapping being present.
SEED_MENU_ITEMS: list[dict[str, Any]] = [
    {"label": "Inicio", "href": "/", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 0, "meta_json": {}},
    {"label": "Nosotros", "href": "/nosotros", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 1, "meta_json": {}},
    {"label": "Eventos", "href": "/eventos", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 2, "meta_json": {}},
    {"label": "Prédicas", "href": "/predicas", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 3, "meta_json": {}},
    {"label": "Cursos", "href": "/cursos", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 4, "meta_json": {}},
    {"label": "Sedes", "href": "/sedes", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 5, "meta_json": {}},
    {"label": "Conocer a Jesús", "href": "/conocer-a-jesus", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 6, "meta_json": {}},
    {"label": "Boletín", "href": "/boletin", "target": "_self", "is_external": False, "visibility": "public", "sort_order": 7, "meta_json": {}},
]

# Hero in the new 8-key shape consumed by ``PublicHeroWithSlides``. Kept
# generic on purpose — the editor replaces this with the production copy.
HERO_PROPS: dict[str, Any] = {
    "eyebrow": "UNA COMUNIDAD QUE ILUMINA",
    "title_lead": "Faro:",
    "title_accent": "Tu Guía,",
    "title_tail": "Su Luz",
    "description": (
        "Navegando juntos hacia la verdad. Un espacio de encuentro, fe y "
        "transformación en el corazón de nuestra comunidad."
    ),
    "primary_cta": "Empezar mi viaje",
    "secondary_cta": "Ver Prédicas",
    "bg_image": "/api/static/cms/home_banner/a7e9a238a55d464cbf0cb6ff88f29671.webp",
}

FEED_PROPS: dict[str, Any] = {
    "parsed": {
        "eyebrow": "Nuestra esencia",
        "section_title": "Bienvenidos a Casa",
        "section_description": (
            "Rutas públicas para conocer la comunidad, profundizar en la fe y "
            "encontrar dónde dar el siguiente paso."
        ),
        "featured_card": {
            "title": "Conocer a Jesús",
            "desc": (
                "Descubre la base de nuestra fe a través de un viaje personal y "
                "transformador. En Faro, te acompañamos en cada paso."
            ),
            "href": "/conocer-a-jesus",
            "cta": "Empezar el camino",
            "img": "/api/static/cms/home_banner/a7e9a238a55d464cbf0cb6ff88f29671.webp",
            "alt": "Equipo pastoral de Faro",
        },
        "cards": [],
        "newsletter_title": "¿Quieres recibir nuestras novedades?",
        "newsletter_description": "Meditaciones semanales, eventos exclusivos y más.\nDirecto a tu correo.",
        "newsletter_placeholder": "Tu correo electrónico",
        "newsletter_submit": "Suscribirme",
        "newsletter_success_title": "¡Gracias por suscribirte!",
        "newsletter_success_desc": "Recibirás meditaciones y novedades semanales.",
    }
}

# Stub slugs created (without sections) so the catch-all route can serve a
# 200 response. Each gets a published empty v#1 snapshot.
# NOTE: we use ``pastors`` (English) so that
# ``ensure_public_cms_pastors.py``'s check-and-skip finds the page already
# published and doesn't try to recreate it under a different slug.
STUB_SLUGS: dict[str, str] = {
    "nosotros": "Quiénes Somos",
    "eventos": "Eventos",
    "predicas": "Prédicas",
    "cursos": "Cursos",
    "sedes": "Sedes",
    "testimonios": "Testimonios",
    "conocer-a-jesus": "Conocer a Jesús",
    "boletin": "Boletín",
    "privacidad": "Política de Privacidad",
    "bienvenida": "Bienvenida",
    "pastors": "Pastores",
}


# ── Helpers ────────────────────────────────────────────────────────────────


def _ensure_site(db) -> tuple[m.CmsSite, bool]:
    """Axioma 3 — CmsSite is the documented cross-sede exception
    (see ``backend/api/_cms_helpers/_shared.py``); do NOT add ``sede_id``.
    """
    site = (
        db.query(m.CmsSite)
        .filter(m.CmsSite.site_key == SITE_KEY)
        .first()
    )
    if site is not None:
        if not site.is_active:
            site.is_active = True
        return site, False
    site = m.CmsSite(
        site_key=SITE_KEY,
        name=SITE_NAME,
        base_path=SITE_BASE_PATH,
        is_active=True,
    )
    db.add(site)
    db.flush()
    return site, True


def _ensure_theme(db, site: m.CmsSite) -> tuple[bool, bool]:
    created = False
    changed = False
    theme = (
        db.query(m.CmsTheme)
        .filter(m.CmsTheme.site_id == site.id, m.CmsTheme.name == THEME_NAME)
        .first()
    )
    if theme is None:
        theme = m.CmsTheme(
            site_id=site.id,
            name=THEME_NAME,
            tokens_json=THEME_TOKENS,
            is_active=True,
            status="active",
        )
        db.add(theme)
        db.flush()
        # Deactivate any other active theme for this site.
        (
            db.query(m.CmsTheme)
            .filter(m.CmsTheme.site_id == site.id, m.CmsTheme.id != theme.id)
            .update({"is_active": False})
        )
        return True, True
    if theme.tokens_json != THEME_TOKENS:
        theme.tokens_json = THEME_TOKENS
        changed = True
    if not theme.is_active or theme.status != "active":
        (
            db.query(m.CmsTheme)
            .filter(m.CmsTheme.site_id == site.id)
            .update({"is_active": False})
        )
        theme.is_active = True
        theme.status = "active"
        changed = True
    return created, changed


def _ensure_menu(db, site: m.CmsSite) -> tuple[bool, bool]:
    """Idempotent. If the menu already has items, do not rebuild them."""
    menu = (
        db.query(m.CmsMenu)
        .filter(m.CmsMenu.site_id == site.id, m.CmsMenu.menu_key == MENU_KEY)
        .first()
    )
    created = False
    changed = False
    if menu is None:
        menu = m.CmsMenu(site_id=site.id, menu_key=MENU_KEY, name="Menú principal", is_active=True)
        db.add(menu)
        db.flush()
        created = True
        changed = True
    elif menu.name != "Menú principal" or not menu.is_active:
        menu.name = "Menú principal"
        menu.is_active = True
        changed = True

    items_count = (
        db.query(func.count(m.CmsMenuItem.id))
        .filter(m.CmsMenuItem.menu_id == menu.id)
        .scalar()
        or 0
    )
    if items_count == 0:
        for item in SEED_MENU_ITEMS:
            db.add(m.CmsMenuItem(menu_id=menu.id, **item))
        changed = True
    return created, changed


def _section_payload(section_key: str, section_type: str, props: dict[str, Any], sort_order: int) -> dict[str, Any]:
    return {
        "section_key": section_key,
        "type": section_type,
        "props_json": props,
        "sort_order": sort_order,
        "is_visible": True,
        "status": "active",
        "locale": "es",
    }


def _publish_version(db, site: m.CmsSite, page: m.CmsPage, sections: list[dict[str, Any]], notes: str) -> int:
    snapshot = {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": "published",
            "seo_json": page.seo_json or {},
        },
        "sections": sections,
    }
    max_v = (
        db.query(func.max(m.CmsPageVersion.version_number))
        .filter(m.CmsPageVersion.page_id == page.id)
        .scalar()
        or 0
    )
    next_v = int(max_v) + 1
    version = m.CmsPageVersion(
        id=uuid.uuid4(),
        page_id=page.id,
        version_number=next_v,
        snapshot_json=snapshot,
        notes=notes,
    )
    db.add(version)
    db.flush()
    page.status = "published"
    page.published_version_id = version.id
    db.add(
        m.CmsPublishLog(
            id=uuid.uuid4(),
            site_id=site.id,
            page_id=page.id,
            entity_type="page",
            entity_id=str(page.id),
            action="publish",
            from_status="draft",
            to_status="published",
            metadata_json={"source": "ensure_public_cms_faro", "version_number": next_v},
        )
    )
    return next_v


def _ensure_home(db, site: m.CmsSite) -> tuple[bool, str]:
    """Ensure ``CmsPage(slug='home')`` exists with hero+feed sections.
    If the page already has a published version, do NOT touch it.
    """
    page = (
        db.query(m.CmsPage)
        .filter(m.CmsPage.site_id == site.id, m.CmsPage.slug == HOME_SLUG)
        .first()
    )
    if page is not None and page.published_version_id is not None:
        return False, "preserved (editor has published_version)"

    if page is None:
        page = m.CmsPage(
            site_id=site.id,
            slug=HOME_SLUG,
            title="Inicio",
            status="draft",
            seo_json={},
        )
        db.add(page)
        db.flush()

    # Wipe any sections that might exist (the page is new or unpublished).
    db.query(m.CmsSection).filter(m.CmsSection.page_id == page.id).delete(synchronize_session=False)
    sections = [
        _section_payload("hero", "hero", HERO_PROPS, 0),
        _section_payload("feed", "feed", FEED_PROPS, 1),
    ]
    for sec in sections:
        db.add(m.CmsSection(page_id=page.id, **sec))
    db.flush()
    next_v = _publish_version(
        db, site, page, sections,
        notes="Re-seeded /faro home with new-shape hero (8 keys)",
    )
    return True, f"created/seeded v#{next_v} with hero+feed"


def _ensure_stub(db, site: m.CmsSite, slug: str, title: str) -> tuple[bool, str]:
    page = (
        db.query(m.CmsPage)
        .filter(m.CmsPage.site_id == site.id, m.CmsPage.slug == slug)
        .first()
    )
    if page is not None and page.published_version_id is not None:
        return False, "preserved (editor has published_version)"
    if page is None:
        page = m.CmsPage(
            site_id=site.id,
            slug=slug,
            title=title,
            status="draft",
            seo_json={},
        )
        db.add(page)
        db.flush()
    next_v = _publish_version(
        db, site, page, [],
        notes=f"Re-seeded stub /{slug} for /faro/* catch-all",
    )
    return True, f"created/seeded v#{next_v}"


def main() -> int:
    with SessionLocal() as db:
        site, site_created = _ensure_site(db)
        theme_created, theme_changed = _ensure_theme(db, site)
        menu_created, menu_changed = _ensure_menu(db, site)
        home_created, home_status = _ensure_home(db, site)

        stub_created = 0
        stub_preserved = 0
        for slug, title in STUB_SLUGS.items():
            created, status = _ensure_stub(db, site, slug, title)
            if created:
                stub_created += 1
            else:
                stub_preserved += 1

        db.commit()

        print(f"=== Site: {SITE_KEY!r} ===")
        print(f"Site:    {'created' if site_created else 'exists'}")
        print(
            f"Theme:   {'created' if theme_created else 'exists'}; "
            f"{'updated/activated' if theme_changed else 'unchanged'}"
        )
        print(
            f"Menu {MENU_KEY}:  {'created' if menu_created else 'exists'}; "
            f"{'updated' if menu_changed else 'unchanged'}"
        )
        print(f"Home:    {home_status}")
        print(
            f"Stubs:   {stub_created} created/seeded, {stub_preserved} preserved"
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())

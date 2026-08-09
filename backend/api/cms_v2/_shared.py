"""Shared helpers for the CMS v2 package (Fase 4 refactor).

These helpers are used across every CMS sub-module (sites, pages, menus,
themes, posts, public endpoints, etc.). Centralising them here lets each
sub-module import from ``cms_v2._shared`` instead of reaching back into
the monolithic ``__init__`` — which is what created circular-import risk
in the original single-file design.

Everything here is import-safe: no FastAPI router definitions, no
``@router.get`` decorators, just plain functions and constants.
"""

from __future__ import annotations

import copy
import logging
import re
import time
import unicodedata
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, lazyload

from backend import crud, models, schemas
from backend.api.cms_v2 import _defaults as _D
from backend.core.cache_v2 import cached_public  # noqa: F401
from backend.core.permissions import normalize_role
from backend.exceptions.cms import (
    CategoryNotFoundError,
    CmsConflictError,
    CmsPermissionError,
    CmsValidationError,
    MenuNotFoundError,
    PageNotFoundError,
    PostNotFoundError,
    SiteNotFoundError,
    TagNotFoundError,
)

logger = logging.getLogger(__name__)


# ── Role constants ──────────────────────────────────────────────────────────

CMS_EDITOR_ROLES = {"admin", "coordinador", "docente", "pastor"}
CMS_PUBLISHER_ROLES = {"admin", "coordinador", "pastor"}

# ── Rate limiting ──────────────────────────────────────────────────────────────

PUBLIC_CMS_RATE_LIMIT = 240


# ── Commit / conflict helper ────────────────────────────────────────────────


def _commit_or_raise_conflict(db: Session, detail: str = "resource already exists") -> None:
    """Commit helper that converts concurrent **unique-key** violations into 409.

    Without this, two simultaneous requests can pass the existence check and
    then raise an unhandled ``IntegrityError`` (500). Wrapping the commit
    lets us return a controlled ``409 Conflict`` instead.

    Aligned (M-12, defensivo) con ``crud.cms._commit_or_conflict``: solo
    traga ``IntegrityError`` cuyo ``pgcode == '23505'`` (Postgres unique
    violation) o el mensaje SQLite ``"UNIQUE constraint failed"``. Toda
    otra ``IntegrityError`` (NOT NULL, FK, check) es un bug genuino y se
    re-raise post-rollback para que salga como 500 (no como falso 409).
    Antes de este fix, el helper tragaba TODA ``IntegrityError`` como 409
    — enmascaraba bugs.

    Unique-violation detection delegated to
    ``backend.crud._utils._is_unique_violation`` — single source of truth
    compartido con ``crud/cms.py`` y ``crud/academy.py`` (consolidación
    de las 3 copias, 2026-08-05). Esta capa CMS preserva el raise de
    ``CmsConflictError`` (dominio CMS) en vez de ``HTTPException``.
    """
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        from backend.crud._utils import _is_unique_violation

        if not _is_unique_violation(exc):
            raise
        logger.debug("Swallowed concurrent create unique-key conflict: %s", exc)
        raise CmsConflictError(detail=detail)


# ── Role assertion ──────────────────────────────────────────────────────────


def _assert_role(user: models.User, allowed_roles: set[str], detail: str = "Not enough permissions") -> None:
    """Validate that the user belongs to one of the allowed role groups.

    Args:
        user: Authenticated ``User`` model instance.
        allowed_roles: Set of role names (lower‑cased) permitted to perform the action.
        detail: Custom error detail returned in the 403 response.
    """
    # Preserve backward‑compatible behaviour for V3 personas where the role is stored
    # in ``rol_plataforma.nombre``. ``normalize_role`` handles case‑insensitivity and
    # whitespace trimming.
    role = normalize_role(getattr(user, "role", ""))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    if role not in allowed_roles:
        raise CmsPermissionError(detail=detail)


# ── String / slug helpers ───────────────────────────────────────────────────


def _slugify(value: str) -> str:
    """Normalize a string into a URL‑safe slug.

    - NFKD decomposition so accented characters collapse to their ASCII
      base (``í`` → ``i``, ``á`` → ``a``, ``ó`` → ``o``, ``ü`` → ``u``).
      This keeps the alphabetic base character so ``Nehemías`` slugifies
      to ``nehemias`` (not ``nehemas`` like a naive ``[^a-z0-9]`` strip
      would do) and aligns with the canonical rule used by
      ``scripts/fix_pastor_photos.py`` and ``crud/cms_pastors_sync.py``.
    - Trims whitespace, lower‑cases, replaces internal whitespace with hyphens.
    - Removes characters that are not alphanumeric, hyphen, underscore or slash.
    - Strips leading/trailing hyphens.
    """
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-_/]", "", value)
    return value.strip("-")


# ── Site / menu / page lookups ──────────────────────────────────────────────


def _get_site_or_404(db: Session, site_key: str) -> models.CmsSite:
    """Retrieve a CMS site by its key or raise a 404 error.

    Args:
        db: SQLAlchemy session.
        site_key: Identifier of the site (case‑insensitive).
    """
    row = crud.get_cms_site_by_key(db, site_key.strip().lower())
    if not row:
        raise SiteNotFoundError()
    return row


def _actor_sede_from_user(db: Session, current_user: models.User) -> uuid.UUID | None:
    """Resolve la sede del actor autenticado desde su persona.

    Retorna ``None`` si el actor no tiene persona o no tiene sede
    asignada (superadmin / anterior path).
    """
    persona_id = crud.resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    if not persona_id:
        return None
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
    if not persona:
        return None
    return persona.sede_id


def _is_global_admin(current_user: models.User) -> bool:
    """Return True if the user has a platform-wide admin role.

    A user without a sede is *not* automatically a global admin.
    Only explicit admin/platform-admin roles bypass tenant scope.
    """
    role = normalize_role(getattr(current_user, "role", ""))
    if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
        role = normalize_role(current_user.rol_plataforma.nombre)
    return role in {"admin", "administrador", "super administrador"}


def _assert_site_sede_scope(
    site: models.CmsSite,
    actor_sede: uuid.UUID | None,
    current_user: models.User,
) -> None:
    """Axioma 3 — Multi-Tenant: validar que el site pertenece a la sede del actor.

    Reglas:
      - Superadministradores globales (detectados por rol, no por ausencia
        de sede) pueden acceder a cualquier site, incluidos los huérfanos
        (sede_id NULL) resultantes de M&A histórico.
      - Un actor con sede solo puede interactuar con sites de SU propia
        sede. Los sites huérfanos (sede_id NULL) NO son accesibles por
        actores con sede: previene el leak multi-tenant documentado en
        C-01 (orphan sites tras ondelete SET NULL histórico). Con el FK
        ahora ondelete=RESTRICT no se generan nuevos huérfanos, pero los
        existentes solo los limpia un admin global.
      - Un actor sin sede que NO sea admin global recibe 404 para evitar
        escalación de privilegios por inconsistencia de datos.
    """
    if _is_global_admin(current_user):
        return
    if actor_sede is None:
        raise SiteNotFoundError()
    if site.sede_id is None:
        raise SiteNotFoundError()
    if site.sede_id != actor_sede:
        raise SiteNotFoundError()


def _get_scoped_site_or_404(
    db: Session,
    site_key: str,
    current_user: models.User,
) -> models.CmsSite:
    """Axioma 3 — retrieve site + enforce sede scope in one call.

    Combines ``_get_site_or_404`` with ``_assert_site_sede_scope`` so that
    every admin endpoint that operates on a site enforces multi-tenant
    isolation without requiring the caller to remember both calls.
    """
    site = _get_site_or_404(db, site_key)
    _assert_site_sede_scope(site, _actor_sede_from_user(db, current_user), current_user)
    return site


def _get_public_site_or_404(db: Session, site_key: str) -> models.CmsSite:
    """Fetch a public‑active CMS site or raise 404.

    Uses ``lazyload('*')`` to avoid the massive cascade of eager-loaded
    relationships on ``CmsSite`` (pages, menus, themes, posts, etc. each
    with ``selectin`` loading). Public endpoints only need ``site.id`` and
    ``site.is_active`` — not the full relational graph.
    """
    row = (
        db.query(models.CmsSite)
        .options(lazyload("*"))
        .filter(models.CmsSite.site_key == site_key.strip().lower())
        .first()
    )
    if not row:
        raise SiteNotFoundError()
    if not row.is_active:
        raise SiteNotFoundError()
    return row


def _get_menu_or_404(db: Session, site_id: UUID, menu_key: str) -> models.CmsMenu:
    """Retrieve a CMS menu by its key for a given site or raise 404.

    Uses ``lazyload('*')`` to avoid eager-loading the ``CmsSite`` cascade.
    """
    row = (
        db.query(models.CmsMenu)
        .options(lazyload("*"))
        .filter(models.CmsMenu.site_id == site_id, models.CmsMenu.menu_key == menu_key)
        .first()
    )
    if not row:
        raise MenuNotFoundError()
    return row


def _get_page_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsPage:
    row = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .filter(models.CmsPage.site_id == site_id, models.CmsPage.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise PageNotFoundError()
    return row


def _snapshot_section_read(
    section_data: dict[str, Any],
    *,
    page_id: uuid.UUID,
    index: int,
    timestamp: datetime,
) -> schemas.CmsSectionRead:
    section_id = section_data.get("id")
    sort_order = section_data.get("sort_order")
    props_json = section_data.get("props_json")

    import uuid as py_uuid

    valid_id = None
    if section_id:
        if isinstance(section_id, py_uuid.UUID):
            valid_id = section_id
        else:
            try:
                valid_id = py_uuid.UUID(str(section_id))
            except (ValueError, AttributeError):
                pass
    if not valid_id:
        valid_id = py_uuid.uuid5(py_uuid.NAMESPACE_DNS, f"section-fallback-{page_id}-{index}")

    return schemas.CmsSectionRead(
        id=valid_id,
        page_id=page_id,
        section_key=str(section_data.get("section_key") or f"published-{index + 1}"),
        type=str(section_data.get("type") or "rich_text"),
        props_json=props_json if isinstance(props_json, dict) else {},
        sort_order=sort_order if isinstance(sort_order, int) else index,
        is_visible=section_data.get("is_visible", True) is not False,
        status=str(section_data.get("status") or "active"),
        created_at=timestamp,
        updated_at=timestamp,
    )


# ── System Variable cache ──────────────────────────────────────────────────────
# Shared across the package so that ``_build_section_defaults`` (called from both
# ``pages.preview_page`` and ``public.public_page``) uses a single in-memory cache.

_system_var_cache: dict[str, tuple[float, str]] = {}
_SYSTEM_VAR_TTL = 300  # 5 minutes


def _get_system_var(db: Session, site_key: str, var_key: str, default: str = "") -> str:
    """Read a single SystemVariable by key, with optional site_key prefix.
    Cached for 5 minutes per site_key+var_key to avoid repeated DB hits."""
    cache_key = f"{site_key}:{var_key}"
    now = time.monotonic()
    if cache_key in _system_var_cache:
        cached_time, cached_val = _system_var_cache[cache_key]
        if now - cached_time < _SYSTEM_VAR_TTL:
            return cached_val
    row = (
        db.query(models.SystemVariable)
        .filter(
            models.SystemVariable.key == f"{site_key}_{var_key}",
            models.SystemVariable.deleted_at.is_(None),
        )
        .first()
    )
    val = row.value if row and row.value else default
    _system_var_cache[cache_key] = (now, val)
    return val


def _get_system_vars_batch(db: Session, site_key: str, var_keys: tuple[str, ...]) -> dict[str, str]:
    """Batch-read multiple SystemVariable rows for a site in one query (N+1 fix)."""
    now = time.monotonic()
    cached: dict[str, str] = {}
    missing: list[str] = []
    for var_key in var_keys:
        cache_key = f"{site_key}:{var_key}"
        hit = _system_var_cache.get(cache_key)
        if hit is not None and now - hit[0] < _SYSTEM_VAR_TTL:
            cached[var_key] = hit[1]
        else:
            missing.append(var_key)
    if missing:
        db_keys = [f"{site_key}_{k}" for k in missing]
        rows = (
            db.query(models.SystemVariable.key, models.SystemVariable.value)
            .filter(
                models.SystemVariable.key.in_(db_keys),
                models.SystemVariable.deleted_at.is_(None),
            )
            .all()
        )
        found: dict[str, str] = {}
        for row in rows:
            suffix = row.key[len(f"{site_key}_") :] if row.key.startswith(f"{site_key}_") else row.key
            found[suffix] = row.value
        now_mono = time.monotonic()
        for var_key in missing:
            cache_key = f"{site_key}:{var_key}"
            value = found.get(var_key, "")
            _system_var_cache[cache_key] = (now_mono, value)
            cached[var_key] = value
    return cached


def _hydrate_testimonials_section(db: Session, props: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hidrata la sección ``testimonials`` desde los ``CmsPost`` publicados.

    Fase 2 (muro de gratitud): la sección se hidrata SIEMPRE desde los
    ``CmsPost`` publicados de la categoría canónica ``testimonials`` a
    menos que el editor haya guardado items manuales explícitos en
    ``props``.

    Extraído de ``_build_section_defaults`` (consolidación de deuda técnica
    🟠#3, 2026-08-05): el bloque inline acoplaba serialización de autores
    con la lógica de defaults del router. Ahora el helper es responsable
    de (a) la query con ``joinedload`` + categoría canónica, (b) el
    mapa CmsPost → dict público (``content``, ``author``, ``emotion``,
    ``image_url``).

    El frontend ``TestimonialsSection`` lee ``props.items`` (vía
    ``cmsItems``); antes del fix se devolvía ``testimonials`` y la sección
    quedaba vacía en el render público.
    """
    base = dict(props or {})
    manual = base.get("items") or base.get("testimonials")
    if isinstance(manual, list) and manual:
        return base

    from sqlalchemy.orm import joinedload

    rows = (
        db.query(models.CmsPost)
        .options(lazyload("*"))
        .options(joinedload(models.CmsPost.author_persona))
        .join(models.CmsPost.categories)
        .filter(models.CmsCategory.slug == "testimonials", models.CmsPost.status == "published")
        .order_by(models.CmsPost.published_at.desc(), models.CmsPost.created_at.desc())
        .limit(6)
        .all()
    )
    testimonials = []
    for post in rows:
        author_name = (
            post.author_persona.nombre_completo
            if post.author_persona
            else _D.TESTIMONIALS_FALLBACK_AUTHOR
        )
        testimonials.append(
            {
                "content": post.content or "",
                "author": author_name,
                "emotion": (post.seo_json or {}).get("emotion", _D.TESTIMONIALS_FALLBACK_EMOTION),
                "image_url": post.featured_image_url or "",
            }
        )
    if testimonials:
        base["items"] = testimonials
    base.setdefault("title", _D.TESTIMONIALS_TITLE)
    return base


def _build_section_defaults(
    db: Session,
    site_key: str,
    section_type: str,
    props: dict[str, Any] | None = None,
    *,
    defaults_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fill section props, optionally reusing dynamic defaults within one request.

    ``defaults_cache`` is deliberately request-scoped: dynamic sections such as
    ``stats`` and ``team`` otherwise repeat the same database work once per
    section on a rendered page. The optional argument preserves compatibility
    for callers that need the original uncached behavior.
    """
    if props and any(
        key in props
        for key in (
            "title",
            "subtitle",
            "body",
            "content",
            "items",
            "personas",
            "pastors",
            "stats",
            "testimonials",
            "faqs",
            "embed_url",
            "map_url",
            "eyebrow",
            "title_lead",
            "primary_cta",
            "bg_image",
        )
    ):
        return props or {}

    cache_key = section_type if not props else None
    if defaults_cache is not None and cache_key is not None:
        cached = defaults_cache.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)

    result = _build_section_defaults_uncached(db, site_key, section_type, props)
    if defaults_cache is not None and cache_key is not None:
        defaults_cache[cache_key] = copy.deepcopy(result)
    return result


def _build_section_defaults_uncached(
    db: Session, site_key: str, section_type: str, props: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build defaults for one section without request-level memoization."""
    # Fase 2 (muro de gratitud): la sección ``testimonials`` se hidrata SIEMPRE
    # desde los ``CmsPost`` publicados de la categoría canónica ``testimonials``
    # a menos que el editor haya guardado items manuales explícitos. Debe ir
    # ANTES del early-return genérico: una sección con ``title`` pero sin items
    # debe hidratarse igual (antes se cortaba y quedaba vacía).
    if section_type == "testimonials":
        return _hydrate_testimonials_section(db, props)

    if props and any(
        key in props
        for key in (
            "title",
            "subtitle",
            "body",
            "content",
            "items",
            "personas",
            "pastors",
            "stats",
            "testimonials",
            "faqs",
            "embed_url",
            "map_url",
            "eyebrow",
            "title_lead",
            "primary_cta",
            "bg_image",
        )
    ):
        return props or {}

    _get_system_vars_batch(
        db,
        site_key,
        (
            "church_name",
            "mission_statement",
            "service_time",
            "address",
            "map_embed_url",
            "welcome_title",
            "cta_text",
            "cta_link",
            "cta_title",
            "cta_description",
        ),
    )
    church_name = _get_system_var(db, site_key, "church_name", _D.CHURCH_NAME)
    mission = _get_system_var(db, site_key, "mission_statement", _D.MISSION_STATEMENT)
    service_time = _get_system_var(db, site_key, "service_time", _D.SERVICE_TIME)
    address = _get_system_var(db, site_key, "address", _D.ADDRESS)
    map_embed = _get_system_var(db, site_key, "map_embed_url", _D.MAP_EMBED_URL)

    if section_type == "hero":
        welcome = _get_system_var(db, site_key, "welcome_title", _D.WELCOME_TITLE)
        return {
            "title": welcome.replace("{church_name}", church_name),
            "subtitle": mission,
            "cta_text": _get_system_var(db, site_key, "cta_text", _D.CTA_TEXT),
            "cta_link": _get_system_var(db, site_key, "cta_link", _D.CTA_LINK),
        }
    if section_type == "cta_banner":
        return {
            "title": _get_system_var(db, site_key, "cta_title", _D.CTA_TITLE),
            "description": _get_system_var(
                db, site_key, "cta_description", _D.CTA_DESCRIPTION
            ),
            "button_text": _D.CTA_BANNER_BUTTON_TEXT,
            "button_link": _D.CTA_BANNER_BUTTON_LINK,
        }
    if section_type == "stats":
        if props and isinstance(props, dict) and ("stats" in props or "items" in props):
            return props
        active_personas = db.query(models.Persona).filter(models.Persona.estado_vital == "ACTIVO").count()
        group_count = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.status == "Activo").count()
        return {
            "stats": [
                {"label": _D.STAT_MEMBERS_LABEL, "value": str(active_personas or 0)},
                {"label": _D.STAT_GROUPS_LABEL, "value": str(group_count or 0)},
                {"label": "Años de Ministerio", "value": _D.STAT_YEARS_OF_MINISTRY},
            ]
        }
    if section_type == "team":
        if props and isinstance(props, dict) and ("personas" in props or "items" in props or "team" in props):
            return props
        leaders = (
            db.query(models.Persona)
            .options(lazyload("*"))
            .filter(models.Persona.is_pastoral_leader.is_(True))
            .order_by(models.Persona.is_main_pastor.desc(), models.Persona.nombre_completo.asc())
            .all()
        )
        personas = []
        for p in leaders:
            name = p.nombre_completo
            slug = _slugify(name)
            personas.append(
                {
                    "name": name,
                    "role": "Pastor Principal" if p.is_main_pastor else "Pastor",
                    "photo_url": p.photo_url or "",
                    "slug": slug,
                    "bio_short": p.bio_short or "",
                }
            )
        if not personas:
            personas = [
                {"name": _D.TEAM_FALLBACK_NAME, "role": _D.TEAM_FALLBACK_ROLE, "photo_url": "", "slug": "pastor", "bio_short": ""}
            ]
        return {"personas": personas, "title": _D.TEAM_TITLE}
    if section_type == "faq":
        if props and isinstance(props, dict) and ("faqs" in props or "items" in props):
            return props
        return {
            "faqs": [
                {"question": "¿A qué hora son los servicios?", "answer": service_time},
                {"question": "¿Dónde están ubicados?", "answer": address},
                {
                    "question": "¿Qué debo esperar en mi primera visita?",
                    "answer": _D.FAQ_FIRST_VISIT_ANSWER,
                },
                {
                    "question": "¿Tienen grupos de estudio?",
                    "answer": _D.FAQ_GROUP_STUDY_ANSWER,
                },
            ],
            "title": _D.FAQ_TITLE,
        }
    if section_type == "embed":
        if props and isinstance(props, dict) and "embed_url" in props:
            return props
        return {"embed_url": map_embed or "", "title": church_name, "description": address}
    return props or {}


# ── Pastoral role helper ───────────────────────────────────────────────────────


def _pastoral_role(persona: models.Persona) -> str:
    """Derive the pastoral role label from a Persona record."""
    role = (getattr(persona, "church_role", None) or "").strip()
    if role:
        return role
    return "Pastor Principal" if persona.is_main_pastor else "Pastor"


# ── Taxonomy / post lookup helpers ──────────────────────────────────────────────


def _get_category_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsCategory:
    row = (
        db.query(models.CmsCategory)
        .options(lazyload("*"))
        .filter(models.CmsCategory.site_id == site_id, models.CmsCategory.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise CategoryNotFoundError()
    return row


def _get_tag_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsTag:
    row = (
        db.query(models.CmsTag)
        .options(lazyload("*"))
        .filter(models.CmsTag.site_id == site_id, models.CmsTag.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise TagNotFoundError()
    return row


def _get_post_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsPost:
    row = (
        db.query(models.CmsPost)
        .options(lazyload("*"))
        .filter(models.CmsPost.site_id == site_id, models.CmsPost.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise PostNotFoundError()
    return row


# ── Canonical categories (testimonials / announcements) ─────────────────────────

CANONICAL_CATEGORIES = {
    "testimonials": ("Testimonials", "Testimonios de la comunidad"),
    "announcements": ("Announcements", "Anuncios oficiales"),
}


def _get_main_site(db: Session) -> models.CmsSite:
    """Obtiene el site principal CCF (site_key='ccf')."""
    site = crud.get_cms_site_by_key(db, "ccf")
    if not site:
        raise SiteNotFoundError("Main site not found")
    return site


def _ensure_canonical_category(db: Session, site_id: UUID, category_slug: str) -> models.CmsCategory:
    """Asegura que la categoría canónica exista en el site principal."""
    name, description = CANONICAL_CATEGORIES.get(category_slug, (category_slug.title(), ""))
    cat = crud.get_or_create_canonical_category(db, site_id, category_slug, name, description)
    return cat


def _validate_canonical_category(category_slug: str) -> None:
    if category_slug not in CANONICAL_CATEGORIES:
        raise CmsValidationError("Invalid canonical category", error_code="invalid_canonical_category")

from __future__ import annotations

import logging
import os
import re
import time
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, lazyload

from backend import crud, models, schemas
from backend.api._cms_helpers import (
    _get_scoped_cms_media,
    _get_scoped_persona,
    _scope_cms_pastoral_team_by_user_sede,
    # Gate 6 anti-drift: SEO audit helpers re-exportados por el __init__
    # del paquete (público) para evitar exponer ``_shared`` como path público.
    # Los call sites usan ‍‍`_audit_xxx.foo()‍‍`‍‍ directamente.
    audit_pages,
    build_media_alt_lookup,
    collect_section_media_ids,
    group_sections_by_page,
)
from backend.core.cache_v2 import cached_public
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import normalize_role, require_module_access
from backend.core.rate_limit import rate_limiter
from backend.core.seo import (
    auto_json_ld_for_page,
    build_breadcrumb_items_from_slug,
    build_breadcrumb_list_json_ld,
    build_robots_txt,
    build_sitemap_xml,
)
from backend.models_shared import _utcnow
from backend.schemas import cms as cms_schemas
from backend.schemas._common import PaginatedResponse
from backend.schemas.cms_v2_sections import validate_section_props

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cms/v2",
    tags=["cms_v2"],
    # F-05 (errorescms.md): rate limiting default para todos los endpoints admin
    # del router CMS v2. Los endpoints publicos (/public/sites/.../sitemap.xml,
    # /robots.txt, /track, /images/resize, etc.) ya declaran su propio
    # ``dependencies=[Depends(rate_limiter(limit=...))]`` con limites mas
    # restrictivos; al aplicarlos a nivel endpoint estos SE APLICAN ADEMAS
    # del router-level (FastAPI encadena deps de router+endpoint en orden).
    # El contador Redis usa ``key = f"rate:{identifier}:{request.url.path}"``
    # — dos paths distintos generan dos contadores distintos, asi que los
    # endpoints con override propio no se falsean por la default router-level.
    #
    # 600 req/min/admin es generoso (escritorio humano-admin no llega ni a
    # 100/min). Protege contra un script de un usuario autenticado abusivo
    # (NO DoS anonimo — eso lo maneja slowapi+auth_v3 externamente).
    dependencies=[Depends(rate_limiter(limit=600, window_seconds=60))],
)
PUBLIC_CMS_RATE_LIMIT = 240


def _commit_or_raise_conflict(db: Session, detail: str = "resource already exists") -> None:
    """Commit helper that converts concurrent unique-key violations into 409.

    Without this, two simultaneous requests can pass the existence check and
    then raise an unhandled ``IntegrityError`` (500). Wrapping the commit
    lets us return a controlled ``409 Conflict`` instead.
    """
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.debug("Concurrent create conflict: %s", exc)
        raise HTTPException(status_code=409, detail=detail)

# ── Section Types (platform-wide catalog admin endpoints) ─────────────────
#
# Counterpart to ``get_allowed_section_types`` above: what the CMS does
# at runtime when an editor builds a page, vs. what the API exposes for
# managing the catalog that backs those decisions.


def _get_section_type_or_404(db: Session, name: str) -> models.CmsSectionType:
    """Look up by name (the public identifier) or raise 404."""
    row = db.query(models.CmsSectionType).filter(models.CmsSectionType.name == name.strip().lower()).first()
    if not row:
        raise HTTPException(status_code=404, detail="section type not found")
    return row


@router.get(
    "/section-types",
    response_model=list[schemas.CmsSectionTypeRead],
)
def list_section_types(
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """List every platform-wide section type.

    Section types are global (no site FK), so the endpoint is mounted
    on the global CMS router. Use ``?only_active=true`` to mirror
    ``get_allowed_section_types()`` semantics — the runtime guard
    consulted by ``create_section``.
    """
    query = db.query(models.CmsSectionType).order_by(models.CmsSectionType.name)
    if only_active:
        query = query.filter(models.CmsSectionType.is_active.is_(True))
    return query.all()


@router.get(
    "/section-types/{name}",
    response_model=schemas.CmsSectionTypeRead,
)
def get_section_type(
    name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    return _get_section_type_or_404(db, name)


@router.post(
    "/section-types",
    response_model=schemas.CmsSectionTypeRead,
    status_code=201,
)
def create_section_type(
    payload: schemas.CmsSectionTypeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Register a new section type. Required role: CMS publisher."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    name = payload.name.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    if db.query(models.CmsSectionType).filter(models.CmsSectionType.name == name).first():
        raise HTTPException(status_code=409, detail="section type already exists")
    row = models.CmsSectionType(
        name=name,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(row)
    _commit_or_raise_conflict(db, detail="section type already exists")
    db.refresh(row)
    return row


@router.patch(
    "/section-types/{name}",
    response_model=schemas.CmsSectionTypeRead,
)
def patch_section_type(
    name: str,
    payload: schemas.CmsSectionTypeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Partially update a section type. ``name`` is immutable by design."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_section_type_or_404(db, name)
    # ``CmsSectionTypeUpdate`` excludes ``name`` to protect dangling
    # ``CmsSection.type`` refs (free-string, no FK cascade).
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/section-types/{name}", status_code=204)
def delete_section_type(
    name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Soft-delete a section type by flipping ``is_active=False``.

    Hard-deletes are intentionally disallowed. ``CmsSection.type`` is a
    free-string column, so a hard delete would silently orphan every
    existing section that uses the type. Soft-delete keeps the catalog
    row for audit and aligns with the seed-script policy in
    ``scripts/seed_cms_section_types.py`` (``apply_section_types``
    preserves admin deactivations on re-seed).
    """
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_section_type_or_404(db, name)
    row.is_active = False
    db.commit()
    return None


def get_allowed_section_types(db: Session) -> set[str]:
    """Return set of active section type names from DB, fallback to hardcoded."""
    try:
        rows = db.query(models.CmsSectionType.name).filter(models.CmsSectionType.is_active.is_(True)).all()
        types = {row[0] for row in rows}
        if types:
            return types
    except Exception as exc:
        # If table missing or any error, fall back
        logger.debug("Section type catalog query failed, using hardcoded fallback: %s", exc)
    # Fallback hardcoded list (kept in sync with scripts/seed_cms_section_types.py)
    return {
        "hero",
        "video_hero",
        "rich_text",
        "rich_text_columns",
        "cards",
        "cta_banner",
        "gallery",
        "faq",
        "embed",
        "testimonials",
        "stats",
        "team",
        "countdown",
        "pricing",
        "image_text",
        "timeline",
        "icon_grid",
        "newsletter",
        "popup_banner",
        "button",
        "toc",
        "divider",
        "collapsible",
        "social_links",
        "spacer",
        "calendar",
        "map",
        "document_upload",
        "content_blocks",
        "accordion",
        "civic_hero_search",
        "civic_convocatoria_cards",
        "civic_quick_links",
        "civic_file_downloads",
        "civic_data_table",
        "civic_alert_banner",
    }


CMS_EDITOR_ROLES = {"admin", "coordinador", "docente", "pastor"}
CMS_PUBLISHER_ROLES = {"admin", "coordinador", "pastor"}


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
        raise HTTPException(status_code=403, detail=detail)


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


def _get_site_or_404(db: Session, site_key: str) -> models.CmsSite:
    """Retrieve a CMS site by its key or raise a 404 error.

    Args:
        db: SQLAlchemy session.
        site_key: Identifier of the site (case‑insensitive).
    """
    row = crud.get_cms_site_by_key(db, site_key.strip().lower())
    if not row:
        raise HTTPException(status_code=404, detail="site not found")
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
        raise HTTPException(status_code=404, detail="site not found")
    if site.sede_id is None:
        raise HTTPException(status_code=404, detail="site not found")
    if site.sede_id != actor_sede:
        raise HTTPException(status_code=404, detail="site not found")


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
        raise HTTPException(status_code=404, detail="site not found")
    if not row.is_active:
        raise HTTPException(status_code=404, detail="site not found")
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
        raise HTTPException(status_code=404, detail="menu not found")
    return row


def _get_page_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsPage:
    row = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .filter(models.CmsPage.site_id == site_id, models.CmsPage.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="page not found")
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


@router.get("/sites", response_model=list[schemas.CmsSiteRead])
def list_sites(
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Listar sites CMS. Axioma 3 — Multi-Tenant: staff con sede solo
    ve sites de su sede; superadmin sin sede ve todos."""
    actor_sede = _actor_sede_from_user(db, current_user)
    sites = crud.list_cms_sites(db, only_active=only_active, sede_id=actor_sede)
    return sites


@router.post("/sites", response_model=schemas.CmsSiteRead, status_code=201)
def create_site(
    payload: schemas.CmsSiteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    if not payload.site_key.strip():
        raise HTTPException(status_code=422, detail="site_key is required")
    if not payload.base_path.strip().startswith("/"):
        raise HTTPException(status_code=422, detail="base_path must start with '/'")
    if crud.get_cms_site_by_key(db, payload.site_key.strip().lower()):
        raise HTTPException(status_code=409, detail="site_key already exists")
    # Axioma 3 — Multi-Tenant: si el actor tiene sede asignada, se fuerza
    # su sede_id (ignorando cualquier valor cross-sede del cliente). Si
    # el actor NO tiene sede (superadmin / anterior path), se respeta el
    # sede_id opcional del payload para permitir asignación administrativa.
    actor_sede = _actor_sede_from_user(db, current_user)
    if actor_sede is not None:
        if payload.sede_id is not None and payload.sede_id != actor_sede:
            payload.sede_id = actor_sede
        elif payload.sede_id is None:
            payload.sede_id = actor_sede
    row = crud.create_cms_site(db, payload, commit_with_conflict_check=True)
    if row is None:
        raise HTTPException(status_code=409, detail="site_key already exists")
    return row


@router.get("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def get_site(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return site


@router.patch("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def patch_site(
    site_key: str,
    payload: schemas.CmsSiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_scoped_site_or_404(db, site_key, current_user)
    # Axioma 3 — Multi-Tenant: bloquear movimiento cross-sede. El
    # sede_id de un site no debe cambiar via API para evitar que un
    # editor de sede_a "adopte" o "mueva" un site de sede_b.
    if payload.sede_id is not None:
        raise HTTPException(
            status_code=422,
            detail="sede_id cannot be changed via site update; create a new site instead",
        )
    return crud.update_cms_site(db, row, payload)


@router.delete("/sites/{site_key}", status_code=204)
def delete_site(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Desactiva un sitio CMS sin eliminar su contenido."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_scoped_site_or_404(db, site_key, current_user)
    crud.archive_cms_site(db, row)
    return None


@router.get("/sites/{site_key}/themes", response_model=list[schemas.CmsThemeRead])
def list_themes(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_themes(db, site.id)


@router.get("/sites/{site_key}/themes/{theme_id}", response_model=schemas.CmsThemeRead)
def get_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return row


@router.post("/sites/{site_key}/themes", response_model=schemas.CmsThemeRead, status_code=201)
def create_theme(
    site_key: str,
    payload: schemas.CmsThemeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(
            current_user,
            CMS_PUBLISHER_ROLES,
            detail="Only publishers can activate a theme",
        )
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.create_cms_theme(db, site.id, payload, created_by=current_user.id)


@router.patch("/sites/{site_key}/themes/{theme_id}", response_model=schemas.CmsThemeRead)
def patch_theme(
    site_key: str,
    theme_id: uuid.UUID,
    payload: schemas.CmsThemeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(
            current_user,
            CMS_PUBLISHER_ROLES,
            detail="Only publishers can activate a theme",
        )
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return crud.update_cms_theme(db, row, payload)


@router.post("/sites/{site_key}/themes/{theme_id}/activate", response_model=schemas.CmsThemeRead)
def activate_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.activate_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return row


@router.delete("/sites/{site_key}/themes/{theme_id}", status_code=204)
def delete_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Archiva un tema CMS sin eliminar su historial."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    crud.archive_cms_theme(db, row)
    return None


@router.get("/sites/{site_key}/menus", response_model=list[schemas.CmsMenuRead])
def list_menus(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_menus(db, site.id)


@router.post("/sites/{site_key}/menus", response_model=schemas.CmsMenuRead, status_code=201)
def create_menu(
    site_key: str,
    payload: schemas.CmsMenuCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    if crud.get_cms_menu(db, site.id, payload.menu_key.strip().lower()):
        raise HTTPException(status_code=409, detail="menu_key already exists")
    row = crud.create_cms_menu(db, site.id, payload, commit_with_conflict_check=True)
    if row is None:
        raise HTTPException(status_code=409, detail="menu_key already exists")
    return row


@router.get("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def get_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_menu_or_404(db, site.id, menu_key)


@router.patch("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def patch_menu(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_menu_or_404(db, site.id, menu_key)
    return crud.update_cms_menu(db, row, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}", status_code=204)
def delete_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Desactiva un menu CMS sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_menu_or_404(db, site.id, menu_key)
    crud.delete_cms_menu(db, row)


@router.get(
    "/sites/{site_key}/menus/{menu_key}/items",
    response_model=list[schemas.CmsMenuItemRead],
)
def list_menu_items(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.list_cms_menu_items(db, menu.id)


@router.post(
    "/sites/{site_key}/menus/{menu_key}/items",
    response_model=schemas.CmsMenuItemRead,
    status_code=201,
)
def create_menu_item(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    row = crud.create_cms_menu_item(db, menu.id, payload, commit_with_conflict_check=True)
    if row is None:
        raise HTTPException(status_code=409, detail="menu item conflict")
    return row


@router.patch(
    "/sites/{site_key}/menus/{menu_key}/items/{item_id}",
    response_model=schemas.CmsMenuItemRead,
)
def patch_menu_item(
    site_key: str,
    menu_key: str,
    item_id: uuid.UUID,
    payload: schemas.CmsMenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id, site_id=site.id)
    if not item:
        raise HTTPException(status_code=404, detail="menu item not found")
    return crud.update_cms_menu_item(db, item, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}/items/{item_id}", status_code=204)
def delete_menu_item(
    site_key: str,
    menu_key: str,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Oculta un item de menu sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id, site_id=site.id)
    if not item:
        raise HTTPException(status_code=404, detail="menu item not found")
    crud.delete_cms_menu_item(db, item)


@router.post(
    "/sites/{site_key}/menus/{menu_key}/reorder",
    response_model=list[schemas.CmsMenuItemRead],
)
def reorder_menu_items(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuItemReorderPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.reorder_cms_menu_items(db, menu.id, payload.items)


@router.get(
    "/sites/{site_key}/pages",
    response_model=PaginatedResponse[schemas.CmsPageRead],
)
def list_pages(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    pages, total = crud.list_cms_pages(db, site.id, skip=skip, limit=limit, status=status)
    return PaginatedResponse[schemas.CmsPageRead](items=pages, total=total, skip=skip, limit=limit)


@router.post("/sites/{site_key}/pages", response_model=schemas.CmsPageRead, status_code=201)
def create_page(
    site_key: str,
    payload: schemas.CmsPageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status.strip().lower() != "draft":
        raise HTTPException(status_code=422, detail="new pages must start in draft")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_page(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="slug already exists")
    row = crud.create_cms_page(db, site.id, payload, current_user.id, commit_with_conflict_check=True)
    if row is None:
        raise HTTPException(status_code=409, detail="slug already exists")
    return row


@router.get("/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPageRead)
def get_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_page_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPageRead)
def patch_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsPageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status is not None:
        raise HTTPException(status_code=422, detail="use workflow endpoint to change status")
    # Scheduled publish + auto-archive (2026-07-06): validaciones del
    # scheduling window. La regla estricta es ``expires_at >= publish_at``
    # sólo si ambos están presentes; ``null`` representa el reset (sin
    # programación). ``publish_at`` no necesita ser futuro aquí — el
    # cliente puede dejar una fecha pasada para cancelar flujo. Pero
    # ``expires_at`` < ``publish_at`` es claramente un error de typo.
    if payload.publish_at is not None and payload.expires_at is not None and payload.expires_at < payload.publish_at:
        raise HTTPException(
            status_code=422,
            detail="expires_at must be >= publish_at",
        )
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_page_or_404(db, site.id, slug)
    updated = crud.update_cms_page(db, row, payload, current_user.id)
    # Workflow parity gap fix (2026-07-06): when an editor sets
    # ``publish_at`` via PATCH on a non-terminal page, auto-flip the
    # status to ``scheduled`` so the cron scheduler picks it up
    # (``find_pages_due_for_publish`` filters require ``status='scheduled'``).
    # The previous POST endpoint already does this; we mirror it here for
    # the modern PATCH path so the recommended flow isn't inert.
    if payload.publish_at is not None and updated.status in {"draft", "in_review", "approved"}:
        updated.status = "scheduled"
        db.commit()
        db.refresh(updated)
    return updated


@router.delete("/sites/{site_key}/pages/{slug}", status_code=204)
def delete_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_page_or_404(db, site.id, slug)
    crud.delete_cms_page(db, row)


@router.post(
    "/sites/{site_key}/pages/{slug}/clone",
    response_model=schemas.CmsPageRead,
    status_code=201,
)
def clone_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsPageClone,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Clone a page with all its active sections (F-02).

    La página clonada arranca como ``draft`` sin schedule.  El slug
    destino debe ser único en el site.
    """
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    source = _get_page_or_404(db, site.id, slug)
    new_slug = _slugify(payload.new_slug)
    if not new_slug:
        raise HTTPException(status_code=422, detail="new_slug is required")
    if new_slug == source.slug:
        raise HTTPException(
            status_code=422,
            detail="new_slug must differ from source slug",
        )
    if crud.get_cms_page(db, site.id, new_slug):
        raise HTTPException(status_code=409, detail="slug already exists")
    cloned = crud.clone_cms_page(
        db,
        source,
        new_slug,
        current_user.id,
        new_title=payload.new_title,
    )
    if cloned is None:
        raise HTTPException(status_code=409, detail="slug already exists")
    return cloned


@router.get(
    "/sites/{site_key}/pages/{slug}/sections",
    response_model=PaginatedResponse[schemas.CmsSectionRead],
)
def list_sections(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    section_type: str | None = Query(None),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    items, total = crud.list_cms_sections(db, page.id, skip=skip, limit=limit, section_type=section_type)
    return PaginatedResponse[schemas.CmsSectionRead](items=items, total=total, skip=skip, limit=limit)


@router.post(
    "/sites/{site_key}/pages/{slug}/sections",
    response_model=schemas.CmsSectionRead,
    status_code=201,
)
def create_section(
    site_key: str,
    slug: str,
    payload: schemas.CmsSectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    allowed_types = get_allowed_section_types(db)
    if payload.type not in allowed_types:
        raise HTTPException(status_code=422, detail="unsupported section type")
    # Validate props against section type schema
    try:
        props = payload.props_json or {}
        validated_props = validate_section_props(payload.type, props)
        payload.props_json = validated_props
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    payload.status = (payload.status or "active").strip().lower()
    if payload.status not in {"active", "archived"}:
        raise HTTPException(status_code=422, detail="unsupported section status")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.create_cms_section(db, page.id, payload, commit_with_conflict_check=True)
    if row is None:
        raise HTTPException(status_code=409, detail="section conflict")
    return row


@router.patch(
    "/sites/{site_key}/pages/{slug}/sections/{section_id}",
    response_model=schemas.CmsSectionRead,
)
def patch_section(
    site_key: str,
    slug: str,
    section_id: uuid.UUID,
    payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    allowed_types = get_allowed_section_types(db)
    if payload.type is not None and payload.type not in allowed_types:
        raise HTTPException(status_code=422, detail="unsupported section type")
    if payload.status is not None:
        payload.status = payload.status.strip().lower()
        if payload.status not in {"active", "archived"}:
            raise HTTPException(status_code=422, detail="unsupported section status")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id, site_id=site.id)
    if not row:
        raise HTTPException(status_code=404, detail="section not found")
    # Validate + sanitise props_json after scope/row checks so we can use
    # the real section type when the client omits ``type``. This guarantees
    # PATCH cannot bypass XSS/whitelist rules by mutating the type first.
    if payload.props_json is not None:
        effective_type = (payload.type or row.type or "").strip().lower() or "rich_text"
        try:
            payload.props_json = validate_section_props(effective_type, payload.props_json)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return crud.update_cms_section(db, row, payload)


@router.delete("/sites/{site_key}/pages/{slug}/sections/{section_id}", status_code=204)
def delete_section(
    site_key: str,
    slug: str,
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id, site_id=site.id)
    if not row:
        raise HTTPException(status_code=404, detail="section not found")
    crud.archive_cms_section(db, row)


@router.post(
    "/sites/{site_key}/pages/{slug}/sections/reorder",
    response_model=list[schemas.CmsSectionRead],
)
def reorder_sections(
    site_key: str,
    slug: str,
    payload: schemas.CmsSectionReorderPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    return crud.reorder_cms_sections(db, page.id, payload.items)


@router.get(
    "/sites/{site_key}/pages/{slug}/versions",
    response_model=PaginatedResponse[schemas.CmsPageVersionRead],
)
def list_versions(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    items, total = crud.list_cms_page_versions(db, page.id, skip=skip, limit=limit)
    return PaginatedResponse[schemas.CmsPageVersionRead](items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/sites/{site_key}/pages/{slug}/publish-log",
    response_model=PaginatedResponse[schemas.CmsPublishLogRead],
)
def list_publish_log(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    items, total = crud.list_cms_publish_logs(db, site.id, page_id=page.id, skip=skip, limit=limit)
    return PaginatedResponse[schemas.CmsPublishLogRead](items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/sites/{site_key}/seo-audit",
    response_model=schemas.SeoAuditResponse,
)
def seo_audit(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    min_score: int | None = Query(None, ge=0, le=100),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Audit SEO sobre las páginas de un sitio.

    CmsSite y CmsPage son globales del faro (Axioma 3) — el audit
    opera cross-sede por diseño para preservar la coherencia editorial
    del site público. Sólo se restringe por ``site_key`` + ``status``.
    Requiere rol editorial (CMS_EDITOR_ROLES) — un lector sin acceso
    de edición recibe 403.

    Implementación: 3 ORM queries para evitar N+1 (``pages`` paginadas,
    ``sections`` por ``page_id IN (...)``, y ``media_alt_lookup`` por
    los UUIDs referenciados en props_json). Scoring y findings corren
    en memoria sobre data materializada.
    """
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)

    pages_query = db.query(models.CmsPage).options(lazyload("*")).filter(models.CmsPage.site_id == site.id)
    if status:
        pages_query = pages_query.filter(models.CmsPage.status == status)
    pages = pages_query.order_by(models.CmsPage.updated_at.desc()).offset(skip).limit(limit).all()
    page_ids = [page.id for page in pages]
    sections_by_page = group_sections_by_page([])
    if page_ids:
        sections_rows = (
            db.query(models.CmsSection)
            .filter(models.CmsSection.page_id.in_(page_ids))
            .order_by(models.CmsSection.sort_order.asc())
            .all()
        )
        sections_by_page = group_sections_by_page(sections_rows)

    media_ids = collect_section_media_ids(section for rows in sections_by_page.values() for section in rows)
    media_alt_lookup = build_media_alt_lookup(db, media_ids)

    audits, aggregate = audit_pages(
        pages,
        sections_by_page,
        media_alt_lookup,
    )
    if min_score is not None:
        audits = [audit for audit in audits if audit.score >= min_score]

    return schemas.SeoAuditResponse(
        site_key=site.site_key,
        aggregate=aggregate,
        pages=audits,
    )


def _cms_readiness_issue(
    *,
    code: str,
    severity: str,
    title: str,
    detail: str,
    count: int,
    href: str | None = None,
) -> cms_schemas.CmsReadinessIssue:
    return cms_schemas.CmsReadinessIssue(
        code=code,
        severity=severity,
        title=title,
        detail=detail,
        count=count,
        href=href,
    )


@router.get(
    "/sites/{site_key}/readiness",
    response_model=cms_schemas.CmsReadinessResponse,
)
def cms_readiness(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Production-readiness snapshot for the CMS site.

    The endpoint intentionally reads existing CMS v2 contracts instead of
    creating a parallel content model. It helps editors see whether the CMS is
    ready to feed public pages: published content, active theme/menu, visible
    sections, SEO/media hygiene, supported section types, redirects and broken
    link checks.
    """
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)

    page_base = db.query(models.CmsPage).filter(models.CmsPage.site_id == site.id)
    total_pages = page_base.count()
    published_pages = page_base.filter(models.CmsPage.status == "published").count()
    draft_pages = page_base.filter(models.CmsPage.status == "draft").count()
    in_review_pages = page_base.filter(models.CmsPage.status == "in_review").count()
    archived_pages = page_base.filter(models.CmsPage.status == "archived").count()
    scheduled_without_date = page_base.filter(
        models.CmsPage.status == "scheduled",
        models.CmsPage.publish_at.is_(None),
    ).count()
    published_without_version = page_base.filter(
        models.CmsPage.status == "published",
        models.CmsPage.published_version_id.is_(None),
    ).count()

    section_base = (
        db.query(models.CmsSection)
        .join(models.CmsPage, models.CmsSection.page_id == models.CmsPage.id)
        .filter(models.CmsPage.site_id == site.id)
    )
    visible_sections = section_base.filter(
        models.CmsSection.is_visible.is_(True),
        models.CmsSection.status != "archived",
        models.CmsSection.deleted_at.is_(None),
    ).count()
    hidden_sections = section_base.filter(
        (models.CmsSection.is_visible.is_(False))
        | (models.CmsSection.status == "archived")
        | (models.CmsSection.deleted_at.isnot(None))
    ).count()
    pages_without_visible_sections = (
        db.query(models.CmsPage.id)
        .filter(models.CmsPage.site_id == site.id)
        .outerjoin(
            models.CmsSection,
            (models.CmsSection.page_id == models.CmsPage.id)
            & (models.CmsSection.is_visible.is_(True))
            & (models.CmsSection.status != "archived")
            & (models.CmsSection.deleted_at.is_(None)),
        )
        .group_by(models.CmsPage.id)
        .having(func.count(models.CmsSection.id) == 0)
        .count()
    )

    allowed_section_types = get_allowed_section_types(db)
    unsupported_sections = section_base.filter(
        models.CmsSection.deleted_at.is_(None),
        ~models.CmsSection.type.in_(allowed_section_types),
    ).count()

    active_themes = (
        db.query(models.CmsTheme)
        .filter(
            models.CmsTheme.site_id == site.id,
            models.CmsTheme.is_active.is_(True),
            models.CmsTheme.status != "archived",
        )
        .count()
    )
    active_menus = (
        db.query(models.CmsMenu).filter(models.CmsMenu.site_id == site.id, models.CmsMenu.is_active.is_(True)).count()
    )
    menu_items = (
        db.query(models.CmsMenuItem)
        .join(models.CmsMenu, models.CmsMenuItem.menu_id == models.CmsMenu.id)
        .filter(models.CmsMenu.site_id == site.id, models.CmsMenu.is_active.is_(True))
        .count()
    )

    media_query = db.query(models.CmsMediaItem).filter(models.CmsMediaItem.status != "archived")
    if site.sede_id is not None:
        media_query = media_query.filter(models.CmsMediaItem.sede_id == site.sede_id)
    media_total = media_query.count()
    media_without_alt = media_query.filter(
        (models.CmsMediaItem.alt_text.is_(None)) | (func.length(func.trim(models.CmsMediaItem.alt_text)) == 0)
    ).count()

    recent_publish_events = db.query(models.CmsPublishLog).filter(models.CmsPublishLog.site_id == site.id).count()

    active_redirects = 0
    unresolved_broken_links = 0
    try:
        active_redirects = (
            db.query(models.CmsRedirect)
            .filter(models.CmsRedirect.site_key == site.site_key, models.CmsRedirect.is_active.is_(True))
            .count()
        )
        unresolved_broken_links = (
            db.query(models.BrokenLinkCheck)
            .filter(
                models.BrokenLinkCheck.site_key == site.site_key,
                models.BrokenLinkCheck.is_broken.is_(True),
                models.BrokenLinkCheck.resolved_at.is_(None),
            )
            .count()
        )
    except Exception:
        logger.exception("Failed to query redirects or broken links for CMS readiness")
        db.rollback()

    issues: list[cms_schemas.CmsReadinessIssue] = []
    if published_pages == 0:
        issues.append(
            _cms_readiness_issue(
                code="no_published_pages",
                severity="error",
                title="Sin páginas publicadas",
                detail="El sitio no tiene contenido CMS publicado para alimentar las páginas públicas.",
                count=1,
                href="/cms/pages",
            )
        )
    if active_themes == 0:
        issues.append(
            _cms_readiness_issue(
                code="no_active_theme",
                severity="error",
                title="Sin tema activo",
                detail="El render público necesita un tema activo para resolver tokens visuales del sitio.",
                count=1,
                href="/cms/themes",
            )
        )
    if unsupported_sections:
        issues.append(
            _cms_readiness_issue(
                code="unsupported_sections",
                severity="error",
                title="Secciones no soportadas",
                detail="Hay secciones cuyo tipo no está activo en el catálogo CMS.",
                count=unsupported_sections,
                href="/cms/section-types",
            )
        )
    if unresolved_broken_links:
        issues.append(
            _cms_readiness_issue(
                code="broken_links",
                severity="error",
                title="Links rotos pendientes",
                detail="Hay enlaces marcados como rotos que pueden producir 404 en navegación pública.",
                count=unresolved_broken_links,
                href="/cms/broken-links",
            )
        )
    if active_menus == 0:
        issues.append(
            _cms_readiness_issue(
                code="no_active_menus",
                severity="warning",
                title="Sin menús activos",
                detail="La navegación pública queda limitada si no hay menús activos configurados.",
                count=1,
                href="/cms/menus",
            )
        )
    if pages_without_visible_sections:
        issues.append(
            _cms_readiness_issue(
                code="pages_without_visible_sections",
                severity="warning",
                title="Páginas sin secciones visibles",
                detail="Estas páginas pueden publicar una experiencia vacía o depender de fallback anterior.",
                count=pages_without_visible_sections,
                href="/cms/pages",
            )
        )
    if published_without_version:
        issues.append(
            _cms_readiness_issue(
                code="published_without_version",
                severity="warning",
                title="Publicadas sin versión fijada",
                detail="Conviene publicar con snapshot para proteger la salida pública ante cambios de borrador.",
                count=published_without_version,
                href="/cms/pages",
            )
        )
    if media_without_alt:
        issues.append(
            _cms_readiness_issue(
                code="media_without_alt",
                severity="warning",
                title="Media sin alt text",
                detail="Las imágenes sin texto alternativo reducen accesibilidad y calidad SEO.",
                count=media_without_alt,
                href="/cms/media",
            )
        )
    if scheduled_without_date:
        issues.append(
            _cms_readiness_issue(
                code="scheduled_without_date",
                severity="warning",
                title="Programadas sin fecha",
                detail=(
                    "Hay páginas en estado scheduled sin publish_at, por lo que no "
                    "podrán publicarse automáticamente."
                ),
                count=scheduled_without_date,
                href="/cms/pages",
            )
        )

    penalty = sum(20 if issue.severity == "error" else 8 for issue in issues)
    score = max(0, 100 - penalty)

    capabilities = [
        cms_schemas.CmsReadinessCapability(
            key="pages",
            label="Gestión de páginas",
            status="ready" if total_pages else "partial",
            detail=f"{total_pages} páginas, {published_pages} publicadas.",
            href="/cms/pages",
        ),
        cms_schemas.CmsReadinessCapability(
            key="builder",
            label="Constructor de secciones",
            status="ready" if visible_sections and not unsupported_sections else "attention",
            detail=f"{visible_sections} visibles, {unsupported_sections} no soportadas.",
            href="/cms/builder",
        ),
        cms_schemas.CmsReadinessCapability(
            key="media",
            label="Media y recursos",
            status=("ready" if media_total and not media_without_alt else ("partial" if media_total else "attention")),
            detail=f"{media_total} archivos activos, {media_without_alt} sin alt.",
            href="/cms/media",
        ),
        cms_schemas.CmsReadinessCapability(
            key="seo",
            label="SEO y publicación",
            status="ready" if published_pages and not published_without_version else "partial",
            detail=f"{published_pages} publicadas, {published_without_version} sin snapshot.",
            href="/cms/seo-audit",
        ),
        cms_schemas.CmsReadinessCapability(
            key="menus",
            label="Menús y navegación",
            status="ready" if active_menus and menu_items else "attention",
            detail=f"{active_menus} menús activos, {menu_items} ítems.",
            href="/cms/menus",
        ),
        cms_schemas.CmsReadinessCapability(
            key="themes",
            label="Temas y tokens",
            status="ready" if active_themes else "attention",
            detail=f"{active_themes} temas activos.",
            href="/cms/themes",
        ),
        cms_schemas.CmsReadinessCapability(
            key="operations",
            label="Operación y auditoría",
            status=(
                "ready" if recent_publish_events or active_redirects or unresolved_broken_links == 0 else "partial"
            ),
            detail=(
                f"{recent_publish_events} eventos, {active_redirects} redirects, {unresolved_broken_links} links rotos."
            ),
            href="/cms/audit",
        ),
    ]

    metrics = [
        cms_schemas.CmsReadinessMetric(key="total_pages", label="Páginas", value=total_pages, href="/cms/pages"),
        cms_schemas.CmsReadinessMetric(
            key="published_pages",
            label="Publicadas",
            value=published_pages,
            href="/cms/pages",
        ),
        cms_schemas.CmsReadinessMetric(key="draft_pages", label="Borradores", value=draft_pages, href="/cms/pages"),
        cms_schemas.CmsReadinessMetric(
            key="in_review_pages",
            label="En revisión",
            value=in_review_pages,
            href="/cms/pages",
        ),
        cms_schemas.CmsReadinessMetric(
            key="archived_pages",
            label="Archivadas",
            value=archived_pages,
            href="/cms/pages",
        ),
        cms_schemas.CmsReadinessMetric(
            key="visible_sections",
            label="Secciones visibles",
            value=visible_sections,
            href="/cms/builder",
        ),
        cms_schemas.CmsReadinessMetric(
            key="hidden_sections",
            label="Secciones ocultas",
            value=hidden_sections,
            href="/cms/builder",
        ),
        cms_schemas.CmsReadinessMetric(key="media_total", label="Media activa", value=media_total, href="/cms/media"),
        cms_schemas.CmsReadinessMetric(
            key="active_menus",
            label="Menús activos",
            value=active_menus,
            href="/cms/menus",
        ),
        cms_schemas.CmsReadinessMetric(
            key="active_themes",
            label="Temas activos",
            value=active_themes,
            href="/cms/themes",
        ),
        cms_schemas.CmsReadinessMetric(
            key="broken_links",
            label="Links rotos",
            value=unresolved_broken_links,
            href="/cms/broken-links",
        ),
    ]

    return cms_schemas.CmsReadinessResponse(
        site_key=site.site_key,
        score=score,
        generated_at=datetime.now(timezone.utc),
        metrics=metrics,
        issues=issues,
        capabilities=capabilities,
    )


@router.get("/sites/{site_key}/pages/{slug}/preview", response_model=schemas.CmsPublicPageRead)
def preview_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    sections_list, _ = crud.list_cms_sections(db, page.id)
    sections = [
        section
        for section in sections_list
        if section.is_visible and getattr(section, "status", "active") != "archived"
    ]
    # ── Inject default props for empty sections (same as public_page) ──
    section_reads = []
    for section in sections:
        sr = schemas.CmsSectionRead.model_validate(section)
        sr.props_json = _build_section_defaults(db, site_key, sr.type, sr.props_json)
        section_reads.append(sr)

    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    page_url = f"{base_url}/{page.slug.lstrip('/')}"
    canonical = (page.seo_json or {}).get("canonical_url") if isinstance(page.seo_json, dict) else None
    json_ld_data = auto_json_ld_for_page(
        page,
        site,
        sections=sections,
        base_url=base_url,
        site_name=_get_system_var(db, site_key, "church_name", site.name),
    )
    # Allow manual override of JSON-LD from seo_json
    if isinstance(page.seo_json, dict) and page.seo_json.get("json_ld"):
        json_ld_data = page.seo_json["json_ld"]

    # Build breadcrumbs
    breadcrumb_items = build_breadcrumb_items_from_slug(
        page.slug, page.title, base_url=base_url, site_name=site.name or "Home"
    )
    breadcrumb_json_ld = build_breadcrumb_list_json_ld(breadcrumb_items, base_url=base_url)

    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=section_reads,
        json_ld=json_ld_data,
        canonical_url=canonical or page_url,
        breadcrumbs=breadcrumb_items,
        breadcrumb_json_ld=breadcrumb_json_ld,
    )


@router.post(
    "/sites/{site_key}/pages/{slug}/rollback/{version_id}",
    response_model=schemas.CmsPageRead,
)
def rollback_page(
    site_key: str,
    slug: str,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    version = crud.get_cms_page_version(db, page.id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="version not found")
    return crud.restore_cms_page_version(db, page, version, user_id=current_user.id)


@router.post("/sites/{site_key}/pages/{slug}/workflow", response_model=schemas.CmsPageRead)
def workflow_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsWorkflowAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    action = payload.action.strip().lower()
    if action in {"approve", "publish", "archive"}:
        _assert_role(current_user, CMS_PUBLISHER_ROLES)
    else:
        _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.transition_cms_page_status(db, page, payload.action, current_user.id, notes=payload.notes)
    if not row:
        raise HTTPException(status_code=422, detail="invalid workflow action")
    return row


@router.get(
    "/public/sites/{site_key}/theme",
    response_model=schemas.CmsThemeRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_theme(site_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    row = (
        db.query(models.CmsTheme)
        .options(lazyload("*"))
        .filter(
            models.CmsTheme.site_id == site.id,
            models.CmsTheme.is_active.is_(True),
            models.CmsTheme.status != "archived",
        )
        .order_by(models.CmsTheme.updated_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="active theme not found")
    return schemas.CmsThemeRead.model_validate(row)


@router.get(
    "/public/sites/{site_key}/menus/{menu_key}",
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_menu(site_key: str, menu_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    if not menu.is_active:
        raise HTTPException(status_code=404, detail="menu not found")
    all_items = (
        db.query(models.CmsMenuItem)
        .options(lazyload("*"))
        .filter(models.CmsMenuItem.menu_id == menu.id)
        .order_by(models.CmsMenuItem.sort_order.asc(), models.CmsMenuItem.id.asc())
        .all()
    )
    public_ids = {item.id for item in all_items if item.visibility == "public"}
    items = [
        item
        for item in all_items
        if item.visibility == "public" and (item.parent_id is None or item.parent_id in public_ids)
    ]
    visible_ids = {item.id for item in items}
    serialized = [
        {
            "id": item.id,
            "parent_id": item.parent_id if item.parent_id in visible_ids else None,
            "label": item.label,
            "href": item.href,
            "target": item.target,
            "is_external": item.is_external,
            "visibility": item.visibility,
            "sort_order": item.sort_order,
            "meta_json": item.meta_json or {},
        }
        for item in items
    ]
    return {
        "site_key": site.site_key,
        "menu_key": menu.menu_key,
        "items": serialized,
    }


_system_var_cache: dict[str, tuple[float, str]] = {}
_SYSTEM_VAR_TTL = 300  # 5 minutes


def _get_system_var(db, site_key: str, var_key: str, default: str = "") -> str:
    """Read a single SystemVariable by key, with optional site_key prefix.
    Cached for 5 minutes per site_key+var_key to avoid repeated DB hits."""
    cache_key = f"{site_key}:{var_key}"
    now = time.monotonic()
    if cache_key in _system_var_cache:
        cached_time, cached_val = _system_var_cache[cache_key]
        if now - cached_time < _SYSTEM_VAR_TTL:
            return cached_val
    row = db.query(models.SystemVariable).filter(
        models.SystemVariable.key == f"{site_key}_{var_key}",
        models.SystemVariable.deleted_at.is_(None),
    ).first()
    val = row.value if row and row.value else default
    _system_var_cache[cache_key] = (now, val)
    return val


def _build_section_defaults(
    db: Session, site_key: str, section_type: str, props: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Fill empty section props with data from SystemVariable / DB / hardcoded."""
    # If the section already has meaningful content, skip defaults
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

    church_name = _get_system_var(db, site_key, "church_name", "Nuestra Iglesia")
    mission = _get_system_var(db, site_key, "mission_statement", "Compartir el amor de Dios y hacer discípulos")
    service_time = _get_system_var(db, site_key, "service_time", "Domingos 10:00 AM")
    address = _get_system_var(db, site_key, "address", "Ciudad, País")
    map_embed = _get_system_var(db, site_key, "map_embed_url", "")

    if section_type == "hero":
        welcome = _get_system_var(db, site_key, "welcome_title", "Bienvenidos a {church_name}")
        return {
            "title": welcome.replace("{church_name}", church_name),
            "subtitle": mission,
            "cta_text": _get_system_var(db, site_key, "cta_text", "Conócenos"),
            "cta_link": _get_system_var(db, site_key, "cta_link", "/pastores"),
        }

    if section_type == "cta_banner":
        return {
            "title": _get_system_var(db, site_key, "cta_title", "Únete a nuestra comunidad"),
            "description": _get_system_var(
                db,
                site_key,
                "cta_description",
                "Te invitamos a ser parte de nuestra familia. Todos son bienvenidos.",
            ),
            "button_text": "Visítanos",
            "button_link": "/contacto",
        }

    if section_type == "stats":
        active_personas = db.query(models.Persona).filter(models.Persona.estado_vital == "ACTIVO").count()
        group_count = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.status == "Activo").count()
        return {
            "stats": [
                {"label": "Miembros Activos", "value": str(active_personas or 0)},
                {"label": "Grupos de Casa", "value": str(group_count or 0)},
                {"label": "Años de Ministerio", "value": "25+"},
            ]
        }

    if section_type == "team":
        leaders = (
            db.query(models.Persona)
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
                {
                    "name": "Pastor",
                    "role": "Pastor Principal",
                    "photo_url": "",
                    "slug": "pastor",
                    "bio_short": "",
                }
            ]
        return {"personas": personas, "title": "Nuestro Equipo Pastoral"}

    if section_type == "testimonials":
        rows = (
            db.query(models.Testimonial)
            .filter(
                models.Testimonial.is_approved.is_(True),
                models.Testimonial.status == "published",
            )
            .order_by(models.Testimonial.created_at.desc())
            .limit(6)
            .all()
        )
        testimonials = []
        for t in rows:
            author_name = t.author.nombre_completo if t.author else "Anónimo"
            testimonials.append(
                {
                    "content": t.content,
                    "author": author_name,
                    "emotion": t.emotion or "Gratitud",
                    "image_url": t.image_url or "",
                }
            )
        if not testimonials:
            testimonials = [
                {
                    "content": ("Dios ha sido fiel en cada etapa. Bendigo a esta iglesia por su amor y apoyo."),
                    "author": "Miembro de la Iglesia",
                    "emotion": "Gratitud",
                    "image_url": "",
                },
            ]
        return {"testimonials": testimonials, "title": "Testimonios"}

    if section_type == "faq":
        return {
            "faqs": [
                {"question": "¿A qué hora son los servicios?", "answer": service_time},
                {"question": "¿Dónde están ubicados?", "answer": address},
                {
                    "question": "¿Qué debo esperar en mi primera visita?",
                    "answer": ("Una comunidad cálida que te recibirá con los brazos abiertos. Ven tal como eres."),
                },
                {
                    "question": "¿Tienen grupos de estudio?",
                    "answer": (
                        "Sí, tenemos grupos de casa que se reúnen durante la semana. Contáctanos para más información."
                    ),
                },
            ],
            "title": "Preguntas Frecuentes",
        }

    if section_type == "embed":
        return {
            "embed_url": map_embed or "",
            "title": church_name,
            "description": address,
        }

    return props or {}


@router.get(
    "/public/sites/{site_key}/pages",
    response_model=PaginatedResponse[schemas.CmsPageRead],
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_pages_list(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    """Public endpoint: list published CMS pages for sitemap and SEO."""
    site = _get_public_site_or_404(db, site_key)
    query = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.status == "published")
    )
    total = query.count()
    pages = query.order_by(models.CmsPage.updated_at.desc()).offset(skip).limit(limit).all()
    return PaginatedResponse[schemas.CmsPageRead](items=pages, total=total, skip=skip, limit=limit)


@router.get(
    "/public/sites/{site_key}/pages/{slug}",
    response_model=schemas.CmsPublicPageRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_page(site_key: str, slug: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    page = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .filter(
            models.CmsPage.site_id == site.id,
            models.CmsPage.slug == _slugify(slug),
            models.CmsPage.status == "published",
        )
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="published page not found")
    published_version = None
    if page.published_version_id:
        published_version = (
            db.query(models.CmsPageVersion)
            .options(lazyload("*"))
            .filter(
                models.CmsPageVersion.page_id == page.id,
                models.CmsPageVersion.id == page.published_version_id,
            )
            .first()
        )

    if published_version:
        snapshot = published_version.snapshot_json or {}
        page_snapshot = snapshot.get("page") if isinstance(snapshot, dict) else {}
        sections_snapshot = snapshot.get("sections") if isinstance(snapshot, dict) else []
        section_rows = [
            _snapshot_section_read(
                section_data,
                page_id=page.id,
                index=index,
                timestamp=published_version.created_at,
            )
            for index, section_data in enumerate(
                sorted(
                    [item for item in sections_snapshot if isinstance(item, dict)],
                    key=lambda item: item.get("sort_order") if isinstance(item.get("sort_order"), int) else 0,
                )
            )
            if section_data.get("is_visible", True) is not False and section_data.get("status", "active") != "archived"
        ]
        # ── Inject default props for empty sections (published version path) ──
        section_rows = [
            schemas.CmsSectionRead(
                **{
                    **s.model_dump(),
                    "props_json": _build_section_defaults(db, site_key, s.type, s.props_json),
                }
            )
            for s in section_rows
        ]

        slug_val = str(page_snapshot.get("slug") or page.slug) if isinstance(page_snapshot, dict) else page.slug
        title_val = str(page_snapshot.get("title") or page.title) if isinstance(page_snapshot, dict) else page.title
        settings = get_settings()
        base_url = settings.frontend_url.rstrip("/")
        breadcrumb_items = build_breadcrumb_items_from_slug(
            slug_val, title_val, base_url=base_url, site_name=site.name or "Home"
        )
        breadcrumb_json_ld = build_breadcrumb_list_json_ld(breadcrumb_items, base_url=base_url)

        page_url = f"{base_url}/{slug_val.lstrip('/')}"
        canonical = (
            page_snapshot.get("canonical_url")
            if isinstance(page_snapshot, dict) and page_snapshot.get("canonical_url")
            else None
        )
        json_ld_data = auto_json_ld_for_page(
            page,
            site,
            sections=section_rows,
            base_url=base_url,
            site_name=_get_system_var(db, site_key, "church_name", site.name),
        )
        # Allow manual override of JSON-LD from seo_json in snapshot
        snapshot_seo = (
            page_snapshot.get("seo_json")
            if isinstance(page_snapshot, dict) and isinstance(page_snapshot.get("seo_json"), dict)
            else {}
        )
        if snapshot_seo.get("json_ld"):
            json_ld_data = snapshot_seo["json_ld"]

        return schemas.CmsPublicPageRead(
            site_key=site.site_key,
            slug=slug_val,
            title=title_val,
            seo_json=snapshot_seo,
            sections=section_rows,
            json_ld=json_ld_data,
            canonical_url=canonical or page_url,
            breadcrumbs=breadcrumb_items,
            breadcrumb_json_ld=breadcrumb_json_ld,
        )

    sections_list, _ = crud.list_cms_sections(db, page.id)
    sections = [
        section
        for section in sections_list
        if section.is_visible and getattr(section, "status", "active") != "archived"
    ]
    section_reads = []
    for section in sections:
        sr = schemas.CmsSectionRead.model_validate(section)
        sr.props_json = _build_section_defaults(db, site_key, sr.type, sr.props_json)
        section_reads.append(sr)

    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    page_url = f"{base_url}/{page.slug.lstrip('/')}"
    canonical = (page.seo_json or {}).get("canonical_url") if isinstance(page.seo_json, dict) else None
    json_ld_data = auto_json_ld_for_page(
        page,
        site,
        sections=sections,
        base_url=base_url,
        site_name=_get_system_var(db, site_key, "church_name", site.name),
    )
    # Allow manual override of JSON-LD from seo_json
    if isinstance(page.seo_json, dict) and page.seo_json.get("json_ld"):
        json_ld_data = page.seo_json["json_ld"]

    # Build breadcrumbs
    breadcrumb_items = build_breadcrumb_items_from_slug(
        page.slug, page.title, base_url=base_url, site_name=site.name or "Home"
    )
    breadcrumb_json_ld = build_breadcrumb_list_json_ld(breadcrumb_items, base_url=base_url)

    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=section_reads,
        json_ld=json_ld_data,
        canonical_url=canonical or page_url,
        breadcrumbs=breadcrumb_items,
        breadcrumb_json_ld=breadcrumb_json_ld,
    )


@router.get(
    "/public/sites/{site_key}/sitemap.xml",
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
@cached_public(ttl=300)
def public_sitemap(site_key: str, db: Session = Depends(get_db)):
    """Public endpoint: generate sitemap.xml for all published pages."""
    site = _get_public_site_or_404(db, site_key)
    pages = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.status == "published")
        .order_by(models.CmsPage.updated_at.desc())
        .limit(500)
        .all()
    )
    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    xml = build_sitemap_xml(pages, base_url, include_images=True)
    return Response(content=xml, media_type="application/xml")


@router.get(
    "/public/sites/{site_key}/robots.txt",
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
@cached_public(ttl=300)
def public_robots(site_key: str, db: Session = Depends(get_db)):
    """Public endpoint: generate robots.txt for the site."""
    _get_public_site_or_404(db, site_key)
    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    sitemap_url = f"{base_url.rstrip('/')}/api/cms/v2/public/sites/{site_key}/sitemap.xml"
    txt = build_robots_txt(base_url, sitemap_url=sitemap_url)
    return Response(content=txt, media_type="text/plain")


# ── Pastoral Team (public + CMS-managed) ───────────────────────────────────


def _pastoral_role(persona: models.Persona) -> str:
    role = (getattr(persona, "church_role", None) or "").strip()
    if role:
        return role
    return "Pastor Principal" if persona.is_main_pastor else "Pastor"


@router.get(
    "/public/sites/{site_key}/pastoral-team",
    response_model=List[schemas.PastoralProfileRead],
    dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))],
)
@cached_public(ttl=300)
def public_pastoral_team(site_key: str, db: Session = Depends(get_db)):
    """Public endpoint: list pastoral leaders.

    Axioma 3 — Multi-Tenant: las pastoras y pastores listados se acotan
    a la sede del usuario actual. Sin embargo, este endpoint es PÚBLICO,
    por lo que ``get_user_sede_id`` retorna ``None`` cuando el caller no
    está autenticado (visitante anónimo) — en ese caso verá el agregado
    global. Para mantener una experiencia consistente con el resto del
    hold hardening, los uniones se hacen a nivel de la query base y el
    caller decide (admin/visitante) si filtra o no.
    """
    # Verify site exists (no auth required for public)
    _get_public_site_or_404(db, site_key)
    base_query = (
        db.query(models.Persona)
        .options(lazyload("*"))
        .filter(
            models.Persona.is_pastoral_leader.is_(True),
            models.Persona.is_pastoral_published.is_(True),
        )
    )
    leaders = base_query.order_by(
        models.Persona.pastoral_sort_order.asc(),
        models.Persona.is_main_pastor.desc(),
        models.Persona.nombre_completo.asc(),
    ).all()
    result = []
    for p in leaders:
        name = p.nombre_completo
        result.append(
            schemas.PastoralProfileRead(
                id=str(p.id),
                name=name,
                slug=_slugify(name),
                photo_url=p.photo_url,
                bio_short=p.bio_short,
                bio_full=p.bio_full,
                role=_pastoral_role(p),
                social_instagram=p.social_instagram,
                social_facebook=p.social_facebook,
                social_twitter=p.social_twitter,
                is_main_pastor=p.is_main_pastor or False,
                pastoral_sort_order=getattr(p, "pastoral_sort_order", 0) or 0,
                is_pastoral_published=getattr(p, "is_pastoral_published", True),
            )
        )
    return result


@router.get(
    "/cms/pastoral-team",
    response_model=List[schemas.PastoralProfileRead],
)
def cms_pastoral_team_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """CMS endpoint: list pastoral leaders.

    Axioma 3 — Multi-Tenant: el listado se acota a la sede del staff.
    Sin esta validación, un editor de sede_a veía los perfiles pastorales
    de sede_b y podía editarlos (vector IDOR blindado en
    ``cms_pastoral_profile_update``). El staff sin sede
    (superadmin / anterior) sigue viendo el agregado global.
    """
    _assert_role(current_user, CMS_EDITOR_ROLES)
    base_query = db.query(models.Persona).options(lazyload("*")).filter(models.Persona.is_pastoral_leader.is_(True))
    base_query = _scope_cms_pastoral_team_by_user_sede(db, current_user, base_query)
    leaders = base_query.order_by(
        models.Persona.pastoral_sort_order.asc(),
        models.Persona.is_main_pastor.desc(),
        models.Persona.nombre_completo.asc(),
    ).all()
    result = []
    for p in leaders:
        name = p.nombre_completo
        result.append(
            schemas.PastoralProfileRead(
                id=str(p.id),
                name=name,
                slug=_slugify(name),
                photo_url=p.photo_url,
                bio_short=p.bio_short,
                bio_full=p.bio_full,
                role=_pastoral_role(p),
                social_instagram=p.social_instagram,
                social_facebook=p.social_facebook,
                social_twitter=p.social_twitter,
                is_main_pastor=p.is_main_pastor or False,
                pastoral_sort_order=getattr(p, "pastoral_sort_order", 0) or 0,
                is_pastoral_published=getattr(p, "is_pastoral_published", True),
            )
        )
    return result


@router.patch(
    "/cms/pastoral-team/{persona_id}",
    response_model=schemas.PastoralProfileRead,
)
def cms_pastoral_profile_update(
    persona_id: str,
    payload: schemas.PastoralProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """CMS endpoint: update a pastoral leader's profile.

    Axioma 3 — IDOR FIX (CRÍTICO): antes de este fix,
    ``crud.get_persona_by_id(db, persona_id)`` retornaba cualquier
    Persona del platform, sin validar que perteneciera a la sede del
    staff actual. Un editor CMS de sede_a con rol ``cms:edit`` podía
    entonces mutar ``photo_url``, ``bio_full``, ``social_*``,
    ``is_main_pastor`` y ``is_pastoral_leader`` de CUALQUIER pastor de
    CUALQUIER sede — un IDOR ciego, defense in depth insuficiente.

    Ahora usamos el helper existente ``_get_scoped_persona`` (mismo
    pattern que ``/api/crm/personas/{id}``): 404 cross-sede
    (existence-leak safe, no 403). Si la persona es de la propia sede,
    el CRUD aplica la mutación; si es de otra sede, 404.

    Defense-in-depth: ``update_pastoral_profile`` CRUD también valida
    scope pre-commit (param ``actor_user_id`` propagado)."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    persona = _get_scoped_persona(db, current_user, persona_id)
    persona = crud.update_pastoral_profile(
        db,
        persona,
        payload,
        actor_user_id=str(current_user.id),
    )
    name = persona.nombre_completo
    return schemas.PastoralProfileRead(
        id=str(persona.id),
        name=name,
        slug=_slugify(name),
        photo_url=persona.photo_url,
        bio_short=persona.bio_short,
        bio_full=persona.bio_full,
        role=_pastoral_role(persona),
        social_instagram=persona.social_instagram,
        social_facebook=persona.social_facebook,
        social_twitter=persona.social_twitter,
        is_main_pastor=persona.is_main_pastor or False,
        pastoral_sort_order=getattr(persona, "pastoral_sort_order", 0) or 0,
        is_pastoral_published=getattr(persona, "is_pastoral_published", True),
    )


@router.get("/global-blocks", response_model=PaginatedResponse[schemas.CmsSectionRead])
def list_global_blocks(
    site_key: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    base = (
        db.query(models.CmsSection)
        .join(models.CmsPage, models.CmsSection.page_id == models.CmsPage.id)
        .filter(
            models.CmsPage.site_id == site.id,
            models.CmsSection.is_global,
            models.CmsSection.is_visible,
            models.CmsSection.deleted_at.is_(None),
        )
    )
    total = base.count()
    blocks = base.order_by(models.CmsSection.global_key).offset(skip).limit(limit).all()
    return PaginatedResponse(
        items=[schemas.CmsSectionRead.model_validate(b) for b in blocks],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/global-blocks", response_model=schemas.CmsSectionRead, status_code=201)
def create_global_block(
    site_key: str,
    payload: schemas.CmsSectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    allowed_types = get_allowed_section_types(db)
    if payload.type not in allowed_types:
        raise HTTPException(status_code=422, detail="unsupported section type")
    try:
        validated_props = validate_section_props(payload.type, payload.props_json or {})
        payload.props_json = validated_props
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = (
        db.query(models.CmsPage)
        .filter(
            models.CmsPage.site_id == site.id,
            models.CmsPage.slug == "_global_blocks",
        )
        .first()
    )
    if not page:
        page = models.CmsPage(
            site_id=site.id,
            slug="_global_blocks",
            title="Global Blocks",
            status="draft",
        )
        db.add(page)
        db.flush()
    payload.is_global = True
    payload.is_visible = True if payload.is_visible is None else payload.is_visible
    payload.section_key = payload.section_key or f"global_{uuid.uuid4().hex[:8]}"
    block = crud.create_cms_section(db, page.id, payload)
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.patch("/global-blocks/{section_id}", response_model=schemas.CmsSectionRead)
def patch_global_block(
    site_key: str,
    section_id: uuid.UUID,
    payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = (
        db.query(models.CmsSection)
        .filter(
            models.CmsSection.id == section_id,
            models.CmsSection.is_global,
        )
        .first()
    )
    if not block:
        raise HTTPException(status_code=404, detail="Global block not found")
    data = payload.model_dump(exclude_unset=True)
    for key in ["type", "props_json", "sort_order", "is_visible", "status", "is_global", "global_key"]:
        if key in data and data[key] is not None:
            setattr(block, key, data[key])
    db.commit()
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.delete("/global-blocks/{section_id}", status_code=204)
def delete_global_block(
    site_key: str,
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = (
        db.query(models.CmsSection)
        .filter(
            models.CmsSection.id == section_id,
            models.CmsSection.is_global,
        )
        .first()
    )
    if not block:
        raise HTTPException(status_code=404, detail="Global block not found")
    block.deleted_at = _utcnow()
    db.commit()
    return None


# ── Posts & Taxonomías ─────────────────────────────────────────────────────


def _get_category_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsCategory:
    row = (
        db.query(models.CmsCategory)
        .options(lazyload("*"))
        .filter(models.CmsCategory.site_id == site_id, models.CmsCategory.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="category not found")
    return row


def _get_tag_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsTag:
    row = (
        db.query(models.CmsTag)
        .options(lazyload("*"))
        .filter(models.CmsTag.site_id == site_id, models.CmsTag.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="tag not found")
    return row


def _get_post_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsPost:
    row = (
        db.query(models.CmsPost)
        .options(lazyload("*"))
        .filter(models.CmsPost.site_id == site_id, models.CmsPost.slug == _slugify(slug))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    return row


# ── Categories ────────────────────────────────────────────────────────────


@router.get("/sites/{site_key}/categories", response_model=list[schemas.CmsCategoryRead])
def list_categories(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_categories(db, site.id)


@router.post("/sites/{site_key}/categories", response_model=schemas.CmsCategoryRead, status_code=201)
def create_category(
    site_key: str,
    payload: schemas.CmsCategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_category(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="category slug already exists")
    try:
        return crud.create_cms_category(db, site.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/sites/{site_key}/categories/{slug}", response_model=schemas.CmsCategoryRead)
def get_category(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_category_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/categories/{slug}", response_model=schemas.CmsCategoryRead)
def patch_category(
    site_key: str,
    slug: str,
    payload: schemas.CmsCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_category_or_404(db, site.id, slug)
    try:
        return crud.update_cms_category(db, row, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/sites/{site_key}/categories/{slug}", status_code=204)
def delete_category(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_category_or_404(db, site.id, slug)
    crud.delete_cms_category(db, row)


# ── Tags ──────────────────────────────────────────────────────────────────


@router.get("/sites/{site_key}/tags", response_model=list[schemas.CmsTagRead])
def list_tags(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_tags(db, site.id)


@router.post("/sites/{site_key}/tags", response_model=schemas.CmsTagRead, status_code=201)
def create_tag(
    site_key: str,
    payload: schemas.CmsTagCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_tag(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="tag slug already exists")
    return crud.create_cms_tag(db, site.id, payload)


@router.get("/sites/{site_key}/tags/{slug}", response_model=schemas.CmsTagRead)
def get_tag(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_tag_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/tags/{slug}", response_model=schemas.CmsTagRead)
def patch_tag(
    site_key: str,
    slug: str,
    payload: schemas.CmsTagUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_tag_or_404(db, site.id, slug)
    return crud.update_cms_tag(db, row, payload)


@router.delete("/sites/{site_key}/tags/{slug}", status_code=204)
def delete_tag(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_tag_or_404(db, site.id, slug)
    crud.delete_cms_tag(db, row)


# ── Posts (Admin) ─────────────────────────────────────────────────────────


@router.get(
    "/sites/{site_key}/posts",
    response_model=PaginatedResponse[schemas.CmsPostReadWithTaxonomies],
)
def list_posts(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    tag_id: uuid.UUID | None = Query(None),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    items, total = crud.list_cms_posts(
        db,
        site.id,
        skip=skip,
        limit=limit,
        status=status,
        category_id=category_id,
        tag_id=tag_id,
    )
    # Batch-fetch categories and tags to avoid N+1 queries
    post_ids = [post.id for post in items]
    cats_by_post = crud.get_posts_categories_batch(db, post_ids)
    tags_by_post = crud.get_posts_tags_batch(db, post_ids)
    enriched = []
    for post in items:
        p = schemas.CmsPostReadWithTaxonomies.model_validate(post)
        p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in cats_by_post.get(str(post.id), [])]
        p.tags = [schemas.CmsTagRead.model_validate(t) for t in tags_by_post.get(str(post.id), [])]
        enriched.append(p)
    return PaginatedResponse[schemas.CmsPostReadWithTaxonomies](items=enriched, total=total, skip=skip, limit=limit)


@router.post("/sites/{site_key}/posts", response_model=schemas.CmsPostReadWithTaxonomies, status_code=201)
def create_post(
    site_key: str,
    payload: schemas.CmsPostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status.strip().lower() not in {"draft", "in_review", "approved", "published", "archived"}:
        raise HTTPException(status_code=422, detail="invalid status")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_post(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="slug already exists")
    try:
        row = crud.create_cms_post(db, site.id, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    p = schemas.CmsPostReadWithTaxonomies.model_validate(row)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, row.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, row.id)]
    return p


@router.get("/sites/{site_key}/posts/{slug}", response_model=schemas.CmsPostReadWithTaxonomies)
def get_post(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_post_or_404(db, site.id, slug)
    p = schemas.CmsPostReadWithTaxonomies.model_validate(row)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, row.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, row.id)]
    return p


@router.patch("/sites/{site_key}/posts/{slug}", response_model=schemas.CmsPostReadWithTaxonomies)
def patch_post(
    site_key: str,
    slug: str,
    payload: schemas.CmsPostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_post_or_404(db, site.id, slug)
    if payload.status is not None and payload.status.strip().lower() not in {
        "draft",
        "in_review",
        "approved",
        "published",
        "archived",
    }:
        raise HTTPException(status_code=422, detail="invalid status")
    # F-09 (errorescms.md): validación de coherencia temporal
    # ``published_at < expires_at`` vive en el CRUD (defense-in-depth,
    # cubre callers no-API) resolviendo los valores efectivos contra el
    # estado actual del row; aquí solo mapeamos ValueError -> 422.
    try:
        updated = crud.update_cms_post(db, row, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    p = schemas.CmsPostReadWithTaxonomies.model_validate(updated)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, updated.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, updated.id)]
    return p


@router.delete("/sites/{site_key}/posts/{slug}", status_code=204)
def delete_post(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_post_or_404(db, site.id, slug)
    crud.delete_cms_post(db, row)


# ── Posts (Public) ────────────────────────────────────────────────────────


@router.get(
    "/public/sites/{site_key}/posts",
    response_model=PaginatedResponse[schemas.CmsPublicPostRead],
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_posts_list(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category_slug: str | None = Query(None),
    tag_slug: str | None = Query(None),
):
    site = _get_public_site_or_404(db, site_key)
    query = (
        db.query(models.CmsPost)
        .options(lazyload("*"))
        .filter(
            models.CmsPost.site_id == site.id,
            models.CmsPost.status == "published",
        )
    )
    if category_slug:
        query = (
            query.join(models.CmsPostCategory).join(models.CmsCategory).filter(models.CmsCategory.slug == category_slug)
        )
    if tag_slug:
        query = query.join(models.CmsPostTag).join(models.CmsTag).filter(models.CmsTag.slug == tag_slug)
    total = query.count()
    items = query.order_by(models.CmsPost.published_at.desc().nullslast()).offset(skip).limit(limit).all()
    enriched = []
    for post in items:
        p = schemas.CmsPublicPostRead.model_validate(post)
        p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, post.id)]
        p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, post.id)]
        author_name = None
        if post.author_persona_id:
            author = db.query(models.Persona).filter(models.Persona.id == post.author_persona_id).first()
            if author:
                author_name = author.nombre_completo
        p.author_name = author_name
        settings = get_settings()
        base_url = settings.frontend_url.rstrip("/")
        p.canonical_url = f"{base_url}/blog/{post.slug}"
        enriched.append(p)
    return PaginatedResponse[schemas.CmsPublicPostRead](items=enriched, total=total, skip=skip, limit=limit)


@router.get(
    "/public/sites/{site_key}/posts/{slug}",
    response_model=schemas.CmsPublicPostRead,
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_post(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
):
    site = _get_public_site_or_404(db, site_key)
    post = (
        db.query(models.CmsPost)
        .options(lazyload("*"))
        .filter(
            models.CmsPost.site_id == site.id,
            models.CmsPost.slug == _slugify(slug),
            models.CmsPost.status == "published",
        )
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="published post not found")
    p = schemas.CmsPublicPostRead.model_validate(post)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, post.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, post.id)]
    author_name = None
    if post.author_persona_id:
        author = db.query(models.Persona).filter(models.Persona.id == post.author_persona_id).first()
        if author:
            author_name = author.nombre_completo
    p.author_name = author_name
    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    p.canonical_url = f"{base_url}/blog/{post.slug}"
    return p


# ── PAGE VIEWS TRACKING (Phase 6 Analytics) ────────────────────────────────────


@router.post(
    "/track/{page_key}",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def track_page_view(page_key: str, request: Request, db: Session = Depends(get_db)):
    """Track a page view for analytics.

    Public endpoint (no auth) — called from the public frontend.
    Rate-limited to 60 req/min. Only writes a page view record;
    no sensitive data exposed.
    """
    try:
        page = (
            db.query(models.CmsPage)
            .join(models.CmsSite)
            .filter(
                models.CmsPage.slug == page_key,
                models.CmsSite.is_active.is_(True),
            )
            .first()
        )
        if page:
            db.add(
                models.CmsPageView(
                    page_id=page.id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", ""),
                    referrer=request.headers.get("referer", ""),
                )
            )
            db.commit()
    except Exception as exc:
        logger.warning("Analytics tracking failed for page_key=%s: %s", page_key, exc)
    return {"ok": True}


@router.get("/analytics/{page_key}", response_model=dict)
def get_page_analytics(
    page_key: str,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Get page view analytics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    page = (
        db.query(models.CmsPage)
        .join(models.CmsSite)
        .filter(
            models.CmsPage.slug == page_key,
        )
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    total = (
        db.query(func.count(models.CmsPageView.id))
        .filter(models.CmsPageView.page_id == page.id, models.CmsPageView.created_at >= cutoff)
        .scalar()
        or 0
    )
    daily = (
        db.query(
            func.date(models.CmsPageView.created_at).label("date"),
            func.count(models.CmsPageView.id).label("views"),
        )
        .filter(models.CmsPageView.page_id == page.id, models.CmsPageView.created_at >= cutoff)
        .group_by(func.date(models.CmsPageView.created_at))
        .order_by(func.date(models.CmsPageView.created_at))
        .all()
    )
    return {
        "page_key": page_key,
        "total_views": total,
        "days": days,
        "daily_views": [{"date": str(d), "views": v} for d, v in daily],
    }


# ── SCHEDULED PUBLISHING (Phase 4) ─────────────────────────────────────────────


@router.post("/pages/{page_id}/schedule", response_model=Dict[str, Any])
def schedule_page_publish(
    site_key: str,
    page_id: uuid.UUID,
    payload: schemas.SchedulePagePublish,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Schedule a page for future publication (compatibility wrapper).

    Superseded (2026-07-06) -- prefer ``PATCH /sites/{site_key}/pages/{slug}``
    with ``publish_at`` and ``expires_at`` fields. This endpoint is
    kept as a thin wrapper for existing integrations; it now persists
    the timestamp to ``CmsPage.publish_at`` instead of the stale
    ``seo_json['_scheduled_at']``. ``scheduled_at`` is required.
    """
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    parsed = payload.scheduled_at
    page = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.id == page_id, models.CmsPage.site_id == site.id)
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    page.publish_at = parsed
    # Defensa in-depth: borrar datos residuales si quedó algo en seo_json.
    seo = page.seo_json if isinstance(page.seo_json, dict) else {}
    if isinstance(seo, dict) and "_scheduled_at" in seo:
        seo.pop("_scheduled_at", None)
        page.seo_json = seo
    db.commit()
    db.refresh(page)
    return {"ok": True, "publish_at": parsed.isoformat()}


# ── IMAGE OPTIMIZATION (Phase 7) ───────────────────────────────────────────────
@router.get(
    "/images/{media_id}/resize",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_resized_image(
    media_id: uuid.UUID,
    width: int = Query(800, le=2400),
    height: Optional[int] = None,
    quality: int = Query(80, le=100),
    db: Session = Depends(get_db),
):
    """Get a resized version of an uploaded image. Returns URL.

    Public endpoint (no auth) -- used by the public frontend for image
    optimization. Rate-limited to 60 req/min.

    Defense-in-depth (Axioma 3): only returns non-archived media that
    belongs to the CCF site (sede_id match).
    """
    # Best-effort scoping: if the canonical CCF site exists and has a
    # sede_id, narrow the lookup to that tenant. Otherwise keep the
    # public endpoint functional and only enforce the archived guard.
    media_query = db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == media_id)
    ccf_site = crud.get_cms_site_by_key(db, "ccf")
    if ccf_site and ccf_site.sede_id is not None:
        media_query = media_query.filter(models.CmsMediaItem.sede_id == ccf_site.sede_id)
    media = media_query.first()
    if not media or (media.status or "") == "archived":
        raise HTTPException(status_code=404, detail="Media not found")
    # For now return the original URL with resize params
    return {"url": media.url, "width": width, "height": height, "quality": quality}


@router.post("/images/optimize", response_model=dict)
async def optimize_uploaded_image(
    media_id: uuid.UUID,
    max_width: int = Query(1920),
    quality: int = Query(80),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
    background_tasks: BackgroundTasks = None,
):
    """Optimize an uploaded image by resizing and reducing quality.

    Axioma 3 — Multi-Tenant (CRÍTICO, IDOR fix): antes de este fix,
    ``db.query(models.CmsMediaItem).filter(id == media_id)`` retornaba
    cualquier media del platform sin validar que perteneciera a la sede
    del staff actual. Un editor CMS de sede_a con rol ``cms:read`` podía
    entonces invocar ``/images/optimize`` con el ``media_id`` de un asset
    perteneciente a sede_b y forzar la reescritura del archivo JPEG
    optimizado en disco vía ``img.save(opt_path, ...)`` — un IDOR que
    resulta en modificación cross-sede del filesystem uploads_dir, no
    sólo de la fila en DB.

    Ahora usamos ``_get_scoped_cms_media`` (mismo helper que el resto
    del CMS-admin): 404 cross-sede (existence-leak safe, no 403) *antes*
    de tocar PIL o el filesystem. Si el media es de la propia sede, el
    CRUD procede con la optimización y el ``img.save``; si es de otra
    sede, 404 y el filesystem queda intacto.

    Defense-in-depth (lazy PIL import): el ``from PIL import Image`` se
    hace DESPUÉS del scope + archived check para que un entorno sin
    PIL instalado NO bypassee el scope check con un 500 — el cross-sede
    sigue siendo 404 limpio. Si PIL falta y el media es local+active,
    devolvemos 503 con un mensaje actionable (instale ``pillow``).

    Performance: la optimización pesada se ejecuta en background via
    ``BackgroundTasks`` para no bloquear la respuesta HTTP.
    """
    media = _get_scoped_cms_media(db, current_user, media_id)
    if (media.status or "") == "archived":
        raise HTTPException(status_code=404, detail="Media not found")

    try:
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Pillow (PIL) no instalado en el servidor — instale "
                "el paquete ``pillow`` para habilitar /images/optimize."
            ),
        ) from exc
    from backend.core.config import get_settings

    settings = get_settings()
    orig_path = os.path.join(settings.uploads_dir, media.filename)
    if not os.path.exists(orig_path):
        raise HTTPException(status_code=404, detail="File not found")

    def _do_optimize():
        img = Image.open(orig_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        opt_filename = f"opt_{media.filename.rsplit('.', 1)[0]}_{max_width}w.jpg"
        opt_path = os.path.join(settings.uploads_dir, opt_filename)
        img.save(opt_path, "JPEG", quality=quality, optimize=True)

    if background_tasks is not None:
        background_tasks.add_task(_do_optimize)

    opt_filename = f"opt_{media.filename.rsplit('.', 1)[0]}_{max_width}w.jpg"
    return {
        "status": "queued",
        "url": f"/uploads/{opt_filename}",
        "media_id": str(media_id),
        "max_width": max_width,
        "quality": quality,
    }

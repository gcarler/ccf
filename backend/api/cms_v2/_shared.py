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

import logging
import re
import unicodedata
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, lazyload

from backend import crud, models, schemas
from backend.core.permissions import normalize_role

logger = logging.getLogger(__name__)


# ── Role constants ──────────────────────────────────────────────────────────

CMS_EDITOR_ROLES = {"admin", "coordinador", "docente", "pastor"}
CMS_PUBLISHER_ROLES = {"admin", "coordinador", "pastor"}


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
    """
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Only swallow unique-key violations (Postgres 23505 / SQLite
        # "UNIQUE constraint failed"). Everything else is a genuine bug
        # that should not be masked as a conflict.
        is_unique_violation = False
        orig = getattr(exc, "orig", None)
        if orig is not None:
            pgcode = getattr(orig, "pgcode", None)
            if pgcode == "23505":
                is_unique_violation = True
            # SQLite exposes unique violations via IntegrityError message
            elif "UNIQUE constraint failed" in str(orig):
                is_unique_violation = True
        if not is_unique_violation:
            raise
        logger.debug("Swallowed concurrent create unique-key conflict: %s", exc)
        raise HTTPException(status_code=409, detail=detail)


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
        raise HTTPException(status_code=403, detail=detail)


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

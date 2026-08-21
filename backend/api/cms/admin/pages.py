"""Pages, sections, versions, preview and readiness admin endpoints (Fase 4 refactor)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms.section_types import get_allowed_section_types
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    _assert_role,
    _build_section_defaults,
    _get_page_or_404,
    _get_scoped_site_or_404,
    _get_system_var,
    _slugify,
)
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.seo import (
    auto_json_ld_for_page,
    build_breadcrumb_items_from_slug,
    build_breadcrumb_list_json_ld,
)
from backend.exceptions.cms import (
    CmsValidationError,
    DraftRequiredError,
    InvalidSlugError,
    SectionConflictError,
    SectionNotFoundError,
    SlugConflictError,
    SlugMismatchError,
    UnsupportedSectionStatusError,
    UnsupportedSectionTypeError,
)
from backend.schemas import cms as cms_schemas
from backend.schemas._common import PaginatedResponse
from backend.schemas.cms_v2_sections import validate_section_props
from backend.services.cms_search_indexer import delete_from_search_index, index_cms_page
from backend.services.cms_workflow import PageWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_pages"])


def _sanitize_audit_changes(obj: Any) -> Any:
    """Convert non-JSON-serializable values (datetime, UUID, etc.) to strings."""
    from datetime import date
    from uuid import UUID

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_audit_changes(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_audit_changes(v) for v in obj]
    return obj


def _log_cms_audit(
    db: Session,
    user: models.User,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    entity_slug: str | None = None,
    site_key: str | None = None,
    changes: dict | None = None,
):
    try:
        log_entry = models.AuditLog(
            actor_persona_id=getattr(user, "persona_id", None) or getattr(user, "id", None),
            actor_email=getattr(user, "email", None),
            actor_role=getattr(user, "role", None),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_slug=entity_slug,
            site_key=site_key,
            changes_json=_sanitize_audit_changes(changes) if changes else {},
        )
        db.add(log_entry)
        db.flush()
    except Exception as exc:
        logger.warning("CMS Audit logging failed: %s", exc)
        # Rollback the failed audit insert so the session stays usable
        # for the caller's own commit (the audit is best-effort).
        try:
            db.rollback()
        except Exception:
            pass


# ── Pages CRUD ───────────────────────────────────────────────────────────────


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
        raise DraftRequiredError()
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise InvalidSlugError()
    if crud.get_cms_page(db, site.id, payload.slug):
        raise SlugConflictError()
    row = crud.create_cms_page(db, site.id, payload, current_user.id, commit_with_conflict_check=True)
    if row is None:
        raise SlugConflictError()
    _log_cms_audit(db, current_user, "page.create", "cms_page", str(row.id), row.slug, site_key)
    index_cms_page(db, row)
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
        raise CmsValidationError("Use workflow endpoint to change status", error_code="status_via_workflow")
    if payload.publish_at is not None and payload.expires_at is not None and payload.expires_at < payload.publish_at:
        raise CmsValidationError("expires_at must be >= publish_at", error_code="invalid_expires_at")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_page_or_404(db, site.id, slug)
    updated = crud.update_cms_page(db, row, payload, current_user.id)
    if payload.publish_at is not None:
        wf = PageWorkflowService(db)
        updated = wf.apply_schedule(updated, publish_at=payload.publish_at, user_id=current_user.id)
    _log_cms_audit(db, current_user, "page.update", "cms_page", str(updated.id), updated.slug, site_key, payload.model_dump(exclude_unset=True))
    index_cms_page(db, updated)
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
    page_id_str = str(row.id)
    crud.delete_cms_page(db, row)
    _log_cms_audit(db, current_user, "page.delete", "cms_page", page_id_str, slug, site_key)
    delete_from_search_index(db, site_key, "page", page_id_str)


@router.post("/sites/{site_key}/pages/{slug}/clone", response_model=schemas.CmsPageRead, status_code=201)
def clone_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsPageClone,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    source = _get_page_or_404(db, site.id, slug)
    new_slug = _slugify(payload.new_slug)
    if not new_slug:
        raise InvalidSlugError("New slug is required")
    if new_slug == source.slug:
        raise SlugMismatchError()
    if crud.get_cms_page(db, site.id, new_slug):
        raise SlugConflictError()
    cloned = crud.clone_cms_page(db, source, new_slug, current_user.id, new_title=payload.new_title)
    if cloned is None:
        raise SlugConflictError()
    _log_cms_audit(db, current_user, "page.clone", "cms_page", str(cloned.id), cloned.slug, site_key, {"source_slug": slug})
    index_cms_page(db, cloned)
    return cloned


# ── Sections CRUD ────────────────────────────────────────────────────────────


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


@router.post("/sites/{site_key}/pages/{slug}/sections", response_model=schemas.CmsSectionRead, status_code=201)
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
        raise UnsupportedSectionTypeError()
    try:
        validated_props = validate_section_props(payload.type, payload.props_json or {})
        payload.props_json = validated_props
    except ValueError as e:
        raise CmsValidationError(str(e))
    payload.status = (payload.status or "active").strip().lower()
    if payload.status not in {"active", "archived"}:
        raise UnsupportedSectionStatusError()
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.create_cms_section(db, page.id, payload, user_id=current_user.id, commit_with_conflict_check=True)
    if row is None:
        raise SectionConflictError()
    _log_cms_audit(db, current_user, "section.create", "cms_section", str(row.id), slug, site_key, {"type": row.type, "sort_order": row.sort_order})
    index_cms_page(db, page)
    return row


@router.patch("/sites/{site_key}/pages/{slug}/sections/{section_id}", response_model=schemas.CmsSectionRead)
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
        raise UnsupportedSectionTypeError()
    if payload.status is not None:
        payload.status = payload.status.strip().lower()
        if payload.status not in {"active", "archived"}:
            raise UnsupportedSectionStatusError()
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id, site_id=site.id)
    if not row:
        raise SectionNotFoundError()
    if payload.props_json is not None:
        effective_type = (payload.type or row.type or "").strip().lower() or "rich_text"
        try:
            payload.props_json = validate_section_props(effective_type, payload.props_json)
        except ValueError as exc:
            raise CmsValidationError(str(exc)) from exc
    res = crud.update_cms_section(db, row, payload, user_id=current_user.id)
    _log_cms_audit(db, current_user, "section.update", "cms_section", str(res.id), slug, site_key, payload.model_dump(exclude_unset=True))
    index_cms_page(db, page)
    return res


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
        raise SectionNotFoundError()
    crud.archive_cms_section(db, row)
    _log_cms_audit(db, current_user, "section.delete", "cms_section", str(section_id), slug, site_key)
    index_cms_page(db, page)


@router.post("/sites/{site_key}/pages/{slug}/sections/reorder", response_model=list[schemas.CmsSectionRead])
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
    reordered = crud.reorder_cms_sections(db, page.id, payload.items)
    _log_cms_audit(db, current_user, "section.reorder", "cms_section", None, slug, site_key, {"count": len(reordered)})
    index_cms_page(db, page)
    return reordered


# ── Versions & Publish Log ───────────────────────────────────────────────────


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


# ── CMS Readiness ────────────────────────────────────────────────────────────


def _cms_readiness_issue(
    *, code: str, severity: str, title: str, detail: str, count: int, href: str | None = None
) -> cms_schemas.CmsReadinessIssue:
    return cms_schemas.CmsReadinessIssue(
        code=code, severity=severity, title=title, detail=detail, count=count, href=href
    )


@router.get("/sites/{site_key}/readiness", response_model=cms_schemas.CmsReadinessResponse)
def cms_readiness(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)

    page_base = db.query(models.CmsPage).filter(models.CmsPage.site_id == site.id)
    total_pages = page_base.count()
    published_pages = page_base.filter(models.CmsPage.status == "published").count()
    draft_pages = page_base.filter(models.CmsPage.status == "draft").count()
    in_review_pages = page_base.filter(models.CmsPage.status == "in_review").count()
    archived_pages = page_base.filter(models.CmsPage.status == "archived").count()
    scheduled_without_date = page_base.filter(
        models.CmsPage.status == "scheduled", models.CmsPage.publish_at.is_(None)
    ).count()
    published_without_version = page_base.filter(
        models.CmsPage.status == "published", models.CmsPage.published_version_id.is_(None)
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
        models.CmsSection.deleted_at.is_(None), ~models.CmsSection.type.in_(allowed_section_types)
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
                detail="Hay páginas en estado scheduled sin publish_at, por lo que no podrán publicarse automáticamente.",
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
            status="ready" if media_total and not media_without_alt else ("partial" if media_total else "attention"),
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
            status="ready" if recent_publish_events or active_redirects or unresolved_broken_links == 0 else "partial",
            detail=f"{recent_publish_events} eventos, {active_redirects} redirects, {unresolved_broken_links} links rotos.",
            href="/cms/audit",
        ),
    ]

    metrics = [
        cms_schemas.CmsReadinessMetric(key="total_pages", label="Páginas", value=total_pages, href="/cms/pages"),
        cms_schemas.CmsReadinessMetric(
            key="published_pages", label="Publicadas", value=published_pages, href="/cms/pages"
        ),
        cms_schemas.CmsReadinessMetric(key="draft_pages", label="Borradores", value=draft_pages, href="/cms/pages"),
        cms_schemas.CmsReadinessMetric(
            key="in_review_pages", label="En revisión", value=in_review_pages, href="/cms/pages"
        ),
        cms_schemas.CmsReadinessMetric(
            key="archived_pages", label="Archivadas", value=archived_pages, href="/cms/pages"
        ),
        cms_schemas.CmsReadinessMetric(
            key="visible_sections", label="Secciones visibles", value=visible_sections, href="/cms/builder"
        ),
        cms_schemas.CmsReadinessMetric(
            key="hidden_sections", label="Secciones ocultas", value=hidden_sections, href="/cms/builder"
        ),
        cms_schemas.CmsReadinessMetric(key="media_total", label="Media activa", value=media_total, href="/cms/media"),
        cms_schemas.CmsReadinessMetric(
            key="active_menus", label="Menús activos", value=active_menus, href="/cms/menus"
        ),
        cms_schemas.CmsReadinessMetric(
            key="active_themes", label="Temas activos", value=active_themes, href="/cms/themes"
        ),
        cms_schemas.CmsReadinessMetric(
            key="broken_links", label="Links rotos", value=unresolved_broken_links, href="/cms/broken-links"
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


# ── Preview ──────────────────────────────────────────────────────────────────


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
    if isinstance(page.seo_json, dict) and page.seo_json.get("json_ld"):
        json_ld_data = page.seo_json["json_ld"]
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

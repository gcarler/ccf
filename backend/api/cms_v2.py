from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import normalize_role, require_module_access
from backend.core.database import get_db

router = APIRouter(prefix="/cms/v2", tags=["cms_v2"])

ALLOWED_SECTION_TYPES = {
    # Existing 19
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
    # New 11
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
}
CMS_EDITOR_ROLES = {"admin", "coordinador", "docente", "pastor"}
CMS_PUBLISHER_ROLES = {"admin", "coordinador", "pastor"}


def _assert_role(
    user: models.User, allowed_roles: set[str], detail: str = "Not enough permissions"
) -> None:
    role = normalize_role(getattr(user, "role", ""))
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail=detail)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-_/]", "", value)
    return value.strip("-")


def _get_site_or_404(db: Session, site_key: str) -> models.CmsSite:
    row = crud.get_cms_site_by_key(db, site_key.strip().lower())
    if not row:
        raise HTTPException(status_code=404, detail="site not found")
    return row


def _get_public_site_or_404(db: Session, site_key: str) -> models.CmsSite:
    row = _get_site_or_404(db, site_key)
    if not row.is_active:
        raise HTTPException(status_code=404, detail="site not found")
    return row


def _get_menu_or_404(db: Session, site_id: int, menu_key: str) -> models.CmsMenu:
    row = crud.get_cms_menu(db, site_id, menu_key.strip().lower())
    if not row:
        raise HTTPException(status_code=404, detail="menu not found")
    return row


def _get_page_or_404(db: Session, site_id: int, slug: str) -> models.CmsPage:
    row = crud.get_cms_page(db, site_id, _slugify(slug))
    if not row:
        raise HTTPException(status_code=404, detail="page not found")
    return row


def _snapshot_section_read(
    section_data: dict[str, Any],
    *,
    page_id: int,
    index: int,
    timestamp: datetime,
) -> schemas.CmsSectionRead:
    section_id = section_data.get("id")
    sort_order = section_data.get("sort_order")
    props_json = section_data.get("props_json")
    return schemas.CmsSectionRead(
        id=section_id if isinstance(section_id, int) else index + 1,
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
    _: models.User = Depends(require_module_access("cms", "read")),
):
    return crud.list_cms_sites(db, only_active=only_active)


@router.post("/sites", response_model=schemas.CmsSiteRead, status_code=201)
def create_site(
    payload: schemas.CmsSiteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    if not payload.site_key.strip():
        raise HTTPException(status_code=422, detail="site_key is required")
    if not payload.base_path.strip().startswith("/"):
        raise HTTPException(status_code=422, detail="base_path must start with '/'")
    if crud.get_cms_site_by_key(db, payload.site_key.strip().lower()):
        raise HTTPException(status_code=409, detail="site_key already exists")
    return crud.create_cms_site(db, payload)


@router.get("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def get_site(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    return _get_site_or_404(db, site_key)


@router.patch("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def patch_site(
    site_key: str,
    payload: schemas.CmsSiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_site_or_404(db, site_key)
    return crud.update_cms_site(db, row, payload)


@router.delete("/sites/{site_key}", status_code=204)
def delete_site(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Desactiva un sitio CMS sin eliminar su contenido."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_site_or_404(db, site_key)
    crud.archive_cms_site(db, row)
    return None


@router.get("/sites/{site_key}/themes", response_model=list[schemas.CmsThemeRead])
def list_themes(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_themes(db, site.id)


@router.post(
    "/sites/{site_key}/themes", response_model=schemas.CmsThemeRead, status_code=201
)
def create_theme(
    site_key: str,
    payload: schemas.CmsThemeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(
            current_user,
            CMS_PUBLISHER_ROLES,
            detail="Only publishers can activate a theme",
        )
    site = _get_site_or_404(db, site_key)
    return crud.create_cms_theme(db, site.id, payload, created_by=current_user.id)


@router.patch(
    "/sites/{site_key}/themes/{theme_id}", response_model=schemas.CmsThemeRead
)
def patch_theme(
    site_key: str,
    theme_id: int,
    payload: schemas.CmsThemeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(
            current_user,
            CMS_PUBLISHER_ROLES,
            detail="Only publishers can activate a theme",
        )
    site = _get_site_or_404(db, site_key)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return crud.update_cms_theme(db, row, payload)


@router.post(
    "/sites/{site_key}/themes/{theme_id}/activate", response_model=schemas.CmsThemeRead
)
def activate_theme(
    site_key: str,
    theme_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
    row = crud.activate_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return row


@router.delete("/sites/{site_key}/themes/{theme_id}", status_code=204)
def delete_theme(
    site_key: str,
    theme_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Archiva un tema CMS sin eliminar su historial."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    crud.archive_cms_theme(db, row)
    return None


@router.get("/sites/{site_key}/menus", response_model=list[schemas.CmsMenuRead])
def list_menus(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_menus(db, site.id)


@router.post(
    "/sites/{site_key}/menus", response_model=schemas.CmsMenuRead, status_code=201
)
def create_menu(
    site_key: str,
    payload: schemas.CmsMenuCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    if crud.get_cms_menu(db, site.id, payload.menu_key.strip().lower()):
        raise HTTPException(status_code=409, detail="menu_key already exists")
    return crud.create_cms_menu(db, site.id, payload)


@router.get("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def get_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return _get_menu_or_404(db, site.id, menu_key)


@router.patch("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def patch_menu(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    row = _get_menu_or_404(db, site.id, menu_key)
    return crud.update_cms_menu(db, row, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}", status_code=204)
def delete_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Desactiva un menu CMS sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
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
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
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
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.create_cms_menu_item(db, menu.id, payload)


@router.patch(
    "/sites/{site_key}/menus/{menu_key}/items/{item_id}",
    response_model=schemas.CmsMenuItemRead,
)
def patch_menu_item(
    site_key: str,
    menu_key: str,
    item_id: int,
    payload: schemas.CmsMenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="menu item not found")
    return crud.update_cms_menu_item(db, item, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}/items/{item_id}", status_code=204)
def delete_menu_item(
    site_key: str,
    menu_key: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Oculta un item de menu sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id)
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
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.reorder_cms_menu_items(db, menu.id, payload.items)


@router.get("/sites/{site_key}/pages", response_model=list[schemas.CmsPageRead])
def list_pages(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_pages(db, site.id)


@router.post(
    "/sites/{site_key}/pages", response_model=schemas.CmsPageRead, status_code=201
)
def create_page(
    site_key: str,
    payload: schemas.CmsPageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status.strip().lower() != "draft":
        raise HTTPException(status_code=422, detail="new pages must start in draft")
    site = _get_site_or_404(db, site_key)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_page(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="slug already exists")
    return crud.create_cms_page(db, site.id, payload, current_user.id)


@router.get("/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPageRead)
def get_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return _get_page_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPageRead)
def patch_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsPageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status is not None:
        raise HTTPException(
            status_code=422, detail="use workflow endpoint to change status"
        )
    site = _get_site_or_404(db, site_key)
    row = _get_page_or_404(db, site.id, slug)
    return crud.update_cms_page(db, row, payload, current_user.id)


@router.delete("/sites/{site_key}/pages/{slug}", status_code=204)
def delete_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    row = _get_page_or_404(db, site.id, slug)
    crud.delete_cms_page(db, row)


@router.get(
    "/sites/{site_key}/pages/{slug}/sections",
    response_model=list[schemas.CmsSectionRead],
)
def list_sections(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.list_cms_sections(db, page.id)


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
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.type not in ALLOWED_SECTION_TYPES:
        raise HTTPException(status_code=422, detail="unsupported section type")
    # Validate props against section type schema
    from backend.schemas.cms_v2_sections import validate_section_props
    try:
        props = payload.props_json or {}
        validated_props = validate_section_props(payload.type, props)
        payload.props_json = validated_props
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    payload.status = (payload.status or "active").strip().lower()
    if payload.status not in {"active", "archived"}:
        raise HTTPException(status_code=422, detail="unsupported section status")
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.create_cms_section(db, page.id, payload)


@router.patch(
    "/sites/{site_key}/pages/{slug}/sections/{section_id}",
    response_model=schemas.CmsSectionRead,
)
def patch_section(
    site_key: str,
    slug: str,
    section_id: int,
    payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.type is not None and payload.type not in ALLOWED_SECTION_TYPES:
        raise HTTPException(status_code=422, detail="unsupported section type")
    if payload.status is not None:
        payload.status = payload.status.strip().lower()
        if payload.status not in {"active", "archived"}:
            raise HTTPException(status_code=422, detail="unsupported section status")
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id)
    if not row:
        raise HTTPException(status_code=404, detail="section not found")
    return crud.update_cms_section(db, row, payload)


@router.delete("/sites/{site_key}/pages/{slug}/sections/{section_id}", status_code=204)
def delete_section(
    site_key: str,
    slug: str,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id)
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
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.reorder_cms_sections(db, page.id, payload.items)


@router.get(
    "/sites/{site_key}/pages/{slug}/versions",
    response_model=list[schemas.CmsPageVersionRead],
)
def list_versions(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.list_cms_page_versions(db, page.id)


@router.get(
    "/sites/{site_key}/pages/{slug}/publish-log",
    response_model=list[schemas.CmsPublishLogRead],
)
def list_publish_log(
    site_key: str,
    slug: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.list_cms_publish_logs(db, site.id, page_id=page.id, limit=limit)


@router.get(
    "/sites/{site_key}/pages/{slug}/preview", response_model=schemas.CmsPublicPageRead
)
def preview_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    sections = [
        section
        for section in crud.list_cms_sections(db, page.id)
        if section.is_visible and getattr(section, "status", "active") != "archived"
    ]
    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=[
            schemas.CmsSectionRead.model_validate(section) for section in sections
        ],
    )


@router.post(
    "/sites/{site_key}/pages/{slug}/rollback/{version_id}",
    response_model=schemas.CmsPageRead,
)
def rollback_page(
    site_key: str,
    slug: str,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    version = crud.get_cms_page_version(db, page.id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="version not found")
    return crud.restore_cms_page_version(db, page, version, user_id=current_user.id)


@router.post(
    "/sites/{site_key}/pages/{slug}/workflow", response_model=schemas.CmsPageRead
)
def workflow_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsWorkflowAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    action = payload.action.strip().lower()
    if action in {"approve", "publish", "archive"}:
        _assert_role(current_user, CMS_PUBLISHER_ROLES)
    else:
        _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.transition_cms_page_status(
        db, page, payload.action, current_user.id, notes=payload.notes
    )
    if not row:
        raise HTTPException(status_code=422, detail="invalid workflow action")
    return row


@router.get("/public/sites/{site_key}/theme", response_model=schemas.CmsThemeRead)
def public_theme(site_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    row = crud.get_active_cms_theme(db, site.id)
    if not row:
        raise HTTPException(status_code=404, detail="active theme not found")
    return row


@router.get("/public/sites/{site_key}/menus/{menu_key}")
def public_menu(site_key: str, menu_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    if not menu.is_active:
        raise HTTPException(status_code=404, detail="menu not found")
    items = [
        item
        for item in crud.list_cms_menu_items(db, menu.id)
        if item.visibility == "public"
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


@router.get(
    "/public/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPublicPageRead
)
def public_page(site_key: str, slug: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    page = crud.get_public_cms_page(db, site.id, _slugify(slug))
    if not page:
        raise HTTPException(status_code=404, detail="published page not found")
    published_version = None
    if page.published_version_id:
        published_version = crud.get_cms_page_version(
            db, page.id, page.published_version_id
        )

    if published_version:
        snapshot = published_version.snapshot_json or {}
        page_snapshot = snapshot.get("page") if isinstance(snapshot, dict) else {}
        sections_snapshot = (
            snapshot.get("sections") if isinstance(snapshot, dict) else []
        )
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
                    key=lambda item: (
                        item.get("sort_order")
                        if isinstance(item.get("sort_order"), int)
                        else 0
                    ),
                )
            )
            if section_data.get("is_visible", True) is not False
            and section_data.get("status", "active") != "archived"
        ]
        return schemas.CmsPublicPageRead(
            site_key=site.site_key,
            slug=(
                str(page_snapshot.get("slug") or page.slug)
                if isinstance(page_snapshot, dict)
                else page.slug
            ),
            title=(
                str(page_snapshot.get("title") or page.title)
                if isinstance(page_snapshot, dict)
                else page.title
            ),
            seo_json=(
                page_snapshot.get("seo_json")
                if isinstance(page_snapshot, dict)
                and isinstance(page_snapshot.get("seo_json"), dict)
                else {}
            ),
            sections=section_rows,
        )

    sections = [
        section
        for section in crud.list_cms_sections(db, page.id)
        if section.is_visible and getattr(section, "status", "active") != "archived"
    ]
    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=[
            schemas.CmsSectionRead.model_validate(section) for section in sections
        ],
    )


# ── GLOBAL BLOCKS (Phase 3) ────────────────────────────────────────────────────

@router.get("/global-blocks", response_model=List[schemas.CmsSectionRead])
def list_global_blocks(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    blocks = (
        db.query(models.CmsSection)
        .join(models.CmsPage, models.CmsSection.page_id == models.CmsPage.id)
        .filter(
            models.CmsPage.site_id == site.id,
            models.CmsSection.is_global == True,
            models.CmsSection.is_visible == True,
        )
        .order_by(models.CmsSection.global_key)
        .all()
    )
    return [schemas.CmsSectionRead.model_validate(b) for b in blocks]


@router.post("/global-blocks", response_model=schemas.CmsSectionRead, status_code=201)
def create_global_block(
    site_key: str,
    payload: schemas.CmsSectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.type not in ALLOWED_SECTION_TYPES:
        raise HTTPException(status_code=422, detail="unsupported section type")
    from backend.schemas.cms_v2_sections import validate_section_props
    try:
        validated_props = validate_section_props(payload.type, payload.props_json or {})
        payload.props_json = validated_props
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    site = _get_site_or_404(db, site_key)
    page = db.query(models.CmsPage).filter(
        models.CmsPage.site_id == site.id,
        models.CmsPage.slug == "_global_blocks",
    ).first()
    if not page:
        page = models.CmsPage(
            site_id=site.id, slug="_global_blocks", title="Global Blocks", status="draft",
        )
        db.add(page)
        db.flush()
    payload.is_global = True
    payload.section_key = payload.section_key or f"global_{uuid.uuid4().hex[:8]}"
    block = crud.create_cms_section(db, page.id, payload)
    db.commit()
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.patch("/global-blocks/{section_id}", response_model=schemas.CmsSectionRead)
def patch_global_block(
    site_key: str, section_id: int, payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = db.query(models.CmsSection).filter(
        models.CmsSection.id == section_id, models.CmsSection.is_global == True,
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Global block not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if hasattr(block, key):
            setattr(block, key, value)
    db.commit()
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.delete("/global-blocks/{section_id}", response_model=dict)
def delete_global_block(
    site_key: str, section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = db.query(models.CmsSection).filter(
        models.CmsSection.id == section_id, models.CmsSection.is_global == True,
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Global block not found")
    db.delete(block)
    db.commit()
    return {"ok": True, "deleted": section_id}


# ── PAGE VIEWS TRACKING (Phase 6 Analytics) ────────────────────────────────────

@router.post("/track/{page_key}", response_model=dict)
def track_page_view(page_key: str, request: Request, db: Session = Depends(get_db)):
    """Track a page view for analytics."""
    try:
        page = db.query(models.CmsPage).join(models.CmsSite).filter(
            models.CmsPage.slug == page_key,
        ).first()
        if page:
            db.add(models.CmsPageView(
                page_id=page.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", ""),
                referrer=request.headers.get("referer", ""),
            ))
            db.commit()
    except Exception:
        pass
    return {"ok": True}


@router.get("/analytics/{page_key}", response_model=dict)
def get_page_analytics(
    page_key: str, days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Get page view analytics."""
    from datetime import timedelta
    from sqlalchemy import func
    cutoff = datetime.utcnow() - timedelta(days=days)
    page = db.query(models.CmsPage).join(models.CmsSite).filter(
        models.CmsPage.slug == page_key,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    total = (
        db.query(func.count(models.CmsPageView.id))
        .filter(models.CmsPageView.page_id == page.id, models.CmsPageView.created_at >= cutoff)
        .scalar() or 0
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
    return {"page_key": page_key, "total_views": total, "days": days,
            "daily_views": [{"date": str(d), "views": v} for d, v in daily]}


# ── SCHEDULED PUBLISHING (Phase 4) ─────────────────────────────────────────────

@router.post("/pages/{page_id}/schedule", response_model=dict)
def schedule_page_publish(
    site_key: str, page_id: int, payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Schedule a page for future publication."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    scheduled_at = payload.get("scheduled_at")
    if not scheduled_at:
        raise HTTPException(status_code=400, detail="scheduled_at is required")
    try:
        dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    page = db.query(models.CmsPage).filter(models.CmsPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    page.status = "scheduled"
    seo = page.seo_json or {}
    seo["_scheduled_at"] = scheduled_at
    page.seo_json = seo
    db.commit()
    return {"ok": True, "scheduled_at": scheduled_at}

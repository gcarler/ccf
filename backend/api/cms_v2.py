from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import normalize_role, require_active_user
from backend.core.database import get_db


router = APIRouter(prefix="/cms/v2", tags=["cms_v2"])

ALLOWED_SECTION_TYPES = {"hero", "rich_text", "cards", "cta_banner", "gallery", "faq", "embed"}
CMS_EDITOR_ROLES = {"admin", "coordinador", "docente", "pastor"}
CMS_PUBLISHER_ROLES = {"admin", "coordinador", "pastor"}


def _assert_role(user: models.User, allowed_roles: set[str], detail: str = "Not enough permissions") -> None:
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


@router.get("/sites", response_model=list[schemas.CmsSiteRead])
def list_sites(
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_cms_sites(db, only_active=only_active)


@router.post("/sites", response_model=schemas.CmsSiteRead, status_code=201)
def create_site(
    payload: schemas.CmsSiteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
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
    _: models.User = Depends(require_active_user),
):
    return _get_site_or_404(db, site_key)


@router.patch("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def patch_site(
    site_key: str,
    payload: schemas.CmsSiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_site_or_404(db, site_key)
    return crud.update_cms_site(db, row, payload)


@router.get("/sites/{site_key}/themes", response_model=list[schemas.CmsThemeRead])
def list_themes(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_themes(db, site.id)


@router.post("/sites/{site_key}/themes", response_model=schemas.CmsThemeRead, status_code=201)
def create_theme(
    site_key: str,
    payload: schemas.CmsThemeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(current_user, CMS_PUBLISHER_ROLES, detail="Only publishers can activate a theme")
    site = _get_site_or_404(db, site_key)
    return crud.create_cms_theme(db, site.id, payload, created_by=current_user.id)


@router.patch("/sites/{site_key}/themes/{theme_id}", response_model=schemas.CmsThemeRead)
def patch_theme(
    site_key: str,
    theme_id: int,
    payload: schemas.CmsThemeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(current_user, CMS_PUBLISHER_ROLES, detail="Only publishers can activate a theme")
    site = _get_site_or_404(db, site_key)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return crud.update_cms_theme(db, row, payload)


@router.post("/sites/{site_key}/themes/{theme_id}/activate", response_model=schemas.CmsThemeRead)
def activate_theme(
    site_key: str,
    theme_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
    row = crud.activate_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return row


@router.get("/sites/{site_key}/menus", response_model=list[schemas.CmsMenuRead])
def list_menus(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_menus(db, site.id)


@router.post("/sites/{site_key}/menus", response_model=schemas.CmsMenuRead, status_code=201)
def create_menu(
    site_key: str,
    payload: schemas.CmsMenuCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
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
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    return _get_menu_or_404(db, site.id, menu_key)


@router.patch("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def patch_menu(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
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
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    row = _get_menu_or_404(db, site.id, menu_key)
    crud.delete_cms_menu(db, row)


@router.get("/sites/{site_key}/menus/{menu_key}/items", response_model=list[schemas.CmsMenuItemRead])
def list_menu_items(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.list_cms_menu_items(db, menu.id)


@router.post("/sites/{site_key}/menus/{menu_key}/items", response_model=schemas.CmsMenuItemRead, status_code=201)
def create_menu_item(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.create_cms_menu_item(db, menu.id, payload)


@router.patch("/sites/{site_key}/menus/{menu_key}/items/{item_id}", response_model=schemas.CmsMenuItemRead)
def patch_menu_item(
    site_key: str,
    menu_key: str,
    item_id: int,
    payload: schemas.CmsMenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
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
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="menu item not found")
    crud.delete_cms_menu_item(db, item)


@router.post("/sites/{site_key}/menus/{menu_key}/reorder", response_model=list[schemas.CmsMenuItemRead])
def reorder_menu_items(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuItemReorderPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.reorder_cms_menu_items(db, menu.id, payload.items)


@router.get("/sites/{site_key}/pages", response_model=list[schemas.CmsPageRead])
def list_pages(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_pages(db, site.id)


@router.post("/sites/{site_key}/pages", response_model=schemas.CmsPageRead, status_code=201)
def create_page(
    site_key: str,
    payload: schemas.CmsPageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
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
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    return _get_page_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPageRead)
def patch_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsPageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status is not None:
        raise HTTPException(status_code=422, detail="use workflow endpoint to change status")
    site = _get_site_or_404(db, site_key)
    row = _get_page_or_404(db, site.id, slug)
    return crud.update_cms_page(db, row, payload, current_user.id)


@router.delete("/sites/{site_key}/pages/{slug}", status_code=204)
def delete_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    row = _get_page_or_404(db, site.id, slug)
    crud.delete_cms_page(db, row)


@router.get("/sites/{site_key}/pages/{slug}/sections", response_model=list[schemas.CmsSectionRead])
def list_sections(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.list_cms_sections(db, page.id)


@router.post("/sites/{site_key}/pages/{slug}/sections", response_model=schemas.CmsSectionRead, status_code=201)
def create_section(
    site_key: str,
    slug: str,
    payload: schemas.CmsSectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.type not in ALLOWED_SECTION_TYPES:
        raise HTTPException(status_code=422, detail="unsupported section type")
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.create_cms_section(db, page.id, payload)


@router.patch("/sites/{site_key}/pages/{slug}/sections/{section_id}", response_model=schemas.CmsSectionRead)
def patch_section(
    site_key: str,
    slug: str,
    section_id: int,
    payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.type is not None and payload.type not in ALLOWED_SECTION_TYPES:
        raise HTTPException(status_code=422, detail="unsupported section type")
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
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id)
    if not row:
        raise HTTPException(status_code=404, detail="section not found")
    crud.delete_cms_section(db, row)


@router.post("/sites/{site_key}/pages/{slug}/sections/reorder", response_model=list[schemas.CmsSectionRead])
def reorder_sections(
    site_key: str,
    slug: str,
    payload: schemas.CmsSectionReorderPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.reorder_cms_sections(db, page.id, payload.items)


@router.get("/sites/{site_key}/pages/{slug}/versions", response_model=list[schemas.CmsPageVersionRead])
def list_versions(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.list_cms_page_versions(db, page.id)


@router.post("/sites/{site_key}/pages/{slug}/rollback/{version_id}", response_model=schemas.CmsPageRead)
def rollback_page(
    site_key: str,
    slug: str,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
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
    current_user: models.User = Depends(require_active_user),
):
    action = payload.action.strip().lower()
    if action in {"approve", "publish", "archive"}:
        _assert_role(current_user, CMS_PUBLISHER_ROLES)
    else:
        _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.transition_cms_page_status(db, page, payload.action, current_user.id, notes=payload.notes)
    if not row:
        raise HTTPException(status_code=422, detail="invalid workflow action")
    return row


@router.get("/public/sites/{site_key}/theme", response_model=schemas.CmsThemeRead)
def public_theme(site_key: str, db: Session = Depends(get_db)):
    site = _get_site_or_404(db, site_key)
    row = crud.get_active_cms_theme(db, site.id)
    if not row:
        raise HTTPException(status_code=404, detail="active theme not found")
    return row


@router.get("/public/sites/{site_key}/menus/{menu_key}")
def public_menu(site_key: str, menu_key: str, db: Session = Depends(get_db)):
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    items = crud.list_cms_menu_items(db, menu.id)
    serialized = [
        {
            "id": item.id,
            "parent_id": item.parent_id,
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


@router.get("/public/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPublicPageRead)
def public_page(site_key: str, slug: str, db: Session = Depends(get_db)):
    site = _get_site_or_404(db, site_key)
    page = crud.get_public_cms_page(db, site.id, _slugify(slug))
    if not page:
        raise HTTPException(status_code=404, detail="published page not found")
    sections = crud.list_cms_sections(db, page.id)
    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=[schemas.CmsSectionRead.model_validate(section) for section in sections],
    )

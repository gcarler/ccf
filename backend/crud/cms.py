"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions)."""

import datetime as dt
import json
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.content_defaults import PAGE_CONTENT_DEFAULTS
from backend.crud._utils import _utcnow
from backend.crud.crm import resolve_persona_id_for_user as resolve_persona_uuid_for_user


def resolve_persona_id_for_user(db: Session, user_id: int | str | None):
    persona_id = resolve_persona_uuid_for_user(db, user_id)
    return persona_id


# ── Page Content ───────────────────────────────────────


def update_page_content(db: Session, page_key: str, payload: schemas.PageContentUpdate):
    page = (
        db.query(models.PageContent)
        .filter(models.PageContent.page_key == page_key)
        .first()
    )
    if not page:
        page = models.PageContent(
            page_key=page_key, title=payload.title or "", content=payload.content or ""
        )
        db.add(page)
        db.commit()
        db.refresh(page)
        return page
    version = models.PageContentVersion(
        page_key=page.page_key, title=page.title, content=page.content
    )
    db.add(version)
    if payload.title is not None:
        page.title = payload.title
    if payload.content is not None:
        page.content = payload.content
    db.commit()
    db.refresh(page)
    return page


def get_page_content(db: Session, page_key: str):
    return (
        db.query(models.PageContent)
        .filter(models.PageContent.page_key == page_key)
        .first()
    )


def list_page_contents(db: Session, limit: int = 200):
    return (
        db.query(models.PageContent)
        .order_by(models.PageContent.updated_at.desc())
        .limit(limit)
        .all()
    )


def get_or_create_page_content(db: Session, page_key: str):
    row = get_page_content(db, page_key)
    if row:
        return row

    defaults = PAGE_CONTENT_DEFAULTS.get(page_key, {})
    title = str(defaults.get("title") or page_key.replace("_", " ").title())
    default_content = defaults.get("content", {})

    if isinstance(default_content, str):
        content_payload = default_content
    else:
        content_payload = json.dumps(default_content, ensure_ascii=False)

    row = models.PageContent(page_key=page_key, title=title, content=content_payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_page_content_versions(db: Session, page_key: str):
    return (
        db.query(models.PageContentVersion)
        .filter(models.PageContentVersion.page_key == page_key)
        .order_by(models.PageContentVersion.created_at.desc())
        .all()
    )


def restore_page_content_version(db: Session, page_key: str, version_id: int):
    version = (
        db.query(models.PageContentVersion)
        .filter(
            models.PageContentVersion.id == version_id,
            models.PageContentVersion.page_key == page_key,
        )
        .first()
    )
    if not version:
        return None

    row = get_or_create_page_content(db, page_key)
    snapshot = models.PageContentVersion(
        page_key=row.page_key, title=row.title, content=row.content
    )
    db.add(snapshot)
    row.title = version.title
    row.content = version.content
    db.commit()
    db.refresh(row)
    return row


# ── Content Publications ───────────────────────────────


def get_or_create_content_publication(db: Session, page_key: str):
    row = (
        db.query(models.ContentPublication)
        .filter(models.ContentPublication.page_key == page_key)
        .first()
    )
    if row:
        return row
    row = models.ContentPublication(page_key=page_key, status="draft")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_content_publication(
    db: Session,
    page_key: str,
    *,
    status: str | None = None,
    publish_at: dt.datetime | None | object = ...,
    expire_at: dt.datetime | None | object = ...,
    notes: str | None = None,
    updated_by: int | None = None,
):
    row = get_or_create_content_publication(db, page_key)
    if status is not None:
        row.status = status
    if publish_at is not ...:
        row.publish_at = publish_at
    if expire_at is not ...:
        row.expire_at = expire_at
    if notes is not None:
        row.notes = notes
    if updated_by is not None:
        row.updated_by_persona_id = resolve_persona_id_for_user(db, updated_by)
    if status == "published":
        row.last_published_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def list_content_publications(db: Session):
    return db.query(models.ContentPublication).all()


# ── CMS Media ──────────────────────────────────────────


def create_cms_media_item(
    db: Session,
    *,
    url: str,
    alt_text: str | None,
    section: str,
    tags: list[str] | None,
    created_by: int | None,
    filename: str | None = None,
    mime_type: str | None = None,
    file_size: int | None = None,
    status: str = "active",
):
    row = models.CmsMediaItem(
        url=url,
        alt_text=alt_text,
        section=section,
        tags=tags or [],
        created_by_persona_id=resolve_persona_id_for_user(db, created_by),
        filename=filename,
        mime_type=mime_type,
        file_size=file_size or 0,
        status=(status or "active").strip().lower(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_cms_media_items(
    db: Session,
    *,
    query: str | None = None,
    section: str | None = None,
    limit: int = 250,
    include_archived: bool = False,
):
    q = db.query(models.CmsMediaItem)
    if not include_archived:
        q = q.filter(models.CmsMediaItem.status != "archived")
    if section:
        q = q.filter(models.CmsMediaItem.section == section)
    if query:
        like = f"%{query.strip()}%"
        q = q.filter(
            or_(
                models.CmsMediaItem.url.ilike(like),
                models.CmsMediaItem.alt_text.ilike(like),
                models.CmsMediaItem.filename.ilike(like),
            )
        )
    return q.order_by(models.CmsMediaItem.updated_at.desc()).limit(limit).all()


def get_cms_media_item(db: Session, item_id: int):
    return (
        db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == item_id).first()
    )


def update_cms_media_item(
    db: Session,
    item_id: int,
    *,
    url: str | None = None,
    alt_text: str | None = None,
    section: str | None = None,
    tags: list[str] | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
    file_size: int | None = None,
    status: str | None = None,
):
    row = get_cms_media_item(db, item_id)
    if not row:
        return None
    if url is not None:
        row.url = url
    if alt_text is not None:
        row.alt_text = alt_text
    if section is not None:
        row.section = section
    if tags is not None:
        row.tags = tags
    if filename is not None:
        row.filename = filename
    if mime_type is not None:
        row.mime_type = mime_type
    if file_size is not None:
        row.file_size = file_size
    if status is not None:
        row.status = status.strip().lower()
    db.commit()
    db.refresh(row)
    return row


def delete_cms_media_item(db: Session, item_id: int) -> bool:
    row = get_cms_media_item(db, item_id)
    if not row:
        return False
    row.status = "archived"
    db.commit()
    return True


# ── CMS Media Assets ───────────────────────────────────


def create_media_asset(
    db: Session, filename: str, url: str, mime_type: str | None, size_bytes: int
):
    row = models.MediaAsset(
        filename=filename, url=url, mime_type=mime_type, size_bytes=size_bytes
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_media_asset(db: Session, asset_id: int) -> bool:
    row = db.query(models.MediaAsset).filter(models.MediaAsset.id == asset_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── CMS Content Metrics ────────────────────────────────


def increment_content_metric(
    db: Session, metric_key: str, ref_id: int, amount: int = 1
):
    row = (
        db.query(models.ContentMetric)
        .filter(
            models.ContentMetric.metric_key == metric_key,
            models.ContentMetric.ref_id == ref_id,
        )
        .first()
    )
    if not row:
        row = models.ContentMetric(metric_key=metric_key, ref_id=ref_id, value=0)
        db.add(row)
    row.value = int(row.value or 0) + int(amount)
    db.commit()
    db.refresh(row)
    return row


# ── CMS v2 Sites ───────────────────────────────────────


def list_cms_sites(db: Session, *, only_active: bool = False):
    q = db.query(models.CmsSite)
    if only_active:
        q = q.filter(models.CmsSite.is_active.is_(True))
    return q.order_by(models.CmsSite.site_key.asc()).all()


def get_cms_site_by_key(db: Session, site_key: str):
    return db.query(models.CmsSite).filter(models.CmsSite.site_key == site_key).first()


def create_cms_site(db: Session, payload: schemas.CmsSiteCreate):
    row = models.CmsSite(
        site_key=payload.site_key.strip().lower(),
        name=payload.name.strip(),
        base_path=payload.base_path.strip(),
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_cms_site(db: Session, row: models.CmsSite, payload: schemas.CmsSiteUpdate):
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "base_path" in data and data["base_path"] is not None:
        row.base_path = str(data["base_path"]).strip()
    if "is_active" in data and data["is_active"] is not None:
        row.is_active = bool(data["is_active"])
    db.commit()
    db.refresh(row)
    return row


# ── CMS v2 Themes ──────────────────────────────────────


def archive_cms_site(db: Session, row: models.CmsSite) -> models.CmsSite:
    row.is_active = False
    db.commit()
    db.refresh(row)
    return row


def list_cms_themes(db: Session, site_id: int):
    return (
        db.query(models.CmsTheme)
        .filter(models.CmsTheme.site_id == site_id)
        .order_by(models.CmsTheme.is_active.desc(), models.CmsTheme.updated_at.desc())
        .all()
    )


def create_cms_theme(
    db: Session, site_id: int, payload: schemas.CmsThemeCreate, created_by: int | None
):
    version = (
        db.query(func.max(models.CmsTheme.version))
        .filter(models.CmsTheme.site_id == site_id)
        .scalar()
        or 0
    )
    status = (payload.status or "active").strip().lower()
    row = models.CmsTheme(
        site_id=site_id,
        name=payload.name.strip(),
        tokens_json=payload.tokens_json or {},
        is_active=bool(payload.is_active) and status != "archived",
        status=status,
        version=int(version) + 1,
        created_by_persona_id=resolve_persona_id_for_user(db, created_by),
    )
    db.add(row)
    if row.is_active:
        db.query(models.CmsTheme).filter(
            models.CmsTheme.site_id == site_id,
            models.CmsTheme.id != row.id,
        ).update({"is_active": False})
    db.commit()
    db.refresh(row)
    return row


def get_cms_theme(db: Session, site_id: int, theme_id: int):
    return (
        db.query(models.CmsTheme)
        .filter(models.CmsTheme.site_id == site_id, models.CmsTheme.id == theme_id)
        .first()
    )


def update_cms_theme(
    db: Session, row: models.CmsTheme, payload: schemas.CmsThemeUpdate
):
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "tokens_json" in data and data["tokens_json"] is not None:
        row.tokens_json = data["tokens_json"]
    if "status" in data and data["status"] is not None:
        row.status = str(data["status"]).strip().lower()
        if row.status == "archived":
            row.is_active = False
    if "is_active" in data and data["is_active"] is not None:
        row.is_active = bool(data["is_active"])
        if row.is_active:
            row.status = "active"
            db.query(models.CmsTheme).filter(
                models.CmsTheme.site_id == row.site_id,
                models.CmsTheme.id != row.id,
            ).update({"is_active": False})
    db.commit()
    db.refresh(row)
    return row


def activate_cms_theme(db: Session, site_id: int, theme_id: int):
    row = get_cms_theme(db, site_id, theme_id)
    if not row:
        return None
    db.query(models.CmsTheme).filter(models.CmsTheme.site_id == site_id).update(
        {"is_active": False}
    )
    row.is_active = True
    row.status = "active"
    db.commit()
    db.refresh(row)
    return row


def archive_cms_theme(db: Session, row: models.CmsTheme) -> models.CmsTheme:
    row.is_active = False
    row.status = "archived"
    db.commit()
    db.refresh(row)
    return row


def get_active_cms_theme(db: Session, site_id: int):
    return (
        db.query(models.CmsTheme)
        .filter(
            models.CmsTheme.site_id == site_id,
            models.CmsTheme.is_active.is_(True),
            models.CmsTheme.status != "archived",
        )
        .order_by(models.CmsTheme.updated_at.desc())
        .first()
    )


# ── CMS v2 Menus ───────────────────────────────────────


def list_cms_menus(db: Session, site_id: int):
    return (
        db.query(models.CmsMenu)
        .filter(models.CmsMenu.site_id == site_id)
        .order_by(models.CmsMenu.menu_key.asc())
        .all()
    )


def get_cms_menu(db: Session, site_id: int, menu_key: str):
    return (
        db.query(models.CmsMenu)
        .filter(models.CmsMenu.site_id == site_id, models.CmsMenu.menu_key == menu_key)
        .first()
    )


def create_cms_menu(db: Session, site_id: int, payload: schemas.CmsMenuCreate):
    row = models.CmsMenu(
        site_id=site_id,
        menu_key=payload.menu_key.strip().lower(),
        name=payload.name.strip(),
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_cms_menu(db: Session, row: models.CmsMenu, payload: schemas.CmsMenuUpdate):
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "is_active" in data and data["is_active"] is not None:
        row.is_active = bool(data["is_active"])
    db.commit()
    db.refresh(row)
    return row


def delete_cms_menu(db: Session, row: models.CmsMenu) -> bool:
    row.is_active = False
    db.commit()
    return True


# ── CMS v2 Menu Items ──────────────────────────────────


def list_cms_menu_items(db: Session, menu_id: int):
    return (
        db.query(models.CmsMenuItem)
        .filter(models.CmsMenuItem.menu_id == menu_id)
        .order_by(models.CmsMenuItem.sort_order.asc(), models.CmsMenuItem.id.asc())
        .all()
    )


def create_cms_menu_item(db: Session, menu_id: int, payload: schemas.CmsMenuItemCreate):
    row = models.CmsMenuItem(
        menu_id=menu_id,
        parent_id=payload.parent_id,
        label=payload.label.strip(),
        href=payload.href.strip(),
        target=payload.target,
        is_external=payload.is_external,
        visibility=payload.visibility,
        sort_order=payload.sort_order,
        meta_json=payload.meta_json or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_cms_menu_item(db: Session, menu_id: int, item_id: int):
    return (
        db.query(models.CmsMenuItem)
        .filter(models.CmsMenuItem.menu_id == menu_id, models.CmsMenuItem.id == item_id)
        .first()
    )


def update_cms_menu_item(
    db: Session, row: models.CmsMenuItem, payload: schemas.CmsMenuItemUpdate
):
    data = payload.model_dump(exclude_unset=True)
    for field in ["parent_id", "target", "is_external", "visibility", "sort_order"]:
        if field in data:
            setattr(row, field, data[field])
    if "label" in data and data["label"] is not None:
        row.label = str(data["label"]).strip()
    if "href" in data and data["href"] is not None:
        row.href = str(data["href"]).strip()
    if "meta_json" in data and data["meta_json"] is not None:
        row.meta_json = data["meta_json"]
    db.commit()
    db.refresh(row)
    return row


def delete_cms_menu_item(db: Session, row: models.CmsMenuItem) -> bool:
    row.visibility = "hidden"
    db.commit()
    return True


def reorder_cms_menu_items(
    db: Session, menu_id: int, items: list[schemas.CmsMenuItemReorderItem]
):
    rows_by_id = {
        row.id: row
        for row in db.query(models.CmsMenuItem)
        .filter(models.CmsMenuItem.menu_id == menu_id)
        .all()
    }
    for item in items:
        row = rows_by_id.get(item.id)
        if not row:
            continue
        row.parent_id = item.parent_id
        row.sort_order = item.sort_order
    db.commit()
    return list_cms_menu_items(db, menu_id)


# ── CMS v2 Pages ───────────────────────────────────────


def list_cms_pages(db: Session, site_id: int):
    return (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site_id)
        .order_by(models.CmsPage.updated_at.desc())
        .all()
    )


def get_cms_page(db: Session, site_id: int, slug: str):
    return (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site_id, models.CmsPage.slug == slug)
        .first()
    )


def create_cms_page(
    db: Session, site_id: int, payload: schemas.CmsPageCreate, user_id: int | None
):
    row = models.CmsPage(
        site_id=site_id,
        slug=payload.slug.strip().lower(),
        title=payload.title.strip(),
        status=payload.status,
        seo_json=payload.seo_json or {},
        created_by_persona_id=resolve_persona_id_for_user(db, user_id),
        updated_by_persona_id=resolve_persona_id_for_user(db, user_id),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_cms_page(
    db: Session,
    row: models.CmsPage,
    payload: schemas.CmsPageUpdate,
    user_id: int | None,
):
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        row.slug = str(data["slug"]).strip().lower()
    if "title" in data and data["title"] is not None:
        row.title = str(data["title"]).strip()
    if "status" in data and data["status"] is not None:
        row.status = str(data["status"]).strip()
    if "seo_json" in data and data["seo_json"] is not None:
        row.seo_json = data["seo_json"]
    if user_id is not None:
        row.updated_by_persona_id = resolve_persona_id_for_user(db, user_id)
    db.commit()
    db.refresh(row)
    return row


def delete_cms_page(db: Session, row: models.CmsPage) -> bool:
    row.status = "archived"
    db.commit()
    return True


# ── CMS v2 Sections ────────────────────────────────────


def list_cms_sections(db: Session, page_id: int):
    return (
        db.query(models.CmsSection)
        .filter(models.CmsSection.page_id == page_id)
        .order_by(models.CmsSection.sort_order.asc(), models.CmsSection.id.asc())
        .all()
    )


def create_cms_section(db: Session, page_id: int, payload: schemas.CmsSectionCreate):
    row = models.CmsSection(
        page_id=page_id,
        section_key=(payload.section_key or uuid.uuid4().hex),
        type=payload.type,
        props_json=payload.props_json or {},
        sort_order=payload.sort_order,
        is_visible=payload.is_visible,
        status=(payload.status or "active").strip().lower(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_cms_section(db: Session, page_id: int, section_id: int):
    return (
        db.query(models.CmsSection)
        .filter(
            models.CmsSection.page_id == page_id, models.CmsSection.id == section_id
        )
        .first()
    )


def update_cms_section(
    db: Session, row: models.CmsSection, payload: schemas.CmsSectionUpdate
):
    data = payload.model_dump(exclude_unset=True)
    for field in ["type", "sort_order", "is_visible", "status"]:
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    if "props_json" in data and data["props_json"] is not None:
        row.props_json = data["props_json"]
    db.commit()
    db.refresh(row)
    return row


def delete_cms_section(db: Session, row: models.CmsSection) -> bool:
    return archive_cms_section(db, row) is not None


def archive_cms_section(db: Session, row: models.CmsSection) -> models.CmsSection:
    row.status = "archived"
    db.commit()
    db.refresh(row)
    return row


def reorder_cms_sections(
    db: Session, page_id: int, items: list[schemas.CmsSectionReorderItem]
):
    rows_by_id = {
        row.id: row
        for row in db.query(models.CmsSection)
        .filter(models.CmsSection.page_id == page_id)
        .all()
    }
    for item in items:
        row = rows_by_id.get(item.id)
        if not row:
            continue
        row.sort_order = item.sort_order
    db.commit()
    return list_cms_sections(db, page_id)


# ── CMS v2 Page Versions ───────────────────────────────


def _build_page_snapshot(db: Session, page: models.CmsPage):
    sections = list_cms_sections(db, page.id)
    return {
        "page": {
            "id": page.id,
            "slug": page.slug,
            "title": page.title,
            "status": page.status,
            "seo_json": page.seo_json or {},
        },
        "sections": [
            {
                "id": section.id,
                "section_key": section.section_key,
                "type": section.type,
                "props_json": section.props_json or {},
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
                "status": getattr(section, "status", "active") or "active",
            }
            for section in sections
        ],
    }


def create_cms_page_version(
    db: Session, page: models.CmsPage, user_id: int | None, notes: str | None = None
):
    max_version = (
        db.query(func.max(models.CmsPageVersion.version_number))
        .filter(models.CmsPageVersion.page_id == page.id)
        .scalar()
        or 0
    )
    snapshot = _build_page_snapshot(db, page)
    row = models.CmsPageVersion(
        page_id=page.id,
        version_number=int(max_version) + 1,
        snapshot_json=snapshot,
        notes=notes,
        created_by_persona_id=resolve_persona_id_for_user(db, user_id),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_cms_page_versions(db: Session, page_id: int):
    return (
        db.query(models.CmsPageVersion)
        .filter(models.CmsPageVersion.page_id == page_id)
        .order_by(models.CmsPageVersion.version_number.desc())
        .all()
    )


def get_cms_page_version(db: Session, page_id: int, version_id: int):
    return (
        db.query(models.CmsPageVersion)
        .filter(
            models.CmsPageVersion.page_id == page_id,
            models.CmsPageVersion.id == version_id,
        )
        .first()
    )


def list_cms_publish_logs(
    db: Session, site_id: int, *, page_id: int | None = None, limit: int = 50
):
    query = db.query(models.CmsPublishLog).filter(
        models.CmsPublishLog.site_id == site_id
    )
    if page_id is not None:
        query = query.filter(models.CmsPublishLog.page_id == page_id)
    return query.order_by(models.CmsPublishLog.created_at.desc()).limit(limit).all()


def restore_cms_page_version(
    db: Session,
    page: models.CmsPage,
    version: models.CmsPageVersion,
    user_id: int | None,
):
    snapshot = version.snapshot_json or {}
    page_data = snapshot.get("page") or {}
    sections_data = snapshot.get("sections") or []
    if isinstance(page_data, dict):
        page.slug = str(page_data.get("slug") or page.slug)
        page.title = str(page_data.get("title") or page.title)
        page.seo_json = page_data.get("seo_json") or {}
    page.status = "draft"
    page.updated_by_persona_id = resolve_persona_id_for_user(db, user_id)
    db.query(models.CmsSection).filter(models.CmsSection.page_id == page.id).delete(
        synchronize_session=False
    )
    for idx, section_data in enumerate(sections_data):
        if not isinstance(section_data, dict):
            continue
        db.add(
            models.CmsSection(
                page_id=page.id,
                section_key=str(section_data.get("section_key") or uuid.uuid4().hex),
                type=str(section_data.get("type") or "rich_text"),
                props_json=section_data.get("props_json") or {},
                sort_order=int(section_data.get("sort_order") or idx),
                is_visible=bool(section_data.get("is_visible", True)),
                status=str(section_data.get("status") or "active"),
            )
        )
    db.commit()
    db.refresh(page)
    return page


def transition_cms_page_status(
    db: Session,
    page: models.CmsPage,
    action: str,
    user_id: int | None,
    notes: str | None = None,
):
    action = action.strip().lower()
    action_map = {
        "submit_review": "in_review",
        "approve": "approved",
        "publish": "published",
        "archive": "archived",
        "revert_draft": "draft",
    }
    if action not in action_map:
        return None
    next_status = action_map[action]
    previous_status = page.status
    if action == "publish":
        version = create_cms_page_version(db, page, user_id=user_id, notes=notes)
        page.published_version_id = version.id
    page.status = next_status
    actor_persona_id = resolve_persona_id_for_user(db, user_id)
    page.updated_by_persona_id = actor_persona_id
    db.add(
        models.CmsPublishLog(
            site_id=page.site_id,
            page_id=page.id,
            entity_type="page",
            entity_id=page.id,
            action=action,
            from_status=previous_status,
            to_status=next_status,
            actor_persona_id=actor_persona_id,
            metadata_json={"notes": notes} if notes else {},
        )
    )
    db.commit()
    db.refresh(page)
    return page


def get_public_cms_page(db: Session, site_id: int, slug: str):
    return (
        db.query(models.CmsPage)
        .filter(
            models.CmsPage.site_id == site_id,
            models.CmsPage.slug == slug,
            models.CmsPage.status == "published",
        )
        .first()
    )


# ── Announcements ───────────────────────────────────────


def create_announcement(
    db: Session, payload: schemas.AnnouncementCreate
) -> models.Announcement:
    status = payload.status or "published"
    row = models.Announcement(
        title=payload.title.strip(),
        content=payload.content.strip(),
        category=payload.category,
        image_url=payload.image_url,
        is_featured=payload.is_featured,
        status=status,
        published_at=_utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_announcements(
    db: Session, *, public_only: bool = False
) -> list[models.Announcement]:
    query = db.query(models.Announcement)
    if public_only:
        query = query.filter(
            models.Announcement.status == "published",
            models.Announcement.published_at <= _utcnow(),
        )
    return query.order_by(models.Announcement.created_at.desc()).all()


def get_announcement(db: Session, announcement_id: int) -> models.Announcement | None:
    return (
        db.query(models.Announcement)
        .filter(models.Announcement.id == announcement_id)
        .first()
    )


def update_announcement(
    db: Session, row: models.Announcement, payload: schemas.AnnouncementUpdate
) -> models.Announcement:
    data = payload.model_dump(exclude_unset=True)
    previous_status = row.status
    for field in ("title", "content", "category", "image_url", "is_featured", "status"):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    if previous_status != "published" and row.status == "published":
        row.published_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_announcement(db: Session, row: models.Announcement) -> bool:
    row.status = "archived"
    db.commit()
    return True


# ── Testimonials ────────────────────────────────────────


def create_testimonial(
    db: Session, payload: schemas.TestimonialCreate
) -> models.Testimonial:
    status = payload.status or ("approved" if payload.is_approved else "pending")
    author_persona_id = payload.author_persona_id or resolve_persona_id_for_user(
        db, payload.author_id
    )
    row = models.Testimonial(
        content=payload.content.strip(),
        emotion=payload.emotion,
        media_type=(payload.media_type or "text").strip() or "text",
        media_url=payload.media_url,
        image_url=payload.image_url,
        video_url=payload.video_url,
        podcast_url=payload.podcast_url,
        is_approved=payload.is_approved,
        show_on_home=payload.show_on_home,
        status=status,
        author_persona_id=author_persona_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_testimonials(
    db: Session, *, approved_only: bool = False
) -> list[models.Testimonial]:
    query = db.query(models.Testimonial)
    if approved_only:
        query = query.filter(
            models.Testimonial.is_approved.is_(True),
            models.Testimonial.status != "archived",
        )
    return query.order_by(models.Testimonial.created_at.desc()).all()


def get_testimonial(db: Session, testimonial_id: int) -> models.Testimonial | None:
    return (
        db.query(models.Testimonial)
        .filter(models.Testimonial.id == testimonial_id)
        .first()
    )


def update_testimonial(
    db: Session, row: models.Testimonial, payload: schemas.TestimonialUpdate
) -> models.Testimonial:
    data = payload.model_dump(exclude_unset=True)
    for field in (
        "content",
        "emotion",
        "media_type",
        "media_url",
        "image_url",
        "video_url",
        "podcast_url",
        "is_approved",
        "show_on_home",
        "status",
    ):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    if (
        "status" not in data
        and "is_approved" in data
        and data["is_approved"] is not None
    ):
        row.status = "approved" if data["is_approved"] else "pending"
    if "status" in data and data["status"] == "approved":
        row.is_approved = True
    if "status" in data and data["status"] in {"pending", "archived"}:
        row.is_approved = False
    db.commit()
    db.refresh(row)
    return row


def delete_testimonial(db: Session, row: models.Testimonial) -> bool:
    row.status = "archived"
    row.is_approved = False
    row.show_on_home = False
    db.commit()
    return True

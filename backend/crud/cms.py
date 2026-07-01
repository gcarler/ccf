"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes de User-Generated Content (Testimonial, Announcement,
CmsMediaItem) y PastoralProfile re-validan scope Multi-Tenant antes de
persistir cambios, propagando actor_user_id desde el caller API. Esto
cierra el TOCTOU gap donde un caller no-API (worker async, script de
seeding, llamada directa al CRUD) podría crear/mutar registros sin
pasar por el helper API `_get_scoped_*` correspondiente.
"""

import datetime as dt
import json
import logging
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.content_defaults import PAGE_CONTENT_DEFAULTS
from backend.crud._utils import _utcnow
from backend.crud.crm import (
    resolve_persona_id_for_user as resolve_persona_uuid_for_user,
)

_logger = logging.getLogger(__name__)


def resolve_persona_id_for_user(db: Session, user_id: uuid.UUID | str | None):
    persona_id = resolve_persona_uuid_for_user(db, user_id)
    return persona_id


# ── Axioma 3 — Multi-Tenant defense-in-depth helpers (CMS CRUD) ──────────


def _actor_sede_or_none_cms(
    db: Session, actor_user_id: str | uuid.UUID
) -> str | None:
    """Resolve la sede de un actor autenticado.

    ``None`` sólo representa un superadministrador canónico sin sede. La
    ausencia o malformación del actor es un error y nunca omite silenciosamente
    el control multi-tenant.
    """
    from fastapi import HTTPException as _HTTPException

    from backend.crud.crm import get_user_sede_id

    try:
        actor_uuid = uuid.UUID(str(actor_user_id))
    except (TypeError, ValueError, AttributeError):
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    if resolve_persona_id_for_user(db, actor_uuid) is None:
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    return get_user_sede_id(db, str(actor_uuid))


def _resolve_persona_sede(db: Session, persona_id) -> str | None:
    """Resuelve la ``sede_id`` de una persona target (UUID) o None.

    Helper usado por defense-in-depth de CMS User-Generated Content.
    Retorna:
      - ``None`` si la persona no existe.
      - ``None`` si la persona no tiene sede asignada (orphan).
      - La sede como ``str`` en caso contrario.
    """
    if persona_id is None:
        return None
    try:
        persona_uuid = uuid.UUID(str(persona_id))
    except (TypeError, ValueError, AttributeError):
        return None
    row = (
        db.query(models.Persona.sede_id)
        .filter(models.Persona.id == persona_uuid)
        .first()
    )
    if not row or row[0] is None:
        return None
    return str(row[0])


def _crud_scope_re_check_cms_content_create(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    author_persona_id,
) -> str | None:
    """Defense in depth para CMS create (Testimonial / Announcement / MediaItem).

    Política estricta sobre el estado de anclas tras la mutación:

      - Actor sin sede o persona autora no resoluble: REJECT 409.

      - **Actor con sede y ``author_persona_id`` resuelve a sede
        distinta de ``actor_sede``**: REJECT 404. Cross-sede leak:
        breach de Axioma 3. Logged at WARNING (no INFO). Mensaje neutro
        para no leakear info del anchor al caller.

      - **Match exacto**: retorna ``target_sede`` (que coincide con
        ``actor_sede``) para que el CRUD lo persista en
        ``row.sede_id = target_sede`` sin JOIN adicional.

    Retorna la sede validada. Ningún UGC puede persistirse sin owner+sede.
    """
    from fastapi import HTTPException as _HTTPException

    if not actor_sede or author_persona_id is None:
        raise _HTTPException(
            status_code=409,
            detail="CMS content requires an attributed persona and sede",
        )

    target_sede = _resolve_persona_sede(db, author_persona_id)
    if target_sede is None or target_sede != str(actor_sede):
        _logger.warning(
            "Axioma 3 scope violation: CMS content create cross-sede "
            "(actor_sede=%s actor_user_id=%s author_persona_id=%s "
            "target_sede=%s)",
            actor_sede,
            actor_user_id,
            author_persona_id,
            target_sede,
        )
        raise _HTTPException(
            status_code=404, detail="CMS content creation blocked"
        )

    return target_sede


def _crud_scope_re_check_cms_content_update(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    current_row_sede: str | None,
    incoming_author_persona_id,
) -> None:
    """Defense in depth para CMS update (Testimonial / Announcement / MediaItem).

    Política OR-based sobre el estado FINAL del row:
      - Actor sin sede: bypass sin check.
      - Row tiene sede_id coherente con actor_sede y el body no introduce
        FK cross-sede: OK.
      - Cualquier vector cross-sede (row.move o incoming_FK.cross): REJECT
        404 con mensaje neutro (existence-leak safe).

    Casos:
      - Row.current_sede es None y actor con sede: REJECT 404 (orphan).
      - Incoming.author_persona_id resuelve a OTRA sede que ``actor_sede``:
        REJECT 404 (TOCTOU para fijar FK cross-sede vía API tras fetch).
    """
    from fastapi import HTTPException as _HTTPException

    if not actor_sede:
        return  # superadmin / anterior path

    if current_row_sede is None or str(current_row_sede) != str(actor_sede):
        _logger.warning(
            "Axioma 3 scope violation: CMS content update row cross-sede "
            "(actor_sede=%s actor_user_id=%s current_row_sede=%s)",
            actor_sede,
            actor_user_id,
            current_row_sede,
        )
        raise _HTTPException(
            status_code=404, detail="CMS content update blocked"
        )

    if incoming_author_persona_id is not None:
        incoming_sede = _resolve_persona_sede(db, incoming_author_persona_id)
        if incoming_sede is None or incoming_sede != str(actor_sede):
            _logger.warning(
                "Axioma 3 scope violation: CMS content update FK cross-sede "
                "(actor_sede=%s actor_user_id=%s incoming=%s target_sede=%s)",
                actor_sede,
                actor_user_id,
                incoming_author_persona_id,
                incoming_sede,
            )
            raise _HTTPException(
                status_code=404, detail="CMS content update blocked"
            )


def _crud_scope_re_check_pastoral_profile(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    target_persona_id,
    target_persona_sede: str | None,
) -> None:
    """Defense in depth para ``update_pastoral_profile``.

    Cierra el IDOR crítico donde un editor CMS puede mutar cualquier
    ``Persona`` del platform via ``cms_pastoral_profile_update``. El helper
    API-layer ``_get_scoped_persona`` ya devuelve 404 cross-sede, pero el
    CRUD re-valida para proteger contra callers no-API (workers, scripts,
    tests directos).
    """
    from fastapi import HTTPException as _HTTPException

    if not actor_sede:
        return  # superadmin / anterior path

    if target_persona_sede is None or str(target_persona_sede) != str(actor_sede):
        _logger.warning(
            "Axioma 3 scope violation: update_pastoral_profile cross-sede "
            "(actor_sede=%s actor_user_id=%s target_persona_id=%s "
            "target_sede=%s)",
            actor_sede,
            actor_user_id,
            target_persona_id,
            target_persona_sede,
        )
        raise _HTTPException(
            status_code=404, detail="Pastoral profile update blocked"
        )


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


def restore_page_content_version(db: Session, page_key: str, version_id: uuid.UUID):
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
    created_by: str | uuid.UUID,
    filename: str | None = None,
    mime_type: str | None = None,
    file_size: int | None = None,
    status: str = "active",
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: deriva ``sede_id`` de la persona creadora
    y re-valida scope Multi-Tenant pre-add via
    ``_crud_scope_re_check_cms_content_create``.

    Si el actor tiene sede asignada y el creator persona es de OTRA sede
    o es unresoluble, raise 404. Superadmin / anterior path (actor sin sede)
    bypassea — consistente con resto del axioma 3.
    """
    creator_persona_id = resolve_persona_id_for_user(db, created_by)
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    derived_sede = _crud_scope_re_check_cms_content_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        author_persona_id=creator_persona_id,
    )

    row = models.CmsMediaItem(
        url=url,
        alt_text=alt_text,
        section=section,
        tags=tags or [],
        created_by_persona_id=creator_persona_id,
        sede_id=derived_sede,
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
    skip: int = 0,
    limit: int = 50,
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
    total = q.count()
    items = (
        q.order_by(models.CmsMediaItem.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_cms_media_item(db: Session, item_id: uuid.UUID):
    return (
        db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == item_id).first()
    )


def update_cms_media_item(
    db: Session,
    item_id: uuid.UUID,
    *,
    url: str | None = None,
    alt_text: str | None = None,
    section: str | None = None,
    tags: list[str] | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
    file_size: int | None = None,
    status: str | None = None,
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: defense-in-depth pre-mutation.

    El caller debe haber ya apuntado una fila via API-layer helper
    (``_get_scoped_cms_media``) que garantiza 404 cross-sede en retrieval.
    Este helper re-valida por si la fila fue movida cross-sede entre el
    fetch y el re-fetch (TOCTOU gap).
    """
    row = get_cms_media_item(db, item_id)
    if not row:
        return None
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
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


def delete_cms_media_item(
    db: Session,
    item_id: uuid.UUID,
    *,
    actor_user_id: str | uuid.UUID,
) -> bool:
    """Axioma 3 — Multi-Tenant: defense-in-depth pre soft-delete.

    Retorna ``False`` tanto para inexistente como para cross-sede (llamada
    equivalente al ``_get_scoped_cms_media`` que ya hizo el API). El API
    layer traduce esto a ``HTTPException(404)``.
    """
    row = get_cms_media_item(db, item_id)
    if not row:
        return False
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
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


def delete_media_asset(db: Session, asset_id: uuid.UUID) -> bool:
    row = db.query(models.MediaAsset).filter(models.MediaAsset.id == asset_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── CMS Content Metrics ────────────────────────────────


def increment_content_metric(
    db: Session, metric_key: str, ref_id: str, amount: int = 1
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


def list_cms_themes(db: Session, site_id: uuid.UUID):
    return (
        db.query(models.CmsTheme)
        .filter(models.CmsTheme.site_id == site_id)
        .order_by(models.CmsTheme.is_active.desc(), models.CmsTheme.updated_at.desc())
        .all()
    )


def create_cms_theme(
    db: Session, site_id: uuid.UUID, payload: schemas.CmsThemeCreate, created_by: int | None
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


def get_cms_theme(db: Session, site_id: uuid.UUID, theme_id: uuid.UUID):
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


def activate_cms_theme(db: Session, site_id: uuid.UUID, theme_id: uuid.UUID):
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


def get_active_cms_theme(db: Session, site_id: uuid.UUID):
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


def list_cms_menus(db: Session, site_id: uuid.UUID):
    return (
        db.query(models.CmsMenu)
        .filter(models.CmsMenu.site_id == site_id)
        .order_by(models.CmsMenu.menu_key.asc())
        .all()
    )


def get_cms_menu(db: Session, site_id: uuid.UUID, menu_key: str):
    return (
        db.query(models.CmsMenu)
        .filter(models.CmsMenu.site_id == site_id, models.CmsMenu.menu_key == menu_key)
        .first()
    )


def create_cms_menu(db: Session, site_id: uuid.UUID, payload: schemas.CmsMenuCreate):
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


def list_cms_menu_items(db: Session, menu_id: uuid.UUID):
    return (
        db.query(models.CmsMenuItem)
        .filter(models.CmsMenuItem.menu_id == menu_id)
        .order_by(models.CmsMenuItem.sort_order.asc(), models.CmsMenuItem.id.asc())
        .all()
    )


def create_cms_menu_item(db: Session, menu_id: uuid.UUID, payload: schemas.CmsMenuItemCreate):
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


def get_cms_menu_item(db: Session, menu_id: uuid.UUID, item_id: uuid.UUID):
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
    db: Session, menu_id: uuid.UUID, items: list[schemas.CmsMenuItemReorderItem]
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


def list_cms_pages(
    db: Session,
    site_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
):
    query = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site_id)
    )
    if status:
        query = query.filter(models.CmsPage.status == status)
    total = query.count()
    items = (
        query
        .order_by(models.CmsPage.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_cms_pages_all(db: Session, site_id: uuid.UUID):
    """Return all pages for a site without pagination."""
    return (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site_id)
        .order_by(models.CmsPage.updated_at.desc())
        .all()
    )


def get_cms_page(db: Session, site_id: uuid.UUID, slug: str):
    return (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site_id, models.CmsPage.slug == slug)
        .first()
    )


def create_cms_page(
    db: Session, site_id: uuid.UUID, payload: schemas.CmsPageCreate, user_id: uuid.UUID | None
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
    user_id: uuid.UUID | None,
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


def list_cms_sections(
    db: Session,
    page_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    section_type: str | None = None,
):
    query = db.query(models.CmsSection).filter(models.CmsSection.page_id == page_id)
    if section_type:
        query = query.filter(models.CmsSection.section_type == section_type)
    total = query.count()
    items = (
        query
        .order_by(models.CmsSection.sort_order.asc(), models.CmsSection.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def create_cms_section(db: Session, page_id: uuid.UUID, payload: schemas.CmsSectionCreate):
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


def get_cms_section(db: Session, page_id: uuid.UUID, section_id: uuid.UUID):
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
    db: Session, page_id: uuid.UUID, items: list[schemas.CmsSectionReorderItem]
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
    # ``list_cms_sections`` returns a ``(items, total)`` tuple (paginated
    # contract). The previous code iterated the tuple unpacking its members;
    # ``for section in sections`` would yield the list *and* the int total,
    # causing ``section.section_key`` to AttributeError and crashing
    # ``create_cms_page_version`` in production.
    sections, _ = list_cms_sections(db, page.id)

    def _jsonable(value):
            # Convert SQLAlchemy/runtime types into JSON-serializable primitives.
            # UUID and datetime objects cannot be encoded by ``json.dumps`` which
            # is what SQLAlchemy uses for JSONB columns; this helper avoids the
            # ``TypeError: Object of type UUID is not JSON serializable`` that
            # crashed ``create_cms_page_version`` on first publish.
            if value is None:
                return None
            if isinstance(value, uuid.UUID):
                return str(value)
            if isinstance(value, (dt.date, dt.datetime)):
                return value.isoformat()
            return value

    return {
        "page": {
            "id": _jsonable(page.id),
            "slug": _jsonable(page.slug),
            "title": _jsonable(page.title),
            "status": _jsonable(page.status),
            "seo_json": page.seo_json or {},
        },
        "sections": [
            {
                "id": _jsonable(section.id),
                "section_key": _jsonable(section.section_key),
                "type": _jsonable(section.type),
                "props_json": section.props_json or {},
                "sort_order": _jsonable(section.sort_order),
                "is_visible": _jsonable(section.is_visible),
                "status": _jsonable(getattr(section, "status", "active") or "active"),
            }
            for section in sections
        ],
    }


def create_cms_page_version(
    db: Session, page: models.CmsPage, user_id: uuid.UUID | None, notes: str | None = None
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


def list_cms_page_versions(
    db: Session,
    page_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
):
    query = db.query(models.CmsPageVersion).filter(models.CmsPageVersion.page_id == page_id)
    total = query.count()
    items = (
        query
        .order_by(models.CmsPageVersion.version_number.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_cms_page_version(db: Session, page_id: uuid.UUID, version_id: uuid.UUID):
    return (
        db.query(models.CmsPageVersion)
        .filter(
            models.CmsPageVersion.page_id == page_id,
            models.CmsPageVersion.id == version_id,
        )
        .first()
    )


def list_cms_publish_logs(
    db: Session,
    site_id: uuid.UUID,
    *,
    page_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = db.query(models.CmsPublishLog).filter(
        models.CmsPublishLog.site_id == site_id
    )
    if page_id is not None:
        query = query.filter(models.CmsPublishLog.page_id == page_id)
    total = query.count()
    items = (
        query
        .order_by(models.CmsPublishLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def restore_cms_page_version(
    db: Session,
    page: models.CmsPage,
    version: models.CmsPageVersion,
    user_id: uuid.UUID | None,
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
    user_id: uuid.UUID | None,
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


def get_public_cms_page(db: Session, site_id: uuid.UUID, slug: str):
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
    db: Session,
    payload: schemas.AnnouncementCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.Announcement:
    """Axioma 3 — Multi-Tenant: ``sede_id`` + ``created_by_persona_id`` se
    derivan server-side desde el current_user y se validan en
    defense-in-depth contra cross-sede.

    Announcement NO tiene autor natural (no es un testimonial) — la única
    ancla de scope es la sede del editor. Si el actor está en sede_a e
    intenta crear un announcement para ``sede_id`` distinto al suyo,
    CRÍTICAMENTE aquí se vulnera Axioma 3. El helper re-check garantiza
    que ``sede_id`` del row matchea ``actor_sede``.

    Nota: como Announcement originalmente no aceptaba author_persona,
    usamos ``actor_user_id`` como creator persona fallback. La función
    resuelve ``created_by_persona_id`` vía ``resolve_persona_id_for_user``
    sobre ``actor_user_id`` (consistente con cómo ``current_user.id`` se
    traduce a ``Persona.id`` en ``auth_v3``).
    """
    status = payload.status or "published"
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    derived_sede = _crud_scope_re_check_cms_content_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        author_persona_id=resolve_persona_id_for_user(db, actor_user_id),
    )
    row = models.Announcement(
        title=payload.title.strip(),
        content=payload.content.strip(),
        category=payload.category,
        image_url=payload.image_url,
        is_featured=payload.is_featured,
        status=status,
        sede_id=derived_sede,
        created_by_persona_id=resolve_persona_id_for_user(db, actor_user_id),
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


def get_announcement(db: Session, announcement_id: uuid.UUID) -> models.Announcement | None:
    return (
        db.query(models.Announcement)
        .filter(models.Announcement.id == announcement_id)
        .first()
    )


def update_announcement(
    db: Session,
    row: models.Announcement,
    payload: schemas.AnnouncementUpdate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.Announcement:
    """Axioma 3 — Multi-Tenant: defense-in-depth pre-mutation.

    El API layer helper (``_get_scoped_cms_announcement``) ya garantizó 404
    cross-sede en retrieval; este helper re-valida por si hubo un
    movimiento TOCTOU entre fetch y commit.
    """
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
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


def delete_announcement(
    db: Session, row: models.Announcement, *, actor_user_id: str | uuid.UUID
) -> bool:
    """Axioma 3 — Multi-Tenant: defense-in-depth pre soft-delete.

    Retorna ``True`` si archivó OK, ``False`` si cross-sede (None guard
    interno). El helper API traduce ``False`` a ``HTTPException(404)``.
    """
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
    row.status = "archived"
    db.commit()
    return True


# ── Testimonials ────────────────────────────────────────


def create_testimonial(
    db: Session,
    payload: schemas.TestimonialCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.Testimonial:
    """Axioma 3 — Multi-Tenant: ``sede_id`` se deriva de la persona del
    autor. Defense-in-depth pre-add garantiza que ``author_persona``
    pertenece a la sede del actor. Si el body omite autor, se usa la persona
    del actor; si no puede resolverse, la creación se rechaza.
    """
    status = payload.status or ("approved" if payload.is_approved else "pending")
    # Resolve ``author_persona_id`` server-side: si el payload lo trae,
    # usamos eso (cliente tiene control explícito). Si no, derivar desde
    # ``actor_user_id`` (consistente con el patrón de ``create_announcement``).
    #
    # NOTA: ``payload.author_id`` NO existe en ``TestimonialCreate`` (era
    # un FK anterior int a ``personas`` que se eliminó cuando se consolidó
    # al schema UUID ``author_persona_id``). Si dereferenciamos
    # ``payload.author_id`` получаем ``AttributeError``; por eso el
    # fallback usa directamente ``actor_user_id`` (la fuente canónica).
    author_persona_id = payload.author_persona_id
    if author_persona_id is None:
        author_persona_id = resolve_persona_id_for_user(db, actor_user_id)
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    derived_sede = _crud_scope_re_check_cms_content_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        author_persona_id=author_persona_id,
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
        sede_id=derived_sede,
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


def get_testimonial(db: Session, testimonial_id: uuid.UUID) -> models.Testimonial | None:
    return (
        db.query(models.Testimonial)
        .filter(models.Testimonial.id == testimonial_id)
        .first()
    )


def update_testimonial(
    db: Session,
    row: models.Testimonial,
    payload: schemas.TestimonialUpdate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.Testimonial:
    """Axioma 3 — Multi-Tenant: defense-in-depth pre-mutation.

    El API helper (``_get_scoped_cms_testimonial``) ya garantizó 404
    cross-sede. Aquí re-validamos TOCTOU + validar que cualquier
    ``author_persona_id`` incoming no introduzca FK cross-sede. Testi-
    monialUpdate no permite cambiar el autor via body (sólo campos de
    state), así que el incoming FK slot es la fila actual.
    """
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.author_persona_id,
    )
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


def delete_testimonial(
    db: Session, row: models.Testimonial, *, actor_user_id: str | uuid.UUID
) -> bool:
    """Axioma 3 — Multi-Tenant: defense-in-depth pre soft-delete."""
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.author_persona_id,
    )
    row.status = "archived"
    row.is_approved = False
    row.show_on_home = False
    db.commit()
    return True


# ── Pastoral Profile ───────────────────────────────────────────────────────


def list_pastoral_team(db: Session) -> list[models.Persona]:
    return (
        db.query(models.Persona)
        .filter(models.Persona.is_pastoral_leader.is_(True))
        .order_by(models.Persona.is_main_pastor.desc(), models.Persona.nombre_completo.asc())
        .all()
    )


def get_persona_by_id(db: Session, persona_id: str) -> models.Persona | None:
    try:
        uid = uuid.UUID(persona_id)
    except ValueError:
        return None
    return db.query(models.Persona).filter(models.Persona.id == uid).first()


def update_pastoral_profile(
    db: Session,
    persona: models.Persona,
    payload: schemas.PastoralProfileUpdate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.Persona:
    """Axioma 3 — Multi-Tenant: defense-in-depth contra IDOR crítico.

    El API helper ``_get_scoped_persona`` (en ``backend.api.crm._shared``)
    ya garantiza 404 cross-sede al recuperar la persona. Este CRUD re-
    valida pre-commit para cubrir callers no-API (workers async, scripts
    que invocan el CRUD directamente).

    Cierre del vector: ``Persona`` no tiene columna ``sede_id`` propia
    para ``cms_pastoral_team_list`` filter, pero SÍ la expone como query
    en ``Persona.sede_id`` (FK). El helper resuelve ``target_persona_sede``
    antes de comparar.
    """
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    target_persona_sede = (
        str(persona.sede_id) if getattr(persona, "sede_id", None) else None
    )
    _crud_scope_re_check_pastoral_profile(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_persona_id=persona.id,
        target_persona_sede=target_persona_sede,
    )
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    return persona

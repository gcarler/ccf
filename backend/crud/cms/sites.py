"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes de User-Generated Content (Testimonial, Announcement,
CmsMediaItem) y PastoralProfile re-validan scope Multi-Tenant antes de
persistir cambios, propagando actor_user_id desde el caller API. Esto
cierra el TOCTOU gap donde un caller no-API (worker async, script de
seeding, llamada directa al CRUD) podría crear/mutar registros sin
pasar por el helper API `_get_scoped_*` correspondiente.
"""

import logging
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, lazyload

from backend import models, schemas
from backend.crud.crm import (
    resolve_persona_id_for_user as resolve_persona_uuid_for_user,
)

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



from backend.core.cache_v2 import invalidate_cached_public, invalidate_cached_public_pattern
from backend.crud.cms._shared import (
    _actor_sede_or_none_cms,
    _commit_or_conflict,
    _crud_scope_re_check_cms_site_content,
    validate_cms_actor_site,
    resolve_site_key,
)


def list_cms_sites(db: Session, *, only_active: bool = False, sede_id: uuid.UUID | None = None):

    q = db.query(models.CmsSite).options(lazyload("*"))
    if only_active:
        q = q.filter(models.CmsSite.is_active.is_(True))
    if sede_id is not None:
        q = q.filter((models.CmsSite.sede_id == sede_id) | (models.CmsSite.sede_id.is_(None)))
    return q.order_by(models.CmsSite.site_key.asc()).all()



def get_cms_site_by_key(db: Session, site_key: str):

    return db.query(models.CmsSite).options(lazyload("*")).filter(models.CmsSite.site_key == site_key).first()



def create_cms_site(
    db: Session,
    payload: schemas.CmsSiteCreate,
    *,
    commit_with_conflict_check: bool = False,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        if actor_sede is not None and payload.sede_id is not None and str(payload.sede_id) != str(actor_sede):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="CMS site creation blocked")
    row = models.CmsSite(
        site_key=payload.site_key.strip().lower(),
        name=payload.name.strip(),
        base_path=payload.base_path.strip(),
        is_active=payload.is_active,
        sede_id=payload.sede_id,
    )
    db.add(row)
    if commit_with_conflict_check and not _commit_or_conflict(db):
        return None
    elif not commit_with_conflict_check:
        db.commit()
    db.refresh(row)
    return row



def update_cms_site(db: Session, row: models.CmsSite, payload: schemas.CmsSiteUpdate, *, actor_user_id=None):
    if actor_user_id is not None:
        validate_cms_actor_site(db, actor_user_id, row.id)
    data = payload.model_dump(exclude_unset=True)
    was_active = row.is_active
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "base_path" in data and data["base_path"] is not None:
        row.base_path = str(data["base_path"]).strip()
    if "is_active" in data and data["is_active"] is not None:
        row.is_active = bool(data["is_active"])
    if "sede_id" in data:
        row.sede_id = data["sede_id"]
    db.commit()
    db.refresh(row)
    # Cierre de staleness: desactivar un site vía PATCH deja de servir
    # sus menús, theme, páginas y posts públicos de inmediato (404).
    if was_active and not row.is_active:
        _invalidate_site_public_cache(db, row.id)
    return row



def archive_cms_site(db: Session, row: models.CmsSite, *, actor_user_id=None) -> models.CmsSite:
    if actor_user_id is not None:
        validate_cms_actor_site(db, actor_user_id, row.id)
    row.is_active = False
    db.commit()
    db.refresh(row)
    # Cierre de staleness: el contenido público del site archivado debe
    # dejar de servirse de inmediato (404), no esperar el TTL de 300s.
    _invalidate_site_public_cache(db, row.id)
    return row



def list_cms_themes(db: Session, site_id: uuid.UUID):
    return (
        db.query(models.CmsTheme)
        .filter(models.CmsTheme.site_id == site_id)
        .order_by(models.CmsTheme.is_active.desc(), models.CmsTheme.updated_at.desc())
        .all()
    )



def create_cms_theme(
    db: Session,
    site_id: uuid.UUID,
    payload: schemas.CmsThemeCreate,
    created_by: uuid.UUID | str | None,
    *,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(db, actor_user_id, actor_sede=actor_sede, site_id=site_id)
    version = db.query(func.max(models.CmsTheme.version)).filter(models.CmsTheme.site_id == site_id).scalar() or 0
    status = (payload.status or "active").strip().lower()
    row = models.CmsTheme(
        site_id=site_id,
        name=payload.name.strip(),
        tokens_json=payload.tokens_json or {},
        is_active=bool(payload.is_active) and status != "archived",
        status=status,
        version=int(version) + 1,
        created_by_persona_id=resolve_persona_uuid_for_user(db, created_by),
        updated_by_persona_id=resolve_persona_uuid_for_user(db, actor_user_id or created_by),
    )
    db.add(row)
    if row.is_active:
        db.query(models.CmsTheme).filter(
            models.CmsTheme.site_id == site_id,
            models.CmsTheme.id != row.id,
        ).update({"is_active": False})
    db.commit()
    db.refresh(row)
    # Cierre de staleness: un theme nuevo (o activo) cambia la respuesta
    # cacheada del endpoint público ``public_theme``.
    _invalidate_public_theme_cache(db, site_id)
    return row



def get_cms_theme(db: Session, site_id: uuid.UUID, theme_id: uuid.UUID):
    return db.query(models.CmsTheme).filter(models.CmsTheme.site_id == site_id, models.CmsTheme.id == theme_id).first()



def update_cms_theme(
    db: Session,
    row: models.CmsTheme,
    payload: schemas.CmsThemeUpdate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(db, actor_user_id, actor_sede=actor_sede, site_id=row.site_id)
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
    if actor_user_id is not None:
        row.updated_by_persona_id = resolve_persona_uuid_for_user(db, actor_user_id)
    db.commit()
    db.refresh(row)
    # Cierre de staleness: name/tokens/is_active/status alteran la
    # respuesta pública cacheada del theme activo.
    _invalidate_public_theme_cache(db, row.site_id)
    return row



def activate_cms_theme(
    db: Session,
    site_id: uuid.UUID,
    theme_id: uuid.UUID,
    *,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(db, actor_user_id, actor_sede=actor_sede, site_id=site_id)
    row = get_cms_theme(db, site_id, theme_id)
    if not row:
        return None
    db.query(models.CmsTheme).filter(models.CmsTheme.site_id == site_id).update({"is_active": False})
    row.is_active = True
    row.status = "active"
    if actor_user_id is not None:
        row.updated_by_persona_id = resolve_persona_uuid_for_user(db, actor_user_id)
    db.commit()
    db.refresh(row)
    # Cierre de staleness: el theme activo cambió — refresca la caché pública.
    _invalidate_public_theme_cache(db, site_id)
    return row



def archive_cms_theme(
    db: Session,
    row: models.CmsTheme,
    *,
    actor_user_id: str | uuid.UUID | None = None,
) -> models.CmsTheme:
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(db, actor_user_id, actor_sede=actor_sede, site_id=row.site_id)
    row.is_active = False
    row.status = "archived"
    if actor_user_id is not None:
        row.updated_by_persona_id = resolve_persona_uuid_for_user(db, actor_user_id)
    db.commit()
    db.refresh(row)
    # Cierre de staleness: archivar el theme activo deja de servirlo en
    # el endpoint público de inmediato (404 si no queda otro activo).
    _invalidate_public_theme_cache(db, row.site_id)
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



def list_cms_menus(db: Session, site_id: uuid.UUID):
    return (
        db.query(models.CmsMenu).filter(models.CmsMenu.site_id == site_id).order_by(models.CmsMenu.menu_key.asc()).all()
    )



def get_cms_menu(db: Session, site_id: uuid.UUID, menu_key: str):
    return (
        db.query(models.CmsMenu).filter(models.CmsMenu.site_id == site_id, models.CmsMenu.menu_key == menu_key).first()
    )



def create_cms_menu(
    db: Session,
    site_id: uuid.UUID,
    payload: schemas.CmsMenuCreate,
    *,
    commit_with_conflict_check: bool = False,
    actor_user_id=None,
):
    if actor_user_id is not None:
        validate_cms_actor_site(db, actor_user_id, site_id)
    row = models.CmsMenu(
        site_id=site_id,
        menu_key=payload.menu_key.strip().lower(),
        name=payload.name.strip(),
        is_active=payload.is_active,
    )
    db.add(row)
    if commit_with_conflict_check and not _commit_or_conflict(db):
        return None
    elif not commit_with_conflict_check:
        db.commit()
    db.refresh(row)
    return row



def update_cms_menu(db: Session, row: models.CmsMenu, payload: schemas.CmsMenuUpdate, *, actor_user_id=None):
    if actor_user_id is not None:
        validate_cms_actor_site(db, actor_user_id, row.site_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "is_active" in data and data["is_active"] is not None:
        row.is_active = bool(data["is_active"])
    db.commit()
    db.refresh(row)
    # Cierre de staleness: desactivar/renombrar un menú altera la
    # respuesta pública cacheada.
    _invalidate_public_menu_cache(db, row)
    return row



def delete_cms_menu(db: Session, row: models.CmsMenu, *, actor_user_id=None) -> bool:
    if actor_user_id is not None:
        validate_cms_actor_site(db, actor_user_id, row.site_id)
    row.is_active = False
    db.commit()
    # Invalidación de caché pública: un menú soft-deleteado debe dejar de
    # servirse de inmediato (404) en el endpoint público en lugar de
    # esperar el TTL de 300s de ``cached_public``.
    _invalidate_public_menu_cache(db, row)
    return True



def _invalidate_public_menu_key(db: Session, site_id: uuid.UUID, menu_key: str) -> None:
    """Borra la entrada cacheada del endpoint público de menús para un
    site + menu_key dados.

    Reconstruye la cache key con el ``site_key`` canónico del site y el
    ``menu_key`` del menú — los mismos argumentos serializables que
    ``public_menu`` recibe por kwargs desde FastAPI.
    """
    try:
        site_key = resolve_site_key(db, site_id)
        if not site_key:
            return
        invalidate_cached_public("public_menu", site_key=site_key, menu_key=menu_key)
    except Exception:  # la invalidación nunca debe romper la mutación
        _logger.debug("public menu cache invalidation skipped", exc_info=True)



def _invalidate_public_menu_cache(db: Session, row: models.CmsMenu) -> None:
    """Invalida la caché pública de un menú (cambios de name/is_active)."""
    _invalidate_public_menu_key(db, row.site_id, row.menu_key)



def _invalidate_public_menu_by_id_cache(db: Session, menu_id: uuid.UUID) -> None:
    """Invalida la caché pública del menú identificado por ``menu_id``.

    Cubre mutaciones que solo conocen el ``menu_id`` (crear item,
    reordenar items) y necesitan resolver el menú padre.
    """
    try:
        menu = (
            db.query(models.CmsMenu)
            .filter(models.CmsMenu.id == menu_id)
            .first()
        )
        if menu is not None:
            _invalidate_public_menu_key(db, menu.site_id, menu.menu_key)
    except Exception:  # la invalidación nunca debe romper la mutación
        _logger.debug("public menu cache invalidation skipped", exc_info=True)



def _invalidate_public_menu_item_cache(db: Session, row: models.CmsMenuItem) -> None:
    """Invalida la caché pública del menú padre de un item.

    El endpoint público filtra items por ``visibility == "public"``, así
    que editar/ocultar un item cambia la respuesta cacheada del menú al
    que pertenece.
    """
    _invalidate_public_menu_by_id_cache(db, row.menu_id)



def _invalidate_public_theme_cache(db: Session, site_id: uuid.UUID) -> None:
    """Invalida la caché pública del theme activo de un site.

    El endpoint ``public_theme`` cachea la respuesta con la key
    ``public_theme(site_key=...)``; crear/actualizar/activar/archivar un
    theme cambia qué theme (o ninguno) se sirve en público.
    """
    try:
        site_key = resolve_site_key(db, site_id)
        if not site_key:
            return
        invalidate_cached_public("public_theme", site_key=site_key)
    except Exception:  # la invalidación nunca debe romper la mutación
        _logger.debug("public theme cache invalidation skipped", exc_info=True)



def _invalidate_site_public_cache(db: Session, site_id: uuid.UUID) -> None:
    """Invalida TODO el contenido público cacheado de un site.

    Usado por ``archive_cms_site``/``update_cms_site`` (al desactivar el
    site): menús, theme, páginas (detail + listado) y posts (detail +
    listado) dejan de servirse en el endpoint público. Las keys de
    listado incluyen query params (skip/limit/category/tag), así que se
    borran por patrón; las keys de detalle se reconstruyen por slug.
    Resuelve ``site_key`` una sola vez (evita N+1).
    """
    try:
        site_key = resolve_site_key(db, site_id)
        if not site_key:
            return
        # Menús
        menu_keys = (
            db.query(models.CmsMenu.menu_key)
            .filter(models.CmsMenu.site_id == site_id)
            .all()
        )
        for (menu_key,) in menu_keys:
            invalidate_cached_public("public_menu", site_key=site_key, menu_key=menu_key)
        # Theme
        invalidate_cached_public("public_theme", site_key=site_key)
        # Páginas (detail por slug + listado por patrón)
        page_slugs = (
            db.query(models.CmsPage.slug)
            .filter(models.CmsPage.site_id == site_id)
            .all()
        )
        for (slug,) in page_slugs:
            invalidate_cached_public("public_page", site_key=site_key, slug=slug)
        invalidate_cached_public_pattern("public_pages_list")
        # Posts (detail por slug + listado por patrón)
        post_slugs = (
            db.query(models.CmsPost.slug)
            .filter(models.CmsPost.site_id == site_id)
            .all()
        )
        for (slug,) in post_slugs:
            invalidate_cached_public("public_post", site_key=site_key, slug=slug)
        invalidate_cached_public_pattern("public_posts_list")
    except Exception:  # la invalidación nunca debe romper la mutación
        _logger.debug("site public cache invalidation skipped", exc_info=True)



def list_cms_menu_items(db: Session, menu_id: uuid.UUID):
    return (
        db.query(models.CmsMenuItem)
        .filter(models.CmsMenuItem.menu_id == menu_id)
        .order_by(models.CmsMenuItem.sort_order.asc(), models.CmsMenuItem.id.asc())
        .all()
    )



def create_cms_menu_item(
    db: Session,
    menu_id: uuid.UUID,
    payload: schemas.CmsMenuItemCreate,
    *,
    commit_with_conflict_check: bool = False,
    actor_user_id=None,
):
    if actor_user_id is not None:
        site_id = db.query(models.CmsMenu.site_id).filter(models.CmsMenu.id == menu_id).scalar()
        validate_cms_actor_site(db, actor_user_id, site_id)
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
    if commit_with_conflict_check and not _commit_or_conflict(db):
        return None
    elif not commit_with_conflict_check:
        db.commit()
    db.refresh(row)
    # Cierre de staleness: un item público nuevo cambia la respuesta
    # cacheada del menú padre de inmediato.
    _invalidate_public_menu_by_id_cache(db, row.menu_id)
    return row



def get_cms_menu_item(
    db: Session,
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    *,
    site_id: uuid.UUID | None = None,
):
    """Retrieve a CMS menu item by menu and item id.

    When ``site_id`` is provided, an extra JOIN + WHERE guarantees that
    the parent ``CmsMenu`` belongs to the requested site (Axioma 3
    defense-in-depth). Existing callers that already scoped the menu
    can omit the parameter and keep the previous behavior.
    """
    query = db.query(models.CmsMenuItem).filter(
        models.CmsMenuItem.menu_id == menu_id,
        models.CmsMenuItem.id == item_id,
    )
    if site_id is not None:
        query = query.join(models.CmsMenu, models.CmsMenuItem.menu_id == models.CmsMenu.id).filter(
            models.CmsMenu.site_id == site_id
        )
    return query.first()



def update_cms_menu_item(db: Session, row: models.CmsMenuItem, payload: schemas.CmsMenuItemUpdate, *, actor_user_id=None):
    if actor_user_id is not None:
        site_id = db.query(models.CmsMenu.site_id).filter(models.CmsMenu.id == row.menu_id).scalar()
        validate_cms_actor_site(db, actor_user_id, site_id)
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
    # Cierre de staleness: label/href/visibility/sort_order alteran la
    # respuesta pública del menú padre.
    _invalidate_public_menu_item_cache(db, row)
    return row



def delete_cms_menu_item(db: Session, row: models.CmsMenuItem, *, actor_user_id=None) -> bool:
    if actor_user_id is not None:
        site_id = db.query(models.CmsMenu.site_id).filter(models.CmsMenu.id == row.menu_id).scalar()
        validate_cms_actor_site(db, actor_user_id, site_id)
    row.visibility = "hidden"
    db.commit()
    # Cierre de staleness: ocultar un item cambia la respuesta pública
    # del menú padre de inmediato.
    _invalidate_public_menu_item_cache(db, row)
    return True



def reorder_cms_menu_items(db: Session, menu_id: uuid.UUID, items: list[schemas.CmsMenuItemReorderItem], *, actor_user_id=None):
    if actor_user_id is not None:
        site_id = db.query(models.CmsMenu.site_id).filter(models.CmsMenu.id == menu_id).scalar()
        validate_cms_actor_site(db, actor_user_id, site_id)
    rows_by_id = {
        row.id: row for row in db.query(models.CmsMenuItem).filter(models.CmsMenuItem.menu_id == menu_id).all()
    }
    for item in items:
        row = rows_by_id.get(item.id)
        if not row:
            continue
        row.parent_id = item.parent_id
        row.sort_order = item.sort_order
    db.commit()
    # Cierre de staleness: el orden de items es parte de la respuesta
    # pública (order_by sort_order) — la caché debe refrescarse ya.
    _invalidate_public_menu_by_id_cache(db, menu_id)
    return list_cms_menu_items(db, menu_id)

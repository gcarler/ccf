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



from backend.crud.cms._shared import _commit_or_conflict


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
):
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



def update_cms_site(db: Session, row: models.CmsSite, payload: schemas.CmsSiteUpdate):
    data = payload.model_dump(exclude_unset=True)
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
    return row



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
    db: Session,
    site_id: uuid.UUID,
    payload: schemas.CmsThemeCreate,
    created_by: uuid.UUID | str | None,
):
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
    return db.query(models.CmsTheme).filter(models.CmsTheme.site_id == site_id, models.CmsTheme.id == theme_id).first()



def update_cms_theme(db: Session, row: models.CmsTheme, payload: schemas.CmsThemeUpdate):
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
    db.query(models.CmsTheme).filter(models.CmsTheme.site_id == site_id).update({"is_active": False})
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
):
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
):
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



def update_cms_menu_item(db: Session, row: models.CmsMenuItem, payload: schemas.CmsMenuItemUpdate):
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



def reorder_cms_menu_items(db: Session, menu_id: uuid.UUID, items: list[schemas.CmsMenuItemReorderItem]):
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
    return list_cms_menu_items(db, menu_id)




"""Public menu endpoints (Fase 4 refactor)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, lazyload

from backend import models
from backend.api.cms_v2._shared import (
    PUBLIC_CMS_RATE_LIMIT,
)
from backend.core.cache_v2 import cached_public
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import MenuNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_public_menus"])


@router.get(
    "/public/sites/{site_key}/menus/{menu_key}",
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_menu(site_key: str, menu_key: str, db: Session = Depends(get_db)):
    # Optimizado N+1: 1 query JOIN CmsMenu+CmsSite (evita el site lookup
    # separado de ``_get_public_site_or_404``). ``lazyload('*')`` previene el
    # selectin automático de ``CmsMenu.items`` y de las 11 relaciones hijas
    # de ``CmsSite`` — los items se cargan abajo en su propia query controlada.
    menu = (
        db.query(models.CmsMenu)
        .options(lazyload("*"))
        .join(models.CmsSite, models.CmsSite.id == models.CmsMenu.site_id)
        .filter(
            models.CmsSite.site_key == site_key.strip().lower(),
            models.CmsSite.is_active.is_(True),
            models.CmsMenu.menu_key == menu_key.strip().lower(),
            models.CmsMenu.is_active.is_(True),
        )
        .first()
    )
    if not menu:
        raise MenuNotFoundError()
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
    return {"site_key": site_key, "menu_key": menu.menu_key, "items": serialized}

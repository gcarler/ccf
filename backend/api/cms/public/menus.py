"""Public menu endpoints (Fase 4 refactor)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, lazyload

from backend import models
from backend.api.cms_v2._shared import (
    PUBLIC_CMS_RATE_LIMIT,
    _get_menu_or_404,
    _get_public_site_or_404,
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
    site = _get_public_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    if not menu.is_active:
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
    return {"site_key": site.site_key, "menu_key": menu.menu_key, "items": serialized}

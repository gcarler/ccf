"""Analytics, scheduling and image operations endpoints (Fase 4 refactor).

Extracted from the monolithic ``cms_v2/__init__.py``.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api._cms_helpers import _get_scoped_cms_media
from backend.api.cms_v2._shared import CMS_PUBLISHER_ROLES, _assert_role, _get_scoped_site_or_404
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.rate_limit import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_analytics_ops"])


# ── Page Views Tracking ──────────────────────────────────────────────────────


@router.post(
    "/track/{page_key}",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def track_page_view(page_key: str, request: Request, db: Session = Depends(get_db)):
    try:
        page = db.query(models.CmsPage).join(models.CmsSite).filter(models.CmsPage.slug == page_key, models.CmsSite.is_active.is_(True)).first()
        if page:
            db.add(models.CmsPageView(
                page_id=page.id, ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", ""), referrer=request.headers.get("referer", ""),
            ))
            db.commit()
    except Exception as exc:
        logger.warning("Analytics tracking failed for page_key=%s: %s", page_key, exc)
    return {"ok": True}


# ── Analytics ────────────────────────────────────────────────────────────────


@router.get("/analytics/{page_key}", response_model=dict)
def get_page_analytics(
    page_key: str,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    page = db.query(models.CmsPage).join(models.CmsSite).filter(models.CmsPage.slug == page_key).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    total = db.query(func.count(models.CmsPageView.id)).filter(models.CmsPageView.page_id == page.id, models.CmsPageView.created_at >= cutoff).scalar() or 0
    daily = (
        db.query(func.date(models.CmsPageView.created_at).label("date"), func.count(models.CmsPageView.id).label("views"))
        .filter(models.CmsPageView.page_id == page.id, models.CmsPageView.created_at >= cutoff)
        .group_by(func.date(models.CmsPageView.created_at)).order_by(func.date(models.CmsPageView.created_at)).all()
    )
    return {"page_key": page_key, "total_views": total, "days": days, "daily_views": [{"date": str(d), "views": v} for d, v in daily]}


# ── Scheduled Publishing ─────────────────────────────────────────────────────


@router.post("/pages/{page_id}/schedule", response_model=Dict[str, Any])
def schedule_page_publish(
    site_key: str,
    page_id: uuid.UUID,
    payload: schemas.SchedulePagePublish,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    parsed = payload.scheduled_at
    page = db.query(models.CmsPage).filter(models.CmsPage.id == page_id, models.CmsPage.site_id == site.id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    page.publish_at = parsed
    seo = page.seo_json if isinstance(page.seo_json, dict) else {}
    if isinstance(seo, dict) and "_scheduled_at" in seo:
        seo.pop("_scheduled_at", None)
        page.seo_json = seo
    db.commit()
    db.refresh(page)
    return {"ok": True, "publish_at": parsed.isoformat()}


# ── Image Operations ─────────────────────────────────────────────────────────


@router.get(
    "/images/{media_id}/resize",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_resized_image(
    media_id: uuid.UUID,
    width: int = Query(800, le=2400),
    height: Optional[int] = None,
    quality: int = Query(80, le=100),
    db: Session = Depends(get_db),
):
    media_query = db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == media_id)
    ccf_site = crud.get_cms_site_by_key(db, "ccf")
    if ccf_site and ccf_site.sede_id is not None:
        media_query = media_query.filter(models.CmsMediaItem.sede_id == ccf_site.sede_id)
    media = media_query.first()
    if not media or (media.status or "") == "archived":
        raise HTTPException(status_code=404, detail="Media not found")
    return {"url": media.url, "width": width, "height": height, "quality": quality}


@router.post("/images/optimize", response_model=dict)
async def optimize_uploaded_image(
    media_id: uuid.UUID,
    max_width: int = Query(1920),
    quality: int = Query(80),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
    background_tasks: BackgroundTasks = None,
):
    media = _get_scoped_cms_media(db, current_user, media_id)
    if (media.status or "") == "archived":
        raise HTTPException(status_code=404, detail="Media not found")
    try:
        from PIL import Image  # noqa: F811
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Pillow (PIL) no instalado en el servidor — instale el paquete ``pillow`` para habilitar /images/optimize.",
        ) from exc
    from backend.core.config import get_settings

    settings = get_settings()
    orig_path = os.path.join(settings.uploads_dir, media.filename)
    if not os.path.exists(orig_path):
        raise HTTPException(status_code=404, detail="File not found")

    def _do_optimize():
        img = Image.open(orig_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        opt_filename = f"opt_{media.filename.rsplit('.', 1)[0]}_{max_width}w.jpg"
        opt_path = os.path.join(settings.uploads_dir, opt_filename)
        img.save(opt_path, "JPEG", quality=quality, optimize=True)

    if background_tasks is not None:
        background_tasks.add_task(_do_optimize)

    opt_filename = f"opt_{media.filename.rsplit('.', 1)[0]}_{max_width}w.jpg"
    return {
        "status": "queued",
        "url": f"/uploads/{opt_filename}",
        "media_id": str(media_id),
        "max_width": max_width,
        "quality": quality,
    }

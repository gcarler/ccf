from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, lazyload

from backend import models, schemas
from backend.api.cms_v2._shared import PUBLIC_CMS_RATE_LIMIT, _get_public_site_or_404
from backend.core.cache_v2 import cached_public
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import ThemeNotFoundError

router = APIRouter(tags=["cms_v2_public"])


@router.get(
    "/public/sites/{site_key}/theme",
    response_model=schemas.CmsThemeRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_theme(site_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    row = (
        db.query(models.CmsTheme)
        .options(lazyload("*"))
        .filter(
            models.CmsTheme.site_id == site.id,
            models.CmsTheme.is_active.is_(True),
            models.CmsTheme.status != "archived",
        )
        .order_by(models.CmsTheme.updated_at.desc())
        .first()
    )
    if not row:
        raise ThemeNotFoundError("Active theme not found")
    return schemas.CmsThemeRead.model_validate(row)

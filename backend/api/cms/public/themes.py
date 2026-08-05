from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, lazyload

from backend import models, schemas
from backend.api.cms_v2._shared import PUBLIC_CMS_RATE_LIMIT
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
    # Optimizado N+1: en lugar de 2 querys separadas (site + theme), hacemos
    # 1 sola query JOIN de CmsTheme con CmsSite filtrando por site_key. El
    # JOIN trae también ``sede`` (lazy="joined" en CmsSite.sede) en la misma
    # query. Combinado con ``lazyload('*')`` evita que el ORM dispare
    # selectin de las 11 relaciones hijas de CmsSite (themes, menus, pages,
    # posts, forms, newsletters, ...). Resultado: 1 SELECT en happy path.
    row = (
        db.query(models.CmsTheme)
        .options(lazyload("*"))
        .join(models.CmsSite, models.CmsSite.id == models.CmsTheme.site_id)
        .filter(
            models.CmsSite.site_key == site_key.strip().lower(),
            models.CmsSite.is_active.is_(True),
            models.CmsTheme.is_active.is_(True),
            models.CmsTheme.status != "archived",
        )
        .order_by(models.CmsTheme.updated_at.desc())
        .first()
    )
    if not row:
        raise ThemeNotFoundError("Active theme not found")
    return schemas.CmsThemeRead.model_validate(row)

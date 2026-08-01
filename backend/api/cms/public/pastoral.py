from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, lazyload

from backend import models, schemas
from backend.api.cms_v2._shared import _get_public_site_or_404, _pastoral_role, _slugify
from backend.core.cache_v2 import cached_public
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter

router = APIRouter(tags=["cms_v2_public"])


@router.get(
    "/public/sites/{site_key}/pastoral-team",
    response_model=List[schemas.PastoralProfileRead],
    dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))],
)
@cached_public(ttl=300)
def public_pastoral_team(site_key: str, db: Session = Depends(get_db)):
    _get_public_site_or_404(db, site_key)
    base_query = (
        db.query(models.Persona)
        .options(lazyload("*"))
        .filter(models.Persona.is_pastoral_leader.is_(True), models.Persona.is_pastoral_published.is_(True))
    )
    leaders = base_query.order_by(
        models.Persona.pastoral_sort_order.asc(),
        models.Persona.is_main_pastor.desc(),
        models.Persona.nombre_completo.asc(),
    ).all()
    result = []
    for p in leaders:
        name = p.nombre_completo
        result.append(
            schemas.PastoralProfileRead(
                id=str(p.id),
                name=name,
                slug=_slugify(name),
                photo_url=p.photo_url,
                bio_short=p.bio_short,
                bio_full=p.bio_full,
                role=_pastoral_role(p),
                social_instagram=p.social_instagram,
                social_facebook=p.social_facebook,
                social_twitter=p.social_twitter,
                is_main_pastor=p.is_main_pastor or False,
                pastoral_sort_order=getattr(p, "pastoral_sort_order", 0) or 0,
                is_pastoral_published=getattr(p, "is_pastoral_published", True),
            )
        )
    return result

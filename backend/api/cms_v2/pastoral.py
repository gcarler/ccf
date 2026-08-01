"""CMS pastoral team admin endpoints (Fase 4 refactor).

Extracted from the monolithic ``cms_v2/__init__.py``.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, lazyload

from backend import crud, models, schemas
from backend.api._cms_helpers import _get_scoped_persona, _scope_cms_pastoral_team_by_user_sede
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    _assert_role,
    _pastoral_role,
    _slugify,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_pastoral"])


# ── CMS Pastoral Team ────────────────────────────────────────────────────────


@router.get("/cms/pastoral-team", response_model=List[schemas.PastoralProfileRead])
def cms_pastoral_team_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    base_query = db.query(models.Persona).options(lazyload("*")).filter(models.Persona.is_pastoral_leader.is_(True))
    base_query = _scope_cms_pastoral_team_by_user_sede(db, current_user, base_query)
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


@router.patch("/cms/pastoral-team/{persona_id}", response_model=schemas.PastoralProfileRead)
def cms_pastoral_profile_update(
    persona_id: str,
    payload: schemas.PastoralProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    persona = _get_scoped_persona(db, current_user, persona_id)
    persona = crud.update_pastoral_profile(db, persona, payload, actor_user_id=str(current_user.id))
    name = persona.nombre_completo
    return schemas.PastoralProfileRead(
        id=str(persona.id),
        name=name,
        slug=_slugify(name),
        photo_url=persona.photo_url,
        bio_short=persona.bio_short,
        bio_full=persona.bio_full,
        role=_pastoral_role(persona),
        social_instagram=persona.social_instagram,
        social_facebook=persona.social_facebook,
        social_twitter=persona.social_twitter,
        is_main_pastor=persona.is_main_pastor or False,
        pastoral_sort_order=getattr(persona, "pastoral_sort_order", 0) or 0,
        is_pastoral_published=getattr(persona, "is_pastoral_published", True),
    )

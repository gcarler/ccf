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

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.cache_v2 import invalidate_cached_public_pattern
from backend.crud.cms._shared import (
    _actor_sede_or_none_cms,
    _crud_scope_re_check_pastoral_profile,
)

_logger = logging.getLogger(__name__)



def _normalize_social_url(val: str | None, platform: str) -> str | None:
    if not val:
        return None
    val = val.strip()
    if not val:
        return None
    if val.startswith("@"):
        handle = val[1:]
        if platform == "instagram":
            return f"https://instagram.com/{handle}"
        if platform == "facebook":
            return f"https://facebook.com/{handle}"
        if platform in ("twitter", "x"):
            return f"https://x.com/{handle}"
    if not (val.startswith("http://") or val.startswith("https://")):
        return f"https://{val}"
    return val


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
    target_persona_sede = str(persona.sede_id) if getattr(persona, "sede_id", None) else None
    _crud_scope_re_check_pastoral_profile(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_persona_id=persona.id,
        target_persona_sede=target_persona_sede,
    )
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ("role", "church_role") and value is not None:
            persona.church_role = value
        elif key == "name" and value:
            parts = value.strip().split(" ", 1)
            persona.first_name = parts[0]
            persona.last_name = parts[1] if len(parts) > 1 else ""
        elif key == "social_instagram":
            persona.social_instagram = _normalize_social_url(value, "instagram")
        elif key == "social_facebook":
            persona.social_facebook = _normalize_social_url(value, "facebook")
        elif key == "social_twitter":
            persona.social_twitter = _normalize_social_url(value, "twitter")
        elif hasattr(persona, key):
            setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    # Cierre de staleness: el perfil pastoral (bio/photo/rol/is_pastoral_*
    # /sort_order) alimenta el endpoint público cacheado
    # ``public_pastoral_team``; un PATCH admin debe reflejarse en público
    # sin esperar el TTL de 300s.
    try:
        invalidate_cached_public_pattern("public_pastoral_team")
    except Exception:  # la invalidación nunca debe romper la mutación
        _logger.warning("public pastoral team cache invalidation failed", exc_info=True)
    return persona


def create_pastoral_profile(
    db: Session,
    payload: schemas.PastoralProfileCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.Persona:
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    target_sede = actor_sede or payload.sede_id

    first_name = payload.first_name or ""
    last_name = payload.last_name or ""
    if not first_name and payload.name:
        parts = payload.name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    persona = models.Persona(
        id=uuid.uuid4(),
        sede_id=target_sede,
        first_name=first_name,
        last_name=last_name,
        church_role=payload.role or payload.church_role or "Pastor",
        is_pastoral_leader=True,
        is_pastoral_published=payload.is_pastoral_published if payload.is_pastoral_published is not None else True,
        is_main_pastor=payload.is_main_pastor or False,
        pastoral_sort_order=payload.pastoral_sort_order or 0,
        photo_url=payload.photo_url,
        bio_short=payload.bio_short,
        bio_full=payload.bio_full,
        social_instagram=_normalize_social_url(payload.social_instagram, "instagram"),
        social_facebook=_normalize_social_url(payload.social_facebook, "facebook"),
        social_twitter=_normalize_social_url(payload.social_twitter, "twitter"),
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    try:
        invalidate_cached_public_pattern("public_pastoral_team")
    except Exception:
        _logger.warning("public pastoral team cache invalidation failed", exc_info=True)
    return persona


def remove_pastoral_profile(
    db: Session,
    persona: models.Persona,
    *,
    actor_user_id: str | uuid.UUID,
) -> None:
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    target_persona_sede = str(persona.sede_id) if getattr(persona, "sede_id", None) else None
    _crud_scope_re_check_pastoral_profile(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_persona_id=persona.id,
        target_persona_sede=target_persona_sede,
    )
    persona.is_pastoral_leader = False
    persona.is_pastoral_published = False
    db.commit()
    try:
        invalidate_cached_public_pattern("public_pastoral_team")
    except Exception:
        _logger.warning("public pastoral team cache invalidation failed", exc_info=True)



def list_pastoral_team(
    db: Session,
    *,
    published_only: bool = False,
    sede_id: uuid.UUID | None = None,
):
    """Return personas that have pastoral profile data."""
    query = db.query(models.Persona).filter(
        or_(
            models.Persona.is_main_pastor.is_(True),
            models.Persona.is_pastoral_leader.is_(True),
        )
    )
    if published_only:
        query = query.filter(models.Persona.is_pastoral_published.is_(True))
    if sede_id is not None:
        query = query.filter(models.Persona.sede_id == sede_id)
    return query.order_by(
        models.Persona.pastoral_sort_order.asc(),
        models.Persona.last_name.asc(),
        models.Persona.first_name.asc(),
    ).all()


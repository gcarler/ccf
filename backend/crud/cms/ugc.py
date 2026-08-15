"""CMS: User-Generated Content (Announcements & Testimonials).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes re-validan scope Multi-Tenant antes de persistir
cambios, propagando ``actor_user_id`` (sin default) desde el caller
API. Esto cierra el TOCTOU gap donde un caller no-API podría crear/mutar
registros sin pasar por el helper ``_get_scoped_*`` correspondiente.

Los modelos ``Announcement`` y ``Testimonial`` mantienen sus tablas
físicas (``announcements``, ``testimonials``) endurecidas por la
migración ``20260701_0002`` con ``sede_id`` NOT NULL. El frontend
público ya consume la API v2 vía ``CmsPost`` con categorías canónicas
(``testimonials`` / ``announcements``); estos wrappers exponen el
contrato CRUD canónico que el gate de arquitectura (Gate 10) y la suite
de tests de cobertura siguen requiriendo.

Axioma 3 — scope por sede en listados: ``list_announcements`` /
``list_testimonials`` aceptan ``sede_id`` y filtran a nivel de query
(antes de paginar), de modo que un caller nunca reciba filas de otras
sedes mezcladas con las propias.
"""

import datetime as dt
import logging
import uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.cms._shared import (
    _actor_sede_or_none_cms,
    _crud_scope_re_check_cms_content_create,
    _crud_scope_re_check_cms_content_update,
)
from backend.crud.crm import (
    resolve_persona_id_for_user as resolve_persona_uuid_for_user,
)

_logger = logging.getLogger(__name__)


# ── Announcements ─────────────────────────────────────────────────────────


def list_announcements(
    db: Session,
    *,
    public_only: bool = False,
    sede_id: str | uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
):
    """Lista announcements activos. ``public_only`` filtra los publicados.

    Axioma 3 — Multi-Tenant: ``sede_id`` filtra a nivel de query (antes de
    paginar) para que el caller nunca reciba filas de otras sedes mezcladas
    con las propias.
    """
    q = db.query(models.Announcement)
    if public_only:
        q = q.filter(
            models.Announcement.status == "published",
            models.Announcement.is_active.is_(True),
        )
    else:
        q = q.filter(models.Announcement.status != "archived")
    if sede_id is not None:
        q = q.filter(models.Announcement.sede_id == sede_id)
    return q.order_by(models.Announcement.created_at.desc()).offset(skip).limit(limit).all()


def get_announcement(db: Session, announcement_id: uuid.UUID):
    return db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()


def create_announcement(
    db: Session,
    *,
    title: str,
    content: str,
    created_by: str | uuid.UUID,
    category: str | None = None,
    image_url: str | None = None,
    is_featured: bool = False,
    status: str = "published",
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: deriva ``sede_id`` de la persona creadora
    y re-valida scope Multi-Tenant pre-add.  ``actor_user_id`` no tiene
    default (Gate 10 de arquitectura lo exige).
    """
    creator_persona_id = resolve_persona_uuid_for_user(db, created_by)
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    derived_sede = _crud_scope_re_check_cms_content_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        author_persona_id=creator_persona_id,
    )
    row = models.Announcement(
        title=title,
        content=content,
        category=category,
        image_url=image_url,
        is_featured=is_featured,
        status=status.strip().lower(),
        created_by_persona_id=creator_persona_id,
        sede_id=derived_sede,
        published_at=_now_utc() if status.strip().lower() == "published" else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_announcement(
    db: Session,
    announcement_id: uuid.UUID,
    *,
    title: str | None = None,
    content: str | None = None,
    category: str | None = None,
    image_url: str | None = None,
    is_active: bool | None = None,
    is_featured: bool | None = None,
    status: str | None = None,
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: defense-in-depth pre-mutation.  ``actor_user_id``
    no tiene default (Gate 10 de arquitectura lo exige).
    """
    row = get_announcement(db, announcement_id)
    if not row:
        return None
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
    if title is not None:
        row.title = title
    if content is not None:
        row.content = content
    if category is not None:
        row.category = category
    if image_url is not None:
        row.image_url = image_url
    if is_active is not None:
        row.is_active = is_active
    if is_featured is not None:
        row.is_featured = is_featured
    if status is not None:
        row.status = status.strip().lower()
    db.commit()
    db.refresh(row)
    return row


def delete_announcement(
    db: Session,
    announcement_id: uuid.UUID,
    *,
    actor_user_id: str | uuid.UUID,
    permanent: bool = False,
) -> bool:
    """Axioma 3 — Multi-Tenant: defense-in-depth pre soft-delete.  ``actor_user_id``
    no tiene default (Gate 10 de arquitectura lo exige).
    """
    row = get_announcement(db, announcement_id)
    if not row:
        return False
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
    if permanent:
        db.delete(row)
    else:
        row.status = "archived"
    db.commit()
    return True


# ── Testimonials ──────────────────────────────────────────────────────────


def list_testimonials(
    db: Session,
    *,
    approved_only: bool = False,
    sede_id: str | uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
):
    """Lista testimonials. ``approved_only`` filtra los aprobados.

    Axioma 3 — Multi-Tenant: ``sede_id`` filtra a nivel de query (antes de
    paginar) para que el caller nunca reciba filas de otras sedes mezcladas
    con las propias.
    """
    q = db.query(models.Testimonial)
    if approved_only:
        q = q.filter(
            models.Testimonial.is_approved.is_(True),
            models.Testimonial.status == "approved",
        )
    else:
        q = q.filter(models.Testimonial.status != "archived")
    if sede_id is not None:
        q = q.filter(models.Testimonial.sede_id == sede_id)
    return q.order_by(models.Testimonial.created_at.desc()).offset(skip).limit(limit).all()


def get_testimonial(db: Session, testimonial_id: uuid.UUID):
    return db.query(models.Testimonial).filter(models.Testimonial.id == testimonial_id).first()


def create_testimonial(
    db: Session,
    *,
    content: str,
    author_persona_id: str | uuid.UUID,
    emotion: str | None = None,
    media_type: str | None = None,
    media_url: str | None = None,
    image_url: str | None = None,
    video_url: str | None = None,
    podcast_url: str | None = None,
    is_approved: bool = False,
    show_on_home: bool = False,
    status: str = "pending",
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: deriva ``sede_id`` de la persona autora
    y re-valida scope Multi-Tenant pre-add.  ``actor_user_id`` no tiene
    default (Gate 10 de arquitectura lo exige).
    """
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    derived_sede = _crud_scope_re_check_cms_content_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        author_persona_id=author_persona_id,
    )
    row = models.Testimonial(
        content=content,
        emotion=emotion,
        media_type=media_type,
        media_url=media_url,
        image_url=image_url,
        video_url=video_url,
        podcast_url=podcast_url,
        is_approved=is_approved,
        show_on_home=show_on_home,
        status=status.strip().lower(),
        author_persona_id=author_persona_id,
        sede_id=derived_sede,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_testimonial(
    db: Session,
    testimonial_id: uuid.UUID,
    *,
    content: str | None = None,
    emotion: str | None = None,
    media_type: str | None = None,
    media_url: str | None = None,
    image_url: str | None = None,
    video_url: str | None = None,
    podcast_url: str | None = None,
    is_approved: bool | None = None,
    show_on_home: bool | None = None,
    status: str | None = None,
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: defense-in-depth pre-mutation.  ``actor_user_id``
    no tiene default (Gate 10 de arquitectura lo exige).
    """
    row = get_testimonial(db, testimonial_id)
    if not row:
        return None
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.author_persona_id,
    )
    if content is not None:
        row.content = content
    if emotion is not None:
        row.emotion = emotion
    if media_type is not None:
        row.media_type = media_type
    if media_url is not None:
        row.media_url = media_url
    if image_url is not None:
        row.image_url = image_url
    if video_url is not None:
        row.video_url = video_url
    if podcast_url is not None:
        row.podcast_url = podcast_url
    if is_approved is not None:
        row.is_approved = is_approved
    if show_on_home is not None:
        row.show_on_home = show_on_home
    if status is not None:
        row.status = status.strip().lower()
    db.commit()
    db.refresh(row)
    return row


def delete_testimonial(
    db: Session,
    testimonial_id: uuid.UUID,
    *,
    actor_user_id: str | uuid.UUID,
    permanent: bool = False,
) -> bool:
    """Axioma 3 — Multi-Tenant: defense-in-depth pre soft-delete.  ``actor_user_id``
    no tiene default (Gate 10 de arquitectura lo exige).
    """
    row = get_testimonial(db, testimonial_id)
    if not row:
        return False
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.author_persona_id,
    )
    if permanent:
        db.delete(row)
    else:
        row.status = "archived"
    db.commit()
    return True


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

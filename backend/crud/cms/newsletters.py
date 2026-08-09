"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes de User-Generated Content (Testimonial, Announcement,
CmsMediaItem) y PastoralProfile re-validan scope Multi-Tenant antes de
persistir cambios, propagando actor_user_id desde el caller API. Esto
cierra el TOCTOU gap donde un caller no-API (worker async, script de
seeding, llamada directa al CRUD) podría crear/mutar registros sin
pasar por el helper API `_get_scoped_*` correspondiente.
"""

import datetime as dt
import logging
import math
import os
import uuid

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, lazyload

from backend import models, schemas
from backend.crud._utils import _utcnow
from backend.crud.crm import (
    resolve_persona_id_for_user as resolve_persona_uuid_for_user,
)

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



def list_cms_newsletters(db: Session, site_id: uuid.UUID) -> list[models.CmsNewsletter]:
    return (
        db.query(models.CmsNewsletter)
        .filter(models.CmsNewsletter.site_id == site_id)
        .order_by(models.CmsNewsletter.created_at.desc())
        .all()
    )



def get_cms_newsletter(db: Session, site_id: uuid.UUID, newsletter_id: uuid.UUID) -> models.CmsNewsletter | None:
    return (
        db.query(models.CmsNewsletter)
        .filter(models.CmsNewsletter.site_id == site_id, models.CmsNewsletter.id == newsletter_id)
        .first()
    )



def create_cms_newsletter(
    db: Session, site_id: uuid.UUID, payload: schemas.CmsNewsletterCreate
) -> models.CmsNewsletter:
    row = models.CmsNewsletter(
        site_id=site_id,
        name=payload.name,
        subject=payload.subject,
        content_html=payload.content_html,
        status=payload.status,
        scheduled_at=payload.scheduled_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def update_cms_newsletter(
    db: Session, row: models.CmsNewsletter, payload: schemas.CmsNewsletterUpdate
) -> models.CmsNewsletter:
    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return row



def delete_cms_newsletter(db: Session, row: models.CmsNewsletter) -> bool:
    db.delete(row)
    db.commit()
    return True



def send_cms_newsletter(db: Session, row: models.CmsNewsletter) -> models.CmsNewsletter:
    active_count = (
        db.query(func.count(models.CmsSubscriber.id))
        .filter(models.CmsSubscriber.site_id == row.site_id, models.CmsSubscriber.is_active.is_(True))
        .scalar()
    ) or 0
    row.status = "sent"
    row.sent_at = _utcnow()
    row.recipient_count = active_count
    db.commit()
    db.refresh(row)

    # Attempt background email dispatch to subscribers
    subscribers = (
        db.query(models.CmsSubscriber)
        .filter(models.CmsSubscriber.site_id == row.site_id, models.CmsSubscriber.is_active.is_(True))
        .all()
    )
    try:
        from backend.services.email import send_email

        for sub in subscribers:
            if sub.email:
                send_email(
                    to=sub.email,
                    subject=row.subject,
                    html=row.content_html,
                )
    except Exception as exc:
        _logger.warning("Failed to dispatch newsletter emails: %s", exc)

    return row



def list_cms_subscribers(
    db: Session,
    site_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[models.CmsSubscriber], int]:
    query = db.query(models.CmsSubscriber).filter(models.CmsSubscriber.site_id == site_id)
    if is_active is not None:
        query = query.filter(models.CmsSubscriber.is_active == is_active)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.CmsSubscriber.email.ilike(search_term),
                models.CmsSubscriber.name.ilike(search_term),
            )
        )
    total = query.count()
    items = (
        query.order_by(models.CmsSubscriber.subscribed_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return items, total



def get_cms_subscriber(db: Session, site_id: uuid.UUID, subscriber_id: uuid.UUID) -> models.CmsSubscriber | None:
    return (
        db.query(models.CmsSubscriber)
        .filter(models.CmsSubscriber.site_id == site_id, models.CmsSubscriber.id == subscriber_id)
        .first()
    )



def create_cms_subscriber(
    db: Session, site_id: uuid.UUID, payload: schemas.CmsSubscriberCreate
) -> models.CmsSubscriber:
    email_clean = payload.email.strip().lower()
    existing = (
        db.query(models.CmsSubscriber)
        .filter(models.CmsSubscriber.site_id == site_id, models.CmsSubscriber.email == email_clean)
        .first()
    )
    if existing:
        existing.is_active = payload.is_active
        if payload.name:
            existing.name = payload.name
        existing.source = payload.source
        existing.unsubscribed_at = None if payload.is_active else _utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    row = models.CmsSubscriber(
        site_id=site_id,
        email=email_clean,
        name=payload.name,
        is_active=payload.is_active,
        source=payload.source,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def import_cms_subscribers(db: Session, site_id: uuid.UUID, payload: schemas.CmsSubscriberImportPayload) -> dict:
    imported_count = 0
    items_to_process: list[tuple[str, str | None]] = []

    if payload.subscribers:
        for s in payload.subscribers:
            if s.email and s.email.strip():
                items_to_process.append((s.email.strip().lower(), s.name))
    elif payload.emails:
        for email in payload.emails:
            if email and email.strip():
                items_to_process.append((email.strip().lower(), None))
    elif payload.csv_content:
        lines = payload.csv_content.strip().splitlines()
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if parts and parts[0] and "@" in parts[0]:
                email = parts[0].lower()
                name = parts[1] if len(parts) > 1 and parts[1] else None
                items_to_process.append((email, name))

    for email, name in items_to_process:
        existing = (
            db.query(models.CmsSubscriber)
            .filter(models.CmsSubscriber.site_id == site_id, models.CmsSubscriber.email == email)
            .first()
        )
        if existing:
            existing.is_active = True
            if name:
                existing.name = name
            existing.unsubscribed_at = None
            existing.source = "import"
        else:
            row = models.CmsSubscriber(
                site_id=site_id,
                email=email,
                name=name,
                is_active=True,
                source="import",
            )
            db.add(row)
        imported_count += 1

    db.commit()
    total_active = (
        db.query(func.count(models.CmsSubscriber.id))
        .filter(models.CmsSubscriber.site_id == site_id, models.CmsSubscriber.is_active.is_(True))
        .scalar()
    ) or 0
    return {"imported_count": imported_count, "total_subscribers": total_active}



def update_cms_subscriber(
    db: Session, row: models.CmsSubscriber, payload: schemas.CmsSubscriberUpdate
) -> models.CmsSubscriber:
    data = payload.model_dump(exclude_unset=True)
    if "is_active" in data:
        if data["is_active"] is False and row.is_active:
            row.unsubscribed_at = _utcnow()
        elif data["is_active"] is True and not row.is_active:
            row.unsubscribed_at = None
    for field, val in data.items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return row



def delete_cms_subscriber(db: Session, row: models.CmsSubscriber) -> bool:
    db.delete(row)
    db.commit()
    return True



def public_subscribe(db: Session, site_id: uuid.UUID, email: str, name: str | None = None) -> models.CmsSubscriber:
    email_clean = email.strip().lower()
    existing = (
        db.query(models.CmsSubscriber)
        .filter(models.CmsSubscriber.site_id == site_id, models.CmsSubscriber.email == email_clean)
        .first()
    )
    if existing:
        existing.is_active = True
        if name:
            existing.name = name
        existing.unsubscribed_at = None
        existing.source = "form"
        db.commit()
        db.refresh(existing)
        return existing

    row = models.CmsSubscriber(
        site_id=site_id,
        email=email_clean,
        name=name,
        is_active=True,
        source="form",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def public_unsubscribe(db: Session, email: str, site_id: uuid.UUID | None = None) -> bool:
    email_clean = email.strip().lower()
    query = db.query(models.CmsSubscriber).filter(models.CmsSubscriber.email == email_clean)
    if site_id:
        query = query.filter(models.CmsSubscriber.site_id == site_id)
    rows = query.all()
    for row in rows:
        row.is_active = False
        row.unsubscribed_at = _utcnow()
    db.commit()
    return True




"""Email Marketing / Newsletter API endpoints (R2-BE). Admin CRUD & Public Subscription/Unsubscription."""

from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    PUBLIC_CMS_RATE_LIMIT,
    _assert_role,
    _get_public_site_or_404,
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import (
    NewsletterNotFoundError,
    SubscriberNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_newsletter"])


def _get_newsletter_or_404(db: Session, site_id: UUID, newsletter_id: UUID) -> models.CmsNewsletter:
    row = crud.get_cms_newsletter(db, site_id, newsletter_id)
    if not row:
        raise NewsletterNotFoundError()
    return row


def _get_subscriber_or_404(db: Session, site_id: UUID, subscriber_id: UUID) -> models.CmsSubscriber:
    row = crud.get_cms_subscriber(db, site_id, subscriber_id)
    if not row:
        raise SubscriberNotFoundError()
    return row


# ── Public Endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/public/subscribe",
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def public_subscribe_endpoint(
    payload: schemas.CmsPublicSubscribeRequest,
    db: Session = Depends(get_db),
):
    site_key = payload.site_key or "ccf"
    site = _get_public_site_or_404(db, site_key)
    subscriber = crud.public_subscribe(db, site.id, email=payload.email, name=payload.name)
    return {
        "success": True,
        "message": "Suscripción realizada con éxito.",
        "subscriber_id": subscriber.id,
    }


@router.post(
    "/public/unsubscribe",
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def public_unsubscribe_endpoint(
    payload: schemas.CmsPublicUnsubscribeRequest,
    db: Session = Depends(get_db),
):
    site_id = None
    if payload.site_key:
        site = _get_public_site_or_404(db, payload.site_key)
        site_id = site.id
    crud.public_unsubscribe(db, email=payload.email, site_id=site_id)
    return {
        "success": True,
        "message": "Dessuscripción realizada con éxito.",
    }


# ── Admin CRUD Endpoints — Newsletters ──────────────────────────────────────


@router.get("/sites/{site_key}/newsletters", response_model=List[schemas.CmsNewsletterRead])
def list_newsletters(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_newsletters(db, site.id)


@router.post(
    "/sites/{site_key}/newsletters",
    response_model=schemas.CmsNewsletterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_newsletter(
    site_key: str,
    payload: schemas.CmsNewsletterCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.create_cms_newsletter(db, site.id, payload, actor_user_id=current_user.id)


@router.get("/sites/{site_key}/newsletters/{id}", response_model=schemas.CmsNewsletterRead)
def get_newsletter(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_newsletter_or_404(db, site.id, id)


@router.patch("/sites/{site_key}/newsletters/{id}", response_model=schemas.CmsNewsletterRead)
def update_newsletter(
    site_key: str,
    id: UUID,
    payload: schemas.CmsNewsletterUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    newsletter = _get_newsletter_or_404(db, site.id, id)
    return crud.update_cms_newsletter(db, newsletter, payload, actor_user_id=current_user.id)


@router.delete("/sites/{site_key}/newsletters/{id}", status_code=status.HTTP_200_OK)
def delete_newsletter(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    newsletter = _get_newsletter_or_404(db, site.id, id)
    crud.delete_cms_newsletter(db, newsletter, actor_user_id=current_user.id)
    return {"success": True, "message": "Boletín eliminado correctamente."}


@router.post("/sites/{site_key}/newsletters/{id}/send", response_model=schemas.CmsNewsletterRead)
def send_newsletter(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    newsletter = _get_newsletter_or_404(db, site.id, id)
    return crud.send_cms_newsletter(db, newsletter, actor_user_id=current_user.id)


# ── Admin CRUD Endpoints — Subscribers ──────────────────────────────────────


@router.get("/sites/{site_key}/subscribers")
def list_subscribers(
    site_key: str,
    only_active: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    res = crud.list_cms_subscribers(db, site.id, is_active=True if only_active else None)
    if isinstance(res, tuple):
        items, _ = res
        return items
    return res


@router.post(
    "/sites/{site_key}/subscribers",
    response_model=schemas.CmsSubscriberRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subscriber(
    site_key: str,
    payload: schemas.CmsSubscriberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.create_cms_subscriber(db, site.id, payload, actor_user_id=current_user.id)


@router.post("/sites/{site_key}/subscribers/import")
def import_subscribers(
    site_key: str,
    payload: schemas.CmsSubscriberImportPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    result = crud.import_cms_subscribers(db, site.id, payload, actor_user_id=current_user.id)
    return {"success": True, **result}


@router.get("/sites/{site_key}/subscribers/{id}", response_model=schemas.CmsSubscriberRead)
def get_subscriber(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_subscriber_or_404(db, site.id, id)


@router.patch("/sites/{site_key}/subscribers/{id}", response_model=schemas.CmsSubscriberRead)
def update_subscriber(
    site_key: str,
    id: UUID,
    payload: schemas.CmsSubscriberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    subscriber = _get_subscriber_or_404(db, site.id, id)
    return crud.update_cms_subscriber(db, subscriber, payload, actor_user_id=current_user.id)


@router.delete("/sites/{site_key}/subscribers/{id}", status_code=status.HTTP_200_OK)
def delete_subscriber(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    subscriber = _get_subscriber_or_404(db, site.id, id)
    crud.delete_cms_subscriber(db, subscriber, actor_user_id=current_user.id)
    return {"success": True, "message": "Suscriptor eliminado correctamente."}

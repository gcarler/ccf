"""Native Contact Forms API endpoints (R1-BE). Admin CRUD & Public Form Submissions."""

from __future__ import annotations

import logging
from html import escape
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    PUBLIC_CMS_RATE_LIMIT,
    _assert_role,
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import FormNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_forms"])


def _get_form_or_404(db: Session, site_id: UUID, form_id: UUID) -> models.CmsForm:
    row = crud.get_cms_form(db, site_id, form_id)
    if not row:
        raise FormNotFoundError()
    return row


# ── Public Endpoint ─────────────────────────────────────────────────────────


@router.post(
    "/public/forms/{form_id}/submit",
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def submit_public_form(
    form_id: UUID,
    payload: schemas.CmsFormSubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    form = crud.get_cms_form_by_id(db, form_id)
    if not form or not form.is_active:
        raise FormNotFoundError(detail="Form not found or inactive")

    client_ip = request.client.host if request.client else None
    submission = crud.create_cms_form_submission(db, form_id=form.id, data=payload.data, ip_address=client_ip)

    if form.notify_emails:
        try:
            from backend.services.email import send_email

            subject = f"Nueva respuesta recibida: {form.name}"
            data_summary = "<br>".join([f"<b>{escape(str(k))}:</b> {escape(str(v))}" for k, v in payload.data.items()])
            html_content = (
                f"<h2>Nueva respuesta en el formulario {escape(form.name)}</h2>"
                f"<p>Detalles de la respuesta:</p>"
                f"<div>{data_summary}</div>"
            )
            for email_addr in form.notify_emails:
                if email_addr and isinstance(email_addr, str):
                    send_email(to=email_addr, subject=subject, html=html_content)
        except Exception as exc:
            logger.warning("Failed to send form submission notification email: %s", exc)

    return {
        "success": True,
        "message": form.success_message,
        "submission_id": submission.id,
    }


# ── Admin CRUD Endpoints ─────────────────────────────────────────────────────


@router.get("/sites/{site_key}/forms", response_model=List[schemas.CmsFormRead])
def list_forms(
    site_key: str,
    only_active: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_forms(db, site.id, only_active=only_active)


@router.post(
    "/sites/{site_key}/forms",
    response_model=schemas.CmsFormRead,
    status_code=201,
)
def create_form(
    site_key: str,
    payload: schemas.CmsFormCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.create_cms_form(db, site.id, payload)


@router.get("/sites/{site_key}/forms/{form_id}", response_model=schemas.CmsFormRead)
def get_form(
    site_key: str,
    form_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_form_or_404(db, site.id, form_id)


@router.patch("/sites/{site_key}/forms/{form_id}", response_model=schemas.CmsFormRead)
@router.put("/sites/{site_key}/forms/{form_id}", response_model=schemas.CmsFormRead)
def update_form(
    site_key: str,
    form_id: UUID,
    payload: schemas.CmsFormUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    form = _get_form_or_404(db, site.id, form_id)
    return crud.update_cms_form(db, form, payload)


@router.delete("/sites/{site_key}/forms/{form_id}", status_code=204)
def delete_form(
    site_key: str,
    form_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    form = _get_form_or_404(db, site.id, form_id)
    crud.delete_cms_form(db, form)


@router.get(
    "/sites/{site_key}/forms/{form_id}/submissions",
    response_model=schemas.CmsFormSubmissionPaginated,
)
def list_form_submissions(
    site_key: str,
    form_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    _get_form_or_404(db, site.id, form_id)
    items, total = crud.list_cms_form_submissions(db, form_id, page=page, page_size=page_size)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }

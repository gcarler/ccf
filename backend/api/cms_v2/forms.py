"""Native Contact Forms API endpoints (R1-BE). Admin CRUD & Public Form Submissions."""

from __future__ import annotations

import asyncio
import logging
from html import escape
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    PUBLIC_CMS_RATE_LIMIT,
    _assert_role,
    _get_scoped_site_or_404,
)
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import FormNotFoundError
from backend.services.form_validation import ValidationError, validate_field_spec, validate_submission, verify_hcaptcha

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_forms"])


def _get_form_or_404(db: Session, site_id: UUID, form_id: UUID) -> models.CmsForm:
    row = crud.get_cms_form(db, site_id, form_id)
    if not row:
        raise FormNotFoundError()
    return row


# ── Public Endpoint V1 (sin validación server-side de fields) ────────────────


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


# ── Public Endpoint V2 (form builder dinámico — plan_de_form_builder) ───────


@router.get(
    "/public/forms/{form_id}",
    response_model=schemas.CmsFormPublicRead,
)
def public_get_form(form_id: UUID, db: Session = Depends(get_db)):
    """Render público del CmsForm: metadatos + ``fields`` para pintar.

    No requiere auth y no expone ``notify_emails``. ``captcha_site_key`` se
    expone (es pública por diseño) si ``captcha_enabled=True``.
    """
    form = crud.get_cms_form_by_id(db, form_id)
    if not form or not form.is_active:
        raise FormNotFoundError(detail="Form not found or inactive")

    settings = get_settings()
    captcha_site_key = settings.hcaptcha_site_key if form.captcha_enabled else None
    return schemas.CmsFormPublicRead(
        id=form.id,
        name=form.name,
        description=form.description,
        fields=form.fields or [],
        submit_button_text=form.submit_button_text,
        success_message=form.success_message,
        captcha_enabled=form.captcha_enabled,
        captcha_provider=form.captcha_provider or "hcaptcha",
        captcha_site_key=captcha_site_key,
        honeypot_enabled=bool(form.honeypot_enabled),
        settings_json=form.settings_json or {},
        is_active=form.is_active,
    )


@router.post(
    "/public/forms/{form_id}/submit/v2",
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def submit_public_form_v2(
    form_id: UUID,
    payload: schemas.CmsFormSubmissionCreateV2,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submit público con validación server-side de campos dinámicos.

    Flujo:
      1. Cargar ``CmsForm`` (404 si inactivo).
      2. Validar ``captcha_token`` con hCaptcha si ``captcha_enabled``.
      3. Honeypot: si ``_hp`` rellenado → 200 silencioso (bot atrapado).
      4. Validar ``data`` contra ``fields`` (tipos, required, regex, opciones,
         condicionales).
      5. Persistir + notificar por email.
    """
    form = crud.get_cms_form_by_id(db, form_id)
    if not form or not form.is_active:
        raise FormNotFoundError(detail="Form not found or inactive")

    # 1. hCaptcha
    if form.captcha_enabled:
        if not payload.captcha_token:
            raise HTTPException(status_code=400, detail={"code": "CAPTCHA_REQUIRED", "detail": "Captcha requerido"})
        remote_ip = request.client.host if request.client else None
        ok = _run_hcaptcha_sync(payload.captcha_token, remote_ip=remote_ip)
        if not ok:
            raise HTTPException(status_code=400, detail={"code": "CAPTCHA_FAILED", "detail": "Captcha inválido"})

    # 2. Honeypot — los bots lo rellenan. Manny: responder 200 para no delatar.
    if bool(form.honeypot_enabled) and payload.hp:
        logger.info("Honeypot triggered on form %s (ip=%s)", form.id, request.client.host if request.client else "?")
        return {"success": True, "message": form.success_message, "submission_id": None, "spam": True}

    # 3. Validación server-side de fields
    try:
        clean = validate_submission(
            form.fields or [],
            payload.data,
            honeypot_value=None,  # honeypot ya validado arriba
            honeypot_enabled=False,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "detail": exc.detail, "field_id": exc.field_id},
        ) from None

    # 4. Persistir
    client_ip = request.client.host if request.client else None
    submission = crud.create_cms_form_submission(db, form_id=form.id, data=clean, ip_address=client_ip)

    # 5. Notificar
    if form.notify_emails:
        try:
            from backend.services.email import send_email

            subject = f"Nueva respuesta recibida: {form.name}"
            data_summary = "<br>".join([f"<b>{escape(str(k))}:</b> {escape(str(v))}" for k, v in clean.items()])
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

    return {"success": True, "message": form.success_message, "submission_id": submission.id}


def _run_hcaptcha_sync(token: str, *, remote_ip: str | None = None) -> bool:
    """Wrapper síncrono sobre ``verify_hcaptcha`` para endpoints no-async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already inside an event loop — create a new one in a thread.
            import threading

            result: list[bool] = []

            def _runner():
                new = asyncio.new_event_loop()
                try:
                    result.append(new.run_until_complete(verify_hcaptcha(token, remote_ip=remote_ip)))
                finally:
                    new.close()

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join(timeout=15)
            return bool(result[0]) if result else False
        return loop.run_until_complete(verify_hcaptcha(token, remote_ip=remote_ip))
    except RuntimeError:
        return asyncio.run(verify_hcaptcha(token, remote_ip=remote_ip))


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
    _validate_fields_spec(payload.fields)
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
    if payload.fields is not None:
        _validate_fields_spec(payload.fields)
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


def _validate_fields_spec(fields: list[dict]) -> None:
    """Valida cada field del formulario contra ``CmsFormFieldSpec``.

    Los campos V1 (sin ``id`` o con schema viejo de 6 tipos) se aceptan
    siempre que sean coherentes. Lanza 422 si algún campo es inválido.
    """
    seen_ids: set[str] = set()
    for spec in fields or []:
        try:
            validate_field_spec(spec)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": exc.code, "detail": exc.detail, "field_id": exc.field_id},
            ) from None
        fid = (spec.get("id") or "").strip()
        if fid and fid in seen_ids:
            raise HTTPException(
                status_code=422,
                detail={"code": "DUPLICATE_FIELD_ID", "detail": f"Campo duplicado: {fid}", "field_id": fid},
            )
        if fid:
            seen_ids.add(fid)

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

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



def list_cms_forms(db: Session, site_id: uuid.UUID, *, only_active: bool = False) -> list[models.CmsForm]:
    query = db.query(models.CmsForm).filter(models.CmsForm.site_id == site_id)
    if only_active:
        query = query.filter(models.CmsForm.is_active.is_(True))
    forms = query.order_by(models.CmsForm.created_at.desc()).all()
    for form in forms:
        count = (
            db.query(func.count(models.CmsFormSubmission.id))
            .filter(models.CmsFormSubmission.form_id == form.id)
            .scalar()
        )
        setattr(form, "submission_count", count or 0)
    return forms



def get_cms_form(db: Session, site_id: uuid.UUID, form_id: uuid.UUID) -> models.CmsForm | None:
    form = db.query(models.CmsForm).filter(models.CmsForm.site_id == site_id, models.CmsForm.id == form_id).first()
    if form:
        count = (
            db.query(func.count(models.CmsFormSubmission.id))
            .filter(models.CmsFormSubmission.form_id == form.id)
            .scalar()
        )
        setattr(form, "submission_count", count or 0)
    return form



def get_cms_form_by_id(db: Session, form_id: uuid.UUID) -> models.CmsForm | None:
    return db.query(models.CmsForm).filter(models.CmsForm.id == form_id).first()



def create_cms_form(db: Session, site_id: uuid.UUID, payload: schemas.CmsFormCreate) -> models.CmsForm:
    row = models.CmsForm(
        site_id=site_id,
        name=payload.name,
        description=payload.description,
        fields=payload.fields,
        submit_button_text=payload.submit_button_text,
        success_message=payload.success_message,
        notify_emails=payload.notify_emails,
        is_active=payload.is_active,
        # plan_de_form_builder
        settings_json=payload.settings_json,
        captcha_enabled=payload.captcha_enabled,
        captcha_provider=payload.captcha_provider,
        honeypot_enabled=payload.honeypot_enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    setattr(row, "submission_count", 0)
    return row



def update_cms_form(db: Session, row: models.CmsForm, payload: schemas.CmsFormUpdate) -> models.CmsForm:
    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    count = (
        db.query(func.count(models.CmsFormSubmission.id)).filter(models.CmsFormSubmission.form_id == row.id).scalar()
    )
    setattr(row, "submission_count", count or 0)
    return row



def delete_cms_form(db: Session, row: models.CmsForm) -> bool:
    db.delete(row)
    db.commit()
    return True



def create_cms_form_submission(
    db: Session, form_id: uuid.UUID, data: dict, ip_address: str | None = None
) -> models.CmsFormSubmission:
    row = models.CmsFormSubmission(
        form_id=form_id,
        data=data,
        ip_address=ip_address,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def list_cms_form_submissions(
    db: Session, form_id: uuid.UUID, page: int = 1, page_size: int = 20
) -> tuple[list[models.CmsFormSubmission], int]:
    query = db.query(models.CmsFormSubmission).filter(models.CmsFormSubmission.form_id == form_id)
    total = query.count()
    items = (
        query.order_by(models.CmsFormSubmission.submitted_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total




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

from sqlalchemy.orm import Session

from backend import models, schemas

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



def list_cms_popups(db: Session, site_id: uuid.UUID, *, only_active: bool = False) -> list[models.CmsPopup]:
    query = db.query(models.CmsPopup).filter(models.CmsPopup.site_id == site_id)
    if only_active:
        query = query.filter(models.CmsPopup.is_active.is_(True))
    return query.order_by(models.CmsPopup.created_at.desc()).all()



def get_cms_popup(db: Session, site_id: uuid.UUID, popup_id: uuid.UUID) -> models.CmsPopup | None:
    return db.query(models.CmsPopup).filter(models.CmsPopup.site_id == site_id, models.CmsPopup.id == popup_id).first()



def create_cms_popup(db: Session, site_id: uuid.UUID, payload: schemas.CmsPopupCreate) -> models.CmsPopup:
    row = models.CmsPopup(
        site_id=site_id,
        name=payload.name,
        content_html=payload.content_html,
        trigger_type=payload.trigger_type,
        trigger_value=payload.trigger_value,
        is_active=payload.is_active,
        show_on_pages=payload.show_on_pages,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def update_cms_popup(db: Session, row: models.CmsPopup, payload: schemas.CmsPopupUpdate) -> models.CmsPopup:
    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return row



def delete_cms_popup(db: Session, row: models.CmsPopup) -> bool:
    db.delete(row)
    db.commit()
    return True




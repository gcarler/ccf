"""CMS locations admin endpoints.

Allows CMS editors and administrators to manage church campuses and sedes
displayed on /sedes, including names, addresses, cities, schedules, photos,
pastors in charge, coordinates, and map links.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, models_ops, schemas
from backend.api.cms_v2._shared import CMS_EDITOR_ROLES, _assert_role
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_module_access

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_locations"])


def _sync_locations_to_cms_section(db: Session) -> None:
    """Synchronize active ChurchLocation records into the 'feed' section of the 'locations' CMS page."""
    locations = (
        db.query(models_ops.ChurchLocation)
        .filter(models_ops.ChurchLocation.deleted_at.is_(None))
        .order_by(
            models_ops.ChurchLocation.sort_order.asc(),
            models_ops.ChurchLocation.is_main.desc(),
            models_ops.ChurchLocation.name.asc(),
        )
        .all()
    )
    items = []
    for loc in locations:
        if loc.is_active:
            items.append({
                "id": str(loc.id),
                "name": loc.name,
                "address": loc.address or "",
                "city": loc.city or "",
                "phone": loc.phone or "",
                "pastor": loc.pastor_name or "",
                "schedule": loc.schedule or "",
                "midweek": loc.midweek or "",
                "image": loc.image_url or "",
                "image_url": loc.image_url or "",
                "maps_url": loc.maps_url or "",
                "map_embed_url": loc.map_embed_url or "",
                "lat": loc.latitude,
                "lng": loc.longitude,
                "is_main": bool(loc.is_main),
            })

    pages = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.slug.in_(["locations", "sedes"]), models.CmsPage.deleted_at.is_(None))
        .all()
    )
    for page in pages:
        section = (
            db.query(models.CmsSection)
            .filter(
                models.CmsSection.page_id == page.id,
                models.CmsSection.section_key == "feed",
                models.CmsSection.deleted_at.is_(None),
            )
            .first()
        )
        if section:
            props = dict(section.props_json or {})
            props["items"] = items
            section.props_json = props
            section.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception as exc:
        logger.warning(f"Could not sync locations to cms_sections: {exc}")
        db.rollback()


def _get_location_or_404(db: Session, location_id_str: str) -> models_ops.ChurchLocation:
    try:
        lid = UUID(location_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    loc = (
        db.query(models_ops.ChurchLocation)
        .filter(models_ops.ChurchLocation.id == lid, models_ops.ChurchLocation.deleted_at.is_(None))
        .first()
    )
    if not loc:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    return loc


@router.get("/cms/locations", response_model=List[schemas.CmsLocationRead])
def cms_locations_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """List all church locations for CMS Builder management."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    locations = (
        db.query(models_ops.ChurchLocation)
        .filter(models_ops.ChurchLocation.deleted_at.is_(None))
        .order_by(
            models_ops.ChurchLocation.sort_order.asc(),
            models_ops.ChurchLocation.is_main.desc(),
            models_ops.ChurchLocation.name.asc(),
        )
        .all()
    )

    result = []
    for loc in locations:
        result.append(
            schemas.CmsLocationRead(
                id=str(loc.id),
                name=loc.name,
                address=loc.address or "",
                city=loc.city or "",
                phone=loc.phone or "",
                pastor=loc.pastor_name or "",
                schedule=loc.schedule or "",
                midweek=loc.midweek or "",
                image=loc.image_url,
                maps_url=loc.maps_url,
                map_embed_url=loc.map_embed_url,
                lat=loc.latitude,
                lng=loc.longitude,
                is_main=bool(loc.is_main),
                is_active=bool(loc.is_active),
                sort_order=getattr(loc, "sort_order", 0) or 0,
            )
        )
    return result


@router.post("/cms/locations", response_model=schemas.CmsLocationRead, status_code=201)
def cms_location_create(
    payload: schemas.CmsLocationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Create a new church location from CMS Builder."""
    _assert_role(current_user, CMS_EDITOR_ROLES)

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre de la sede es requerido")

    # If new location is designated as main, unset is_main on all other locations
    if payload.is_main:
        db.query(models_ops.ChurchLocation).filter(
            models_ops.ChurchLocation.deleted_at.is_(None)
        ).update({"is_main": False})

    loc = models_ops.ChurchLocation(
        name=name,
        address=payload.address.strip() if payload.address else "",
        city=payload.city.strip() if payload.city else None,
        phone=payload.phone.strip() if payload.phone else None,
        pastor_name=payload.pastor.strip() if payload.pastor else None,
        schedule=payload.schedule.strip() if payload.schedule else None,
        midweek=payload.midweek.strip() if payload.midweek else None,
        image_url=payload.image.strip() if payload.image else None,
        maps_url=payload.maps_url.strip() if payload.maps_url else None,
        map_embed_url=payload.map_embed_url.strip() if payload.map_embed_url else None,
        latitude=payload.lat,
        longitude=payload.lng,
        is_main=payload.is_main if payload.is_main is not None else False,
        is_active=payload.is_active if payload.is_active is not None else True,
        sort_order=payload.sort_order or 0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)

    # Sync to CMS page sections
    _sync_locations_to_cms_section(db)

    record_admin_action(
        db,
        current_user,
        action="cms.locations.create",
        resource_type="church_location",
        resource_id=str(loc.id),
        metadata={"name": loc.name, "city": loc.city},
    )

    return schemas.CmsLocationRead(
        id=str(loc.id),
        name=loc.name,
        address=loc.address or "",
        city=loc.city or "",
        phone=loc.phone or "",
        pastor=loc.pastor_name or "",
        schedule=loc.schedule or "",
        midweek=loc.midweek or "",
        image=loc.image_url,
        maps_url=loc.maps_url,
        map_embed_url=loc.map_embed_url,
        lat=loc.latitude,
        lng=loc.longitude,
        is_main=bool(loc.is_main),
        is_active=bool(loc.is_active),
        sort_order=getattr(loc, "sort_order", 0) or 0,
    )


@router.patch("/cms/locations/{location_id}", response_model=schemas.CmsLocationRead)
def cms_location_update(
    location_id: str,
    payload: schemas.CmsLocationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Update a church location from CMS Builder."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    loc = _get_location_or_404(db, location_id)

    update_data = payload.model_dump(exclude_unset=True)

    # If is_main is explicitly being set to True, clear is_main on others
    if update_data.get("is_main") is True:
        db.query(models_ops.ChurchLocation).filter(
            models_ops.ChurchLocation.id != loc.id,
            models_ops.ChurchLocation.deleted_at.is_(None),
        ).update({"is_main": False})

    field_map = {
        "name": "name",
        "address": "address",
        "city": "city",
        "phone": "phone",
        "pastor": "pastor_name",
        "schedule": "schedule",
        "midweek": "midweek",
        "image": "image_url",
        "maps_url": "maps_url",
        "map_embed_url": "map_embed_url",
        "lat": "latitude",
        "lng": "longitude",
        "is_main": "is_main",
        "is_active": "is_active",
        "sort_order": "sort_order",
    }

    for payload_key, model_col in field_map.items():
        if payload_key in update_data:
            val = update_data[payload_key]
            if isinstance(val, str):
                val = val.strip() or None
            setattr(loc, model_col, val)

    db.commit()
    db.refresh(loc)

    # Sync to CMS page sections
    _sync_locations_to_cms_section(db)

    record_admin_action(
        db,
        current_user,
        action="cms.locations.update",
        resource_type="church_location",
        resource_id=str(loc.id),
        metadata={"name": loc.name, "updated_fields": list(update_data.keys())},
    )

    return schemas.CmsLocationRead(
        id=str(loc.id),
        name=loc.name,
        address=loc.address or "",
        city=loc.city or "",
        phone=loc.phone or "",
        pastor=loc.pastor_name or "",
        schedule=loc.schedule or "",
        midweek=loc.midweek or "",
        image=loc.image_url,
        maps_url=loc.maps_url,
        map_embed_url=loc.map_embed_url,
        lat=loc.latitude,
        lng=loc.longitude,
        is_main=bool(loc.is_main),
        is_active=bool(loc.is_active),
        sort_order=getattr(loc, "sort_order", 0) or 0,
    )


@router.delete("/cms/locations/{location_id}", status_code=204)
def cms_location_delete(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Archive / soft delete a church location from CMS Builder."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    loc = _get_location_or_404(db, location_id)

    loc.deleted_at = datetime.now(timezone.utc)
    loc.is_active = False
    db.commit()

    # Sync to CMS page sections
    _sync_locations_to_cms_section(db)

    record_admin_action(
        db,
        current_user,
        action="cms.locations.delete",
        resource_type="church_location",
        resource_id=str(loc.id),
        metadata={"name": loc.name},
    )
    return None

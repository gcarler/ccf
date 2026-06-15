"""CRUD — Biblioteca de Recursos CRM (crm_resources)."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models_crm import CrmResource
from backend.schemas.crm_resources import CrmResourceCreate, CrmResourceUpdate


def list_resources(
    db: Session,
    *,
    sede_id: Optional[str] = None,
    type: Optional[str] = None,
    channel: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[CrmResource]:
    query = db.query(CrmResource).filter(CrmResource.is_active.is_(True))
    if sede_id:
        query = query.filter(CrmResource.sede_id == sede_id)
    if type:
        query = query.filter(CrmResource.type == type)
    if channel:
        query = query.filter(CrmResource.channel == channel)
    if category:
        query = query.filter(CrmResource.category == category)
    if q:
        term = f"%{q.lower()}%"
        query = query.filter(
            CrmResource.name.ilike(term) | CrmResource.body.ilike(term)
        )
    return query.order_by(CrmResource.updated_at.desc()).offset(skip).limit(limit).all()


def get_resource(db: Session, resource_id: str) -> Optional[CrmResource]:
    return (
        db.query(CrmResource)
        .filter(CrmResource.id == resource_id, CrmResource.is_active.is_(True))
        .first()
    )


def create_resource(
    db: Session,
    payload: CrmResourceCreate,
    *,
    sede_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> CrmResource:
    data = payload.model_dump()
    row = CrmResource(**data, sede_id=sede_id, created_by=created_by)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_resource(
    db: Session, resource_id: str, payload: CrmResourceUpdate
) -> Optional[CrmResource]:
    row = get_resource(db, resource_id)
    if not row:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_resource(db: Session, resource_id: str) -> bool:
    row = get_resource(db, resource_id)
    if not row:
        return False
    row.is_active = False
    db.commit()
    return True


def increment_usage(db: Session, resource_id: str) -> Optional[CrmResource]:
    row = get_resource(db, resource_id)
    if not row:
        return None
    row.usage_count = (row.usage_count or 0) + 1
    db.commit()
    db.refresh(row)
    return row

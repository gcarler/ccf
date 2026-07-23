"""Operations CRUD: church_locations, social_channels, system_variables."""

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models
from backend.models_shared import _utcnow

# ── Schemas (inline — lightweight) ─────────────────────────────────────────


class ChurchLocationCreate(BaseModel):
    name: str
    address: str | None = None
    pastor_name: str | None = None
    location_type: str | None = None


class ChurchLocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    pastor_name: str | None = None
    is_active: bool | None = None
    location_type: str | None = None


class SocialChannelCreate(BaseModel):
    platform: str
    url: str
    is_visible: bool = True


class SocialChannelUpdate(BaseModel):
    platform: str | None = None
    url: str | None = None
    is_visible: bool | None = None


class SystemVariableCreate(BaseModel):
    key: str
    value: str | None = None
    description: str | None = None


class SystemVariableUpdate(BaseModel):
    value: str | None = None
    description: str | None = None


# ── Church Locations ────────────────────────────────────────────────────────


def get_church_locations(db: Session, only_active: bool = False):
    query = db.query(models.ChurchLocation).filter(models.ChurchLocation.deleted_at.is_(None))
    if only_active:
        query = query.filter(models.ChurchLocation.is_active)
    return query.order_by(models.ChurchLocation.name).all()


def get_church_location(db: Session, location_id: UUID):
    return (
        db.query(models.ChurchLocation)
        .filter(
            models.ChurchLocation.id == location_id,
            models.ChurchLocation.deleted_at.is_(None),
        )
        .first()
    )


def create_church_location(db: Session, payload: ChurchLocationCreate):
    row = models.ChurchLocation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_church_location(
    db: Session, location_id: UUID, payload: ChurchLocationUpdate
):
    row = (
        db.query(models.ChurchLocation)
        .filter(
            models.ChurchLocation.id == location_id,
            models.ChurchLocation.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_church_location(db: Session, location_id: UUID) -> bool:
    row = (
        db.query(models.ChurchLocation)
        .filter(models.ChurchLocation.id == location_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Social Channels ─────────────────────────────────────────────────────────


def get_social_channels(db: Session, only_visible: bool = False):
    query = db.query(models.SocialChannel).filter(models.SocialChannel.deleted_at.is_(None))
    if only_visible:
        query = query.filter(models.SocialChannel.is_visible)
    return query.all()


def get_social_channel(db: Session, channel_id: UUID):
    return (
        db.query(models.SocialChannel)
        .filter(
            models.SocialChannel.id == channel_id,
            models.SocialChannel.deleted_at.is_(None),
        )
        .first()
    )


def create_social_channel(db: Session, payload: SocialChannelCreate):
    row = models.SocialChannel(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_social_channel(db: Session, channel_id: UUID, payload: SocialChannelUpdate):
    row = (
        db.query(models.SocialChannel)
        .filter(
            models.SocialChannel.id == channel_id,
            models.SocialChannel.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_social_channel(db: Session, channel_id: UUID) -> bool:
    row = (
        db.query(models.SocialChannel)
        .filter(models.SocialChannel.id == channel_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── System Variables ────────────────────────────────────────────────────────


def get_system_variables(db: Session):
    return db.query(models.SystemVariable).filter(models.SystemVariable.deleted_at.is_(None)).all()


def get_system_variable(db: Session, key: str):
    return (
        db.query(models.SystemVariable)
        .filter(
            models.SystemVariable.key == key,
            models.SystemVariable.deleted_at.is_(None),
        )
        .first()
    )


def get_system_variable_value(
    db: Session, key: str, default: str | None = None
) -> str | None:
    row = get_system_variable(db, key)
    return row.value if row else default


def create_system_variable(db: Session, payload: SystemVariableCreate):
    row = models.SystemVariable(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_system_variable(db: Session, key: str, payload: SystemVariableUpdate):
    row = (
        db.query(models.SystemVariable)
        .filter(
            models.SystemVariable.key == key,
            models.SystemVariable.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def upsert_system_variable(
    db: Session, key: str, value: str, description: str | None = None
):
    # get_system_variable already filters deleted rows.
    row = get_system_variable(db, key)
    if row:
        row.value = value
        if description is not None:
            row.description = description
    else:
        row = models.SystemVariable(key=key, value=value, description=description)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_system_variable(db: Session, key: str) -> bool:
    row = (
        db.query(models.SystemVariable)
        .filter(
            models.SystemVariable.key == key,
            models.SystemVariable.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    # Free the unique key so a new variable with the same key can be created.
    suffix = f" [deleted:{row.id}]"
    row.key = f"{row.key[: 100 - len(suffix)]}{suffix}"
    row.deleted_at = _utcnow()
    db.commit()
    return True

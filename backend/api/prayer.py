from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_active_user
from backend.crud.crm import get_user_sede_id

router = APIRouter()


@router.post("", response_model=schemas.PrayerRequest)
def create_prayer_request(
    request: schemas.PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user: "models.User" = Depends(require_active_user),
):
    sede_id = get_user_sede_id(db, current_user.id)
    row = crud.create_prayer_request(db, payload=request)
    if sede_id and not row.sede_id:
        row.sede_id = sede_id
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=List[schemas.PrayerRequest])
def read_prayer_requests(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
    current_user: "models.User" = Depends(require_active_user),
):
    """Solo devuelve pedidos publicos (is_public=True). Los privados van al CRM."""
    sede_id = get_user_sede_id(db, current_user.id)
    return (
        db.query(models.PrayerRequest)
        .filter(models.PrayerRequest.is_public)
        .filter(models.PrayerRequest.sede_id == sede_id)
        .order_by(models.PrayerRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

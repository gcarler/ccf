from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db

router = APIRouter()


@router.post("", response_model=schemas.PrayerRequest)
def create_prayer_request(
    request: schemas.PrayerRequestCreate, db: Session = Depends(get_db)
):
    return crud.create_prayer_request(db, payload=request)


@router.get("", response_model=List[schemas.PrayerRequest])
def read_prayer_requests(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """Solo devuelve pedidos publicos (is_public=True). Los privados van al CRM."""
    return (
        db.query(models.PrayerRequest)
        .filter(models.PrayerRequest.is_public == True)
        .order_by(models.PrayerRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

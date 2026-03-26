from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend import crud, schemas, models
from backend.core.database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.PrayerRequest)
def create_prayer_request(request: schemas.PrayerRequestCreate, db: Session = Depends(get_db)):
    return crud.create_prayer_request(db=db, request=request)

@router.get("/", response_model=List[schemas.PrayerRequest])
def read_prayer_requests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_prayer_requests(db=db, skip=skip, limit=limit)

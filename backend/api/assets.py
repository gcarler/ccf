from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
import datetime as dt
from backend import crud, schemas, models
from backend.core.database import get_db

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.get("/", response_model=List[dict])
def list_assets(db: Session = Depends(get_db)):
    """Lista el inventario de activos de la iglesia."""
    return crud.get_assets(db)

@router.post("/maintenance")
def register_maintenance(item_id: uuid.UUID, description: str, db: Session = Depends(get_db)):
    """Registra un log de mantenimiento para un equipo."""
    return crud.create_maintenance_log(db, item_id=item_id, description=description, service_date=dt.date.today())

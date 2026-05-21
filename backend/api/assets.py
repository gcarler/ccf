from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
import datetime as dt
from backend import crud, schemas, models
from backend.core.database import get_db

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.get("", response_model=List[dict])
def list_assets(db: Session = Depends(get_db)):
    """Lista el inventario de activos de la iglesia."""
    return crud.get_assets(db)

@router.post("/maintenance")
def register_maintenance(item_id: uuid.UUID, description: str, db: Session = Depends(get_db)):
    """Registra un log de mantenimiento para un equipo."""
    return crud.create_maintenance_log(db, item_id=item_id, description=description, service_date=dt.date.today())

@router.get("/maintenance-tasks", response_model=List[dict])
def list_maintenance_tasks(db: Session = Depends(get_db)):
    """Obtiene la lista de tareas de mantenimiento programadas."""
    # Por ahora devolvemos los logs recientes como tareas
    logs = db.query(models.MaintenanceLog).order_by(models.MaintenanceLog.service_date.desc()).all()
    result = []
    for l in logs:
        result.append({
            "id": l.id,
            "item": l.asset.name if l.asset else "Desconocido",
            "task": l.description,
            "date": l.service_date.isoformat(),
            "priority": "Alta" if "urgente" in l.description.lower() else "Media"
        })
    return result


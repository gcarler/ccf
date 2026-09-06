import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage
from backend.core.tenant import require_user_sede_id
from backend.models_evangelism import EstrategiaEvangelismo

router = APIRouter(prefix="", tags=["Evangelism Public"])

DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
}

def get_next_occurrence(dia_str, hora_str):
    if not dia_str or not hora_str:
        return None
    try:
        dia_idx = DIAS_SEMANA.get(dia_str.lower().strip())
        if dia_idx is None:
            return None
            
        hh_str, mm_str = hora_str.split(":")
        hh = int(hh_str)
        mm = int(mm_str)
        now = datetime.datetime.now(datetime.timezone.utc)
        
        days_ahead = dia_idx - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and (now.hour > hh or (now.hour == hh and now.minute >= mm))):
            days_ahead += 7
            
        next_date = now + datetime.timedelta(days=days_ahead)
        next_dt = next_date.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return next_dt
    except Exception:
        return None

@router.get("/public/upcoming-events")
def get_upcoming_public_events(db: Session = Depends(get_db)):
    estrategias = db.query(EstrategiaEvangelismo).filter(
        EstrategiaEvangelismo.is_public == True,
        EstrategiaEvangelismo.activa == True,
        EstrategiaEvangelismo.deleted_at.is_(None)
    ).all()
    
    events = []
    for est in estrategias:
        next_dt = get_next_occurrence(est.dia_reunion, est.hora_reunion)
        if next_dt:
            events.append({
                "id": str(est.id),
                "nombre": est.nombre,
                "typology": est.typology,
                "dia_reunion": est.dia_reunion,
                "hora_reunion": est.hora_reunion,
                "next_datetime": next_dt.isoformat(),
                "next_date": next_dt.strftime("%Y-%m-%d")
            })
            
    events.sort(key=lambda x: x["next_datetime"])
    return events

@router.get("/strategies/public-config")
def get_public_strategies_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage)
):
    user_sede_id = require_user_sede_id(db, current_user)
    estrategias = db.query(EstrategiaEvangelismo).filter(
        EstrategiaEvangelismo.sede_id == user_sede_id,
        EstrategiaEvangelismo.deleted_at.is_(None)
    ).order_by(EstrategiaEvangelismo.nombre).all()
    
    return [
        {
            "id": str(est.id),
            "nombre": est.nombre,
            "typology": est.typology,
            "dia_reunion": est.dia_reunion,
            "hora_reunion": est.hora_reunion,
            "is_public": est.is_public
        }
        for est in estrategias
    ]

class TogglePublicPayload(BaseModel):
    is_public: bool

@router.patch("/strategies/{estrategia_id}/toggle-public")
def toggle_public_strategy(
    estrategia_id: str,
    payload: TogglePublicPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage)
):
    user_sede_id = require_user_sede_id(db, current_user)
    est = db.query(EstrategiaEvangelismo).filter(
        EstrategiaEvangelismo.id == estrategia_id,
        EstrategiaEvangelismo.sede_id == user_sede_id,
        EstrategiaEvangelismo.deleted_at.is_(None)
    ).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
        
    est.is_public = payload.is_public
    db.commit()
    
    return {"id": str(est.id), "is_public": est.is_public}

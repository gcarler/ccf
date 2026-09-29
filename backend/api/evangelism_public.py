from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage
from backend.core.tenant import require_user_sede_id
from backend.models_evangelism import EstrategiaEvangelismo
from backend import models
import datetime
import re
import uuid as _uuid
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage
from backend.core.tenant import require_user_sede_id
from backend.models_evangelism import EstrategiaEvangelismo
from backend import models

router = APIRouter(prefix="", tags=["Evangelism Public"])

DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2, 
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
}

def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", cleaned) or "evento"

def _get_pastoral_category(nombre: str, typology: Optional[str]) -> str:
    n = nombre.lower()
    if "faro" in n or "casa" in n or "hogar" in n:
        return "Grupos de Hogar y Conexión"
    if "escuela" in n or "dominical" in n or "culto" in n or "adoracion" in n or "adoración" in n:
        return "Culto Dominical y Enseñanza"
    if "joven" in n or "juventud" in n:
        return "Reunión de Jóvenes"
    if typology == "evento_masivo":
        return "Celebración Especial"
    return "Reunión Congregacional"

def _get_event_image(nombre: str, typology: Optional[str]) -> str:
    n = nombre.lower()
    if "faro" in n or "casa" in n or "hogar" in n:
        return "/images/events/faros-en-casa.jpg"
    if "escuela" in n or "dominical" in n or "primera" in n or "segunda" in n:
        return "/images/events/escuela-dominical.jpg"
    return "/images/events/reunion-general.jpg"

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
    estrategias = (
        db.query(EstrategiaEvangelismo)
        .options(joinedload(EstrategiaEvangelismo.sede))
        .filter(
            EstrategiaEvangelismo.is_public == True,
            EstrategiaEvangelismo.activa == True,
            EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .all()
    )
    
    events = []
    for est in estrategias:
        next_dt = get_next_occurrence(est.dia_reunion, est.hora_reunion)
        if next_dt:
            sede_info = None
            if est.sede:
                sede_info = {
                    "id": str(est.sede.id),
                    "nombre": est.sede.nombre,
                    "ciudad": est.sede.ciudad or "Monterrey",
                }
            elif est.sede_id:
                sede_info = {
                    "id": str(est.sede_id),
                    "nombre": "Sede Central",
                    "ciudad": "Monterrey",
                }

            nombre = est.nombre or "Reunión CCF"
            slug = _slugify(nombre)
            pastoral_cat = _get_pastoral_category(nombre, est.typology)
            img_url = _get_event_image(nombre, est.typology)

            descripcion = est.descripcion
            if not descripcion:
                if "faro" in nombre.lower():
                    descripcion = "Un espacio cercano en hogares para orar, aprender de la Palabra y compartir la comunión en comunidad."
                elif "dominical" in nombre.lower():
                    descripcion = "Tiempo especial para alabar a Dios en familia, recibir enseñanza práctica y ser renovados en Su presencia."
                else:
                    descripcion = "Reunión semanal de edificación, alabanza y compañerismo en Comunidad Cristiana El Faro."

            events.append({
                "id": str(est.id),
                "nombre": nombre,
                "slug": slug,
                "typology": est.typology,
                "categoria_pastoral": pastoral_cat,
                "descripcion": descripcion,
                "dia_reunion": est.dia_reunion,
                "hora_reunion": est.hora_reunion,
                "next_datetime": next_dt.isoformat(),
                "next_date": next_dt.strftime("%Y-%m-%d"),
                "imagen_url": img_url,
                "sede": sede_info,
                "lugar": f"{sede_info['nombre']} ({sede_info['ciudad']})" if sede_info else "Comunidad Cristiana El Faro",
            })
            
    events.sort(key=lambda x: x["next_datetime"])
    return events

class StrategyRegistrationPayload(BaseModel):
    nombre: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    asistentes_count: int = 1
    peticion_oracion: Optional[str] = None

@router.post("/public/strategies/{strategy_id}/register")
def register_public_strategy_attendance(
    strategy_id: str,
    payload: StrategyRegistrationPayload,
    db: Session = Depends(get_db),
):
    try:
        strat_uuid = _uuid.UUID(strategy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de reunión inválido")

    est = (
        db.query(EstrategiaEvangelismo)
        .options(joinedload(EstrategiaEvangelismo.sede))
        .filter(
            EstrategiaEvangelismo.id == strat_uuid,
            EstrategiaEvangelismo.is_public == True,
            EstrategiaEvangelismo.activa == True,
            EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    if not est:
        raise HTTPException(status_code=404, detail="Reunión no encontrada o no disponible públicamente")

    next_dt = get_next_occurrence(est.dia_reunion, est.hora_reunion)

    return {
        "status": "CONFIRMED",
        "message": f"¡Gracias {payload.nombre}! Tu asistencia a {est.nombre} ha sido registrada con éxito.",
        "reunion": {
            "id": str(est.id),
            "nombre": est.nombre,
            "dia_reunion": est.dia_reunion,
            "hora_reunion": est.hora_reunion,
            "next_datetime": next_dt.isoformat() if next_dt else None,
            "lugar": est.sede.nombre if est.sede else "Comunidad Cristiana El Faro",
        },
        "asistente": {
            "nombre": payload.nombre,
            "email": payload.email,
            "telefono": payload.telefono,
            "asistentes_count": payload.asistentes_count,
        },
    }

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

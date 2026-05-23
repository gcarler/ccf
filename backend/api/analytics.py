from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/radar", response_model=schemas.PastorRadarSchema)
def get_pastor_radar(db: Session = Depends(get_db)):
    """Obtiene los KPIs de inteligencia ministerial (Radar del Pastor)."""
    radar = crud.get_pastor_radar(db)
    if not radar:
        return {
            "membresia_viva": 0,
            "bautismos_este_anio": 0,
            "estudiantes_activos": 0,
            "recaudacion_mes": 0,
        }
    return radar


@router.get("/dashboard-metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Metricas consolidadas para el dashboard administrativo."""
    return crud.get_dashboard_metrics(db)


@router.get("/events/summary")
def get_events_summary(db: Session = Depends(get_db)):
    """Resumen de eventos para reportes administrativos."""
    total_events = db.query(func.count(models.CrmEvent.id)).scalar() or 0
    total_attendees = db.query(func.count(models.EventAttendance.id)).scalar() or 0
    upcoming = (
        db.query(func.count(models.CrmEvent.id))
        .filter(models.CrmEvent.event_date >= func.date("now"))
        .scalar()
        or 0
    )
    return {
        "total_events": total_events,
        "total_attendees": total_attendees,
        "upcoming_events": upcoming,
    }

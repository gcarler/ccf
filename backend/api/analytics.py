from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend import crud, schemas
from backend.core.database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/radar", response_model=schemas.PastorRadarSchema)
def get_pastor_radar(db: Session = Depends(get_db)):
    """Obtiene los KPIs de inteligencia ministerial (Radar del Pastor)."""
    radar = crud.get_pastor_radar(db)
    if not radar:
        # Fallback si no hay datos
        return {
            "membresia_viva": 0,
            "bautismos_este_anio": 0,
            "estudiantes_activos": 0,
            "recaudacion_mes": 0
        }
    return radar

@router.get("/dashboard-metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Metricas consolidadas para el dashboard administrativo."""
    return crud.get_dashboard_metrics(db)

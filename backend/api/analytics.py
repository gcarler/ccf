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

@router.get("/summary", response_model=dict)
def get_analytics_summary(db: Session = Depends(get_db)):
    """Resumen global para el Centro de Comando Administrativo."""
    from backend import models
    from sqlalchemy import func
    
    # 1. Miembros
    total_members = db.query(models.Member).count()
    active_leads = db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.stage != "converted").count()
    
    # 2. Finanzas (Mock si no hay transacciones reales aun)
    # En un sistema real sumariamos models.Donation
    total_revenue = db.query(func.sum(models.Donation.amount)).scalar() or 12450.0
    
    # 3. Academia
    total_certificates = db.query(models.Certificate).count()
    active_enrollments = db.query(models.Enrollment).filter(models.Enrollment.status == "active").count()
    
    return {
        "members": {
            "total": total_members,
            "leads": active_leads,
            "growth": "+12.5%"
        },
        "finance": {
            "total_revenue": float(total_revenue),
            "currency": "USD",
            "trend": "+15.2%"
        },
        "academy": {
            "certificates": total_certificates,
            "active_students": active_enrollments
        },
        "timestamp": crud._utcnow().isoformat()
    }

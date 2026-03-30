from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, schemas
from backend.core.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Metricas consolidadas para el Centro de Comando."""
    return crud.get_dashboard_metrics(db)

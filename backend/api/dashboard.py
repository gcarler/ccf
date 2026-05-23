from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, schemas
from backend.core.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=schemas.AcademyDashboard)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Metricas consolidadas (Academy por defecto)."""
    return crud.get_academy_dashboard(db)


@router.get("/academy", response_model=schemas.AcademyDashboard)
def get_academy_dashboard(db: Session = Depends(get_db)):
    """Metricas del modulo de Academia."""
    return crud.get_academy_dashboard(db)


@router.get("/crm", response_model=schemas.CrmDashboard)
def get_crm_dashboard(db: Session = Depends(get_db)):
    """Metricas del modulo CRM/Pastoral."""
    return crud.get_crm_dashboard(db)


@router.get("/finance", response_model=schemas.FinanceDashboard)
def get_finance_dashboard(db: Session = Depends(get_db)):
    """Metricas del modulo de Finanzas."""
    return crud.get_finance_dashboard(db)


@router.get("/admin", response_model=schemas.AdminGlobalDashboard)
def get_admin_dashboard(db: Session = Depends(get_db)):
    """Metricas globales de administracion."""
    return crud.get_admin_dashboard(db)

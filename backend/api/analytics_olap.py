"""OLAP Analytics REST Endpoints.

Exposes high-performance DuckDB OLAP engine queries for BI and Dashboards:
- GET /api/analytics/olap/growth
- GET /api/analytics/olap/attendance-trends
- GET /api/analytics/olap/financial-summary
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_pastor_or_admin
from backend.core.tenant import get_user_sede_id
from backend.services.duckdb_engine import duckdb_analytics_service

logger = logging.getLogger("CCF-Analytics-OLAP")

router = APIRouter(prefix="/analytics/olap", tags=["Analytics OLAP"])


def _resolve_effective_sede(
    db: Session,
    current_user: models.User,
    requested_sede_id: Optional[str],
) -> Optional[str]:
    """Resolves effective sede_id based on user permissions and multitenancy rules."""
    user_sede = get_user_sede_id(db, current_user.id)
    # Check if user has global admin role
    is_admin = False
    if hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
        role_name = getattr(current_user.rol_plataforma, "nombre", "").lower()
        if "admin" in role_name or "super" in role_name:
            is_admin = True
    elif hasattr(current_user, "role") and current_user.role:
        if str(current_user.role).lower() in ("admin", "superadmin", "administrador"):
            is_admin = True

    if is_admin:
        # Admins can query any sede or cross-sede (None)
        return requested_sede_id

    # Non-admin users are scoped to their home sede
    if requested_sede_id and user_sede and str(requested_sede_id) != str(user_sede):
        logger.warning(
            "User %s attempted to query sede %s outside assigned sede %s",
            current_user.id,
            requested_sede_id,
            user_sede,
        )
        # Enforce home sede for tenant isolation
        return str(user_sede)

    return str(user_sede) if user_sede else requested_sede_id


@router.get("/growth", summary="Church growth metrics across sedes over time")
def get_growth_metrics(
    sede_id: Optional[str] = Query(None, description="Filter by Sede UUID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    group_by: str = Query("month", description="Grouping interval: day, week, month, quarter, year"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
) -> Dict[str, Any]:
    """Calculate church growth metrics across sedes over time using DuckDB in-memory OLAP engine."""
    effective_sede_id = _resolve_effective_sede(db, current_user, sede_id)
    try:
        return duckdb_analytics_service.get_church_growth_metrics(
            sede_id=effective_sede_id,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            db_session=db,
        )
    except Exception as exc:
        logger.error("Error executing DuckDB growth analytics: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate growth metrics: {exc}",
        ) from exc


@router.get("/attendance-trends", summary="Attendance trends across services and age groups")
def get_attendance_trends(
    sede_id: Optional[str] = Query(None, description="Filter by Sede UUID"),
    event_type: Optional[str] = Query(None, description="Filter by event type (DOMINICAL, ORACION, JOVENES, etc.)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    group_by: str = Query("month", description="Grouping interval: day, week, month, year"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
) -> Dict[str, Any]:
    """Calculate attendance trends and age group demographics using DuckDB in-memory OLAP engine."""
    effective_sede_id = _resolve_effective_sede(db, current_user, sede_id)
    try:
        return duckdb_analytics_service.get_attendance_trends(
            sede_id=effective_sede_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            db_session=db,
        )
    except Exception as exc:
        logger.error("Error executing DuckDB attendance analytics: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate attendance trends: {exc}",
        ) from exc


@router.get("/financial-summary", summary="Multi-year financial statements & KPI aggregations")
def get_financial_summary(
    sede_id: Optional[str] = Query(None, description="Filter by Sede UUID"),
    start_year: Optional[int] = Query(None, description="Start year (e.g. 2023)"),
    end_year: Optional[int] = Query(None, description="End year (e.g. 2026)"),
    group_by: str = Query("year", description="Grouping interval: month, quarter, year"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
) -> Dict[str, Any]:
    """Calculate multi-year financial statements and KPI aggregations using DuckDB in-memory OLAP engine."""
    effective_sede_id = _resolve_effective_sede(db, current_user, sede_id)
    try:
        return duckdb_analytics_service.get_financial_summary(
            sede_id=effective_sede_id,
            start_year=start_year,
            end_year=end_year,
            group_by=group_by,
            db_session=db,
        )
    except Exception as exc:
        logger.error("Error executing DuckDB financial analytics: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate financial summary: {exc}",
        ) from exc

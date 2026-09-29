"""API Router para Análisis de Cohortes de Retención, LTV Espiritual y Auditoría Pastoral Multi-Sede.

TKT-EVT-COHORT-RETENTION-05 (Fase 5 Super-PRO Evangelismo):
- GET /events/{event_id}/cohort-retention: Métricas de cohorte temporal (30d, 60d, 90d) y LTV espiritual de un evento.
- GET /cohorts/multi-sede: Auditoría pastoral comparativa y ranking de efectividad multi-sede.
- GET /cohorts/matrix: Matriz temporal de retención de cohortes (vista mensual).
- GET /cohorts/export: Exportación ejecutiva en CSV (UTF-8 BOM para Excel).
- GET /cohorts/attendees/{persona_id}/spiritual-journey: Línea de tiempo espiritual e hitos del asistente.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import Response as RawResponse
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_events._shared import require_event_access
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage, require_evangelism_read
from backend.core.rate_limit import academy_limiter
from backend.core.tenant import require_user_sede_id
from backend.services.event_cohort_retention_service import (
    calculate_event_cohort_retention,
    calculate_multi_sede_cohort_analysis,
    calculate_temporal_cohort_matrix,
    export_cohort_pastoral_report_csv,
    get_attendee_spiritual_journey,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/events/{event_id}/cohort-retention")
@academy_limiter.limit("60/minute")
def get_event_cohort_retention(
    request: Request,
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Retorna métricas de retención a 30, 60 y 90 días, desglose de LTV espiritual y nómina de la cohorte."""
    event = require_event_access(db, current_user, event_id)
    return calculate_event_cohort_retention(db, event)


@router.get("/cohorts/multi-sede")
@academy_limiter.limit("60/minute")
def get_multi_sede_cohorts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Auditoría pastoral multi-sede con KPIs globales, rankings y tasas de retención entre sedes."""
    user_sede_id = getattr(current_user, "sede_id", None)
    return calculate_multi_sede_cohort_analysis(db, requesting_user_sede_id=user_sede_id)


@router.get("/cohorts/matrix")
@academy_limiter.limit("60/minute")
def get_cohort_retention_matrix(
    request: Request,
    sede_id: Optional[UUID] = Query(None, description="Filtrar por sede específica"),
    months: int = Query(6, ge=1, le=24, description="Número de meses hacia atrás"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Matriz temporal de retención de cohortes para heatmap mes a mes (30d, 60d, 90d)."""
    # Si el usuario no es admin global, forzar su sede si no se especificó o restringir
    effective_sede = sede_id
    if not effective_sede and getattr(current_user, "sede_id", None):
        # Si tiene sede y se desea restringir o ver la sede
        if not getattr(current_user, "is_superuser", False) and getattr(current_user, "church_role", "") != "Pastor General":
            effective_sede = current_user.sede_id

    return calculate_temporal_cohort_matrix(db, sede_id=effective_sede, months_count=months)


@router.get("/cohorts/export")
@academy_limiter.limit("30/minute")
def export_pastoral_cohort_report(
    request: Request,
    sede_id: Optional[UUID] = Query(None, description="Filtrar por sede"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Exporta el reporte ejecutivo en CSV (con UTF-8 BOM para compatibilidad total con Excel)."""
    csv_content = export_cohort_pastoral_report_csv(db, requesting_sede_id=sede_id)

    record_admin_action(
        db,
        current_user,
        action="export_pastoral_cohort_report",
        resource_type="evangelism_cohorts",
        resource_id=str(sede_id) if sede_id else "ALL_SEDES",
    )

    filename = "ccf_auditoria_pastoral_cohortes.csv"
    return RawResponse(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/cohorts/attendees/{persona_id}/spiritual-journey")
@academy_limiter.limit("60/minute")
def get_persona_spiritual_journey(
    request: Request,
    persona_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Línea de tiempo espiritual del asistente: hitos de madurez, eventos y conexión a grupos."""
    try:
        return get_attendee_spiritual_journey(db, persona_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

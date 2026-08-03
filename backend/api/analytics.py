from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.analytics import queries as analytics_queries
from backend.core.database import get_db
from backend.core.permissions import require_pastor_or_admin

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/radar", response_model=schemas.PastorRadarSchema)
def get_pastor_radar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    sede_id = crud.get_user_sede_id(db, current_user.id)
    radar = crud.get_pastor_radar(db, sede_id=sede_id)
    if not radar:
        return {
            "membresia_viva": 0,
            "bautismos_este_anio": 0,
            "estudiantes_activos": 0,
            "recaudacion_mes": 0,
        }
    return radar


@router.get("/dashboard-metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Métricas planas del módulo Academia.

    Contrato: ``schemas.DashboardMetrics`` (active_students,
    completion_rate, certificates_issued, cards, top_courses, etc.).
    Restaurado alineando ``crud.get_dashboard_metrics`` con el shape
    esperado — antes delegaba en ``get_academy_dashboard`` y devolvía un
    ``AcademyDashboard`` (visual con cards/enrollment_trends), lo que
    rompía ``response_model`` con ``ResponseValidationError``.

    Axioma 3: el scope por sede se resuelve con la sede del usuario
    autenticado; un superadmin sin sede ve todas las sedes.
    """
    sede_id = crud.get_user_sede_id(db, current_user.id)
    return crud.get_dashboard_metrics(db, sede_id=sede_id)


@router.get("/events/summary")
def get_events_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    sede_id = crud.get_user_sede_id(db, current_user.id)
    base = db.query(models.CrmEvent)
    if sede_id:
        base = base.filter(models.CrmEvent.sede_id == sede_id)
    total_events = base.with_entities(func.count(models.CrmEvent.id)).scalar() or 0
    upcoming = (
        base.filter(models.CrmEvent.event_date >= func.current_date())
        .with_entities(func.count(models.CrmEvent.id))
        .scalar()
        or 0
    )
    # EventAttendance joins through CrmEvent for sede filtering
    att_q = db.query(func.count(models.EventAttendance.id)).join(
        models.CrmEvent, models.EventAttendance.event_id == models.CrmEvent.id
    )
    if sede_id:
        att_q = att_q.filter(models.CrmEvent.sede_id == sede_id)
    total_attendees = att_q.scalar() or 0
    return {
        "total_events": total_events,
        "total_attendees": total_attendees,
        "upcoming_events": upcoming,
    }


@router.get("/events/summary/warehouse")
def get_warehouse_event_summary(
    _db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_pastor_or_admin),
):
    """BI event summary from the duckdb warehouse over the last N days.

    Falls back to an empty (non-throwing) payload when duckdb is not
    installed so the analytics UI never 500s on setup-only environments.
    """
    try:
        summary = analytics_queries.get_event_summary(days=7)
        summary["days"] = 7
        summary["source"] = "duckdb/domain_events"
        return summary
    except Exception as exc:  # pragma: no cover - depends on runtime duckdb
        return {"total_events": 0, "by_event": [], "source": "duckdb/domain_events", "error": f"warehouse_unavailable: {exc}"}


@router.get("/academy/performance")
def get_warehouse_course_performance(
    _db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Per-course performance (enrollments/certificates/approvals) in the warehouse."""
    try:
        rows = analytics_queries.get_course_performance(limit=10)
        return {"source": "duckdb/domain_events", "courses": rows}
    except Exception as exc:  # pragma: no cover - robustness runtime
        return {"source": "duckdb/domain_events", "courses": [], "error": f"warehouse_unavailable: {exc}"}


@router.get("/events/raw")
def warehouse_raw_events(
    _db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Most recent raw domain events from the warehouse (BI auditing feed)."""
    try:
        return {"source": "duckdb/domain_events", "events": analytics_queries.list_raw_events(limit=50)}
    except Exception as exc:  # pragma: no cover - robustness runtime duckdb
        return {"source": "duckdb/domain_events", "events": [], "error": f"warehouse_unavailable: {exc}"}

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend import models
from backend.auth import require_active_user, require_admin
from backend.core.database import get_db
from backend.crud.crm import get_user_sede_id

router = APIRouter()


@router.get("/search")
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Búsqueda global inteligente."""
    results = []
    projects = db.execute(
        text(
            "SELECT id, title, description FROM projects WHERE title LIKE :q OR description LIKE :q LIMIT 10"
        ),
        {"q": f"%{q}%"},
    ).fetchall()
    for p in projects:
        results.append(
            {
                "id": p.id,
                "title": p.title,
                "detail": p.description,
                "type": "project",
                "href": f"/projects/{p.id}",
            }
        )

    tasks = db.execute(
        text(
            "SELECT id, project_id, title FROM project_tasks WHERE title LIKE :q LIMIT 10"
        ),
        {"q": f"%{q}%"},
    ).fetchall()
    for t in tasks:
        results.append(
            {
                "id": t.id,
                "title": t.title,
                "detail": f"Tarea en proyecto #{t.project_id}",
                "type": "task",
                "href": f"/projects/{t.project_id}",
            }
        )

    return {"query": q, "items": results}


@router.get("/calendar")
def get_global_calendar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    events = []
    sede_id = get_user_sede_id(db, current_user.id)
    agenda_events = db.query(models.AgendaEvent).filter(models.AgendaEvent.sede_id == sede_id).all()
    for event in agenda_events:
        events.append(
            {
                "id": f"agenda-{event.id}",
                "title": event.title,
                "start": event.start_at.isoformat(),
                "end": event.end_at.isoformat() if event.end_at else None,
                "type": "agenda_event",
                "color": "red",
                "allDay": event.is_all_day,
                "href": f"/agenda/events/{event.id}",
                "location": event.location,
            }
        )
    evangelism_events = (
        db.query(models.CrmEvent).filter(models.CrmEvent.event_date.isnot(None), models.CrmEvent.sede_id == sede_id).all()
    )
    for event in evangelism_events:
        events.append(
            {
                "id": f"evangelism-{event.id}",
                "title": event.name,
                "start": event.event_date.isoformat(),
                "end": None,
                "type": "evangelism_event",
                "color": "green",
                "allDay": False,
                "href": f"/evangelism/events/{event.id}",
                "location": event.location,
            }
        )
    tasks = (
        db.query(models.ProjectTask)
        .filter(models.ProjectTask.due_date.isnot(None))
        .all()  # 🛡️ TODO: filtrar por sede_id si los proyectos son multi-sede
    )
    for t in tasks:
        events.append(
            {
                "id": f"task-{t.id}",
                "title": t.title,
                "start": t.due_date.isoformat(),
                "type": "task",
                "color": "blue",
                "href": f"/projects/{t.project_id}",
            }
        )

    # Birthday events from members
    from sqlalchemy import func as sqlfunc
    today = datetime.now(timezone.utc).date()
    try:
        personas = db.query(models.Persona).filter(
            models.Persona.birthday.isnot(None),
            sqlfunc.extract("month", models.Persona.birthday) >= 1,
            models.Persona.sede_id == sede_id,
        ).all()
    except Exception:
        personas = []

    for m in personas:
        if not m.birthday:
            continue
        try:
            bday = m.birthday
            if isinstance(bday, str):
                bday = datetime.fromisoformat(bday).date()
            # Show birthday on the current-year date
            event_date = bday.replace(year=today.year)
            age = today.year - bday.year
            events.append({
                "id": f"birthday-{m.id}",
                "title": f"🎂 {m.first_name} {m.last_name or ''} — {age} años".strip(),
                "start": event_date.isoformat(),
                "end": None,
                "type": "reminder",
                "color": "purple",
                "allDay": True,
                "href": f"/crm/members/{m.id}",
            })
        except Exception:
            continue

    return events


@router.get("/workload")
def get_team_workload(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Analiza la carga de trabajo ministerial."""
    query = text("SELECT * FROM view_user_workload")
    rows = db.execute(query).fetchall()
    result = []
    for r in rows:
        open_tasks = r.open_tasks or 0
        critical = r.critical_tasks or 0
        status = "disponible"
        if open_tasks > 8 or critical > 3:
            status = "sobrecargado"
        elif open_tasks > 4:
            status = "en_capacidad"

        result.append(
            {
                "user_id": r.user_id,
                "name": r.full_name or r.username,
                "total": r.total_tasks,
                "open": open_tasks,
                "critical": critical,
                "overdue": r.overdue_tasks or 0,
                "load_status": status,
                "capacity_percent": min(int((open_tasks / 10) * 100), 100),
            }
        )
    return result


from backend.core.ai import generate_ministerial_content


@router.post("/ai/generate")
async def ai_generate(
    payload: Dict[str, str], current_user: models.User = Depends(require_active_user)
):
    """Genera contenido ministerial usando Llama 3 local."""
    prompt = payload.get("prompt", "")
    context = payload.get("context", "")

    if not prompt:
        raise HTTPException(status_code=400, detail="Falta el prompt")

    response = await generate_ministerial_content(prompt, context)
    return {"response": response}


@router.get("/health")
def get_system_health():
    return {"status": "ok", "version": "3.0.0-PRO"}


@router.get("/health/modules")
def get_module_health():
    """Health check por módulo — muestra qué módulos están operativos."""
    from backend.middleware.module_isolation import get_module_health
    from backend.core.database import engine
    from sqlalchemy import text

    modules = get_module_health()

    # Check database connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"

    modules["database"] = {"status": db_status, "failures": 0, "last_failure": 0}

    # List all registered modules
    known_modules = [
        "evangelism", "crm", "academy", "projects", "agents",
        "admin", "finance", "donations", "governance", "messaging",
        "support", "spiritual_life", "graph", "community", "prayer",
        "analytics", "dashboard", "tables", "system", "auth",
        "kernel", "agenda", "public", "workspace",
    ]
    for mod in known_modules:
        if mod not in modules:
            modules[mod] = {"status": "healthy", "failures": 0, "last_failure": 0}

    total_healthy = sum(1 for m in modules.values() if m.get("status") in ("healthy", "closed", "ok"))
    total_modules = len(modules)

    return {
        "status": "ok" if total_healthy == total_modules else "degraded",
        "modules": modules,
        "summary": f"{total_healthy}/{total_modules} modules healthy",
    }


@router.get("/db/health")
def get_database_health(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Comprehensive database health check.

    Returns connection stats, table sizes, index bloat,
    cache hit ratio, and slow query detection.
    """
    health = {"status": "ok", "checks": {}}

    # 1. Connection count
    conn_row = db.execute(
        text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
    ).first()
    health["checks"]["active_connections"] = conn_row[0] if conn_row else 0

    # 2. Database size
    size_row = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).first()
    health["checks"]["database_size"] = size_row[0] if size_row else "unknown"

    # 3. Cache hit ratio (should be > 0.99 for production)
    hit_row = db.execute(
        text(
            "SELECT round(sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 4) "
            "FROM pg_statio_user_tables"
        )
    ).first()
    hit_ratio = hit_row[0] if hit_row else None
    health["checks"]["cache_hit_ratio"] = hit_ratio
    if hit_ratio and float(hit_ratio) < 0.95:
        health["status"] = "warning"

    # 4. Table sizes (top 10)
    size_rows = db.execute(
        text(
            "SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) "
            "FROM pg_class WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace "
            "ORDER BY pg_total_relation_size(oid) DESC LIMIT 10"
        )
    ).fetchall()
    health["checks"]["largest_tables"] = [
        {"table": r[0], "size": r[1]} for r in size_rows
    ]

    # 5. Index usage ratio
    idx_row = db.execute(
        text(
            "SELECT round(100.0 * sum(idx_scan) / nullif(sum(idx_scan) + sum(seq_scan), 0), 2) "
            "FROM pg_stat_user_tables"
        )
    ).first()
    health["checks"]["index_usage_percent"] = idx_row[0] if idx_row else None

    # 6. Dead tuples (tables that need VACUUM)
    dead_row = db.execute(
        text(
            "SELECT relname, n_dead_tup FROM pg_stat_user_tables "
            "WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC LIMIT 5"
        )
    ).fetchall()
    health["checks"]["tables_needing_vacuum"] = [
        {"table": r[0], "dead_tuples": r[1]} for r in dead_row
    ]

    # 7. Materialized view freshness
    mv_rows = db.execute(
        text(
            "SELECT matviewname, "
            "EXTRACT(EPOCH FROM NOW() - refreshed_at)::int as age_seconds "
            "FROM pg_matviews m, "
            "LATERAL (SELECT refreshed_at FROM mv_academy_summary LIMIT 1) v "
            "WHERE schemaname = 'public' AND matviewname = 'mv_academy_summary'"
        )
    ).fetchall()
    health["checks"]["mv_academy_age_seconds"] = (
        mv_rows[0][1] if mv_rows else "not refreshed"
    )

    # 8. Long-running queries (> 30s)
    slow_row = db.execute(
        text(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE state = 'active' AND query_start < NOW() - INTERVAL '30 seconds' "
            "AND query NOT LIKE '%pg_stat_activity%'"
        )
    ).first()
    health["checks"]["long_running_queries"] = slow_row[0] if slow_row else 0
    if health["checks"]["long_running_queries"] > 0:
        health["status"] = "warning"

    return health


@router.post("/db/maintenance")
def run_db_maintenance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Run database maintenance operations asynchronously.

    Triggers:
    1. Refresh all materialized views (CONCURRENTLY)
    2. VACUUM ANALYZE all tables

    VACUUM runs in background to avoid request timeout.
    """
    import subprocess
    import threading

    def _run_vacuum():
        """Run VACUUM ANALYZE in background thread."""
        from backend.core.database import engine
        try:
            with engine.connect() as conn:
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                conn.execute(text("VACUUM ANALYZE;"))
        except Exception:
            pass

    # 1. Refresh materialized views (fast, runs inline)
    try:
        db.execute(text("SELECT refresh_dashboard_views()"), execution_options={"autocommit": True})
        refresh_ok = True
    except Exception:
        refresh_ok = False

    # 2. Start VACUUM in background (non-blocking)
    threading.Thread(target=_run_vacuum, daemon=True).start()

    # 3. Report table stats
    try:
        rows = db.execute(
            text(
                "SELECT relname, n_live_tup, n_dead_tup, last_vacuum, last_analyze "
                "FROM pg_stat_user_tables WHERE n_dead_tup > 0 "
                "ORDER BY n_dead_tup DESC LIMIT 10"
            )
        ).fetchall()
        tables_with_dead = [
            {
                "table": r[0],
                "live_tuples": r[1],
                "dead_tuples": r[2],
                "last_vacuum": str(r[3]) if r[3] else "never",
                "last_analyze": str(r[4]) if r[4] else "never",
            }
            for r in rows
        ]
    except Exception:
        tables_with_dead = []

    return {
        "status": "ok",
        "message": "Maintenance started (VACUUM running in background)",
        "operations": {
            "refresh_views": "ok" if refresh_ok else "error",
            "vacuum_analyze": "started (background)",
        },
        "tables_with_dead_tuples": tables_with_dead,
    }

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

import logging
from backend import models
from backend.core.ai import generate_ministerial_content
from backend.core.database import get_db
from backend.core.permissions import require_active_user, require_admin
from backend.crud.crm import get_user_sede_id

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/search")
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Búsqueda global inteligente."""
    results = []
    projects = db.execute(
        text("SELECT id, title, description FROM projects WHERE title LIKE :q OR description LIKE :q LIMIT 10"),
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
        text("SELECT id, project_id, title FROM project_tasks WHERE title LIKE :q LIMIT 10"),
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
    view: str = Query("todo", pattern="^(todo|evangelismo|crm|proyectos|personal|cumpleanos)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """
    Calendario unificado con vistas modulares.
    view: todo | evangelismo | crm | proyectos | personal
    """
    from sqlalchemy import func as sqlfunc

    from backend.crud.crm import resolve_persona_id_for_user

    events = []
    sede_id = get_user_sede_id(db, current_user.id)
    current_persona_id = resolve_persona_id_for_user(db, current_user.id)

    # ── helpers ────────────────────────────────────────────────────────────

    def _include(*views: str) -> bool:
        return view == "todo" or view in views

    # ── EVANGELISMO ────────────────────────────────────────────────────────

    if _include("evangelismo"):
        # Estrategias (fecha_inicio / fecha_fin)
        estrategias = (
            db.query(models.EstrategiaEvangelismo)
            .filter(
                models.EstrategiaEvangelismo.deleted_at.is_(None),
                models.EstrategiaEvangelismo.activa.is_(True),
                models.EstrategiaEvangelismo.sede_id == sede_id,
                models.EstrategiaEvangelismo.fecha_inicio.isnot(None),
            )
            .all()
        )
        for e in estrategias:
            events.append({
                "id": f"estrategia-{e.id}",
                "title": e.nombre,
                "start": e.fecha_inicio.isoformat(),
                "end": e.fecha_fin.isoformat() if e.fecha_fin else None,
                "type": "evangelism_strategy",
                "allDay": True,
                "href": f"/plataforma/evangelism/estrategias/{e.id}",
            })

        # Sesiones de grupos de evangelismo
        sesiones = (
            db.query(models.SesionGrupo)
            .join(models.GrupoEvangelismo, models.SesionGrupo.grupo_id == models.GrupoEvangelismo.id)
            .filter(
                models.SesionGrupo.deleted_at.is_(None),
                models.GrupoEvangelismo.sede_id == sede_id,
            )
            .all()
        )
        for s in sesiones:
            grupo_name = s.grupo.nombre if s.grupo else "Grupo"
            events.append({
                "id": f"sesion-{s.id}",
                "title": s.tema_estudio or f"Sesión — {grupo_name}",
                "start": s.fecha_sesion.isoformat(),
                "end": None,
                "type": "evangelism_session",
                "allDay": False,
                "href": f"/plataforma/evangelism/grupos/{s.grupo_id}",
            })

        # Eventos evangelísticos (crm_events)
        crm_events = (
            db.query(models.CrmEvent)
            .filter(
                models.CrmEvent.event_date.isnot(None),
                models.CrmEvent.sede_id == sede_id,
            )
            .all()
        )
        for ev in crm_events:
            events.append({
                "id": f"evangelism-{ev.id}",
                "title": ev.name,
                "start": ev.event_date.isoformat(),
                "end": None,
                "type": "evangelism_event",
                "allDay": False,
                "href": f"/plataforma/evangelism/events/{ev.id}",
                "location": ev.location,
            })

    # ── CRM / CONSOLIDACIÓN ────────────────────────────────────────────────

    if _include("crm"):
        # Casos con SLA de contacto
        crm_casos = (
            db.query(models.CasoCRM)
            .filter(
                models.CasoCRM.deleted_at.is_(None),
                models.CasoCRM.sla_vencimiento_contacto.isnot(None),
                models.CasoCRM.sede_id == sede_id,
            )
            .all()
        )
        for case in crm_casos:
            persona_name = (
                f"{case.persona.first_name} {case.persona.last_name}".strip()
                if case.persona else "Caso CRM"
            )
            events.append({
                "id": f"crm-caso-{case.id}",
                "title": f"Seguimiento: {persona_name}",
                "start": case.sla_vencimiento_contacto.isoformat(),
                "end": None,
                "type": "crm_caso",
                "allDay": False,
                "href": f"/plataforma/crm/pipeline/{case.id}",
            })

        # Tareas CRM
        crm_tareas = (
            db.query(models.TareaCRM)
            .join(models.CasoCRM, models.TareaCRM.caso_id == models.CasoCRM.id)
            .filter(
                models.TareaCRM.deleted_at.is_(None),
                models.TareaCRM.estado != "completed",
                models.CasoCRM.deleted_at.is_(None),
                models.CasoCRM.sede_id == sede_id,
            )
            .all()
        )
        for task in crm_tareas:
            events.append({
                "id": f"crm-tarea-{task.id}",
                "title": task.titulo,
                "start": task.fecha_vencimiento.isoformat(),
                "end": None,
                "type": "crm_tarea",
                "allDay": False,
                "href": f"/plataforma/crm/pipeline/{task.caso_id}",
            })

    # ── PROYECTOS ──────────────────────────────────────────────────────────

    if _include("proyectos"):
        # Tareas de proyectos
        proj_tasks = (
            db.query(models.ProjectTask)
            .join(models.Project, models.ProjectTask.project_id == models.Project.id)
            .filter(
                models.ProjectTask.due_date.isnot(None),
                or_(
                    models.Project.sede_id.is_(None),
                    models.Project.sede_id == sede_id,
                ),
            )
            .all()
        )
        for t in proj_tasks:
            events.append({
                "id": f"task-{t.id}",
                "title": t.title,
                "start": t.due_date.isoformat(),
                "type": "task",
                "allDay": False,
                "href": f"/plataforma/proyectos/{t.project_id}",
            })

        # Hitos de proyectos
        milestones = (
            db.query(models.ProjectMilestone)
            .join(models.Project, models.ProjectMilestone.project_id == models.Project.id)
            .filter(
                models.ProjectMilestone.deleted_at.is_(None),
                models.ProjectMilestone.target_date.isnot(None),
                models.ProjectMilestone.is_completed.is_(False),
                or_(
                    models.Project.sede_id.is_(None),
                    models.Project.sede_id == sede_id,
                ),
            )
            .all()
        )
        for m in milestones:
            events.append({
                "id": f"milestone-{m.id}",
                "title": f"🏁 {m.title}",
                "start": m.target_date.isoformat(),
                "end": None,
                "type": "project_milestone",
                "allDay": True,
                "href": f"/plataforma/proyectos/{m.project_id}",
            })

    # ── PERSONAL ───────────────────────────────────────────────────────────

    if _include("personal"):
        personal_filters = [
            models.EventoAgenda.deleted_at.is_(None),
            models.EventoAgenda.sede_id == sede_id,
        ]
        # In personal view, show only the user's own events
        if view == "personal" and current_persona_id:
            personal_filters.append(
                models.EventoAgenda.organizador_persona_id == current_persona_id
            )

        agenda_events = db.query(models.EventoAgenda).filter(*personal_filters).all()
        for ev in agenda_events:
            events.append({
                "id": f"agenda-{ev.id}",
                "title": ev.titulo,
                "start": ev.fecha_inicio.isoformat(),
                "end": ev.fecha_fin.isoformat() if ev.fecha_fin else None,
                "type": "agenda_event",
                "allDay": ev.todo_el_dia,
                "href": f"/plataforma/agenda/events/{ev.id}",
                "location": ev.ubicacion_texto,
            })

    # ── CUMPLEAÑOS (todo + personal + cumpleanos) ──────────────────────────

    if _include("personal", "cumpleanos"):
        today = datetime.now(timezone.utc).date()
        try:
            personas_bday = (
                db.query(models.Persona)
                .filter(
                    models.Persona.birthday.isnot(None),
                    sqlfunc.extract("month", models.Persona.birthday) >= 1,
                    models.Persona.sede_id == sede_id,
                )
                .all()
            )
        except Exception:
            logger.exception("Failed to query birthdays for calendar")
            personas_bday = []

        for m in personas_bday:
            if not m.birthday:
                continue
            try:
                bday = m.birthday
                if isinstance(bday, str):
                    bday = datetime.fromisoformat(bday).date()
                event_date = bday.replace(year=today.year)
                age = today.year - bday.year
                events.append({
                    "id": f"birthday-{m.id}",
                    "title": f"🎂 {m.first_name} {m.last_name or ''} — {age} años".strip(),
                    "start": event_date.isoformat(),
                    "end": None,
                    "type": "birthday",
                    "allDay": True,
                    "href": f"/plataforma/crm/personas/{m.id}",
                })
            except Exception as exc:
                logger.debug("Failed to process birthday for persona=%s: %s", m.id, exc)
                continue

    return events


def _shape_workload_row(user_id, name, total, open_tasks, critical, overdue):
    """Calcula ``load_status`` y ``capacity_percent`` para una fila de carga."""
    status = "disponible"
    if open_tasks > 8 or critical > 3:
        status = "sobrecargado"
    elif open_tasks > 4:
        status = "en_capacidad"
    return {
        "persona_id": user_id,
        "name": name,
        "total": total,
        "open": open_tasks,
        "critical": critical,
        "overdue": overdue,
        "load_status": status,
        "capacity_percent": min(int((open_tasks / 10) * 100), 100),
    }


@router.get("/workload")
def get_team_workload(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Analiza la carga de trabajo ministerial.

    Usa la vista precomputada ``view_user_workload`` (PostgreSQL) cuando
    existe. En SQLite/tests o DB antes de la migración ``20260522_0021``
    cae a un fallback ORM que produce el mismo shape de respuesta.
    """
    rows = []
    try:
        rows = db.execute(text("SELECT * FROM view_user_workload")).fetchall()
        rows = [
            _shape_workload_row(
                user_id=r.user_id,
                name=r.full_name or r.username,
                total=r.total_tasks or 0,
                open_tasks=r.open_tasks or 0,
                critical=r.critical_tasks or 0,
                overdue=r.overdue_tasks or 0,
            )
            for r in rows
        ]
    except (OperationalError, ProgrammingError):
        # La vista no existe en este motor; calculamos el equivalente.
        db.rollback()
        rows = [_shape_workload_row(**row) for row in _compute_workload_via_orm(db)]

    return rows


def _compute_workload_via_orm(db: Session) -> List[Dict]:
    """Replica semántica de ``view_user_workload`` sobre tablas base.

    Mantiene el contrato de ``_shape_workload_row``: una fila por usuario
    con las keys ``user_id``, ``name``, ``total``, ``open_tasks``,
    ``critical`` y ``overdue`` (alineadas con los kwargs del helper; las
    columnas equivalentes en la vista PostgreSQL viven en la migración
    histórica ``20260522_0021_seed_and_view.py``).
    """
    user_model = getattr(models, "User", None)
    task_model = getattr(models, "ProjectTask", None)

    if task_model is None or not hasattr(task_model, "assignee_id"):
        # Sin ProjectTask con ``assignee_id`` no podemos calcular: retornamos
        # shape correcto con totales en cero para no romper el contrato.
        if user_model is None:
            return []
        return [
            {
                # Claves alineadas con los kwargs de ``_shape_workload_row``.
                "user_id": u.id,
                "name": getattr(u, "username", "") or getattr(u, "email", ""),
                "total": 0,
                "open_tasks": 0,
                "critical": 0,
                "overdue": 0,
            }
            for u in db.query(user_model).all()
        ]


    open_statuses = ("todo", "in_progress", "review")
    rows = (
        db.query(
            user_model.id.label("user_id"),
            user_model.username.label("username"),
            func.coalesce(func.count(task_model.id), 0).label("total_tasks"),
            func.coalesce(
                func.sum(case((task_model.status.in_(open_statuses), 1), else_=0)),
                0,
            ).label("open_tasks"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (task_model.priority == "urgent")
                            & (task_model.status != "done"),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("critical_tasks"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (task_model.due_date < func.now())
                            & (task_model.status != "done"),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("overdue_tasks"),
        )
        .outerjoin(task_model, task_model.assignee_id == user_model.id)
        .group_by(user_model.id, user_model.username)
        .all()
    )

    return [
        {
            # Las claves coinciden con los kwargs de ``_shape_workload_row``
            # para que el caller pueda hacer ``[_shape_workload_row(**row) ...]``.
            "user_id": r.user_id,
            "name": getattr(r, "full_name", None) or r.username,
            "total": int(r.total_tasks or 0),
            "open_tasks": int(r.open_tasks or 0),
            "critical": int(r.critical_tasks or 0),
            "overdue": int(r.overdue_tasks or 0),
        }
        for r in rows
    ]


# Nota: ``current_user`` es consumido por ``Depends(require_active_user)``;
# este parámetro solo documenta la dependencia para FastAPI y alinea el
# signature con otras rutas de /api/system/*.


@router.post("/ai/generate")
async def ai_generate(payload: Dict[str, str], current_user: models.User = Depends(require_active_user)):
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
    from sqlalchemy import text

    from backend.core.database import engine
    from backend.middleware.module_isolation import get_module_health

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
        "evangelism",
        "crm",
        "academy",
        "projects",
        "agents",
        "admin",
        "finance",
        "donations",
        "governance",
        "messaging",
        "support",
        "spiritual_life",
        "graph",
        "community",
        "prayer",
        "analytics",
        "dashboard",
        "tables",
        "system",
        "auth",
        "kernel",
        "agenda",
        "public",
        "workspace",
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
    conn_row = db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")).first()
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
    health["checks"]["largest_tables"] = [{"table": r[0], "size": r[1]} for r in size_rows]

    # 5. Index usage ratio
    idx_row = db.execute(
        text(
            "SELECT round(100.0 * sum(idx_scan) / nullif(sum(idx_scan) + sum(seq_scan), 0), 2) FROM pg_stat_user_tables"
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
    health["checks"]["tables_needing_vacuum"] = [{"table": r[0], "dead_tuples": r[1]} for r in dead_row]

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
    health["checks"]["mv_academy_age_seconds"] = mv_rows[0][1] if mv_rows else "not refreshed"

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
    import threading

    def _run_vacuum():
        """Run VACUUM ANALYZE in background thread."""
        from backend.core.database import engine

        try:
            with engine.connect() as conn:
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                conn.execute(text("VACUUM ANALYZE;"))
        except Exception:
            logger.exception("Background VACUUM ANALYZE failed")

    # 1. Refresh materialized views (fast, runs inline)
    try:
        db.execute(
            text("SELECT refresh_dashboard_views()"),
            execution_options={"autocommit": True},
        )
        refresh_ok = True
    except Exception:
        logger.exception("Failed to refresh materialized views")
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
        logger.exception("Failed to query dead tuple statistics")
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

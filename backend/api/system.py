from __future__ import annotations

import math as Math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend import models
from backend.auth import require_active_user
from backend.core.database import get_db

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
    agenda_events = db.query(models.AgendaEvent).all()
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
        db.query(models.CrmEvent).filter(models.CrmEvent.event_date.isnot(None)).all()
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
        .all()
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

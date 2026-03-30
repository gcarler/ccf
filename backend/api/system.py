from __future__ import annotations
import math as Math
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.core.database import get_db
from backend.auth import require_active_user
from backend import models

router = APIRouter()

@router.get("/search")
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    """Búsqueda global inteligente."""
    results = []
    projects = db.execute(text("SELECT id, title, description FROM projects WHERE title LIKE :q OR description LIKE :q LIMIT 10"), {"q": f"%{q}%"}).fetchall()
    for p in projects:
        results.append({"id": p.id, "title": p.title, "detail": p.description, "type": "project", "href": f"/projects/{p.id}"})
    
    tasks = db.execute(text("SELECT id, project_id, title FROM project_tasks WHERE title LIKE :q LIMIT 10"), {"q": f"%{q}%"}).fetchall()
    for t in tasks:
        results.append({"id": t.id, "title": t.title, "detail": f"Tarea en proyecto #{t.project_id}", "type": "task", "href": f"/projects/{t.project_id}"})
    
    return {"query": q, "items": results}

@router.get("/calendar")
def get_global_calendar(db: Session = Depends(get_db), current_user: models.User = Depends(require_active_user)):
    events = []
    tasks = db.query(models.ProjectTask).filter(models.ProjectTask.due_date.isnot(None)).all()
    for t in tasks:
        events.append({"id": f"task-{t.id}", "title": t.title, "start": t.due_date.isoformat(), "type": "task", "color": "blue", "href": f"/projects/{t.project_id}"})
    return events

@router.get("/workload")
def get_team_workload(db: Session = Depends(get_db), current_user: models.User = Depends(require_active_user)):
    """Analiza la carga de trabajo ministerial."""
    query = text("SELECT * FROM view_user_workload")
    rows = db.execute(query).fetchall()
    result = []
    for r in rows:
        open_tasks = r.open_tasks or 0
        critical = r.critical_tasks or 0
        status = "disponible"
        if open_tasks > 8 or critical > 3: status = "sobrecargado"
        elif open_tasks > 4: status = "en_capacidad"
        
        result.append({
            "user_id": r.user_id,
            "name": r.full_name or r.username,
            "total": r.total_tasks,
            "open": open_tasks,
            "critical": critical,
            "overdue": r.overdue_tasks or 0,
            "load_status": status,
            "capacity_percent": min(int((open_tasks / 10) * 100), 100)
        })
    return result

@router.get("/health")
def get_system_health():
    return {"status": "ok", "version": "3.0.0-PRO"}

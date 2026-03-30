from __future__ import annotations
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from backend.core.database import get_db
from backend.auth import require_active_user, require_admin
from backend import models, crud, schemas

router = APIRouter()

@router.get("/admin/audit", response_model=List[schemas.AdminAuditLog])
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Expone los logs de auditoría para el panel de seguridad visual v3.9."""
    return crud.get_admin_audit_logs(db, limit=limit)

@router.get("/search")
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    """Búsqueda global inteligente en proyectos, tareas y miembros."""
    results = []
    
    # 1. Buscar en Proyectos (vía FTS5 si está disponible o fallback)
    projects = db.execute(text(
        "SELECT id, title, description, 'project' as type FROM projects WHERE title LIKE :q OR description LIKE :q LIMIT 10"
    ), {"q": f"%{q}%"}).fetchall()
    
    for p in projects:
        results.append({
            "id": p.id,
            "title": p.title,
            "detail": p.description,
            "type": "project",
            "href": f"/projects/{p.id}"
        })

    # 2. Buscar en Tareas
    tasks = db.execute(text(
        "SELECT id, project_id, title, 'task' as type FROM project_tasks WHERE title LIKE :q LIMIT 10"
    ), {"q": f"%{q}%"}).fetchall()
    
    for t in tasks:
        results.append({
            "id": t.id,
            "title": t.title,
            "detail": f"Tarea en proyecto #{t.project_id}",
            "type": "task",
            "href": f"/projects/{t.project_id}" # Redirigir al proyecto
        })

    # 3. Buscar en Miembros
    members = db.execute(text(
        "SELECT id, first_name, last_name, email, 'member' as type FROM members WHERE first_name LIKE :q OR last_name LIKE :q OR email LIKE :q LIMIT 10"
    ), {"q": f"%{q}%"}).fetchall()
    
    for m in members:
        results.append({
            "id": m.id,
            "title": f"{m.first_name} {m.last_name}",
            "detail": m.email,
            "type": "member",
            "href": f"/crm/members/{m.id}"
        })

    return {
        "query": q,
        "count": len(results),
        "items": results
    }

@router.get("/health")
def get_system_health():
    return {"status": "ok", "version": "3.0.0-PRO"}

@router.get("/calendar")
def get_global_calendar(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    """Unifica todas las fechas críticas de la plataforma para el Calendario Maestro."""
    events = []
    
    # 1. Tareas de Proyecto
    tasks = db.query(models.ProjectTask).filter(models.ProjectTask.due_date.isnot(None)).all()
    for t in tasks:
        events.append({
            "id": f"task-{t.id}",
            "title": t.title,
            "start": t.due_date.isoformat() if hasattr(t.due_date, 'isoformat') else t.due_date,
            "type": "task",
            "color": "blue",
            "href": f"/projects/{t.project_id}"
        })

    # 2. Eventos del CRM
    crm_events = db.query(models.CrmEvent).all()
    for e in crm_events:
        events.append({
            "id": f"crm-{e.id}",
            "title": e.title,
            "start": e.event_date.isoformat() if hasattr(e.event_date, 'isoformat') else e.event_date,
            "type": "crm",
            "color": "emerald",
            "href": "/crm/events"
        })

    # 3. Recordatorios Personales
    reminders = db.query(models.UserReminder).filter(
        models.UserReminder.user_id == current_user.id,
        models.UserReminder.is_dismissed == False
    ).all()
    for r in reminders:
        events.append({
            "id": f"rem-{r.id}",
            "title": r.title,
            "start": r.remind_at.isoformat() if hasattr(r.remind_at, 'isoformat') else r.remind_at,
            "type": "reminder",
            "color": "rose",
            "href": "/reminders"
        })

    return events

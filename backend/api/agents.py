from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend import crud, models, schemas
from backend.auth import require_admin, require_active_user
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.agents.orchestrator import AgentOrchestrator


router = APIRouter(prefix="/agents", tags=["agents"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/summary")
def analytics_summary(
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Resumen global para el Dashboard de Administración."""
    total_members = db.query(models.Member).count()
    total_projects = db.query(models.Project).count()
    total_enrollments = db.query(models.Enrollment).count()
    total_certificates = db.query(models.Certificate).count()
    pending_tasks = db.query(models.AgentTask).filter(models.AgentTask.status == "pending").count()
    unread_insights = db.query(models.AgentInsight).filter(models.AgentInsight.acknowledged == False).count()

    pending_testimonials = 0
    try:
        block = crud.get_or_create_page_content(db, "faro_testimonials_feed")
        if block and block.content:
            items = json.loads(block.content)
            if isinstance(items, list):
                pending_testimonials = sum(1 for t in items if not t.get("is_approved"))
    except Exception:
        pass

    return {
        "total_members": total_members,
        "total_projects": total_projects,
        "total_enrollments": total_enrollments,
        "total_certificates": total_certificates,
        "pending_agent_tasks": pending_tasks,
        "unread_insights": unread_insights,
        "pending_testimonials": pending_testimonials,
    }


@router.post("/tasks", response_model=schemas.AgentTask)
def create_task(
    task: schemas.AgentTaskCreate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_agent_task(db, task)
    record_admin_action(
        db,
        current_user,
        action="create_agent_task",
        resource_type="agent_task",
        resource_id=str(created.id),
        metadata={"title": created.title, "priority": created.priority},
    )
    return created


@router.get("/tasks", response_model=List[schemas.AgentTask])
def list_tasks(
    status: Optional[str] = None,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    return crud.list_agent_tasks(db, status)


@router.patch("/tasks/{task_id}", response_model=schemas.AgentTask)
def update_task(
    task_id: int,
    payload: schemas.AgentTaskUpdate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    updated = crud.update_agent_task(db, task_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    record_admin_action(
        db,
        current_user,
        action="update_agent_task",
        resource_type="agent_task",
        resource_id=str(task_id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    return updated


@router.post("/insights", response_model=schemas.AgentInsight)
def create_insight(
    insight: schemas.AgentInsightCreate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_agent_insight(db, insight)
    record_admin_action(
        db,
        current_user,
        action="create_agent_insight",
        resource_type="agent_insight",
        resource_id=str(created.id),
        metadata={"title": created.title, "type": created.insight_type},
    )
    return created


@router.get("/insights", response_model=List[schemas.AgentInsight])
def list_insights(
    acknowledged: Optional[bool] = None,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    return crud.list_agent_insights(db, acknowledged)


@router.post("/insights/{insight_id}/ack")
def acknowledge_insight(
    insight_id: int,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    insight = crud.acknowledge_insight(db, insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    record_admin_action(
        db,
        current_user,
        action="ack_agent_insight",
        resource_type="agent_insight",
        resource_id=str(insight_id),
    )
    return {"status": "ok"}


class AskRequest(BaseModel):
    query: str


@router.post("/ask")
def ask_optimus(
    payload: AskRequest,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    """
    Query the Neural MESH engine. It searches the Knowledge Base and 
    then uses AgentOrchestrator to generate a high-quality response.
    """
    # 1. Search in KB for context
    kb_results = crud.search_knowledge_base(db, payload.query)
    context = ""
    sources = []
    
    if kb_results:
        context = "\n".join([f"Source [{r.title}]: {r.content}" for r in kb_results])
        sources = [r.title for r in kb_results]

    # 2. Use Orchestrator for real AI generation if configured
    try:
        orchestrator = AgentOrchestrator()
        # Create a custom prompt combining KB context and query
        full_query = f"Context from Knowledge Base:\n{context}\n\nUser Question: {payload.query}"
        
        insight = orchestrator.run_diagnosis(
            summary=f"Consulta de usuario: {payload.query}",
            metrics={"context_length": len(context), "user": current_user.username, "full_query": full_query}
        )
        
        return {
            "answer": insight.payload,
            "sources": sources
        }
    except Exception as e:
        # Fallback to basic KB retrieval if AI fails or is not configured
        if kb_results:
            return {
                "answer": f"He encontrado informaci??n relevante en nuestra base de conocimientos: {kb_results[0].content[:500]}...",
                "sources": sources
            }
        
        return {
            "answer": "Lo siento, el motor neuronal MESH no est?? disponible en este momento y no encontr?? informaci??n en la base de datos local. ??Te gustar??a que notifique a un administrador?",
            "sources": []
        }

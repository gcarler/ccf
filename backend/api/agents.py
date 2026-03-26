from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend import crud, models, schemas
from backend.auth import require_admin, require_active_user
from backend.core.audit import record_admin_action
from backend.core.database import get_db


router = APIRouter(prefix="/agents", tags=["agents"])


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
    # 1. Search in KB
    results = crud.search_knowledge_base(db, payload.query)
    
    if not results:
        return {
            "answer": "Lo siento, no encontr?? informaci??n espec??fica sobre eso en mi base de conocimientos actual. ??Te gustar??a que asigne esta duda a un pastor?",
            "sources": []
        }
    
    # 2. Simulate AI response generation
    context = "\n".join([r.content for r in results])
    # In a real app, we would send 'context' and 'payload.query' to OpenAI/Gemini here.
    
    return {
        "answer": f"Seg??n nuestros manuales y doctrina: {results[0].content[:200]}...",
        "sources": [r.title for r in results]
    }

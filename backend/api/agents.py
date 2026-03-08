from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend import crud, models, schemas
from backend.auth import require_admin, require_active_user
from backend.core.database import get_db


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/tasks", response_model=schemas.AgentTask)
def create_task(
    task: schemas.AgentTaskCreate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.create_agent_task(db, task)


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
    return updated


@router.post("/insights", response_model=schemas.AgentInsight)
def create_insight(
    insight: schemas.AgentInsightCreate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.create_agent_insight(db, insight)


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
    return {"status": "ok"}

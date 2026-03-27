from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend import crud, models, schemas
from backend.core.database import get_db
from backend.auth import require_active_user, require_staff_or_admin

router = APIRouter()

@router.get("/", response_model=List[schemas.Project])
def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    return db.query(models.Project).offset(skip).limit(limit).all()

@router.get("/{project_id}", response_model=schemas.Project)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/tasks", response_model=schemas.ProjectTask)
def create_task(
    task: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    db_task = models.ProjectTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.patch("/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_task(
    task_id: int,
    task_update: schemas.ProjectTaskBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    db_task = db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

@router.post("/tasks/{task_id}/supplies", response_model=schemas.TaskSupply)
def add_task_supply(
    task_id: int,
    supply: schemas.TaskSupplyBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    db_supply = models.TaskSupply(**supply.model_dump(), task_id=task_id)
    db.add(db_supply)
    db.commit()
    db.refresh(db_supply)
    return db_supply

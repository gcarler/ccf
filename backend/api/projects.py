from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend import crud, schemas, models
from backend.database import get_db
from backend.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=List[schemas.Project])
def read_projects(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
):
    all_projects = crud.get_projects(db, skip=skip, limit=limit)
    # Filter by access
    if current_user.role == "admin":
        return all_projects
    
    accessible = [p for p in all_projects if crud.check_access(db, current_user, "project", "read", str(p.id))]
    return accessible

@router.post("/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not crud.check_access(db, current_user, "module", "write", "projects"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.create_project(db=db, project=project)

@router.get("/{project_id}", response_model=schemas.Project)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not crud.check_access(db, current_user, "project", "read", str(project_id)):
        raise HTTPException(status_code=403, detail="Forbidden")
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not crud.check_access(db, current_user, "project", "admin", str(project_id)):
        raise HTTPException(status_code=403, detail="Forbidden")
    success = crud.delete_project(db, project_id=project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success"}

@router.get("/{project_id}/tasks", response_model=List[schemas.ProjectTask])
def read_project_tasks(
    project_id: int,
    root_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not crud.check_access(db, current_user, "project", "read", str(project_id)):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.get_project_tasks(db, project_id=project_id, root_only=root_only)

@router.post("/{project_id}/tasks", response_model=schemas.ProjectTask)
def create_task(
    project_id: int,
    task: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if task.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    if not crud.check_access(db, current_user, "project", "write", str(project_id)):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.create_project_task(db=db, task=task)

from backend.core.audit import record_admin_action

@router.patch("/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_task(
    task_id: int,
    task_update: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Get task first to find project_id
    db_task = db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not crud.check_access(db, current_user, "project", "write", str(db_task.project_id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Convert string dates to datetime objects if present
    for key in ['due_date', 'start_date']:
        if key in task_update and task_update[key] and isinstance(task_update[key], str):
            try:
                task_update[key] = datetime.fromisoformat(task_update[key].replace('Z', '+00:00'))
            except ValueError:
                pass

    db_task = crud.update_project_task(db, task_id=task_id, task_update=task_update)
    
    # Audit log
    record_admin_action(
        db,
        current_user,
        action="update_task",
        resource_type="project_task",
        resource_id=str(task_id),
        metadata=task_update
    )
    
    return db_task

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_task = db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not crud.check_access(db, current_user, "project", "write", str(db_task.project_id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    success = crud.delete_project_task(db, task_id=task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success"}

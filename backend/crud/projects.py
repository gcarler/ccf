"""Projects and project tasks CRUD."""
from sqlalchemy.orm import Session

from backend import models, schemas


def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def create_project_task(db: Session, task: schemas.ProjectTaskCreate):
    db_task = models.ProjectTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

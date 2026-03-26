from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend import crud, schemas, models
from backend.core.database import get_db
from backend.core.config import get_settings
from backend.auth import get_current_user, require_admin


router = APIRouter()
settings = get_settings()


@router.get("/", tags=["system"])
def root():
    return {"message": "Welcome to CCF Platform API", "environment": settings.environment}


@router.get("/healthz", tags=["system"])
def healthcheck():
    return {"status": "ok"}


# -----------------
# Workspace Config
# -----------------

@router.get("/workspace/config", response_model=schemas.WorkspaceConfig, tags=["workspace"])
def read_workspace_config(db: Session = Depends(get_db)):
    config = crud.get_workspace_config(db)
    if not config:
        # Return a default empty config if none exists in DB yet
        return {
            "id": 0,
            "features_enabled": {},
            "ui_theme_config": {},
            "navigation_schema": [],
            "is_active": True,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
    return config


@router.patch("/workspace/config", response_model=schemas.WorkspaceConfig, tags=["workspace"])
def update_workspace_config(
    config_update: schemas.WorkspaceConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    return crud.update_workspace_config(db, config_update, user_id=current_user.id)

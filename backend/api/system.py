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
# Workspace Config Removed (Models Deleted)
# -----------------

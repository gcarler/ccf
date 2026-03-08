from fastapi import APIRouter

from backend.core.config import get_settings


router = APIRouter()
settings = get_settings()


@router.get("/", tags=["system"])
def root():
    return {"message": "Welcome to CCF Platform API", "environment": settings.environment}


@router.get("/healthz", tags=["system"])
def healthcheck():
    return {"status": "ok"}

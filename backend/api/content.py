from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_active_user
from backend.core.database import get_db


router = APIRouter(prefix="/content", tags=["content"])


@router.get("", response_model=List[schemas.PageContentRead])
def list_content_blocks(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_page_contents(db, limit=limit)


@router.get("/{page_key}", response_model=schemas.PageContentRead)
def get_content_block(
    page_key: str,
    db: Session = Depends(get_db),
):
    return crud.get_or_create_page_content(db, page_key)


@router.put("/{page_key}", response_model=schemas.PageContentRead)
def put_content_block(
    page_key: str,
    payload: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.update_page_content(db, page_key, payload)


@router.patch("/{page_key}", response_model=schemas.PageContentRead)
def patch_content_block(
    page_key: str,
    payload: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.update_page_content(db, page_key, payload)


@router.post("/{page_key}", response_model=schemas.PageContentRead)
def post_content_block(
    page_key: str,
    payload: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.update_page_content(db, page_key, payload)


@router.get("/{page_key}/versions", response_model=List[schemas.PageContentVersionRead])
def get_content_versions(
    page_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.get_page_content_versions(db, page_key)

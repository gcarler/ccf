"""Table Schema and View persistence API for AirTable."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_active_user

router = APIRouter(prefix="/api/tables", tags=["tables"])


# ── Models ──────────────────────────────────────────────────────────────────────

class TableSchema(BaseModel):
    """Represents a configurable table schema."""
    id: int
    name: str
    columns: List[Dict[str, Any]]
    view_name: Optional[str] = None
    created_by: int
    created_at: str


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.get("/schemas", response_model=List[Dict[str, Any]])
def list_table_schemas(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """List all saved table schemas for the current user."""
    views = (
        db.query(models.AirTableView)
        .filter(models.AirTableView.user_id == current_user.id)
        .all()
    )
    return [
        {
            "id": v.id,
            "name": v.name,
            "schema": v.schema_json,
            "filters": v.filters_json,
            "grouping": v.grouping_json,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in views
    ]


@router.post("/schemas", response_model=Dict[str, Any], status_code=201)
def create_table_schema(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Save a new table schema/view."""
    view = models.AirTableView(
        user_id=current_user.id,
        name=payload.get("name", "Untitled View"),
        schema_json=payload.get("schema", {}),
        filters_json=payload.get("filters", []),
        grouping_json=payload.get("grouping", []),
        conditional_format_json=payload.get("conditional_format", []),
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return {"id": view.id, "name": view.name}


@router.patch("/schemas/{view_id}", response_model=Dict[str, Any])
def update_table_schema(
    view_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Update a saved table schema/view."""
    view = db.query(models.AirTableView).filter(
        models.AirTableView.id == view_id,
        models.AirTableView.user_id == current_user.id,
    ).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")

    if "name" in payload:
        view.name = payload["name"]
    if "schema" in payload:
        view.schema_json = payload["schema"]
    if "filters" in payload:
        view.filters_json = payload["filters"]
    if "grouping" in payload:
        view.grouping_json = payload["grouping"]

    db.commit()
    db.refresh(view)
    return {"id": view.id, "name": view.name}


@router.delete("/schemas/{view_id}", response_model=Dict[str, Any])
def delete_table_schema(
    view_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Delete a saved table schema/view."""
    view = db.query(models.AirTableView).filter(
        models.AirTableView.id == view_id,
        models.AirTableView.user_id == current_user.id,
    ).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    db.delete(view)
    db.commit()
    return {"ok": True}

"""Table Schema and View persistence API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models_shared import _utcnow
from backend import models
from backend.crud.crm import resolve_persona_id_for_user
from backend.core.database import get_db
from backend.core.permissions import require_active_user

router = APIRouter(prefix="/tables", tags=["tables"])


def _resolve_persona(db: Session, user) -> models.Persona | None:
    persona_id = resolve_persona_id_for_user(db, getattr(user, "id", None))
    if not persona_id:
        return None
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()


# ── Models ──────────────────────────────────────────────────────────────────────

class TableSchema(BaseModel):
    """Represents a configurable table schema."""
    id: str
    name: str
    columns: List[Dict[str, Any]]
    view_name: Optional[str] = None
    created_by: str
    created_at: str


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.get("/schemas", response_model=List[Dict[str, Any]])
def list_table_schemas(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """List all saved table schemas for the current user."""
    persona = _resolve_persona(db, current_user)
    persona_id = persona.id if persona else None
    views = (
        db.query(models.SavedView)
        .filter(
            models.SavedView.persona_id == persona_id,
            models.SavedView.deleted_at.is_(None),
        )
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
    persona = _resolve_persona(db, current_user)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    view = models.SavedView(
        persona_id=persona.id,
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
    view_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Update a saved table schema/view."""
    persona = _resolve_persona(db, current_user)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    view = db.query(models.SavedView).filter(
        models.SavedView.id == view_id,
        models.SavedView.persona_id == persona.id,
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
    view_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Delete a saved table schema/view."""
    persona = _resolve_persona(db, current_user)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    view = db.query(models.SavedView).filter(
        models.SavedView.id == view_id,
        models.SavedView.persona_id == persona.id,
    ).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    view.deleted_at = _utcnow()
    db.commit()
    return {"ok": True}

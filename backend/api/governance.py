from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.permissions import require_admin
from backend.core.database import get_db

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/audit-logs", response_model=List[schemas.AdminAuditLog])
def list_audit_logs(
    limit: int = 100,
    actor_persona_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_admin_audit_logs(
        db,
        limit=limit,
        actor_persona_id=actor_persona_id,
        resource_type=resource_type,
    )

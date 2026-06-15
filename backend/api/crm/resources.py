"""CRM — Biblioteca de Recursos (plantillas de mensajes, guiones pastorales, respuestas rápidas)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import require_module_access
from backend.core.database import get_db
from backend.crud.crm import get_user_sede_id, resolve_persona_id_from_identity
from backend.crud.crm_resources import (
    create_resource,
    delete_resource,
    get_resource,
    increment_usage,
    list_resources,
    update_resource,
)
from backend.schemas.crm_resources import CrmResourceCreate, CrmResourceOut, CrmResourceUpdate

router = APIRouter(prefix="/resources", tags=["CRM"])


@router.get("", response_model=List[CrmResourceOut])
def get_resources(
    type: Optional[str] = None,
    channel: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    sede_id = get_user_sede_id(db, str(user.id))
    rows = list_resources(
        db, sede_id=sede_id, type=type, channel=channel, category=category, q=q,
        skip=skip, limit=limit,
    )
    return [CrmResourceOut.from_orm_safe(r) for r in rows]


@router.post("", response_model=CrmResourceOut, status_code=201)
def create_new_resource(
    payload: CrmResourceCreate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    sede_id = get_user_sede_id(db, str(user.id))
    persona_id = resolve_persona_id_from_identity(db, str(user.id))
    row = create_resource(db, payload, sede_id=sede_id, created_by=str(persona_id) if persona_id else None)
    return CrmResourceOut.from_orm_safe(row)


@router.get("/{resource_id}", response_model=CrmResourceOut)
def get_one_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    row = get_resource(db, resource_id)
    if not row:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return CrmResourceOut.from_orm_safe(row)


@router.patch("/{resource_id}", response_model=CrmResourceOut)
def update_one_resource(
    resource_id: str,
    payload: CrmResourceUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    row = update_resource(db, resource_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return CrmResourceOut.from_orm_safe(row)


@router.delete("/{resource_id}", status_code=204)
def delete_one_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    ok = delete_resource(db, resource_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")


@router.post("/{resource_id}/use", response_model=CrmResourceOut)
def register_use(
    resource_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    row = increment_usage(db, resource_id)
    if not row:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return CrmResourceOut.from_orm_safe(row)

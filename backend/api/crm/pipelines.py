from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_pastor_or_admin
from backend.core.tenant import require_user_sede_id
from backend.crud import crm_pipeline
from backend.schemas.crm_pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineStageCreate,
    PipelineStageResponse,
)

router = APIRouter(tags=["CRM"])


def _owned_pipeline(db: Session, pipeline_id: UUID, current_user) -> models.PipelineCRM:
    row = crm_pipeline.get_pipeline(db, pipeline_id)
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    if not row or row.sede_id != sede_id:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")
    return row


def _serialize_pipeline(row: models.PipelineCRM) -> dict:
    return {
        "id": row.id,
        "sede_id": row.sede_id,
        "name": row.nombre,
        "pipeline_type": row.tipo.value if hasattr(row.tipo, "value") else row.tipo,
        "description": row.descripcion,
        "is_active": row.activo,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _serialize_stage(row: models.EtapaPipeline) -> dict:
    return {
        "id": row.id,
        "pipeline_id": row.pipeline_id,
        "name": row.nombre,
        "order_index": row.orden,
        "requires_action": row.requiere_accion,
        "created_at": row.created_at,
    }


@router.get("/pipelines", response_model=list[PipelineResponse])
def list_pipelines(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    return [_serialize_pipeline(row) for row in crm_pipeline.list_pipelines(db, sede_id)]


@router.post("/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    row = crm_pipeline.create_pipeline(
        db,
        {
            "sede_id": sede_id,
            "nombre": payload.name,
            "tipo": payload.pipeline_type,
            "descripcion": payload.description,
            "activo": payload.is_active,
        },
    )
    return _serialize_pipeline(row)


@router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    return _serialize_pipeline(_owned_pipeline(db, pipeline_id, current_user))


@router.put("/pipelines/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(
    pipeline_id: UUID,
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    row = _owned_pipeline(db, pipeline_id, current_user)
    row = crm_pipeline.update_pipeline(
        db,
        row,
        {
            "nombre": payload.name,
            "tipo": payload.pipeline_type,
            "descripcion": payload.description,
            "activo": payload.is_active,
        },
    )
    return _serialize_pipeline(row)


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    crm_pipeline.archive_pipeline(db, _owned_pipeline(db, pipeline_id, current_user))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/pipelines/{pipeline_id}/stages", response_model=list[PipelineStageResponse])
def list_pipeline_stages(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    _owned_pipeline(db, pipeline_id, current_user)
    return [_serialize_stage(row) for row in crm_pipeline.list_stages(db, pipeline_id)]


@router.post(
    "/pipelines/{pipeline_id}/stages",
    response_model=PipelineStageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pipeline_stage(
    pipeline_id: UUID,
    payload: PipelineStageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    _owned_pipeline(db, pipeline_id, current_user)
    row = crm_pipeline.create_stage(
        db,
        {
            "pipeline_id": pipeline_id,
            "nombre": payload.name,
            "orden": payload.order_index,
            "requiere_accion": payload.requires_action,
        },
    )
    return _serialize_stage(row)


@router.put("/pipeline-stages/{stage_id}", response_model=PipelineStageResponse)
def update_pipeline_stage(
    stage_id: UUID,
    payload: PipelineStageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    row = crm_pipeline.get_stage(db, stage_id)
    if not row:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    _owned_pipeline(db, row.pipeline_id, current_user)
    row = crm_pipeline.update_stage(
        db,
        row,
        {
            "nombre": payload.name,
            "orden": payload.order_index,
            "requiere_accion": payload.requires_action,
        },
    )
    return _serialize_stage(row)


@router.delete("/pipeline-stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_pipeline_stage(
    stage_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    row = crm_pipeline.get_stage(db, stage_id)
    if not row:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    _owned_pipeline(db, row.pipeline_id, current_user)
    crm_pipeline.archive_stage(db, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

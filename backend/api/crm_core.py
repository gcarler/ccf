"""CRM Core 2.0 — API REST para Pipelines, Casos, Interacciones y Tareas.

Endpoints:
  Pipelines:  CRUD + etapas
  Plantillas: listar, crear
  Casos:      CRUD + mover etapa + cerrar
  Interacciones: listar, crear (por caso)
  Tareas:        listar, crear, completar (por caso)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import require_pastor_or_admin
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id
from backend.crud import crm_core as crud
from backend.schemas.crm_core import (
    CasoCRMCreate, CasoCRMResponse,
    EtapaPipelineCreate, EtapaPipelineResponse,
    InteraccionCRMCreate, InteraccionCRMResponse,
    PipelineCRMCreate, PipelineCRMResponse,
    PlantillaMensajeCreate, PlantillaMensajeResponse,
    TareaCRMCreate, TareaCRMResponse,
)

router = APIRouter(prefix="/v2/crm", tags=["CRM v2"])


def _assert_same_sede(obj, sede_id: str, detail: str):
    if not obj or str(getattr(obj, "sede_id", "")) != sede_id:
        raise HTTPException(status_code=404, detail=detail)
    return obj


# ──────────────────────────────────────────────
# PIPELINES
# ──────────────────────────────────────────────

@router.get("/pipelines", response_model=List[PipelineCRMResponse])
def list_pipelines(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    return crud.list_pipelines(db, sede_id=require_user_sede_id(db, current_user))


@router.post("/pipelines", response_model=PipelineCRMResponse)
def create_pipeline(
    payload: PipelineCRMCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    payload = payload.model_copy(update={"sede_id": require_user_sede_id(db, current_user)})
    return crud.create_pipeline(db, payload)


@router.get("/pipelines/{pipeline_id}", response_model=PipelineCRMResponse)
def get_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    obj = crud.get_pipeline(db, pipeline_id)
    return _assert_same_sede(obj, require_user_sede_id(db, current_user), "Pipeline no encontrado")


@router.put("/pipelines/{pipeline_id}", response_model=PipelineCRMResponse)
def update_pipeline(
    pipeline_id: int,
    payload: PipelineCRMCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_pipeline(db, pipeline_id)
    sede_id = require_user_sede_id(db, current_user)
    _assert_same_sede(current, sede_id, "Pipeline no encontrado")
    payload = payload.model_copy(update={"sede_id": sede_id})
    obj = crud.update_pipeline(db, pipeline_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")
    return obj


@router.delete("/pipelines/{pipeline_id}", status_code=204)
def delete_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_pipeline(db, pipeline_id)
    _assert_same_sede(current, require_user_sede_id(db, current_user), "Pipeline no encontrado")
    if not crud.delete_pipeline(db, pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")


# ── Etapas ──

@router.get("/pipelines/{pipeline_id}/etapas", response_model=List[EtapaPipelineResponse])
def list_etapas(
    pipeline_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    pipeline = crud.get_pipeline(db, pipeline_id)
    _assert_same_sede(pipeline, require_user_sede_id(db, current_user), "Pipeline no encontrado")
    return crud.get_etapas_by_pipeline(db, pipeline_id)


@router.post("/pipelines/{pipeline_id}/etapas", response_model=EtapaPipelineResponse)
def create_etapa(
    pipeline_id: int,
    payload: EtapaPipelineCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    pipeline = crud.get_pipeline(db, pipeline_id)
    _assert_same_sede(pipeline, require_user_sede_id(db, current_user), "Pipeline no encontrado")
    payload.pipeline_id = pipeline_id
    return crud.create_etapa(db, payload)


@router.put("/etapas/{etapa_id}", response_model=EtapaPipelineResponse)
def update_etapa(
    etapa_id: int,
    payload: EtapaPipelineCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_etapa(db, etapa_id)
    pipeline = crud.get_pipeline(db, current.pipeline_id) if current else None
    _assert_same_sede(pipeline, require_user_sede_id(db, current_user), "Etapa no encontrada")
    obj = crud.update_etapa(db, etapa_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    return obj


@router.delete("/etapas/{etapa_id}", status_code=204)
def delete_etapa(
    etapa_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_etapa(db, etapa_id)
    pipeline = crud.get_pipeline(db, current.pipeline_id) if current else None
    _assert_same_sede(pipeline, require_user_sede_id(db, current_user), "Etapa no encontrada")
    if not crud.delete_etapa(db, etapa_id):
        raise HTTPException(status_code=404, detail="Etapa no encontrada")


# ──────────────────────────────────────────────
# PLANTILLAS
# ──────────────────────────────────────────────

@router.get("/plantillas", response_model=List[PlantillaMensajeResponse])
def list_plantillas(
    canal: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_plantillas(db, canal=canal)


@router.post("/plantillas", response_model=PlantillaMensajeResponse)
def create_plantilla(
    payload: PlantillaMensajeCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_plantilla(db, payload)


# ──────────────────────────────────────────────
# CASOS
# ──────────────────────────────────────────────

@router.get("/casos", response_model=List[CasoCRMResponse])
def list_casos(
    pipeline_id: Optional[int] = Query(None),
    asignado_a_id: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    return crud.list_casos(
        db,
        pipeline_id=pipeline_id,
        asignado_a_id=asignado_a_id,
        estado=estado,
        sede_id=require_user_sede_id(db, current_user),
    )


@router.post("/casos", response_model=CasoCRMResponse)
def create_caso(
    payload: CasoCRMCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    payload = payload.model_copy(update={"sede_id": require_user_sede_id(db, current_user)})
    return crud.create_caso(db, payload)


@router.get("/casos/{caso_id}", response_model=CasoCRMResponse)
def get_caso(
    caso_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    obj = crud.get_caso(db, caso_id)
    return _assert_same_sede(obj, require_user_sede_id(db, current_user), "Caso no encontrado")


@router.put("/casos/{caso_id}", response_model=CasoCRMResponse)
def update_caso(
    caso_id: str,
    payload: CasoCRMCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_caso(db, caso_id)
    sede_id = require_user_sede_id(db, current_user)
    _assert_same_sede(current, sede_id, "Caso no encontrado")
    payload = payload.model_copy(update={"sede_id": sede_id})
    obj = crud.update_caso(db, caso_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return obj


@router.patch("/casos/{caso_id}/mover", response_model=CasoCRMResponse)
def mover_caso(
    caso_id: str,
    nueva_etapa_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_caso(db, caso_id)
    _assert_same_sede(current, require_user_sede_id(db, current_user), "Caso no encontrado")
    obj = crud.mover_etapa(db, caso_id, nueva_etapa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return obj


@router.post("/casos/{caso_id}/close", response_model=CasoCRMResponse)
def close_caso(
    caso_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_caso(db, caso_id)
    _assert_same_sede(current, require_user_sede_id(db, current_user), "Caso no encontrado")
    obj = crud.close_caso(db, caso_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return obj


# ──────────────────────────────────────────────
# INTERACCIONES
# ──────────────────────────────────────────────

@router.get("/casos/{caso_id}/interacciones", response_model=List[InteraccionCRMResponse])
def list_interacciones(
    caso_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_caso(db, caso_id)
    _assert_same_sede(current, require_user_sede_id(db, current_user), "Caso no encontrado")
    return crud.list_interacciones(db, caso_id)


@router.post("/casos/{caso_id}/interacciones", response_model=InteraccionCRMResponse)
def create_interaccion(
    caso_id: str,
    payload: InteraccionCRMCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_caso(db, caso_id)
    _assert_same_sede(current, require_user_sede_id(db, current_user), "Caso no encontrado")
    payload.caso_id = caso_id
    return crud.create_interaccion(db, payload)


# ──────────────────────────────────────────────
# TAREAS
# ──────────────────────────────────────────────

@router.get("/casos/{caso_id}/tareas", response_model=List[TareaCRMResponse])
def list_tareas(
    caso_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_caso(db, caso_id)
    _assert_same_sede(current, require_user_sede_id(db, current_user), "Caso no encontrado")
    return crud.list_tareas(db, caso_id)


@router.post("/casos/{caso_id}/tareas", response_model=TareaCRMResponse)
def create_tarea(
    caso_id: str,
    payload: TareaCRMCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    current = crud.get_caso(db, caso_id)
    _assert_same_sede(current, require_user_sede_id(db, current_user), "Caso no encontrado")
    payload.caso_id = caso_id
    return crud.create_tarea(db, payload)


@router.patch("/tareas/{tarea_id}/complete", response_model=TareaCRMResponse)
def complete_tarea(
    tarea_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    tarea = crud.get_tarea(db, tarea_id)
    caso = crud.get_caso(db, tarea.caso_id) if tarea else None
    _assert_same_sede(caso, require_user_sede_id(db, current_user), "Tarea no encontrada")
    obj = crud.complete_tarea(db, tarea_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return obj

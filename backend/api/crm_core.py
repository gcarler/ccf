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
from backend.crud import crm_core as crud
from backend.schemas.crm_core import (
    CasoCRMCreate, CasoCRMResponse,
    EtapaPipelineCreate, EtapaPipelineResponse,
    InteraccionCRMCreate, InteraccionCRMResponse,
    PipelineCRMCreate, PipelineCRMResponse,
    PlantillaMensajeCreate, PlantillaMensajeResponse,
    TareaCRMCreate, TareaCRMResponse,
)

router = APIRouter(prefix="/crm-core", tags=["CRM Core"])


# ──────────────────────────────────────────────
# PIPELINES
# ──────────────────────────────────────────────

@router.get("/pipelines", response_model=List[PipelineCRMResponse])
def list_pipelines(
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_pipelines(db, sede_id=sede_id)


@router.post("/pipelines", response_model=PipelineCRMResponse)
def create_pipeline(
    payload: PipelineCRMCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_pipeline(db, payload)


@router.get("/pipelines/{pipeline_id}", response_model=PipelineCRMResponse)
def get_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.get_pipeline(db, pipeline_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")
    return obj


@router.put("/pipelines/{pipeline_id}", response_model=PipelineCRMResponse)
def update_pipeline(
    pipeline_id: int,
    payload: PipelineCRMCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_pipeline(db, pipeline_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")
    return obj


@router.delete("/pipelines/{pipeline_id}", status_code=204)
def delete_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if not crud.delete_pipeline(db, pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")


# ── Etapas ──

@router.get("/pipelines/{pipeline_id}/etapas", response_model=List[EtapaPipelineResponse])
def list_etapas(
    pipeline_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.get_etapas_by_pipeline(db, pipeline_id)


@router.post("/pipelines/{pipeline_id}/etapas", response_model=EtapaPipelineResponse)
def create_etapa(
    pipeline_id: int,
    payload: EtapaPipelineCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    payload.pipeline_id = pipeline_id
    return crud.create_etapa(db, payload)


@router.put("/etapas/{etapa_id}", response_model=EtapaPipelineResponse)
def update_etapa(
    etapa_id: int,
    payload: EtapaPipelineCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_etapa(db, etapa_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    return obj


@router.delete("/etapas/{etapa_id}", status_code=204)
def delete_etapa(
    etapa_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
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
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_casos(db, pipeline_id=pipeline_id, asignado_a_id=asignado_a_id, estado=estado)


@router.post("/casos", response_model=CasoCRMResponse)
def create_caso(
    payload: CasoCRMCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_caso(db, payload)


@router.get("/casos/{caso_id}", response_model=CasoCRMResponse)
def get_caso(
    caso_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.get_caso(db, caso_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return obj


@router.put("/casos/{caso_id}", response_model=CasoCRMResponse)
def update_caso(
    caso_id: str,
    payload: CasoCRMCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_caso(db, caso_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return obj


@router.patch("/casos/{caso_id}/mover", response_model=CasoCRMResponse)
def mover_caso(
    caso_id: str,
    nueva_etapa_id: int = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.mover_etapa(db, caso_id, nueva_etapa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return obj


@router.post("/casos/{caso_id}/close", response_model=CasoCRMResponse)
def close_caso(
    caso_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
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
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_interacciones(db, caso_id)


@router.post("/casos/{caso_id}/interacciones", response_model=InteraccionCRMResponse)
def create_interaccion(
    caso_id: str,
    payload: InteraccionCRMCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    payload.caso_id = caso_id
    return crud.create_interaccion(db, payload)


# ──────────────────────────────────────────────
# TAREAS
# ──────────────────────────────────────────────

@router.get("/casos/{caso_id}/tareas", response_model=List[TareaCRMResponse])
def list_tareas(
    caso_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_tareas(db, caso_id)


@router.post("/casos/{caso_id}/tareas", response_model=TareaCRMResponse)
def create_tarea(
    caso_id: str,
    payload: TareaCRMCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    payload.caso_id = caso_id
    return crud.create_tarea(db, payload)


@router.patch("/tareas/{tarea_id}/complete", response_model=TareaCRMResponse)
def complete_tarea(
    tarea_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.complete_tarea(db, tarea_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return obj

"""CRM Core 2.0 — Pipeline, Casos, Interacciones, Tareas CRUD."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models_crm_core import (
    CasoCRM,
    EstadoCasoEnum,
    EtapaPipeline,
    InteraccionCRM,
    PipelineCRM,
    PlantillaMensaje,
    TareaCRM,
)
from backend.schemas.crm_core import (
    CasoCRMCreate,
    CasoCRMUpdate,
    EtapaPipelineCreate,
    EtapaPipelineUpdate,
    InteraccionCRMCreate,
    PipelineCRMCreate,
    PipelineCRMUpdate,
    PlantillaMensajeCreate,
    TareaCRMCreate,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PipelineCRM
# ═══════════════════════════════════════════════════════════════════════════════

def create_pipeline(db: Session, payload: PipelineCRMCreate) -> PipelineCRM:
    """Create a new CRM pipeline."""
    row = PipelineCRM(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_pipeline(db: Session, id: int) -> Optional[PipelineCRM]:
    """Get a single pipeline by id."""
    return db.query(PipelineCRM).filter(PipelineCRM.id == id).first()


def list_pipelines(db: Session, sede_id: int) -> List[PipelineCRM]:
    """List all pipelines for a given sede."""
    return (
        db.query(PipelineCRM)
        .filter(PipelineCRM.sede_id == sede_id)
        .order_by(PipelineCRM.id)
        .all()
    )


def update_pipeline(
    db: Session, id: int, payload: PipelineCRMUpdate
) -> Optional[PipelineCRM]:
    """Update an existing pipeline. Returns None if not found."""
    row = db.query(PipelineCRM).filter(PipelineCRM.id == id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_pipeline(db: Session, id: int) -> bool:
    """Delete a pipeline. Returns True if deleted, False if not found."""
    row = db.query(PipelineCRM).filter(PipelineCRM.id == id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# EtapaPipeline
# ═══════════════════════════════════════════════════════════════════════════════

def create_etapa(db: Session, payload: EtapaPipelineCreate) -> EtapaPipeline:
    """Create a new pipeline stage."""
    row = EtapaPipeline(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_etapas_by_pipeline(
    db: Session, pipeline_id: int
) -> List[EtapaPipeline]:
    """List all stages for a pipeline, ordered by position."""
    return (
        db.query(EtapaPipeline)
        .filter(EtapaPipeline.pipeline_id == pipeline_id)
        .order_by(EtapaPipeline.orden)
        .all()
    )


def update_etapa(
    db: Session, id: int, payload: EtapaPipelineUpdate
) -> Optional[EtapaPipeline]:
    """Update a pipeline stage. Returns None if not found."""
    row = db.query(EtapaPipeline).filter(EtapaPipeline.id == id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_etapa(db: Session, id: int) -> bool:
    """Delete a pipeline stage. Returns True if deleted, False if not found."""
    row = db.query(EtapaPipeline).filter(EtapaPipeline.id == id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# PlantillaMensaje
# ═══════════════════════════════════════════════════════════════════════════════

def create_plantilla(
    db: Session, payload: PlantillaMensajeCreate
) -> PlantillaMensaje:
    """Create a new message template."""
    row = PlantillaMensaje(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_plantillas(
    db: Session, canal: Optional[str] = None
) -> List[PlantillaMensaje]:
    """List message templates, optionally filtered by channel."""
    query = db.query(PlantillaMensaje)
    if canal is not None:
        query = query.filter(PlantillaMensaje.canal == canal)
    return query.order_by(PlantillaMensaje.titulo).all()


# ═══════════════════════════════════════════════════════════════════════════════
# CasoCRM
# ═══════════════════════════════════════════════════════════════════════════════

def create_caso(db: Session, payload: CasoCRMCreate) -> CasoCRM:
    """Create a new CRM case/ticket."""
    data = payload.model_dump()
    # Ensure estado defaults to ABIERTO
    data.setdefault("estado", EstadoCasoEnum.ABIERTO)
    row = CasoCRM(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_caso(db: Session, id: str) -> Optional[CasoCRM]:
    """Get a single case by id."""
    return db.query(CasoCRM).filter(CasoCRM.id == id).first()


def list_casos(
    db: Session,
    pipeline_id: Optional[int] = None,
    asignado_a_id: Optional[str] = None,
    estado: Optional[str] = None,
) -> List[CasoCRM]:
    """List cases with optional filters."""
    query = db.query(CasoCRM)
    if pipeline_id is not None:
        query = query.filter(CasoCRM.pipeline_id == pipeline_id)
    if asignado_a_id is not None:
        query = query.filter(CasoCRM.asignado_a_id == asignado_a_id)
    if estado is not None:
        query = query.filter(CasoCRM.estado == estado)
    return query.order_by(CasoCRM.fecha_creacion.desc()).all()


def update_caso(
    db: Session, id: str, payload: CasoCRMUpdate
) -> Optional[CasoCRM]:
    """Update a case. Returns None if not found."""
    row = db.query(CasoCRM).filter(CasoCRM.id == id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def mover_etapa(
    db: Session, caso_id: str, nueva_etapa_id: int
) -> Optional[CasoCRM]:
    """Move a case to a new stage. Auto-transitions ABIERTO → EN_PROGRESO."""
    row = db.query(CasoCRM).filter(CasoCRM.id == caso_id).first()
    if not row:
        return None
    row.etapa_actual_id = nueva_etapa_id
    if row.estado == EstadoCasoEnum.ABIERTO:
        row.estado = EstadoCasoEnum.EN_PROGRESO
    db.commit()
    db.refresh(row)
    return row


def close_caso(db: Session, id: str) -> Optional[CasoCRM]:
    """Close a case as successfully resolved. Returns None if not found."""
    row = db.query(CasoCRM).filter(CasoCRM.id == id).first()
    if not row:
        return None
    row.estado = EstadoCasoEnum.RESUELTO_EXITO
    row.fecha_cierre = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


# ═══════════════════════════════════════════════════════════════════════════════
# InteraccionCRM
# ═══════════════════════════════════════════════════════════════════════════════

def create_interaccion(
    db: Session, payload: InteraccionCRMCreate
) -> InteraccionCRM:
    """Log a new interaction on a case."""
    row = InteraccionCRM(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_interacciones(
    db: Session, caso_id: str
) -> List[InteraccionCRM]:
    """List all interactions for a case, newest first."""
    return (
        db.query(InteraccionCRM)
        .filter(InteraccionCRM.caso_id == caso_id)
        .order_by(InteraccionCRM.fecha_interaccion.desc())
        .all()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TareaCRM
# ═══════════════════════════════════════════════════════════════════════════════

def create_tarea(db: Session, payload: TareaCRMCreate) -> TareaCRM:
    """Create a new task attached to a case."""
    row = TareaCRM(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_tareas(db: Session, caso_id: str) -> List[TareaCRM]:
    """List all tasks for a case."""
    return (
        db.query(TareaCRM)
        .filter(TareaCRM.caso_id == caso_id)
        .order_by(TareaCRM.fecha_vencimiento)
        .all()
    )


def complete_tarea(db: Session, id: str) -> Optional[TareaCRM]:
    """Mark a task as completed. Returns None if not found."""
    row = db.query(TareaCRM).filter(TareaCRM.id == id).first()
    if not row:
        return None
    row.completada = True
    row.fecha_completada = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row

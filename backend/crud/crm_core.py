"""CRM Core 2.0 — Pipeline, Casos, Interacciones, Tareas CRUD."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models_crm_core import (
    CasoCRM, EstadoCasoEnum, EtapaPipeline, InteraccionCRM,
    PipelineCRM, PlantillaMensaje, TareaCRM,
)
from backend.schemas.crm_core import (
    CasoCRMCreate, EtapaPipelineCreate, InteraccionCRMCreate,
    PipelineCRMCreate, PlantillaMensajeCreate, TareaCRMCreate,
)


# ═══════════════════════════════════════════════════════════════════
# PipelineCRM
# ═══════════════════════════════════════════════════════════════════

def create_pipeline(db: Session, payload: PipelineCRMCreate) -> PipelineCRM:
    row = PipelineCRM(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row

def get_pipeline(db: Session, id: int) -> Optional[PipelineCRM]:
    return db.query(PipelineCRM).filter(PipelineCRM.id == id).first()

def list_pipelines(db: Session, sede_id: Optional[int] = None) -> List[PipelineCRM]:
    q = db.query(PipelineCRM)
    if sede_id is not None:
        q = q.filter(PipelineCRM.sede_id == sede_id)
    return q.order_by(PipelineCRM.id).all()

def update_pipeline(db: Session, id: int, payload: PipelineCRMCreate) -> Optional[PipelineCRM]:
    row = db.query(PipelineCRM).filter(PipelineCRM.id == id).first()
    if not row: return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row

def delete_pipeline(db: Session, id: int) -> bool:
    row = db.query(PipelineCRM).filter(PipelineCRM.id == id).first()
    if not row: return False
    db.delete(row); db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# EtapaPipeline
# ═══════════════════════════════════════════════════════════════════

def create_etapa(db: Session, payload: EtapaPipelineCreate) -> EtapaPipeline:
    row = EtapaPipeline(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row

def get_etapas_by_pipeline(db: Session, pipeline_id: int) -> List[EtapaPipeline]:
    return (db.query(EtapaPipeline)
            .filter(EtapaPipeline.pipeline_id == pipeline_id)
            .order_by(EtapaPipeline.orden).all())

def update_etapa(db: Session, id: int, payload: EtapaPipelineCreate) -> Optional[EtapaPipeline]:
    row = db.query(EtapaPipeline).filter(EtapaPipeline.id == id).first()
    if not row: return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row

def delete_etapa(db: Session, id: int) -> bool:
    row = db.query(EtapaPipeline).filter(EtapaPipeline.id == id).first()
    if not row: return False
    db.delete(row); db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# PlantillaMensaje
# ═══════════════════════════════════════════════════════════════════

def create_plantilla(db: Session, payload: PlantillaMensajeCreate) -> PlantillaMensaje:
    row = PlantillaMensaje(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row

def list_plantillas(db: Session, canal: Optional[str] = None) -> List[PlantillaMensaje]:
    q = db.query(PlantillaMensaje)
    if canal: q = q.filter(PlantillaMensaje.canal == canal)
    return q.order_by(PlantillaMensaje.titulo).all()


# ═══════════════════════════════════════════════════════════════════
# CasoCRM
# ═══════════════════════════════════════════════════════════════════

def create_caso(db: Session, payload: CasoCRMCreate) -> CasoCRM:
    data = payload.model_dump()
    data.setdefault("estado", EstadoCasoEnum.ABIERTO)
    row = CasoCRM(**data)
    db.add(row); db.commit(); db.refresh(row)
    return row

def get_caso(db: Session, id: str) -> Optional[CasoCRM]:
    return db.query(CasoCRM).filter(CasoCRM.id == id).first()

def list_casos(db: Session, pipeline_id: Optional[int] = None,
               asignado_a_id: Optional[str] = None,
               estado: Optional[str] = None) -> List[CasoCRM]:
    q = db.query(CasoCRM)
    if pipeline_id is not None: q = q.filter(CasoCRM.pipeline_id == pipeline_id)
    if asignado_a_id is not None: q = q.filter(CasoCRM.asignado_a_id == asignado_a_id)
    if estado is not None: q = q.filter(CasoCRM.estado == estado)
    return q.order_by(CasoCRM.fecha_creacion.desc()).all()

def update_caso(db: Session, id: str, payload: CasoCRMCreate) -> Optional[CasoCRM]:
    row = db.query(CasoCRM).filter(CasoCRM.id == id).first()
    if not row: return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row

def mover_etapa(db: Session, caso_id: str, nueva_etapa_id: int) -> Optional[CasoCRM]:
    row = db.query(CasoCRM).filter(CasoCRM.id == caso_id).first()
    if not row: return None
    row.etapa_actual_id = nueva_etapa_id
    db.commit(); db.refresh(row)
    return row

def close_caso(db: Session, id: str) -> Optional[CasoCRM]:
    row = db.query(CasoCRM).filter(CasoCRM.id == id).first()
    if not row: return None
    row.estado = EstadoCasoEnum.CERRADO_PERDIDO
    row.fecha_cierre = datetime.utcnow()
    db.commit(); db.refresh(row)
    return row


# ═══════════════════════════════════════════════════════════════════
# InteraccionCRM
# ═══════════════════════════════════════════════════════════════════

def create_interaccion(db: Session, payload: InteraccionCRMCreate) -> InteraccionCRM:
    row = InteraccionCRM(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row

def list_interacciones(db: Session, caso_id: str) -> List[InteraccionCRM]:
    return (db.query(InteraccionCRM)
            .filter(InteraccionCRM.caso_id == caso_id)
            .order_by(InteraccionCRM.fecha_interaccion.desc()).all())


# ═══════════════════════════════════════════════════════════════════
# TareaCRM
# ═══════════════════════════════════════════════════════════════════

def create_tarea(db: Session, payload: TareaCRMCreate) -> TareaCRM:
    row = TareaCRM(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row

def list_tareas(db: Session, caso_id: str) -> List[TareaCRM]:
    return (db.query(TareaCRM)
            .filter(TareaCRM.caso_id == caso_id)
            .order_by(TareaCRM.fecha_vencimiento).all())

def complete_tarea(db: Session, id: str) -> Optional[TareaCRM]:
    row = db.query(TareaCRM).filter(TareaCRM.id == id).first()
    if not row: return None
    row.completada = True
    row.fecha_completada = datetime.utcnow()
    db.commit(); db.refresh(row)
    return row

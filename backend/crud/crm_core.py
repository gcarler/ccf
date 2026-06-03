"""CRM Core 2.0 — CRUD functions."""
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from sqlalchemy.orm import Session

from backend.models_crm_core import (
    PipelineCRM, EtapaPipeline, PlantillaMensaje,
    CasoCRM, InteraccionCRM, TareaCRM,
    TipoPipelineEnum,
)
from backend.schemas.crm_core import (
    PipelineCRMCreate, EtapaPipelineCreate, PlantillaMensajeCreate,
    CasoCRMCreate, InteraccionCRMCreate, TareaCRMCreate,
)


# ── Pipeline ────────────────────────────────────────────

def create_pipeline(db: Session, payload: PipelineCRMCreate) -> PipelineCRM:
    obj = PipelineCRM(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_pipeline(db: Session, pipeline_id: int) -> Optional[PipelineCRM]:
    return db.query(PipelineCRM).filter(PipelineCRM.id == pipeline_id).first()


def list_pipelines(db: Session, sede_id: Optional[int] = None) -> List[PipelineCRM]:
    q = db.query(PipelineCRM)
    if sede_id:
        q = q.filter(PipelineCRM.sede_id == sede_id)
    return q.all()


def update_pipeline(db: Session, pipeline_id: int, payload: PipelineCRMCreate) -> Optional[PipelineCRM]:
    obj = get_pipeline(db, pipeline_id)
    if not obj:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


def delete_pipeline(db: Session, pipeline_id: int) -> bool:
    obj = get_pipeline(db, pipeline_id)
    if not obj:
        return False
    obj.deleted_at = _utcnow()
    db.commit()
    return True


# ── Etapas ──────────────────────────────────────────────

def create_etapa(db: Session, payload: EtapaPipelineCreate) -> EtapaPipeline:
    obj = EtapaPipeline(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_etapas_by_pipeline(db: Session, pipeline_id: int) -> List[EtapaPipeline]:
    return db.query(EtapaPipeline).filter(EtapaPipeline.pipeline_id == pipeline_id).order_by(EtapaPipeline.orden).all()


def update_etapa(db: Session, etapa_id: int, payload: EtapaPipelineCreate) -> Optional[EtapaPipeline]:
    obj = db.query(EtapaPipeline).filter(EtapaPipeline.id == etapa_id).first()
    if not obj:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_etapa(db: Session, etapa_id: int) -> bool:
    obj = db.query(EtapaPipeline).filter(EtapaPipeline.id == etapa_id).first()
    if not obj:
        return False
    obj.deleted_at = _utcnow()
    db.commit()
    return True


# ── Plantillas ──────────────────────────────────────────

def create_plantilla(db: Session, payload: PlantillaMensajeCreate) -> PlantillaMensaje:
    obj = PlantillaMensaje(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_plantillas(db: Session, canal: Optional[str] = None) -> List[PlantillaMensaje]:
    q = db.query(PlantillaMensaje)
    if canal:
        q = q.filter(PlantillaMensaje.canal == canal)
    return q.all()


# ── Casos ───────────────────────────────────────────────

def create_caso(db: Session, payload: CasoCRMCreate) -> CasoCRM:
    obj = CasoCRM(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_caso(db: Session, caso_id: int) -> Optional[CasoCRM]:
    return db.query(CasoCRM).filter(CasoCRM.id == caso_id, CasoCRM.deleted_at.is_(None)).first()


def list_casos(db: Session, pipeline_id: Optional[int] = None, asignado_a_id: Optional[str] = None,
               estado: Optional[str] = None, sede_id: Optional[int] = None) -> List[CasoCRM]:
    q = db.query(CasoCRM).filter(CasoCRM.deleted_at.is_(None))
    if pipeline_id:
        q = q.filter(CasoCRM.pipeline_id == pipeline_id)
    if asignado_a_id:
        q = q.filter(CasoCRM.asignado_a_id == asignado_a_id)
    if estado:
        q = q.filter(CasoCRM.estado == estado)
    if sede_id:
        q = q.filter(CasoCRM.sede_id == sede_id)
    return q.order_by(CasoCRM.created_at.desc()).all()


def update_caso(db: Session, caso_id: int, payload: CasoCRMCreate) -> Optional[CasoCRM]:
    obj = get_caso(db, caso_id)
    if not obj:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


def mover_etapa(db: Session, caso_id: int, nueva_etapa_id: int) -> Optional[CasoCRM]:
    obj = get_caso(db, caso_id)
    if not obj:
        return None
    obj.etapa_actual_id = nueva_etapa_id
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


def close_caso(db: Session, caso_id: int, motivo: Optional[str] = None) -> Optional[CasoCRM]:
    obj = get_caso(db, caso_id)
    if not obj:
        return None
    obj.estado = "CERRADO"
    obj.fecha_cierre = datetime.now(timezone.utc)
    obj.motivo_cierre = motivo
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


# ── Interacciones ───────────────────────────────────────

def create_interaccion(db: Session, payload: InteraccionCRMCreate) -> InteraccionCRM:
    obj = InteraccionCRM(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_interacciones(db: Session, caso_id: int) -> List[InteraccionCRM]:
    return db.query(InteraccionCRM).filter(InteraccionCRM.caso_id == caso_id).order_by(InteraccionCRM.created_at.desc()).all()


# ── Tareas ──────────────────────────────────────────────

def create_tarea(db: Session, payload: TareaCRMCreate) -> TareaCRM:
    obj = TareaCRM(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_tareas(db: Session, caso_id: int) -> List[TareaCRM]:
    return db.query(TareaCRM).filter(TareaCRM.caso_id == caso_id).order_by(TareaCRM.created_at.desc()).all()


def complete_tarea(db: Session, tarea_id: int) -> Optional[TareaCRM]:
    obj = db.query(TareaCRM).filter(TareaCRM.id == tarea_id).first()
    if not obj:
        return None
    obj.completada = True
    obj.completada_en = datetime.now(timezone.utc)
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


def seed_pipeline_nuevos_visitantes(db: Session, sede_id: uuid.UUID) -> PipelineCRM:
    """Idempotente: crea pipeline NUEVOS_VISITANTES con etapa inicial si no existe."""
    pipeline = (
        db.query(PipelineCRM)
        .filter(
            PipelineCRM.sede_id == sede_id,
            PipelineCRM.tipo == TipoPipelineEnum.NUEVOS_VISITANTES,
            PipelineCRM.activo == True,
        )
        .first()
    )
    if pipeline:
        return pipeline

    pipeline = PipelineCRM(
        sede_id=sede_id,
        nombre="Nuevos Visitantes",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        activo=True,
    )
    db.add(pipeline)
    db.flush()

    etapa = EtapaPipeline(
        pipeline_id=pipeline.id,
        nombre="Nuevo Contacto",
        orden=1,
        requiere_accion=True,
    )
    db.add(etapa)
    db.commit()
    db.refresh(pipeline)
    return pipeline

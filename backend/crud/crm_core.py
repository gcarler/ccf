"""CRM Core 2.0 — CRUD functions."""

from datetime import datetime, timezone
from typing import Optional, List
import uuid

from sqlalchemy.orm import Session

from backend.models_crm_core import (
    PipelineCRM,
    EtapaPipeline,
    PlantillaMensaje,
    CasoCRM,
    InteraccionCRM,
    TareaCRM,
    TipoPipelineEnum,
)
from backend.crud._utils import _utcnow
from backend.schemas.crm_core import (
    PipelineCRMCreate,
    EtapaPipelineCreate,
    PlantillaMensajeCreate,
    CasoCRMCreate,
    InteraccionCRMCreate,
    TareaCRMCreate,
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


def list_pipelines(db: Session, sede_id: Optional[str] = None) -> List[PipelineCRM]:
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


def get_etapa(db: Session, etapa_id: int) -> Optional[EtapaPipeline]:
    return db.query(EtapaPipeline).filter(EtapaPipeline.id == etapa_id).first()


def update_etapa(db: Session, etapa_id: int, payload: EtapaPipelineCreate) -> Optional[EtapaPipeline]:
    obj = get_etapa(db, etapa_id)
    if not obj:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_etapa(db: Session, etapa_id: int) -> bool:
    obj = get_etapa(db, etapa_id)
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
    data = payload.model_dump()
    # Convert string UUIDs to uuid.UUID objects for the model
    for key in ("persona_id", "sede_id", "asignado_a_id", "created_by_id"):
        val = data.get(key)
        if val and isinstance(val, str):
            try:
                data[key] = uuid.UUID(val)
            except ValueError:
                data[key] = None
    obj = CasoCRM(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_caso(db: Session, caso_id: str) -> Optional[CasoCRM]:
    """Get caso by UUID string. Converts to uuid.UUID internally."""
    try:
        uid = uuid.UUID(caso_id) if isinstance(caso_id, str) else caso_id
    except (ValueError, AttributeError):
        return None
    return db.query(CasoCRM).filter(CasoCRM.id == uid, CasoCRM.deleted_at.is_(None)).first()


def list_casos(
    db: Session,
    pipeline_id: Optional[int] = None,
    asignado_a_id: Optional[str] = None,
    estado: Optional[str] = None,
    sede_id: Optional[str] = None,
) -> List[CasoCRM]:
    q = db.query(CasoCRM).filter(CasoCRM.deleted_at.is_(None))
    if pipeline_id:
        q = q.filter(CasoCRM.pipeline_id == pipeline_id)
    if asignado_a_id:
        q = q.filter(CasoCRM.asignado_a_id == asignado_a_id)
    if estado:
        q = q.filter(CasoCRM.estado == estado)
    if sede_id:
        q = q.filter(CasoCRM.sede_id == sede_id)
    return q.order_by(CasoCRM.fecha_creacion.desc()).all()


def update_caso(db: Session, caso_id: str, payload: CasoCRMCreate) -> Optional[CasoCRM]:
    obj = get_caso(db, caso_id)
    if not obj:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    if hasattr(obj, 'updated_at'):
        obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


def mover_etapa(db: Session, caso_id: str, nueva_etapa_id: int) -> Optional[CasoCRM]:
    obj = get_caso(db, caso_id)
    if not obj:
        return None
    obj.etapa_actual_id = nueva_etapa_id
    if hasattr(obj, 'updated_at'):
        obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


def close_caso(db: Session, caso_id: str, motivo: Optional[str] = None) -> Optional[CasoCRM]:
    obj = get_caso(db, caso_id)
    if not obj:
        return None
    obj.estado = EstadoCasoEnum.CERRADO_PERDIDO
    obj.fecha_cierre = datetime.now(timezone.utc)
    if hasattr(obj, 'updated_at'):
        obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


# ── Interacciones ───────────────────────────────────────


def create_interaccion(db: Session, payload: InteraccionCRMCreate) -> InteraccionCRM:
    data = payload.model_dump()
    caso_id_val = data.get("caso_id")
    if caso_id_val and isinstance(caso_id_val, str):
        try:
            data["caso_id"] = uuid.UUID(caso_id_val)
        except ValueError:
            data["caso_id"] = None
    realizada_por = data.get("realizada_por_id")
    if realizada_por and isinstance(realizada_por, str):
        try:
            data["realizada_por_id"] = uuid.UUID(realizada_por)
        except ValueError:
            data["realizada_por_id"] = None
    obj = InteraccionCRM(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_interacciones(db: Session, caso_id: str) -> List[InteraccionCRM]:
    try:
        uid = uuid.UUID(caso_id) if isinstance(caso_id, str) else caso_id
    except (ValueError, AttributeError):
        return []
    return (
        db.query(InteraccionCRM)
        .filter(InteraccionCRM.caso_id == uid)
        .order_by(InteraccionCRM.created_at.desc())
        .all()
    )


# ── Tareas ──────────────────────────────────────────────


def create_tarea(db: Session, payload: TareaCRMCreate) -> TareaCRM:
    data = payload.model_dump()
    caso_id_val = data.get("caso_id")
    if caso_id_val and isinstance(caso_id_val, str):
        try:
            data["caso_id"] = uuid.UUID(caso_id_val)
        except ValueError:
            data["caso_id"] = None
    asignado_a = data.get("asignado_a_id")
    if asignado_a and isinstance(asignado_a, str):
        try:
            data["asignado_a_id"] = uuid.UUID(asignado_a)
        except ValueError:
            data["asignado_a_id"] = None
    obj = TareaCRM(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_tareas(db: Session, caso_id: str) -> List[TareaCRM]:
    try:
        uid = uuid.UUID(caso_id) if isinstance(caso_id, str) else caso_id
    except (ValueError, AttributeError):
        return []
    return db.query(TareaCRM).filter(TareaCRM.caso_id == uid).order_by(TareaCRM.created_at.desc()).all()


def get_tarea(db: Session, tarea_id: int) -> Optional[TareaCRM]:
    return db.query(TareaCRM).filter(TareaCRM.id == tarea_id).first()


def complete_tarea(db: Session, tarea_id: int) -> Optional[TareaCRM]:
    obj = get_tarea(db, tarea_id)
    if not obj:
        return None
    obj.completada = True
    obj.fecha_completada = datetime.now(timezone.utc)
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
            PipelineCRM.activo.is_(True),
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

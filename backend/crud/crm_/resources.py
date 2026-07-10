"""CRUD — Biblioteca de Recursos CRM (plantillas, adjuntos, bitácora de envíos)."""
from __future__ import annotations

import uuid as _uuid
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models_crm import (
    BitacoraEnvioPlantilla,
    CanalEnvio,
    CategoriaRecurso,
    EstadoEnvioPlantilla,
    PlantillaMensaje,
    RecursoAdjunto,
)
from backend.schemas.crm.resources import (
    CategoriaRecursoCreate,
    CategoriaRecursoUpdate,
    PlantillaMensajeCreate,
    PlantillaMensajeUpdate,
)

# ── Categorías ────────────────────────────────────────────────────────────────

def list_categorias(db: Session) -> List[CategoriaRecurso]:
    return db.query(CategoriaRecurso).filter_by(activo=True).order_by(CategoriaRecurso.nombre).all()


def get_categoria(db: Session, categoria_id: str) -> Optional[CategoriaRecurso]:
    return db.query(CategoriaRecurso).filter_by(id=_uuid.UUID(categoria_id), activo=True).first()


def create_categoria(db: Session, payload: CategoriaRecursoCreate) -> CategoriaRecurso:
    obj = CategoriaRecurso(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_categoria(db: Session, categoria_id: str, payload: CategoriaRecursoUpdate) -> Optional[CategoriaRecurso]:
    obj = get_categoria(db, categoria_id)
    if not obj:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_categoria(db: Session, categoria_id: str) -> bool:
    obj = get_categoria(db, categoria_id)
    if not obj:
        return False
    obj.activo = False
    db.commit()
    return True


# ── Plantillas ────────────────────────────────────────────────────────────────

def list_plantillas(
    db: Session, *,
    sede_id: str,
    canal: Optional[str] = None,
    categoria_id: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[PlantillaMensaje]:
    qry = db.query(PlantillaMensaje).filter_by(sede_id=_uuid.UUID(sede_id), activo=True)
    if canal:
        qry = qry.filter(PlantillaMensaje.canal == CanalEnvio(canal))
    if categoria_id:
        qry = qry.filter(PlantillaMensaje.categoria_id == _uuid.UUID(categoria_id))
    if q:
        term = f"%{q}%"
        qry = qry.filter(
            PlantillaMensaje.titulo.ilike(term) | PlantillaMensaje.contenido_texto.ilike(term)
        )
    return qry.order_by(PlantillaMensaje.fecha_actualizacion.desc()).offset(skip).limit(limit).all()


def get_plantilla(db: Session, plantilla_id: str) -> Optional[PlantillaMensaje]:
    return db.query(PlantillaMensaje).filter_by(id=_uuid.UUID(plantilla_id), activo=True).first()


def create_plantilla(
    db: Session,
    payload: PlantillaMensajeCreate,
    *,
    sede_id: str,
    creado_por_id: Optional[str] = None,
) -> PlantillaMensaje:
    data = payload.model_dump()
    data["canal"] = CanalEnvio(data["canal"])
    data["categoria_id"] = _uuid.UUID(data["categoria_id"])
    obj = PlantillaMensaje(
        **data,
        sede_id=_uuid.UUID(sede_id),
        creado_por_id=_uuid.UUID(creado_por_id) if creado_por_id else None,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_plantilla(
    db: Session, plantilla_id: str, payload: PlantillaMensajeUpdate
) -> Optional[PlantillaMensaje]:
    obj = get_plantilla(db, plantilla_id)
    if not obj:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "canal" in data and data["canal"]:
        data["canal"] = CanalEnvio(data["canal"])
    if "categoria_id" in data and data["categoria_id"]:
        data["categoria_id"] = _uuid.UUID(data["categoria_id"])
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_plantilla(db: Session, plantilla_id: str) -> bool:
    obj = get_plantilla(db, plantilla_id)
    if not obj:
        return False
    obj.activo = False
    db.commit()
    return True


def count_envios(db: Session, plantilla_id: str) -> int:
    return (
        db.query(func.count(BitacoraEnvioPlantilla.id))
        .filter_by(plantilla_id=_uuid.UUID(plantilla_id))
        .scalar()
        or 0
    )


# ── Adjuntos ──────────────────────────────────────────────────────────────────

def list_adjuntos(db: Session, *, plantilla_id: str) -> List[RecursoAdjunto]:
    return (
        db.query(RecursoAdjunto)
        .filter_by(plantilla_id=_uuid.UUID(plantilla_id), activo=True)
        .order_by(RecursoAdjunto.fecha_creacion)
        .all()
    )


def create_adjunto(
    db: Session, *,
    sede_id: str,
    plantilla_id: Optional[str],
    nombre_recurso: str,
    url_acceso: str,
    nombre_archivo: str,
    tipo_mime: str,
    peso_bytes: int,
    seaweed_fid: Optional[str] = None,
    creado_por_id: Optional[str] = None,
) -> RecursoAdjunto:
    obj = RecursoAdjunto(
        sede_id=_uuid.UUID(sede_id),
        plantilla_id=_uuid.UUID(plantilla_id) if plantilla_id else None,
        nombre_recurso=nombre_recurso,
        seaweed_fid=seaweed_fid,
        url_acceso=url_acceso,
        nombre_archivo=nombre_archivo,
        tipo_mime=tipo_mime,
        peso_bytes=peso_bytes,
        creado_por_id=_uuid.UUID(creado_por_id) if creado_por_id else None,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_adjunto(db: Session, adjunto_id: str) -> bool:
    obj = db.query(RecursoAdjunto).filter_by(id=_uuid.UUID(adjunto_id), activo=True).first()
    if not obj:
        return False
    obj.activo = False
    db.commit()
    return True


# ── Bitácora ──────────────────────────────────────────────────────────────────

def create_envio(
    db: Session, *,
    sede_id: str,
    plantilla_id: Optional[str],
    caso_id: Optional[str],
    enviado_por_id: Optional[str],
    destinatario_id: str,
    payload_hidratado: Dict,
) -> BitacoraEnvioPlantilla:
    obj = BitacoraEnvioPlantilla(
        sede_id=_uuid.UUID(sede_id),
        plantilla_id=_uuid.UUID(plantilla_id) if plantilla_id else None,
        caso_id=_uuid.UUID(caso_id) if caso_id else None,
        enviado_por_id=_uuid.UUID(enviado_por_id) if enviado_por_id else None,
        destinatario_id=_uuid.UUID(destinatario_id),
        payload_hidratado=payload_hidratado,
        estado=EstadoEnvioPlantilla.PROCESANDO,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_estado_envio(
    db: Session, envio_id: str, estado: str, log_error: Optional[str] = None
) -> Optional[BitacoraEnvioPlantilla]:
    obj = db.query(BitacoraEnvioPlantilla).filter_by(id=_uuid.UUID(envio_id)).first()
    if not obj:
        return None
    obj.estado = EstadoEnvioPlantilla(estado)
    if log_error is not None:
        obj.log_error = log_error
    db.commit()
    db.refresh(obj)
    return obj


def list_envios_plantilla(
    db: Session, *, plantilla_id: str, skip: int = 0, limit: int = 50
) -> List[BitacoraEnvioPlantilla]:
    return (
        db.query(BitacoraEnvioPlantilla)
        .filter_by(plantilla_id=_uuid.UUID(plantilla_id))
        .order_by(BitacoraEnvioPlantilla.fecha_envio.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_envios_sede(
    db: Session, *, sede_id: str, skip: int = 0, limit: int = 100
) -> List[BitacoraEnvioPlantilla]:
    return (
        db.query(BitacoraEnvioPlantilla)
        .filter_by(sede_id=_uuid.UUID(sede_id))
        .order_by(BitacoraEnvioPlantilla.fecha_envio.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

"""CRM Core — Pipeline, Casos, Interacciones, Tareas (Centro de Consolidación).

Modelos para el CRM 2.0: pipelines configurables, call center omnicanal,
trazabilidad de origen, y SLAs de tiempo de respuesta.
"""
from datetime import datetime

import enum
import uuid as _uuid

from sqlalchemy import (Boolean, Column, DateTime, Enum as SAEnum, ForeignKey,
                        Integer, String, Text)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow():
    return datetime.utcnow()


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────

class TipoPipelineEnum(str, enum.Enum):
    NUEVOS_VISITANTES = "NUEVOS_VISITANTES"
    CONSEJERIA = "CONSEJERIA"
    RETENCION = "RETENCION"
    VOLUNTARIADO = "VOLUNTARIADO"


class EstadoCasoEnum(str, enum.Enum):
    ABIERTO = "ABIERTO"
    EN_PROGRESO = "EN_PROGRESO"
    ESPERANDO_RESPUESTA = "ESPERANDO_RESPUESTA"
    RESUELTO_EXITO = "RESUELTO_EXITO"
    CERRADO_PERDIDO = "CERRADO_PERDIDO"


class PrioridadCasoEnum(str, enum.Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class CanalOrigenEnum(str, enum.Enum):
    WEB_FORM = "WEB_FORM"
    EVANGELISMO = "EVANGELISMO"
    ASISTENCIA_SERVICIO = "ASISTENCIA_SERVICIO"
    DERIVACION_INTERNA = "DERIVACION_INTERNA"


class TipoInteraccionEnum(str, enum.Enum):
    LLAMADA_OUTBOUND = "LLAMADA_OUTBOUND"
    LLAMADA_INBOUND = "LLAMADA_INBOUND"
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    VISITA_PRESENCIAL = "VISITA_PRESENCIAL"
    CITA_CONSEJERIA = "CITA_CONSEJERIA"


# ──────────────────────────────────────────────
# PIPELINES
# ──────────────────────────────────────────────

class PipelineCRM(Base):
    __tablename__ = "crm_pipelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    tipo = Column(SAEnum(TipoPipelineEnum), nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)

    etapas = relationship("EtapaPipeline", back_populates="pipeline",
                          order_by="EtapaPipeline.orden")
    casos = relationship("CasoCRM", back_populates="pipeline")


class EtapaPipeline(Base):
    __tablename__ = "crm_etapas_pipeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey("crm_pipelines.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    orden = Column(Integer, nullable=False)
    requiere_accion = Column(Boolean, default=True)

    pipeline = relationship("PipelineCRM", back_populates="etapas")
    casos = relationship("CasoCRM", back_populates="etapa_actual")


# ──────────────────────────────────────────────
# PLANTILLAS
# ──────────────────────────────────────────────

class PlantillaMensaje(Base):
    __tablename__ = "crm_plantillas_mensaje"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(150), nullable=False)
    canal = Column(String(50), nullable=False)
    contenido_texto = Column(Text, nullable=False)
    creado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))


# ──────────────────────────────────────────────
# CASOS (TICKETS)
# ──────────────────────────────────────────────

class CasoCRM(Base):
    __tablename__ = "crm_casos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    pipeline_id = Column(Integer, ForeignKey("crm_pipelines.id"), nullable=False)
    etapa_actual_id = Column(Integer, ForeignKey("crm_etapas_pipeline.id"), nullable=False)
    titulo_caso = Column(String(200), nullable=False)
    prioridad = Column(SAEnum(PrioridadCasoEnum), default=PrioridadCasoEnum.MEDIA)
    estado = Column(SAEnum(EstadoCasoEnum), default=EstadoCasoEnum.ABIERTO)
    origen_canal = Column(SAEnum(CanalOrigenEnum), nullable=False)
    origen_detalle_id = Column(String)
    payload_web = Column(JSONB, nullable=True)
    asignado_a_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    fecha_creacion = Column(DateTime, default=_utcnow)
    fecha_cierre = Column(DateTime, nullable=True)
    sla_vencimiento_contacto = Column(DateTime, nullable=False)
    is_overdue = Column(Boolean, default=False)

    pipeline = relationship("PipelineCRM", back_populates="casos")
    etapa_actual = relationship("EtapaPipeline", back_populates="casos")
    interacciones = relationship("InteraccionCRM", back_populates="caso",
                                 cascade="all, delete-orphan")
    tareas = relationship("TareaCRM", back_populates="caso",
                          cascade="all, delete-orphan")


# ──────────────────────────────────────────────
# INTERACCIONES (BITÁCORA CALL CENTER)
# ──────────────────────────────────────────────

class InteraccionCRM(Base):
    __tablename__ = "crm_interacciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id"), nullable=False)
    realizado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    tipo = Column(SAEnum(TipoInteraccionEnum), nullable=False)
    fecha_interaccion = Column(DateTime, default=_utcnow)
    resumen = Column(Text, nullable=False)
    plantilla_usada_id = Column(Integer, ForeignKey("crm_plantillas_mensaje.id"), nullable=True)

    caso = relationship("CasoCRM", back_populates="interacciones")


# ──────────────────────────────────────────────
# TAREAS CRM
# ──────────────────────────────────────────────

class TareaCRM(Base):
    __tablename__ = "crm_tareas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    caso_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id"), nullable=False)
    asignado_a_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    fecha_vencimiento = Column(DateTime, nullable=False)
    completada = Column(Boolean, default=False)
    fecha_completada = Column(DateTime, nullable=True)

    caso = relationship("CasoCRM", back_populates="tareas")

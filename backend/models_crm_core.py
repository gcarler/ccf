"""CRM Core — Pipeline, Casos, Interacciones, Tareas (Centro de Consolidación).

Modelos para el CRM 2.0: pipelines configurables, call center omnicanal,
trazabilidad de origen, y SLAs de tiempo de respuesta.
"""
from datetime import datetime

import enum
import uuid as _uuid

from sqlalchemy import (Boolean, Column, DateTime, Enum as SAEnum, ForeignKey,
                        Integer, String, Text, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.hybrid import hybrid_property
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
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    etapas = relationship("EtapaPipeline", back_populates="pipeline",
                          order_by="EtapaPipeline.orden",
                          cascade="all, delete-orphan")
    casos = relationship("CasoCRM", back_populates="pipeline")


class EtapaPipeline(Base):
    __tablename__ = "crm_etapas_pipeline"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "orden", name="uq_etapa_pipeline_orden"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    orden = Column(Integer, nullable=False)
    requiere_accion = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    pipeline = relationship("PipelineCRM", back_populates="etapas")
    casos = relationship("CasoCRM", back_populates="etapa_actual")


# ──────────────────────────────────────────────
# PLANTILLAS
# ──────────────────────────────────────────────

class PlantillaMensaje(Base):
    __tablename__ = "crm_plantillas_mensaje"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(150), nullable=False)
    canal = Column(SAEnum(TipoInteraccionEnum), nullable=False, index=True)
    contenido_texto = Column(Text, nullable=False)
    creado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    creado_por = relationship("Persona", foreign_keys=[creado_por_id])


# ──────────────────────────────────────────────
# CASOS (TICKETS)
# ──────────────────────────────────────────────

class CasoCRM(Base):
    __tablename__ = "crm_casos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False, index=True)
    pipeline_id = Column(Integer, ForeignKey("crm_pipelines.id"), nullable=False, index=True)
    etapa_actual_id = Column(Integer, ForeignKey("crm_etapas_pipeline.id"), nullable=False, index=True)
    titulo_caso = Column(String(200), nullable=False)
    prioridad = Column(SAEnum(PrioridadCasoEnum), default=PrioridadCasoEnum.MEDIA, index=True)
    estado = Column(SAEnum(EstadoCasoEnum), default=EstadoCasoEnum.ABIERTO, index=True)
    origen_canal = Column(SAEnum(CanalOrigenEnum), nullable=False, index=True)
    origen_detalle_id = Column(String(200), nullable=True, index=True)
    payload_web = Column(JSONB, nullable=True)
    asignado_a_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    fecha_creacion = Column(DateTime(timezone=True), default=_utcnow, index=True)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    sla_vencimiento_contacto = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    @hybrid_property
    def is_overdue(self) -> bool:
        if self.sla_vencimiento_contacto is None:
            return False
        return _utcnow() > self.sla_vencimiento_contacto

    @is_overdue.expression
    def is_overdue(cls):
        return (cls.sla_vencimiento_contacto != None) & (cls.sla_vencimiento_contacto < func.now())  # noqa: E711

    persona = relationship("Persona", foreign_keys=[persona_id])
    asignado_a = relationship("Persona", foreign_keys=[asignado_a_id])
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
    caso_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id", ondelete="CASCADE"), nullable=False, index=True)
    realizado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    tipo = Column(SAEnum(TipoInteraccionEnum), nullable=False, index=True)
    fecha_interaccion = Column(DateTime(timezone=True), default=_utcnow, index=True)
    resumen = Column(Text, nullable=False)
    duration_seconds = Column(Integer, default=0)
    plantilla_usada_id = Column(Integer, ForeignKey("crm_plantillas_mensaje.id"), nullable=True)

    caso = relationship("CasoCRM", back_populates="interacciones")
    realizado_por = relationship("Persona", foreign_keys=[realizado_por_id])


# ──────────────────────────────────────────────
# TAREAS CRM
# ──────────────────────────────────────────────

class TareaCRM(Base):
    __tablename__ = "crm_tareas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    caso_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id", ondelete="CASCADE"), nullable=False, index=True)
    asignado_a_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    fecha_vencimiento = Column(DateTime(timezone=True), nullable=False, index=True)
    completada = Column(Boolean, default=False, index=True)
    fecha_completada = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    caso = relationship("CasoCRM", back_populates="tareas")
    asignado_a = relationship("Persona", foreign_keys=[asignado_a_id])

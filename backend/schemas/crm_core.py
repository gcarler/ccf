"""CRM Core 2.0 — Pydantic schemas for Pipelines, Casos, Interacciones, Tareas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.schemas._common import orm_config


# ──────────────────────────────────────────────
# EtapaPipeline
# ──────────────────────────────────────────────

class EtapaPipelineResponse(BaseModel):
    id: int
    pipeline_id: int
    nombre: str
    orden: int
    requiere_accion: bool

    model_config = orm_config


class EtapaPipelineCreate(BaseModel):
    pipeline_id: int
    nombre: str
    orden: int
    requiere_accion: bool = True


# ──────────────────────────────────────────────
# PipelineCRM
# ──────────────────────────────────────────────

class PipelineCRMResponse(BaseModel):
    id: int
    nombre: str
    tipo: str
    descripcion: Optional[str] = None
    sede_id: int
    activo: bool
    etapas: list[EtapaPipelineResponse] = []

    model_config = orm_config


class PipelineCRMCreate(BaseModel):
    nombre: str
    tipo: str
    descripcion: Optional[str] = None
    sede_id: int
    activo: bool = True


# ──────────────────────────────────────────────
# PlantillaMensaje
# ──────────────────────────────────────────────

class PlantillaMensajeResponse(BaseModel):
    id: int
    titulo: str
    canal: str
    contenido_texto: str
    creado_por_id: Optional[str] = None

    model_config = orm_config


class PlantillaMensajeCreate(BaseModel):
    titulo: str
    canal: str
    contenido_texto: str


# ──────────────────────────────────────────────
# TareaCRM
# ──────────────────────────────────────────────

class TareaCRMResponse(BaseModel):
    id: str
    caso_id: str
    asignado_a_id: str
    titulo: str
    descripcion: Optional[str] = None
    fecha_vencimiento: datetime
    completada: bool
    fecha_completada: Optional[datetime] = None

    model_config = orm_config


class TareaCRMCreate(BaseModel):
    caso_id: str
    titulo: str
    descripcion: Optional[str] = None
    fecha_vencimiento: datetime
    asignado_a_id: str


# ──────────────────────────────────────────────
# InteraccionCRM
# ──────────────────────────────────────────────

class InteraccionCRMResponse(BaseModel):
    id: int
    caso_id: str
    realizado_por_id: str
    tipo: str
    fecha_interaccion: datetime
    resumen: str
    plantilla_usada_id: Optional[int] = None

    model_config = orm_config


class InteraccionCRMCreate(BaseModel):
    caso_id: str
    tipo: str
    resumen: str
    plantilla_usada_id: Optional[int] = None


# ──────────────────────────────────────────────
# CasoCRM
# ──────────────────────────────────────────────

class CasoCRMResponse(BaseModel):
    id: str
    persona_id: str
    sede_id: int
    pipeline_id: int
    etapa_actual_id: int
    titulo_caso: str
    prioridad: str
    estado: str
    origen_canal: str
    origen_detalle_id: Optional[str] = None
    payload_web: Optional[dict] = None
    asignado_a_id: Optional[str] = None
    fecha_creacion: datetime
    fecha_cierre: Optional[datetime] = None
    sla_vencimiento_contacto: datetime
    is_overdue: bool
    interacciones: list[InteraccionCRMResponse] = []
    tareas: list[TareaCRMResponse] = []

    model_config = orm_config


class CasoCRMCreate(BaseModel):
    persona_id: str
    sede_id: int
    pipeline_id: int
    etapa_actual_id: int
    titulo_caso: str
    prioridad: str = "MEDIA"
    estado: str = "ABIERTO"
    origen_canal: str
    origen_detalle_id: Optional[str] = None
    payload_web: Optional[dict] = None
    asignado_a_id: Optional[str] = None
    sla_vencimiento_contacto: datetime

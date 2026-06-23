"""CRM Core 2.0 — Pydantic schemas (from backend.schemas._common import orm_config)."""
from __future__ import annotations
from uuid import UUID

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from backend.schemas._common import orm_config  # ConfigDict(from_attributes=True)


# ── Pipeline ────────────────────────────────────────────

class PipelineCRMCreate(BaseModel):
    nombre: str
    tipo: str
    descripcion: Optional[str] = None
    sede_id: str
    activo: bool = True


class PipelineCRMResponse(BaseModel):
    model_config = orm_config
    id: UUID
    nombre: str
    tipo: str
    descripcion: Optional[str] = None
    sede_id: str
    activo: bool
    etapas: List[EtapaPipelineResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Etapa Pipeline ──────────────────────────────────────

class EtapaPipelineCreate(BaseModel):
    pipeline_id: UUID
    nombre: str
    orden: int
    color: Optional[str] = None
    requiere_accion: bool = False
    sla_hours: Optional[int] = None


class EtapaPipelineResponse(BaseModel):
    model_config = orm_config
    id: UUID
    pipeline_id: UUID
    nombre: str
    orden: int
    color: Optional[str] = None
    requiere_accion: bool
    sla_hours: Optional[int] = None
    created_at: Optional[datetime] = None


# ── Plantilla Mensaje ───────────────────────────────────

class PlantillaMensajeCreate(BaseModel):
    titulo: str
    canal: str = "WHATSAPP"
    contenido_texto: str
    contenido_html: Optional[str] = None


class PlantillaMensajeResponse(BaseModel):
    model_config = orm_config
    id: UUID
    titulo: str
    canal: str
    contenido_texto: str
    contenido_html: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Caso CRM ────────────────────────────────────────────

class CasoCRMCreate(BaseModel):
    persona_id: UUID
    sede_id: str
    pipeline_id: Optional[int] = None
    etapa_actual_id: Optional[int] = None
    titulo_caso: str
    descripcion: Optional[str] = None
    prioridad: str = "MEDIA"
    estado: str = "ABIERTO"
    origen_canal: str = "MANUAL"
    origen_detalle_id: Optional[str] = None
    payload_web: Optional[dict] = None
    asignado_a_id: Optional[str] = None
    sla_vencimiento_contacto: Optional[datetime] = None
    created_by_id: Optional[str] = None


class CasoCRMResponse(BaseModel):
    model_config = orm_config
    id: str  # UUID as string
    persona_id: UUID
    sede_id: str
    pipeline_id: Optional[int] = None
    etapa_actual_id: Optional[int] = None
    titulo_caso: str
    descripcion: Optional[str] = None
    prioridad: str
    estado: str
    origen_canal: str
    origen_detalle_id: Optional[str] = None
    payload_web: Optional[dict] = None
    asignado_a_id: Optional[str] = None
    sla_vencimiento_contacto: Optional[datetime] = None
    sla_vencimiento_cierre: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    motivo_cierre: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[str] = None
    interacciones: List[InteraccionCRMResponse] = []
    tareas: List[TareaCRMResponse] = []


# ── Interacción CRM ─────────────────────────────────────

class InteraccionCRMCreate(BaseModel):
    caso_id: str  # UUID as string
    tipo: str
    resumen: str
    detalle: Optional[str] = None
    plantilla_usada_id: Optional[int] = None
    realizada_por_id: Optional[str] = None


class InteraccionCRMResponse(BaseModel):
    model_config = orm_config
    id: UUID
    caso_id: str  # UUID as string
    tipo: str
    resumen: str
    detalle: Optional[str] = None
    plantilla_usada_id: Optional[int] = None
    realizada_por_id: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Tarea CRM ───────────────────────────────────────────

class TareaCRMCreate(BaseModel):
    caso_id: str  # UUID as string
    titulo: str
    descripcion: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    asignado_a_id: Optional[str] = None


class TareaCRMResponse(BaseModel):
    model_config = orm_config
    id: str  # UUID as string
    caso_id: str  # UUID as string
    titulo: str
    descripcion: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    completada: bool
    completada_en: Optional[datetime] = None
    asignado_a_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

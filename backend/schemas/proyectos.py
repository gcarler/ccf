from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config


# ── Proyecto ────────────────────────────────────────────────────────────────

class ProyectoBase(BaseModel):
    proyecto_padre_id: Optional[uuid.UUID] = None
    codigo_wbs: str = Field(..., min_length=1, max_length=50)
    sede_id: str
    nombre: str = Field(..., min_length=1, max_length=150)
    descripcion: Optional[str] = None
    estado: str = "PLANIFICACION"
    fecha_inicio: date
    fecha_fin_est: date
    presupuesto_est: Optional[float] = None


class ProyectoCreate(ProyectoBase):
    creado_por_id: int


class ProyectoUpdate(BaseModel):
    proyecto_padre_id: Optional[uuid.UUID] = None
    codigo_wbs: Optional[str] = None
    sede_id: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_est: Optional[date] = None
    fecha_fin_real: Optional[date] = None
    presupuesto_est: Optional[float] = None


# ── Equipo ──────────────────────────────────────────────────────────────────

class EquipoProyectoBase(BaseModel):
    persona_id: str
    rol_proyecto: str = Field(..., min_length=1, max_length=50)
    permiso_edicion: bool = False


class EquipoProyectoCreate(EquipoProyectoBase):
    pass


class EquipoProyectoSchema(EquipoProyectoBase):
    id: int
    proyecto_id: uuid.UUID
    fecha_asignacion: Optional[datetime] = None
    es_historico: bool = False

    model_config = orm_config


# ── Tarea ───────────────────────────────────────────────────────────────────

class TareaProyectoBase(BaseModel):
    tarea_padre_id: Optional[uuid.UUID] = None
    codigo_wbs: str = Field(..., min_length=1, max_length=50)
    titulo: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    estado: str = "POR_HACER"
    prioridad: str = "MEDIA"
    asignado_a_id: Optional[int] = None
    fecha_vencimiento: datetime


class TareaProyectoCreate(TareaProyectoBase):
    creado_por_id: int


class TareaProyectoUpdate(BaseModel):
    tarea_padre_id: Optional[uuid.UUID] = None
    codigo_wbs: Optional[str] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    asignado_a_id: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None


class TareaProyectoSchema(TareaProyectoBase):
    id: uuid.UUID
    proyecto_id: uuid.UUID
    creado_por_id: int
    fecha_completado: Optional[datetime] = None

    subtareas: list[TareaProyectoSchema] = Field(default_factory=list)

    model_config = orm_config


# ── Dependencias ────────────────────────────────────────────────────────────

class DependenciaTareaCreate(BaseModel):
    tarea_bloqueante_id: uuid.UUID
    tipo_dependencia: str = "FIN_A_INICIO"


class DependenciaTareaSchema(BaseModel):
    tarea_bloqueante_id: uuid.UUID
    tarea_bloqueada_id: uuid.UUID
    tipo_dependencia: str = "FIN_A_INICIO"

    model_config = orm_config


# ── Comentarios ─────────────────────────────────────────────────────────────

class ComentarioTareaCreate(BaseModel):
    comentario: str = Field(..., min_length=1)


class ComentarioTareaSchema(BaseModel):
    id: int
    tarea_id: uuid.UUID
    persona_id: str
    comentario: str
    fecha_creacion: Optional[datetime] = None

    model_config = orm_config


# ── Documentos ──────────────────────────────────────────────────────────────

class DocumentoCreate(BaseModel):
    tarea_id: Optional[uuid.UUID] = None
    seaweed_fid: str = Field(..., max_length=100)
    url_acceso: Optional[str] = None
    nombre_archivo: str = Field(..., max_length=255)
    extension: str = Field(..., max_length=20)
    peso_bytes: int


class DocumentoSchema(BaseModel):
    id: uuid.UUID
    proyecto_id: uuid.UUID
    tarea_id: Optional[uuid.UUID] = None
    seaweed_fid: str
    url_acceso: Optional[str] = None
    nombre_archivo: str
    extension: str
    peso_bytes: int
    subido_por_id: int
    fecha_subida: Optional[datetime] = None
    activo: bool = True

    model_config = orm_config


# ── Response compuesto (proyecto + relaciones) ──────────────────────────────
# Definido DESPUÉS de EquipoProyectoSchema y TareaProyectoSchema

class ProyectoSchema(ProyectoBase):
    id: uuid.UUID
    fecha_fin_real: Optional[date] = None
    creado_por_id: int
    fecha_creacion: Optional[datetime] = None

    equipo: list[EquipoProyectoSchema] = Field(default_factory=list)
    tareas: list[TareaProyectoSchema] = Field(default_factory=list)

    model_config = orm_config

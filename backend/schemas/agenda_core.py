"""Agenda / Calendario Unificado — Pydantic schemas.

RecursoFisico, EventoAgenda, ParticipanteEvento, ReservaRecurso.
"""
from __future__ import annotations
from uuid import UUID

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.schemas._common import orm_config


# ═══════════════════════════════════════════════════════════════════
# RecursoFisico
# ═══════════════════════════════════════════════════════════════════

class RecursoFisicoResponse(BaseModel):
    id: UUID
    sede_id: str
    nombre: str
    tipo: str
    capacidad_maxima: Optional[int] = None
    activo: bool

    model_config = orm_config


class RecursoFisicoCreate(BaseModel):
    sede_id: str
    nombre: str
    tipo: str
    capacidad_maxima: Optional[int] = None
    activo: bool = True


# ═══════════════════════════════════════════════════════════════════
# EventoAgenda
# ═══════════════════════════════════════════════════════════════════

class EventoAgendaResponse(BaseModel):
    id: UUID
    sede_id: str
    modulo_origen: str
    entidad_origen_id: Optional[str] = None
    titulo: str
    descripcion: Optional[str] = None
    fecha_inicio: datetime
    fecha_fin: datetime
    todo_el_dia: bool
    regla_recurrencia: Optional[str] = None
    fecha_limite_recurrencia: Optional[datetime] = None
    excepciones_recurrencia: list[str] = []
    recordatorios_config: list = []
    color_hex: Optional[str] = None
    ubicacion_texto: Optional[str] = None
    url_conferencia: Optional[str] = None
    organizador_persona_id: str
    visibilidad: str
    estado: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    participantes: list[ParticipanteEventoResponse] = []
    reservas: list[ReservaRecursoResponse] = []

    model_config = orm_config


class EventoAgendaCreate(BaseModel):
    sede_id: str
    modulo_origen: str = "MANUAL"
    entidad_origen_id: Optional[str] = None
    titulo: str
    descripcion: Optional[str] = None
    fecha_inicio: datetime
    fecha_fin: datetime
    todo_el_dia: bool = False
    regla_recurrencia: Optional[str] = None
    fecha_limite_recurrencia: Optional[datetime] = None
    excepciones_recurrencia: list[str] = []
    recordatorios_config: list = []
    color_hex: Optional[str] = None
    ubicacion_texto: Optional[str] = None
    url_conferencia: Optional[str] = None
    organizador_persona_id: str
    visibilidad: str = "PRIVADO"
    estado: str = "ACTIVO"


# ═══════════════════════════════════════════════════════════════════
# ParticipanteEvento
# ═══════════════════════════════════════════════════════════════════

class ParticipanteEventoResponse(BaseModel):
    id: UUID
    evento_id: str
    persona_id: UUID
    estado_confirmacion: str
    es_requerido: bool
    fecha_confirmacion: Optional[datetime] = None

    model_config = orm_config


class ParticipanteEventoCreate(BaseModel):
    evento_id: str
    persona_id: UUID
    estado_confirmacion: str = "PENDIENTE"
    es_requerido: bool = True
    fecha_confirmacion: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════
# ReservaRecurso
# ═══════════════════════════════════════════════════════════════════

class ReservaRecursoResponse(BaseModel):
    id: UUID
    evento_id: str
    recurso_id: str
    bloqueo_inicio: datetime
    bloqueo_fin: datetime

    model_config = orm_config


class ReservaRecursoCreate(BaseModel):
    evento_id: str
    recurso_id: str
    bloqueo_inicio: datetime
    bloqueo_fin: datetime

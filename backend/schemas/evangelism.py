"""Esquemas Pydantic del módulo de Evangelismo refactorizado.

Contiene los nuevos esquemas con nomenclatura en español y enums.
Los esquemas antiguos en schemas/crm.py se mantienen para back-compat.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from backend.schemas._common import orm_config


# ──────────────────────────────────────────────
# ENUMS (re-exportados para uso en endpoints)
# ──────────────────────────────────────────────

class ClaseEstrategiaEnum(str, Enum):
    RELACIONAL = "RELACIONAL"
    EVENTO_MASIVO = "EVENTO_MASIVO"
    SECTORIAL = "SECTORIAL"


class RolEnGrupoEnum(str, Enum):
    LIDER = "LIDER"
    COLIDER = "COLIDER"
    MIEMBRO = "MIEMBRO"
    VISITANTE = "VISITANTE"


class EstadoAsistenciaEnum(str, Enum):
    ASISTIO = "ASISTIO"
    FALTO = "FALTO"
    EXCUSA = "EXCUSA"


class TipoSeguimientoEnum(str, Enum):
    LLAMADA = "LLAMADA"
    MENSAJE = "MENSAJE_WHATSAPP"
    VISITA_PRESENCIAL = "VISITA_PRESENCIAL"
    ORACION = "ORACION"


class FrecuenciaEnum(str, Enum):
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"
    EVENTO_UNICO = "EVENTO_UNICO"


class EstadoSesionEnum(str, Enum):
    PENDIENTE = "PENDIENTE"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"


# ──────────────────────────────────────────────
# ESTRATEGIA DE EVANGELISMO
# ──────────────────────────────────────────────

class EstrategiaEvangelismoBase(BaseModel):
    name: str
    description: Optional[str] = None
    clase_raiz: Optional[ClaseEstrategiaEnum] = None
    activa: bool = True

    # Campos legacy (back-compat)
    typology: Optional[str] = None
    recurrence: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    event_format: Optional[str] = None
    phases: Optional[List[Dict[str, Any]]] = None
    phase_count: Optional[int] = None
    niche_objective: Optional[str] = None
    strategy_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "active"
    group_count: Optional[int] = None


class EstrategiaEvangelismoCreate(EstrategiaEvangelismoBase):
    pass


class EstrategiaEvangelismoUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    clase_raiz: Optional[ClaseEstrategiaEnum] = None
    activa: Optional[bool] = None

    # Campos legacy
    typology: Optional[str] = None
    recurrence: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    event_format: Optional[str] = None
    phases: Optional[List[Dict[str, Any]]] = None
    niche_objective: Optional[str] = None
    strategy_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None


class EstrategiaEvangelismoResponse(EstrategiaEvangelismoBase):
    id: int
    codigo: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = orm_config


# ──────────────────────────────────────────────
# ROL PERSONALIZADO DE ESTRATEGIA
# ──────────────────────────────────────────────

class RolPersonalizadoEstrategiaBase(BaseModel):
    nombre_rol: str
    descripcion: Optional[str] = None


class RolPersonalizadoEstrategiaCreate(RolPersonalizadoEstrategiaBase):
    estrategia_id: str


class RolPersonalizadoEstrategiaResponse(RolPersonalizadoEstrategiaBase):
    id: int
    estrategia_id: str
    created_at: datetime
    model_config = orm_config


# ──────────────────────────────────────────────
# PARTICIPANTE DE GRUPO
# ──────────────────────────────────────────────

class ParticipanteGrupoBase(BaseModel):
    role: str = "miembro"
    rol_personalizado_id: Optional[int] = None
    activo: bool = True


class ParticipanteGrupoCreate(ParticipanteGrupoBase):
    grupo_id: int
    persona_id: str


class ParticipanteGrupoUpdate(BaseModel):
    role: Optional[str] = None
    rol_personalizado_id: Optional[int] = None
    activo: Optional[bool] = None


class ParticipanteGrupoResponse(ParticipanteGrupoBase):
    id: int
    grupo_id: int
    persona_id: str
    fecha_ingreso: Optional[datetime] = None
    model_config = orm_config


# ──────────────────────────────────────────────
# ASISTENCIA A SESIÓN
# ──────────────────────────────────────────────

class AsistenciaSesionBase(BaseModel):
    estado: EstadoAsistenciaEnum = EstadoAsistenciaEnum.ASISTIO
    es_primera_vez: bool = False
    requiere_seguimiento: bool = False
    motivo_excusa_id: Optional[int] = None
    detalle_excusa: Optional[str] = None
    notas: Optional[str] = None


class AsistenciaSesionCreate(AsistenciaSesionBase):
    sesion_id: int
    persona_id: str


class AsistenciaSesionUpdate(BaseModel):
    estado: Optional[EstadoAsistenciaEnum] = None
    es_primera_vez: Optional[bool] = None
    requiere_seguimiento: Optional[bool] = None
    motivo_excusa_id: Optional[int] = None
    detalle_excusa: Optional[str] = None
    notas: Optional[str] = None


class AsistenciaSesionResponse(AsistenciaSesionBase):
    id: int
    sesion_id: int
    persona_id: str
    attended: Optional[bool] = None
    status: Optional[str] = None
    model_config = orm_config


# ──────────────────────────────────────────────
# REGISTRO DE SEGUIMIENTO
# ──────────────────────────────────────────────

class RegistroSeguimientoBase(BaseModel):
    tipo: TipoSeguimientoEnum
    fecha_programada: Optional[datetime] = None
    notas: Optional[str] = None


class RegistroSeguimientoCreate(RegistroSeguimientoBase):
    asistencia_id: int


class RegistroSeguimientoUpdate(BaseModel):
    fecha_realizada: Optional[datetime] = None
    realizado_por_persona_id: Optional[str] = None
    notas: Optional[str] = None
    completado: Optional[bool] = None
    resultado: Optional[str] = None


class RegistroSeguimientoResponse(RegistroSeguimientoBase):
    id: int
    asistencia_id: int
    fecha_realizada: Optional[datetime] = None
    realizado_por_persona_id: Optional[str] = None
    completado: bool = False
    resultado: Optional[str] = None
    created_at: datetime
    model_config = orm_config


# ──────────────────────────────────────────────
# MOTIVO EXCUSA
# ──────────────────────────────────────────────

class MotivoExcusaBase(BaseModel):
    descripcion: str
    activo: bool = True


class MotivoExcusaCreate(MotivoExcusaBase):
    pass


class MotivoExcusaUpdate(BaseModel):
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


class MotivoExcusaResponse(MotivoExcusaBase):
    id: int
    es_del_sistema: bool
    model_config = orm_config


# ──────────────────────────────────────────────
# BULK ASISTENCIA
# ──────────────────────────────────────────────

class AsistenciaBulkItem(BaseModel):
    persona_id: str
    estado: EstadoAsistenciaEnum = EstadoAsistenciaEnum.ASISTIO
    es_primera_vez: bool = False
    requiere_seguimiento: bool = False
    notas: Optional[str] = None


class AsistenciaBulkCreate(BaseModel):
    sesion_id: int
    registros: List[AsistenciaBulkItem]


# ──────────────────────────────────────────────
# GRUPO EVANGELISMO (back-compat con CellGroup)
# ──────────────────────────────────────────────

class GrupoEvangelismoCreate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    leader_name: Optional[str] = None
    evangelism_strategy_id: int
    leader_id: Optional[str] = None
    assistant_id: Optional[str] = None
    host_id: Optional[str] = None
    capacity: int = 15
    status: Optional[str] = "Activo"
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    base_attendee_ids: Optional[List[str]] = None


class CellGroupMemberWithRole(BaseModel):
    persona_id: str
    role: str = "miembro"


class GrupoEvangelismoUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None
    leader_id: Optional[str] = None
    assistant_id: Optional[str] = None
    host_id: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    base_attendee_ids: Optional[List[str]] = None
    base_attendees_with_roles: Optional[List[CellGroupMemberWithRole]] = None


class SesionGrupoCreate(BaseModel):
    grupo_id: int
    season_id: Optional[int] = None
    session_date: datetime
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    status: str = "Realizada"


class SesionGrupoUpdate(BaseModel):
    session_date: Optional[datetime] = None
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    status: Optional[str] = None


class AsistenciaGrupoCreate(BaseModel):
    persona_id: str
    status: str = "present"
    notes: Optional[str] = None

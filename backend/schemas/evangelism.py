"""Esquemas Pydantic del modulo de Evangelismo."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from uuid import UUID
from pydantic import AliasChoices, BaseModel, Field, computed_field, model_validator

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
    ANFITRION = "ANFITRION"
    ASISTENTE = "ASISTENTE"
    INVITADO = "INVITADO"
    PERSONALIZADO = "PERSONALIZADO"


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
    BIMENSUAL = "BIMENSUAL"
    TRIMESTRAL = "TRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"
    EVENTO_UNICO = "EVENTO_UNICO"


class EstadoSesionEnum(str, Enum):
    PENDIENTE = "PENDIENTE"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"


class HabilitacionSesionEnum(str, Enum):
    DESHABILITADO = "DESHABILITADO"
    HABILITADO = "HABILITADO"
    CERRADO = "CERRADO"
    CANCELADA = "CANCELADA"


# ──────────────────────────────────────────────
# ESTRATEGIA DE EVANGELISMO
# ──────────────────────────────────────────────

class EstrategiaEvangelismoBase(BaseModel):
    name: str
    description: Optional[str] = None
    clase_raiz: Optional[str] = None
    activa: bool = True

    # Campos publicados por la API de estrategia
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
    clase_raiz: Optional[str] = None  # string, no enum — el frontend envía minúsculas
    activa: Optional[bool] = None
    default_role_id: Optional[UUID] = None

    # Campos publicados por la API de estrategia
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
    id: UUID
    codigo: Optional[str] = None
    default_role_id: Optional[UUID] = None
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
    estrategia_id: UUID


class RolPersonalizadoEstrategiaResponse(RolPersonalizadoEstrategiaBase):
    id: UUID
    estrategia_id: UUID
    created_at: datetime
    model_config = orm_config


# ──────────────────────────────────────────────
# PARTICIPANTE DE GRUPO
# ──────────────────────────────────────────────

class ParticipanteGrupoBase(BaseModel):
    role: str = "participante"
    rol_personalizado_id: Optional[UUID] = None
    activo: bool = True


class ParticipanteGrupoCreate(ParticipanteGrupoBase):
    grupo_id: UUID
    persona_id: UUID


class ParticipanteGrupoUpdate(BaseModel):
    role: Optional[str] = None
    rol_personalizado_id: Optional[UUID] = None
    activo: Optional[bool] = None


class ParticipanteGrupoResponse(ParticipanteGrupoBase):
    id: UUID
    grupo_id: UUID
    persona_id: UUID
    fecha_ingreso: Optional[datetime] = None
    model_config = orm_config


# ──────────────────────────────────────────────
# ASISTENCIA A SESIÓN
# ──────────────────────────────────────────────

class AsistenciaSesionBase(BaseModel):
    estado: EstadoAsistenciaEnum = EstadoAsistenciaEnum.ASISTIO
    es_primera_vez: bool = False
    requiere_seguimiento: bool = False
    motivo_excusa_id: Optional[UUID] = None
    detalle_excusa: Optional[str] = None
    notas: Optional[str] = None


class AsistenciaSesionCreate(AsistenciaSesionBase):
    sesion_id: str
    persona_id: UUID


class AsistenciaSesionUpdate(BaseModel):
    estado: Optional[EstadoAsistenciaEnum] = None
    es_primera_vez: Optional[bool] = None
    requiere_seguimiento: Optional[bool] = None
    motivo_excusa_id: Optional[UUID] = None
    detalle_excusa: Optional[str] = None
    notas: Optional[str] = None


class AsistenciaSesionResponse(AsistenciaSesionBase):
    id: UUID
    sesion_id: str
    persona_id: UUID
    attended: Optional[bool] = None
    status: Optional[str] = None
    model_config = orm_config


# ──────────────────────────────────────────────
# REGISTRO DE SEGUIMIENTO
# Alineado con columnas reales del modelo:
#   tipo, fecha_seguimiento, observaciones, estado_completado, responsable_id
# ──────────────────────────────────────────────

class RegistroSeguimientoBase(BaseModel):
    tipo: TipoSeguimientoEnum
    observaciones: Optional[str] = None
    fecha_seguimiento: Optional[datetime] = None
    estado_completado: bool = True

    @model_validator(mode="before")
    @classmethod
    def _map_public_names(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "notas" in data and "observaciones" not in data:
                data["observaciones"] = data.pop("notas")
            if "completado" in data and "estado_completado" not in data:
                data["estado_completado"] = data.pop("completado")
            if "fecha_realizada" in data and "fecha_seguimiento" not in data:
                data["fecha_seguimiento"] = data.pop("fecha_realizada")
            if "fecha_programada" in data and "fecha_seguimiento" not in data:
                data["fecha_seguimiento"] = data.pop("fecha_programada")
        return data


class RegistroSeguimientoCreate(RegistroSeguimientoBase):
    asistencia_id: str
    responsable_id: Optional[str] = None


class RegistroSeguimientoUpdate(BaseModel):
    observaciones: Optional[str] = None
    estado_completado: Optional[bool] = None
    fecha_seguimiento: Optional[datetime] = None
    responsable_id: Optional[str] = None
    tipo: Optional[TipoSeguimientoEnum] = None

    @model_validator(mode="before")
    @classmethod
    def _map_public_names(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "notas" in data and "observaciones" not in data:
                data["observaciones"] = data.pop("notas")
            if "completado" in data and "estado_completado" not in data:
                data["estado_completado"] = data.pop("completado")
            if "fecha_realizada" in data and "fecha_seguimiento" not in data:
                data["fecha_seguimiento"] = data.pop("fecha_realizada")
            if "realizado_por_persona_id" in data and "responsable_id" not in data:
                data["responsable_id"] = data.pop("realizado_por_persona_id")
        return data


class RegistroSeguimientoResponse(BaseModel):
    id: UUID
    asistencia_id: str
    tipo: TipoSeguimientoEnum
    observaciones: Optional[str] = None
    fecha_seguimiento: Optional[datetime] = None
    estado_completado: bool = True
    responsable_id: Optional[str] = None
    created_at: datetime

    @computed_field
    @property
    def completado(self) -> bool:
        return self.estado_completado

    @computed_field
    @property
    def notas(self) -> Optional[str]:
        return self.observaciones

    @computed_field
    @property
    def fecha_realizada(self) -> Optional[datetime]:
        return self.fecha_seguimiento

    @computed_field
    @property
    def fecha_programada(self) -> Optional[datetime]:
        return self.fecha_seguimiento

    @computed_field
    @property
    def realizado_por_persona_id(self) -> Optional[str]:
        return self.responsable_id

    @computed_field
    @property
    def resultado(self) -> Optional[str]:
        return None  # columna no existe en modelo, retorna None

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
    id: UUID
    es_del_sistema: bool
    model_config = orm_config


# ──────────────────────────────────────────────
# BULK ASISTENCIA
# ──────────────────────────────────────────────

class AsistenciaBulkItem(BaseModel):
    persona_id: UUID
    estado: EstadoAsistenciaEnum = EstadoAsistenciaEnum.ASISTIO
    es_primera_vez: bool = False
    requiere_seguimiento: bool = False
    notas: Optional[str] = None


class AsistenciaBulkCreate(BaseModel):
    sesion_id: str
    registros: List[AsistenciaBulkItem]


# ──────────────────────────────────────────────
# GRUPO EVANGELISMO
# ──────────────────────────────────────────────

class GrupoEvangelismoCreate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    leader_name: Optional[str] = None
    evangelism_strategy_id: Optional[UUID] = Field(
        default=None,
        validation_alias=AliasChoices("evangelism_strategy_id", "estrategia_id"),
    )
    leader_id: Optional[UUID] = None
    assistant_id: Optional[UUID] = None
    host_id: Optional[UUID] = None
    capacity: int = 15
    status: Optional[str] = "Activo"
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    base_attendee_ids: Optional[List[UUID]] = None
    base_attendees_with_roles: Optional[List["ParticipanteGrupoConRol"]] = None


# Schema para participantes de grupo
class ParticipanteGrupoConRol(BaseModel):
    persona_id: UUID
    role: str = "participante"
    rol_personalizado_id: Optional[UUID] = None


class GrupoEvangelismoUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None
    leader_id: Optional[UUID] = None
    assistant_id: Optional[UUID] = None
    host_id: Optional[UUID] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    base_attendee_ids: Optional[List[UUID]] = None
    base_attendees_with_roles: Optional[List[ParticipanteGrupoConRol]] = None


class SesionGrupoCreate(BaseModel):
    grupo_id: Optional[UUID] = None
    season_id: Optional[UUID] = None
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
    persona_id: UUID
    status: str = "present"
    notes: Optional[str] = None

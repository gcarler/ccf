"""Esquemas Pydantic del modulo de Evangelismo."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from backend.schemas._common import orm_config


def _coerce_uuid_or_none(v):
    """Coerce str|UUID|None to UUID|None before pydantic validation.

    Permite compatibilidad con callers que serializan el body a JSON antes
    de invocar ``model_validate`` (frontend + tests legacy). Ningún valor
    malformado se convierte silenciosamente — el validador del tipo
    ``UUID`` lo rechaza después, evitando el 500.
    """
    if v is None or isinstance(v, UUID):
        return v
    try:
        return UUID(str(v))
    except (ValueError, AttributeError, TypeError):
        return v


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
    # El handler asigna estrategia_id desde path-param; no requiere del body.
    estrategia_id: Optional[UUID] = None


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
    sesion_id: UUID
    persona_id: UUID

    @field_validator("sesion_id", mode="before")
    @classmethod
    def _v_sesion_id(cls, v):
        """Acepta str o UUID; emite UUID antes de la validación."""
        return _coerce_uuid_or_none(v)


class AsistenciaSesionUpdate(BaseModel):
    estado: Optional[EstadoAsistenciaEnum] = None
    es_primera_vez: Optional[bool] = None
    requiere_seguimiento: Optional[bool] = None
    motivo_excusa_id: Optional[UUID] = None
    detalle_excusa: Optional[str] = None
    notas: Optional[str] = None


class AsistenciaSesionResponse(AsistenciaSesionBase):
    id: UUID
    sesion_id: UUID
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

class RegistroSeguimientoCreate(RegistroSeguimientoBase):
    # El handler asigna asistencia_id desde path-param; no requiere del body.
    asistencia_id: Optional[UUID] = None
    responsable_id: Optional[UUID] = None

    @field_validator("asistencia_id", "responsable_id", mode="before")
    @classmethod
    def _v_uuids(cls, v):
        return _coerce_uuid_or_none(v)


class RegistroSeguimientoUpdate(BaseModel):
    observaciones: Optional[str] = None
    estado_completado: Optional[bool] = None
    fecha_seguimiento: Optional[datetime] = None
    responsable_id: Optional[UUID] = None
    tipo: Optional[TipoSeguimientoEnum] = None

    @field_validator("responsable_id", mode="before")
    @classmethod
    def _v_responsable_id(cls, v):
        return _coerce_uuid_or_none(v)

class RegistroSeguimientoResponse(BaseModel):
    id: UUID
    # Cambiados de str → UUID para alinear con el ORM
    # ``RegistroSeguimiento.asistencia_id`` y ``responsable_id``. Pydantic v2
    # strict rechazaba implicit UUID→str; ahora acepta nativo y al serializar
    # a JSON (``model_dump(mode="json")`` o Pydantic encoder) emite string.
    asistencia_id: UUID
    tipo: TipoSeguimientoEnum
    observaciones: Optional[str] = None
    fecha_seguimiento: Optional[datetime] = None
    estado_completado: bool = True
    responsable_id: Optional[UUID] = None
    created_at: datetime

    model_config = orm_config

    @field_validator("asistencia_id", "responsable_id", mode="before")
    @classmethod
    def coerce_uuid_to_str_or_uuid(cls, v):
        """Acepta tanto ``str`` como ``UUID`` en la frontera para
        compatibilidad con callers que serializan el body a JSON antes
        de invocar ``model_validate``."""
        if v is None or isinstance(v, UUID):
            return v
        try:
            return UUID(str(v))
        except (ValueError, AttributeError):
            return v


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
    sesion_id: UUID
    registros: List[AsistenciaBulkItem]

    @field_validator("sesion_id", mode="before")
    @classmethod
    def _v_sesion_id_bulk(cls, v):
        """Acepta str o UUID; emite UUID antes de la validación.

        Coherente con ``AsistenciaSesionCreate.sesion_id`` — el flujo
        bulk termina llamando a ``crud.submit_asistencia(AsistenciaSesionCreate(...))``
        ya validado por ``_coerce_uuid_or_404``, así que el filtro del
        JOIN (``SesionGrupo.id == sesion_uuid``) no recibe nunca un str
        ni un None.
        """
        return _coerce_uuid_or_none(v)


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
    evangelism_strategy_id: Optional[UUID] = None
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
    report_deadline: Optional[datetime] = None
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
    report_deadline: Optional[datetime] = None
    status: Optional[str] = None


class AsistenciaGrupoCreate(BaseModel):
    persona_id: UUID
    status: str = "present"
    notes: Optional[str] = None


# ──────────────────────────────────────────────
# SESION GRUPO — respuesta
# ──────────────────────────────────────────────

class SesionGrupoResponse(BaseModel):
    """Schema de respuesta canonica para endpoints de ``SesionGrupo``.

    Serializa ``UUID`` a ``str`` y ``datetime`` a ISO-8601 para preservar
    el contrato que el frontend esperaba, antes expuesto como ``dict``
    manual en ``PUT /api/evangelism/sessions/{id}``. Unificar la
    serializacion evita drift de tipos entre backend y frontend y
    permite que el handler retorne un modelo Pydantic en vez de un
    ``dict`` artesanal.

    Los atributos del ORM se leen via ``from_attributes=True``
    (``orm_config``): los synonyms ``session_date``, ``status``,
    ``topic``, ``report_notes``, ``cancellation_reason`` se resuelven
    automaticamente desde las columnas en espanol de
    ``backend.models_evangelism.SesionGrupo``.
    """
    id: str
    grupo_id: str
    session_date: Optional[datetime] = None
    status: str = "Realizada"
    estado_habilitacion: str = "DESHABILITADO"
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    report_deadline: Optional[datetime] = None
    reported_at: Optional[datetime] = None

    model_config = orm_config

    @field_validator("id", "grupo_id", "reported_by_persona_id", mode="before")
    @classmethod
    def _coerce_uuid_to_str(cls, v):
        """Acepta ``UUID`` o ``str`` y siempre emite ``str``.

        Esencial para mantener el contrato historico con el frontend
        (donde ``session_id``, ``grupo_id`` y ``reported_by_persona_id``
        se reciben como string).
        """
        if v is None:
            return v
        if isinstance(v, UUID):
            return str(v)
        return v

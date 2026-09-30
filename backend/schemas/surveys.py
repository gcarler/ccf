"""Schemas Pydantic v2 para el módulo de Encuestas Dinámicas (Google Forms Parity)."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TipoPregunta(str, Enum):
    TEXTO_CORTO = "TEXTO_CORTO"
    PARRAFO = "PARRAFO"
    OPCION_MULTIPLE = "OPCION_MULTIPLE"
    CASILLAS = "CASILLAS"
    DESPLEGABLE = "DESPLEGABLE"
    ESCALA_LINEAL = "ESCALA_LINEAL"
    CUADRICULA_RADIO = "CUADRICULA_RADIO"
    CUADRICULA_CASILLAS = "CUADRICULA_CASILLAS"
    FECHA = "FECHA"
    HORA = "HORA"
    SUBIR_ARCHIVO = "SUBIR_ARCHIVO"
    SECCION_SALTO = "SECCION_SALTO"


class EstadoFormulario(str, Enum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    CERRADO = "CERRADO"
    ARCHIVADO = "ARCHIVADO"


class PreguntaOpcion(BaseModel):
    id: str = Field(default_factory=lambda: str(UUID(int=0)))
    label: str
    salto_seccion_id: Optional[str] = None
    es_otro: bool = False


class PreguntaFilaColumna(BaseModel):
    id: str
    label: str


class ConfigVisual(BaseModel):
    tema: str = "light"
    color_primario: str = "#2563eb"
    banner_url: Optional[str] = None
    logo_url: Optional[str] = None
    fuente: str = "Inter"


# ── PREGUNTAS ────────────────────────────────────────────────────────────────


class EncuestaPreguntaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    tipo_pregunta: TipoPregunta
    orden: int = 0
    es_requerida: bool = False
    opciones: List[Dict[str, Any]] = Field(default_factory=list)
    filas: List[Dict[str, Any]] = Field(default_factory=list)
    columnas: List[Dict[str, Any]] = Field(default_factory=list)
    escala_min: int = 1
    escala_max: int = 5
    escala_min_etiqueta: Optional[str] = None
    escala_max_etiqueta: Optional[str] = None
    archivo_tipos_permitidos: List[str] = Field(default_factory=list)
    archivo_max_mb: int = 10
    archivo_max_archivos: int = 1
    configuracion: Dict[str, Any] = Field(default_factory=dict)


class EncuestaPreguntaCreate(EncuestaPreguntaBase):
    pass


class EncuestaPreguntaUpdate(BaseModel):
    id: Optional[UUID] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    tipo_pregunta: Optional[TipoPregunta] = None
    orden: Optional[int] = None
    es_requerida: Optional[bool] = None
    opciones: Optional[List[Dict[str, Any]]] = None
    filas: Optional[List[Dict[str, Any]]] = None
    columnas: Optional[List[Dict[str, Any]]] = None
    escala_min: Optional[int] = None
    escala_max: Optional[int] = None
    escala_min_etiqueta: Optional[str] = None
    escala_max_etiqueta: Optional[str] = None
    archivo_tipos_permitidos: Optional[List[str]] = None
    archivo_max_mb: Optional[int] = None
    archivo_max_archivos: Optional[int] = None
    configuracion: Optional[Dict[str, Any]] = None


class EncuestaPreguntaResponse(EncuestaPreguntaBase):
    id: UUID
    formulario_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EncuestaPreguntasBatchRequest(BaseModel):
    preguntas: List[EncuestaPreguntaCreate]


# ── FORMULARIOS ──────────────────────────────────────────────────────────────


class EncuestaFormularioBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    slug: Optional[str] = None
    es_publico: bool = True
    requiere_autenticacion: bool = False
    limitar_una_respuesta: bool = False
    permitir_editar_respuesta: bool = False
    mostrar_barra_progreso: bool = True
    mensaje_confirmacion: Optional[str] = "¡Tu respuesta ha sido registrada exitosamente!"
    redirigir_url: Optional[str] = None
    fecha_apertura: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    max_respuestas: Optional[int] = None
    estado: EstadoFormulario = EstadoFormulario.BORRADOR
    config_visual: Dict[str, Any] = Field(default_factory=dict)
    ajustes: Dict[str, Any] = Field(default_factory=dict)


class EncuestaFormularioCreate(EncuestaFormularioBase):
    preguntas: Optional[List[EncuestaPreguntaCreate]] = None


class EncuestaFormularioUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    slug: Optional[str] = None
    es_publico: Optional[bool] = None
    requiere_autenticacion: Optional[bool] = None
    limitar_una_respuesta: Optional[bool] = None
    permitir_editar_respuesta: Optional[bool] = None
    mostrar_barra_progreso: Optional[bool] = None
    mensaje_confirmacion: Optional[str] = None
    redirigir_url: Optional[str] = None
    fecha_apertura: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    max_respuestas: Optional[int] = None
    estado: Optional[EstadoFormulario] = None
    config_visual: Optional[Dict[str, Any]] = None
    ajustes: Optional[Dict[str, Any]] = None


class EncuestaFormularioResponse(EncuestaFormularioBase):
    id: UUID
    sede_id: Optional[UUID] = None
    total_respuestas: int
    creado_por_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    preguntas: List[EncuestaPreguntaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EncuestaFormularioPublicResponse(BaseModel):
    id: UUID
    titulo: str
    descripcion: Optional[str] = None
    slug: Optional[str] = None
    es_publico: bool
    requiere_autenticacion: bool
    mostrar_barra_progreso: bool
    mensaje_confirmacion: Optional[str] = None
    redirigir_url: Optional[str] = None
    estado: EstadoFormulario
    config_visual: Dict[str, Any]
    preguntas: List[EncuestaPreguntaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ── RESPUESTAS Y ENVÍOS ───────────────────────────────────────────────────────


class RespuestaItemInput(BaseModel):
    pregunta_id: UUID
    valor_texto: Optional[str] = None
    valor_numero: Optional[float] = None
    valor_fecha: Optional[date] = None
    valor_hora: Optional[str] = None
    valor_json: Optional[Any] = None  # Lista de opciones seleccionadas, dict cuadrícula, etc.


class EncuestaSubmitRequest(BaseModel):
    respuestas: List[RespuestaItemInput]
    email_respondente: Optional[str] = None
    nombre_respondente: Optional[str] = None
    metadatos: Dict[str, Any] = Field(default_factory=dict)


class EncuestaSubmitResponse(BaseModel):
    status: str = "success"
    envio_id: UUID
    mensaje_confirmacion: str
    redirigir_url: Optional[str] = None


class EncuestaRespuestaDetalleResponse(BaseModel):
    id: UUID
    pregunta_id: UUID
    valor_texto: Optional[str] = None
    valor_numero: Optional[float] = None
    valor_fecha: Optional[date] = None
    valor_hora: Optional[str] = None
    valor_json: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)


class EncuestaRespuestaEnvioIndividualResponse(BaseModel):
    id: UUID
    formulario_id: UUID
    persona_id: Optional[UUID] = None
    usuario_id: Optional[UUID] = None
    email_respondente: Optional[str] = None
    nombre_respondente: Optional[str] = None
    metadatos: Dict[str, Any]
    created_at: datetime
    detalles: List[EncuestaRespuestaDetalleResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ── ANALÍTICA Y TABLA ────────────────────────────────────────────────────────


class PreguntaAnalyticsSummary(BaseModel):
    pregunta_id: UUID
    titulo: str
    tipo_pregunta: str
    total_respuestas: int
    # Para opción múltiple, casillas, desplegables: conteos por opción {"Opción A": 14, ...}
    distribucion_opciones: Dict[str, int] = Field(default_factory=dict)
    # Para escala lineal y numéricas: media, min, max
    promedio: Optional[float] = None
    minimo: Optional[float] = None
    maximo: Optional[float] = None
    # Para texto corto, párrafo: lista de últimas respuestas representativas
    respuestas_recientes: List[str] = Field(default_factory=list)


class EncuestaAnalyticsSummary(BaseModel):
    formulario_id: UUID
    titulo: str
    total_respuestas: int
    primera_respuesta: Optional[datetime] = None
    ultima_respuesta: Optional[datetime] = None
    preguntas: List[PreguntaAnalyticsSummary] = Field(default_factory=list)


class EncuestaRespuestasTableResponse(BaseModel):
    total: int
    skip: int
    limit: int
    columnas: List[Dict[str, str]]  # [{"key": "created_at", "label": "Fecha"}, {"key": "p_<uuid>", "label": "Título"}]
    filas: List[Dict[str, Any]]

"""Schemas para la Biblioteca de Recursos CRM."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

# ── CategoriaRecurso ──────────────────────────────────────────────────────────

class CategoriaRecursoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    color_ui_hex: str = "#6B7280"


class CategoriaRecursoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    color_ui_hex: Optional[str] = None
    activo: Optional[bool] = None


class CategoriaRecursoOut(BaseModel):
    id: UUID
    nombre: str
    descripcion: Optional[str] = None
    color_ui_hex: str
    activo: bool

    @classmethod
    def from_orm_safe(cls, obj) -> "CategoriaRecursoOut":
        return cls(
            id=str(obj.id),
            nombre=obj.nombre,
            descripcion=obj.descripcion,
            color_ui_hex=obj.color_ui_hex or "#6B7280",
            activo=obj.activo,
        )


# ── RecursoAdjunto ────────────────────────────────────────────────────────────

class RecursoAdjuntoOut(BaseModel):
    id: UUID
    sede_id: str
    plantilla_id: Optional[str] = None
    nombre_recurso: str
    url_acceso: str
    nombre_archivo: str
    tipo_mime: str
    peso_bytes: int
    fecha_creacion: str

    @classmethod
    def from_orm_safe(cls, obj) -> "RecursoAdjuntoOut":
        return cls(
            id=str(obj.id),
            sede_id=str(obj.sede_id),
            plantilla_id=str(obj.plantilla_id) if obj.plantilla_id else None,
            nombre_recurso=obj.nombre_recurso,
            url_acceso=obj.url_acceso,
            nombre_archivo=obj.nombre_archivo,
            tipo_mime=obj.tipo_mime,
            peso_bytes=obj.peso_bytes,
            fecha_creacion=obj.fecha_creacion.isoformat(),
        )


# ── PlantillaMensaje ──────────────────────────────────────────────────────────

class PlantillaMensajeCreate(BaseModel):
    categoria_id: str
    titulo: str
    canal: str  # WHATSAPP | EMAIL | SMS
    asunto: Optional[str] = None
    contenido_texto: str
    contenido_html: Optional[str] = None
    variables_requeridas: List[str] = []
    meta_template_id: Optional[str] = None


class PlantillaMensajeUpdate(BaseModel):
    categoria_id: Optional[str] = None
    titulo: Optional[str] = None
    canal: Optional[str] = None
    asunto: Optional[str] = None
    contenido_texto: Optional[str] = None
    contenido_html: Optional[str] = None
    variables_requeridas: Optional[List[str]] = None
    meta_template_id: Optional[str] = None


class PlantillaMensajeOut(BaseModel):
    id: UUID
    sede_id: str
    categoria_id: str
    titulo: str
    canal: str
    asunto: Optional[str] = None
    contenido_texto: str
    contenido_html: Optional[str] = None
    variables_requeridas: List[str]
    meta_template_id: Optional[str] = None
    creado_por_id: Optional[str] = None
    fecha_creacion: str
    fecha_actualizacion: str
    activo: bool
    categoria: Optional[CategoriaRecursoOut] = None
    adjuntos: List[RecursoAdjuntoOut] = []
    total_envios: int = 0

    @classmethod
    def from_orm_safe(cls, obj, total_envios: int = 0) -> "PlantillaMensajeOut":
        return cls(
            id=str(obj.id),
            sede_id=str(obj.sede_id),
            categoria_id=str(obj.categoria_id),
            titulo=obj.titulo,
            canal=obj.canal.value if hasattr(obj.canal, "value") else str(obj.canal),
            asunto=obj.asunto,
            contenido_texto=obj.contenido_texto,
            contenido_html=getattr(obj, "contenido_html", None),
            variables_requeridas=obj.variables_requeridas or [],
            meta_template_id=obj.meta_template_id,
            creado_por_id=str(obj.creado_por_id) if obj.creado_por_id else None,
            fecha_creacion=obj.fecha_creacion.isoformat(),
            fecha_actualizacion=obj.fecha_actualizacion.isoformat(),
            activo=obj.activo,
            categoria=CategoriaRecursoOut.from_orm_safe(obj.categoria) if obj.categoria else None,
            adjuntos=[RecursoAdjuntoOut.from_orm_safe(a) for a in (obj.adjuntos or []) if a.activo],
            total_envios=total_envios,
        )


# ── Envío / Bitácora ──────────────────────────────────────────────────────────

class EnviarPlantillaPayload(BaseModel):
    destinatario_id: str
    caso_id: Optional[str] = None
    variables: Dict[str, str] = {}


class BitacoraEnvioOut(BaseModel):
    id: UUID
    sede_id: str
    plantilla_id: Optional[str] = None
    caso_id: Optional[str] = None
    enviado_por_id: Optional[str] = None
    destinatario_id: str
    fecha_envio: str
    estado: str
    payload_hidratado: Dict[str, Any]
    log_error: Optional[str] = None
    communication_log_id: Optional[UUID] = None
    external_id: Optional[str] = None
    outcome: Optional[str] = None

    @classmethod
    def from_orm_safe(cls, obj, **extra) -> "BitacoraEnvioOut":
        return cls(
            id=str(obj.id),
            sede_id=str(obj.sede_id),
            plantilla_id=str(obj.plantilla_id) if obj.plantilla_id else None,
            caso_id=str(obj.caso_id) if obj.caso_id else None,
            enviado_por_id=str(obj.enviado_por_id) if obj.enviado_por_id else None,
            destinatario_id=str(obj.destinatario_id),
            fecha_envio=obj.fecha_envio.isoformat(),
            estado=obj.estado.value if hasattr(obj.estado, "value") else str(obj.estado),
            payload_hidratado=obj.payload_hidratado or {},
            log_error=obj.log_error,
            communication_log_id=extra.get("communication_log_id"),
            external_id=extra.get("external_id"),
            outcome=extra.get("outcome"),
        )


# ── Campañas ──────────────────────────────────────────────────────────────────

class CampaignFromPlantillaPayload(BaseModel):
    campaign_name: str
    target_segments: List[str]
    variables_por_persona: Dict[str, Dict[str, str]] = {}
    default_variables: Dict[str, str] = {}
    note: Optional[str] = None


class CampaignResultOut(BaseModel):
    status: str = "success"
    campaign_name: str
    external_id: str
    target_count: int
    delivered_count: int
    failed_count: int
    envio_ids: List[str]


# ── Banco de recursos del sistema ─────────────────────────────────────────────

class ApplySystemTemplatePayload(BaseModel):
    template_id: str


class SystemTemplateOut(BaseModel):
    id: str
    categoria: str
    titulo: str
    canal: str
    asunto: Optional[str] = None
    contenido_texto: str
    contenido_html: Optional[str] = None
    html_template_type: Optional[str] = None
    variables_requeridas: List[str]
    descripcion: Optional[str] = None


class SystemTemplateCatalogOut(BaseModel):
    categorias: List[CategoriaRecursoCreate]
    plantillas: List[SystemTemplateOut]

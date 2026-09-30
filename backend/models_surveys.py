"""CCF Surveys / Encuestas Dinámicas (Google Forms Parity).

Modelos híbridos relacionales + JSON para encuestas dinámicas,
formularios interactivos, recolección de respuestas y analítica.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class EncuestaFormulario(Base):
    __tablename__ = "encuesta_formularios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Axioma 3: Aislamiento Multi-Tenant (NULL = alcance ministerial global/universo)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    slug = Column(String(255), nullable=True, index=True)

    # Configuración de acceso y respuesta
    es_publico = Column(Boolean, default=True, nullable=False)
    requiere_autenticacion = Column(Boolean, default=False, nullable=False)
    limitar_una_respuesta = Column(Boolean, default=False, nullable=False)
    permitir_editar_respuesta = Column(Boolean, default=False, nullable=False)
    mostrar_barra_progreso = Column(Boolean, default=True, nullable=False)
    mensaje_confirmacion = Column(Text, nullable=True)
    redirigir_url = Column(String(500), nullable=True)

    # Ventana de vigencia y límites
    fecha_apertura = Column(DateTime(timezone=True), nullable=True)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    max_respuestas = Column(Integer, nullable=True)
    total_respuestas = Column(Integer, default=0, nullable=False)

    # Ciclo de vida: BORRADOR, PUBLICADO, CERRADO, ARCHIVADO
    estado = Column(String(50), default="BORRADOR", nullable=False, index=True)

    # Personalización visual: banner, colores, fuente, logo
    config_visual = Column(JSON, default=dict, nullable=False)

    # Ajustes avanzados (notificaciones por email, webhook, etc.)
    ajustes = Column(JSON, default=dict, nullable=False)

    # Auditoría y ciclo de vida (Axioma 1: Kernel de Personas)
    creado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    preguntas = relationship(
        "EncuestaPregunta",
        back_populates="formulario",
        cascade="all, delete-orphan",
        order_by="EncuestaPregunta.orden",
    )
    respuestas_envios = relationship(
        "EncuestaRespuestaEnvio",
        back_populates="formulario",
        cascade="all, delete-orphan",
    )


class EncuestaPregunta(Base):
    __tablename__ = "encuesta_preguntas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formulario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encuesta_formularios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    titulo = Column(Text, nullable=False)
    descripcion = Column(Text, nullable=True)

    # 11 tipos canónicos + SECCION_SALTO:
    # TEXTO_CORTO, PARRAFO, OPCION_MULTIPLE, CASILLAS, DESPLEGABLE,
    # ESCALA_LINEAL, CUADRICULA_RADIO, CUADRICULA_CASILLAS, FECHA, HORA,
    # SUBIR_ARCHIVO, SECCION_SALTO
    tipo_pregunta = Column(String(50), nullable=False)
    orden = Column(Integer, default=0, nullable=False, index=True)
    es_requerida = Column(Boolean, default=False, nullable=False)

    # Estructura de opciones y cuadrículas
    opciones = Column(JSON, default=list, nullable=False)  # [{"id": "1", "label": "Opción 1", "salto_seccion": null}]
    filas = Column(JSON, default=list, nullable=False)  # Para matrices / cuadrículas
    columnas = Column(JSON, default=list, nullable=False)  # Para matrices / cuadrículas

    # Escala lineal
    escala_min = Column(Integer, default=1, nullable=False)
    escala_max = Column(Integer, default=5, nullable=False)
    escala_min_etiqueta = Column(String(100), nullable=True)
    escala_max_etiqueta = Column(String(100), nullable=True)

    # Subida de archivo
    archivo_tipos_permitidos = Column(JSON, default=list, nullable=False)  # ["image/*", "application/pdf"]
    archivo_max_mb = Column(Integer, default=10, nullable=False)
    archivo_max_archivos = Column(Integer, default=1, nullable=False)

    # Validaciones y saltos condicionales
    configuracion = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relaciones
    formulario = relationship("EncuestaFormulario", back_populates="preguntas")
    respuestas_detalles = relationship(
        "EncuestaRespuestaDetalle",
        back_populates="pregunta",
        cascade="all, delete-orphan",
    )


class EncuestaRespuestaEnvio(Base):
    __tablename__ = "encuesta_respuestas_envios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formulario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encuesta_formularios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Axioma 1: Kernel de Personas (Single Source of Truth)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True, index=True)

    ip_hash = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    email_respondente = Column(String(255), nullable=True, index=True)
    nombre_respondente = Column(String(255), nullable=True)

    # Metadatos del envío (duración, dispositivo, referer)
    metadatos = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relaciones
    formulario = relationship("EncuestaFormulario", back_populates="respuestas_envios")
    detalles = relationship(
        "EncuestaRespuestaDetalle",
        back_populates="envio",
        cascade="all, delete-orphan",
    )


class EncuestaRespuestaDetalle(Base):
    __tablename__ = "encuesta_respuestas_detalles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encuesta_respuestas_envios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pregunta_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encuesta_preguntas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Columnas tipadas para indexación / consultas rápidas + JSON para compuestas
    valor_texto = Column(Text, nullable=True)
    valor_numero = Column(Float, nullable=True)
    valor_fecha = Column(Date, nullable=True)
    valor_hora = Column(String(10), nullable=True)
    valor_json = Column(JSON, nullable=True)  # Casillas, cuadrículas, lista de archivos subidos

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relaciones
    envio = relationship("EncuestaRespuestaEnvio", back_populates="detalles")
    pregunta = relationship("EncuestaPregunta", back_populates="respuestas_detalles")

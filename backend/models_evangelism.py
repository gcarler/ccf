"""Módulo de Evangelismo — Schema canónico definitivo.

Tablas: sedes, categorias_estrategia, motivos_excusa, logs_auditoria,
        estrategias_evangelismo, estrategia_roles_personalizados,
        grupos_evangelismo, grupo_participantes, sesiones_grupo,
        asistencias, registros_seguimiento, historial_embudo.
"""
from __future__ import annotations

import enum
import uuid
import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, DDL, event,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base
from backend.models_shared import _utcnow


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────

class RolEnGrupoEnum(str, enum.Enum):
    LIDER = "LIDER"
    COLIDER = "COLIDER"
    ANFITRION = "ANFITRION"
    ASISTENTE = "ASISTENTE"
    INVITADO = "INVITADO"
    PERSONALIZADO = "PERSONALIZADO"


class EstadoAsistenciaEnum(str, enum.Enum):
    ASISTIO = "ASISTIO"
    FALTO = "FALTO"
    EXCUSA = "EXCUSA"


class TipoSeguimientoEnum(str, enum.Enum):
    LLAMADA = "LLAMADA"
    MENSAJE = "MENSAJE_WHATSAPP"
    VISITA_PRESENCIAL = "VISITA_PRESENCIAL"
    ORACION = "ORACION"


class FrecuenciaEnum(str, enum.Enum):
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"
    EVENTO_UNICO = "EVENTO_UNICO"


class EstadoSesionEnum(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"


# ──────────────────────────────────────────────
# MULTI-TENANT
# ──────────────────────────────────────────────

class Sede(Base):
    __tablename__ = "sedes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(150), nullable=False)
    ciudad = Column(String(100), nullable=False)
    es_activa = Column(Boolean, default=True)


# ──────────────────────────────────────────────
# AUDITORÍA
# ──────────────────────────────────────────────

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tabla_afectada = Column(String(100), nullable=False)
    registro_id = Column(String(100), nullable=False)
    accion = Column(String(20), nullable=False)
    detalles_cambio = Column(JSONB, nullable=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    fecha_accion = Column(DateTime, default=_utcnow)


# ──────────────────────────────────────────────
# CONFIGURACIÓN DINÁMICA
# ──────────────────────────────────────────────

class CategoriaEstrategia(Base):
    __tablename__ = "categorias_estrategia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=True)
    es_del_sistema = Column(Boolean, default=False)
    activa = Column(Boolean, default=True)


class MotivoExcusa(Base):
    __tablename__ = "motivos_excusa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    descripcion = Column(String(200), nullable=False, unique=True)
    es_del_sistema = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)


# ──────────────────────────────────────────────
# CORE EVANGELISMO
# ──────────────────────────────────────────────

class EstrategiaEvangelismo(Base):
    __tablename__ = "estrategias_evangelismo"

    id = Column(String(50), primary_key=True)
    nombre = Column(String(200), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias_estrategia.id"), nullable=False)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=_utcnow)
    frecuencia = Column(String(20), nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    activa = Column(Boolean, default=True)

    categoria = relationship("CategoriaEstrategia")
    sede = relationship("Sede")
    grupos = relationship("GrupoEvangelismo", back_populates="estrategia", cascade="all, delete-orphan")
    roles_personalizados = relationship("RolPersonalizadoEstrategia", back_populates="estrategia")


class RolPersonalizadoEstrategia(Base):
    __tablename__ = "estrategia_roles_personalizados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estrategia_id = Column(String(50), ForeignKey("estrategias_evangelismo.id", ondelete="CASCADE"), nullable=False)
    nombre_rol = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)

    estrategia = relationship("EstrategiaEvangelismo", back_populates="roles_personalizados")


class GrupoEvangelismo(Base):
    __tablename__ = "grupos_evangelismo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estrategia_id = Column(String(50), ForeignKey("estrategias_evangelismo.id", ondelete="CASCADE"), nullable=False)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    ubicacion = Column(String(255), nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    dia_reunion = Column(String(20), nullable=True)
    hora_reunion = Column(String(10), nullable=True)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    estrategia = relationship("EstrategiaEvangelismo", back_populates="grupos")
    sede = relationship("Sede")
    participantes = relationship("ParticipanteGrupo", back_populates="grupo", cascade="all, delete-orphan")
    sesiones = relationship("SesionGrupo", back_populates="grupo", cascade="all, delete-orphan")


# ──────────────────────────────────────────────
# PARTICIPANTES, SESIONES Y ASISTENCIA
# ──────────────────────────────────────────────

class ParticipanteGrupo(Base):
    __tablename__ = "grupo_participantes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(Integer, ForeignKey("grupos_evangelismo.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    rol_base = Column(String(20), nullable=False)
    rol_personalizado_id = Column(Integer, ForeignKey("estrategia_roles_personalizados.id", ondelete="SET NULL"), nullable=True)
    fecha_ingreso = Column(DateTime, default=_utcnow)
    activo = Column(Boolean, default=True)

    grupo = relationship("GrupoEvangelismo", back_populates="participantes")
    persona = relationship("Persona", back_populates="participaciones_grupo")
    rol_personalizado = relationship("RolPersonalizadoEstrategia")


class SesionGrupo(Base):
    __tablename__ = "sesiones_grupo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(Integer, ForeignKey("grupos_evangelismo.id", ondelete="CASCADE"), nullable=False)
    fecha_sesion = Column(DateTime, nullable=False)
    estado = Column(String(20), default=EstadoSesionEnum.PENDIENTE.value, nullable=False)
    motivo_cancelacion = Column(String(255), nullable=True)
    tema_estudio = Column(String(200), nullable=True)
    notas_lider = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    grupo = relationship("GrupoEvangelismo", back_populates="sesiones")
    asistencias = relationship("Asistencia", back_populates="sesion", cascade="all, delete-orphan")


class Asistencia(Base):
    __tablename__ = "asistencias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sesion_id = Column(Integer, ForeignKey("sesiones_grupo.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    estado = Column(String(20), nullable=False)
    motivo_excusa_id = Column(Integer, ForeignKey("motivos_excusa.id", ondelete="SET NULL"), nullable=True)
    detalle_excusa = Column(String(255), nullable=True)
    es_primera_vez = Column(Boolean, default=False)
    requiere_seguimiento = Column(Boolean, default=False)

    sesion = relationship("SesionGrupo", back_populates="asistencias")
    persona = relationship("Persona", back_populates="asistencias")
    motivo_excusa = relationship("MotivoExcusa")
    seguimientos = relationship("RegistroSeguimiento", back_populates="asistencia", cascade="all, delete-orphan")


class RegistroSeguimiento(Base):
    __tablename__ = "registros_seguimiento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asistencia_id = Column(Integer, ForeignKey("asistencias.id", ondelete="CASCADE"), nullable=False)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    fecha_seguimiento = Column(DateTime, default=_utcnow, nullable=False)
    tipo = Column(String(30), nullable=False)
    observaciones = Column(Text, nullable=True)
    estado_completado = Column(Boolean, default=True)

    asistencia = relationship("Asistencia", back_populates="seguimientos")
    responsable = relationship("Persona", foreign_keys=[responsable_id], back_populates="seguimientos_realizados")


# ──────────────────────────────────────────────
# HISTORIAL DE EMBUDO (VELOCIDAD MINISTERIAL)
# ──────────────────────────────────────────────

class HistorialEmbudo(Base):
    __tablename__ = "historial_embudo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    rol_anterior = Column(String(100), nullable=True)
    rol_nuevo = Column(String(100), nullable=False)
    fecha_cambio = Column(DateTime, default=_utcnow)
    dias_en_estado_anterior = Column(Integer, nullable=True)

    persona = relationship("Persona", back_populates="historial_embudo")

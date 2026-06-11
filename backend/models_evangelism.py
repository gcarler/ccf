"""Módulo de Evangelismo — Schema canónico definitivo.

Tablas: sedes, categorias_estrategia, motivos_excusa, logs_auditoria,
        estrategias_evangelismo, estrategia_roles_personalizados,
        grupos_evangelismo, grupo_participantes, sesiones_grupo,
        asistencias, registros_seguimiento, historial_embudo.
"""
from __future__ import annotations

import enum
import uuid as _uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, JSON, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, synonym

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
    BIMENSUAL = "BIMENSUAL"
    TRIMESTRAL = "TRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"
    EVENTO_UNICO = "EVENTO_UNICO"


class EstadoSesionEnum(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"

class HabilitacionSesionEnum(str, enum.Enum):
    DESHABILITADO = "DESHABILITADO"
    HABILITADO = "HABILITADO"
    CERRADO = "CERRADO"
    CANCELADA = "CANCELADA"


# ──────────────────────────────────────────────
# MULTI-TENANT
# ──────────────────────────────────────────────

class Sede(Base):
    __tablename__ = "sedes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    nombre = Column(String(150), nullable=False)
    ciudad = Column(String(100), nullable=False)
    es_activa = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


# ──────────────────────────────────────────────
# AUDITORÍA
# ──────────────────────────────────────────────

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tabla_afectada = Column(String(100), nullable=False)
    registro_id = Column(String(100), nullable=False)
    accion = Column(String(20), nullable=False)
    detalles_cambio = Column(JSON, nullable=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    fecha_accion = Column(DateTime(timezone=True), default=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


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
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class MotivoExcusa(Base):
    __tablename__ = "motivos_excusa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    descripcion = Column(String(200), nullable=False, unique=True)
    es_del_sistema = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    activo = Column(Boolean, default=True)


# ──────────────────────────────────────────────
# CORE EVANGELISMO
# ──────────────────────────────────────────────

class EstrategiaEvangelismo(Base):
    __tablename__ = "estrategias_evangelismo"

    id = Column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    codigo = Column(String(20), unique=True, nullable=True, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    clase_raiz = Column(String(50), nullable=True, index=True)
    activa = Column(Boolean, default=True, index=True)

    # Tipología
    typology = Column(String(50), nullable=True, index=True)  # relacional | evento_masivo | sectorial

    # Relacional
    frecuencia = Column(String(20), nullable=True)
    dia_reunion = Column(String(20), nullable=True)
    hora_reunion = Column(String(10), nullable=True)

    # Evento Masivo
    event_format = Column(String(30), nullable=True)  # UNICA_LOCACION | MULTILOCACION
    phases = Column(JSON, nullable=True)

    # Sectorial
    niche_objective = Column(String(255), nullable=True)

    # General
    strategy_type = Column(String(100), nullable=True)
    status = Column(String(50), default="active")
    default_role_id = Column(Integer, ForeignKey("estrategia_roles_personalizados.id", ondelete="SET NULL"), nullable=True)

    # Fechas
    fecha_inicio = Column(DateTime(timezone=True), nullable=True)
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # FKs
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias_estrategia.id"), nullable=False)

    # Relaciones
    categoria = relationship("CategoriaEstrategia")
    sede = relationship("Sede")
    grupos = relationship("GrupoEvangelismo", back_populates="estrategia", cascade="all, delete-orphan")
    roles_personalizados = relationship(
        "RolPersonalizadoEstrategia",
        back_populates="estrategia",
        foreign_keys="RolPersonalizadoEstrategia.estrategia_id",
    )
    default_role = relationship(
        "RolPersonalizadoEstrategia",
        foreign_keys=[default_role_id],
        uselist=False,
    )

    # English aliases for backward compatibility
    name = synonym("nombre")
    description = synonym("descripcion")
    start_date = synonym("fecha_inicio")
    end_date = synonym("fecha_fin")
    day_of_week = synonym("dia_reunion")
    start_time = synonym("hora_reunion")
    recurrence = synonym("frecuencia")
    created_at = synonym("fecha_creacion")


class RolPersonalizadoEstrategia(Base):
    __tablename__ = "estrategia_roles_personalizados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estrategia_id = Column(String(36), ForeignKey("estrategias_evangelismo.id", ondelete="CASCADE"), nullable=True, index=True)
    nombre_rol = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    estrategia = relationship(
        "EstrategiaEvangelismo",
        back_populates="roles_personalizados",
        foreign_keys=[estrategia_id],
    )

    deleted_at = Column(DateTime(timezone=True), nullable=True)


class GrupoEvangelismo(Base):
    __tablename__ = "grupos_evangelismo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estrategia_id = Column(String(36), ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False)
    codigo = Column(String(30), unique=True, nullable=True, index=True)
    nombre = Column(String(150), nullable=False)
    ubicacion = Column(String(255), nullable=True)
    direccion = Column(String(255), nullable=True)
    capacidad = Column(Integer, default=15)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    dia_reunion = Column(String(20), nullable=True)
    hora_reunion = Column(String(10), nullable=True)
    activo = Column(Boolean, default=True)
    lider_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    asistente_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    anfitrion_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    parent_group_id = Column(Integer, ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True)
    notes_historial = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    parent_group = relationship("GrupoEvangelismo", remote_side=[id], backref="child_groups")
    estrategia = relationship("EstrategiaEvangelismo", back_populates="grupos")
    sede = relationship("Sede")
    lider = relationship("Persona", foreign_keys=[lider_persona_id])
    asistente = relationship("Persona", foreign_keys=[asistente_persona_id])
    anfitrion = relationship("Persona", foreign_keys=[anfitrion_persona_id])
    participantes = relationship("ParticipanteGrupo", back_populates="grupo", cascade="all, delete-orphan")
    sesiones = relationship("SesionGrupo", back_populates="grupo", cascade="all, delete-orphan")

    # English aliases used throughout the API layer
    code = synonym("codigo")
    name = synonym("nombre")
    zone = synonym("ubicacion")
    address = synonym("direccion")
    capacity = synonym("capacidad")
    latitude = synonym("latitud")
    longitude = synonym("longitud")
    day_of_week = synonym("dia_reunion")
    start_time = synonym("hora_reunion")
    leader_id = synonym("lider_persona_id")
    assistant_id = synonym("asistente_persona_id")
    host_id = synonym("anfitrion_persona_id")
    leader_persona_id = synonym("lider_persona_id")
    assistant_persona_id = synonym("asistente_persona_id")
    host_persona_id = synonym("anfitrion_persona_id")
    # evangelism_strategy_id es columna directa (antes era synonym de estrategia_id legacy)

    @hybrid_property
    def status(self):
        return "active" if self.activo else "inactive"

    @status.setter
    def status(self, val):
        self.activo = val in ("active", "Activo", True)

    @hybrid_property
    def leader_name(self):
        val = getattr(self, '_leader_name', None)
        if not val and self.lider is not None:
            return f"{self.lider.first_name} {self.lider.last_name}"
        return val

    @leader_name.setter
    def leader_name(self, val):
        self._leader_name = val

    @hybrid_property
    def members_count(self):
        return len(self.participantes) if self.participantes is not None else 0

    @members_count.setter
    def members_count(self, val):
        self._members_count = val

    @hybrid_property
    def end_time(self):
        return getattr(self, "_end_time", None)

    @end_time.setter
    def end_time(self, val):
        self._end_time = val

    def __init__(self, **kwargs):
        leader_name = kwargs.pop("leader_name", None)
        members_count = kwargs.pop("members_count", None)
        end_time = kwargs.pop("end_time", None)
        if "evangelism_strategy_id" in kwargs and "estrategia_id" not in kwargs:
            kwargs["estrategia_id"] = kwargs.pop("evangelism_strategy_id")
        super().__init__(**kwargs)
        if leader_name is not None:
            self._leader_name = leader_name
        if members_count is not None:
            self._members_count = members_count
        if end_time is not None:
            self._end_time = end_time


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
    fecha_ingreso = Column(DateTime(timezone=True), default=_utcnow)
    activo = Column(Boolean, default=True)

    grupo = relationship("GrupoEvangelismo", back_populates="participantes")
    persona = relationship("Persona", back_populates="participaciones_grupo")
    rol_personalizado = relationship("RolPersonalizadoEstrategia")

    # English aliases
    role = synonym("rol_base")
    cell_group_id = synonym("grupo_id")
    cell_group = synonym("grupo")
    member_id = synonym("persona_id")

    deleted_at = Column(DateTime(timezone=True), nullable=True)

class SesionGrupo(Base):
    __tablename__ = "sesiones_grupo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(Integer, ForeignKey("grupos_evangelismo.id", ondelete="CASCADE"), nullable=False)
    fecha_sesion = Column(DateTime(timezone=True), nullable=False)
    estado = Column(String(20), default=EstadoSesionEnum.PENDIENTE.value, nullable=False)
    estado_habilitacion = Column(String(20), default=HabilitacionSesionEnum.DESHABILITADO.value, nullable=False)
    habilitado_por = Column(UUID(as_uuid=True), nullable=True)
    habilitado_en = Column(DateTime(timezone=True), nullable=True)
    motivo_cancelacion = Column(String(255), nullable=True)
    tema_estudio = Column(String(200), nullable=True)
    notas_lider = Column(Text, nullable=True)
    offering_amount = Column(Numeric(12, 2), nullable=True)
    season_id = Column(Integer, ForeignKey("campaign_seasons.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    grupo = relationship("GrupoEvangelismo", back_populates="sesiones")
    asistencias = relationship("Asistencia", back_populates="sesion", cascade="all, delete-orphan")

    cell_group_id = synonym("grupo_id")
    cell_group = synonym("grupo")
    session_date = synonym("fecha_sesion")
    status = synonym("estado")
    topic = synonym("tema_estudio")
    cancellation_reason = synonym("motivo_cancelacion")
    report_notes = synonym("notas_lider")

    @property
    def season(self):
        return None

    @property
    def novelty_type(self):
        return getattr(self, '_novelty_type', None)

    @novelty_type.setter
    def novelty_type(self, value):
        self._novelty_type = value

    @property
    def novelty_detail(self):
        return getattr(self, '_novelty_detail', None)

    @novelty_detail.setter
    def novelty_detail(self, value):
        self._novelty_detail = value

    @property
    def reported_by_persona_id(self):
        return getattr(self, '_reported_by_persona_id', None)

    @reported_by_persona_id.setter
    def reported_by_persona_id(self, value):
        self._reported_by_persona_id = value

    @property
    def reported_at(self):
        return None

    @reported_at.setter
    def reported_at(self, value):
        pass

    @property
    def report_deadline(self):
        return getattr(self, "_report_deadline", None)

    @report_deadline.setter
    def report_deadline(self, value):
        self._report_deadline = value

    def __init__(self, **kwargs):
        offering_amount = kwargs.pop("offering_amount", None)
        kwargs.pop("reported_by_persona_id", None)
        kwargs.pop("reported_at", None)
        kwargs.pop("novelty_type", None)
        kwargs.pop("novelty_detail", None)
        report_deadline = kwargs.pop("report_deadline", None)
        super().__init__(**kwargs)
        if offering_amount is not None:
            self._offering_amount = offering_amount
        if report_deadline is not None:
            self._report_deadline = report_deadline


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
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # English aliases for legacy support
    session_id = synonym("sesion_id")
    member_id = synonym("persona_id")
    absence_reason = synonym("motivo_excusa_id")
    absence_reason_detail = synonym("detalle_excusa")

    @property
    def attended(self):
        return str(self.estado).strip().lower() in {
            "asistio",
            "presente",
            "present",
            "primera_vez",
            "first_time",
        }

    @attended.setter
    def attended(self, value):
        self.estado = "Presente" if value else "Ausente"

    sesion = relationship("SesionGrupo", back_populates="asistencias")
    persona = relationship("Persona", back_populates="asistencias")
    motivo_excusa = relationship("MotivoExcusa")
    seguimientos = relationship("RegistroSeguimiento", back_populates="asistencia", cascade="all, delete-orphan")


class RegistroSeguimiento(Base):
    __tablename__ = "registros_seguimiento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asistencia_id = Column(Integer, ForeignKey("asistencias.id", ondelete="CASCADE"), nullable=False)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    fecha_seguimiento = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    tipo = Column(String(30), nullable=False)
    observaciones = Column(Text, nullable=True)
    estado_completado = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

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
    fecha_cambio = Column(DateTime(timezone=True), default=_utcnow)
    dias_en_estado_anterior = Column(Integer, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    persona = relationship("Persona", back_populates="historial_embudo")

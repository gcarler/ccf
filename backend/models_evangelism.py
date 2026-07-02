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
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, synonym

from backend.core.database import Base
from backend.models_shared import _utcnow


class CampaignSeason(Base):
    __tablename__ = "campaign_seasons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    periodicity = Column(String(20), default="SEMANAL", nullable=False)
    status = Column(String(20), default="Activa", index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


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

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=True)
    es_del_sistema = Column(Boolean, default=False)
    activa = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class MotivoExcusa(Base):
    __tablename__ = "motivos_excusa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    descripcion = Column(String(200), nullable=False, unique=True)
    es_del_sistema = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    activo = Column(Boolean, default=True)


# ──────────────────────────────────────────────
# CORE EVANGELISMO
# ──────────────────────────────────────────────

class EstrategiaEvangelismo(Base):
    __tablename__ = "estrategias_evangelismo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
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
    default_role_id = Column(UUID(as_uuid=True), ForeignKey("estrategia_roles_personalizados.id", ondelete="SET NULL"), nullable=True)

    # Fechas
    fecha_inicio = Column(DateTime(timezone=True), nullable=True)
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # FKs
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False)
    categoria_id = Column(UUID(as_uuid=True), ForeignKey("categorias_estrategia.id"), nullable=False)

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

    # API field names
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    estrategia_id = Column(UUID(as_uuid=True), ForeignKey("estrategias_evangelismo.id", ondelete="CASCADE"), nullable=True, index=True)
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    estrategia_id = Column(UUID(as_uuid=True), ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True)
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
    parent_group_id = Column(UUID(as_uuid=True), ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True)
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
    # evangelism_strategy_id es columna directa.

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
    def personas_count(self):
        if self.participantes is None:
            return 0
        return sum(1 for p in self.participantes if p.activo and p.deleted_at is None)

    @personas_count.setter
    def personas_count(self, val):
        self._personas_count = val

    @hybrid_property
    def end_time(self):
        return getattr(self, "_end_time", None)

    @end_time.setter
    def end_time(self, val):
        self._end_time = val

    def __init__(self, **kwargs):
        leader_name = kwargs.pop("leader_name", None)
        personas_count = kwargs.pop("personas_count", None)
        end_time = kwargs.pop("end_time", None)
        if "evangelism_strategy_id" in kwargs and "estrategia_id" not in kwargs:
            kwargs["estrategia_id"] = kwargs.pop("evangelism_strategy_id")
        super().__init__(**kwargs)
        if leader_name is not None:
            self._leader_name = leader_name
        if personas_count is not None:
            self._personas_count = personas_count
        if end_time is not None:
            self._end_time = end_time


# ──────────────────────────────────────────────
# PARTICIPANTES, SESIONES Y ASISTENCIA
# ──────────────────────────────────────────────

class ParticipanteGrupo(Base):
    __tablename__ = "grupo_participantes"
    __table_args__ = (
        UniqueConstraint("grupo_id", "persona_id", name="uq_participante_grupo_persona"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    grupo_id = Column(UUID(as_uuid=True), ForeignKey("grupos_evangelismo.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    rol_base = Column(String(20), nullable=False)
    rol_personalizado_id = Column(UUID(as_uuid=True), ForeignKey("estrategia_roles_personalizados.id", ondelete="SET NULL"), nullable=True)
    fecha_ingreso = Column(DateTime(timezone=True), default=_utcnow)
    activo = Column(Boolean, default=True)

    grupo = relationship("GrupoEvangelismo", back_populates="participantes")
    persona = relationship("Persona", back_populates="participaciones_grupo")
    rol_personalizado = relationship("RolPersonalizadoEstrategia")

    role = synonym("rol_base")

    deleted_at = Column(DateTime(timezone=True), nullable=True)

class SesionGrupo(Base):
    __tablename__ = "sesiones_grupo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    grupo_id = Column(UUID(as_uuid=True), ForeignKey("grupos_evangelismo.id", ondelete="CASCADE"), nullable=False)
    fecha_sesion = Column(DateTime(timezone=True), nullable=False)
    estado = Column(String(20), default=EstadoSesionEnum.PENDIENTE.value, nullable=False)
    estado_habilitacion = Column(String(20), default=HabilitacionSesionEnum.DESHABILITADO.value, nullable=False)
    habilitado_por = Column(UUID(as_uuid=True), nullable=True)
    habilitado_en = Column(DateTime(timezone=True), nullable=True)
    motivo_cancelacion = Column(String(255), nullable=True)
    tema_estudio = Column(String(200), nullable=True)
    notas_lider = Column(Text, nullable=True)
    offering_amount = Column(Numeric(12, 2), nullable=True)
    season_id = Column(UUID(as_uuid=True), ForeignKey("campaign_seasons.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    # Marca de tiempo de cuando se reportó la asistencia por última vez.
    # Antes era un ``@property`` Python con setter stub (``pass``)
    # que retornaba ``None`` — fix en Sprint 3 vía migración
    # ``20260702_reported_at_tz``: ahora es columna real.
    reported_at = Column(DateTime(timezone=True), nullable=True)

    grupo = relationship("GrupoEvangelismo", back_populates="sesiones")
    asistencias = relationship("Asistencia", back_populates="sesion", cascade="all, delete-orphan")

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

    # ``reported_at`` ya NO es ``@property`` stub: es columna real
    # ``Column(DateTime(timezone=True), nullable=True)``. El fix en
    # ``20260702_reported_at_tz`` cierra el bug por el cual los
    # endpoints siempre emitían ``null`` aunque el handler seteara
    # el timestamp con ``_datetime.now(_timezone.utc)``.

    @property
    def report_deadline(self):
        return getattr(self, "_report_deadline", None)

    @report_deadline.setter
    def report_deadline(self, value):
        self._report_deadline = value

    def __init__(self, **kwargs):
        kwargs.pop("reported_by_persona_id", None)
        # ``reported_at`` y ``offering_amount`` son columnas reales (``Column``)
        # y deben llegar a ``super().__init__`` para que SQLAlchemy las persista.
        # Antes ambos eran ``kwargs.pop``+@property-stub:
        #   * reported_at: fix Sprint 3 vía columna real + migración
        #     ``20260702_reported_at_tz``.
        #   * offering_amount: idéntico anti-pattern — el pop descartaba el valor
        #     y se asignaba a un ``_offering_amount`` privado que NUNCA se leía.
        #     Si el caller hacía ``SesionGrupo(offering_amount=N, ...)`` la
        #     ``Column(Numeric(12, 2))`` quedaba en NULL y todos los readers
        #     (``evangelism_analytics`` sums, ``get_grupo``, weekly aggregates)
        #     devolvían None/0. Fix Sprint 3.5: dejar fluir a la columna.
        # Los atributos virtuales restantes (``novelty_type``/``detail`` y
        # ``report_deadline``) sí son campos computados via @property + setter.
        kwargs.pop("novelty_type", None)
        kwargs.pop("novelty_detail", None)
        report_deadline = kwargs.pop("report_deadline", None)
        super().__init__(**kwargs)
        if report_deadline is not None:
            self._report_deadline = report_deadline


class Asistencia(Base):
    __tablename__ = "asistencias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sesion_id = Column(UUID(as_uuid=True), ForeignKey("sesiones_grupo.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    estado = Column(String(20), nullable=False)
    motivo_excusa_id = Column(UUID(as_uuid=True), ForeignKey("motivos_excusa.id", ondelete="SET NULL"), nullable=True)
    detalle_excusa = Column(String(255), nullable=True)
    es_primera_vez = Column(Boolean, default=False)
    requiere_seguimiento = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # API field names
    absence_reason = synonym("motivo_excusa_id")
    absence_reason_detail = synonym("detalle_excusa")
    notes = synonym("detalle_excusa")

    @property
    def status(self):
        # Determine the lowercase, normalized status string for frontend rendering.
        est = str(self.estado).strip().lower()
        if self.es_primera_vez or est in {"primera_vez", "first_time"}:
            return "first_time"
        if est in {"falto", "ausente", "absent"}:
            return "absent"
        if est in {"excusa", "excused"}:
            return "excused"
        if est in {"presente", "present", "asistio"}:
            return "present"
        return est

    @status.setter
    def status(self, value):
        val = str(value).strip().lower()
        if val == "absent":
            self.estado = "FALTO"
            self.es_primera_vez = False
        elif val == "first_time":
            self.estado = "primera_vez"
            self.es_primera_vez = True
        elif val == "excused":
            self.estado = "EXCUSA"
            self.es_primera_vez = False
        else:
            self.estado = "Presente"
            self.es_primera_vez = False

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    asistencia_id = Column(UUID(as_uuid=True), ForeignKey("asistencias.id", ondelete="CASCADE"), nullable=False)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    fecha_seguimiento = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    created_at = synonym("fecha_creacion")
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    rol_anterior = Column(String(100), nullable=True)
    rol_nuevo = Column(String(100), nullable=False)
    fecha_cambio = Column(DateTime(timezone=True), default=_utcnow)
    dias_en_estado_anterior = Column(Integer, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    persona = relationship("Persona", back_populates="historial_embudo")

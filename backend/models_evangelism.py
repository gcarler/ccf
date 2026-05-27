"""Modelos del módulo de Evangelismo — Enums, nuevas tablas.

Los modelos existentes (EvangelismStrategy, GloryHouse, etc.) se modifican
in-place en models_academy.py y models_crm.py para evitar conflictos de
mapeo SQLAlchemy. Este archivo contiene solo enums y tablas completamente nuevas.
"""

from __future__ import annotations

import enum
import datetime as dt

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import backref, relationship

from backend.core.database import Base
from backend.models_shared import _utcnow


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────

class ClaseEstrategiaEnum(str, enum.Enum):
    """Clasificación raíz de una estrategia de evangelismo."""
    RELACIONAL = "relacional"
    EVENTO_MASIVO = "evento_masivo"
    SECTORIAL = "sectorial"


class RolEnGrupoEnum(str, enum.Enum):
    """Roles base dentro de un grupo de evangelismo."""
    LIDER = "lider"
    COLIDER = "colider"
    MIEMBRO = "miembro"
    VISITANTE = "visitante"


class EstadoAsistenciaEnum(str, enum.Enum):
    """Estado de asistencia a una sesión."""
    PRESENTE = "presente"
    AUSENTE = "ausente"
    PRIMERA_VEZ = "primera_vez"


class TipoSeguimientoEnum(str, enum.Enum):
    """Tipo de seguimiento posterior a una asistencia."""
    LLAMADA = "llamada"
    VISITA = "visita"
    ORACION = "oracion"
    MENSAJE = "mensaje"
    CITA = "cita"


# ──────────────────────────────────────────────
# TABLAS NUEVAS
# ──────────────────────────────────────────────

class RolPersonalizadoEstrategia(Base):
    """Roles personalizados que una estrategia puede definir además de los roles base.

    Ej: una estrategia sectorial podría tener roles como "Coordinador de zona",
    "Encuestador", "Logística", etc.
    """

    __tablename__ = "roles_personalizados_estrategia"

    id = Column(Integer, primary_key=True, index=True)
    estrategia_id = Column(
        String(20),
        ForeignKey("evangelism_strategies.codigo", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    # No backref aquí — la relación se define desde EstrategiaEvangelismo


class RegistroSeguimiento(Base):
    """Registro de seguimiento individual asociado a una asistencia.

    Permite trackear llamadas, visitas, oraciones, mensajes o citas
    que se realizan como follow-up después de una sesión.
    """

    __tablename__ = "registros_seguimiento"

    id = Column(Integer, primary_key=True, index=True)
    asistencia_id = Column(
        Integer,
        ForeignKey("glory_house_attendance.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(20), nullable=False, index=True)  # TipoSeguimientoEnum values
    fecha_programada = Column(DateTime, nullable=True, index=True)
    fecha_realizada = Column(DateTime, nullable=True)
    realizado_por_member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notas = Column(Text, nullable=True)
    completado = Column(Boolean, default=False, index=True)
    resultado = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    asistencia = relationship("GloryHouseAttendance", back_populates="seguimientos")
    realizado_por = relationship("Member", foreign_keys=[realizado_por_member_id])

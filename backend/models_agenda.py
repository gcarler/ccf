"""Agenda / Calendario Unificado — Recursos, Eventos, Participantes, Reservas.

Bus de eventos polimórfico con recurrencia RFC 5545, recordatorios,
timezone-aware, soft-delete forense, y control de colisiones de recursos.
"""
import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow_tz():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════
# RECURSOS FÍSICOS
# ═══════════════════════════════════════════════════════════════════

class RecursoFisico(Base):
    __tablename__ = "agenda_recursos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)
    capacidad_maxima = Column(Integer, nullable=True)
    activo = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


# ═══════════════════════════════════════════════════════════════════
# BUS UNIFICADO DE EVENTOS
# ═══════════════════════════════════════════════════════════════════

class EventoAgenda(Base):
    __tablename__ = "agenda_eventos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False)
    modulo_origen = Column(String(50), nullable=False, default="MANUAL")
    entidad_origen_id = Column(String(100), nullable=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_fin = Column(DateTime(timezone=True), nullable=False)
    todo_el_dia = Column(Boolean, default=False)
    regla_recurrencia = Column(String(255), nullable=True)
    fecha_limite_recurrencia = Column(DateTime(timezone=True), nullable=True)
    excepciones_recurrencia = Column(
        JSON().with_variant(ARRAY(String), "postgresql"), default=list
    )
    recordatorios_config = Column(JSON, default=list)
    color_hex = Column(String(10), nullable=True)
    ubicacion_texto = Column(String(255), nullable=True)
    url_conferencia = Column(String(255), nullable=True)
    organizador_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"),
                                    nullable=False)
    visibilidad = Column(String(50), default="PRIVADO")
    estado = Column(String(50), default="ACTIVO")
    created_at = Column(DateTime(timezone=True), default=_utcnow_tz)
    updated_at = Column(DateTime(timezone=True), default=_utcnow_tz,
                        onupdate=_utcnow_tz)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    participantes = relationship("ParticipanteEvento", back_populates="evento",
                                 cascade="all, delete-orphan")
    reservas = relationship("ReservaRecurso", back_populates="evento",
                            cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════════
# PARTICIPANTES
# ═══════════════════════════════════════════════════════════════════

class ParticipanteEvento(Base):
    __tablename__ = "agenda_participantes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    evento_id = Column(UUID(as_uuid=True),
                       ForeignKey("agenda_eventos.id", ondelete="CASCADE"),
                       nullable=False)
    persona_id = Column(UUID(as_uuid=True),
                        ForeignKey("personas.id", ondelete="CASCADE"),
                        nullable=False)
    estado_confirmacion = Column(String(50), default="PENDIENTE")
    es_requerido = Column(Boolean, default=True)
    fecha_confirmacion = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    evento = relationship("EventoAgenda", back_populates="participantes")


# ═══════════════════════════════════════════════════════════════════
# RESERVA DE RECURSOS
# ═══════════════════════════════════════════════════════════════════

class ReservaRecurso(Base):
    __tablename__ = "agenda_reserva_recursos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    evento_id = Column(UUID(as_uuid=True),
                       ForeignKey("agenda_eventos.id", ondelete="CASCADE"),
                       nullable=False)
    recurso_id = Column(UUID(as_uuid=True),
                        ForeignKey("agenda_recursos.id", ondelete="CASCADE"),
                        nullable=False)
    bloqueo_inicio = Column(DateTime(timezone=True), nullable=False)
    bloqueo_fin = Column(DateTime(timezone=True), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    evento = relationship("EventoAgenda", back_populates="reservas")

    # NOTE: Para evitar colisiones en PostgreSQL, ejecutar como DBA:
    # ALTER TABLE agenda_reserva_recursos ADD CONSTRAINT sin_colisiones_fisicas
    # EXCLUDE USING gist (recurso_id WITH =, tstzrange(bloqueo_inicio, bloqueo_fin) WITH &&)
    # WHERE (bloqueo_inicio IS NOT NULL AND bloqueo_fin IS NOT NULL);
    # Requiere: CREATE EXTENSION IF NOT EXISTS btree_gist;

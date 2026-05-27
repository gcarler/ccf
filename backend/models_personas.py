"""Modelo Persona — Entidad canónica de persona en la plataforma.

Persona es el modelo unificado. No todos son miembros formales,
pero todos tienen perfil y pueden participar en grupos de evangelismo.
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import backref, relationship

from backend.core.database import Base
from backend.models_shared import _utcnow


class Persona(Base):
    __tablename__ = "personas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    family_id = Column(
        Integer,
        ForeignKey("families.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sede_id = Column(Integer, ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    # --- Core ---
    nombre_completo = Column(String(300), nullable=False, index=True)
    email = Column(String(200), nullable=True, index=True)
    telefono = Column(String(50), nullable=True, index=True)
    church_role = Column(String(100), nullable=True, index=True)
    estado_vital = Column(String(20), default="ACTIVO", index=True)

    ministerio = Column(String(100), nullable=True)
    rol_iglesia = Column(String(100), nullable=True)
    permiso_plataforma = Column(String(50), nullable=True)

    # --- Datos legacy (demográficos) ---
    datos_extra = Column(JSONB, nullable=True, default=dict)

    # --- Tags y origen (evangelismo) ---
    tags_sistema = Column(ARRAY(String), nullable=True, default=list)
    origen_estrategia_id = Column(
        String(50),
        ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    origen_grupo_id = Column(
        Integer,
        ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    origen_fecha = Column(DateTime, nullable=True)

    # --- Timestamps ---
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", backref=backref("persona_profile", uselist=False))
    family = relationship("Family", back_populates="members")
    sede = relationship("Sede")

    donations = relationship("Donation", back_populates="persona")
    tasks = relationship("CrmTask", back_populates="persona")
    event_attendances = relationship("EventAttendance", back_populates="persona", cascade="all, delete-orphan")
    volunteer_shifts = relationship("VolunteerShift", back_populates="persona", cascade="all, delete-orphan")
    communication_logs = relationship("CommunicationLog", back_populates="persona", cascade="all, delete-orphan")
    positions = relationship("MemberPosition", back_populates="persona", cascade="all, delete-orphan")

    consolidation_cases = relationship(
        "ConsolidationCase",
        foreign_keys="ConsolidationCase.persona_id",
        back_populates="persona",
        cascade="all, delete-orphan",
    )
    consolidated_cases_as_pastor = relationship(
        "ConsolidationCase",
        foreign_keys="ConsolidationCase.assigned_pastor_persona_id",
        back_populates="assigned_pastor",
    )
    consolidated_cases_as_leader = relationship(
        "ConsolidationCase",
        foreign_keys="ConsolidationCase.assigned_leader_persona_id",
        back_populates="assigned_leader",
    )
    consolidation_assignments_sent = relationship(
        "ConsolidationAssignment",
        foreign_keys="ConsolidationAssignment.assigned_by_persona_id",
        back_populates="assigned_by_persona",
    )
    consolidation_assignments_received = relationship(
        "ConsolidationAssignment",
        foreign_keys="ConsolidationAssignment.assigned_to_persona_id",
        back_populates="assigned_to_persona",
    )
    consolidation_interactions = relationship(
        "ConsolidationInteraction",
        foreign_keys="ConsolidationInteraction.performed_by_persona_id",
        back_populates="performed_by_persona",
    )

    # Evangelismo
    participaciones_grupo = relationship("ParticipanteGrupo", back_populates="persona", cascade="all, delete-orphan")
    asistencias = relationship("Asistencia", back_populates="persona", cascade="all, delete-orphan")
    seguimientos_realizados = relationship(
        "RegistroSeguimiento",
        foreign_keys="RegistroSeguimiento.responsable_id",
        back_populates="responsable",
    )
    historial_embudo = relationship("HistorialEmbudo", back_populates="persona", cascade="all, delete-orphan")

    origen_estrategia = relationship("EstrategiaEvangelismo", foreign_keys=[origen_estrategia_id])
    origen_grupo = relationship("GrupoEvangelismo", foreign_keys=[origen_grupo_id])

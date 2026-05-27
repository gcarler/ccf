from __future__ import annotations

import uuid as _uuid

from sqlalchemy import (Boolean, Column, Date, DateTime, Enum, ForeignKey,
                        Integer, Numeric, String, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.models_shared import Base, _utcnow


class Proyecto(Base):
    __tablename__ = "proyectos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    proyecto_padre_id = Column(UUID(as_uuid=True), ForeignKey("proyectos.id"))
    codigo_wbs = Column(String(50), nullable=False, unique=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    estado = Column(Enum("PLANIFICACION", "EN_PROGRESO", "PAUSADO", "COMPLETADO", "CANCELADO",
                         name="estado_proyecto", create_type=False),
                    default="PLANIFICACION")
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin_est = Column(Date, nullable=False)
    fecha_fin_real = Column(Date)
    presupuesto_est = Column(Numeric(12, 2))
    creado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=_utcnow)

    padre = relationship("Proyecto", remote_side="Proyecto.id", backref="subproyectos")
    equipo = relationship("EquipoProyecto", back_populates="proyecto", cascade="all, delete-orphan")
    tareas = relationship("TareaProyecto", back_populates="proyecto", cascade="all, delete-orphan")


class EquipoProyecto(Base):
    __tablename__ = "equipo_proyecto"

    id = Column(Integer, primary_key=True)
    proyecto_id = Column(UUID(as_uuid=True), ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    rol_proyecto = Column(String(50), nullable=False)
    permiso_edicion = Column(Boolean, default=False)
    fecha_asignacion = Column(DateTime, default=_utcnow)
    es_historico = Column(Boolean, default=False)

    proyecto = relationship("Proyecto", back_populates="equipo")


class TareaProyecto(Base):
    __tablename__ = "tareas_proyecto"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    proyecto_id = Column(UUID(as_uuid=True), ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    tarea_padre_id = Column(UUID(as_uuid=True), ForeignKey("tareas_proyecto.id"))
    codigo_wbs = Column(String(50), nullable=False)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    estado = Column(Enum("POR_HACER", "EN_PROGRESO", "EN_REVISION", "COMPLETADO", "BLOQUEADO",
                         name="estado_tarea", create_type=False),
                    default="POR_HACER")
    prioridad = Column(Enum("BAJA", "MEDIA", "ALTA", "URGENTE",
                            name="prioridad_tarea", create_type=False),
                       default="MEDIA")
    asignado_a_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))
    creado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    fecha_vencimiento = Column(DateTime, nullable=False)
    fecha_completado = Column(DateTime)

    proyecto = relationship("Proyecto", back_populates="tareas")
    tarea_padre = relationship("TareaProyecto", remote_side="TareaProyecto.id", backref="subtareas")
    comentarios = relationship("ComentarioTarea", back_populates="tarea", cascade="all, delete-orphan")
    dependencias_bloqueantes = relationship(
        "DependenciaTarea",
        foreign_keys="DependenciaTarea.tarea_bloqueada_id",
        back_populates="tarea_bloqueada",
    )


class DependenciaTarea(Base):
    __tablename__ = "dependencias_tareas"

    tarea_bloqueante_id = Column(UUID(as_uuid=True), ForeignKey("tareas_proyecto.id", ondelete="CASCADE"), primary_key=True)
    tarea_bloqueada_id = Column(UUID(as_uuid=True), ForeignKey("tareas_proyecto.id", ondelete="CASCADE"), primary_key=True)
    tipo_dependencia = Column(Enum("FIN_A_INICIO", "INICIO_A_INICIO", "FIN_A_FIN",
                                   name="tipo_dependencia", create_type=False),
                              default="FIN_A_INICIO")

    tarea_bloqueante = relationship("TareaProyecto", foreign_keys=[tarea_bloqueante_id])
    tarea_bloqueada = relationship("TareaProyecto", foreign_keys=[tarea_bloqueada_id], back_populates="dependencias_bloqueantes")


class ComentarioTarea(Base):
    __tablename__ = "comentarios_tarea"

    id = Column(Integer, primary_key=True)
    tarea_id = Column(UUID(as_uuid=True), ForeignKey("tareas_proyecto.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    comentario = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime, default=_utcnow)

    tarea = relationship("TareaProyecto", back_populates="comentarios")


class DocumentoProyecto(Base):
    __tablename__ = "documentos_proyecto"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    proyecto_id = Column(UUID(as_uuid=True), ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    tarea_id = Column(UUID(as_uuid=True), ForeignKey("tareas_proyecto.id", ondelete="SET NULL"))
    seaweed_fid = Column(String(100), nullable=False, unique=True)
    url_acceso = Column(Text)
    nombre_archivo = Column(String(255), nullable=False)
    extension = Column(String(20), nullable=False)
    peso_bytes = Column(Integer, nullable=False)
    subido_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    fecha_subida = Column(DateTime, default=_utcnow)
    activo = Column(Boolean, default=True)

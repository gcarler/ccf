"""Academy 2.0 — Catálogo, Evaluaciones, Matrícula, Progreso, Certificaciones.

Modelos para la Academia con Kernel UUID, motor de evaluaciones (quizzes),
seguimiento de progreso por lección, foros, y certificaciones.
"""
from datetime import datetime, timezone

import uuid as _uuid

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, JSON, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════
# CATÁLOGO ACADÉMICO
# ═══════════════════════════════════════════════════════════════════

class Curso(Base):
    __tablename__ = "academy_courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True)
    code = Column(String(50), nullable=False, unique=True)
    slug = Column(String(200), nullable=True, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    excerpt = Column(Text, nullable=True)
    tag = Column(String(100), nullable=True)
    cta_text = Column(String(100), nullable=True)
    syllabus = Column(JSON, nullable=True)
    instructor_name = Column(String(200), nullable=True)
    modality = Column(String(50), nullable=False)
    otorga_rol_iglesia = Column(String(50), nullable=True)
    is_published = Column(Boolean, default=False)
    is_self_paced = Column(Boolean, default=False)
    duration_hours = Column(Integer, nullable=False)
    xp_per_lesson = Column(Integer, default=10)
    image_url = Column(String(255))
    # open=cualquier registrado | member=academy:study | advanced=academy:edit
    access_level = Column(String(20), nullable=False, default="member", server_default="member")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    lecciones = relationship("Leccion", back_populates="curso",
                             cascade="all, delete-orphan")
    prerrequisitos = relationship("PrerrequisitoCurso",
                                  foreign_keys="PrerrequisitoCurso.course_id")


class PrerrequisitoCurso(Base):
    __tablename__ = "academy_course_prerequisites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False)
    prerequisite_course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"),
                                    nullable=False)

    __table_args__ = (
        UniqueConstraint("course_id", "prerequisite_course_id",
                         name="uq_course_prerequisite"),
    )


class Leccion(Base):
    __tablename__ = "academy_lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="video")
    media_url = Column(String(255))
    order_index = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    is_published = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    curso = relationship("Curso", back_populates="lecciones")


# ═══════════════════════════════════════════════════════════════════
# EVALUACIONES
# ═══════════════════════════════════════════════════════════════════

class Evaluacion(Base):
    __tablename__ = "academy_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    max_score = Column(Float, nullable=False)
    passing_score = Column(Float, nullable=False)
    weight = Column(Numeric, default=1.0)
    is_published = Column(Boolean, default=False)

    preguntas = relationship("Pregunta", back_populates="evaluacion",
                             cascade="all, delete-orphan")


class Pregunta(Base):
    __tablename__ = "academy_assessment_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessments.id"),
                           nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50))
    points = Column(Integer, default=1)

    evaluacion = relationship("Evaluacion", back_populates="preguntas")
    opciones = relationship("Opcion", back_populates="pregunta",
                            cascade="all, delete-orphan")


class Opcion(Base):
    __tablename__ = "academy_assessment_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessment_questions.id"),
                         nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    pregunta = relationship("Pregunta", back_populates="opciones")


# ═══════════════════════════════════════════════════════════════════
# MATRÍCULA Y PROGRESO
# ═══════════════════════════════════════════════════════════════════

class Matricula(Base):
    __tablename__ = "academy_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"),
                        nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False)
    cohort_name = Column(String(100))
    status = Column(String(50), nullable=False, default="ACTIVO")
    progress_percent = Column(Float, default=0.0)
    final_grade = Column(Float, nullable=True)
    attendance_percent = Column(Float, default=0.0)
    approved = Column(Boolean, default=False)
    acta_closed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    persona = relationship("Persona")
    curso = relationship("Curso")

    __table_args__ = (
        UniqueConstraint("persona_id", "course_id",
                         name="uq_enrollment_persona_course"),
    )


class ProgresoLeccion(Base):
    __tablename__ = "academy_lesson_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"),
                        nullable=False)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=False)
    progress_percent = Column(Numeric, default=0.0)
    is_completed = Column(Boolean, default=False)
    last_position_seconds = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("persona_id", "lesson_id",
                         name="uq_lesson_progress_persona_lesson"),
    )


class AsistenciaClase(Base):
    __tablename__ = "academy_course_attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True),
                           ForeignKey("academy_enrollments.id"), nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False)
    recorded_by_persona_id = Column(UUID(as_uuid=True),
                                    ForeignKey("personas.id"), nullable=False)


class IntentoEvaluacion(Base):
    __tablename__ = "academy_assessment_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessments.id"),
                           nullable=False)
    enrollment_id = Column(UUID(as_uuid=True),
                           ForeignKey("academy_enrollments.id"), nullable=False)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, default=False)
    submitted_at = Column(DateTime(timezone=True), default=_utcnow)

    evaluacion = relationship("Evaluacion")
    matricula = relationship("Matricula")


class EntregaTarea(Base):
    __tablename__ = "academy_assignment_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True),
                           ForeignKey("academy_enrollments.id"), nullable=False)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=False)
    seaweed_fid = Column(String(100), nullable=False)
    teacher_feedback = Column(Text, nullable=True)
    grade = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ═══════════════════════════════════════════════════════════════════
# CERTIFICACIONES
# ═══════════════════════════════════════════════════════════════════

class Certificado(Base):
    __tablename__ = "academy_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True),
                           ForeignKey("academy_enrollments.id"), nullable=False)
    certificate_code = Column(String(100), nullable=False, unique=True)
    certificate_type = Column(String(50))
    issued_at = Column(DateTime(timezone=True), default=_utcnow)


class ActaFormal(Base):
    __tablename__ = "academy_formal_actas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False)
    cohort_name = Column(String(100), nullable=False)
    closed_by_persona_id = Column(UUID(as_uuid=True),
                                  ForeignKey("personas.id"), nullable=False)
    min_grade = Column(Float, nullable=False)
    min_attendance = Column(Float, nullable=False)
    status = Column(String(50), default="BORRADOR")

    entradas = relationship("ActaEntrada", back_populates="acta",
                            cascade="all, delete-orphan")


class ActaEntrada(Base):
    """Notas individuales de cada alumno en un acta."""
    __tablename__ = "academy_formal_acta_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    acta_id = Column(UUID(as_uuid=True), ForeignKey("academy_formal_actas.id"), nullable=False)
    enrollment_id = Column(UUID(as_uuid=True),
                           ForeignKey("academy_enrollments.id"), nullable=False)
    final_grade = Column(Float, nullable=True)
    attendance_percent = Column(Float, default=0.0)
    approved = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    acta = relationship("ActaFormal", back_populates="entradas")


# ═══════════════════════════════════════════════════════════════════
# FOROS
# ═══════════════════════════════════════════════════════════════════

class HiloForo(Base):
    __tablename__ = "academy_forum_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"),
                               nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class ComentarioForo(Base):
    __tablename__ = "academy_forum_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("academy_forum_threads.id"),
                       nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("academy_forum_comments.id"),
                       nullable=True)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"),
                               nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    respuestas = relationship("ComentarioForo", backref="parent",
                              remote_side="ComentarioForo.id")

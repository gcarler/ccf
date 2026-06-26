"""Academy 2.0 — Pydantic schemas (Create + Response) for all academy_core models."""

from __future__ import annotations
from uuid import UUID

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config


# ═══════════════════════════════════════════════════════════════════════
# CATÁLOGO ACADÉMICO
# ═══════════════════════════════════════════════════════════════════════

class CursoCreate(BaseModel):
    sede_id: Optional[str] = None
    code: str
    title: str
    description: Optional[str] = None
    modality: str
    otorga_rol_iglesia: Optional[str] = None
    is_published: bool = False
    is_self_paced: bool = False
    duration_hours: int
    xp_per_lesson: int = 10
    image_url: Optional[str] = None
    access_level: Literal["open", "persona", "advanced"] = "persona"


class CursoUpdate(BaseModel):
    sede_id: Optional[str] = None
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    modality: Optional[str] = None
    otorga_rol_iglesia: Optional[str] = None
    is_published: Optional[bool] = None
    is_self_paced: Optional[bool] = None
    duration_hours: Optional[int] = None
    xp_per_lesson: Optional[int] = None
    image_url: Optional[str] = None
    access_level: Optional[Literal["open", "persona", "advanced"]] = None


class CursoResponse(BaseModel):
    id: UUID
    sede_id: Optional[str] = None
    code: str
    title: str
    description: Optional[str] = None
    modality: str
    otorga_rol_iglesia: Optional[str] = None
    is_published: bool = False
    is_self_paced: bool = False
    duration_hours: int
    xp_per_lesson: int = 10
    image_url: Optional[str] = None
    access_level: str = "persona"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    lecciones: list[LeccionResponse] = Field(default_factory=list)
    model_config = orm_config


class LeccionCreate(BaseModel):
    course_id: UUID
    title: str
    content: str
    content_type: str = "video"
    media_url: Optional[str] = None
    order_index: int
    duration_minutes: int
    is_published: bool = False


class LeccionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    media_url: Optional[str] = None
    order_index: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_published: Optional[bool] = None


class LeccionResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    content: str
    content_type: str = "video"
    media_url: Optional[str] = None
    order_index: int
    duration_minutes: int
    is_published: bool = False
    model_config = orm_config


class PrerrequisitoCursoCreate(BaseModel):
    course_id: UUID
    prerequisite_course_id: str


class PrerrequisitoCursoResponse(BaseModel):
    id: UUID
    course_id: UUID
    prerequisite_course_id: str
    model_config = orm_config


# ═══════════════════════════════════════════════════════════════════════
# EVALUACIONES
# ═══════════════════════════════════════════════════════════════════════

class EvaluacionCreate(BaseModel):
    course_id: UUID
    lesson_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    max_score: float
    passing_score: float
    weight: float = 1.0
    is_published: bool = False


class EvaluacionResponse(BaseModel):
    id: UUID
    course_id: UUID
    lesson_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    max_score: float
    passing_score: float
    weight: float = 1.0
    is_published: bool = False
    model_config = orm_config


class PreguntaCreate(BaseModel):
    assessment_id: str
    question_text: str
    question_type: Optional[str] = None
    points: int = 1


class PreguntaResponse(BaseModel):
    id: UUID
    assessment_id: str
    question_text: str
    question_type: Optional[str] = None
    points: int = 1
    opciones: list[OpcionResponse] = Field(default_factory=list)
    model_config = orm_config


class OpcionCreate(BaseModel):
    question_id: str
    option_text: str
    is_correct: bool = False


class OpcionResponse(BaseModel):
    id: UUID
    question_id: str
    option_text: str
    is_correct: bool = False
    model_config = orm_config


# ═══════════════════════════════════════════════════════════════════════
# MATRÍCULA Y PROGRESO
# ═══════════════════════════════════════════════════════════════════════

class MatriculaCreate(BaseModel):
    persona_id: UUID
    course_id: UUID
    cohort_name: Optional[str] = None
    status: str = "ACTIVO"
    progress_percent: float = 0.0
    final_grade: Optional[float] = None
    attendance_percent: float = 0.0
    approved: bool = False
    acta_closed: bool = False
    completed_at: Optional[datetime] = None


class MatriculaResponse(BaseModel):
    id: UUID
    persona_id: UUID
    course_id: UUID
    cohort_name: Optional[str] = None
    status: str = "ACTIVO"
    progress_percent: float = 0.0
    final_grade: Optional[float] = None
    attendance_percent: float = 0.0
    approved: bool = False
    acta_closed: bool = False
    completed_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = orm_config


class ProgresoUpdate(BaseModel):
    progress_percent: Optional[float] = None
    lessons_completed: Optional[list] = None


class ProgresoLeccionCreate(BaseModel):
    persona_id: UUID
    lesson_id: UUID
    progress_percent: float = 0.0
    is_completed: bool = False
    last_position_seconds: int = 0


class ProgresoLeccionResponse(BaseModel):
    id: UUID
    persona_id: UUID
    lesson_id: UUID
    progress_percent: float = 0.0
    is_completed: bool = False
    last_position_seconds: int = 0
    model_config = orm_config


class AsistenciaClaseCreate(BaseModel):
    enrollment_id: UUID
    session_date: datetime
    status: str
    recorded_by_persona_id: str


class AsistenciaClaseResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    session_date: datetime
    status: str
    recorded_by_persona_id: str
    model_config = orm_config


class IntentoEvaluacionCreate(BaseModel):
    assessment_id: str
    enrollment_id: UUID
    score: Optional[float] = None
    passed: bool = False


class IntentoEvaluacionResponse(BaseModel):
    id: UUID
    assessment_id: str
    enrollment_id: UUID
    score: Optional[float] = None
    passed: bool = False
    submitted_at: Optional[datetime] = None
    model_config = orm_config


class EntregaTareaCreate(BaseModel):
    enrollment_id: UUID
    lesson_id: UUID
    seaweed_fid: str
    teacher_feedback: Optional[str] = None
    grade: Optional[float] = None


class EntregaTareaResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    lesson_id: UUID
    seaweed_fid: str
    teacher_feedback: Optional[str] = None
    grade: Optional[float] = None
    created_at: Optional[datetime] = None
    model_config = orm_config


# ═══════════════════════════════════════════════════════════════════════
# CERTIFICACIONES
# ═══════════════════════════════════════════════════════════════════════

class CertificadoCreate(BaseModel):
    enrollment_id: UUID
    certificate_code: str
    certificate_type: Optional[str] = None


class CertificadoResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    certificate_code: str
    certificate_type: Optional[str] = None
    issued_at: Optional[datetime] = None
    model_config = orm_config


class ActaFormalCreate(BaseModel):
    course_id: UUID
    cohort_name: str
    closed_by_persona_id: str
    min_grade: float
    min_attendance: float
    status: str = "BORRADOR"


class ActaFormalResponse(BaseModel):
    id: UUID
    course_id: UUID
    cohort_name: str
    closed_by_persona_id: str
    min_grade: float
    min_attendance: float
    status: str = "BORRADOR"
    model_config = orm_config


# ═══════════════════════════════════════════════════════════════════════
# FOROS
# ═══════════════════════════════════════════════════════════════════════

class HiloForoCreate(BaseModel):
    course_id: UUID
    author_persona_id: str
    title: str
    content: str


class HiloForoResponse(BaseModel):
    id: UUID
    course_id: UUID
    author_persona_id: str
    title: str
    content: str
    created_at: Optional[datetime] = None
    model_config = orm_config


class ComentarioForoCreate(BaseModel):
    thread_id: UUID
    parent_id: Optional[int] = None
    author_persona_id: str
    content: str


class ComentarioForoResponse(BaseModel):
    id: UUID
    thread_id: UUID
    parent_id: Optional[int] = None
    author_persona_id: str
    content: str
    created_at: Optional[datetime] = None
    model_config = orm_config

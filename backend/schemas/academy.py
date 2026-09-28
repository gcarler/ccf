from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from backend.schemas._common import orm_config


# M-09 — Helper de normalización tz-aware (modo before-validation).
# SQLite read-back pierde tzinfo (documentado en projects/MEMORY.md —
# `_as_aware_utc`). Pydantic acepta naive datetimes por defecto; este helper
# adjunta UTC si falta tzinfo, sin rechazar el input. Aplicado vía
# `@field_validator(..., mode="before")` en los read schemas con datetimes
# sensibles (Enrollment.created_at, Certificate.issued_at,
# AssessmentAttempt.created_at). No se aplica a `datetime | None` (None pasa).
def _ensure_utc(value: Any) -> Any:
    """Normaliza un datetime naive → aware UTC在读膜back desde SQLite."""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# ── Enums canónicos (validación en borde Pydantic) ────────────────────────────
# Definidos aquí (no en api/academy.py) porque los write schemas los usan.
# Reflejan el vocabulario de String(50) en models_academy_core.py.


class Modality(str, Enum):
    """TKT-051 — vocabulario canónico para ``Course.modality`` (String 50)."""

    ONLINE = "online"
    PRESENTIAL = "presential"
    HYBRID = "hybrid"
    FORMAL = "formal"
    NON_FORMAL = "non_formal"
    VIRTUAL = "virtual"


class ContentType(str, Enum):
    """TKT-054 — vocabulario canónico para ``Lesson.content_type`` (String 50)."""

    VIDEO = "video"
    TEXT = "text"
    DOCUMENT = "document"
    IMAGE = "image"


class CoursePrerequisiteBase(BaseModel):
    course_id: UUID
    prerequisite_course_id: str


class CoursePrerequisite(CoursePrerequisiteBase):
    id: UUID
    model_config = orm_config


class Course(BaseModel):
    id: UUID
    code: str
    slug: Optional[str] = None
    title: str
    description: Optional[str] = None
    excerpt: Optional[str] = None
    tag: Optional[str] = None
    cta_text: Optional[str] = None
    syllabus: Optional[dict | list] = None
    modality: str
    # H-01 (cierre 2026-07-24): sede del curso (NULL = global legítimo por
    # A-03 lectura/captación). El API lo inyecta vía ``get_user_sede_id`` en
    # ``create_course_admin``; el write schema ``CoursePayload`` NO lo acepta
    # (``extra="forbid"``) para impedir que un cliente atribuya a otra sede.
    sede_id: Optional[UUID] = None
    is_published: bool = True
    is_self_paced: bool = False
    duration_hours: int = 0
    xp_per_lesson: int = 10
    cohort_name: Optional[str] = None
    certificate_type: Optional[str] = None
    access_level: str = "persona"  # open | persona | advanced
    created_at: datetime | None = None
    prerequisites: List[CoursePrerequisite] = Field(default_factory=list)
    lesson_count: int = 0
    total_minutes: int = 0
    image_url: Optional[str] = None
    instructor_name: Optional[str] = None
    model_config = orm_config


class Lesson(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    content: Optional[str] = None
    content_type: str = "video"
    media_url: Optional[str] = None
    order_index: int = 0
    duration_minutes: int = 0
    model_config = orm_config


class AssessmentOption(BaseModel):
    id: UUID
    option_text: str
    model_config = orm_config


class AssessmentQuestion(BaseModel):
    id: UUID
    question_text: str
    question_type: str
    points: int
    options: List[AssessmentOption] = Field(default_factory=list)
    model_config = orm_config

    # M-08 — alias de escritura: el write ``AssessmentQuestionPayload`` usa
    # ``text``/``type``; exponemos también esos nombres en lectura para que
    # un cliente pueda consumir una sola surface sin distinguir read vs write.
    @computed_field
    @property
    def text(self) -> str:
        return self.question_text

    @computed_field
    @property
    def type(self) -> str:
        return self.question_type


class Assessment(BaseModel):
    id: UUID
    # M-10 — el ORM es ``nullable=False``; el schema read no debe aceptar None.
    course_id: UUID
    title: str = "Assessment"
    description: Optional[str] = None
    min_score: float = 70
    weight: float = 1.0
    questions: List[AssessmentQuestion] = Field(default_factory=list)
    model_config = orm_config

    # M-08 — alias de escritura: el ORM persiste ``passing_score`` (sinónimo
    # ORM de ``min_score``); el write schema ``AssessmentPayload``/``AssessmentUpdate``
    # usa ``passing_score``. Exponemos ambos en lectura para estabilizar el contrato.
    @computed_field
    @property
    def passing_score(self) -> float:
        return self.min_score


class AssessmentAttempt(BaseModel):
    id: UUID
    enrollment_id: UUID
    assessment_id: UUID
    score: float = 0.0
    passed: bool = False
    created_at: datetime | None = None
    answers: List[AssessmentAnswer] = Field(default_factory=list)
    model_config = orm_config

    # M-09 — tz-aware normalización (SQLite read-back pierde tzinfo).
    _ensure_tz_created = field_validator("created_at", mode="before")(classmethod(lambda cls, v: _ensure_utc(v)))


class AssessmentAnswer(BaseModel):
    id: UUID
    attempt_id: UUID
    question_id: UUID
    selected_option_id: Optional[UUID] = None
    text_response: Optional[str] = None
    is_correct: Optional[bool] = None
    points_awarded: float = 0
    model_config = orm_config


class AssessmentAnswerSubmit(BaseModel):
    question_id: UUID
    selected_option_id: Optional[UUID] = None
    text_response: Optional[str] = None


class AssessmentAttemptSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_id: Optional[UUID] = None
    submitted_score: Optional[float] = None
    answers: Optional[List[AssessmentAnswerSubmit]] = None


class EnrollmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_id: UUID
    course_id: UUID


class Enrollment(BaseModel):
    id: UUID
    persona_id: UUID
    course_id: UUID
    status: str = "active"
    progress_percent: float = 0
    approved: bool = False
    certificate_issued: bool = False
    final_grade: Optional[float] = None
    attendance_percent: float = 0
    acta_closed: bool = False
    created_at: datetime | None = None
    model_config = orm_config

    # M-09 — tz-aware normalización (SQLite read-back pierde tzinfo).
    _ensure_tz_created = field_validator("created_at", mode="before")(classmethod(lambda cls, v: _ensure_utc(v)))


class CourseAttendanceBase(BaseModel):
    enrollment_id: UUID
    status: str = "present"
    # M-10 — el ORM ``session_date`` es ``nullable=False``; no debe ser Optional.
    session_date: datetime


class CourseAttendanceCreate(CourseAttendanceBase):
    pass


class BulkAttendanceRecord(BaseModel):
    enrollment_id: UUID
    status: str


class BulkAttendanceCreate(BaseModel):
    session_date: datetime
    records: List[BulkAttendanceRecord]


class Certificate(BaseModel):
    id: UUID
    enrollment_id: UUID
    certificate_code: str
    issued_at: datetime
    model_config = orm_config

    # M-09 — tz-aware normalización (SQLite read-back pierde tzinfo).
    _ensure_tz_issued = field_validator("issued_at", mode="before")(classmethod(lambda cls, v: _ensure_utc(v)))


class CertificateValidationStudent(BaseModel):
    """Metadatos públicos del estudiante certificado — sin PII ni IDs internos."""

    username: str | None = None


class CertificateValidationCourse(BaseModel):
    """Metadatos públicos del curso asociado al certificado."""

    title: str


class CertificateValidationEnrollment(BaseModel):
    """Datos públicos de la inscripción firmada por el certificado."""

    student: CertificateValidationStudent
    course: CertificateValidationCourse


class CertificateValidation(BaseModel):
    """Respuesta pública de validación de un certificado por código.

    A diferencia del schema ``Certificate`` (que expone IDs internos y se
    reserva al flujo autenticado de emisión), este schema sólo transporta
    metadatos públicos无毒: ``certificate_code``, ``issued_at``,
    ``certificate_type`` y los anidados ``enrollment.student.username`` +
    ``enrollment.course.title`` que consume el frontend de validación
    pública. No expone ``id`` ni ``enrollment_id`` internos — cierra la
    enumeración oracle de A-01.
    """

    certificate_code: str
    certificate_type: str | None = None
    issued_at: datetime
    enrollment: CertificateValidationEnrollment
    model_config = orm_config


class DashboardMetrics(BaseModel):
    active_students: int = 0
    completion_rate: float = 0.0
    certificates_issued: int = 0
    cards: list[dict] = []
    formal_stats: dict = {}
    no_formal_stats: dict = {}
    top_courses: list[dict] = []


class CourseAttendance(BaseModel):
    id: UUID
    enrollment_id: UUID
    session_date: datetime
    status: str = "present"
    recorded_by_persona_id: Optional[UUID] = None
    model_config = orm_config


class PilotReadiness(BaseModel):
    environment_ready: bool = False
    readiness_score: float = 0.0
    checklist: List[Dict[str, Any]] = Field(default_factory=list)


class FormalActaCloseRequest(BaseModel):
    min_grade: float = 70
    min_attendance: float = 75


class FormalActa(BaseModel):
    id: UUID
    course_id: UUID
    status: str = "closed"
    created_at: datetime
    # M-11 — exponer actor y metadatos del acta para cumplir REGLAS.md §4.1
    # (actor required) a nivel contrato. El modelo los定义 en
    # ``models_academy_core.py:288-296`` como ``nullable=False``.
    cohort_name: str = "General"
    closed_by_persona_id: UUID
    min_grade: float = 70
    min_attendance: float = 75
    model_config = orm_config


class AcademyActivityLog(BaseModel):
    """F-10 (cierre 2026-08-02): schema read dedicado para ``AcademyActivityLog``.

    El modelo ``models_academy_core.AcademyActivityLog`` (tabla
    ``academy_activity_logs``) se persiste en mutaciones del módulo
    (enrollment, forum_resolved, course_archived, submission_graded) pero no
    tenía schema dedicado en ``schemas/academy.py`` — cualquier
    serialización futura caería a dict ad-hoc. ``payload_json`` (JSON) se
    expone como ``dict | None`` y ``value`` (Numeric) como ``float``.
    """

    id: UUID
    event_type: str
    course_id: UUID | None = None
    persona_id: UUID | None = None
    modality: str | None = None
    value: float = 1.0
    payload_json: dict | None = None
    created_at: datetime | None = None
    model_config = orm_config

    # M-09 — tz-aware normalización (SQLite read-back pierde tzinfo).
    _ensure_tz_created = field_validator("created_at", mode="before")(classmethod(lambda cls, v: _ensure_utc(v)))


class FormalActaEntry(BaseModel):
    """F-10 (cierre 2026-08-02): schema read dedicado para ``FormalActaEntry``.

    Modelo ``models_academy_core.FormalActaEntry`` (tabla
    ``academy_formal_acta_entries``). ``final_grade`` es nullable y
    ``attendance_percent``/``approved`` reflejan el cierre del acta.
    """

    id: UUID
    acta_id: UUID
    enrollment_id: UUID
    final_grade: float | None = None
    attendance_percent: float = 0.0
    approved: bool = False
    notes: str | None = None
    model_config = orm_config


class Resource(BaseModel):
    id: UUID
    lesson_id: UUID
    title: str
    file_url: str
    resource_type: Optional[str] = None
    model_config = orm_config


class ResourceCreate(BaseModel):
    """Material enlazado a una lección; el archivo ya debe estar gestionado por storage."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    file_url: str = Field(min_length=1, max_length=500)
    resource_type: str | None = Field(default=None, max_length=50)


class AssignmentSubmission(BaseModel):
    id: UUID
    enrollment_id: UUID
    lesson_id: UUID
    file_url: str
    comment: Optional[str] = None
    grade: Optional[float] = None
    teacher_feedback: Optional[str] = None
    created_at: datetime
    model_config = orm_config


class AssignmentSubmissionReview(BaseModel):
    id: UUID
    enrollment_id: UUID
    lesson_id: UUID
    student_name: str
    lesson_title: str
    file_url: str
    comment: Optional[str] = None
    grade: Optional[float] = None
    teacher_feedback: Optional[str] = None
    submitted_at: datetime


class AcademyStudentProfile(BaseModel):
    persona_id: UUID
    username: str
    total_progress: float = 0.0
    enrollments_count: int = 0
    certificates_count: int = 0
    active_courses: list[Enrollment] = Field(default_factory=list)
    recent_certificates: list[Certificate] = Field(default_factory=list)


class ForumCategory(str, Enum):
    GENERAL = "general"
    ANNOUNCEMENT = "announcement"
    QUESTION = "question"
    DISCUSSION = "discussion"
    RESOURCE = "resource"
    THEOLOGY = "theology"
    LEADERSHIP = "leadership"
    ACADEMIC = "academic"
    MISSIONS = "missions"
    TESTIMONIES = "testimonies"


class ForumThreadBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=200)
    category: ForumCategory = ForumCategory.GENERAL

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> object:
        """Acepta etiquetas históricas de UI, pero persiste el vocabulario canónico."""
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        aliases = {
            "teologia": "theology",
            "teología": "theology",
            "liderazgo": "leadership",
            "academico": "academic",
            "académico": "academic",
            "misiones": "missions",
            "testimonios": "testimonies",
        }
        return aliases.get(normalized, normalized)


class ForumThreadCreate(ForumThreadBase):
    content: Optional[str] = None
    course_id: Optional[UUID] = None


class ForumThread(BaseModel):
    id: UUID
    title: str
    category: str
    author_persona_id: UUID
    is_resolved: bool = False
    created_at: datetime
    model_config = orm_config


class ForumCommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=10000)
    parent_id: UUID | None = None


class ForumCommentRead(BaseModel):
    id: UUID
    thread_id: UUID
    parent_id: UUID | None = None
    author_persona_id: UUID
    content: str
    created_at: datetime
    model_config = orm_config


# ── Write schemas (consolidated from api/academy.py inline models) ────────────


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    progress_percent: float = Field(ge=0, le=100)
    last_position_seconds: int = Field(default=0, ge=0)


class LessonProgressResponse(BaseModel):
    """H-02 (cierre 2026-07-24): response tipado para
    ``GET /academy/lessons/{id}/progress``.

    Antes, el endpoint devolvía un dict literal ``{"progress_percent": ...,
    "last_position_seconds": ..., "is_completed": ...}`` sin
    ``response_model``. ``ProgressUpdate`` valida el write, pero el read
    quedaba fuera del contract — el ORM ``LessonProgress`` no se exponía
    con schema. Ahora el endpoint declara ``response_model=LessonProgressResponse``,
    y mapea tanto el ORM row (``progress_percent``, ``last_position_seconds``,
    ``is_completed``) como el dict fallback (0.0 / 0 / False cuando no
    hay progreso guardado) en el mismo contract.
    """

    model_config = orm_config

    progress_percent: float = 0.0
    last_position_seconds: int = 0
    is_completed: bool = False


class CoursePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=50)
    slug: str | None = Field(default=None, max_length=200)
    title: str = Field(max_length=200)
    description: str | None = None
    excerpt: str | None = None
    tag: str | None = Field(default=None, max_length=100)
    cta_text: str | None = Field(default=None, max_length=100)
    syllabus: dict | list | None = None
    modality: Modality = Modality.ONLINE
    is_published: bool = False
    is_self_paced: bool = False
    duration_hours: int = Field(default=0, ge=0)
    cohort_name: str | None = Field(default=None, max_length=100)
    certificate_type: str | None = Field(default=None, max_length=50)
    instructor_name: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=255)
    access_level: Literal["open", "persona", "advanced"] = "persona"


class CourseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, max_length=50)
    slug: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    excerpt: str | None = None
    tag: str | None = Field(default=None, max_length=100)
    cta_text: str | None = Field(default=None, max_length=100)
    syllabus: dict | list | None = None
    modality: Modality | None = None
    is_published: bool | None = None
    is_self_paced: bool | None = None
    duration_hours: int | None = Field(default=None, ge=0)
    cohort_name: str | None = Field(default=None, max_length=100)
    certificate_type: str | None = Field(default=None, max_length=50)
    instructor_name: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=255)
    access_level: Literal["open", "persona", "advanced"] | None = None


class LessonPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=200)
    content: str = ""
    content_type: ContentType = ContentType.VIDEO
    media_url: str | None = None
    order_index: int = 0
    duration_minutes: int = Field(default=0, ge=0)
    is_published: bool = False


class LessonUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    content: str | None = None
    content_type: ContentType | None = None
    media_url: str | None = None
    order_index: int | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    is_published: bool | None = None


class AssessmentQuestionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    type: str = "multiple_choice"
    points: int = Field(default=1, ge=1)
    options: list[str] = Field(default_factory=list)
    correct_option: int = Field(default=0, ge=0)


class AssessmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: UUID
    lesson_id: UUID | None = None
    title: str = Field(max_length=200)
    description: str | None = None
    passing_score: float = Field(default=70, ge=0, le=100)
    questions: list[AssessmentQuestionPayload] = Field(default_factory=list)


class AssessmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    passing_score: float | None = Field(default=None, ge=0, le=100)


class GradeSubmissionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grade: float = Field(ge=0, le=100)
    feedback: str | None = None


# ── Response schemas (typed responses for serialize_dict endpoints) ────────────


class CourseListItem(BaseModel):
    id: UUID
    code: str
    slug: str | None = None
    title: str
    description: str | None = None
    excerpt: str | None = None
    tag: str | None = None
    cta_text: str | None = None
    modality: str
    # H-01 (cierre 2026-07-24): sede del curso en el contract list item.
    sede_id: UUID | None = None
    is_published: bool
    is_self_paced: bool
    duration_hours: int
    cohort_name: str | None = None
    certificate_type: str | None = None
    xp_per_lesson: int
    access_level: str
    image_url: str | None = None
    instructor_name: str | None = None
    created_at: datetime | None = None
    lesson_count: int = 0
    total_minutes: int = 0
    model_config = orm_config


class EnrollmentResponse(BaseModel):
    id: UUID
    persona_id: UUID
    course_id: UUID
    status: str
    progress_percent: float
    final_grade: float | None = None
    attendance_percent: float
    approved: bool
    acta_closed: bool
    certificate_issued: bool
    created_at: datetime | None = None
    course: CourseListItem | None = None
    model_config = orm_config


class MyProgressItem(BaseModel):
    id: UUID
    title: str
    progress_percent: float
    status: str
    average_grade: float
    lessons_completed: int
    total_lessons: int
    last_activity: datetime | None = None
    certificate_issued: bool


class MyCertificateItem(BaseModel):
    id: UUID
    enrollment_id: UUID
    certificate_code: str
    certificate_type: str | None = None
    course_title: str
    issued_at: datetime


class ScheduleItem(BaseModel):
    id: UUID
    title: str
    modality: str
    cohort_name: str | None = None
    duration_hours: int


class DashboardMetricsResponse(BaseModel):
    active_students: int = 0
    completion_rate: float = 0.0
    certificates_issued: int = 0
    cards: list[dict] = []
    formal_stats: dict = {}
    no_formal_stats: dict = {}
    top_courses: list[dict] = []


class PilotReadinessResponse(BaseModel):
    environment_ready: bool = False
    readiness_score: float = 0.0
    checklist: list[dict] = []


class SubmissionListItem(BaseModel):
    id: UUID
    enrollment_id: UUID
    lesson_id: UUID
    student_name: str
    lesson_title: str
    file_url: str
    comment: str | None = None
    grade: float | None = None
    teacher_feedback: str | None = None
    submitted_at: datetime


class CourseStudentItem(BaseModel):
    id: UUID
    enrollment_id: UUID
    persona_id: UUID
    username: str
    email: str
    status: str
    progress: float
    progress_percent: float
    attendance_count: int
    average_grade: float
    approved: bool


class AcademyPersonaItem(BaseModel):
    id: UUID
    persona_id: UUID
    username: str
    name: Optional[str] = None
    full_name: Optional[str] = None
    email: str
    role: str
    is_active: bool


class MyProfileResponse(BaseModel):
    persona_id: UUID
    username: str
    total_progress: float
    enrollments_count: int
    certificates_count: int
    active_courses: list[EnrollmentResponse] = []
    recent_certificates: list[Certificate] = []


# ── Super-PRO Academy: Programs, Credits, Study Plans & Grading Schemes ──────────


class AcademyProgramBase(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    program_type: str = Field(default="diplomado", max_length=50)
    level_name: Optional[str] = Field(default=None, max_length=100)
    total_duration_type: str = Field(default="semestres", max_length=50)
    total_duration_units: int = Field(default=2, ge=1)
    total_credits: int = Field(default=0, ge=0)
    modality: str = Field(default="presencial", max_length=50)
    has_teachers: bool = True
    teachers_can_grade: bool = True
    min_passing_grade: float = Field(default=70.0, ge=0.0)
    grading_scale_max: float = Field(default=100.0, gt=0.0)
    min_attendance_percent: float = Field(default=80.0, ge=0.0, le=100.0)
    is_active: bool = True


class AcademyProgramCreate(AcademyProgramBase):
    model_config = ConfigDict(extra="forbid")


class AcademyProgramUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    program_type: Optional[str] = Field(default=None, max_length=50)
    level_name: Optional[str] = Field(default=None, max_length=100)
    total_duration_type: Optional[str] = Field(default=None, max_length=50)
    total_duration_units: Optional[int] = Field(default=None, ge=1)
    total_credits: Optional[int] = Field(default=None, ge=0)
    modality: Optional[str] = Field(default=None, max_length=50)
    has_teachers: Optional[bool] = None
    teachers_can_grade: Optional[bool] = None
    min_passing_grade: Optional[float] = Field(default=None, ge=0.0)
    grading_scale_max: Optional[float] = Field(default=None, gt=0.0)
    min_attendance_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    is_active: Optional[bool] = None


class AcademyProgramRead(AcademyProgramBase):
    id: UUID
    sede_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    study_plans_count: int = 0
    model_config = orm_config


class AcademyAcademicPeriodBase(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=100)
    period_type: str = Field(default="semestral", max_length=50)
    start_date: date
    end_date: date
    enrollment_start_date: Optional[date] = None
    enrollment_end_date: Optional[date] = None
    grading_deadline: Optional[date] = None
    status: str = Field(default="open", max_length=50)
    is_active: bool = True


class AcademyAcademicPeriodCreate(AcademyAcademicPeriodBase):
    model_config = ConfigDict(extra="forbid")


class AcademyAcademicPeriodUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    period_type: Optional[str] = Field(default=None, max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    enrollment_start_date: Optional[date] = None
    enrollment_end_date: Optional[date] = None
    grading_deadline: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class AcademyAcademicPeriodRead(AcademyAcademicPeriodBase):
    id: UUID
    sede_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    offerings_count: int = 0
    model_config = orm_config


class AcademyGradingSchemeCutBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    order_index: int = Field(default=1, ge=1)
    weight_percent: float = Field(default=30.0, ge=0.0, le=100.0)
    description: Optional[str] = None


class AcademyGradingSchemeCutCreate(AcademyGradingSchemeCutBase):
    model_config = ConfigDict(extra="forbid")


class AcademyGradingSchemeCutRead(AcademyGradingSchemeCutBase):
    id: UUID
    scheme_id: UUID
    model_config = orm_config


class AcademyGradingSchemeBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None
    scale_max: float = Field(default=100.0, gt=0.0)
    passing_grade: float = Field(default=70.0, ge=0.0)
    is_default: bool = False
    is_active: bool = True


class AcademyGradingSchemeCreate(AcademyGradingSchemeBase):
    cuts: List[AcademyGradingSchemeCutCreate] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class AcademyGradingSchemeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None
    scale_max: Optional[float] = Field(default=None, gt=0.0)
    passing_grade: Optional[float] = Field(default=None, ge=0.0)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    cuts: Optional[List[AcademyGradingSchemeCutCreate]] = None


class AcademyGradingSchemeRead(AcademyGradingSchemeBase):
    id: UUID
    sede_id: Optional[UUID] = None
    cuts: List[AcademyGradingSchemeCutRead] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    model_config = orm_config


class AcademyStudyPlanSubjectBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    level_number: int = Field(default=1, ge=1)
    credits: int = Field(default=3, ge=0)
    weekly_hours_theory: int = Field(default=2, ge=0)
    weekly_hours_practice: int = Field(default=2, ge=0)
    weekly_hours_independent: int = Field(default=4, ge=0)
    is_mandatory: bool = True
    course_id: Optional[UUID] = None
    default_grading_scheme_id: Optional[UUID] = None
    order_index: int = 0
    prerequisite_codes: Optional[List[str]] = None


class AcademyStudyPlanSubjectCreate(AcademyStudyPlanSubjectBase):
    model_config = ConfigDict(extra="forbid")


class AcademyStudyPlanSubjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    level_number: Optional[int] = Field(default=None, ge=1)
    credits: Optional[int] = Field(default=None, ge=0)
    weekly_hours_theory: Optional[int] = Field(default=None, ge=0)
    weekly_hours_practice: Optional[int] = Field(default=None, ge=0)
    weekly_hours_independent: Optional[int] = Field(default=None, ge=0)
    is_mandatory: Optional[bool] = None
    course_id: Optional[UUID] = None
    default_grading_scheme_id: Optional[UUID] = None
    order_index: Optional[int] = None
    prerequisite_codes: Optional[List[str]] = None


class AcademyStudyPlanSubjectRead(AcademyStudyPlanSubjectBase):
    id: UUID
    study_plan_id: UUID
    created_at: Optional[datetime] = None
    model_config = orm_config


class AcademyStudyPlanBase(BaseModel):
    program_id: UUID
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    total_credits: int = Field(default=0, ge=0)
    total_levels: int = Field(default=1, ge=1)
    level_type: str = Field(default="semestre", max_length=50)
    is_active: bool = True


class AcademyStudyPlanCreate(AcademyStudyPlanBase):
    model_config = ConfigDict(extra="forbid")


class AcademyStudyPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    total_credits: Optional[int] = Field(default=None, ge=0)
    total_levels: Optional[int] = Field(default=None, ge=1)
    level_type: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class AcademyStudyPlanRead(AcademyStudyPlanBase):
    id: UUID
    sede_id: Optional[UUID] = None
    subjects: List[AcademyStudyPlanSubjectRead] = Field(default_factory=list)
    program_name: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = orm_config


class AcademyPeriodOfferingBase(BaseModel):
    academic_period_id: UUID
    subject_id: UUID
    course_id: Optional[UUID] = None
    docente_persona_id: Optional[UUID] = None
    grading_scheme_id: UUID
    group_name: str = Field(default="Grupo 01", max_length=50)
    quota_max: int = Field(default=40, ge=1)
    status: str = Field(default="open", max_length=50)
    classroom: Optional[str] = Field(default=None, max_length=100)
    schedule_summary: Optional[str] = Field(default=None, max_length=200)


class AcademyPeriodOfferingCreate(AcademyPeriodOfferingBase):
    model_config = ConfigDict(extra="forbid")


class AcademyPeriodOfferingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    docente_persona_id: Optional[UUID] = None
    grading_scheme_id: Optional[UUID] = None
    group_name: Optional[str] = Field(default=None, max_length=50)
    quota_max: Optional[int] = Field(default=None, ge=1)
    status: Optional[str] = Field(default=None, max_length=50)
    classroom: Optional[str] = Field(default=None, max_length=100)
    schedule_summary: Optional[str] = Field(default=None, max_length=200)


class AcademyPeriodOfferingRead(AcademyPeriodOfferingBase):
    id: UUID
    sede_id: Optional[UUID] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    credits: int = 0
    docente_name: Optional[str] = None
    period_code: Optional[str] = None
    grading_scheme_name: Optional[str] = None
    enrolled_count: int = 0
    created_at: Optional[datetime] = None
    model_config = orm_config


class AcademyStudentPeriodGradeItem(BaseModel):
    persona_id: UUID
    cut_id: UUID
    grade_value: Optional[float] = Field(default=None, ge=0.0)
    comments: Optional[str] = None


class AcademyBatchGradeSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offering_id: Optional[UUID] = None
    grades: List[AcademyStudentPeriodGradeItem]


class AcademyStudentPeriodGradeRead(BaseModel):
    id: UUID
    offering_id: UUID
    persona_id: UUID
    student_name: Optional[str] = None
    cut_id: UUID
    cut_name: Optional[str] = None
    cut_weight: float = 0.0
    grade_value: Optional[float] = None
    comments: Optional[str] = None
    graded_by_persona_id: Optional[UUID] = None
    graded_at: Optional[datetime] = None
    model_config = orm_config


class AcademyStudentSubjectRecordRead(BaseModel):
    id: UUID
    offering_id: UUID
    persona_id: UUID
    student_name: Optional[str] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    credits_attempted: int = 0
    credits_earned: int = 0
    calculated_final_grade: Optional[float] = None
    final_grade_override: Optional[float] = None
    passed: bool = False
    attendance_percent: float = 0.0
    status: str = "enrolled"
    acta_number: Optional[str] = None
    model_config = orm_config


class AcademicTranscriptSubject(BaseModel):
    offering_id: Optional[UUID] = None
    subject_code: str
    subject_name: str
    credits: int
    period_code: str
    final_grade: float
    passed: bool
    status: str


class AcademicTranscriptSummary(BaseModel):
    persona_id: UUID
    student_name: str
    total_credits_attempted: int
    total_credits_earned: int
    weighted_gpa: float  # Promedio Ponderado Acumulado por Créditos
    subjects: List[AcademicTranscriptSubject] = Field(default_factory=list)

class AcademyStudentEnrollmentCreate(BaseModel):
    persona_id: UUID

class AcademyStudentEnrollmentRead(BaseModel):
    id: UUID
    offering_id: UUID
    persona_id: UUID
    enrolled_by_persona_id: UUID
    enrolled_at: datetime
    status: str
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Tutor Socrático & Defensas Interactivas ───────────────────────────────────

class SocraticQueryRequest(BaseModel):
    question: str = Field(min_length=1, description="Pregunta o consulta del estudiante")
    context: Optional[str] = Field(default=None, description="Contexto temático o lección relacionada")


class SocraticQueryResponse(BaseModel):
    session_id: UUID
    offering_id: UUID
    student_id: UUID
    question: str
    socratic_response: str
    session_type: str = "tutor"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DefenseStartRequest(BaseModel):
    submission_id: Optional[UUID] = Field(default=None, description="ID de la entrega a defender (opcional)")


class DefenseSessionStatusResponse(BaseModel):
    id: UUID
    offering_id: Optional[UUID] = None
    submission_id: Optional[UUID] = None
    student_id: UUID
    status: str
    score: Optional[float] = None
    duration_seconds: int = 300
    current_question_index: int = 0
    total_questions: int = 0
    current_question: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    time_remaining_seconds: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DefenseAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, description="Respuesta del estudiante a la pregunta socrática actual")


class DefenseAnswerResponse(BaseModel):
    session_id: UUID
    status: str
    current_question_index: int
    total_questions: int
    next_question: Optional[str] = None
    is_completed: bool = False
    score: Optional[float] = None
    feedback: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DefenseCloseResponse(BaseModel):
    session_id: UUID
    status: str
    score: float
    feedback: str
    ended_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Grafo de Conocimiento & Portafolio Verificable ────────────────────────────

class KnowledgeNodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255, description="Título del nodo de conocimiento")
    description: Optional[str] = Field(default=None, description="Descripción del concepto, habilidad o competencia")
    node_type: str = Field(default="concept", description="Tipo de nodo: concept, skill, competency")
    weight: float = Field(default=1.0, ge=0.0, description="Ponderación del nodo en la asignatura")


class KnowledgeNodeRead(BaseModel):
    id: UUID
    offering_id: UUID
    title: str
    description: Optional[str] = None
    node_type: str
    weight: float
    created_at: datetime
    deleted_at: Optional[datetime] = None
    sede_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeEdgeCreate(BaseModel):
    source_node_id: UUID = Field(description="ID del nodo origen / prerrequisito")
    target_node_id: UUID = Field(description="ID del nodo destino")
    edge_type: str = Field(default="requires", description="Tipo de relación: requires, leads_to, related")
    weight: float = Field(default=1.0, ge=0.0, description="Peso de la conexión")


class KnowledgeEdgeRead(BaseModel):
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: str
    weight: float
    created_at: datetime
    deleted_at: Optional[datetime] = None
    sede_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeGraphResponse(BaseModel):
    offering_id: UUID
    nodes: List[KnowledgeNodeRead]
    edges: List[KnowledgeEdgeRead]


class StudentNodeProgressRead(BaseModel):
    id: UUID
    student_id: UUID
    node_id: UUID
    mastery_score: float
    attempts: int
    last_evaluated_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeEvaluateRequest(BaseModel):
    response_text: Optional[str] = Field(default=None, description="Respuesta o argumentación del estudiante")
    mastery_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Puntaje de dominio opcional")


class NodeEvaluateResponse(BaseModel):
    node_id: UUID
    student_id: UUID
    mastery_score: float
    attempts: int
    feedback: str
    last_evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningPathNode(BaseModel):
    node_id: UUID
    title: str
    node_type: str
    mastery_score: float
    status: str
    order_index: int


class LearningPathResponse(BaseModel):
    offering_id: UUID
    student_id: UUID
    current_average_mastery: float
    path: List[LearningPathNode]
    suggested_next_node: Optional[LearningPathNode] = None


class PortfolioEntryCreate(BaseModel):
    offering_id: Optional[UUID] = Field(default=None, description="Comisión académica asociada (opcional)")
    entry_type: str = Field(default="project", description="Tipo: project, defense, certification, grade")
    title: str = Field(min_length=1, max_length=255, description="Título del logro o evidencia")
    description: Optional[str] = Field(default=None, description="Descripción detallada del artefacto")
    evidence_url: Optional[str] = Field(default=None, max_length=500, description="Enlace a la evidencia")
    score: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Calificación cuantitativa")
    is_public: bool = Field(default=False, description="Visibilidad en el portafolio público")


class PortfolioEntryRead(BaseModel):
    id: UUID
    student_id: UUID
    offering_id: Optional[UUID] = None
    entry_type: str
    title: str
    description: Optional[str] = None
    evidence_url: Optional[str] = None
    score: Optional[float] = None
    issued_at: datetime
    credential_hash: Optional[str] = None
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioPublishToggleResponse(BaseModel):
    id: UUID
    is_public: bool
    message: str


class PortfolioVerifyResponse(BaseModel):
    entry_id: UUID
    is_valid: bool
    credential_hash: Optional[str] = None
    calculated_hash: str
    issued_at: datetime
    student_id: UUID


# =============================================================================
# WELLNESS & COPILOT SCHEMAS (Hito 3 - Campus OS Cognitivo)
# =============================================================================

class WellnessSignalCreate(BaseModel):
    student_id: UUID
    offering_id: Optional[UUID] = None
    signal_type: str = Field(description="engagement_drop, grade_risk, absence_pattern, stress_indicator")
    severity: str = Field(default="medium", description="low, medium, high, critical")
    details: Optional[Dict[str, Any]] = None


class WellnessSignalRead(BaseModel):
    id: UUID
    student_id: UUID
    offering_id: Optional[UUID] = None
    signal_type: str
    severity: str
    detected_at: datetime
    details: Optional[Dict[str, Any]] = None
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[UUID] = None
    created_at: datetime
    student_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WellnessAlertRead(BaseModel):
    id: UUID
    signal_id: UUID
    recipient_id: UUID
    message: str
    sent_at: datetime
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WellnessDetectRequest(BaseModel):
    offering_id: UUID


class WellnessDetectResponse(BaseModel):
    detected_count: int
    signals: List[WellnessSignalRead]
    summary: str


class StudentRiskProfileResponse(BaseModel):
    student_id: UUID
    risk_score: float
    risk_level: str
    active_signals_count: int
    signals: List[WellnessSignalRead]
    recommendations: List[str]


class CopilotActivityItem(BaseModel):
    activity_type: str
    title: str
    description: str
    estimated_duration_minutes: int
    aligned_nodes: List[str] = Field(default_factory=list)


class CopilotActivitySuggestionRequest(BaseModel):
    offering_id: UUID
    topic: str


class CopilotActivitySuggestionResponse(BaseModel):
    offering_id: UUID
    topic: str
    suggestions: List[CopilotActivityItem]


class CopilotRubricCriterion(BaseModel):
    criterion: str
    weight: float
    levels: Dict[str, str]


class CopilotRubricRequest(BaseModel):
    title: str
    competencies: List[str]


class CopilotRubricResponse(BaseModel):
    title: str
    competencies: List[str]
    criteria: List[CopilotRubricCriterion]


class CopilotClassPerformanceRequest(BaseModel):
    offering_id: UUID


class CopilotClassPerformanceResponse(BaseModel):
    offering_id: UUID
    total_students: int
    average_grade: float
    grade_distribution: Dict[str, int]
    weak_knowledge_nodes: List[Dict[str, Any]]
    at_risk_students: List[Dict[str, Any]]
    pedagogical_recommendations: List[str]


class CopilotWeeklyReportResponse(BaseModel):
    offering_id: UUID
    week_period: str
    total_enrolled: int
    average_attendance_percent: float
    grades_summary: Dict[str, Any]
    wellness_alerts_count: int
    active_wellness_signals: List[WellnessSignalRead]
    knowledge_graph_progress_percent: float
    key_highlights: List[str]


class AchievementCreate(BaseModel):
    code: str = Field(max_length=100)
    title: str = Field(max_length=200)
    description: Optional[str] = None
    achievement_type: str = "milestone"
    points: int = 10
    badge_icon: Optional[str] = "award"
    is_active: bool = True
    sede_id: Optional[UUID] = None


class AchievementRead(BaseModel):
    id: UUID
    code: str
    title: str
    description: Optional[str] = None
    achievement_type: str
    points: int
    badge_icon: Optional[str] = None
    is_active: bool
    sede_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentAchievementAwardRequest(BaseModel):
    student_id: UUID
    achievement_id: UUID
    offering_id: Optional[UUID] = None
    evidence: Optional[Dict[str, Any]] = None


class StudentAchievementRead(BaseModel):
    id: UUID
    student_id: UUID
    achievement_id: UUID
    offering_id: Optional[UUID] = None
    earned_at: datetime
    evidence: Optional[Dict[str, Any]] = None
    credential_hash: Optional[str] = None
    sede_id: Optional[UUID] = None
    achievement: Optional[AchievementRead] = None

    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntryRead(BaseModel):
    id: UUID
    student_id: UUID
    student_name: str
    total_points: int
    rank: Optional[int] = None
    period: str
    offering_id: Optional[UUID] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaderboardRecalculateRequest(BaseModel):
    period: Optional[str] = "2026-Q3"
    offering_id: Optional[UUID] = None


class CredentialVerificationResponse(BaseModel):
    verified: bool
    student_id: UUID
    student_name: str
    achievement_id: UUID
    achievement_title: str
    badge_icon: Optional[str] = None
    points: int
    credential_hash: str
    earned_at: datetime
    is_valid: bool = True


class StudyGroupMemberRead(BaseModel):
    id: UUID
    group_id: UUID
    student_id: UUID
    student_name: str
    role: str
    joined_at: datetime
    sede_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class StudyGroupCreate(BaseModel):
    offering_id: UUID
    name: str = Field(max_length=255)
    description: Optional[str] = None
    max_members: int = 5


class StudyGroupRead(BaseModel):
    id: UUID
    offering_id: UUID
    name: str
    description: Optional[str] = None
    max_members: int
    is_active: bool
    created_by: UUID
    creator_name: Optional[str] = None
    sede_id: Optional[UUID] = None
    created_at: datetime
    members_count: int = 0
    members: List[StudyGroupMemberRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


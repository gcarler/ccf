from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas._common import orm_config

# ── Enums canónicos (validación en borde Pydantic) ────────────────────────────
# Definidos aquí (no en api/academy.py) porque los write schemas los usan.
# Reflejan el vocabulario de String(50) en models_academy_core.py.


class Modality(str, Enum):
    """TKT-051 — vocabulario canónico para ``Course.modality`` (String 50)."""
    ONLINE = "online"
    PRESENTIAL = "presential"
    HYBRID = "hybrid"


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


class Assessment(BaseModel):
    id: UUID
    course_id: Optional[UUID] = None
    title: str = "Assessment"
    description: Optional[str] = None
    min_score: float = 70
    weight: float = 1.0
    questions: List[AssessmentQuestion] = Field(default_factory=list)
    model_config = orm_config


class AssessmentAttempt(BaseModel):
    id: UUID
    enrollment_id: UUID
    assessment_id: UUID
    score: float = 0.0
    passed: bool = False
    created_at: datetime | None = None
    answers: List[AssessmentAnswer] = Field(default_factory=list)
    model_config = orm_config


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


class CourseAttendanceBase(BaseModel):
    enrollment_id: UUID
    status: str = "present"
    session_date: Optional[datetime] = None


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

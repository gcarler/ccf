from __future__ import annotations
from uuid import UUID

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config


class CoursePrerequisiteBase(BaseModel):
    course_id: UUID
    prerequisite_course_id: str


class CoursePrerequisite(CoursePrerequisiteBase):
    id: UUID
    model_config = orm_config


class Course(BaseModel):
    id: UUID
    code: str
    title: str
    description: Optional[str] = None
    modality: str
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
    assessment_id: str
    score: float = 0.0
    passed: bool = False
    created_at: datetime | None = None
    answers: List[AssessmentAnswer] = Field(default_factory=list)
    model_config = orm_config


class AssessmentAnswer(BaseModel):
    id: UUID
    question_id: str
    selected_option_id: Optional[str] = None
    text_response: Optional[str] = None
    is_correct: Optional[bool] = None
    points_awarded: float = 0
    model_config = orm_config


class AssessmentAnswerSubmit(BaseModel):
    question_id: str
    selected_option_id: Optional[str] = None
    text_response: Optional[str] = None


class AssessmentAttemptSubmit(BaseModel):
    submitted_score: Optional[float] = None
    answers: Optional[List[AssessmentAnswerSubmit]] = None


class EnrollmentCreate(BaseModel):
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
    resource_type: str
    model_config = orm_config


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


# Alias usado por api/academy.py
Attendance = CourseAttendance


class AcademyStudentProfile(BaseModel):
    persona_id: UUID
    username: str
    total_progress: float = 0.0
    enrollments_count: int = 0
    certificates_count: int = 0
    active_courses: list[Enrollment] = Field(default_factory=list)
    recent_certificates: list[Certificate] = Field(default_factory=list)


class ForumThreadBase(BaseModel):
    title: str
    category: str


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


class ChatMessage(BaseModel):
    id: UUID
    sender_id: str
    content: str
    created_at: datetime
    model_config = orm_config

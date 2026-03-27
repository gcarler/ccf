from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, create_model

orm_config: ConfigDict = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "estudiante"


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class User(UserBase):
    id: int
    xp: int = 0
    is_active: bool = True
    created_at: datetime
    model_config = orm_config


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class TokenUser(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    xp: int = 0


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TaskSupplyBase(BaseModel):
    item_name: str
    quantity: int = 1
    status: str = "pending"


class TaskSupply(TaskSupplyBase):
    id: int
    task_id: int
    model_config = orm_config


class ProjectTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "normal"
    assignee_id: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)


class ProjectTaskCreate(ProjectTaskBase):
    project_id: int


class ProjectTask(ProjectTaskBase):
    id: int
    project_id: int
    supplies: List[TaskSupply] = Field(default_factory=list)
    model_config = orm_config


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "planning"


class Project(ProjectBase):
    id: int
    created_at: datetime
    tasks: List[ProjectTask] = Field(default_factory=list)
    model_config = orm_config


class Course(BaseModel):
    id: int
    code: str
    title: str
    modality: str
    is_published: bool = True
    created_at: datetime | None = None
    model_config = orm_config


class Lesson(BaseModel):
    id: int
    course_id: int
    title: str
    content: Optional[str] = None
    order_index: int = 0
    model_config = orm_config


class Assessment(BaseModel):
    id: int
    title: str = "Assessment"
    model_config = orm_config


class AssessmentAttempt(BaseModel):
    id: int
    enrollment_id: int
    assessment_id: int
    score: float = 0.0
    submitted_at: datetime | None = None
    model_config = orm_config


class AssessmentAttemptSubmit(BaseModel):
    submitted_score: float


class EnrollmentCreate(BaseModel):
    user_id: int
    course_id: int


class Enrollment(BaseModel):
    id: int
    user_id: int
    course_id: int
    status: str = "active"
    progress_percent: float = 0
    approved: bool = False
    certificate_issued: bool = False
    model_config = orm_config


class Attendance(BaseModel):
    id: int
    enrollment_id: int
    created_at: datetime
    model_config = orm_config


class Certificate(BaseModel):
    id: int
    enrollment_id: int
    certificate_code: str
    issued_at: datetime
    model_config = orm_config


class DashboardMetrics(BaseModel):
    active_students: int = 0
    completion_rate: float = 0
    certificates_issued: int = 0


class PilotReadiness(BaseModel):
    environment_ready: bool
    checklist: List[Dict[str, Any]]


class FormalActaCloseRequest(BaseModel):
    min_grade: float = 70
    min_attendance: float = 75


class FormalActa(BaseModel):
    id: int
    course_id: int
    status: str = "closed"
    created_at: datetime
    model_config = orm_config


class Resource(BaseModel):
    id: int
    lesson_id: int
    title: str
    file_url: str
    resource_type: str
    model_config = orm_config


class AssignmentSubmission(BaseModel):
    id: int
    enrollment_id: int
    lesson_id: int
    file_url: str
    comment: Optional[str] = None
    grade: Optional[float] = None
    teacher_feedback: Optional[str] = None
    created_at: datetime
    model_config = orm_config


class AssignmentSubmissionReview(BaseModel):
    id: int
    enrollment_id: int
    lesson_id: int
    student_name: str
    lesson_title: str
    file_url: str
    comment: Optional[str] = None
    grade: Optional[float] = None
    teacher_feedback: Optional[str] = None
    submitted_at: datetime


class AcademyStudentProfile(BaseModel):
    user_id: int
    enrollments: int = 0
    certificates: int = 0


class ForumThreadBase(BaseModel):
    title: str
    category: str


class ForumThreadCreate(ForumThreadBase):
    author_id: int


class ForumThread(BaseModel):
    id: int
    title: str
    category: str
    author_id: int
    is_resolved: bool = False
    created_at: datetime
    model_config = orm_config


class ChatMessage(BaseModel):
    id: int
    sender_id: int
    content: str
    created_at: datetime
    model_config = orm_config


class UserBadge(BaseModel):
    id: int
    earned_at: datetime
    model_config = orm_config


class MemberCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    family_id: Optional[int] = None
    church_role: str = "Miembro"


class MemberUpdate(BaseModel):
    phone: Optional[str] = None
    church_role: Optional[str] = None


class ConsolidationPipelineCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    source: Optional[str] = None
    stage: str = "new"
    assigned_pastor_id: Optional[int] = None


class ConsolidationPipelineUpdate(BaseModel):
    stage: Optional[str] = None
    assigned_pastor_id: Optional[int] = None


class PastoralCallLogCreate(BaseModel):
    lead_id: int
    pastor_id: int
    outcome: str


class AgentTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    source: Optional[str] = None


class AgentTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class AgentTask(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    source: Optional[str] = None
    created_at: datetime
    model_config = orm_config


class AgentInsightCreate(BaseModel):
    title: str
    insight_type: str
    payload: str


class AgentInsight(BaseModel):
    id: int
    title: str
    insight_type: str
    payload: str
    acknowledged: bool = False
    created_at: datetime
    model_config = orm_config


class AdminAuditLog(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    model_config = orm_config


class Notification(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    is_read: bool = False
    created_at: datetime
    model_config = orm_config


class CommunicationLogCreate(BaseModel):
    member_id: int
    channel: str
    content: str
    leader_id: Optional[int] = None
    outcome: str = "sent"


class CommunicationLog(BaseModel):
    id: int
    member_id: int
    channel: str
    content: str
    leader_id: Optional[int] = None
    outcome: str = "sent"
    created_at: datetime
    model_config = orm_config


class PageContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class MilestoneCreate(BaseModel):
    person_id: int
    type: str
    event_date: date


class Milestone(BaseModel):
    id: int
    person_id: int
    type: str
    event_date: date
    created_at: datetime
    model_config = orm_config


class SupportTicketCreate(BaseModel):
    subject: str
    description: str


class SupportTicket(BaseModel):
    id: int
    subject: str
    description: str
    status: str = "open"
    model_config = orm_config


class DonationCreate(BaseModel):
    amount: float
    donor_name: Optional[str] = None


class Donation(BaseModel):
    id: int
    amount: float
    donor_name: Optional[str] = None
    created_at: datetime
    model_config = orm_config


class CommunityBoardCardCreate(BaseModel):
    title: str
    body: Optional[str] = None


class CommunityBoardCard(BaseModel):
    id: int
    title: str
    body: Optional[str] = None
    created_at: datetime
    model_config = orm_config


class PastorRadarSchema(BaseModel):
    membresia_viva: int = 0
    bautismos_este_anio: int = 0
    estudiantes_activos: int = 0
    recaudacion_mes: float = 0


_dynamic_schema_cache: dict[str, type[BaseModel]] = {}


def __getattr__(name: str):
    if name.startswith("__"):
        raise AttributeError(name)
    cached = _dynamic_schema_cache.get(name)
    if cached is not None:
        return cached
    dynamic_model = create_model(name, __config__=ConfigDict(extra="allow", from_attributes=True))
    _dynamic_schema_cache[name] = dynamic_model
    return dynamic_model

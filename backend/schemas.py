from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Annotated
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator


orm_config: ConfigDict = ConfigDict(from_attributes=True)


# -----------------
# Auth & Users
# -----------------
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario ??nico para la plataforma")
    email: EmailStr = Field(..., description="Correo electr??nico institucional o personal")
    role: str = Field("estudiante", description="Rol del usuario (admin, staff, pastor, estudiante)")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Contrase??a de acceso (m??nimo 8 caracteres)")


class User(UserBase):
    id: int
    is_active: bool
    is_email_verified: bool = False
    created_at: datetime

    model_config = orm_config


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class TokenUser(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: str
    xp: int = 0
    is_email_verified: Optional[bool] = None


class Level(BaseModel):
    id: int
    title: str
    min_xp: int
    icon_key: Optional[str] = None

    model_config = orm_config


class Badge(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    icon_key: str
    xp_reward: int

    model_config = orm_config


class UserBadge(BaseModel):
    id: int
    badge: Badge
    earned_at: datetime

    model_config = orm_config


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class RefreshToken(BaseModel):
    id: int
    user_id: int
    token: str
    expires_at: datetime
    revoked: bool

    model_config = orm_config


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str


class EmailVerificationConfirm(BaseModel):
    token: str


class EmailVerificationResend(BaseModel):
    email: Optional[EmailStr] = None


# -----------------
# Governance & Audit
# -----------------
class AdminAuditLog(BaseModel):
    id: int
    actor_user_id: int
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    action_data: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = orm_config


# -----------------
# Testimonials
# -----------------
class TestimonialBase(BaseModel):
    content: str = Field(..., min_length=10)
    emotion: Optional[str] = None
    show_on_home: bool = False


class TestimonialCreate(TestimonialBase):
    author_id: int


class Testimonial(TestimonialBase):
    id: int
    author_id: int
    is_approved: bool
    created_at: datetime
    author: Optional[TokenUser] = None

    model_config = orm_config


class TestimonialUpdate(BaseModel):
    is_approved: Optional[bool] = None
    content: Optional[str] = None
    show_on_home: Optional[bool] = None


# -----------------
# Courses & Lessons
# -----------------
class ResourceBase(BaseModel):
    title: str
    file_url: str
    resource_type: str
    lesson_id: Optional[int] = None
    course_id: Optional[int] = None


class Resource(ResourceBase):
    id: int
    created_at: datetime

    model_config = orm_config


class LessonBase(BaseModel):
    title: str = Field(..., min_length=5)
    content: str
    order_index: int = 0
    duration_minutes: int = 0


class LessonCreate(LessonBase):
    course_id: int


class Lesson(LessonBase):
    id: int
    course_id: int
    created_at: datetime
    resources: List[Resource] = []

    model_config = orm_config


class CourseBase(BaseModel):
    code: str = Field(..., pattern=r'^[A-Z0-9-]+$', description="C??digo ??nico alfanum??rico del curso")
    title: str = Field(..., min_length=5, description="Nombre oficial del curso")
    description: Optional[str] = None
    modality: str = Field(..., description="Modalidad: 'formal' o 'no_formal'")
    is_published: bool = True
    is_self_paced: bool = False
    duration_hours: int = Field(0, ge=0)
    cohort_name: Optional[str] = None
    certificate_type: Optional[str] = None


class CourseCreate(CourseBase):
    pass


class Course(CourseBase):
    id: int
    created_at: datetime
    lessons: List[Lesson] = []

    model_config = orm_config


class CoursePrerequisite(BaseModel):
    id: int
    course_id: int
    prerequisite_course_id: int

    model_config = orm_config


# -----------------
# Enrollments & Assessments
# -----------------
class EnrollmentBase(BaseModel):
    user_id: str
    course_id: int


class EnrollmentCreate(EnrollmentBase):
    pass


class Enrollment(EnrollmentBase):
    id: int
    status: str
    progress_percent: float
    final_grade: Optional[float] = None
    attendance_percent: float
    approved: bool
    acta_closed: bool
    certificate_issued: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    course: Optional[Course] = None

    model_config = orm_config


class QuestionOptionBase(BaseModel):
    option_text: str
    is_correct: bool = False


class QuestionOptionCreate(QuestionOptionBase):
    question_id: int


class QuestionOption(QuestionOptionBase):
    id: int
    question_id: int

    model_config = orm_config


class AssessmentQuestionBase(BaseModel):
    question_text: str
    question_type: str = "multiple_choice"
    points: float = 1.0
    order_index: int = 0


class AssessmentQuestionCreate(AssessmentQuestionBase):
    assessment_id: int


class AssessmentQuestion(AssessmentQuestionBase):
    id: int
    assessment_id: int
    options: List[QuestionOption] = []

    model_config = orm_config


class AssessmentBase(BaseModel):
    title: str = Field(..., min_length=5, description="T??tulo descriptivo de la evaluaci??n")
    description: Optional[str] = Field(None, description="Instrucciones detalladas para el estudiante")
    max_score: float = Field(100.0, ge=0, description="Puntaje m??ximo alcanzable")
    passing_score: float = Field(70.0, ge=0, description="Puntaje m??nimo para aprobar")
    is_published: bool = True

    @model_validator(mode='after')
    def validate_scores(self) -> 'AssessmentBase':
        if self.passing_score > self.max_score:
            raise ValueError('El puntaje de aprobaci??n no puede ser mayor al puntaje m??ximo')
        return self


class AssessmentCreate(AssessmentBase):
    course_id: int


class Assessment(AssessmentBase):
    id: int
    course_id: int
    created_at: datetime
    questions: List[AssessmentQuestion] = []

    model_config = orm_config


class AssessmentAttemptSubmit(BaseModel):
    submitted_score: float


class AssessmentAttempt(BaseModel):
    id: int
    assessment_id: int
    enrollment_id: int
    submitted_score: float
    passed: bool
    created_at: datetime

    model_config = orm_config


class AssignmentSubmissionBase(BaseModel):
    enrollment_id: int
    lesson_id: int
    file_url: str
    comment: Optional[str] = None
    grade: Optional[float] = None
    teacher_feedback: Optional[str] = None


class AssignmentSubmission(AssignmentSubmissionBase):
    id: int
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


class FormalActaCloseRequest(BaseModel):
    min_grade: float = 70
    min_attendance: float = 80


class FormalActa(BaseModel):
    id: int
    course_id: int
    cohort_name: Optional[str]
    closed_by_user_id: int
    min_grade: float
    min_attendance: float
    created_at: datetime

    model_config = orm_config


class Certificate(BaseModel):
    id: int
    enrollment_id: int
    certificate_code: str
    certificate_type: Optional[str]
    issued_at: datetime

    model_config = orm_config


class MetricCard(BaseModel):
    title: str
    value: str
    trend: str
    tone: str

class DashboardMetrics(BaseModel):
    total_courses: int
    formal_courses: int
    non_formal_courses: int
    total_enrollments: int
    completed_enrollments: int
    approved_formal_enrollments: int
    approved_non_formal_enrollments: int
    cards: Optional[List[MetricCard]] = None


class PilotChecklistItem(BaseModel):
    key: str
    label: str
    completed: bool


class PilotReadiness(BaseModel):
    environment_ready: bool
    kpi_dashboard_ready: bool
    support_ready: bool
    security_ready: bool
    readiness_score: float
    checklist: List[PilotChecklistItem]


# -----------------
# Families & CRM
# -----------------
class FamilyBase(BaseModel):
    name: str


class FamilyCreate(FamilyBase):
    pass


class Family(FamilyBase):
    id: int
    created_at: datetime

    model_config = orm_config


class MemberBase(BaseModel):
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$', description="Tel??fono en formato E.164")
    role_in_family: Optional[str] = Field(None, description="Padre, Madre, Hijo, etc.")
    church_role: Optional[str] = "Miembro"
    birthday: Optional[datetime] = None
    family_id: Optional[int] = None
    user_id: Optional[int] = None


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role_in_family: Optional[str] = None
    church_role: Optional[str] = None
    birthday: Optional[datetime] = None
    family_id: Optional[int] = None
    user_id: Optional[int] = None


class Member(MemberBase):
    id: int
    qr_token: str
    created_at: datetime

    model_config = orm_config


class MemberAcademyProfile(BaseModel):
    is_linked: bool
    username: Optional[str] = None
    enrollments: List[Enrollment] = []


class EventBase(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: str
    day_of_week: Optional[int] = None
    month_day: Optional[str] = None
    fixed_date: Optional[datetime] = None


class EventCreate(EventBase):
    pass


class Event(EventBase):
    id: int
    created_at: datetime

    model_config = orm_config


class Attendance(BaseModel):
    id: int
    member_id: Optional[int]
    event_id: Optional[int]
    enrollment_id: Optional[int]
    attendance_date: datetime
    status: str

    model_config = orm_config


class AttendanceCreate(BaseModel):
    member_id: Optional[int] = None
    event_id: Optional[int] = None
    enrollment_id: Optional[int] = None
    attendance_date: datetime
    status: str = "attended"


class VolunteerBase(BaseModel):
    member_id: Optional[int] = None
    name: str
    role: str
    assigned_event: str
    status: str = "Pendiente"


class VolunteerCreate(VolunteerBase):
    pass


class Volunteer(VolunteerBase):
    id: int
    created_at: datetime

    model_config = orm_config


class ConsolidationPipelineBase(BaseModel):
    first_name: str
    last_name: str
    phone: str
    source: str
    stage: str = "new"
    notes: Optional[str] = None
    prayer_requests: Optional[str] = None
    assigned_pastor_id: Optional[int] = None
    is_automation_paused: bool = False


class ConsolidationPipelineCreate(ConsolidationPipelineBase):
    pass


class ConsolidationPipelineUpdate(BaseModel):
    stage: Optional[str] = None
    notes: Optional[str] = None
    prayer_requests: Optional[str] = None
    assigned_pastor_id: Optional[int] = None
    is_automation_paused: Optional[bool] = None


class ConsolidationPipeline(ConsolidationPipelineBase):
    id: int
    created_at: datetime

    model_config = orm_config


class ConsolidationAutomationBase(BaseModel):
    stage: str
    delay_days: int
    channel: str
    template: str
    is_active: bool = True


class ConsolidationAutomationCreate(ConsolidationAutomationBase):
    pass


class ConsolidationAutomationUpdate(BaseModel):
    stage: Optional[str] = None
    delay_days: Optional[int] = None
    channel: Optional[str] = None
    template: Optional[str] = None
    is_active: Optional[bool] = None


class ConsolidationAutomation(ConsolidationAutomationBase):
    id: int
    created_at: datetime

    model_config = orm_config


class PastoralCallLogBase(BaseModel):
    lead_id: int
    pastor_id: int
    outcome: str
    notes: Optional[str] = None
    prayer_requests: Optional[str] = None


class PastoralCallLogCreate(PastoralCallLogBase):
    pass


class PastoralCallLog(PastoralCallLogBase):
    id: int
    created_at: datetime

    model_config = orm_config


class CommunicationLogBase(BaseModel):
    member_id: int
    channel: str
    content: str
    outcome: Optional[str] = None
    leader_id: Optional[int] = None
    follow_up_date: Optional[datetime] = None


class CommunicationLogCreate(CommunicationLogBase):
    pass


class CommunicationLog(CommunicationLogBase):
    id: int
    created_at: datetime

    model_config = orm_config


class CrmSettingsBase(BaseModel):
    church_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    timezone: Optional[str] = None
    enable_whatsapp: Optional[bool] = None
    enable_sms: Optional[bool] = None
    twilio_api_key: Optional[str] = None
    smtp_server: Optional[str] = None


class CrmSettingsUpdate(CrmSettingsBase):
    pass


class CrmSettings(CrmSettingsBase):
    id: int
    updated_at: datetime

    model_config = orm_config


class GloryHouseBase(BaseModel):
    name: str
    zone: str
    leader_name: str
    members_count: int = 0
    schedule: str
    status: str = "Activo"


class GloryHouseCreate(GloryHouseBase):
    pass


class GloryHouse(GloryHouseBase):
    id: int
    created_at: datetime

    model_config = orm_config


# -----------------
# CMS & Content
# -----------------
class AnnouncementBase(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    category: str = "General"
    is_active: bool = True


class AnnouncementCreate(AnnouncementBase):
    pass


class Announcement(AnnouncementBase):
    id: int
    created_at: datetime

    model_config = orm_config


class SermonBase(BaseModel):
    title: str
    description: Optional[str] = None
    preacher: str
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[str] = None
    date: datetime


class SermonCreate(SermonBase):
    pass


class Sermon(SermonBase):
    id: int
    created_at: datetime

    model_config = orm_config


class BookBase(BaseModel):
    title: str
    description: Optional[str] = None
    author: str
    cover_image_url: Optional[str] = None
    download_url: Optional[str] = None
    is_published: bool = True


class BookCreate(BookBase):
    pass


class Book(BookBase):
    id: int
    created_at: datetime

    model_config = orm_config


class NavigationItemBase(BaseModel):
    label: str
    href: str
    icon: Optional[str] = None
    target: str = "main"
    order_index: int = 0
    parent_id: Optional[int] = None
    is_active: bool = True


class NavigationItemCreate(NavigationItemBase):
    pass


class NavigationItem(NavigationItemBase):
    id: int
    children: List["NavigationItem"] = []

    model_config = orm_config


class PageContentBase(BaseModel):
    page_key: str
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None


class PageContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None


class PageContent(PageContentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = orm_config


class PageContentVersion(BaseModel):
    id: int
    page_content_id: int
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime

    model_config = orm_config


# -----------------
# Counseling & Donations
# -----------------
class CounselingSessionBase(BaseModel):
    pastor_id: int
    member_id: Optional[int] = None
    lead_id: Optional[int] = None
    scheduled_at: datetime
    duration_minutes: int = 60
    status: str = "Pendiente"
    topic: Optional[str] = None
    summary: Optional[str] = None
    confidential_notes: Optional[str] = None


class CounselingSessionCreate(CounselingSessionBase):
    pass


class CounselingSession(CounselingSessionBase):
    id: int
    created_at: datetime

    model_config = orm_config


class CounselingSessionUpdate(BaseModel):
    status: Optional[str] = None
    summary: Optional[str] = None
    confidential_notes: Optional[str] = None


class DonationBase(BaseModel):
    amount: float = Field(..., gt=0, description="Monto de la donaci??n (debe ser mayor a 0)")
    currency: str = Field("USD", min_length=3, max_length=3)
    donor_name: Optional[str] = None
    donor_email: Optional[EmailStr] = None
    donation_type: str = "Ofrenda General"
    status: str = "completada"


class DonationCreate(DonationBase):
    pass


class Donation(DonationBase):
    id: int
    created_at: datetime

    model_config = orm_config


class TreasuryTransactionBase(BaseModel):
    type: str  # income, expense
    category: str
    amount: float
    currency: str = "USD"
    description: str
    date: Optional[datetime] = None
    attachment_url: Optional[str] = None
    status: str = "completed"


class TreasuryTransactionCreate(TreasuryTransactionBase):
    recorded_by_id: int


class TreasuryTransaction(TreasuryTransactionBase):
    id: int
    recorded_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = orm_config


# -----------------
# Agent capabilities
# -----------------
class CapabilityBase(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    tools_schema: Optional[str] = None
    input_metadata: Optional[str] = None
    output_metadata: Optional[str] = None
    is_active: bool = True


class CapabilityCreate(CapabilityBase):
    pass


class Capability(CapabilityBase):
    id: int
    last_registered_at: datetime

    model_config = orm_config


class MediaAssetBase(BaseModel):
    filename: str
    url: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None


class MediaAsset(MediaAssetBase):
    id: int
    created_at: datetime

    model_config = orm_config


class ContentMetric(BaseModel):
    id: int
    content_type: str
    content_id: int
    metric_type: str
    value: int
    updated_at: datetime

    model_config = orm_config


class ContentMetricIncrement(BaseModel):
    metric_type: str = "view"
    amount: int = 1


class AgentTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    assignee: Optional[str] = None
    source: str = "agent"
    extra: Optional[str] = None


class AgentTaskCreate(AgentTaskBase):
    pass


class AgentTask(AgentTaskBase):
    id: int
    status: str
    created_at: datetime

    model_config = orm_config


class AgentTaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    acknowledged: Optional[bool] = None
    extra: Optional[str] = None


class AgentInsightBase(BaseModel):
    title: str
    insight_type: str
    payload: str


class AgentInsightCreate(AgentInsightBase):
    pass


class AgentInsight(AgentInsightBase):
    id: int
    acknowledged: bool
    created_at: datetime

    model_config = orm_config


# -----------------
# Prayer & Support
# -----------------
class PrayerRequestBase(BaseModel):
    name: str
    request: str
    category: str = "General"
    is_anonymous: bool = False


class PrayerRequestCreate(PrayerRequestBase):
    user_id: Optional[int] = None


class PrayerRequest(PrayerRequestBase):
    id: int
    user_id: Optional[int]
    is_answered: bool
    created_at: datetime

    model_config = orm_config


class SupportTicketBase(BaseModel):
    subject: str
    description: str
    priority: str = "media"
    category: str = "Tecnico"


class SupportTicketCreate(SupportTicketBase):
    user_id: int


class SupportTicket(SupportTicketBase):
    id: int
    user_id: int
    status: str
    created_at: datetime

    model_config = orm_config


# -----------------
# Academy Profile
# -----------------
class AcademyStudentProfile(BaseModel):
    user_id: int
    username: str
    total_progress: float
    enrollments_count: int
    certificates_count: int
    active_courses: List[Enrollment]
    recent_certificates: List[Certificate]


# -----------------
# Projects & Tasks
# -----------------
class ProjectTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    order_index: int = 0


class ProjectTaskCreate(ProjectTaskBase):
    project_id: int


class ProjectTask(ProjectTaskBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    subtasks: List["ProjectTask"] = []

    model_config = orm_config


class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "active"
    color: Optional[str] = None
    icon: Optional[str] = None


class ProjectCreate(ProjectBase):
    owner_id: int


class Project(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    tasks: List[ProjectTask] = []

    model_config = orm_config


class NotificationBase(BaseModel):
    title: str
    content: str
    notif_type: str = "system"
    link_url: Optional[str] = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime

    model_config = orm_config


# -----------------
# Community Hub
# -----------------
class CommunityBoardCardBase(BaseModel):
    column_id: str
    name: str
    stage: str
    owner: str
    due_date: Optional[datetime] = None
    priority: str = "Media"
    status: str = "Pendiente"
    comments: Optional[str] = None
    link: Optional[str] = None


class CommunityBoardCardCreate(CommunityBoardCardBase):
    pass


class CommunityBoardCard(CommunityBoardCardBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = orm_config


# -----------------
# Workspace Config
# -----------------
class WorkspaceConfigBase(BaseModel):
    features_enabled: dict = {}
    ui_theme_config: dict = {}
    navigation_schema: List[dict] = []
    is_active: bool = True


class WorkspaceConfigUpdate(BaseModel):
    features_enabled: Optional[dict] = None
    ui_theme_config: Optional[dict] = None
    navigation_schema: Optional[List[dict]] = None
    is_active: Optional[bool] = None


class WorkspaceConfig(WorkspaceConfigBase):
    id: int
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = orm_config

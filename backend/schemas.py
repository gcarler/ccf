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


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    xp: Optional[int] = None


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


class TaskSupplyCreate(TaskSupplyBase):
    pass


class TaskSupplyUpdate(BaseModel):
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None


class TaskSupply(TaskSupplyBase):
    id: int
    task_id: int
    model_config = orm_config

class ProjectAttachment(BaseModel):
    id: int
    task_id: int
    filename: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
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
    attachments: List[Any] = Field(default_factory=list)


class ProjectTaskCreate(ProjectTaskBase):
    project_id: Optional[int] = None


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None


class ProjectTask(ProjectTaskBase):
    id: int
    project_id: int
    parent_id: Optional[int] = None
    order_index: int = 0
    supplies: List[TaskSupply] = Field(default_factory=list)
    subtasks: List["ProjectTask"] = Field(default_factory=list)
    model_config = orm_config


class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "planning"
    owner_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    whiteboard_data: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    whiteboard_data: Optional[str] = None


class ProjectMilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    is_completed: bool = False

class ProjectMilestone(ProjectMilestoneBase):
    id: int
    project_id: int
    model_config = orm_config

class ProjectActivityLog(BaseModel):
    id: int
    project_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = "Sistema"
    action_type: str
    description: str
    created_at: Optional[datetime] = None
    model_config = orm_config

class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tasks: List[ProjectTask] = Field(default_factory=list)
    milestones: List[ProjectMilestone] = Field(default_factory=list)
    activities: List[ProjectActivityLog] = Field(default_factory=list)
    progress_percent: int = 0
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Map ORM activity_logs relationship -> activities field
        if hasattr(obj, 'activity_logs') and not isinstance(obj, dict):
            obj.__dict__.setdefault('activities', list(obj.activity_logs or []))
        instance = super().model_validate(obj, **kwargs)
        # Calculate progress from tasks if not set on model
        if hasattr(obj, 'tasks') and obj.tasks:
            done = sum(1 for t in obj.tasks if getattr(t, 'status', '') == 'done')
            instance.progress_percent = round((done / len(obj.tasks)) * 100)
        return instance


class ProjectInboxItem(BaseModel):
    id: str
    type: str
    user: str
    content: str
    project: str
    project_id: int
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    is_read: bool = False
    created_at: datetime


class ProjectActivityItem(BaseModel):
    id: str
    kind: str
    project_id: int
    project_title: str
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    description: str
    created_at: datetime


class ProjectCommentBase(BaseModel):
    content: str
    task_id: Optional[int] = None


class ProjectCommentCreate(ProjectCommentBase):
    pass


class ProjectCommentUpdate(BaseModel):
    content: Optional[str] = None
    is_resolved: Optional[bool] = None


class ProjectCommentItem(ProjectCommentBase):
    id: int
    project_id: int
    author_id: int
    author_name: str
    is_resolved: bool = False
    created_at: datetime
    updated_at: datetime


class InboxReadToggle(BaseModel):
    is_read: bool = True


class ProjectPortfolioSummaryRow(BaseModel):
    project_status: str
    total_projects: int
    total_tasks: int
    completed_tasks: int
    completion_ratio: float


class ProjectWorkloadSummaryRow(BaseModel):
    assignee_id: Optional[int] = None
    open_tasks: int
    in_review: int
    overdue_tasks: int


ProjectTask.model_rebuild()


class CoursePrerequisiteBase(BaseModel):
    course_id: int
    prerequisite_course_id: int

class CoursePrerequisite(CoursePrerequisiteBase):
    id: int
    model_config = orm_config

class Course(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    modality: str
    is_published: bool = True
    created_at: datetime | None = None
    prerequisites: List[CoursePrerequisite] = Field(default_factory=list)
    lesson_count: int = 0
    total_minutes: int = 0
    model_config = orm_config


class Lesson(BaseModel):
    id: int
    course_id: int
    title: str
    content: Optional[str] = None
    content_type: str = "video"
    media_url: Optional[str] = None
    order_index: int = 0
    duration_minutes: int = 0
    model_config = orm_config


class AssessmentOption(BaseModel):
    id: int
    option_text: str
    model_config = orm_config


class AssessmentQuestion(BaseModel):
    id: int
    question_text: str
    question_type: str
    points: int
    options: List[AssessmentOption] = Field(default_factory=list)
    model_config = orm_config


class Assessment(BaseModel):
    id: int
    title: str = "Assessment"
    min_score: float = 70
    weight: float = 1.0
    questions: List[AssessmentQuestion] = Field(default_factory=list)
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


class CourseAttendanceBase(BaseModel):
    enrollment_id: int
    status: str = "present"
    session_date: Optional[datetime] = None


class CourseAttendanceCreate(CourseAttendanceBase):
    pass


class CourseAttendance(CourseAttendanceBase):
    id: int
    recorded_by_id: Optional[int] = None
    model_config = orm_config


class BulkAttendanceRecord(BaseModel):
    enrollment_id: int
    status: str


class BulkAttendanceCreate(BaseModel):
    session_date: datetime
    records: List[BulkAttendanceRecord]


class Certificate(BaseModel):
    id: int
    enrollment_id: int
    certificate_code: str
    issued_at: datetime
    model_config = orm_config


class DashboardMetrics(BaseModel):
    total_courses: int = 0
    total_enrollments: int = 0
    approved_formal_enrollments: int = 0

class PilotReadiness(BaseModel):
    readiness_score: float = 0.0
    checklist: List[Dict[str, Any]] = Field(default_factory=list)


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


class CrmEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    location: Optional[str] = None

class CrmEventCreate(CrmEventBase):
    pass

class CrmEvent(CrmEventBase):
    id: int
    created_at: datetime
    model_config = orm_config

class EventAttendanceBase(BaseModel):
    event_id: int
    member_id: int
    status: str = "present"

class EventAttendanceCreate(EventAttendanceBase):
    pass

class EventAttendance(EventAttendanceBase):
    id: int
    scanned_at: datetime
    model_config = orm_config

class CounselingTicketBase(BaseModel):
    member_id: int
    subject: str
    notes: Optional[str] = None
    status: str = "open"

class CounselingTicketCreate(CounselingTicketBase):
    pastor_id: Optional[int] = None

class CounselingTicket(CounselingTicketBase):
    id: int
    pastor_id: Optional[int] = None
    created_at: datetime
    model_config = orm_config

class PrayerRequestBase(BaseModel):
    requester_name: str
    request_text: str
    is_public: bool = False
    status: str = "pending"

class PrayerRequestCreate(PrayerRequestBase):
    pass

class PrayerRequest(PrayerRequestBase):
    id: int
    created_at: datetime
    model_config = orm_config

class DonationBase(BaseModel):
    member_id: Optional[int] = None
    amount: float
    donation_type: str = "Diezmo"
    fund_id: Optional[int] = None
    donor_name: Optional[str] = None

class DonationCreate(DonationBase):
    pass

class Donation(DonationBase):
    id: int
    created_at: datetime
    model_config = orm_config

class CrmTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    member_id: Optional[int] = None
    lead_id: Optional[int] = None
    assignee_id: int
    due_date: Optional[datetime] = None
    status: str = "todo"
    priority: str = "normal"

class CrmTaskCreate(CrmTaskBase):
    pass

class CrmTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None

class CrmTask(CrmTaskBase):
    id: int
    created_at: datetime
    model_config = orm_config

class VolunteerShiftBase(BaseModel):
    member_id: int
    role_name: str
    team_name: str
    shift_start: datetime
    shift_end: datetime
    status: str = "confirmed"
    notes: Optional[str] = None

class VolunteerShiftCreate(VolunteerShiftBase):
    pass

class VolunteerShift(VolunteerShiftBase):
    id: int
    created_at: datetime
    model_config = orm_config

class Member(BaseModel):
    id: int
    user_id: Optional[int] = None
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: str
    spiritual_status: str
    family_id: Optional[int] = None
    birthday: Optional[datetime] = None
    gender: Optional[str] = None
    spiritual_health: float = 0.8
    academy_progress: float = 0.0
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    created_at: datetime
    model_config = orm_config

class Family(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    members_count: int = 0
    created_at: datetime
    model_config = orm_config

class GloryHouse(BaseModel):
    id: int
    name: str
    zone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    leader_name: Optional[str] = None
    members_count: int
    capacity: int
    status: str
    created_at: datetime
    model_config = orm_config

class GloryHouseCreate(BaseModel):
    name: str
    zone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    leader_name: Optional[str] = None
    capacity: int = 15

class MemberCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = None
    family_id: int = Field(...)
    church_role: str = "Miembro"
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None


class MemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: Optional[str] = None
    spiritual_status: Optional[str] = None
    family_id: Optional[int] = None
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None


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


class PageContentRead(BaseModel):
    id: int
    page_key: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class PageContentVersionRead(BaseModel):
    id: int
    page_key: str
    title: str
    content: str
    created_at: datetime
    model_config = orm_config


class ContentWorkflowUpdate(BaseModel):
    action: str
    notes: Optional[str] = None
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None


class ContentWorkflowRead(BaseModel):
    page_key: str
    status: str
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    last_published_at: Optional[datetime] = None
    notes: Optional[str] = None
    updated_at: datetime


class CmsMetrics(BaseModel):
    total_blocks: int
    draft_blocks: int
    in_review_blocks: int
    approved_blocks: int
    published_blocks: int
    archived_blocks: int
    testimonials_total: int
    testimonials_approved: int
    announcements_total: int
    announcements_active: int


class CmsMediaCreate(BaseModel):
    url: str
    alt_text: Optional[str] = None
    section: str = "general"
    tags: List[str] = Field(default_factory=list)


class CmsMediaUpdate(BaseModel):
    url: Optional[str] = None
    alt_text: Optional[str] = None
    section: Optional[str] = None
    tags: Optional[List[str]] = None


class CmsMediaRead(BaseModel):
    id: int
    url: str
    alt_text: Optional[str] = None
    section: str
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsSiteCreate(BaseModel):
    site_key: str
    name: str
    base_path: str
    is_active: bool = True


class CmsSiteUpdate(BaseModel):
    name: Optional[str] = None
    base_path: Optional[str] = None
    is_active: Optional[bool] = None


class CmsSiteRead(BaseModel):
    id: int
    site_key: str
    name: str
    base_path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsThemeCreate(BaseModel):
    name: str
    tokens_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class CmsThemeUpdate(BaseModel):
    name: Optional[str] = None
    tokens_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class CmsThemeRead(BaseModel):
    id: int
    site_id: int
    name: str
    tokens_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    version: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsMenuCreate(BaseModel):
    menu_key: str
    name: str
    is_active: bool = True


class CmsMenuUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class CmsMenuRead(BaseModel):
    id: int
    site_id: int
    menu_key: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsMenuItemCreate(BaseModel):
    label: str
    href: str
    parent_id: Optional[int] = None
    target: str = "_self"
    is_external: bool = False
    visibility: str = "public"
    sort_order: int = 0
    meta_json: Dict[str, Any] = Field(default_factory=dict)


class CmsMenuItemUpdate(BaseModel):
    label: Optional[str] = None
    href: Optional[str] = None
    parent_id: Optional[int] = None
    target: Optional[str] = None
    is_external: Optional[bool] = None
    visibility: Optional[str] = None
    sort_order: Optional[int] = None
    meta_json: Optional[Dict[str, Any]] = None


class CmsMenuItemReorderItem(BaseModel):
    id: int
    parent_id: Optional[int] = None
    sort_order: int


class CmsMenuItemReorderPayload(BaseModel):
    items: List[CmsMenuItemReorderItem]


class CmsMenuItemRead(BaseModel):
    id: int
    menu_id: int
    parent_id: Optional[int] = None
    label: str
    href: str
    target: str
    is_external: bool
    visibility: str
    sort_order: int
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPageCreate(BaseModel):
    slug: str
    title: str
    status: str = "draft"
    seo_json: Dict[str, Any] = Field(default_factory=dict)


class CmsPageUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    seo_json: Optional[Dict[str, Any]] = None


class CmsPageRead(BaseModel):
    id: int
    site_id: int
    slug: str
    title: str
    status: str
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    published_version_id: Optional[int] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsSectionCreate(BaseModel):
    section_key: Optional[str] = None
    type: str
    props_json: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    is_visible: bool = True


class CmsSectionUpdate(BaseModel):
    type: Optional[str] = None
    props_json: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None


class CmsSectionReorderItem(BaseModel):
    id: int
    sort_order: int


class CmsSectionReorderPayload(BaseModel):
    items: List[CmsSectionReorderItem]


class CmsSectionRead(BaseModel):
    id: int
    page_id: int
    section_key: str
    type: str
    props_json: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int
    is_visible: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPageVersionRead(BaseModel):
    id: int
    page_id: int
    version_number: int
    snapshot_json: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    model_config = orm_config


class CmsWorkflowAction(BaseModel):
    action: str
    notes: Optional[str] = None


class CmsPublicPageRead(BaseModel):
    site_key: str
    slug: str
    title: str
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    sections: List[CmsSectionRead] = Field(default_factory=list)


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

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, ConfigDict


orm_config: ConfigDict = ConfigDict(from_attributes=True)


# -----------------
# Auth & Users
# -----------------
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class TokenUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class RefreshToken(BaseModel):
    id: int
    user_id: int
    token: str
    expires_at: datetime
    revoked: bool

    class Config:
        from_attributes = True


# -----------------
# Testimonials
# -----------------
class TestimonialBase(BaseModel):
    content: str
    emotion: Optional[str] = None


class TestimonialCreate(TestimonialBase):
    author_id: int


class Testimonial(TestimonialBase):
    id: int
    author_id: int
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TestimonialUpdate(BaseModel):
    is_approved: Optional[bool] = None
    content: Optional[str] = None


# -----------------
# Courses & Lessons
# -----------------
class LessonBase(BaseModel):
    title: str
    content: str
    order_index: int = 0
    duration_minutes: int = 0


class LessonCreate(LessonBase):
    course_id: int


class Lesson(LessonBase):
    id: int
    course_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    modality: str
    is_published: bool = True
    is_self_paced: bool = False
    duration_hours: int = 0
    cohort_name: Optional[str] = None
    certificate_type: Optional[str] = None


class CourseCreate(CourseBase):
    pass


class Course(CourseBase):
    id: int
    created_at: datetime
    lessons: List[Lesson] = []

    class Config:
        from_attributes = True


class ResourceBase(BaseModel):
    title: str
    file_url: str
    resource_type: str
    lesson_id: Optional[int] = None
    course_id: Optional[int] = None


class Resource(ResourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CoursePrerequisite(BaseModel):
    id: int
    course_id: int
    prerequisite_course_id: int

    class Config:
        from_attributes = True


# -----------------
# Enrollments & Assessments
# -----------------
class EnrollmentBase(BaseModel):
    user_id: int
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
    course: Course

    class Config:
        from_attributes = True


class AssessmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    max_score: float = 100
    passing_score: float = 70
    is_published: bool = True


class AssessmentCreate(AssessmentBase):
    course_id: int


class Assessment(AssessmentBase):
    id: int
    course_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AssessmentAttemptSubmit(BaseModel):
    submitted_score: float


class AssessmentAttempt(BaseModel):
    id: int
    assessment_id: int
    enrollment_id: int
    submitted_score: float
    passed: bool
    created_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class Certificate(BaseModel):
    id: int
    enrollment_id: int
    certificate_code: str
    certificate_type: Optional[str]
    issued_at: datetime

    class Config:
        from_attributes = True


class DashboardMetrics(BaseModel):
    total_courses: int
    formal_courses: int
    non_formal_courses: int
    total_enrollments: int
    completed_enrollments: int
    approved_formal_enrollments: int
    approved_non_formal_enrollments: int


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

    class Config:
        from_attributes = True


class MemberBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role_in_family: Optional[str] = None
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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class Attendance(BaseModel):
    id: int
    member_id: Optional[int]
    event_id: Optional[int]
    enrollment_id: Optional[int]
    attendance_date: datetime
    status: str

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class PageContentVersion(BaseModel):
    id: int
    page_content_id: int
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class DonationBase(BaseModel):
    amount: float
    currency: str = "USD"
    donor_name: Optional[str] = None
    donor_email: Optional[EmailStr] = None
    donation_type: str = "Ofrenda General"
    status: str = "completada"


class DonationCreate(DonationBase):
    pass


class Donation(DonationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class MediaAssetBase(BaseModel):
    filename: str
    url: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None


class MediaAsset(MediaAssetBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ContentMetric(BaseModel):
    id: int
    content_type: str
    content_id: int
    metric_type: str
    value: int
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True

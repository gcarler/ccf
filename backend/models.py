from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.core.database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="estudiante", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    member = relationship("Member", back_populates="user", uselist=False)
    enrollments = relationship("Enrollment", back_populates="student")
    testimonials = relationship("Testimonial", back_populates="author")


class Testimonial(Base, TimestampMixin):
    __tablename__ = "testimonials"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    emotion = Column(String, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)

    author = relationship("User", back_populates="testimonials")


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    modality = Column(String, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    is_self_paced = Column(Boolean, default=False, nullable=False)
    duration_hours = Column(Integer, default=0, nullable=False)
    cohort_name = Column(String, nullable=True)
    certificate_type = Column(String, nullable=True)

    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course")
    assessments = relationship("Assessment", back_populates="course", cascade="all, delete-orphan")
    actas = relationship("FormalActa", back_populates="course", cascade="all, delete-orphan")


class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    duration_minutes = Column(Integer, default=0, nullable=False)

    course = relationship("Course", back_populates="lessons")
    resources = relationship("Resource", back_populates="lesson", cascade="all, delete-orphan")
    submissions = relationship("AssignmentSubmission", back_populates="lesson", cascade="all, delete-orphan")


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    lesson = relationship("Lesson", back_populates="resources")


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    max_score = Column(Float, default=100, nullable=False)
    passing_score = Column(Float, default=70, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)

    course = relationship("Course", back_populates="assessments")
    attempts = relationship("AssessmentAttempt", back_populates="assessment")


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True, nullable=False)
    status = Column(String, default="active", nullable=False)
    progress_percent = Column(Float, default=0, nullable=False)
    final_grade = Column(Float, nullable=True)
    attendance_percent = Column(Float, default=0, nullable=False)
    approved = Column(Boolean, default=False, nullable=False)
    acta_closed = Column(Boolean, default=False, nullable=False)
    certificate_issued = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    assessment_attempts = relationship("AssessmentAttempt", back_populates="enrollment", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="enrollment", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="enrollment")


class AssessmentAttempt(Base, TimestampMixin):
    __tablename__ = "assessment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), index=True, nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), index=True, nullable=False)
    submitted_score = Column(Float, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)

    assessment = relationship("Assessment", back_populates="attempts")
    enrollment = relationship("Enrollment", back_populates="assessment_attempts")


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True, nullable=False)
    prerequisite_course_id = Column(Integer, ForeignKey("courses.id"), index=True, nullable=False)


class FormalActa(Base, TimestampMixin):
    __tablename__ = "formal_actas"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    cohort_name = Column(String, nullable=True)
    closed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    min_grade = Column(Float, default=70, nullable=False)
    min_attendance = Column(Float, default=80, nullable=False)

    course = relationship("Course", back_populates="actas")


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), index=True, nullable=False)
    certificate_code = Column(String, unique=True, index=True, nullable=False)
    certificate_type = Column(String, nullable=True)
    issued_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    enrollment = relationship("Enrollment", back_populates="certificates")


class Family(Base, TimestampMixin):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)

    members = relationship("Member", back_populates="family")


class Member(Base, TimestampMixin):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, nullable=True)
    role_in_family = Column(String, nullable=True)
    church_role = Column(String, default="Miembro", nullable=False)
    qr_token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)
    birthday = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="member")
    family = relationship("Family", back_populates="members")
    attendances = relationship("Attendance", back_populates="member")


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String, nullable=False)
    day_of_week = Column(Integer, nullable=True)
    month_day = Column(String, nullable=True)
    fixed_date = Column(DateTime, nullable=True)

    attendances = relationship("Attendance", back_populates="event")


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), index=True, nullable=True)
    attendance_date = Column(DateTime, default=dt.datetime.utcnow, index=True, nullable=False)
    status = Column(String, default="attended", nullable=False)

    member = relationship("Member", back_populates="attendances")
    event = relationship("Event", back_populates="attendances")
    enrollment = relationship("Enrollment", back_populates="attendances")


class AssignmentSubmission(Base, TimestampMixin):
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), index=True, nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), index=True, nullable=False)
    file_url = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    grade = Column(Float, nullable=True)
    teacher_feedback = Column(Text, nullable=True)

    enrollment = relationship("Enrollment")
    lesson = relationship("Lesson", back_populates="submissions")


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    category = Column(String, default="General", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Sermon(Base, TimestampMixin):
    __tablename__ = "sermons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    preacher = Column(String, nullable=False)
    video_url = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    date = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    views = Column(Integer, default=0, nullable=False)


class Book(Base, TimestampMixin):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=False)
    cover_image_url = Column(String, nullable=True)
    download_url = Column(String, nullable=True)
    is_published = Column(Boolean, default=True, nullable=False)


class PageContent(Base, TimestampMixin):
    __tablename__ = "page_contents"

    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)


class PageContentVersion(Base, TimestampMixin):
    __tablename__ = "page_content_versions"

    id = Column(Integer, primary_key=True, index=True)
    page_content_id = Column(Integer, ForeignKey("page_contents.id"), nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)

    page_content = relationship("PageContent")


class Volunteer(Base, TimestampMixin):
    __tablename__ = "volunteers"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    assigned_event = Column(String, nullable=False)
    status = Column(String, default="Pendiente", nullable=False)


class ConsolidationPipeline(Base, TimestampMixin):
    __tablename__ = "consolidation_pipeline"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    phone = Column(String, nullable=False)
    source = Column(String, nullable=False)
    stage = Column(String, default="new", nullable=False)
    notes = Column(Text, nullable=True)
    prayer_requests = Column(Text, nullable=True)
    assigned_pastor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_automation_paused = Column(Boolean, default=False, nullable=False)

    call_logs = relationship("PastoralCallLog", back_populates="lead", cascade="all, delete-orphan")


class PastoralCallLog(Base, TimestampMixin):
    __tablename__ = "pastoral_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("consolidation_pipeline.id"), index=True, nullable=False)
    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outcome = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    prayer_requests = Column(Text, nullable=True)

    lead = relationship("ConsolidationPipeline", back_populates="call_logs")


class ConsolidationAutomation(Base, TimestampMixin):
    __tablename__ = "consolidation_automations"

    id = Column(Integer, primary_key=True, index=True)
    stage = Column(String, index=True, nullable=False)
    delay_days = Column(Integer, default=0, nullable=False)
    channel = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class CounselingSession(Base, TimestampMixin):
    __tablename__ = "counseling_sessions"

    id = Column(Integer, primary_key=True, index=True)
    pastor_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("consolidation_pipeline.id"), nullable=True, index=True)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    status = Column(String, default="Pendiente", nullable=False)
    topic = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    confidential_notes = Column(Text, nullable=True)

    member = relationship("Member")
    lead = relationship("ConsolidationPipeline")


class Donation(Base, TimestampMixin):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    donor_name = Column(String, nullable=True)
    donor_email = Column(String, nullable=True)
    donation_type = Column(String, default="Ofrenda General", nullable=False)
    status = Column(String, default="completada", nullable=False)


class CommunicationLog(Base, TimestampMixin):
    __tablename__ = "communication_logs"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=False)
    channel = Column(String, nullable=False)
    content = Column(Text, nullable=False)


class MediaAsset(Base, TimestampMixin):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    url = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)


class ContentMetric(Base, TimestampMixin):
    __tablename__ = "content_metrics"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String, nullable=False)
    content_id = Column(Integer, nullable=False)
    metric_type = Column(String, nullable=False, default="view")
    value = Column(Integer, default=0, nullable=False)


class Capability(Base, TimestampMixin):
    __tablename__ = "mesh_capabilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    version = Column(String, default="1.0.0", nullable=False)
    tools_schema = Column(Text, nullable=True)
    input_metadata = Column(Text, nullable=True)
    output_metadata = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_registered_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class GloryHouse(Base, TimestampMixin):
    __tablename__ = "glory_houses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    zone = Column(String, index=True, nullable=False)
    leader_name = Column(String, nullable=False)
    members_count = Column(Integer, default=0, nullable=False)
    schedule = Column(String, nullable=False)
    status = Column(String, default="Activo", nullable=False)


class AgentTask(Base, TimestampMixin):
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending", nullable=False)
    source = Column(String, nullable=False)
    assignee = Column(String, nullable=True)
    priority = Column(String, default="medium", nullable=False)
    extra = Column(Text, nullable=True)


class AgentInsight(Base, TimestampMixin):
    __tablename__ = "agent_insights"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    insight_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User")


class AdminAuditLog(Base, TimestampMixin):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    action_data = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)

    actor = relationship("User")

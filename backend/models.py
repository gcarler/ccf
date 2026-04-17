from __future__ import annotations
import datetime as dt
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Numeric, JSON, Table, UniqueConstraint,
    PrimaryKeyConstraint, func, cast, Index, Float
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import UUID
import uuid
from backend.core.database import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)

# 1. IDENTITY, GAMIFICATION & UI
class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    permissions = Column(JSON)
    role_users = relationship("User", back_populates="user_role_obj")

class Level(Base):
    __tablename__ = "levels"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), unique=True, nullable=False)
    min_xp = Column(Integer, default=0)
    icon_key = Column(String(50), nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=True)
    role = Column(String(20), default="estudiante", index=True)

    # --- Gamification ---
    xp = Column(Integer, default=0, index=True)
    current_level_id = Column(Integer, ForeignKey("levels.id"), nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    is_email_verified = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user_role_obj = relationship("Role", back_populates="role_users")
    enrollments = relationship("Enrollment", back_populates="student")
    badges = relationship("UserBadge", back_populates="user")
    ui_prefs = relationship("UserUIPreference", back_populates="user", uselist=False)

    # Relationships for CRM & Pipeline
    assigned_leads = relationship("ConsolidationPipeline", back_populates="pastor")

    # Relationships for Projects
    assigned_tasks = relationship("ProjectTask", back_populates="assignee")

class Badge(Base):
    __tablename__ = "badges"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon_key = Column(String(50), nullable=False)
    xp_reward = Column(Integer, default=50)

class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="badges")
    badge_obj = relationship("Badge")

class UserUIPreference(Base):
    __tablename__ = "user_ui_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    settings = Column(JSON, default={})
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    user = relationship("User", back_populates="ui_prefs")

# 2. ACADEMY & FORUM
class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=True)
    modality = Column(String(20), nullable=False, index=True)
    is_published = Column(Boolean, default=True)
    is_self_paced = Column(Boolean, default=True)
    duration_hours = Column(Integer, default=0)
    cohort_name = Column(String(100), nullable=True)
    certificate_type = Column(String(50), default="Participación")
    xp_per_lesson = Column(Integer, default=10)
    created_at = Column(DateTime, default=_utcnow)
    lessons = relationship("Lesson", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course")
    prerequisites = relationship(
        "CoursePrerequisite",
        foreign_keys="CoursePrerequisite.course_id",
        back_populates="course"
    )

class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    prerequisite_course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("course_id", "prerequisite_course_id", name="uq_course_prerequisite"),)

    course = relationship("Course", foreign_keys=[course_id], back_populates="prerequisites")
    prerequisite_course = relationship("Course", foreign_keys=[prerequisite_course_id])

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="video") # video, pdf, quiz
    media_url = Column(String(255), nullable=True)
    order_index = Column(Integer, default=0)
    duration_minutes = Column(Integer, default=0)
    course = relationship("Course", back_populates="lessons")
    resources = relationship("Resource", back_populates="lesson")
    assessments = relationship("Assessment", back_populates="lesson")

class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    progress_percent = Column(Numeric(5, 2), default=0)
    last_position_seconds = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),)

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True) # Direct course relation
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    min_score = Column(Numeric(5, 2), default=70)
    weight = Column(Numeric(5, 2), default=1.0)

    lesson = relationship("Lesson", back_populates="assessments")
    course = relationship("Course") # New relationship
    questions = relationship("AssessmentQuestion", back_populates="assessment")

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="multiple_choice")
    points = Column(Integer, default=10)

    assessment = relationship("Assessment", back_populates="questions")
    options = relationship("AssessmentOption", back_populates="question")

class AssessmentOption(Base):
    __tablename__ = "assessment_options"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("assessment_questions.id"), nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("AssessmentQuestion", back_populates="options")

class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    score = Column(Numeric(5, 2), default=0)
    passed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    title = Column(String(200), nullable=False)
    file_url = Column(String(500), nullable=False)
    resource_type = Column(String(50), nullable=True)

    lesson = relationship("Lesson", back_populates="resources")

class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    file_url = Column(String(500), nullable=False)
    comment = Column(Text, nullable=True)
    grade = Column(Numeric(5, 2), nullable=True)
    teacher_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

class FormalActa(Base):
    __tablename__ = "formal_actas"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    closed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="closed") # closed, archived
    min_grade_required = Column(Numeric(5, 2), default=70)
    min_attendance_required = Column(Numeric(5, 2), default=75)
    created_at = Column(DateTime, default=_utcnow)

class ForumComment(Base):
    __tablename__ = "forum_comments"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("forum_threads.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    members = relationship("Member", back_populates="family")

class GloryHouse(Base):
    __tablename__ = "glory_houses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    zone = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    leader_name = Column(String(100), nullable=True)
    members_count = Column(Integer, default=0)
    capacity = Column(Integer, default=15)
    schedule = Column(String(100), nullable=True)
    status = Column(String(20), default="Activo")
    created_at = Column(DateTime, default=_utcnow)

class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    status = Column(String(20), default="active") # active, completed, dropped
    progress_percent = Column(Numeric(5, 2), default=0)
    lessons_completed = Column(JSON, default=[])
    approved = Column(Boolean, default=False)
    certificate_issued = Column(Boolean, default=False)
    certificate_code = Column(String(64), nullable=True)
    access_window_end = Column(DateTime, nullable=True) # RN-NF-004
    created_at = Column(DateTime, default=_utcnow)
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

class AcademyActivityLog(Base):
    __tablename__ = "academy_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True) # enrollment, completion, drop, certificate
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    modality = Column(String(20), nullable=True) # formal, no_formal
    value = Column(Numeric(10, 2), default=1.0)
    created_at = Column(DateTime, default=_utcnow, index=True)

class ForumThread(Base):
    __tablename__ = "forum_threads"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

# 3. CRM & CHAT
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(String(100), nullable=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow, index=True)

class ConsolidationPipeline(Base):
    __tablename__ = "consolidation_pipeline"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    source = Column(String(100), nullable=True)
    stage = Column(String(20), default="new", index=True)
    notes = Column(Text, nullable=True)

    assigned_pastor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    pastor = relationship("User", back_populates="assigned_leads")

class CrmEvent(Base):
    __tablename__ = "crm_events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime, nullable=False, index=True)
    location = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    attendances = relationship("EventAttendance", back_populates="event")

class EventAttendance(Base):
    __tablename__ = "event_attendances"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("crm_events.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    scanned_at = Column(DateTime, default=_utcnow, index=True)
    status = Column(String(50), default="present", index=True)

    event = relationship("CrmEvent", back_populates="attendances")
    member = relationship("Member")

class CounselingTicket(Base):
    __tablename__ = "counseling_tickets"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    subject = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="open", index=True) # open, in_progress, resolved
    priority_level = Column(String(20), default="NORMAL", index=True) # URGENT, HIGH, NORMAL
    sentiment_score = Column(Float, nullable=True) # -1.0 to 1.0
    sentiment_label = Column(String(20), nullable=True) # POSITIVE, NEUTRAL, NEGATIVE
    created_at = Column(DateTime, default=_utcnow, index=True)

    member = relationship("Member")
    pastor = relationship("User")

class PrayerRequest(Base):
    __tablename__ = "prayer_requests"
    id = Column(Integer, primary_key=True, index=True)
    requester_name = Column(String(200), nullable=False, index=True)
    request_text = Column(Text, nullable=False)
    category = Column(String(50), default="General") # New column
    is_public = Column(Boolean, default=False, index=True)
    status = Column(String(50), default="pending", index=True) # pending, praying, answered
    created_at = Column(DateTime, default=_utcnow, index=True)

# --- RELATIONS TABLES ---
member_ministries = Table(
    "member_ministries",
    Base.metadata,
    Column("member_id", Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
    Column("ministry_id", Integer, ForeignKey("ministries.id", ondelete="CASCADE"), primary_key=True),
)

class Ministry(Base):
    __tablename__ = "ministries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    leader_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    members = relationship("Member", secondary=member_ministries, back_populates="ministries")

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="SET NULL"), nullable=True, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    email = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    church_role = Column(String(50), default="Miembro", index=True)
    is_baptized = Column(Boolean, default=False, index=True)
    spiritual_status = Column(String(50), default="Nuevo", index=True) # Nuevo, Creyente, Discípulo, Servidor
    
    # --- New Management Fields ---
    talents = Column(Text, nullable=True) # Habilidades (Música, Tech, Cocina, etc)
    spiritual_gifts = Column(Text, nullable=True) # Dones (Liderazgo, Misericordia, etc)
    pastoral_notes = Column(Text, nullable=True) # Notas internas para el pastor
    
    created_at = Column(DateTime, default=_utcnow, index=True)

    user = relationship("User", backref=backref("member_profile", uselist=False))
    family = relationship("Family", back_populates="members")
    ministries = relationship("Ministry", secondary=member_ministries, back_populates="members")
    donations = relationship("Donation", back_populates="member")
    tasks = relationship("CrmTask", back_populates="member")


# 4. PROJECTS & ACTIVITIES
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning") # active, completed, on_hold
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    whiteboard_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    activity_logs = relationship("ProjectActivityLog", back_populates="project", cascade="all, delete-orphan")
    owner = relationship("User", foreign_keys=[owner_id])

class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    project = relationship("Project", back_populates="milestones")

class ProjectActivityLog(Base):
    __tablename__ = "project_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String(50)) # 'task_created', 'milestone_completed', etc.
    description = Column(Text)
    created_at = Column(DateTime, default=_utcnow)

    project = relationship("Project", back_populates="activity_logs")
    user = relationship("User")

class ProjectTask(Base):
    __tablename__ = "project_tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    order_index = Column(Integer, default=0)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(20), default="todo") # todo, in_progress, review, done
    priority = Column(String(20), default="normal") # urgent, high, normal, low
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    start_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    labels = Column(JSON, default=[]) # e.g. ["Alabanza", "Importante"]
    attachments = Column(JSON, default=[]) # e.g. [{"name": "file.pdf", "url": "/static/uploads/file.pdf"}]
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
    supplies = relationship("TaskSupply", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("ProjectAttachment", back_populates="task", cascade="all, delete-orphan")
    subtasks = relationship(
        "ProjectTask",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )

class ProjectAttachment(Base):
    __tablename__ = "project_attachments"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    task = relationship("ProjectTask", back_populates="attachments")
    uploader = relationship("User")

class TaskSupply(Base):
    __tablename__ = "task_supplies"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="pending") # pending, ready, unavailable

    task = relationship("ProjectTask", back_populates="supplies")

class ProjectComment(Base):
    __tablename__ = "project_comments"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

class ProjectInboxState(Base):
    __tablename__ = "project_inbox_state"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(80), nullable=False)
    is_read = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_project_item"),)

# 5. OTHERS
class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    stock = Column(Integer, default=0)
    status = Column(String(20), default="ok")
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

class AgentInsight(Base):
    __tablename__ = "agent_insights"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    insight_type = Column(String(50), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending", index=True)
    priority = Column(String(20), default="medium")
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(120), nullable=False, index=True)
    resource_type = Column(String(120), nullable=True, index=True)
    resource_id = Column(String(120), nullable=True)
    ip_address = Column(String(45), nullable=True) # New column
    severity = Column(String(20), default="info") # New column
    metadata_json = Column("metadata", JSON, default={})
    created_at = Column(DateTime, default=_utcnow, index=True)


class PastoralCallLog(Base):
    __tablename__ = "pastoral_call_logs"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("consolidation_pipeline.id"), nullable=False, index=True)
    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outcome = Column(String(120), nullable=False)
    notes = Column(Text, nullable=True)
    duration_seconds = Column(Integer, default=0) # New column
    created_at = Column(DateTime, default=_utcnow)


class PageContent(Base):
    __tablename__ = "page_contents"
    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String(120), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class PageContentVersion(Base):
    __tablename__ = "page_content_versions"
    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String(120), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class ContentPublication(Base):
    __tablename__ = "content_publications"
    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String(120), unique=True, nullable=False, index=True)
    status = Column(String(30), default="draft", index=True)  # draft, in_review, approved, published, archived
    publish_at = Column(DateTime, nullable=True)
    expire_at = Column(DateTime, nullable=True)
    last_published_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class ContentMetric(Base):
    __tablename__ = "content_metrics"
    id = Column(Integer, primary_key=True, index=True)
    metric_key = Column(String(120), nullable=False, index=True)
    ref_id = Column(Integer, nullable=False, index=True)
    value = Column(Integer, default=0)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    mime_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)


class CmsMediaItem(Base):
    __tablename__ = "cms_media_items"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    alt_text = Column(String(255), nullable=True)
    dimensions = Column(String(50), nullable=True) # New column
    section = Column(String(120), nullable=False, index=True, default="general")
    tags = Column(JSON, default=[])
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsSite(Base):
    __tablename__ = "cms_sites"
    id = Column(Integer, primary_key=True, index=True)
    site_key = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    base_path = Column(String(120), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsTheme(Base):
    __tablename__ = "cms_themes"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    tokens_json = Column(JSON, default={})
    is_active = Column(Boolean, default=False, index=True)
    version = Column(Integer, default=1)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsMenu(Base):
    __tablename__ = "cms_menus"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_key = Column(String(80), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "menu_key", name="uq_cms_menu_site_key"),
    )


class CmsMenuItem(Base):
    __tablename__ = "cms_menu_items"
    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, ForeignKey("cms_menus.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("cms_menu_items.id", ondelete="CASCADE"), nullable=True, index=True)
    label = Column(String(120), nullable=False)
    href = Column(String(255), nullable=False)
    target = Column(String(20), default="_self")
    is_external = Column(Boolean, default=False)
    visibility = Column(String(20), default="public")
    sort_order = Column(Integer, default=0)
    meta_json = Column(JSON, default={})
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsPage(Base):
    __tablename__ = "cms_pages"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(160), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(30), default="draft", index=True)
    seo_json = Column(JSON, default={})
    published_version_id = Column(Integer, ForeignKey("cms_page_versions.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_page_site_slug"),
    )


class CmsPageVersion(Base):
    __tablename__ = "cms_page_versions"
    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, default={})
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("page_id", "version_number", name="uq_cms_page_version_number"),
    )


class CmsSection(Base):
    __tablename__ = "cms_sections"
    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    section_key = Column(String(120), nullable=False, index=True)
    type = Column(String(80), nullable=False, index=True)
    props_json = Column(JSON, default={})
    sort_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsPublishLog(Base):
    __tablename__ = "cms_publish_logs"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id = Column(Integer, ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False, index=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime, default=_utcnow, index=True)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


class UserReminder(Base):
    __tablename__ = "user_reminders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    remind_at = Column(DateTime, nullable=False)
    priority = Column(String(20), default="normal")
    related_type = Column(String(50), nullable=True) # e.g. 'task', 'event'
    related_id = Column(Integer, nullable=True)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


class CommunicationLog(Base):
    __tablename__ = "communication_logs"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    channel = Column(String(50), nullable=False) # WhatsApp, SMS, Email
    recipient_phone = Column(String(20), nullable=True)
    content = Column(Text, nullable=False)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    outcome = Column(String(50), default="sent") # pending, sent, delivered, failed
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(20), nullable=True)
    external_id = Column(String(100), nullable=True, index=True) # ID de Twilio/Meta
    created_at = Column(DateTime, default=_utcnow)


class CourseAttendance(Base):
    __tablename__ = "course_attendance"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    session_date = Column(DateTime, default=_utcnow, index=True)
    status = Column(String(20), default="present")  # present, absent, justified
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    enrollment = relationship("Enrollment")


class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False, index=True)
    certificate_code = Column(String(64), unique=True, nullable=False, index=True)
    issued_at = Column(DateTime, default=_utcnow)

class Donation(Base):
    __tablename__ = "donations"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    donation_type = Column(String(50), default="Diezmo") # Diezmo, Ofrenda, Especial
    status = Column(String(20), default="completed") # New column
    reference_code = Column(String(100), nullable=True) # New column
    payment_method = Column(String(50), default="Transferencia") # New column
    fund_id = Column(Integer, nullable=True)
    person_id = Column(Integer, nullable=True) # Legado compatibilidad
    donor_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    
    member = relationship("Member", back_populates="donations")

class DonationCategory(Base):
    __tablename__ = "donation_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    color_code = Column(String(50), default="blue")
    is_active = Column(Boolean, default=True)


class AssetItem(Base):
    __tablename__ = "assets_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    brand = Column(String(100))
    serial_number = Column(String(100), unique=True)
    purchase_price = Column(Float)
    current_status = Column(String(50), default='Disponible') # Disponible, Mantenimiento, Dañado
    category = Column(String(100), default='Mobiliario')
    created_at = Column(DateTime, default=_utcnow)

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("assets_items.id"))
    service_date = Column(DateTime, default=_utcnow)
    description = Column(Text)
    cost = Column(Float, default=0.0)
    
    asset = relationship("AssetItem")

class ChurchLocation(Base):
    __tablename__ = "church_locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    pastor_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    location_type = Column(String(50), default="Central") # Central, Sede, Anexo
    created_at = Column(DateTime, default=_utcnow)

class SocialChannel(Base):
    __tablename__ = "social_channels"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False) # Facebook, Instagram, YouTube, Web
    url = Column(String(255), nullable=False)
    is_visible = Column(Boolean, default=True)

class SystemVariable(Base):
    __tablename__ = "system_variables"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(String(255))

class CrmTask(Base):
    __tablename__ = "crm_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="Pastoral", nullable=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("consolidation_pipeline.id"), nullable=True, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending") # pending, in_progress, done, urgent
    priority = Column(String(20), default="medium") # urgent, high, medium, low
    created_at = Column(DateTime, default=_utcnow, index=True)
    
    member = relationship("Member", back_populates="tasks")
    lead = relationship("ConsolidationPipeline")
    assignee = relationship("User")


class VolunteerShift(Base):
    __tablename__ = "volunteer_shifts"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    role_name = Column(String(100), nullable=False) # Alabanza, Ujier, etc.
    team_name = Column(String(100), nullable=False)
    shift_start = Column(DateTime, nullable=False)
    shift_end = Column(DateTime, nullable=False)
    status = Column(String(20), default="confirmed") # confirmed, pending, cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    member = relationship("Member")

class VolunteerSkill(Base):
    __tablename__ = "volunteer_skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(100)) # Musico, Tecnico, Administrativo, Servicio

member_volunteer_skills = Table(
    "member_volunteer_skills",
    Base.metadata,
    Column("member_id", Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("volunteer_skills.id", ondelete="CASCADE"), primary_key=True),
)


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    image_url = Column(String(500), nullable=True)
    is_featured = Column(Boolean, default=False)
    published_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)

class Testimonial(Base):
    __tablename__ = "testimonials"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    emotion = Column(String(50), default="Gratitud")
    is_approved = Column(Boolean, default=False)
    show_on_home = Column(Boolean, default=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

class CrmAutomation(Base):
    __tablename__ = "crm_automations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    trigger_event = Column(String(50), nullable=False) # birthday, new_member, inactivity
    action_type = Column(String(50), nullable=False) # send_whatsapp, create_task
    action_payload = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)




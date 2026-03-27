from __future__ import annotations
import uuid
import datetime as dt
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, 
    ForeignKey, Numeric, JSON, Enum, Table, UniqueConstraint,
    PrimaryKeyConstraint, func, cast, Index
)
from sqlalchemy.orm import relationship, backref
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
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
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
    modality = Column(String(20), nullable=False, index=True)
    is_published = Column(Boolean, default=True)
    xp_per_lesson = Column(Integer, default=10)
    created_at = Column(DateTime, default=_utcnow)
    lessons = relationship("Lesson", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course")

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    course = relationship("Course", back_populates="lessons")

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
    created_at = Column(DateTime, default=_utcnow)
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

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
    
    assigned_pastor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    pastor = relationship("User", back_populates="assigned_leads")

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    family_id = Column(Integer, nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    church_role = Column(String(50), default="Miembro")
    
    user = relationship("User", backref=backref("member_profile", uselist=False))

# 4. PROJECTS & ACTIVITIES
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning") # active, completed, on_hold
    created_at = Column(DateTime, default=_utcnow)
    
    tasks = relationship("ProjectTask", back_populates="project")

class ProjectTask(Base):
    __tablename__ = "project_tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    status = Column(String(20), default="todo") # todo, in_progress, review, done
    priority = Column(String(20), default="normal") # urgent, high, normal, low
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    start_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    labels = Column(JSON, default=[]) # e.g. ["Alabanza", "Importante"]
    
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
    supplies = relationship("TaskSupply", back_populates="task")

class TaskSupply(Base):
    """Insumos requeridos para una actividad específica"""
    __tablename__ = "task_supplies"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("project_tasks.id"), nullable=False)
    item_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="pending") # pending, ready, unavailable
    
    task = relationship("ProjectTask", back_populates="supplies")

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
    metadata_json = Column("metadata", JSON, default={})
    created_at = Column(DateTime, default=_utcnow, index=True)


class PastoralCallLog(Base):
    __tablename__ = "pastoral_call_logs"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("consolidation_pipeline.id"), nullable=False, index=True)
    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outcome = Column(String(120), nullable=False)
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


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


class CommunicationLog(Base):
    __tablename__ = "communication_logs"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False, index=True)
    channel = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    outcome = Column(String(50), default="sent")
    created_at = Column(DateTime, default=_utcnow)


class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False, index=True)
    certificate_code = Column(String(64), unique=True, nullable=False, index=True)
    issued_at = Column(DateTime, default=_utcnow)

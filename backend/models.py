from __future__ import annotations
import uuid
import datetime as dt
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, 
    ForeignKey, Numeric, JSON, Enum, Table, UniqueConstraint,
    PrimaryKeyConstraint, func, cast
)
from sqlalchemy.orm import relationship, backref
from backend.core.database import Base

# 1. IDENTITY & GAMIFICATION
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
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=True)
    role = Column(String(20), default="estudiante")
    
    xp = Column(Integer, default=0)
    current_level_id = Column(Integer, ForeignKey("levels.id"), nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    user_role_obj = relationship("Role", back_populates="role_users")
    enrollments = relationship("Enrollment", back_populates="student")
    badges = relationship("UserBadge", back_populates="user")
    ui_prefs = relationship("UserUIPreference", back_populates="user", uselist=False)

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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge")

class UserUIPreference(Base):
    __tablename__ = "user_ui_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    settings = Column(JSON, default={})
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    user = relationship("User", back_populates="ui_prefs")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# 2. ACADEMY
class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=True)
    modality = Column(String(20), nullable=False)
    is_published = Column(Boolean, default=True)
    certificate_type = Column(String(50), nullable=True)
    xp_per_lesson = Column(Integer, default=10)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    lessons = relationship("Lesson", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course")
    assessments = relationship("Assessment", back_populates="course")

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    order_index = Column(Integer, default=0)

    course = relationship("Course", back_populates="lessons")
    resources = relationship("Resource", back_populates="lesson")

class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    title = Column(String(200), nullable=False)
    file_url = Column(Text, nullable=False)
    resource_type = Column(String(50), nullable=False) 
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    lesson = relationship("Lesson", back_populates="resources")

class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    prerequisite_course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    status = Column(String(20), default="active")
    progress_percent = Column(Numeric(5, 2), default=0)
    lessons_completed = Column(JSON, default=[])
    approved = Column(Boolean, default=False)
    acta_closed = Column(Boolean, default=False)
    certificate_issued = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    passing_score = Column(Numeric(5, 2), default=70)
    is_published = Column(Boolean, default=True)

    course = relationship("Course", back_populates="assessments")

class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    certificate_code = Column(String(50), unique=True, index=True)
    certificate_type = Column(String(50), nullable=True)
    issued_at = Column(DateTime, default=dt.datetime.utcnow)

# 3. CRM, AUDIT & AGENTS
class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    church_role = Column(String(50), default="Miembro")
    
class GloryHouse(Base):
    __tablename__ = "glory_houses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    leader_name = Column(String(100), nullable=True)
    status = Column(String(20), default="active")

class Donation(Base):
    __tablename__ = "donations"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    donor_name = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    action_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class AgentInsight(Base):
    __tablename__ = "agent_insights"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    insight_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class AgentTask(Base):
    __tablename__ = "agent_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    priority = Column(String(20), default="medium")
    source = Column(String(50), default="agent")
    created_at = Column(DateTime, default=dt.datetime.utcnow)

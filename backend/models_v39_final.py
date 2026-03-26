from __future__ import annotations
import uuid
import datetime as dt
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, 
    ForeignKey, Numeric, JSON, Table, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.core.database import Base

# 1. IDENTITY SCHEMA
class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "identity"}
    role_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    permissions = Column(JSONB)
    users = relationship("User", back_populates="role_obj")

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role_id = Column(Integer, ForeignKey("identity.roles.role_id"))
    role = Column(String(20), default="estudiante")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    
    role_obj = relationship("Role", back_populates="users")
    person = relationship("Person", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")

# 2. MEMBERSHIP SCHEMA
class Family(Base):
    __tablename__ = "families"
    __table_args__ = {"schema": "membership"}
    family_id = Column(Integer, primary_key=True)
    family_name = Column(String(100), nullable=False)
    address = Column(Text)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    members = relationship("Person", back_populates="family")

class Person(Base):
    __tablename__ = "persons"
    __table_args__ = {"schema": "membership"}
    person_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(Integer, ForeignKey("membership.families.family_id"))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True)
    phone_mobile = Column(String(20))
    status = Column(String(20), default='Activo')
    gender = Column(String(1))
    is_baptized = Column(Boolean, default=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.user_id"))
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    
    user = relationship("User", back_populates="person")
    family = relationship("Family", back_populates="members")

class GloryHouse(Base):
    __tablename__ = "cell_groups"
    __table_args__ = {"schema": "membership"}
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    zone = Column(String(100))
    host_name = Column(String(100))
    leader_name = Column(String(100))
    members_count = Column(Integer, default=0)
    schedule = Column(String(100))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# 3. WEB CONTENT SCHEMA (CMS)
class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="General")
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class Sermon(Base):
    __tablename__ = "sermons"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    preacher = Column(String(100))
    video_url = Column(String(255))
    duration = Column(String(20))
    thumbnail_url = Column(String(255))
    series = Column(String(100))
    date = Column(DateTime, default=dt.datetime.utcnow)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class Testimonial(Base):
    __tablename__ = "testimonials"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.user_id"))
    author_id = Column(UUID(as_uuid=True))
    content = Column(Text, nullable=False)
    category = Column(String(50))
    emotion = Column(String(50))
    is_approved = Column(Boolean, default=False)
    show_on_home = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    author = relationship("User")

class Book(Base):
    __tablename__ = "library_books"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100))
    description = Column(Text)
    cover_image_url = Column(String(255))
    download_url = Column(String(255))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class Event(Base):
    __tablename__ = "church_events"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    event_type = Column(String(50))
    event_date = Column(DateTime)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class PageContent(Base):
    __tablename__ = "page_contents"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    page_key = Column(String(100), unique=True, index=True)
    title = Column(String(200))
    content = Column(Text)
    image_url = Column(String(255))
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

class PageContentVersion(Base):
    __tablename__ = "page_content_versions"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    page_content_id = Column(Integer, ForeignKey("web_content.page_contents.id"))
    title = Column(String(200))
    content = Column(Text)
    image_url = Column(String(255))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# 4. EDUCATION SCHEMA (ACADEMY)
class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {"schema": "web_content"}
    course_id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    modality = Column(String(20))
    certificate_type = Column(String(50), default="Participacion")
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    lessons = relationship("Lesson", back_populates="course")
    assessments = relationship("Assessment", back_populates="course")

class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("web_content.courses.course_id"))
    title = Column(String(200), nullable=False)
    content = Column(Text)
    order_index = Column(Integer, default=0)
    course = relationship("Course", back_populates="lessons")
    resources = relationship("LessonResource", back_populates="lesson")

class LessonResource(Base):
    __tablename__ = "lesson_resources"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("web_content.lessons.id"))
    title = Column(String(200))
    url = Column(String(255))
    lesson = relationship("Lesson", back_populates="resources")

class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.user_id"))
    course_id = Column(Integer, ForeignKey("web_content.courses.course_id"))
    status = Column(String(20), default="active")
    progress_percent = Column(Numeric(5, 2), default=0)
    approved = Column(Boolean, default=False)
    certificate_issued = Column(Boolean, default=False)
    final_grade = Column(Numeric(5, 2))
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    course = relationship("Course")

class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = {"schema": "web_content"}
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("web_content.courses.course_id"))
    title = Column(String(200))
    passing_score = Column(Numeric(5, 2), default=70)
    max_score = Column(Numeric(5, 2), default=100)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    course = relationship("Course", back_populates="assessments")

# 5. SYSTEM SCHEMA
class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "identity"}
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.user_id"))
    title = Column(String(200))
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    user = relationship("User", back_populates="notifications")

# 6. ANALYTICS SCHEMA
class PastorRadar(Base):
    __tablename__ = "v_pastor_radar"
    __table_args__ = {"schema": "analytics"}
    membresia_viva = Column(Integer, primary_key=True)
    bautismos_este_anio = Column(Integer)
    estudiantes_activos = Column(Integer)
    recaudacion_mes = Column(Numeric(15, 2))

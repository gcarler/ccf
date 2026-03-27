"""
CCF MESH - MODELOS DE DATOS V3.9 TOTAL
Este archivo contiene la arquitectura completa ministerial.
Consolidado en un solo archivo para maxima estabilidad.
"""

from __future__ import annotations
import uuid
import datetime as dt
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, 
    ForeignKey, Numeric, JSON, Table, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from backend.core.database import Base

# =============================================================================
# 1. IDENTIDAD
# =============================================================================

class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    permissions = Column(JSONB)
    users = relationship("User", back_populates="role_obj")

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"))
    role = Column(String(20), default="estudiante")
    xp = Column(Integer, default=0)
    current_level_id = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    
    role_obj = relationship("Role", back_populates="users")
    person = relationship("Person", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")

# =============================================================================
# 2. MEMBRESIA Y TALENTO
# =============================================================================

class Family(Base):
    __tablename__ = "families"
    family_id = Column(Integer, primary_key=True)
    family_name = Column(String(100), nullable=False)
    address = Column(Text)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    members = relationship("Person", back_populates="family")

class EcclesiasticalOffice(Base):
    __tablename__ = "ecclesiastical_offices"
    office_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

class Skill(Base):
    __tablename__ = "skills"
    skill_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))

person_skills = Table(
    'person_skills', Base.metadata,
    Column('person_id', UUID(as_uuid=True), ForeignKey('persons.person_id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.skill_id'), primary_key=True)
)

class Person(Base):
    __tablename__ = "persons"
    person_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(Integer, ForeignKey("families.family_id"))
    office_id = Column(Integer, ForeignKey("ecclesiastical_offices.office_id"))
    mentor_id = Column(UUID(as_uuid=True), ForeignKey("persons.person_id"))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True)
    phone_mobile = Column(String(20))
    status = Column(String(20), default='Activo')
    gender = Column(String(1))
    is_baptized = Column(Boolean, default=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    
    user = relationship("User", back_populates="person")
    family = relationship("Family", back_populates="members")
    skills = relationship("Skill", secondary=person_skills)

class GloryHouse(Base):
    __tablename__ = "cell_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    zone = Column(String(100))
    host_name = Column(String(100))
    leader_name = Column(String(100))
    members_count = Column(Integer, default=0)
    schedule = Column(String(100))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# =============================================================================
# 3. VIDA ESPIRITUAL
# =============================================================================

class Milestone(Base):
    __tablename__ = "milestones"
    milestone_id = Column(Integer, primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.person_id"))
    type = Column(String(50), nullable=False) 
    event_date = Column(Date, nullable=False)
    minister_id = Column(UUID(as_uuid=True), ForeignKey("persons.person_id"))
    certificate_url = Column(Text)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# =============================================================================
# 4. FINANZAS
# =============================================================================

class Fund(Base):
    __tablename__ = "funds"
    fund_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_public = Column(Boolean, default=True)
    current_balance = Column(Numeric(15, 2), default=0)

class Donation(Base):
    __tablename__ = "donations"
    donation_id = Column(Integer, primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.person_id"))
    fund_id = Column(Integer, ForeignKey("funds.fund_id"))
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_date = Column(DateTime, default=dt.datetime.utcnow)
    person = relationship("Person")

class Expenditure(Base):
    __tablename__ = "expenditures"
    expenditure_id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("funds.fund_id"))
    amount = Column(Numeric(15, 2), nullable=False)
    category = Column(String(100))
    proof_url = Column(Text)

class MissionImpact(Base):
    __tablename__ = "mission_impact"
    impact_id = Column(Integer, primary_key=True)
    expenditure_id = Column(Integer, ForeignKey("expenditures.expenditure_id"))
    impact_metric = Column(String(100))
    quantity = Column(Integer)

# =============================================================================
# 5. ACTIVOS
# =============================================================================

class AssetItem(Base):
    __tablename__ = "assets_items"
    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    brand = Column(String(100))
    serial_number = Column(String(100), unique=True)
    purchase_price = Column(Numeric(15, 2))
    current_status = Column(String(50), default='Disponible')

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    log_id = Column(Integer, primary_key=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("assets_items.item_id"))
    service_date = Column(Date, nullable=False)
    description = Column(Text)

# =============================================================================
# 6. CONTENIDO (CMS)
# =============================================================================

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="General")
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class Sermon(Base):
    __tablename__ = "sermons"
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
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    content = Column(Text, nullable=False)
    category = Column(String(50))
    emotion = Column(String(50))
    is_approved = Column(Boolean, default=False)
    show_on_home = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class Book(Base):
    __tablename__ = "library_books"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100))
    description = Column(Text)
    cover_image_url = Column(String(255))
    download_url = Column(String(255))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class Event(Base):
    __tablename__ = "church_events"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    event_type = Column(String(50))
    event_date = Column(DateTime)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# =============================================================================
# 7. ACADEMIA
# =============================================================================

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    modality = Column(String(20))
    certificate_type = Column(String(50), default="Participacion")
    xp_per_lesson = Column(Integer, default=10)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    lessons = relationship("Lesson", back_populates="course")

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(200), nullable=False)
    content = Column(Text)
    order_index = Column(Integer, default=0)
    course = relationship("Course", back_populates="lessons")

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    status = Column(String(20), default="active")
    progress_percent = Column(Numeric(5, 2), default=0)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    course = relationship("Course")

# =============================================================================
# 8. ANALITICA Y SISTEMA
# =============================================================================

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    title = Column(String(200))
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    user = relationship("User", back_populates="notifications")

class PastorRadar(Base):
    __tablename__ = 'v_pastor_radar'
    membresia_viva = Column(Integer, primary_key=True)
    bautismos_este_anio = Column(Integer)
    estudiantes_activos = Column(Integer)
    recaudacion_mes = Column(Numeric(15, 2))

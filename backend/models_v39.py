from __future__ import annotations
import uuid
import datetime as dt
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, 
    ForeignKey, Numeric, JSON, Enum, Table, UniqueConstraint,
    PrimaryKeyConstraint, func, cast
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PG_ENUM
from sqlalchemy.orm import relationship, backref
from backend.core.database import Base

# =============================================================================
# 1. ESQUEMA DE IDENTIDAD (Acceso y Seguridad)
# =============================================================================

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "identity"}

    role_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False) # Admin, Pastor, L??der, Agente
    permissions = Column(JSONB) # Permisos granulares

    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role_id = Column(Integer, ForeignKey("identity.roles.role_id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    role = relationship("Role", back_populates="users")
    person = relationship("Person", back_populates="user", uselist=False)

# =============================================================================
# 2. ESQUEMA DE MEMBRES??A Y TALENTO
# =============================================================================

class Family(Base):
    __tablename__ = "families"
    __table_args__ = {"schema": "membership"}

    family_id = Column(Integer, primary_key=True)
    family_name = Column(String(100), nullable=False)
    address = Column(Text)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    members = relationship("Person", back_populates="family")

class EcclesiasticalOffice(Base):
    __tablename__ = "ecclesiastical_offices"
    __table_args__ = {"schema": "membership"}

    office_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False) # Ap??stol, Profeta, etc.

class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = {"schema": "membership"}

    skill_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))

person_skills = Table(
    'person_skills', Base.metadata,
    Column('person_id', UUID(as_uuid=True), ForeignKey('membership.persons.person_id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('membership.skills.skill_id'), primary_key=True),
    schema='membership'
)

class Person(Base):
    __tablename__ = "persons"
    __table_args__ = {"schema": "membership"}

    person_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(Integer, ForeignKey("membership.families.family_id"))
    office_id = Column(Integer, ForeignKey("membership.ecclesiastical_offices.office_id"))
    mentor_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    document_id = Column(String(20), unique=True)
    gender = Column(String(1)) # M / F
    birth_date = Column(Date)
    email = Column(String(150), unique=True)
    phone_mobile = Column(String(20))
    status = Column(String(20), default='Activo')
    is_baptized = Column(Boolean, default=False)
    preferred_platform = Column(String(50))
    # location_coords: PostgreSQL Point would need special handling, using string/json for now
    location_coords = Column(String(100)) 
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.user_id"))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="person")
    family = relationship("Family", back_populates="members")
    mentees = relationship("Person", backref=backref("mentor", remote_side=[person_id]))
    skills = relationship("Skill", secondary=person_skills)
    ministry_assignments = relationship("MinistryAssignment", back_populates="person")

class Ministry(Base):
    __tablename__ = "ministries"
    __table_args__ = {"schema": "membership"}

    ministry_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    leader_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class MinistryAssignment(Base):
    __tablename__ = "person_ministry_assignments"
    __table_args__ = {"schema": "membership"}

    assignment_id = Column(Integer, primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    ministry_id = Column(Integer, ForeignKey("membership.ministries.ministry_id"))
    position_title = Column(String(100))
    is_head_of_ministry = Column(Boolean, default=False)
    joined_at = Column(Date, default=dt.date.today)

    person = relationship("Person", back_populates="ministry_assignments")

# =============================================================================
# 3. ESQUEMA CMS Y EDUCACI??N
# =============================================================================

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "web_content"}

    category_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)

class Post(Base):
    __tablename__ = "posts"
    __table_args__ = {"schema": "web_content"}

    post_id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(String(20), nullable=False) # Enum: Testimonio, Predica, etc.
    category_id = Column(Integer, ForeignKey("web_content.categories.category_id"))
    author_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    featured_image = Column(Text)
    video_url = Column(Text)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

class CourseV39(Base):
    __tablename__ = "courses"
    __table_args__ = {"schema": "web_content"}

    course_id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("web_content.posts.post_id"), unique=True)
    access_level = Column(String(20), default='Abierto')
    capacity = Column(Integer)
    meeting_link = Column(Text)
    is_active = Column(Boolean, default=True)

# =============================================================================
# 4. ESQUEMA DE HITOS ESPIRITUALES
# =============================================================================

class Milestone(Base):
    __tablename__ = "milestones"
    __table_args__ = {"schema": "spiritual_life"}

    milestone_id = Column(Integer, primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    type = Column(String(50), nullable=False) # Decision_Fe, Bautismo_Aguas, etc.
    event_date = Column(Date, nullable=False)
    minister_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    certificate_url = Column(Text)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# =============================================================================
# 5. ESQUEMA DE DISCIPULADO (Academia)
# =============================================================================

class AcademyLevel(Base):
    __tablename__ = "levels"
    __table_args__ = {"schema": "discipleship"}

    level_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    order_index = Column(Integer, unique=True)

class StudentProgress(Base):
    __tablename__ = "student_progress"
    __table_args__ = {"schema": "discipleship"}

    progress_id = Column(Integer, primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    level_id = Column(Integer, ForeignKey("discipleship.levels.level_id"))
    status = Column(String(20), default='En Curso')
    mentor_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    completion_date = Column(Date)

# =============================================================================
# 6. ESQUEMA CRM Y CONSEJER??A
# =============================================================================

class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = {"schema": "crm"}

    interaction_id = Column(Integer, primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    interaction_type = Column(String(20), nullable=False)
    notes = Column(Text)
    follow_up_date = Column(DateTime)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

# =============================================================================
# 7. ESQUEMA DE FINANZAS
# =============================================================================

class Fund(Base):
    __tablename__ = "funds"
    __table_args__ = {"schema": "finances"}

    fund_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_public = Column(Boolean, default=True)
    current_balance = Column(Numeric(15, 2), default=0)

class Donation(Base):
    __tablename__ = "donations"
    __table_args__ = {"schema": "finances"}

    donation_id = Column(Integer, primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("membership.persons.person_id"))
    fund_id = Column(Integer, ForeignKey("finances.funds.fund_id"))
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_date = Column(DateTime, default=dt.datetime.utcnow)

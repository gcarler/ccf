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
    is_baptized = Column(Boolean, default=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.user_id"))
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    
    user = relationship("User", back_populates="person")
    family = relationship("Family", back_populates="members")

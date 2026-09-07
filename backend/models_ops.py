import uuid as _uuid

from backend.models_shared import *
from backend.models_shared import _utcnow


class ChurchLocation(Base):
    __tablename__ = "church_locations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    city = Column(String(100), nullable=True)
    phone = Column(String(100), nullable=True)
    pastor_name = Column(String(100), nullable=True)
    schedule = Column(String(255), nullable=True)
    midweek = Column(String(255), nullable=True)
    image_url = Column(String(500), nullable=True)
    maps_url = Column(String(500), nullable=True)
    map_embed_url = Column(String(1000), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_main = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    location_type = Column(String(50), default="Central")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class SocialChannel(Base):
    __tablename__ = "social_channels"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    platform = Column(String(50), nullable=False)
    url = Column(String(255), nullable=False)
    is_visible = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class SystemVariable(Base):
    __tablename__ = "system_variables"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(String(255))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

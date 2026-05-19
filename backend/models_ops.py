from backend.models_shared import *
from backend.models_shared import _utcnow


class ChurchLocation(Base):
    __tablename__ = "church_locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    pastor_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    location_type = Column(String(50), default="Central")
    created_at = Column(DateTime, default=_utcnow)


class SocialChannel(Base):
    __tablename__ = "social_channels"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)
    url = Column(String(255), nullable=False)
    is_visible = Column(Boolean, default=True)


class SystemVariable(Base):
    __tablename__ = "system_variables"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(String(255))

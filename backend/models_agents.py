from backend.models_shared import *
from backend.models_shared import _utcnow


class AgentInsight(Base):
    __tablename__ = "agent_insights"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    insight_type = Column(String(50), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False, index=True)
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

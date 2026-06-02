from backend.models_shared import *
from backend.models_shared import _utcnow


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    action = Column(String(120), nullable=False, index=True)
    resource_type = Column(String(120), nullable=True, index=True)
    resource_id = Column(String(120), nullable=True)
    ip_address = Column(String(45), nullable=True)
    severity = Column(String(20), default="info")
    metadata_json = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    trigger_type = Column(String(100), nullable=False, index=True)
    action_type = Column(String(100), nullable=True, index=True)
    action_payload = Column(JSON, default={})
    config_json = Column(Text, nullable=True, default="{}")
    is_active = Column(Boolean, default=True, index=True)
    last_run = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, index=True)

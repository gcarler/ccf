import uuid as _uuid
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, JSON,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship

from backend.models_shared import Base, _utcnow


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning", index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("Persona", foreign_keys=[owner_id])
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    activity_logs = relationship("ProjectActivityLog", back_populates="project", cascade="all, delete-orphan")
    whiteboard = relationship("ProjectWhiteboard", back_populates="project", uselist=False, cascade="all, delete-orphan")

    # ``name`` is a thin alias over ``title`` so callers that pass or read
    # ``name`` (e.g. ``tests/test_crud_integration.py::TestProjectsCrud``)
    # work without renaming the canonical column. The setter keeps store/update
    # paths single-source-of-truth on ``title``.
    @property
    def name(self) -> str | None:
        return self.title

    @name.setter
    def name(self, value: str | None) -> None:
        self.title = value


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship("Project", back_populates="milestones")


class ProjectActivityLog(Base):
    __tablename__ = "project_activity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    project = relationship("Project", back_populates="activity_logs")
    persona = relationship("Persona", foreign_keys=[persona_id])


class ProjectWhiteboard(Base):
    __tablename__ = "project_whiteboards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False, default="Pizarra")
    elements_json = Column(Text, nullable=False, default="[]")
    thumbnail_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="whiteboard")


class ProjectTask(Base):
    __tablename__ = "project_tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    order_index = Column(Integer, default=0)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="todo", index=True)
    priority = Column(String(20), default="medium")
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    labels = Column(JSON, default=list)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("Persona", foreign_keys=[assignee_id])
    supplies = relationship("TaskSupply", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("ProjectAttachment", back_populates="task", cascade="all, delete-orphan")
    subtasks = relationship(
        "ProjectTask",
        backref=backref("parent", remote_side="ProjectTask.id"),
        cascade="all, delete-orphan",
    )


class ProjectAttachment(Base):
    __tablename__ = "project_attachments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    task = relationship("ProjectTask", back_populates="attachments")
    uploader = relationship("Persona", foreign_keys=[uploader_id])


class TaskSupply(Base):
    __tablename__ = "task_supplies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="pending")
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("ProjectTask", back_populates="supplies")


class ProjectComment(Base):
    __tablename__ = "project_comments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    author = relationship("Persona", foreign_keys=[author_id])


class ProjectPhase(Base):
    __tablename__ = "project_phases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    slug = Column(String(20), nullable=False)
    color = Column(String(20), default="#94a3b8")
    order_index = Column(Integer, default=0)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship(
        "Project",
        backref=backref("phases", order_by="ProjectPhase.order_index", cascade="all, delete-orphan"),
    )


class ProjectInboxState(Base):
    __tablename__ = "project_inbox_state"
    __table_args__ = (UniqueConstraint("persona_id", "item_id", name="uq_persona_project_item"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(80), nullable=False)
    is_read = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ProjectDocument(Base):
    __tablename__ = "project_documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="Wiki")
    content = Column(Text, nullable=False, default="")
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    last_edited_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    project = relationship("Project")
    author = relationship("Persona", foreign_keys=[author_id])

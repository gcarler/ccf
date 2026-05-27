from backend.models_shared import *
from backend.models_shared import _utcnow

from backend.models_identity import User


# 4. PROJECTS & ACTIVITIES
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning")  # active, completed, on_hold
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    tasks = relationship(
        "ProjectTask", back_populates="project", cascade="all, delete-orphan"
    )
    milestones = relationship(
        "ProjectMilestone", back_populates="project", cascade="all, delete-orphan"
    )
    activity_logs = relationship(
        "ProjectActivityLog", back_populates="project", cascade="all, delete-orphan"
    )
    whiteboard = relationship(
        "ProjectWhiteboard",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    owner = relationship("User", foreign_keys=[owner_id])


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    project = relationship("Project", back_populates="milestones")


class ProjectActivityLog(Base):
    __tablename__ = "project_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String(50))  # 'task_created', 'milestone_completed', etc.
    description = Column(Text)
    created_at = Column(DateTime, default=_utcnow)

    project = relationship("Project", back_populates="activity_logs")
    user = relationship("User")


class ProjectWhiteboard(Base):
    __tablename__ = "project_whiteboards"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title = Column(String(200), nullable=False)
    elements_json = Column(Text, nullable=False, default="[]")
    thumbnail_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, index=True)

    project = relationship("Project", back_populates="whiteboard")


class ProjectTask(Base):
    __tablename__ = "project_tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = Column(
        Integer,
        ForeignKey("project_tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    order_index = Column(Integer, default=0)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(20), default="todo")  # todo, in_progress, review, done
    priority = Column(String(20), default="medium")  # urgent, high, medium, low
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    start_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    labels = Column(JSON, default=[])  # e.g. ["Alabanza", "Importante"]
    attachments = Column(
        JSON, default=[]
    )  # e.g. [{"name": "file.pdf", "url": "/static/uploads/file.pdf"}]
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
    supplies = relationship(
        "TaskSupply", back_populates="task", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "ProjectAttachment", back_populates="task", cascade="all, delete-orphan"
    )
    subtasks = relationship(
        "ProjectTask",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )


class ProjectAttachment(Base):
    __tablename__ = "project_attachments"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer,
        ForeignKey("project_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    task = relationship("ProjectTask", back_populates="attachments")
    uploader = relationship("User")


class TaskSupply(Base):
    __tablename__ = "task_supplies"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer,
        ForeignKey("project_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="pending")  # pending, ready, unavailable

    task = relationship("ProjectTask", back_populates="supplies")


class ProjectComment(Base):
    __tablename__ = "project_comments"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id = Column(
        Integer, ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True
    )
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class ProjectPhase(Base):
    __tablename__ = "project_phases"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(50), nullable=False)
    slug = Column(String(20), nullable=False)
    color = Column(String(20), default="#94a3b8")
    order_index = Column(Integer, default=0)

    project = relationship(
        "Project",
        backref=backref(
            "phases", order_by="ProjectPhase.order_index", cascade="all, delete-orphan"
        ),
    )


class ProjectInboxState(Base):
    __tablename__ = "project_inbox_state"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id = Column(String(80), nullable=False)
    is_read = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_project_item"),
    )


class ProjectDocument(Base):
    __tablename__ = "project_documents"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False, default="")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_edited_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    created_at = Column(DateTime, default=_utcnow, index=True)

    project = relationship("Project")
    author = relationship("User")

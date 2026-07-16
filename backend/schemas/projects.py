from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from backend.schemas._common import orm_config


def coerce_uuid_to_str(v: Any) -> str:
    if isinstance(v, uuid.UUID):
        return str(v)
    return v

UUIDStr = Annotated[str, BeforeValidator(coerce_uuid_to_str)]


class TaskSupplyBase(BaseModel):
    item_name: str
    quantity: int = 1
    status: str = "pending"


class TaskSupplyCreate(TaskSupplyBase):
    pass


class TaskSupplyUpdate(BaseModel):
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None


class TaskSupply(TaskSupplyBase):
    id: UUIDStr
    task_id: UUIDStr
    model_config = orm_config


class ProjectPhaseSchema(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    name: str
    slug: str
    color: str = "#94a3b8"
    order_index: int = 0
    model_config = orm_config


class ProjectPhaseInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    slug: str = Field(..., min_length=1, max_length=20)
    color: str = "#94a3b8"


class ProjectAttachment(BaseModel):
    id: UUIDStr
    task_id: UUIDStr
    filename: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
    model_config = orm_config


def _normalize_priority_value(v: Any) -> Any:
    """Map accepted priority aliases to canonical enums before validation."""
    if isinstance(v, str):
        return {"normal": "medium"}.get(v, v)
    return v


ProjectPriority = Annotated[
    Literal["low", "medium", "high", "urgent"],
    BeforeValidator(_normalize_priority_value),
]


def _normalize_project_status_value(v: Any) -> Any:
    """Map accepted project status aliases to canonical 5-value enum before validation.

    Task-level status is intentionally NOT normalized here because it adopts
    dynamic ``ProjectPhase.slug`` values (see ``_assert_status_in_project_phases``
    in ``backend/api/projects.py``). Only ``Project.status`` is constrained.
    """
    if isinstance(v, str):
        status_aliases = {
            "paused": "on_hold",
            "stopped": "on_hold",
            "done": "completed",
            "finished": "completed",
            "cancelled": "archived",
            "closed": "archived",
        }
        return status_aliases.get(v.lower(), v)
    return v


# Canonical ProjectStatus. The 5-value tuple mirrors the frontend
# ``PROJECT_STATUSES`` in ``frontend/src/lib/projects/constants.ts`` and the
# dropdown options in ``InlineProjectStatusPicker``.
ProjectStatus = Annotated[
    Literal["planning", "active", "on_hold", "completed", "archived"],
    BeforeValidator(_normalize_project_status_value),
]


class ProjectTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: ProjectPriority = "medium"
    assignee_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    attachments: List[ProjectAttachment] = Field(default_factory=list)

class ProjectTaskCreate(ProjectTaskBase):
    project_id: Optional[UUIDStr] = None
    parent_id: Optional[UUIDStr] = None


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[ProjectPriority] = None
    assignee_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None

class ProjectTask(ProjectTaskBase):
    id: UUIDStr
    project_id: UUIDStr
    parent_id: Optional[UUIDStr] = None
    order_index: int = 0
    supplies: List[TaskSupply] = Field(default_factory=list)
    subtasks: List["ProjectTask"] = Field(default_factory=list)
    model_config = orm_config


class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: ProjectStatus = "planning"
    owner_id: Optional[UUIDStr] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    owner_id: Optional[UUIDStr] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ProjectMilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    is_completed: Optional[bool] = False


class ProjectMilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    is_completed: Optional[bool] = None


class ProjectMilestone(ProjectMilestoneBase):
    id: UUIDStr
    project_id: UUIDStr
    model_config = orm_config


class ProjectActivityLog(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    persona_id: Optional[UUIDStr] = None
    user_name: Optional[str] = "Sistema"
    action_type: str
    description: str
    created_at: Optional[datetime] = None
    model_config = orm_config


class Project(ProjectBase):
    id: UUIDStr
    created_at: datetime
    updated_at: Optional[datetime] = None
    tasks: List[ProjectTask] = Field(default_factory=list)
    milestones: List[ProjectMilestone] = Field(default_factory=list)
    activities: List[ProjectActivityLog] = Field(default_factory=list)
    progress_percent: int = 0
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Map ORM activity_logs relationship -> activities field
        if hasattr(obj, "activity_logs") and not isinstance(obj, dict):
            obj.__dict__.setdefault("activities", list(obj.activity_logs or []))
        instance = super().model_validate(obj, **kwargs)
        # Calculate progress from tasks if not set on model
        if hasattr(obj, "tasks") and obj.tasks:
            done = sum(1 for t in obj.tasks if getattr(t, "status", "") == "completed")
            instance.progress_percent = round((done / len(obj.tasks)) * 100)
        return instance


class ProjectInboxItem(BaseModel):
    id: UUIDStr
    type: str
    user: str
    content: str
    project: str
    project_id: UUIDStr
    task_id: Optional[UUIDStr] = None
    task_title: Optional[str] = None
    is_read: bool = False
    created_at: datetime


class ProjectActivityItem(BaseModel):
    id: UUIDStr
    kind: str
    project_id: UUIDStr
    project_title: str
    task_id: Optional[UUIDStr] = None
    task_title: Optional[str] = None
    description: str
    created_at: datetime


class ProjectCommentBase(BaseModel):
    content: str
    task_id: Optional[UUIDStr] = None


class ProjectCommentCreate(ProjectCommentBase):
    pass


class ProjectCommentCreateWithProject(ProjectCommentBase):
    """Payload for the flat /projects/comments endpoint that carries the
    project_id in the request body."""

    project_id: UUIDStr


class ProjectCommentUpdate(BaseModel):
    content: Optional[str] = None
    is_resolved: Optional[bool] = None


class ProjectCommentItem(ProjectCommentBase):
    id: UUIDStr
    project_id: UUIDStr
    author_id: Optional[UUIDStr] = None
    author_name: str
    is_resolved: bool = False
    created_at: datetime
    updated_at: datetime


class InboxReadToggle(BaseModel):
    is_read: bool = True


class ProjectDocument(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    title: str
    content: Optional[str] = None
    author_id: Optional[UUIDStr] = None
    last_edited_at: Optional[datetime] = None
    created_at: datetime
    version: int = 1
    model_config = orm_config


class ProjectDocumentCreate(BaseModel):
    title: str
    content: Optional[str] = ""
    project_id: UUIDStr


class ProjectDocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


# Alias used by wiki endpoints
ProjectDocumentRead = ProjectDocument


class ProjectWhiteboard(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    title: str
    elements_json: str = "[]"
    created_at: datetime
    updated_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    model_config = orm_config


class ProjectWhiteboardUpdate(BaseModel):
    title: Optional[str] = None
    elements_json: Optional[str] = None
    thumbnail_url: Optional[str] = None


class ProjectPortfolioSummaryRow(BaseModel):
    project_status: str
    total_projects: int
    total_tasks: int
    completed_tasks: int
    completion_ratio: float


class ProjectWorkloadSummaryRow(BaseModel):
    assignee_id: Optional[str] = None
    open_tasks: int
    in_review: int
    overdue_tasks: int


# Resolve forward references for ProjectTask.subtasks
ProjectTask.model_rebuild()


class ProjectMessageCreate(BaseModel):
    content: str


class ProjectMessageItem(BaseModel):
    id: UUIDStr
    sender_id: str
    sender_name: str = ""
    content: str
    created_at: datetime
    is_read: bool = False
    model_config = orm_config

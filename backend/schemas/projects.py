from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas._common import orm_config


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
    id: int
    task_id: int
    model_config = orm_config


class ProjectPhaseSchema(BaseModel):
    id: int
    project_id: int
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
    id: int
    task_id: int
    filename: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
    model_config = orm_config


class ProjectTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    assignee_id: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    attachments: List[Any] = Field(default_factory=list)

    @field_validator("labels", mode="before")
    @classmethod
    def _coerce_labels(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class ProjectTaskCreate(ProjectTaskBase):
    project_id: Optional[int] = None
    parent_id: Optional[int] = None


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None

    @field_validator("labels", mode="before")
    @classmethod
    def _coerce_labels(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class ProjectTask(ProjectTaskBase):
    id: int
    project_id: int
    parent_id: Optional[int] = None
    order_index: int = 0
    supplies: List[TaskSupply] = Field(default_factory=list)
    subtasks: List["ProjectTask"] = Field(default_factory=list)
    model_config = orm_config


class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "planning"
    owner_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ProjectMilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    is_completed: bool = False


class ProjectMilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    is_completed: Optional[bool] = None


class ProjectMilestone(ProjectMilestoneBase):
    id: int
    project_id: int
    model_config = orm_config


class ProjectActivityLog(BaseModel):
    id: int
    project_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = "Sistema"
    action_type: str
    description: str
    created_at: Optional[datetime] = None
    model_config = orm_config


class Project(ProjectBase):
    id: int
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
    id: str
    type: str
    user: str
    content: str
    project: str
    project_id: int
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    is_read: bool = False
    created_at: datetime


class ProjectActivityItem(BaseModel):
    id: str
    kind: str
    project_id: int
    project_title: str
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    description: str
    created_at: datetime


class ProjectCommentBase(BaseModel):
    content: str
    task_id: Optional[int] = None


class ProjectCommentCreate(ProjectCommentBase):
    pass


class ProjectCommentUpdate(BaseModel):
    content: Optional[str] = None
    is_resolved: Optional[bool] = None


class ProjectCommentItem(ProjectCommentBase):
    id: int
    project_id: int
    author_id: int
    author_name: str
    is_resolved: bool = False
    created_at: datetime
    updated_at: datetime


class InboxReadToggle(BaseModel):
    is_read: bool = True


class ProjectDocument(BaseModel):
    id: int
    project_id: int
    title: str
    content: Optional[str] = None
    author_id: Optional[int] = None
    last_edited_at: Optional[datetime] = None
    created_at: datetime
    version: int = 1
    model_config = orm_config


class ProjectDocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class ProjectWhiteboard(BaseModel):
    id: int
    project_id: int
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
    assignee_id: Optional[int] = None
    open_tasks: int
    in_review: int
    overdue_tasks: int


# Resolve forward references for ProjectTask.subtasks
ProjectTask.model_rebuild()

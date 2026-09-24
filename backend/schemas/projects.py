from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from backend.schemas._common import orm_config


def coerce_uuid_to_str(v: Any) -> str:
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


UUIDStr = Annotated[str, BeforeValidator(coerce_uuid_to_str)]


class TaskSupplyBase(BaseModel):
    item_name: str
    quantity: int = Field(default=1, ge=0)
    status: Literal["pending", "ready", "unavailable"] = "pending"


class TaskSupplyCreate(TaskSupplyBase):
    pass


class TaskSupplyUpdate(BaseModel):
    item_name: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=0)
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


def _strip_str_or_passthrough(v: Any) -> Any:
    """Strip whitespace from required task title before validation.

    Empty / whitespace-only titles become ``""`` after strip, which then fails
    the ``min_length=1`` constraint in :class:`ProjectTaskBase.title` and
    :class:`ProjectTaskUpdate.title`. Returns the input untouched when it is
    not a string (``None`` is allowed for the optional PATCH path).

    Cierra ``PEND-QUALITY-TASK-CREATE-001`` (2026-07-16): la vista list
    enviaba ``title: ''`` literal desde ``ProjectViewsContent`` y quedaba
    persistido como tarea vacía.
    """
    return v.strip() if isinstance(v, str) else v


class ProjectTaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "todo"
    priority: ProjectPriority = "medium"
    assignee_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    node: Optional[str] = Field(default=None, max_length=50)
    labels: List[str] = Field(default_factory=list)
    attachments: List[ProjectAttachment] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)

    @field_validator("node", mode="before")
    @classmethod
    def _node_strip(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) and v.strip() else (None if isinstance(v, str) else v)


class ProjectTaskCreate(ProjectTaskBase):
    project_id: Optional[UUIDStr] = None
    parent_id: Optional[UUIDStr] = None


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[ProjectPriority] = None
    assignee_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    node: Optional[str] = Field(default=None, max_length=50)
    labels: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)


class ProjectTask(ProjectTaskBase):
    id: UUIDStr
    project_id: UUIDStr
    parent_id: Optional[UUIDStr] = None
    order_index: int = 0
    supplies: List[TaskSupply] = Field(default_factory=list)
    subtasks: List["ProjectTask"] = Field(default_factory=list)
    model_config = orm_config


class ProjectKPIBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    target_value: float = Field(..., gt=0)
    current_value: float = Field(default=0.0)
    unit: str = Field(default="unidades", max_length=30)
    category: str = Field(default="impact", max_length=50)
    due_date: Optional[datetime] = None


class ProjectKPICreate(ProjectKPIBase):
    pass


class ProjectKPIUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    target_value: Optional[float] = Field(default=None, gt=0)
    current_value: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=30)
    category: Optional[str] = Field(default=None, max_length=50)
    due_date: Optional[datetime] = None


class ProjectKPI(ProjectKPIBase):
    id: UUIDStr
    project_id: UUIDStr
    created_at: datetime
    updated_at: Optional[datetime] = None
    progress_percent: int = 0
    model_config = orm_config

    @classmethod
    def model_validate(cls, obj, **kwargs):
        instance = super().model_validate(obj, **kwargs)
        if instance.target_value and instance.target_value > 0:
            pct = round((instance.current_value / instance.target_value) * 100)
            instance.progress_percent = max(0, min(100, pct))
        return instance


class ProjectTaskDependencyCreate(BaseModel):
    predecessor_id: UUIDStr
    successor_id: UUIDStr
    dependency_type: Literal["FS", "SS", "FF", "SF"] = "FS"
    lag_days: int = Field(default=0, ge=0)


class ProjectTaskDependency(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    predecessor_id: UUIDStr
    successor_id: UUIDStr
    dependency_type: str = "FS"
    lag_days: int = 0
    created_at: datetime
    model_config = orm_config


class ProjectExpenseBase(BaseModel):
    category: str = Field(default="general", max_length=50)
    description: Optional[str] = None
    amount: float = Field(default=0.0, ge=0)
    date: Optional[datetime] = None
    receipt_url: Optional[str] = Field(default=None, max_length=500)
    status: Literal["planned", "committed", "paid"] = "planned"


class ProjectExpenseCreate(ProjectExpenseBase):
    amount: float = Field(..., ge=0)


class ProjectExpenseUpdate(BaseModel):
    category: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    date: Optional[datetime] = None
    receipt_url: Optional[str] = Field(default=None, max_length=500)
    status: Optional[Literal["planned", "committed", "paid"]] = None


class ProjectExpense(ProjectExpenseBase):
    id: UUIDStr
    project_id: UUIDStr
    created_by: Optional[UUIDStr] = None
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = orm_config


class ProjectBudgetSummary(BaseModel):
    project_id: UUIDStr
    budget_allocated: float = 0.0
    budget_spent: float = 0.0
    remaining_budget: float = 0.0
    burn_rate_percent: float = 0.0
    total_expenses_count: int = 0
    planned_amount: float = 0.0
    committed_amount: float = 0.0
    paid_amount: float = 0.0
    by_category: dict[str, float] = Field(default_factory=dict)
    model_config = orm_config


class ProjectRiskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="tecnico", max_length=50)
    probability: int = Field(default=3, ge=1, le=5)
    impact: int = Field(default=3, ge=1, le=5)
    mitigation_plan: Optional[str] = None
    contingency_plan: Optional[str] = None
    owner_id: Optional[UUIDStr] = None
    status: Literal["active", "mitigated", "occurred"] = "active"

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)


class ProjectRiskCreate(ProjectRiskBase):
    pass


class ProjectRiskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, max_length=50)
    probability: Optional[int] = Field(default=None, ge=1, le=5)
    impact: Optional[int] = Field(default=None, ge=1, le=5)
    mitigation_plan: Optional[str] = None
    contingency_plan: Optional[str] = None
    owner_id: Optional[UUIDStr] = None
    status: Optional[Literal["active", "mitigated", "occurred"]] = None

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)


class ProjectRisk(ProjectRiskBase):
    id: UUIDStr
    project_id: UUIDStr
    severity_score: int = 9
    severity_level: Literal["low", "medium", "high", "critical"] = "medium"
    owner_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = orm_config

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Resolve owner full name if owner relation is present
        if hasattr(obj, "owner") and getattr(obj, "owner", None) is not None:
            owner_obj = getattr(obj, "owner")
            name = getattr(owner_obj, "full_name", None) or f"{getattr(owner_obj, 'nombres', '')} {getattr(owner_obj, 'apellidos', '')}".strip()
            if name:
                if isinstance(obj, dict):
                    obj["owner_name"] = name
                else:
                    setattr(obj, "owner_name", name)
        instance = super().model_validate(obj, **kwargs)
        prob = instance.probability or 1
        imp = instance.impact or 1
        instance.severity_score = prob * imp
        if instance.severity_score >= 15:
            instance.severity_level = "critical"
        elif instance.severity_score >= 10:
            instance.severity_level = "high"
        elif instance.severity_score >= 5:
            instance.severity_level = "medium"
        else:
            instance.severity_level = "low"
        return instance


class ProjectRiskSummary(BaseModel):
    project_id: UUIDStr
    total_risks: int = 0
    active_risks: int = 0
    mitigated_risks: int = 0
    occurred_risks: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    matrix_5x5: List[dict] = Field(default_factory=list)
    by_category: dict[str, int] = Field(default_factory=dict)
    model_config = orm_config


class TaskReassignPayload(BaseModel):
    new_assignee_id: Optional[UUIDStr] = None


class ProjectWorkloadTaskItem(BaseModel):
    id: UUIDStr
    title: str
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    is_overdue: bool = False
    model_config = orm_config


class ProjectMemberWorkload(BaseModel):
    persona_id: Optional[UUIDStr] = None
    name: str = "Sin Asignar"
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    total_tasks: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    urgent_tasks: int = 0
    high_tasks: int = 0
    medium_tasks: int = 0
    low_tasks: int = 0
    capacity_status: Literal["available", "balanced", "overloaded"] = "available"
    workload_percent: int = 0
    tasks: List[ProjectWorkloadTaskItem] = Field(default_factory=list)
    model_config = orm_config


class ProjectWorkloadSummary(BaseModel):
    project_id: UUIDStr
    total_members: int = 0
    total_active_tasks: int = 0
    total_completed_tasks: int = 0
    total_overdue_tasks: int = 0
    overloaded_members_count: int = 0
    balanced_members_count: int = 0
    available_members_count: int = 0
    unassigned_tasks_count: int = 0
    members: List[ProjectMemberWorkload] = Field(default_factory=list)
    model_config = orm_config


# ============================================================================
# Critical Path Method (CPM) Schemas (Super-PRO Fase 4)
# ============================================================================

class TaskCriticalPathItem(BaseModel):
    task_id: UUIDStr
    title: str
    duration_days: int
    early_start: int
    early_finish: int
    late_start: int
    late_finish: int
    slack_days: int
    is_critical: bool
    early_start_date: Optional[datetime] = None
    early_finish_date: Optional[datetime] = None
    late_start_date: Optional[datetime] = None
    late_finish_date: Optional[datetime] = None
    model_config = orm_config


class ProjectCriticalPathSummary(BaseModel):
    project_id: UUIDStr
    total_duration_days: int
    critical_tasks_count: int
    critical_path_task_ids: List[UUIDStr] = Field(default_factory=list)
    tasks: List[TaskCriticalPathItem] = Field(default_factory=list)
    has_cycles: bool = False
    model_config = orm_config


# ============================================================================
# Project Baseline Schemas (Super-PRO Fase 4)
# ============================================================================

class ProjectBaselineCreate(BaseModel):
    name: str = Field(default="Línea Base", min_length=1, max_length=100)
    description: Optional[str] = None


class TaskBaselineComparisonItem(BaseModel):
    task_id: UUIDStr
    title: str
    baseline_start: Optional[datetime] = None
    baseline_due: Optional[datetime] = None
    baseline_duration: int = 1
    current_start: Optional[datetime] = None
    current_due: Optional[datetime] = None
    current_duration: int = 1
    variance_days: int = 0
    status: str = "todo"
    model_config = orm_config


class ProjectBaseline(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    name: str
    description: Optional[str] = None
    created_by: Optional[UUIDStr] = None
    created_at: datetime
    snapshot_data: dict = Field(default_factory=dict)
    comparisons: List[TaskBaselineComparisonItem] = Field(default_factory=list)
    total_variance_days: int = 0
    model_config = orm_config


class ProjectBaselineSummary(BaseModel):
    has_baseline: bool = False
    latest_baseline: Optional[ProjectBaseline] = None
    total_baselines: int = 0
    model_config = orm_config





class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: ProjectStatus = "planning"
    owner_id: Optional[UUIDStr] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    progress_mode: Literal["auto_tasks", "milestones", "manual"] = "auto_tasks"
    manual_progress: float = 0.0
    budget_allocated: Optional[float] = None
    budget_spent: Optional[float] = None
    health_override: Optional[Literal["on_track", "at_risk", "off_track"]] = None

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)

    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    owner_id: Optional[UUIDStr] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    progress_mode: Optional[Literal["auto_tasks", "milestones", "manual"]] = None
    manual_progress: Optional[float] = None
    budget_allocated: Optional[float] = None
    budget_spent: Optional[float] = None
    health_override: Optional[Literal["on_track", "at_risk", "off_track"]] = None


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
    kpis: List[ProjectKPI] = Field(default_factory=list)
    dependencies: List[ProjectTaskDependency] = Field(default_factory=list)
    expenses: List[ProjectExpense] = Field(default_factory=list)
    budget_summary: Optional[ProjectBudgetSummary] = None
    risks: List[ProjectRisk] = Field(default_factory=list)
    risks_summary: Optional[ProjectRiskSummary] = None
    workload_summary: Optional[ProjectWorkloadSummary] = None
    progress_percent: int = 0
    health_status: Literal["on_track", "at_risk", "off_track", "completed"] = "on_track"
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Map ORM activity_logs relationship -> activities field
        if hasattr(obj, "activity_logs") and not isinstance(obj, dict):
            obj.__dict__.setdefault("activities", list(obj.activity_logs or []))
        instance = super().model_validate(obj, **kwargs)

        # Calculate progress depending on progress_mode
        if instance.progress_mode == "manual":
            instance.progress_percent = max(0, min(100, round(instance.manual_progress or 0.0)))
        elif instance.progress_mode == "milestones" and hasattr(obj, "milestones") and obj.milestones:
            total_m = len(obj.milestones)
            done_m = sum(1 for m in obj.milestones if getattr(m, "is_completed", False))
            instance.progress_percent = round((done_m / total_m) * 100) if total_m else 0
        elif hasattr(obj, "tasks") and obj.tasks:
            done = sum(1 for t in obj.tasks if getattr(t, "status", "") == "completed")
            instance.progress_percent = round((done / len(obj.tasks)) * 100)
        else:
            instance.progress_percent = 0

        # Calculate health_status
        if instance.status == "completed":
            instance.health_status = "completed"
        elif instance.health_override:
            instance.health_status = instance.health_override
        else:
            # Automatic health derived from overdue tasks or status
            now_dt = datetime.now(timezone.utc)
            tasks_list = getattr(obj, "tasks", []) or []
            overdue_count = 0
            for t in tasks_list:
                d_date = getattr(t, "due_date", None)
                t_status = getattr(t, "status", "")
                if t_status != "completed" and d_date:
                    # Compare timezone-aware
                    d_dt = d_date if hasattr(d_date, "tzinfo") and d_date.tzinfo else d_date.replace(tzinfo=timezone.utc)
                    if d_dt < now_dt:
                        overdue_count += 1

            if overdue_count >= 2:
                instance.health_status = "off_track"
            elif overdue_count == 1:
                instance.health_status = "at_risk"
            else:
                instance.health_status = "on_track"

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


class CommentAttachment(BaseModel):
    url: str
    type: str
    name: str
    size: int


class ProjectCommentBase(BaseModel):
    content: str
    task_id: Optional[UUIDStr] = None
    attachments: List[CommentAttachment] = []
    mentions: List[UUIDStr] = []


class ProjectCommentCreate(ProjectCommentBase):
    pass


class ProjectCommentCreateWithProject(ProjectCommentBase):
    """Payload for the flat /projects/comments endpoint that carries the
    project_id in the request body."""

    project_id: UUIDStr


class ProjectCommentUpdate(BaseModel):
    content: Optional[str] = None
    is_resolved: Optional[bool] = None
    attachments: Optional[List[CommentAttachment]] = None
    mentions: Optional[List[UUIDStr]] = None


class ProjectCommentItem(ProjectCommentBase):
    id: UUIDStr
    project_id: UUIDStr
    author_id: Optional[UUIDStr] = None
    author_name: str
    is_resolved: bool = False
    created_at: datetime
    updated_at: datetime
    module_type: Literal["project", "activity", "agenda"] = "project"
    context_title: Optional[str] = None


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
    # Control de concurrencia optimista (PZ-07): el cliente envía el
    # `updated_at` que tenía al cargar la pizarra. Si el servidor detecta
    # que hubo una escritura más nueva, responde 409 para que el cliente
    # re-concilie en lugar de sobrescribir silenciosamente (last-writer-wins).
    base_updated_at: Optional[datetime] = None


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


class ProjectAnalytics(BaseModel):
    """Real computed analytics for the project master view.

    Replaces the hardcoded metrics previously rendered in
    ``ProjectMasterView`` (Velocidad / Retraso / Riesgo / Salud). All values
    are derived from the persisted task set of the project.
    """

    project_id: UUIDStr
    total_tasks: int
    completed_tasks: int
    open_tasks: int
    overdue_tasks: int
    unassigned_tasks: int
    velocity: float
    velocity_unit: str = "tareas/día"
    overdue_days: int
    risk_level: Literal["bajo", "medio", "alto"]
    risk_reason: str
    health_score: int
    health_label: Literal["óptima", "buena", "en riesgo", "crítica"]


# Resolve forward references for ProjectTask.subtasks
ProjectTask.model_rebuild()


class ProjectMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class ProjectMessageItem(BaseModel):
    id: UUIDStr
    sender_id: str
    sender_name: str = ""
    content: str
    created_at: datetime
    is_read: bool = False
    model_config = orm_config


class ProjectMemberCreate(BaseModel):
    persona_id: UUIDStr


class ProjectMember(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    persona_id: UUIDStr
    role: str = "member"
    invited_at: Optional[datetime] = None
    persona_name: Optional[str] = None
    model_config = orm_config

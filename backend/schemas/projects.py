from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from backend.schemas._common import AwareDateTime, orm_config


def coerce_uuid_to_str(v: Any) -> str:
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


UUIDStr = Annotated[str, BeforeValidator(coerce_uuid_to_str)]


def _validate_project_link_url(value: Optional[str]) -> Optional[str]:
    """Allow navigable URLs/paths while rejecting scriptable and ambiguous schemes."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if "\\" in normalized or any(ord(char) < 0x20 or ord(char) == 0x7F for char in normalized):
        raise ValueError("El enlace contiene caracteres no permitidos")
    try:
        parsed = urlsplit(normalized)
        if parsed.scheme:
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                raise ValueError("El enlace debe usar HTTP o HTTPS")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("El enlace no puede incluir credenciales")
        elif parsed.netloc or normalized.startswith("//"):
            raise ValueError("No se permiten enlaces de red relativos")
    except ValueError as exc:
        if str(exc).startswith(("El enlace", "No se permiten")):
            raise
        raise ValueError("El enlace no tiene un formato válido") from exc
    return normalized


class TaskSupplyBase(BaseModel):
    item_name: str
    quantity: int = Field(default=1, ge=0)
    status: Literal["pending", "ready", "unavailable", "received", "approved", "purchased", "paid"] = "pending"
    unit_cost: float = Field(default=0.0, ge=0.0)
    total_cost: float = Field(default=0.0, ge=0.0)


class TaskSupplyCreate(TaskSupplyBase):
    pass


class TaskSupplyUpdate(BaseModel):
    item_name: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None
    unit_cost: Optional[float] = Field(default=None, ge=0.0)
    total_cost: Optional[float] = Field(default=None, ge=0.0)


class TaskSupply(TaskSupplyBase):
    id: UUIDStr
    task_id: UUIDStr
    expense_id: Optional[UUIDStr] = None
    model_config = orm_config


class ProjectPhaseSchema(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    name: str
    slug: str
    color: str = "#94a3b8"
    order_index: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    model_config = orm_config


class ProjectPhaseInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    slug: str = Field(..., min_length=1, max_length=20)
    color: str = "#94a3b8"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @model_validator(mode="after")
    def _validate_phase_dates(self) -> ProjectPhaseInput:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date no puede ser posterior a end_date de la fase")
        return self


class ProjectAttachment(BaseModel):
    id: UUIDStr
    task_id: UUIDStr
    filename: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
    model_config = orm_config


class ProjectCharterUpdate(BaseModel):
    sponsor_id: Optional[UUID] = None
    business_case: Optional[str] = None
    strategic_justification: Optional[str] = None
    measurable_objectives: List[str] = Field(default_factory=list)
    key_assumptions: List[str] = Field(default_factory=list)
    key_constraints: List[str] = Field(default_factory=list)
    high_level_risks: List[str] = Field(default_factory=list)
    preliminary_budget: Optional[float] = Field(default=None, ge=0)
    development_approach: Literal["predictive", "agile", "hybrid"] = "hybrid"
    pmo_type: Literal["supportive", "controlling", "directive"] = "controlling"
    charter_status: Optional[Literal["draft", "authorized"]] = None


class ProjectCharterRead(ProjectCharterUpdate):
    project_id: UUID
    authorized_by: Optional[UUID] = None
    authorized_at: Optional[datetime] = None
    model_config = orm_config


class PMOPortfolioProject(BaseModel):
    project_id: UUIDStr
    title: str
    status: str
    development_approach: Literal["predictive", "agile", "hybrid"]
    pmo_type: Literal["supportive", "controlling", "directive"]
    bac: float
    ev: float
    ac: float
    cpi: float
    spi: float
    csi: float
    quadrant: Literal[
        "q1_optimal",
        "q2_cost_acceleration",
        "q3_underutilized_capacity",
        "q4_critical_emergency",
    ]
    progress_pct: float
    charter_status: Literal["draft", "authorized"]


class PMOPortfolioTotals(BaseModel):
    total_projects: int
    total_bac: float
    total_ev: float
    total_ac: float
    portfolio_cpi: float
    portfolio_spi: float
    portfolio_csi: float


class PMOPortfolioQuadrantsDistribution(BaseModel):
    q1_optimal: int
    q2_cost_acceleration: int
    q3_underutilized_capacity: int
    q4_critical_emergency: int


class PMOPortfolioMatrixResponse(BaseModel):
    portfolio_totals: PMOPortfolioTotals
    quadrants_distribution: PMOPortfolioQuadrantsDistribution
    projects_matrix: List[PMOPortfolioProject] = Field(default_factory=list)


class ProjectStakeholderCreate(BaseModel):
    persona_id: Optional[UUID] = None
    display_name: Optional[str] = Field(default=None, max_length=200)
    role_title: Optional[str] = Field(default=None, max_length=200)
    organization_or_ministry: Optional[str] = Field(default=None, max_length=200)
    power_level: int = Field(ge=1, le=5)
    interest_level: int = Field(ge=1, le=5)
    engagement_level: Literal["unaware", "resistant", "neutral", "supportive", "leading"] = "neutral"
    management_strategy: Optional[str] = None

    @model_validator(mode="after")
    def require_identity(self) -> "ProjectStakeholderCreate":
        if self.persona_id is None and not ((self.display_name or "").strip() or (self.role_title or "").strip()):
            raise ValueError("persona_id, display_name o role_title es obligatorio")
        return self


class ProjectStakeholderUpdate(BaseModel):
    persona_id: Optional[UUID] = None
    display_name: Optional[str] = Field(default=None, max_length=200)
    role_title: Optional[str] = Field(default=None, max_length=200)
    organization_or_ministry: Optional[str] = Field(default=None, max_length=200)
    power_level: Optional[int] = Field(default=None, ge=1, le=5)
    interest_level: Optional[int] = Field(default=None, ge=1, le=5)
    engagement_level: Optional[Literal["unaware", "resistant", "neutral", "supportive", "leading"]] = None
    management_strategy: Optional[str] = None


class ProjectStakeholderRead(ProjectStakeholderCreate):
    id: UUID
    project_id: UUID
    quadrant: Literal["manage_closely", "keep_satisfied", "keep_informed", "monitor"]
    model_config = orm_config


class ProjectLessonLearned(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None
    recommendation: Optional[str] = None


class ProjectClosureFinalize(BaseModel):
    deliverables_accepted_verified: bool
    financial_reconciliation_completed: bool
    final_bac: Optional[float] = Field(default=None, ge=0)
    final_ac: Optional[float] = Field(default=None, ge=0)
    operational_handover_to: Optional[str] = Field(default=None, max_length=255)
    lessons_learned: List[ProjectLessonLearned] = Field(default_factory=list)


class ProjectClosureRead(ProjectClosureFinalize):
    project_id: UUID
    closure_status: Literal["open", "closed"]
    final_variance: Optional[float] = None
    closed_by: Optional[UUID] = None
    closed_at: Optional[datetime] = None
    wiki_synced: bool = False
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

# Match persisted VARCHAR limits so oversized inputs fail validation (422)
# rather than at flush time as an internal server error.
PROJECT_TITLE_MAX_LENGTH = 200
TASK_TITLE_MAX_LENGTH = 200


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
    title: str = Field(..., min_length=1, max_length=TASK_TITLE_MAX_LENGTH)
    description: Optional[str] = None
    status: str = "todo"
    priority: ProjectPriority = "medium"
    assignee_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    node: Optional[str] = Field(default=None, max_length=50)
    component_id: Optional[UUIDStr] = None
    physical_progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    estimated_hours: float = Field(default=0.0, ge=0.0)
    labels: List[str] = Field(default_factory=list)
    attachments: List[ProjectAttachment] = Field(default_factory=list)

    @field_validator("attachments", mode="before")
    @classmethod
    def _exclude_soft_deleted_attachments(cls, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return [item for item in value if getattr(item, "deleted_at", None) is None]
        return value

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)

    @field_validator("node", mode="before")
    @classmethod
    def _node_strip(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) and v.strip() else (None if isinstance(v, str) else v)

    @model_validator(mode="after")
    def _validate_dates(self) -> ProjectTaskBase:
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValueError("start_date no puede ser posterior a due_date")
        return self


class ProjectTaskCreate(ProjectTaskBase):
    project_id: Optional[UUIDStr] = None
    parent_id: Optional[UUIDStr] = None


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=TASK_TITLE_MAX_LENGTH)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[ProjectPriority] = None
    assignee_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    node: Optional[str] = Field(default=None, max_length=50)
    component_id: Optional[UUIDStr] = None
    physical_progress_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    estimated_hours: Optional[float] = Field(default=None, ge=0.0)
    labels: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None

    @field_validator("title", mode="before")
    @classmethod
    def _title_no_blank(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)

    @model_validator(mode="after")
    def _validate_dates(self) -> ProjectTaskUpdate:
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValueError("start_date no puede ser posterior a due_date")
        return self


class ProjectTask(ProjectTaskBase):
    id: UUIDStr
    project_id: UUIDStr
    parent_id: Optional[UUIDStr] = None
    order_index: int = 0
    actual_cost: float = 0.0
    actual_hours: float = 0.0
    supplies: List[TaskSupply] = Field(default_factory=list)
    subtasks: List["ProjectTask"] = Field(default_factory=list)
    model_config = orm_config


class ProjectTaskPageItem(ProjectTask):
    project_title: Optional[str] = None


class ProjectKPIBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    target_value: float = Field(..., gt=0)
    current_value: float = Field(default=0.0)
    unit: str = Field(default="unidades", max_length=30)
    category: str = Field(default="impact", max_length=50)
    due_date: Optional[datetime] = None
    source_type: str = Field(default="manual", max_length=60)
    component_id: Optional[UUIDStr] = None


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
    source_type: Optional[str] = Field(default=None, max_length=60)
    component_id: Optional[UUIDStr] = None


class ProjectKPI(ProjectKPIBase):
    id: UUIDStr
    project_id: UUIDStr
    created_at: datetime
    updated_at: Optional[datetime] = None
    progress_percent: int = 0
    component_name: Optional[str] = None
    last_spi: Optional[float] = None
    frente: Optional[str] = None
    is_auto_synced: bool = False
    model_config = orm_config

    @classmethod
    def model_validate(cls, obj, **kwargs):
        instance = super().model_validate(obj, **kwargs)
        if instance.description and "<!--ccf_kpi_meta:" in instance.description:
            idx = instance.description.rfind("<!--ccf_kpi_meta:")
            clean = instance.description[:idx].rstrip()
            instance.description = clean if clean else None
        if instance.target_value and instance.target_value > 0:
            pct = round((instance.current_value / instance.target_value) * 100)
            instance.progress_percent = max(0, min(100, pct))
            if instance.last_spi is None:
                instance.last_spi = round(instance.current_value / instance.target_value, 4)
        instance.is_auto_synced = bool(instance.source_type and instance.source_type != "manual")
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
    status: Literal["planned", "committed", "approved", "paid"] = "planned"
    component_id: Optional[UUIDStr] = None
    task_id: Optional[UUIDStr] = None


class ProjectExpenseCreate(ProjectExpenseBase):
    amount: float = Field(..., ge=0)

    @field_validator("receipt_url")
    @classmethod
    def validate_receipt_url(cls, value: Optional[str]) -> Optional[str]:
        return _validate_project_link_url(value)


class ProjectExpenseUpdate(BaseModel):
    category: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    date: Optional[datetime] = None
    receipt_url: Optional[str] = Field(default=None, max_length=500)
    status: Optional[Literal["planned", "committed", "approved", "paid"]] = None
    component_id: Optional[UUIDStr] = None
    task_id: Optional[UUIDStr] = None

    @field_validator("receipt_url")
    @classmethod
    def validate_receipt_url(cls, value: Optional[str]) -> Optional[str]:
        return _validate_project_link_url(value)


class ProjectExpense(ProjectExpenseBase):
    id: UUIDStr
    project_id: UUIDStr
    created_by: Optional[UUIDStr] = None
    creator_name: Optional[str] = None
    task_title: Optional[str] = None
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
    work_packages_budget: float = 0.0
    contingency_reserve: float = 0.0
    management_reserve: float = 0.0
    management_reserve_pct: float = 10.0
    total_project_budget: float = 0.0
    threats_emv: float = 0.0
    opportunities_emv: float = 0.0
    net_emv: float = 0.0
    cpi_stability_rule: Optional[dict] = None
    early_warning_sentinel: Optional[dict] = None
    by_category: dict[str, float] = Field(default_factory=dict)
    model_config = orm_config


class ProjectRiskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=PROJECT_TITLE_MAX_LENGTH)
    category: str = Field(default="tecnico", max_length=50)
    risk_type: Literal["threat", "opportunity"] = "threat"
    probability: int = Field(default=3, ge=1, le=5)
    probability_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    impact: int = Field(default=3, ge=1, le=5)
    financial_impact: float = Field(default=0.0, ge=0.0)
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
    title: Optional[str] = Field(default=None, min_length=1, max_length=PROJECT_TITLE_MAX_LENGTH)
    category: Optional[str] = Field(default=None, max_length=50)
    risk_type: Optional[Literal["threat", "opportunity"]] = None
    probability: Optional[int] = Field(default=None, ge=1, le=5)
    probability_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    impact: Optional[int] = Field(default=None, ge=1, le=5)
    financial_impact: Optional[float] = Field(default=None, ge=0.0)
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
    probability_pct: float = 60.0
    financial_impact: float = 0.0
    emv: float = 0.0
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
        if instance.contingency_plan and "<!--ccf_risk_meta:" in instance.contingency_plan:
            idx = instance.contingency_plan.rfind("<!--ccf_risk_meta:")
            clean = instance.contingency_plan[:idx].rstrip()
            instance.contingency_plan = clean if clean else None
        prob = instance.probability or 1
        imp = instance.impact or 1
        if instance.probability_pct is None:
            instance.probability_pct = round(prob * 20.0, 2)
        raw_emv = (float(instance.probability_pct) / 100.0) * float(instance.financial_impact or 0.0)
        if abs(raw_emv) < 1e-9:
            instance.emv = 0.0
        else:
            instance.emv = round(-abs(raw_emv) if instance.risk_type == "opportunity" else abs(raw_emv), 2)
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
    threats_count: int = 0
    opportunities_count: int = 0
    threats_emv: float = 0.0
    opportunities_emv: float = 0.0
    total_emv: float = 0.0
    required_contingency_reserve: float = 0.0
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
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
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
    estimated_hours_total: float = 0.0
    actual_hours_logged: float = 0.0
    hours_utilization_pct: float = 0.0
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
    total_estimated_hours: float = 0.0
    total_actual_hours: float = 0.0
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
    lag_days: int = 0
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
    excluded_parent_tasks_count: int = 0
    total_lag_days: int = 0
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


# ============================================================================
# Time Tracking Schemas (Super-PRO Fase 5)
# ============================================================================

class ProjectTimeLogBase(BaseModel):
    task_id: Optional[UUIDStr] = None
    hours: float = Field(..., gt=0, le=24, description="Horas dedicadas (0-24)")
    date: Optional[datetime] = None
    description: Optional[str] = None
    is_billable: bool = True


class ProjectTimeLogCreate(ProjectTimeLogBase):
    # Optional attribution to another same-sede persona; the endpoint
    # validates tenant ownership before persisting the work log.
    persona_id: Optional[UUIDStr] = None


class ProjectTimeLog(ProjectTimeLogBase):
    id: UUIDStr
    project_id: UUIDStr
    persona_id: UUIDStr
    persona_name: Optional[str] = None
    task_title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = orm_config


class TaskTimeSummaryItem(BaseModel):
    task_id: UUIDStr
    task_title: str
    total_hours: float
    billable_hours: float
    logs_count: int
    model_config = orm_config


class MemberTimeSummaryItem(BaseModel):
    persona_id: UUIDStr
    persona_name: str
    avatar_url: Optional[str] = None
    total_hours: float
    billable_hours: float
    logs_count: int
    model_config = orm_config


class ProjectTimeTrackingSummary(BaseModel):
    project_id: UUIDStr
    total_hours: float = 0.0
    billable_hours: float = 0.0
    non_billable_hours: float = 0.0
    total_logs: int = 0
    by_task: List[TaskTimeSummaryItem] = Field(default_factory=list)
    by_member: List[MemberTimeSummaryItem] = Field(default_factory=list)
    model_config = orm_config


class ProjectExecutiveReportProject(BaseModel):
    id: UUIDStr
    title: str
    description: str
    status: str
    priority: str
    health_override: Optional[str] = None
    progress_mode: Optional[str] = None
    progress_percentage: float
    budget_allocated: float
    budget_spent: float
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    owner_name: str
    sede_id: Optional[UUIDStr] = None
    created_at: Optional[datetime] = None


class ProjectExecutiveTasksMetrics(BaseModel):
    total: int
    completed: int
    in_progress: int
    todo: int
    blocked: int
    completion_rate: float


class ProjectExecutiveRiskItem(BaseModel):
    id: UUIDStr
    title: str
    category: str
    probability: int
    impact: int
    severity: int
    status: str
    mitigation_plan: Optional[str] = None


class ProjectExecutiveRiskMatrixCell(BaseModel):
    probability: int
    impact: int
    severity_score: int
    count: int
    risk_ids: List[UUIDStr] = Field(default_factory=list)
    active_count: int


class ProjectExecutiveRiskKpis(BaseModel):
    project_id: UUIDStr
    total_risks: int
    active_risks: int
    mitigated_risks: int
    occurred_risks: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    matrix_5x5: List[ProjectExecutiveRiskMatrixCell] = Field(default_factory=list)
    by_category: dict[str, int] = Field(default_factory=dict)
    risks: List[ProjectExecutiveRiskItem] = Field(default_factory=list)


class ProjectExecutivePhaseItem(BaseModel):
    id: UUIDStr
    name: str
    order_index: int
    total_tasks: int
    completed_tasks: int
    progress_percent: float


class ProjectGovernanceSummary(BaseModel):
    charter_status: Literal["draft", "authorized"] = "draft"
    sponsor_id: Optional[UUIDStr] = None
    authorized_at: Optional[datetime] = None
    measurable_objectives_count: int = 0
    stakeholders_total: int = 0
    stakeholders_by_quadrant: dict[str, int] = Field(default_factory=lambda: {
        "manage_closely": 0,
        "keep_satisfied": 0,
        "keep_informed": 0,
        "monitor": 0,
    })
    closure_status: Literal["open", "closed"] = "open"
    deliverables_accepted_verified: bool = False
    financial_reconciliation_completed: bool = False
    lessons_learned_count: int = 0


class CcbAndQualitySummary(BaseModel):
    """Resumen ejecutivo de Control de Cambios (CCB) y Calidad (DoD / CoQ) — PMI Vol. 6 §4-§5."""

    total_change_requests: int = 0
    pending_ccb_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    net_approved_cost_delta: float = 0.0
    net_approved_schedule_days: int = 0
    tasks_dod_accepted_count: int = 0
    total_coq_cost: float = 0.0
    coq_by_category: dict = Field(default_factory=dict)
    total_leaf_tasks: int = 0
    dod_signed_off_count: int = 0
    dod_all_four_met_count: int = 0
    dod_completion_rate_pct: float = 0.0
    total_cost_of_conformance: float = 0.0
    coq_conformance_ratio_pct: float = 0.0
    total_cost_of_non_conformance: float = 0.0


class ProjectExecutiveReportData(BaseModel):
    project: ProjectExecutiveReportProject
    tasks_metrics: ProjectExecutiveTasksMetrics
    financial_kpis: ProjectBudgetSummary
    cpi_stability_rule: Optional[dict] = None
    early_warning_sentinel: Optional[dict] = None
    raid_kpis: ProjectExecutiveRiskKpis
    cpm_metrics: ProjectCriticalPathSummary
    time_metrics: ProjectTimeTrackingSummary
    phases: List[ProjectExecutivePhaseItem] = Field(default_factory=list)
    execution_matrix: Optional[dict] = Field(default_factory=dict)
    submodules_summary: Optional[dict] = Field(default_factory=dict)
    governance_summary: Optional[ProjectGovernanceSummary] = None
    kpis: List[ProjectKPI] = Field(default_factory=list)
    indicators: List[ProjectIndicator] = Field(default_factory=list)
    ccb_and_quality_summary: Optional[dict] = None
    generated_at: datetime
    organization: str
    model_config = orm_config






class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=PROJECT_TITLE_MAX_LENGTH)
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
    title: Optional[str] = Field(default=None, min_length=1, max_length=PROJECT_TITLE_MAX_LENGTH)

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
    title: str = Field(..., max_length=PROJECT_TITLE_MAX_LENGTH)
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    is_completed: Optional[bool] = False


class ProjectMilestoneUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=PROJECT_TITLE_MAX_LENGTH)
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
    execution_matrix: Optional[dict] = None
    progress_percent: int = 0
    health_status: Literal["on_track", "at_risk", "off_track", "completed"] = "on_track"
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("tasks", "milestones", mode="before")
    @classmethod
    def _exclude_soft_deleted_children(cls, value: Any) -> Any:
        if not isinstance(value, (list, tuple)):
            return value
        return [
            item
            for item in value
            if (
                item.get("deleted_at") is None
                if isinstance(item, dict)
                else getattr(item, "deleted_at", None) is None
            )
        ]

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Map ORM activity_logs relationship -> activities field
        if hasattr(obj, "activity_logs") and not isinstance(obj, dict):
            obj.__dict__.setdefault("activities", list(obj.activity_logs or []))
        instance = super().model_validate(obj, **kwargs)

        # Calculate progress depending on progress_mode
        if instance.progress_mode == "manual":
            instance.progress_percent = max(0, min(100, round(instance.manual_progress or 0.0)))
        elif instance.progress_mode == "milestones" and instance.milestones:
            total_m = len(instance.milestones)
            done_m = sum(1 for milestone in instance.milestones if milestone.is_completed)
            instance.progress_percent = round((done_m / total_m) * 100) if total_m else 0
        elif isinstance(instance.execution_matrix, dict) and instance.execution_matrix.get("rollup_hierarchy", {}).get("project_progress_pct") is not None:
            instance.progress_percent = max(
                0,
                min(100, round(float(instance.execution_matrix["rollup_hierarchy"]["project_progress_pct"]))),
            )
        elif instance.tasks:
            has_continuous = any((getattr(t, "physical_progress_pct", 0.0) or 0.0) > 0 for t in instance.tasks)
            if has_continuous:
                from backend.services.project_evm_service import _compute_tasks_weighted_progress_pct
                instance.progress_percent = max(0, min(100, round(_compute_tasks_weighted_progress_pct(instance.tasks))))
            else:
                done = sum(1 for task in instance.tasks if task.status == "completed")
                instance.progress_percent = round((done / len(instance.tasks)) * 100)
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
            overdue_count = 0
            for task in instance.tasks:
                d_date = task.due_date
                t_status = task.status
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


class ProjectSummary(ProjectBase):
    """Small project collection item; never serializes child relationships."""

    id: UUIDStr
    created_at: AwareDateTime
    updated_at: Optional[AwareDateTime] = None
    task_count: int = 0
    completed_task_count: int = 0
    in_progress_task_count: int = 0
    progress_percent: int = 0
    health_status: Literal["on_track", "at_risk", "off_track", "completed"] = "on_track"
    model_config = orm_config


class ProjectAssigneeCandidate(BaseModel):
    """Minimal same-sede identity used by the Projects assignment picker."""

    id: UUIDStr
    nombre_completo: str
    model_config = orm_config


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
    is_pinned: Optional[bool] = None
    attachments: Optional[List[CommentAttachment]] = None
    mentions: Optional[List[UUIDStr]] = None


class ProjectCommentItem(ProjectCommentBase):
    id: UUIDStr
    project_id: UUIDStr
    author_id: Optional[UUIDStr] = None
    author_name: str
    is_resolved: bool = False
    is_pinned: bool = False
    pinned_at: Optional[datetime] = None
    pinned_by: Optional[UUIDStr] = None
    pinner_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    module_type: Literal["project", "activity", "agenda"] = "project"
    context_title: Optional[str] = None


ProjectComment = ProjectCommentItem


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
    title: str = Field(..., max_length=PROJECT_TITLE_MAX_LENGTH)
    content: Optional[str] = ""
    project_id: UUIDStr


class ProjectDocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=PROJECT_TITLE_MAX_LENGTH)
    content: Optional[str] = None


# Alias used by wiki endpoints
ProjectDocumentRead = ProjectDocument


class ProjectWikiImageUpload(BaseModel):
    """Respuesta al subir una imagen para la wiki del proyecto."""

    url: str


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
    title: Optional[str] = Field(default=None, max_length=PROJECT_TITLE_MAX_LENGTH)
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
    cpi: Optional[float] = None
    spi: Optional[float] = None
    cost_variance: Optional[float] = None
    cpi_status: Optional[str] = None


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


# ── Project Templates (Super-PRO Fase 6) ───────────────────────────────────

class TemplatePhaseItem(BaseModel):
    title: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    order: int = 0
    order_index: int = 0
    slug: Optional[str] = None
    color: Optional[str] = "#94a3b8"

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("title") or data.get("name") or "Fase"
            data["title"] = val
            data["name"] = val
            ord_val = data.get("order") if data.get("order") is not None else data.get("order_index", 0)
            data["order"] = ord_val
            data["order_index"] = ord_val
            if not data.get("slug"):
                import re
                clean = re.sub(r"[^a-zA-Z0-9_]", "_", val.lower())[:20]
                data["slug"] = clean or "phase"
        return data


class TemplateTaskItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=TASK_TITLE_MAX_LENGTH)
    description: Optional[str] = None
    priority: str = "medium"
    phase_index: Optional[int] = None
    phase_name: Optional[str] = None
    duration_days: int = 1
    day_offset: int = 0
    is_milestone: bool = False


class TemplateStructure(BaseModel):
    phases: List[TemplatePhaseItem] = Field(default_factory=list)
    tasks: List[TemplateTaskItem] = Field(default_factory=list)
    default_view: Optional[str] = "kanban"
    tags: List[str] = Field(default_factory=list)


class ProjectTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = "general"
    default_budget: float = 0.0
    structure: TemplateStructure = Field(default_factory=TemplateStructure)
    is_public: bool = True


class ProjectTemplateCreate(ProjectTemplateBase):
    sede_id: Optional[UUIDStr] = None


class ProjectTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    default_budget: Optional[float] = None
    structure: Optional[TemplateStructure] = None
    is_public: Optional[bool] = None


class ProjectTemplate(ProjectTemplateBase):
    id: UUIDStr
    created_by: Optional[UUIDStr] = None
    creator_name: Optional[str] = None
    sede_id: Optional[UUIDStr] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class InstantiateProjectFromTemplate(BaseModel):
    title: str = Field(..., min_length=1, max_length=PROJECT_TITLE_MAX_LENGTH)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    budget_allocated: Optional[float] = None
    owner_id: Optional[UUIDStr] = None


class SaveProjectAsTemplate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = "general"
    is_public: bool = True


# ── Project Automations & Triggers (Super-PRO Fase 7) ───────────────────────

class ProjectAutomationRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_event: str = Field(default="task_completed", max_length=50)
    condition_data: dict = Field(default_factory=dict)
    action_type: str = Field(default="notify_assignee", max_length=50)
    action_data: dict = Field(default_factory=dict)
    is_active: bool = True


class ProjectAutomationRuleCreate(ProjectAutomationRuleBase):
    project_id: Optional[UUIDStr] = None
    sede_id: Optional[UUIDStr] = None


class ProjectAutomationRuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_event: Optional[str] = None
    condition_data: Optional[dict] = None
    action_type: Optional[str] = None
    action_data: Optional[dict] = None
    is_active: Optional[bool] = None


class ProjectAutomationRule(ProjectAutomationRuleBase):
    id: UUIDStr
    project_id: Optional[UUIDStr] = None
    execution_count: int = 0
    last_triggered_at: Optional[datetime] = None
    created_by: Optional[UUIDStr] = None
    creator_name: Optional[str] = None
    sede_id: Optional[UUIDStr] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class EvaluateAutomationPayload(BaseModel):
    trigger_event: str
    task_id: Optional[UUIDStr] = None
    context_data: Optional[dict] = Field(default_factory=dict)
    dry_run: bool = True

    def __init__(self, **data):
        if "context" in data and "context_data" not in data:
            data["context_data"] = data.pop("context")
        super().__init__(**data)


class AutomationExecutionResult(BaseModel):
    rule_id: UUIDStr
    rule_name: str
    action_type: str
    status: str
    details: Optional[str] = None


# ── Project Indicators MGA / CREMA & SPI (Super-PRO CREMA Fase 1) ───────────

class ProjectIndicatorRecordBase(BaseModel):
    period: str = Field(..., min_length=1, max_length=50)
    target_value: float = 0.0
    actual_value: float = 0.0
    spi: Optional[float] = None
    notes: Optional[str] = None
    evidence_url: Optional[str] = None
    reported_at: Optional[datetime] = None


class ProjectIndicatorRecordCreate(ProjectIndicatorRecordBase):
    indicator_id: Optional[UUIDStr] = None

    @field_validator("evidence_url")
    @classmethod
    def validate_evidence_url(cls, value: Optional[str]) -> Optional[str]:
        return _validate_project_link_url(value)


class ProjectIndicatorRecord(ProjectIndicatorRecordBase):
    id: UUIDStr
    indicator_id: UUIDStr
    reported_by: Optional[UUIDStr] = None
    reporter_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class ProjectIndicatorBase(BaseModel):
    code: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    level: str = Field(default="PRODUCTO_PRINCIPAL", max_length=50)
    calculation_type: str = Field(default="ABSOLUTO_ACUMULADO", max_length=50)
    unit_of_measure: Optional[str] = None
    baseline_value: float = 0.0
    target_value: float = 0.0
    current_value: float = 0.0
    frequency: str = Field(default="mensual", max_length=50)
    period_targets: dict = Field(default_factory=dict)
    crema_score: Optional[float] = None
    crema_evaluation: dict = Field(default_factory=dict)
    source_type: str = Field(default="manual", max_length=60)
    component_id: Optional[UUIDStr] = None


class ProjectIndicatorCreate(ProjectIndicatorBase):
    project_id: Optional[UUIDStr] = None
    sede_id: Optional[UUIDStr] = None


class ProjectIndicatorUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    level: Optional[str] = None
    calculation_type: Optional[str] = None
    unit_of_measure: Optional[str] = None
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    frequency: Optional[str] = None
    period_targets: Optional[dict] = None
    crema_score: Optional[float] = None
    crema_evaluation: Optional[dict] = None
    source_type: Optional[str] = Field(default=None, max_length=60)
    component_id: Optional[UUIDStr] = None


class ProjectIndicator(ProjectIndicatorBase):
    id: UUIDStr
    project_id: UUIDStr
    created_by: Optional[UUIDStr] = None
    creator_name: Optional[str] = None
    sede_id: Optional[UUIDStr] = None
    records_count: int = 0
    last_spi: Optional[float] = None
    component_name: Optional[str] = None
    frente: Optional[str] = None
    is_auto_synced: bool = False
    created_at: datetime
    updated_at: datetime
    records: List[ProjectIndicatorRecord] = Field(default_factory=list)
    model_config = orm_config



class ValidateCremaPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    level: Optional[str] = "PRODUCTO_PRINCIPAL"
    calculation_type: Optional[str] = "ABSOLUTO_ACUMULADO"
    unit_of_measure: Optional[str] = None
    target_value: Optional[float] = None
    frequency: Optional[str] = "mensual"


class CremaCriterionDetail(BaseModel):
    score: float
    passed: bool
    recommendations: List[str] = Field(default_factory=list)


class CremaValidationResult(BaseModel):
    score: float
    status: str
    criteria: dict
    summary: str


# ── Project User Favorites and Pinning (Super-PRO Files Fase 1) ───────────

class ProjectUserFavoriteBase(BaseModel):
    entity_type: str = Field(default="task", max_length=50)
    entity_id: UUIDStr


class ProjectUserFavorite(ProjectUserFavoriteBase):
    id: UUIDStr
    project_id: UUIDStr
    persona_id: UUIDStr
    created_at: datetime
    model_config = orm_config


class ProjectUserFavoriteToggleResponse(BaseModel):
    is_favorite: bool
    entity_type: str
    entity_id: UUIDStr
    message: str


class ProjectPinCommentPayload(BaseModel):
    is_pinned: Optional[bool] = None


# ── Bóveda Documental y Visor Universal Embebido (Super-PRO Files Fase 2) ──

class ProjectFileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(default="general", max_length=100)
    file_source: Literal["local", "drive", "dropbox", "onedrive"] = "local"
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    drive_file_id: Optional[str] = None
    task_id: Optional[UUIDStr] = None
    phase_id: Optional[UUIDStr] = None


class ProjectFileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = "general"
    file_source: Literal["local", "drive", "dropbox", "onedrive"] = "local"
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    drive_file_id: Optional[str] = None
    task_id: Optional[UUIDStr] = None
    phase_id: Optional[UUIDStr] = None


class ProjectFileLinkDrivePayload(BaseModel):
    drive_url: str = Field(..., min_length=5, description="URL pública o compartida de Google Drive / Docs")
    name: Optional[str] = Field(None, max_length=255, description="Nombre descriptivo del documento")
    description: Optional[str] = None
    category: Optional[str] = "general"
    task_id: Optional[UUIDStr] = None
    phase_id: Optional[UUIDStr] = None


class ProjectFileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    task_id: Optional[UUIDStr] = None
    phase_id: Optional[UUIDStr] = None


class ProjectFile(ProjectFileBase):
    id: UUIDStr
    project_id: UUIDStr
    embed_url: Optional[str] = None
    task_title: Optional[str] = None
    phase_name: Optional[str] = None
    uploaded_by: Optional[UUIDStr] = None
    uploader_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = orm_config


class ProjectFilesSummary(BaseModel):
    project_id: UUIDStr
    total_files: int = 0
    total_size_bytes: int = 0
    by_source: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    files: List[ProjectFile] = Field(default_factory=list)


# ── Earned Value Management (EVM) Schemas ──────────────────────────────────


class ProjectEVMMetrics(BaseModel):
    project_id: UUIDStr
    calculated_at: str
    bac: float = Field(..., description="Presupuesto total aprobado (Budget at Completion)")
    work_packages_budget: float = Field(default=0.0, description="Presupuesto de paquetes de trabajo EDT")
    contingency_reserve: float = Field(default=0.0, description="Reserva de contingencia EMV dentro de BAC")
    management_reserve: float = Field(default=0.0, description="Reserva de gestión fuera de BAC")
    management_reserve_pct: float = Field(default=10.0, description="Porcentaje de reserva de gestión")
    total_project_budget: float = Field(default=0.0, description="Presupuesto Total del Proyecto (BAC + Reserva de Gestión)")
    reserves: Optional[dict] = Field(default=None, description="Desglose canónico de reservas PMI Vol. 6 §3")
    ac: float = Field(..., description="Costo real gastado a la fecha (Actual Cost)")
    ev: float = Field(..., description="Valor ganado del avance físico (Earned Value)")
    pv: float = Field(..., description="Valor planificado según cronograma (Planned Value)")
    progress_percentage: float = Field(..., description="Porcentaje de avance físico real")
    financial_percentage: float = Field(..., description="Porcentaje de ejecución presupuestal")
    cpi: float = Field(..., description="Índice de desempeño del costo (EV / AC)")
    spi: float = Field(..., description="Índice de desempeño del cronograma (EV / PV)")
    cv: float = Field(..., description="Variación del costo (EV - AC)")
    sv: float = Field(..., description="Variación del cronograma (EV - PV)")
    cr: float = Field(..., description="Razón crítica (CPI * SPI)")
    eac: float = Field(..., description="Estimación al finalizar (BAC / CPI)")
    vac: float = Field(..., description="Variación presupuestaria al finalizar (BAC - EAC)")
    health_status: str = Field(..., description="Diagnóstico general de desempeño EVM")
    health_color: str = Field(..., description="Código de color semántico (success, warning, destructive)")
    cpi_stability_rule: Optional[dict] = Field(default=None, description="Regla del 15% de Estabilidad del CPI PMI Vol. 5 §2.1")
    early_warning_sentinel: Optional[dict] = Field(default=None, description="Protocolo Sentinel de Alerta Temprana PMI Vol. 5 §4")
    has_baseline: bool = Field(default=False, description="Indica si el proyecto tiene una línea base activa")
    baseline_id: Optional[UUIDStr] = Field(default=None, description="ID de la línea base activa")
    baseline_name: Optional[str] = Field(default=None, description="Nombre de la línea base activa")
    baseline_bac: Optional[float] = Field(default=None, description="BAC congelado en la línea base")
    baseline_progress_pct: Optional[float] = Field(default=None, description="Avance congelado en la línea base")
    baseline_variance_cost: float = Field(default=0.0, description="Variación de costo actual frente al BAC de línea base (baseline_bac - ac)")
    baseline_variance_schedule: float = Field(default=0.0, description="Variación de avance frente a línea base (progress_percentage - baseline_progress_pct)")
    recommendations: List[str] = Field(default_factory=list)


class ProjectCurveSPoint(BaseModel):
    date: str
    label: str
    pv: float
    baseline_pv: Optional[float] = None
    ev: Optional[float] = None
    ac: Optional[float] = None
    cpi: Optional[float] = None
    spi: Optional[float] = None


class ProjectCurveSResponse(BaseModel):
    project_id: UUIDStr
    summary: ProjectEVMMetrics
    points: List[ProjectCurveSPoint] = Field(default_factory=list)
    execution_matrix: Optional[dict] = None


# ── EDT Nivel 2: Componentes y Regla del 100% ──────────────────────────────


class ProjectComponentBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Código EDT/WBS del componente")
    name: str = Field(..., min_length=1, max_length=200, description="Nombre descriptivo del componente")
    description: Optional[str] = Field(default=None, description="Descripción del alcance del paquete de trabajo")
    budget_allocated: float = Field(default=0.0, ge=0.0, description="Presupuesto asignado al componente (BAC)")
    order_index: int = Field(default=0, ge=0, description="Orden de presentación en el desglose")
    color: Optional[str] = Field(default="#3b82f6", max_length=20, description="Color identificador")
    status: str = Field(default="active", max_length=20, description="Estado del componente")

    @field_validator("code", "name", mode="before")
    @classmethod
    def _strip_strings(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)


class ProjectComponentCreate(ProjectComponentBase):
    project_id: Optional[UUIDStr] = None


class ProjectComponentUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    budget_allocated: Optional[float] = Field(default=None, ge=0.0)
    order_index: Optional[int] = Field(default=None, ge=0)
    color: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None, max_length=20)

    @field_validator("code", "name", mode="before")
    @classmethod
    def _strip_strings(cls, v: Any) -> Any:
        return _strip_str_or_passthrough(v)


class ProjectComponent(ProjectComponentBase):
    id: UUIDStr
    project_id: UUIDStr
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = orm_config


class ComponentEVMMetrics(BaseModel):
    component_id: UUIDStr
    code: str
    name: str
    budget_allocated: float
    total_tasks: int = 0
    completed_tasks: int = 0
    physical_progress_pct: float = 0.0
    ev: float = 0.0
    pv: float = 0.0
    ac: float = 0.0
    cpi: float = 1.0
    spi: float = 1.0
    cv: float = 0.0
    sv: float = 0.0
    cr: float = 1.0
    financial_progress_pct: float = 0.0
    balance_gap_pct: float = 0.0
    health_status: str = "OPTIMO"
    health_color: str = "success"


class ProjectComponentDetail(ProjectComponent):
    tasks_count: int = 0
    expenses_count: int = 0
    evm: Optional[ComponentEVMMetrics] = None


class ProjectBudget100RuleValidation(BaseModel):
    project_id: UUIDStr
    project_budget_allocated: float
    components_budget_total: float
    budget_difference: float
    allocation_percentage: float
    is_rule_satisfied: bool
    is_fully_allocated: bool
    status: Literal["balanced", "under_allocated", "over_allocated", "no_project_budget"]
    components_count: int
    recommendations: List[str] = Field(default_factory=list)


class ProjectComponentsBreakdown(BaseModel):
    project_id: UUIDStr
    components: List[ProjectComponentDetail] = Field(default_factory=list)
    budget_rule: ProjectBudget100RuleValidation


# ============================================================================
# WBS / EDT Nivel 3: Paquetes de Trabajo, 3 Dimensiones y Roll-Up (Fase 3)
# ============================================================================

class TaskTimeDimension(BaseModel):
    """Dimensión 1: Tiempo y Esfuerzo (Schedule & Effort)."""
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    subtasks_estimated_hours: float = 0.0
    total_estimated_hours: float = 0.0
    model_config = orm_config


class TaskProgressDimension(BaseModel):
    """Dimensión 2: Avance Físico Continuo y Ponderado (Physical Progress 0-100%)."""
    physical_progress_pct: float = 0.0
    rolled_up_progress_pct: float = 0.0
    is_leaf: bool = True
    subtasks_count: int = 0
    completed_subtasks_count: int = 0
    weight_basis: str = "estimated_hours"  # "estimated_hours" | "equal_count"
    model_config = orm_config


class TaskCostDimension(BaseModel):
    """Dimensión 3: Costo e Imputación Financiera (Financial & Cost)."""
    direct_cost: float = 0.0
    subtasks_cost: float = 0.0
    total_cost: float = 0.0
    actual_cost: float = 0.0
    planned_cost: float = 0.0
    committed_cost: float = 0.0
    expenses_count: int = 0
    model_config = orm_config


class TaskDimensionsDetail(BaseModel):
    """Detalle unificado de las 3 Dimensiones de Control PMI para un paquete de trabajo."""
    task_id: UUIDStr
    project_id: UUIDStr
    title: str
    status: str
    priority: str = "medium"
    parent_id: Optional[UUIDStr] = None
    component_id: Optional[UUIDStr] = None
    component_name: Optional[str] = None
    time: TaskTimeDimension
    progress: TaskProgressDimension
    cost: TaskCostDimension
    expenses: List[ProjectExpense] = Field(default_factory=list)
    model_config = orm_config


class ProjectTasksRollupSummary(BaseModel):
    """Resumen de Roll-Up de tareas y paquetes de trabajo a nivel de proyecto."""
    project_id: UUIDStr
    total_tasks: int = 0
    leaf_tasks_count: int = 0
    parent_tasks_count: int = 0
    total_estimated_hours: float = 0.0
    total_actual_hours: float = 0.0
    overall_physical_progress_pct: float = 0.0
    total_expenses_cost: float = 0.0
    tasks_with_expenses_count: int = 0
    tasks_rollup: List[TaskDimensionsDetail] = Field(default_factory=list)
    model_config = orm_config


# ============================================================================
# WBS / EDT Nivel 4: Matriz de 4 Cuadrantes, Organigrama WBS y Modelos EAC (Fase 4)
# ============================================================================

class EarnedScheduleMetrics(BaseModel):
    """Métricas de Tiempo Ganado (Earned Schedule - ES) bajo estándar Lipke / PMI."""
    planned_duration_days: float = Field(..., description="Duración total planificada en días (PD)")
    actual_time_days: float = Field(..., description="Tiempo real transcurrido a la fecha en días (AT)")
    earned_schedule_days: float = Field(..., description="Tiempo ganado en unidades de tiempo (ES)")
    schedule_variance_time_days: float = Field(..., description="Variación del cronograma en tiempo SV(t) = ES - AT")
    schedule_performance_index_time: float = Field(..., description="Índice de desempeño del cronograma en tiempo SPI(t) = ES / AT")
    estimated_duration_at_completion_days: float = Field(..., description="Duración estimada al cierre EDAC = PD / SPI(t)")
    time_variance_at_completion_days: float = Field(..., description="Variación de tiempo al cierre TVAC = PD - EDAC")
    projected_finish_date: Optional[str] = Field(default=None, description="Fecha de culminación proyectada (ISO)")
    model_config = orm_config


class EACForecastModel(BaseModel):
    """Modelo de Pronóstico a la Conclusión (EAC, ETC, VAC)."""
    model_key: Literal["typical", "atypical", "composite"]
    title: str
    description: str
    formula: str
    eac: float = Field(..., description="Estimate at Completion")
    etc: float = Field(..., description="Estimate to Complete = EAC - AC")
    vac: float = Field(..., description="Variance at Completion = BAC - EAC")
    vac_percentage: float = Field(..., description="Variación porcentual respecto a BAC")
    model_config = orm_config


class TCPIMetrics(BaseModel):
    """Índice de Desempeño del Trabajo por Completar (TCPI)."""
    tcpi_bac: Optional[float] = Field(default=None, description="TCPI requerido para cumplir el presupuesto BAC")
    tcpi_eac: Optional[float] = Field(default=None, description="TCPI requerido para cumplir el pronóstico EAC típico")
    is_budget_depleted: bool = Field(default=False, description="Indica si el presupuesto BAC ya fue consumido")
    difficulty_level: Literal["feasible", "moderate", "hard", "critical"] = Field(default="feasible")
    explanation: str
    model_config = orm_config


class EarlyWarningAlert(BaseModel):
    """Alerta temprana de desviación según la Regla del 15% PMI."""
    metric: str
    level: Literal["critical", "warning", "info"]
    title: str
    detail: str
    threshold: str
    current_value: float
    model_config = orm_config


class CPIversusSPIQuadrant(BaseModel):
    """Matriz de 4 Cuadrantes CPI vs SPI."""
    quadrant_id: Literal["quadrant_1", "quadrant_2", "quadrant_3", "quadrant_4"]
    quadrant_number: int
    name: str
    health_status: Literal["OPTIMO", "RIESGO", "CRITICO", "ATENCION"]
    badge_color: Literal["success", "warning", "destructive", "accent"]
    description: str
    action_recommendation: str
    cpi: float
    spi: float
    point_x_pct: float
    point_y_pct: float
    rule_15_triggered: bool = False
    alerts: List[EarlyWarningAlert] = Field(default_factory=list)
    model_config = orm_config


class ProjectEVMAdvancedResponse(BaseModel):
    """Respuesta consolidada de EVM Avanzado: Matriz de 4 Cuadrantes, Pronósticos EAC, ES y TCPI."""
    project_id: UUIDStr
    calculated_at: str
    standard_evm: ProjectEVMMetrics
    earned_schedule: EarnedScheduleMetrics
    forecast_models: Dict[str, EACForecastModel]
    tcpi: TCPIMetrics
    quadrant: CPIversusSPIQuadrant
    early_warnings: List[EarlyWarningAlert] = Field(default_factory=list)
    reserves: Optional[dict] = None
    cpi_stability_rule: Optional[dict] = None
    early_warning_sentinel: Optional[dict] = None
    model_config = orm_config


class WBSNode(BaseModel):
    """Nodo jerárquico del Organigrama / Árbol WBS."""
    id: str
    wbs_code: str
    title: str
    description: Optional[str] = None
    type: Literal["project", "component", "task"]
    level: int
    status: str
    progress_pct: float
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    budget_allocated: Optional[float] = None
    cost: float = 0.0
    is_leaf: bool = True
    health_status: Optional[str] = None
    children: List[WBSNode] = Field(default_factory=list)
    model_config = orm_config


class ProjectWBSTreeResponse(BaseModel):
    """Respuesta del Organigrama / Árbol de EDT jerárquica con codificación automática recursiva."""
    project_id: UUIDStr
    project_title: str
    total_nodes: int
    max_depth: int
    root: WBSNode
    model_config = orm_config


class DocumentConversionResponse(BaseModel):
    """Respuesta del motor AnyDoc tras procesar un documento."""
    filename: str
    format: str
    markdown: str
    char_count: int
    word_count: int
    processing_time_ms: float
    engine: str = "anydoc_v0.2.4"
    success: bool = True
    error: Optional[str] = None
    model_config = orm_config


class ConvertAndPublishWikiRequest(BaseModel):
    """Petición para convertir un documento y publicarlo como Wiki del Proyecto o Wiki Ministerial."""
    filename: str
    content_base64: Optional[str] = None
    format_hint: Optional[str] = None
    target_type: Literal["project_wiki", "platform_wiki"] = "project_wiki"
    title: Optional[str] = None
    category: Optional[str] = "proyectos"
    tags: List[str] = Field(default_factory=list)
    model_config = orm_config


class ConvertAndPublishWikiResponse(BaseModel):
    """Respuesta tras convertir y publicar documento en Wiki."""
    conversion: DocumentConversionResponse
    published_to: str
    document_id: Optional[str] = None
    page_key: Optional[str] = None
    title: str
    message: str
    model_config = orm_config


class PMIKnowledgeVolumeSchema(BaseModel):
    """Metadatos y contenido de un volumen de doctrina PMI."""
    vol: int
    page_key: str
    file_name: str
    title: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    char_count: int = 0
    word_count: int = 0
    content: Optional[str] = None
    model_config = orm_config


class PMIDoctrineIndexResponse(BaseModel):
    """Respuesta del compendio canónico de doctrina PMI."""
    total_volumes: int
    volumes: List[PMIKnowledgeVolumeSchema]
    kb_indexed_count: int = 0
    wiki_seeded_count: int = 0
    model_config = orm_config


class ProjectLabelItem(BaseModel):
    """Etiqueta de proyecto con conteo de tareas activas."""
    name: str
    task_count: int = 0
    model_config = orm_config


class ProjectLabelRenameInput(BaseModel):
    """Entrada para renombrar una etiqueta a nivel de proyecto."""
    old_name: str
    new_name: str


class ProjectExecutionSyncRequest(BaseModel):
    """Petición para sincronizar y/o autogenerar indicadores Pro y KPIs desde la ejecución real."""
    seed_pro_families: Optional[bool] = None
    seed_pro_indicators: Optional[bool] = None
    seed_kpis: Optional[bool] = None
    seed_pro_kpis: Optional[bool] = None
    period_label: Optional[str] = None
    record_period: Optional[str] = None


class ProjectExecutionSyncResponse(BaseModel):
    """Respuesta tras sincronizar la Matriz de Indicadores y KPIs con los 3 Frentes de ejecución."""
    project_id: UUIDStr
    synced_indicators: int = 0
    seeded_indicators: int = 0
    synced_kpis: int = 0
    seeded_kpis: int = 0
    synced_indicators_count: int = 0
    seeded_indicators_count: int = 0
    synced_kpis_count: int = 0
    seeded_kpis_count: int = 0
    execution_matrix: dict = Field(default_factory=dict)
    indicators: List[ProjectIndicator] = Field(default_factory=list)
    kpis: List[ProjectKPI] = Field(default_factory=list)
    model_config = orm_config


ProjectExecutiveReportData.model_rebuild()

# ============================================================================
# Control Integrado de Cambios (CCB) — PMI Vol. 6 §5
# ============================================================================

CRChangeType = Literal["scope", "schedule", "budget", "integrated"]
CRStatus = Literal["pending_ccb", "approved", "rejected"]


class ProjectChangeRequestCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    justification: str = Field(..., min_length=1)
    change_type: CRChangeType = "integrated"
    cost_impact_delta: float = Field(default=0.0)
    schedule_impact_days: int = Field(default=0)
    scope_impact_summary: Optional[str] = None


class ProjectChangeRequestDecide(BaseModel):
    decision: Literal["approved", "rejected"]
    review_notes: str = Field(..., min_length=1)


class ProjectChangeRequest(BaseModel):
    id: UUIDStr
    project_id: UUIDStr
    title: str
    justification: str
    change_type: str
    cost_impact_delta: float
    schedule_impact_days: int
    scope_impact_summary: Optional[str] = None
    status: str
    requested_by: UUIDStr
    reviewed_by: Optional[UUIDStr] = None
    review_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    resulting_baseline_id: Optional[UUIDStr] = None
    model_config = orm_config


class ProjectChangeRequestSummary(BaseModel):
    pending_ccb: int = 0
    approved: int = 0
    rejected: int = 0
    approved_cost_impact_total: float = 0.0
    approved_schedule_impact_days_total: int = 0
    pending_cost_impact_total: float = 0.0
    pending_schedule_impact_days_total: int = 0


class ProjectChangeRequestListResponse(BaseModel):
    project_id: UUIDStr
    items: List[ProjectChangeRequest] = Field(default_factory=list)
    summary: ProjectChangeRequestSummary = Field(default_factory=ProjectChangeRequestSummary)


# ============================================================================
# Criterios de Aceptación (DoD / Validate Scope) — PMI Vol. 6 §4
# ============================================================================

CoQClassification = Literal["prevention", "appraisal", "internal_failure", "external_failure"]


class ProjectDodAcceptanceUpdate(BaseModel):
    specification_met: bool = False
    tests_no_critical_failures: bool = False
    evidence_archived: bool = False
    supervisor_sign_off: bool = False
    coq_classification: Optional[CoQClassification] = None
    coq_amount: Optional[float] = None


class ProjectDodAcceptance(BaseModel):
    task_id: UUIDStr
    project_id: UUIDStr
    specification_met: bool
    tests_no_critical_failures: bool
    evidence_archived: bool
    supervisor_sign_off: bool
    status: str
    accepted_by: Optional[UUIDStr] = None
    accepted_at: Optional[datetime] = None
    coq_classification: Optional[str] = None
    coq_amount: Optional[float] = None
    model_config = orm_config


# ============================================================================
# Helpers PMI: WBS (Vol. 6 §5.3) y Matriz de Riesgos 5x5 (Vol. 6 §11.3)
# ============================================================================


def normalize_wbs_component_code(code: Optional[str]) -> Optional[str]:
    """Normaliza el código de componente WBS (PMI): `edt 1.1` → `EDT-1.1`.

    - `None` → `None`; espacios internos → `-`; mayúsculas; vacío → `None`.
    - Los guiones bajos del código se conservan (`cmp_02` → `CMP_02`).
    """
    if code is None:
        return None
    stripped = re.sub(r"\s+", "-", str(code).strip()).upper()
    return stripped if stripped else None


def validate_pmi_severity_matrix_bounds(probability: int, impact: int) -> dict:
    """Clampa y puntúa un riesgo en la matriz 5x5 de PMI (probabilidad × impact).

    Ambas entradas se reclaman al rango 1..5 (default 1 al ser inválidas/0).
    Banda de severidad: 'critical' (score ≥ 15), 'high' (≥ 10),
    'moderate' (≥ 5) y 'low' en el resto.
    """
    p = max(1, min(5, int(probability or 1)))
    i = max(1, min(5, int(impact or 1)))
    score = p * i
    if score >= 15:
        severity_band = "critical"
    elif score >= 10:
        severity_band = "high"
    elif score >= 5:
        severity_band = "moderate"
    else:
        severity_band = "low"
    return {
        "probability": p,
        "impact": i,
        "severity_score": score,
        "severity_band": severity_band,
    }


def validate_milestone_weights_distribution(
    weights: Optional[List[float | int]] = None,
) -> dict:
    """Audita la ponderación de hitos bajo la técnica PMI EVMT Weighted Milestones (§3.4)."""
    valid_weights: List[float] = []
    for w in weights or []:
        if w is None or isinstance(w, bool):
            continue
        if isinstance(w, (int, float)):
            valid_weights.append(float(w))

    total_milestones = len(valid_weights)
    positive_weight_count = sum(1 for w in valid_weights if w > 0.0)
    zero_or_negative_count = sum(1 for w in valid_weights if w <= 0.0)
    total_weight = round(sum(max(0.0, w) for w in valid_weights), 2)

    normalized_shares_pct = [
        round((max(0.0, w) / total_weight) * 100.0, 2) if total_weight > 0.0 else 0.0
        for w in valid_weights
    ]
    max_share_pct = max(normalized_shares_pct) if normalized_shares_pct else 0.0

    is_balanced = bool(
        (
            total_milestones > 0
            and zero_or_negative_count == 0
            and total_weight > 0.0
            and max_share_pct <= 80.0
        )
        or (
            total_milestones == 1
            and zero_or_negative_count == 0
            and total_weight > 0.0
        )
    )

    return {
        "total_milestones": total_milestones,
        "positive_weight_count": positive_weight_count,
        "zero_or_negative_count": zero_or_negative_count,
        "total_weight": total_weight,
        "normalized_shares_pct": normalized_shares_pct,
        "max_share_pct": max_share_pct,
        "is_balanced": is_balanced,
    }

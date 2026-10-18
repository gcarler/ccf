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


def validate_raci_assignment_matrix(
    assignments: Optional[List[dict]] = None,
) -> dict:
    """Audita una matriz de asignación de responsabilidades RACI según PMI PMBOK §9.1.2.2."""
    role_map = {
        "R": "R",
        "RESPONSIBLE": "R",
        "A": "A",
        "ACCOUNTABLE": "A",
        "C": "C",
        "CONSULTED": "C",
        "I": "I",
        "INFORMED": "I",
    }

    responsible_count = 0
    accountable_count = 0
    consulted_count = 0
    informed_count = 0
    invalid_role_count = 0

    for item in assignments or []:
        if not isinstance(item, dict):
            continue
        raw_role = str(item.get("raci_role") or item.get("role") or "").strip().upper()
        normalized = role_map.get(raw_role)
        if normalized == "R":
            responsible_count += 1
        elif normalized == "A":
            accountable_count += 1
        elif normalized == "C":
            consulted_count += 1
        elif normalized == "I":
            informed_count += 1
        else:
            invalid_role_count += 1

    has_single_accountable = bool(accountable_count == 1)
    has_at_least_one_responsible = bool(responsible_count >= 1)
    is_raci_compliant = bool(
        has_single_accountable and has_at_least_one_responsible and invalid_role_count == 0
    )

    if is_raci_compliant:
        raci_violation_reason = "none"
    elif accountable_count == 0:
        raci_violation_reason = "missing_accountable"
    elif accountable_count > 1:
        raci_violation_reason = "multiple_accountable"
    elif responsible_count == 0:
        raci_violation_reason = "missing_responsible"
    else:
        raci_violation_reason = "invalid_role"

    return {
        "responsible_count": responsible_count,
        "accountable_count": accountable_count,
        "consulted_count": consulted_count,
        "informed_count": informed_count,
        "invalid_role_count": invalid_role_count,
        "has_single_accountable": has_single_accountable,
        "has_at_least_one_responsible": has_at_least_one_responsible,
        "is_raci_compliant": is_raci_compliant,
        "raci_violation_reason": raci_violation_reason,
    }


THREAT_STRATEGIES = {"avoid", "mitigate", "transfer", "escalate", "accept"}
OPPORTUNITY_STRATEGIES = {"exploit", "enhance", "share", "escalate", "accept"}
PMI_VALID_RISK_TYPES = {"threat", "opportunity"}


def validate_pmi_risk_response_strategy(
    risk_type: Optional[str] = "threat",
    strategy: Optional[str] = None,
    contingency_reserve: float = 0.0,
) -> dict:
    """Valida la estrategia de respuesta a riesgos PMI (PMBOK §11.5, Plan Risk Responses).

    Normaliza `risk_type` (default 'threat' si vacío/None) y `strategy`
    (default '' si None), y consulta los conjuntos canónicos:
    - THREAT_STRATEGIES: avoid / mitigate / transfer / escalate / accept.
    - OPPORTUNITY_STRATEGIES: exploit / enhance / share / escalate / accept.
    La contingencia se clampa a >= 0.0 y se redondea a 2 decimales; cuando
    la estrategia es 'accept', la contingencia > 0 implica aceptación
    activa y la contingencia == 0 aceptación pasiva.
    `response_validity_status`:
    - 'invalid_risk_type' si el tipo no es threat/opportunity;
    - 'missing_strategy' si la estrategia viene vacía;
    - 'misaligned_strategy' si la estrategia no pertenece a su tipo;
    - 'valid_response' si la estrategia es válida y alineada.
    """
    risk_type_norm = str(risk_type or "").strip().lower() or "threat"
    if risk_type_norm not in PMI_VALID_RISK_TYPES:
        risk_type_norm = str(risk_type or "").strip().lower()
    strategy_norm = str(strategy or "").strip().lower()
    contingency = round(max(0.0, float(contingency_reserve or 0.0)), 2)

    is_valid_risk_type = risk_type_norm in PMI_VALID_RISK_TYPES
    allowed_strategies = (
        sorted(THREAT_STRATEGIES if risk_type_norm == "threat" else OPPORTUNITY_STRATEGIES)
        if is_valid_risk_type
        else []
    )
    is_aligned_strategy = bool(is_valid_risk_type and strategy_norm in allowed_strategies)

    if strategy_norm != "accept":
        acceptance_mode = "not_applicable"
    elif contingency > 0:
        acceptance_mode = "active_acceptance"
    else:
        acceptance_mode = "passive_acceptance"

    if not is_valid_risk_type:
        response_validity_status = "invalid_risk_type"
    elif not strategy_norm:
        response_validity_status = "missing_strategy"
    elif not is_aligned_strategy:
        response_validity_status = "misaligned_strategy"
    else:
        response_validity_status = "valid_response"

    return {
        "risk_type": risk_type_norm,
        "strategy": strategy_norm,
        "contingency_reserve": contingency,
        "is_valid_risk_type": is_valid_risk_type,
        "is_aligned_strategy": is_aligned_strategy,
        "acceptance_mode": acceptance_mode,
        "allowed_strategies": allowed_strategies,
        "response_validity_status": response_validity_status,
    }


def classify_stakeholder_power_interest_quadrant(
    power_score: int | float | None,
    interest_score: int | float | None,
    high_threshold: int = 3,
) -> dict[str, Any]:
    """Clasifica un interesado en la matriz Poder-Interés según PMI PMBOK §13.1.2.4."""
    is_clamped = False

    if power_score is None:
        is_clamped = True
        power = 1
    else:
        raw_power = int(round(float(power_score)))
        if raw_power < 1 or raw_power > 5:
            is_clamped = True
        power = min(5, max(1, raw_power))

    if interest_score is None:
        is_clamped = True
        interest = 1
    else:
        raw_interest = int(round(float(interest_score)))
        if raw_interest < 1 or raw_interest > 5:
            is_clamped = True
        interest = min(5, max(1, raw_interest))

    cutoff = min(5, max(2, int(high_threshold or 3)))
    is_high_power = power >= cutoff
    is_high_interest = interest >= cutoff
    salience_index = power * interest

    if is_high_power and is_high_interest:
        quadrant_code = "manage_closely"
        recommended_strategy = (
            "Involucrar activamente y gestionar de cerca en decisiones clave"
        )
    elif is_high_power and not is_high_interest:
        quadrant_code = "keep_satisfied"
        recommended_strategy = "Mantener satisfecho sin saturar con detalles operativos"
    elif not is_high_power and is_high_interest:
        quadrant_code = "keep_informed"
        recommended_strategy = (
            "Mantener informado periódicamente y consultar en su área"
        )
    else:
        quadrant_code = "monitor"
        recommended_strategy = "Monitorear con esfuerzo mínimo de comunicación"

    return {
        "power": power,
        "interest": interest,
        "salience_index": salience_index,
        "is_high_power": is_high_power,
        "is_high_interest": is_high_interest,
        "is_clamped": is_clamped,
        "quadrant_code": quadrant_code,
        "recommended_strategy": recommended_strategy,
    }


def validate_risk_emv_exposure(
    probability_pct: float | None,
    financial_impact: float | None,
    risk_type: str | None = "threat",
) -> dict[str, Any]:
    """Calcula y valida el Valor Monetario Esperado (EMV = P * I) según PMI PMBOK §11.4.2.5."""
    risk_type_norm = (risk_type or "threat").strip().lower() or "threat"
    is_valid_risk_type = risk_type_norm in {"threat", "opportunity"}

    if probability_pct is None:
        raw_prob = 0.0
        is_prob_clamped = True
    else:
        raw_prob = float(probability_pct)
        is_prob_clamped = raw_prob < 0.0 or raw_prob > 100.0

    prob_pct = round(min(100.0, max(0.0, raw_prob)), 2)
    prob_decimal = round(prob_pct / 100.0, 4)

    abs_impact = round(abs(float(financial_impact or 0.0)), 2)
    emv_magnitude = round(prob_decimal * abs_impact, 2)
    signed_emv = (
        -emv_magnitude
        if (risk_type_norm == "threat" and emv_magnitude > 0)
        else (emv_magnitude if risk_type_norm == "opportunity" else 0.0)
    )

    if not is_valid_risk_type:
        emv_exposure_tier = "invalid_risk_type"
    elif emv_magnitude == 0.0:
        emv_exposure_tier = "zero_exposure"
    elif emv_magnitude >= 10000.0:
        emv_exposure_tier = "high_financial_exposure"
    elif emv_magnitude >= 1000.0:
        emv_exposure_tier = "moderate_financial_exposure"
    else:
        emv_exposure_tier = "minor_financial_exposure"

    return {
        "risk_type": risk_type_norm,
        "is_valid_risk_type": is_valid_risk_type,
        "probability_pct": prob_pct,
        "probability_decimal": prob_decimal,
        "is_prob_clamped": is_prob_clamped,
        "impact_magnitude": abs_impact,
        "emv_magnitude": emv_magnitude,
        "signed_emv": signed_emv,
        "emv_exposure_tier": emv_exposure_tier,
    }


def validate_ccb_change_request_justification(
    title: str | None,
    justification: str | None,
    cost_impact: float | int | None = 0.0,
    schedule_days_impact: int | float | None = 0,
) -> dict[str, Any]:
    """Valida la justificación de una solicitud de cambio (Change Request — PMI PMBOK §4.6).

    Evalúa título, justificación, y el impacto contra el baseline (costo/duracion):
    - `has_baseline_impact`: True si el costo o la duración cambian (delta != 0).
    - `is_valid`: título >= 5 chars y justificación >= 20 chars con impacto en
      baseline (>= 10 chars administrativa sin impacto).
    - `impact_tier`: 'HIGH_BASELINE_IMPACT' si |costo| >= 5000.0 o |dias| >= 10.0;
      'MODERATE_BASELINE_IMPACT' con impacto distinto de cero; y
      'ADMINISTRATIVE_NO_BASELINE_SHIFT' sin impacto en baseline.
    - `posture`: 'REJECTED_INSUFFICIENT_JUSTIFICATION' si is_valid es False;
      'CCB_FORMAL_BOARD_REVIEW' para impacto alto;
      'PM_DELEGATED_APPROVAL_ELIGIBLE' para impacto moderado; y
      'FAST_TRACK_ADMINISTRATIVE' sin impacto en baseline.
    """
    clean_title = (title or "").strip()
    clean_justification = (justification or "").strip()
    cost_delta = round(float(cost_impact or 0.0), 2)
    schedule_delta_days = round(float(schedule_days_impact or 0), 2)

    has_baseline_impact = bool(
        abs(cost_delta) > 0.0 or abs(schedule_delta_days) > 0.0
    )
    is_valid = bool(
        len(clean_title) >= 5
        and (
            len(clean_justification) >= 20
            if has_baseline_impact
            else len(clean_justification) >= 10
        )
    )

    if abs(cost_delta) >= 5000.0 or abs(schedule_delta_days) >= 10.0:
        impact_tier = "HIGH_BASELINE_IMPACT"
    elif has_baseline_impact:
        impact_tier = "MODERATE_BASELINE_IMPACT"
    else:
        impact_tier = "ADMINISTRATIVE_NO_BASELINE_SHIFT"

    if not is_valid:
        posture = "REJECTED_INSUFFICIENT_JUSTIFICATION"
    elif impact_tier == "HIGH_BASELINE_IMPACT":
        posture = "CCB_FORMAL_BOARD_REVIEW"
    elif impact_tier == "MODERATE_BASELINE_IMPACT":
        posture = "PM_DELEGATED_APPROVAL_ELIGIBLE"
    else:
        posture = "FAST_TRACK_ADMINISTRATIVE"

    return {
        "clean_title": clean_title,
        "clean_justification": clean_justification,
        "cost_delta": cost_delta,
        "schedule_delta_days": schedule_delta_days,
        "has_baseline_impact": has_baseline_impact,
        "is_valid": is_valid,
        "impact_tier": impact_tier,
        "posture": posture,
    }


def validate_milestone_deliverable_gate(
    title: str | None,
    acceptance_criteria: str | None,
    due_date: str | None,
    progress_pct: float | int | None = 0.0,
) -> dict[str, Any]:
    """Valida un hito (milestone) y sus criterios de aceptación según PMI PMBOK §6.2 (Define Activities) y §5.5 (Validate Scope)."""
    clean_title = (title or "").strip()
    clean_criteria = (acceptance_criteria or "").strip()
    clean_due_date = (due_date or "").strip()
    safe_progress = max(0.0, min(100.0, round(float(progress_pct or 0.0), 2)))

    has_valid_title = bool(len(clean_title) >= 5)
    has_acceptance_criteria = bool(len(clean_criteria) >= 15)
    has_due_date = bool(len(clean_due_date) >= 8)
    is_gate_ready = bool(
        has_valid_title and has_acceptance_criteria and has_due_date
    )

    if not has_valid_title or not has_due_date:
        posture = "INVALID_MILESTONE_SPEC"
    elif not has_acceptance_criteria:
        posture = "MISSING_ACCEPTANCE_CRITERIA"
    elif safe_progress >= 100.0:
        posture = "MILESTONE_GATE_VERIFIED"
    else:
        posture = "MILESTONE_IN_EXECUTION"

    return {
        "clean_title": clean_title,
        "clean_criteria": clean_criteria,
        "clean_due_date": clean_due_date,
        "safe_progress": safe_progress,
        "has_valid_title": has_valid_title,
        "has_acceptance_criteria": has_acceptance_criteria,
        "has_due_date": has_due_date,
        "is_gate_ready": is_gate_ready,
        "posture": posture,
    }


def validate_wbs_code_hierarchy(
    wbs_code: str | None,
    parent_wbs_code: str | None = None,
    max_depth: int | None = 5,
) -> dict[str, Any]:
    """Valida la jerarquía y nivel de descomposición de un código WBS según PMI PMBOK §5.4 (Create WBS)."""
    clean_code = (wbs_code or "").strip()
    clean_parent = (parent_wbs_code or "").strip()
    safe_max_depth = max(1, int(max_depth or 5))
    is_valid_format = bool(re.fullmatch(r"[1-9]\d*(\.[1-9]\d*)*", clean_code))
    segments = clean_code.split(".") if is_valid_format else []
    depth = len(segments)
    parent_aligned = (
        True
        if not clean_parent
        else bool(
            is_valid_format and depth >= 2 and ".".join(segments[:-1]) == clean_parent
        )
    )
    exceeds_max_depth = bool(is_valid_format and depth > safe_max_depth)
    is_valid = bool(is_valid_format and parent_aligned and not exceeds_max_depth)

    if not is_valid_format:
        posture = "MALFORMED_WBS_CODE"
    elif not parent_aligned:
        posture = "ORPHAN_PARENT_MISMATCH"
    elif exceeds_max_depth:
        posture = "EXCESSIVE_WBS_DECOMPOSITION"
    elif depth == 1:
        posture = "ROOT_CONTROL_ACCOUNT"
    else:
        posture = "VALID_WORK_PACKAGE_WBS"

    return {
        "clean_code": clean_code,
        "clean_parent": clean_parent,
        "safe_max_depth": safe_max_depth,
        "is_valid_format": is_valid_format,
        "segments": segments,
        "depth": depth,
        "parent_aligned": parent_aligned,
        "exceeds_max_depth": exceeds_max_depth,
        "is_valid": is_valid,
        "posture": posture,
    }


def validate_resource_allocation_utilization(
    assigned_hours: float | int | None,
    capacity_hours: float | int | None = 40.0,
    max_utilization_pct: float | int | None = 100.0,
) -> dict[str, Any]:
    """Valida la carga y sobreasignación de recursos según PMI PMBOK §9.2 (Estimate Activity Resources) y §9.6 (Control Resources)."""
    safe_assigned = max(0.0, round(float(assigned_hours or 0.0), 2))
    safe_capacity = max(0.0, round(float(capacity_hours or 0.0), 2))
    safe_max_pct = max(10.0, round(float(max_utilization_pct or 100.0), 2))

    utilization_pct = (
        round((safe_assigned / safe_capacity) * 100.0, 2)
        if safe_capacity > 0
        else (100.0 if safe_assigned > 0 else 0.0)
    )
    overallocated_hours = round(
        max(0.0, safe_assigned - (safe_capacity * (safe_max_pct / 100.0))), 2
    )
    is_overallocated = bool(safe_capacity == 0.0 and safe_assigned > 0.0) or bool(
        utilization_pct > safe_max_pct
    )

    if safe_capacity == 0.0:
        posture = "ZERO_CAPACITY_UNAVAILABLE"
    elif utilization_pct > safe_max_pct:
        posture = "RESOURCE_OVERALLOCATED"
    elif not is_overallocated and utilization_pct >= 70.0:
        posture = "OPTIMAL_RESOURCE_LOAD"
    else:
        posture = "UNDERUTILIZED_CAPACITY"

    return {
        "safe_assigned": safe_assigned,
        "safe_capacity": safe_capacity,
        "safe_max_pct": safe_max_pct,
        "utilization_pct": utilization_pct,
        "overallocated_hours": overallocated_hours,
        "is_overallocated": is_overallocated,
        "posture": posture,
    }



def validate_schedule_dependency_lead_lag(
    dependencies: Optional[list[dict]],
    max_lag_days: int = 30,
) -> dict:
    """Valida la red de dependencias del cronograma (PMBOK §6.3 — FS/SS/FF/SF, lead/lag).

    Cada dict suele declarar `predecessor_id`, `successor_id`, `type`/
    `relationship` (FS|SS|FF|SF case-insensitive, default 'FS') y `lag_days`
    (default 0; admite lead negativo):
    - `self_dependency_ids`: ids con predecessor == successor no vacío
      (circular self-link).
    - `invalid_relationship_types`: valores declarados fuera de la gramática.
    - `excessive_lag_links`: enlaces 'pred->succ' con abs(lag) > max_lag_days.
    - `sf_relationship_count`: conteo de dependencias SF.
    - `is_valid`: las tres listas de error vacías.
    - `network_posture`: 'NO_DEPENDENCIES_DEFINED' sin dependencias;
      'CIRCULAR_SELF_LINK_DETECTED' con self-links;
      'INVALID_DEPENDENCY_GRAMMAR' con tipos inválidos;
      'EXCESSIVE_LAG_DISTORTION' con lag excesivo; y
      'SOUND_SCHEDULE_NETWORK' en el caso válido.
    """
    VALID_RELATIONSHIPS = {"fs", "ss", "ff", "sf"}
    items = [item for item in (dependencies or []) if isinstance(item, dict)]
    safe_max_lag = float(max_lag_days) if max_lag_days is not None else 30.0

    self_dependency_ids: list[str] = []
    invalid_relationship_types: list[str] = []
    excessive_lag_links: list[str] = []
    sf_relationship_count = 0

    for item in items:
        predecessor_id = str(item.get("predecessor_id") or "").strip()
        successor_id = str(item.get("successor_id") or "").strip()
        relationship = str(
            item.get("type") or item.get("relationship") or "FS"
        ).strip().lower()
        lag_days = float(item.get("lag_days") or 0.0)

        if predecessor_id and predecessor_id == successor_id:
            self_dependency_ids.append(predecessor_id)
        if relationship not in VALID_RELATIONSHIPS:
            invalid_relationship_types.append(relationship)
        if abs(lag_days) > safe_max_lag:
            excessive_lag_links.append(f"{predecessor_id}->{successor_id}")
        if relationship == "sf":
            sf_relationship_count += 1

    total_dependencies = len(items)
    is_valid = bool(
        not self_dependency_ids
        and not invalid_relationship_types
        and not excessive_lag_links
    )

    if total_dependencies == 0:
        network_posture = "NO_DEPENDENCIES_DEFINED"
    elif self_dependency_ids:
        network_posture = "CIRCULAR_SELF_LINK_DETECTED"
    elif invalid_relationship_types:
        network_posture = "INVALID_DEPENDENCY_GRAMMAR"
    elif excessive_lag_links:
        network_posture = "EXCESSIVE_LAG_DISTORTION"
    else:
        network_posture = "SOUND_SCHEDULE_NETWORK"

    return {
        "is_valid": is_valid,
        "total_dependencies": total_dependencies,
        "self_dependency_ids": self_dependency_ids,
        "invalid_relationship_types": invalid_relationship_types,
        "excessive_lag_links": excessive_lag_links,
        "sf_relationship_count": sf_relationship_count,
        "network_posture": network_posture,
    }


def validate_risk_trigger_and_fallback_plan(
    risks: Optional[list[dict]],
    high_severity_threshold: int = 12,
) -> dict[str, Any]:
    """Valida disparadores de alerta temprana, planes de contingencia/respaldo y severidad residual en riesgos de alta exposición (PMBOK §11.5 y §11.7)."""
    items = [item for item in (risks or []) if isinstance(item, dict)]
    try:
        safe_threshold = max(1, int(high_severity_threshold if high_severity_threshold is not None else 12))
    except (TypeError, ValueError):
        safe_threshold = 12

    total_risks = len(items)
    high_exposure_count = 0
    missing_trigger_ids: list[str] = []
    missing_fallback_ids: list[str] = []
    unreduced_residual_ids: list[str] = []

    for idx, item in enumerate(items, start=1):
        raw_id = item.get("id") if item.get("id") is not None else item.get("code")
        risk_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"RISK-{idx}"
        )

        try:
            prob = int(item.get("probability") or 1)
        except (TypeError, ValueError):
            prob = 1
        try:
            imp = int(item.get("impact") or 1)
        except (TypeError, ValueError):
            imp = 1

        raw_sev = item.get("severity") if item.get("severity") is not None else item.get("score")
        if raw_sev is not None:
            try:
                severity = int(raw_sev)
            except (TypeError, ValueError):
                severity = prob * imp
        else:
            severity = prob * imp

        if severity < safe_threshold:
            continue

        high_exposure_count += 1

        trigger_str = str(
            item.get("trigger_condition")
            or item.get("early_warning_trigger")
            or ""
        ).strip()
        if len(trigger_str) < 6:
            missing_trigger_ids.append(risk_id)

        fallback_str = str(
            item.get("fallback_plan")
            or item.get("contingency_plan")
            or ""
        ).strip()
        if len(fallback_str) < 8:
            missing_fallback_ids.append(risk_id)

        try:
            residual = int(item.get("residual_severity") or 0)
        except (TypeError, ValueError):
            residual = 0
        if residual > 0 and residual >= severity:
            unreduced_residual_ids.append(risk_id)

    is_valid = bool(
        len(missing_trigger_ids) == 0
        and len(missing_fallback_ids) == 0
        and len(unreduced_residual_ids) == 0
    )

    if total_risks == 0:
        risk_governance_posture = "NO_RISKS_EVALUATED"
    elif len(missing_trigger_ids) > 0:
        risk_governance_posture = "MISSING_EARLY_WARNING_TRIGGERS"
    elif len(missing_fallback_ids) > 0:
        risk_governance_posture = "MISSING_FALLBACK_CONTINGENCY"
    elif len(unreduced_residual_ids) > 0:
        risk_governance_posture = "INEFFECTIVE_RESIDUAL_MITIGATION"
    else:
        risk_governance_posture = "GOVERNED_RISK_RESPONSE_MATRIX"

    return {
        "is_valid": is_valid,
        "total_risks": total_risks,
        "high_exposure_count": high_exposure_count,
        "missing_trigger_ids": missing_trigger_ids,
        "missing_fallback_ids": missing_fallback_ids,
        "unreduced_residual_ids": unreduced_residual_ids,
        "risk_governance_posture": risk_governance_posture,
    }


def validate_procurement_contract_fee_structure(
    contracts: Optional[list[dict]],
    max_award_fee_pct: float = 20.0,
) -> dict:
    """Valida el tipo de contrato y la estructura de fee de incentivo (PMBOK §12.1).

    Tipos válidos: FFP, FPIF, FP-EPA, CPFF, CPIF, CPAF, TM (case-insensitive).
    Cada contrato declara `id`/`contract_id`, `contract_type`, `target_cost`/
    `base_amount`, `fee_amount`/`fixed_fee`, `ceiling_price`/
    `not_to_exceed_limit` y buy/seller share ratios opcionales:
    - `invalid_type_ids`: tipos fuera de la gramática (plural, no repetidos).
    - `unbounded_tm_ids`: Time & Materials sin techo (`ceiling_price` <= 0).
    - `excessive_fee_ids`: fee/target * 100 > max_award_fee_pct (target > 0).
    - `imbalanced_share_ratio_ids`: FPIF/CPIF con ratios provistos cuya suma
      difiere de 1.0 en más de 0.01.
    - `is_valid`: las 4 listas vacías.
    - `contract_governance_posture`: 'NO_CONTRACTS_DEFINED' sin contratos;
      'INVALID_CONTRACT_TYPE' con tipos inválidos;
      'UNBOUNDED_TM_EXPOSURE' sin techo TM;
      'IMBALANCED_INCENTIVE_OR_EXCESSIVE_FEE' con fee excesivo o ratios
      desbalanceados; y 'SOUND_PROCUREMENT_STRUCTURE' en el caso sano.
    """
    VALID_TYPES = {"ffp", "fpif", "fp-epa", "cpff", "cpif", "cpaf", "tm"}
    PPIF_TYPES = {"fpif", "cpif"}
    items = [item for item in (contracts or []) if isinstance(item, dict)]
    safe_max_fee_pct = float(max_award_fee_pct if max_award_fee_pct is not None else 20.0)

    invalid_type_ids: list[str] = []
    unbounded_tm_ids: list[str] = []
    excessive_fee_ids: list[str] = []
    imbalanced_share_ratio_ids: list[str] = []

    for item in items:
        contract_id = str(item.get("id") or item.get("contract_id") or "").strip()
        contract_type = str(item.get("contract_type") or "").strip().lower()
        target_cost = float(item.get("target_cost") or item.get("base_amount") or 0.0)
        fee_amount = float(item.get("fee_amount") or item.get("fixed_fee") or 0.0)
        ceiling_price = float(
            item.get("ceiling_price") or item.get("not_to_exceed_limit") or 0.0
        )

        if contract_type not in VALID_TYPES:
            invalid_type_ids.append(contract_id)
        if contract_type == "tm" and ceiling_price <= 0:
            unbounded_tm_ids.append(contract_id)
        if target_cost > 0 and (fee_amount / target_cost) * 100.0 > safe_max_fee_pct:
            excessive_fee_ids.append(contract_id)
        if contract_type in PPIF_TYPES:
            has_buyer = item.get("buyer_share_ratio") is not None
            has_seller = item.get("seller_share_ratio") is not None
            if has_buyer or has_seller:
                buyer_ratio = float(item.get("buyer_share_ratio") or 0.0)
                seller_ratio = float(item.get("seller_share_ratio") or 0.0)
                if abs((buyer_ratio + seller_ratio) - 1.0) > 0.01:
                    imbalanced_share_ratio_ids.append(contract_id)

    total_contracts = len(items)
    is_valid = bool(
        not invalid_type_ids
        and not unbounded_tm_ids
        and not excessive_fee_ids
        and not imbalanced_share_ratio_ids
    )

    if total_contracts == 0:
        contract_governance_posture = "NO_CONTRACTS_DEFINED"
    elif invalid_type_ids:
        contract_governance_posture = "INVALID_CONTRACT_TYPE"
    elif unbounded_tm_ids:
        contract_governance_posture = "UNBOUNDED_TM_EXPOSURE"
    elif excessive_fee_ids or imbalanced_share_ratio_ids:
        contract_governance_posture = "IMBALANCED_INCENTIVE_OR_EXCESSIVE_FEE"
    else:
        contract_governance_posture = "SOUND_PROCUREMENT_STRUCTURE"

    return {
        "total_contracts": total_contracts,
        "invalid_type_ids": invalid_type_ids,
        "unbounded_tm_ids": unbounded_tm_ids,
        "excessive_fee_ids": excessive_fee_ids,
        "imbalanced_share_ratio_ids": imbalanced_share_ratio_ids,
        "is_valid": is_valid,
        "contract_governance_posture": contract_governance_posture,
    }


def validate_resource_histogram_overallocation(
    allocations: Optional[List[Dict[str, Any]]] = None,
    max_daily_hours: float = 8.0,
) -> Dict[str, Any]:
    """Valida el histograma de asignación de recursos por período (PMI 6.5.2.3 y 9.2).

    Detecta sobreasignaciones (horas acumuladas del mismo recurso en el mismo
    período por encima de su capacidad) y horas inválidas (<= 0.0), devolviendo
    la postura de gobernanza del histograma de recursos.
    """
    records = [item for item in (allocations or []) if isinstance(item, dict)]
    result: Dict[str, Any] = {
        "total_records": 0,
        "unique_resources_count": 0,
        "peak_utilization_pct": 0.0,
        "invalid_allocation_ids": [],
        "overallocated_resource_periods": [],
        "is_valid": True,
        "allocation_posture": "NO_ALLOCATIONS_DEFINED",
    }
    if not records:
        return result

    invalid_allocation_ids: List[str] = []
    bucket_hours: Dict[tuple, float] = {}
    bucket_capacity: Dict[tuple, float] = {}
    unique_resources: set = set()

    for idx, item in enumerate(records, start=1):
        alloc_id = str(item.get("id") or item.get("allocation_id") or "").strip() or f"ALLOC-{idx}"
        res_id = str(item.get("resource_id") or item.get("assignee_id") or item.get("user_id") or "").strip() or "UNASSIGNED"
        period = str(item.get("period") or item.get("date") or item.get("week") or "").strip() or "DEFAULT"
        try:
            hours = float(item["allocated_hours"] if item.get("allocated_hours") is not None else (item.get("hours") or 0.0))
        except (TypeError, ValueError):
            hours = 0.0
        try:
            cap_raw = float(item["capacity_hours"] if item.get("capacity_hours") is not None else (item.get("max_hours") or 0.0))
        except (TypeError, ValueError):
            cap_raw = 0.0
        bucket_cap = cap_raw if cap_raw > 0.0 else max(0.01, float(max_daily_hours))

        unique_resources.add(res_id)
        if hours <= 0.0:
            invalid_allocation_ids.append(alloc_id)
        else:
            bucket_hours[(res_id, period)] = bucket_hours.get((res_id, period), 0.0) + hours
            bucket_capacity[(res_id, period)] = max(bucket_capacity.get((res_id, period), 0.0), bucket_cap)

    peak_utilization_pct = 0.0
    overallocated_resource_periods: List[str] = []
    for key in sorted(bucket_hours.keys()):
        tot_h = bucket_hours[key]
        cap_h = bucket_capacity[key]
        util_pct = (tot_h / cap_h) * 100.0
        peak_utilization_pct = max(peak_utilization_pct, util_pct)
        if tot_h > cap_h + 1e-9:
            res_id, period = key
            overallocated_resource_periods.append(f"{res_id}@{period}")

    peak_utilization_pct = round(peak_utilization_pct, 2)
    is_valid = bool(len(invalid_allocation_ids) == 0 and len(overallocated_resource_periods) == 0)

    if len(invalid_allocation_ids) > 0:
        allocation_posture = "INVALID_ALLOCATION_HOURS"
    elif len(overallocated_resource_periods) > 0:
        allocation_posture = "RESOURCE_HISTOGRAM_OVERALLOCATION"
    else:
        allocation_posture = "BALANCED_RESOURCE_HISTOGRAM"

    return {
        "total_records": len(records),
        "unique_resources_count": len(unique_resources),
        "peak_utilization_pct": peak_utilization_pct,
        "invalid_allocation_ids": invalid_allocation_ids,
        "overallocated_resource_periods": overallocated_resource_periods,
        "is_valid": is_valid,
        "allocation_posture": allocation_posture,
    }


def validate_pert_three_point_estimates(
    estimates: Optional[List[Dict[str, Any]]] = None,
    max_coefficient_of_variation_pct: float = 35.0,
) -> Dict[str, Any]:
    """Valida estimaciones de tres puntos PERT Beta (O, M, P) de actividades o paquetes de trabajo según PMI PMBOK §6.4.2.4 y §7.2.2.5."""
    import math

    items = [item for item in (estimates or []) if isinstance(item, dict)]
    total_items = len(items)
    if total_items == 0:
        return {
            "total_items": 0,
            "total_expected_estimate": 0.0,
            "combined_standard_deviation": 0.0,
            "inverted_or_nonpositive_ids": [],
            "excessive_uncertainty_ids": [],
            "is_valid": True,
            "pert_posture": "NO_PERT_ESTIMATES_PROVIDED",
        }

    def _parse_val(item: Dict[str, Any], primary_key: str, alt_key: str) -> float:
        raw = item.get(primary_key) if item.get(primary_key) is not None else item.get(alt_key)
        if raw is None or isinstance(raw, bool):
            return -1.0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return -1.0

    try:
        max_cv_pct = float(max_coefficient_of_variation_pct)
    except (TypeError, ValueError):
        max_cv_pct = 35.0

    inverted_or_nonpositive_ids: List[str] = []
    excessive_uncertainty_ids: List[str] = []
    sum_expected = 0.0
    sum_variance = 0.0

    for idx, item in enumerate(items, start=1):
        item_id = (
            str(
                item.get("id")
                or item.get("activity_id")
                or item.get("task_id")
                or ""
            ).strip()
            or f"PERT-{idx}"
        )
        opt = _parse_val(item, "optimistic", "o")
        ml = _parse_val(item, "most_likely", "m")
        pes = _parse_val(item, "pessimistic", "p")

        if opt <= 0.0 or ml <= 0.0 or pes <= 0.0 or opt > ml or ml > pes:
            inverted_or_nonpositive_ids.append(item_id)
            continue

        expected = (opt + 4.0 * ml + pes) / 6.0
        sigma = (pes - opt) / 6.0
        variance = sigma * sigma
        sum_expected += expected
        sum_variance += variance

        cv_pct = (sigma / expected) * 100.0 if expected > 0.0 else 0.0
        if cv_pct > max_cv_pct + 1e-9:
            excessive_uncertainty_ids.append(item_id)

    total_expected_estimate = round(sum_expected, 2)
    combined_standard_deviation = round(math.sqrt(sum_variance), 2)
    is_valid = bool(
        len(inverted_or_nonpositive_ids) == 0 and len(excessive_uncertainty_ids) == 0
    )

    if len(inverted_or_nonpositive_ids) > 0:
        pert_posture = "INVERTED_OR_NONPOSITIVE_PERT_BOUNDS"
    elif len(excessive_uncertainty_ids) > 0:
        pert_posture = "EXCESSIVE_ESTIMATE_UNCERTAINTY_SPREAD"
    else:
        pert_posture = "SOUND_PERT_THREE_POINT_MODEL"

    return {
        "total_items": total_items,
        "total_expected_estimate": total_expected_estimate,
        "combined_standard_deviation": combined_standard_deviation,
        "inverted_or_nonpositive_ids": inverted_or_nonpositive_ids,
        "excessive_uncertainty_ids": excessive_uncertainty_ids,
        "is_valid": is_valid,
        "pert_posture": pert_posture,
    }


_INACTIVE_REQUIREMENT_STATUSES = frozenset(
    {
        "cancelled",
        "deferred",
        "rejected",
        "cancelado",
        "diferido",
        "rechazado",
    }
)


def validate_requirements_traceability_matrix(
    requirements: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Valida la cobertura bidireccional de la Matriz de Trazabilidad de Requisitos (RTM) según PMI PMBOK §5.2.3.2."""
    valid_reqs = [item for item in (requirements or []) if isinstance(item, dict)]
    total_requirements = len(valid_reqs)
    if total_requirements == 0:
        return {
            "total_requirements": 0,
            "active_requirements_count": 0,
            "fully_traced_count": 0,
            "traceability_coverage_pct": 0.0,
            "orphan_business_objective_ids": [],
            "unmapped_wbs_deliverable_ids": [],
            "unverified_test_case_ids": [],
            "is_valid": True,
            "rtm_posture": "NO_REQUIREMENTS_DEFINED",
        }

    active_requirements_count = 0
    fully_traced_count = 0
    orphan_business_objective_ids: List[str] = []
    unmapped_wbs_deliverable_ids: List[str] = []
    unverified_test_case_ids: List[str] = []

    for idx, item in enumerate(valid_reqs, start=1):
        req_id = (
            str(
                item.get("id")
                or item.get("req_id")
                or item.get("code")
                or ""
            ).strip()
            or f"REQ-{idx}"
        )
        status = str(item.get("status") or "").strip().lower()
        is_active = status not in _INACTIVE_REQUIREMENT_STATUSES
        if is_active:
            active_requirements_count += 1
            has_obj = bool(
                str(
                    item.get("business_objective")
                    or item.get("objective_id")
                    or item.get("strategic_goal")
                    or ""
                ).strip()
            )
            has_wbs = bool(
                str(
                    item.get("wbs_deliverable")
                    or item.get("wbs_code")
                    or item.get("deliverable_id")
                    or ""
                ).strip()
            )
            has_test = bool(
                str(
                    item.get("verification_test_id")
                    or item.get("test_case_id")
                    or item.get("acceptance_test")
                    or ""
                ).strip()
            )
            if not has_obj:
                orphan_business_objective_ids.append(req_id)
            if not has_wbs:
                unmapped_wbs_deliverable_ids.append(req_id)
            if not has_test:
                unverified_test_case_ids.append(req_id)
            if has_obj and has_wbs and has_test:
                fully_traced_count += 1

    traceability_coverage_pct = (
        round((fully_traced_count / active_requirements_count) * 100.0, 2)
        if active_requirements_count > 0
        else 100.0
    )
    is_valid = bool(
        len(orphan_business_objective_ids) == 0
        and len(unmapped_wbs_deliverable_ids) == 0
        and len(unverified_test_case_ids) == 0
    )

    if len(orphan_business_objective_ids) > 0:
        rtm_posture = "ORPHAN_REQUIREMENTS_WITHOUT_BUSINESS_NEED"
    elif len(unmapped_wbs_deliverable_ids) > 0:
        rtm_posture = "UNMAPPED_WBS_DELIVERABLE_GAPS"
    elif len(unverified_test_case_ids) > 0:
        rtm_posture = "MISSING_VERIFICATION_TEST_COVERAGE"
    else:
        rtm_posture = "BIDIRECTIONAL_RTM_COMPLIANT"

    return {
        "total_requirements": total_requirements,
        "active_requirements_count": active_requirements_count,
        "fully_traced_count": fully_traced_count,
        "traceability_coverage_pct": traceability_coverage_pct,
        "orphan_business_objective_ids": orphan_business_objective_ids,
        "unmapped_wbs_deliverable_ids": unmapped_wbs_deliverable_ids,
        "unverified_test_case_ids": unverified_test_case_ids,
        "is_valid": is_valid,
        "rtm_posture": rtm_posture,
    }



def validate_cpm_float_and_critical_path(
    activities: list[dict[str, Any]] | None = None,
    near_critical_threshold_days: float = 2.0,
) -> dict[str, Any]:
    """Valida Total Float, Free Float y la ruta crítica de un cronograma CPM (PMBOK §6.5.2.2).

    Cada actividad declara `id`/`activity_id`/`wbs_code` (fallback 'ACT-{idx}'),
    holgura total (`total_float_days`/`total_float`/`tf`), holgura libre
    (`free_float_days`/`free_float`/`ff`) y el flag declarado
    (`is_critical`/`critical_path`):
    - `negative_float_activity_ids`: Total Float < 0 (alerta de retraso).
    - `float_inversion_activity_ids`: Free Float > Total Float, o Free Float
      negativo con Total Float >= 0 (inversión matemática CPM).
    - `misclassified_critical_activity_ids`: TF <= 0 sin flag crítico, o
      TF > umbral cuasi-crítico con flag crítico declarado.
    - `critical_activities_count` (TF <= 0) y `near_critical_count`
      (0 < TF <= umbral).
    - `is_cpm_schedule_valid`: sin hallazgos en las 3 listas.
    - `cpm_schedule_posture`: 'NO_ACTIVITIES_EVALUATED' sin actividades;
      'CPM_FLOAT_INVERSION_ERROR'; 'NEGATIVE_TOTAL_FLOAT_ALERT';
      'CRITICAL_PATH_CLASSIFICATION_DRIFT'; 'SOUND_CPM_NETWORK_SCHEDULE'.
    """
    records = [a for a in (activities or []) if isinstance(a, dict)]
    if not records:
        return {
            "total_activities": 0,
            "critical_activities_count": 0,
            "near_critical_count": 0,
            "negative_float_activity_ids": [],
            "float_inversion_activity_ids": [],
            "misclassified_critical_activity_ids": [],
            "is_cpm_schedule_valid": True,
            "cpm_schedule_posture": "NO_ACTIVITIES_EVALUATED",
        }

    total_activities = len(records)
    critical_activities_count = 0
    near_critical_count = 0
    negative_float_activity_ids: list[str] = []
    float_inversion_activity_ids: list[str] = []
    misclassified_critical_activity_ids: list[str] = []

    for idx, item in enumerate(records, start=1):
        act_id = str(
            item.get("id") or item.get("activity_id") or item.get("wbs_code") or f"ACT-{idx}"
        ).strip()
        try:
            total_float_days = float(
                item.get("total_float_days")
                if item.get("total_float_days") is not None
                else (item.get("total_float") if item.get("total_float") is not None else (item.get("tf") or 0.0))
            )
        except (TypeError, ValueError):
            total_float_days = 0.0
        try:
            free_float_days = float(
                item.get("free_float_days")
                if item.get("free_float_days") is not None
                else (item.get("free_float") if item.get("free_float") is not None else (item.get("ff") or 0.0))
            )
        except (TypeError, ValueError):
            free_float_days = 0.0
        is_critical_declared = bool(item.get("is_critical") or item.get("critical_path"))
        threshold = float(near_critical_threshold_days)

        if total_float_days < -1e-9:
            negative_float_activity_ids.append(act_id)
        if (
            free_float_days > total_float_days + 1e-9
            or (free_float_days < -1e-9 and total_float_days >= -1e-9)
        ):
            float_inversion_activity_ids.append(act_id)
        if (total_float_days <= 1e-9 and not is_critical_declared) or (
            total_float_days > threshold + 1e-9 and is_critical_declared
        ):
            misclassified_critical_activity_ids.append(act_id)
        if total_float_days <= 1e-9:
            critical_activities_count += 1
        elif total_float_days <= threshold + 1e-9:
            near_critical_count += 1

    is_cpm_schedule_valid = bool(
        len(negative_float_activity_ids) == 0
        and len(float_inversion_activity_ids) == 0
        and len(misclassified_critical_activity_ids) == 0
    )
    if total_activities == 0:
        cpm_schedule_posture = "NO_ACTIVITIES_EVALUATED"
    elif len(float_inversion_activity_ids) > 0:
        cpm_schedule_posture = "CPM_FLOAT_INVERSION_ERROR"
    elif len(negative_float_activity_ids) > 0:
        cpm_schedule_posture = "NEGATIVE_TOTAL_FLOAT_ALERT"
    elif len(misclassified_critical_activity_ids) > 0:
        cpm_schedule_posture = "CRITICAL_PATH_CLASSIFICATION_DRIFT"
    else:
        cpm_schedule_posture = "SOUND_CPM_NETWORK_SCHEDULE"

    return {
        "total_activities": total_activities,
        "critical_activities_count": critical_activities_count,
        "near_critical_count": near_critical_count,
        "negative_float_activity_ids": negative_float_activity_ids,
        "float_inversion_activity_ids": float_inversion_activity_ids,
        "misclassified_critical_activity_ids": misclassified_critical_activity_ids,
        "is_cpm_schedule_valid": is_cpm_schedule_valid,
        "cpm_schedule_posture": cpm_schedule_posture,
    }


__all__ = [
    "validate_cpm_float_and_critical_path",
]

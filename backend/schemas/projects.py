from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Literal, Mapping, Optional, Sequence
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


_OPPORTUNITY_RISK_KINDS = frozenset({"opportunity", "oportunidad", "positive"})


def validate_emv_decision_tree_exposure(
    risk_scenarios: list[dict[str, Any]] | None = None,
    contingency_reserve_available: float = 0.0,
) -> dict[str, Any]:
    """Valida el Valor Monetario Esperado (EMV) y cobertura de reserva de contingencia según PMI PMBOK §11.4.2.2."""
    items = [item for item in (risk_scenarios or []) if isinstance(item, dict)]
    total_scenarios = len(items)
    if total_scenarios == 0:
        return {
            "total_scenarios": 0,
            "net_threat_emv": 0.0,
            "reserve_shortfall": 0.0,
            "invalid_probability_risk_ids": [],
            "emv_mismatch_risk_ids": [],
            "is_emv_valid_and_buffered": True,
            "emv_posture": "NO_RISK_SCENARIOS",
        }

    invalid_probability_risk_ids: list[str] = []
    emv_mismatch_risk_ids: list[str] = []
    net_threat_emv_raw = 0.0

    for idx, item in enumerate(items, start=1):
        risk_id = (
            str(
                item.get("id")
                or item.get("risk_id")
                or item.get("code")
                or f"RSK-{idx}"
            ).strip()
            or f"RSK-{idx}"
        )
        raw_prob = (
            item.get("probability")
            if item.get("probability") is not None
            else (
                item.get("prob")
                if item.get("prob") is not None
                else item.get("p")
            )
        )
        prob_val: Optional[float] = None
        if raw_prob is not None and not isinstance(raw_prob, bool):
            try:
                prob_val = float(raw_prob)
            except (TypeError, ValueError):
                prob_val = None

        if prob_val is None or prob_val < 0.0 or prob_val > 1.0:
            invalid_probability_risk_ids.append(risk_id)
            continue

        raw_impact = (
            item.get("impact_cost")
            if item.get("impact_cost") is not None
            else (
                item.get("impact_amount")
                if item.get("impact_amount") is not None
                else (item.get("impact") or 0.0)
            )
        )
        try:
            impact_val = float(raw_impact)
        except (TypeError, ValueError):
            impact_val = 0.0

        kind = (
            str(
                item.get("type")
                or item.get("risk_type")
                or item.get("nature")
                or "threat"
            )
            .strip()
            .lower()
        )
        if kind in _OPPORTUNITY_RISK_KINDS:
            threat_emv = -abs(prob_val * abs(impact_val))
        else:
            threat_emv = abs(prob_val * abs(impact_val))

        expected_emv_abs = round(prob_val * abs(impact_val), 2)
        raw_reported = (
            item.get("reported_emv")
            if item.get("reported_emv") is not None
            else item.get("emv")
        )
        if raw_reported is not None and not isinstance(raw_reported, bool):
            try:
                rep_val = float(raw_reported)
                if abs(abs(rep_val) - expected_emv_abs) > 0.05:
                    emv_mismatch_risk_ids.append(risk_id)
            except (TypeError, ValueError):
                emv_mismatch_risk_ids.append(risk_id)

        net_threat_emv_raw += threat_emv

    try:
        avail_res = max(0.0, float(contingency_reserve_available or 0.0))
    except (TypeError, ValueError):
        avail_res = 0.0

    net_threat_emv = round(max(0.0, net_threat_emv_raw), 2)
    reserve_shortfall = round(max(0.0, net_threat_emv - avail_res), 2)
    is_emv_valid_and_buffered = bool(
        len(invalid_probability_risk_ids) == 0
        and len(emv_mismatch_risk_ids) == 0
        and reserve_shortfall <= 1e-9
    )

    if len(invalid_probability_risk_ids) > 0:
        emv_posture = "INVALID_PROBABILITY_RANGE"
    elif len(emv_mismatch_risk_ids) > 0:
        emv_posture = "EMV_CALCULATION_MISMATCH"
    elif reserve_shortfall > 1e-9:
        emv_posture = "CONTINGENCY_RESERVE_EMV_SHORTFALL"
    else:
        emv_posture = "BUFFERED_EMV_EXPOSURE"

    return {
        "total_scenarios": total_scenarios,
        "net_threat_emv": net_threat_emv,
        "reserve_shortfall": reserve_shortfall,
        "invalid_probability_risk_ids": invalid_probability_risk_ids,
        "emv_mismatch_risk_ids": emv_mismatch_risk_ids,
        "is_emv_valid_and_buffered": is_emv_valid_and_buffered,
        "emv_posture": emv_posture,
    }


_PDM_VALID_DEPENDENCY_TYPES = {"FS", "SS", "FF", "SF"}


def validate_pdm_dependency_leads_and_lags(
    dependencies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Valida tipos de dependencia lógica (FS/SS/FF/SF) y razonabilidad de adelantos/retrasos (PDM, PMI PMBOK §6.3.2.1)."""
    items = [item for item in (dependencies or []) if isinstance(item, dict)]
    total_dependencies = len(items)
    if total_dependencies == 0:
        return {
            "total_dependencies": 0,
            "invalid_relationship_ids": [],
            "excessive_lead_dependency_ids": [],
            "unjustified_sf_dependency_ids": [],
            "is_pdm_network_valid": True,
            "pdm_posture": "NO_DEPENDENCIES_EVALUATED",
        }

    invalid_relationship_ids: list[str] = []
    excessive_lead_dependency_ids: list[str] = []
    unjustified_sf_dependency_ids: list[str] = []

    for idx, item in enumerate(items, start=1):
        dep_id = (
            str(
                item.get("id")
                or item.get("dependency_id")
                or f"DEP-{idx}"
            ).strip()
            or f"DEP-{idx}"
        )
        pred_id = str(
            item.get("predecessor_id") or item.get("from_id") or ""
        ).strip()
        succ_id = str(
            item.get("successor_id") or item.get("to_id") or ""
        ).strip()
        dep_type = (
            str(
                item.get("type")
                or item.get("dependency_type")
                or item.get("link_type")
                or "FS"
            )
            .strip()
            .upper()
        )
        try:
            lag_days = float(item.get("lag_days") or item.get("lag") or 0.0)
        except (TypeError, ValueError):
            lag_days = 0.0
        try:
            pred_duration = float(
                item.get("predecessor_duration_days")
                or item.get("predecessor_duration")
                or 0.0
            )
        except (TypeError, ValueError):
            pred_duration = 0.0
        justification = str(
            item.get("justification") or item.get("rationale") or ""
        ).strip()

        if (pred_id and succ_id and pred_id == succ_id) or (
            dep_type not in _PDM_VALID_DEPENDENCY_TYPES
        ):
            invalid_relationship_ids.append(dep_id)

        if (
            lag_days < -1e-9
            and pred_duration > 0.0
            and abs(lag_days) >= pred_duration - 1e-9
        ):
            excessive_lead_dependency_ids.append(dep_id)

        if dep_type == "SF" and len(justification) < 5:
            unjustified_sf_dependency_ids.append(dep_id)

    is_pdm_network_valid = bool(
        len(invalid_relationship_ids) == 0
        and len(excessive_lead_dependency_ids) == 0
        and len(unjustified_sf_dependency_ids) == 0
    )

    if len(invalid_relationship_ids) > 0:
        pdm_posture = "INVALID_PDM_RELATIONSHIP"
    elif len(excessive_lead_dependency_ids) > 0:
        pdm_posture = "EXCESSIVE_NEGATIVE_LAG_LEAD"
    elif len(unjustified_sf_dependency_ids) > 0:
        pdm_posture = "UNJUSTIFIED_SF_DEPENDENCY"
    else:
        pdm_posture = "SOUND_PDM_LOGICAL_NETWORK"

    return {
        "total_dependencies": total_dependencies,
        "invalid_relationship_ids": invalid_relationship_ids,
        "excessive_lead_dependency_ids": excessive_lead_dependency_ids,
        "unjustified_sf_dependency_ids": unjustified_sf_dependency_ids,
        "is_pdm_network_valid": is_pdm_network_valid,
        "pdm_posture": pdm_posture,
    }


def validate_cpif_cost_sharing_and_fee_bounds(
    target_cost: float,
    target_fee: float,
    minimum_fee: float,
    maximum_fee: float,
    buyer_share_ratio_pct: float,
    seller_share_ratio_pct: float,
    actual_cost: float,
) -> dict[str, Any]:
    """PMBOK §12.1 — Cost-Plus-Incentive-Fee (CPIF): bandas min/max y reparto de costos.

    Fórmula canónica PMI: el honorario crudo ajusta ``target_fee`` por la
    variación de costo según el porcentaje de reparto del vendedor, acotado a
    la banda [minimum_fee, maximum_fee]; el comprador reembolsa costo real +
    honorario final. Rangos de kantor: costo mínimo que logra el honorario
    máximo y costo máximo que deja el honorario en el mínimo.
    """
    floats = {
        "target_cost": target_cost,
        "target_fee": target_fee,
        "minimum_fee": minimum_fee,
        "maximum_fee": maximum_fee,
        "buyer_share_ratio_pct": buyer_share_ratio_pct,
        "seller_share_ratio_pct": seller_share_ratio_pct,
        "actual_cost": actual_cost,
    }
    for name, value in floats.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            raise ValueError(f"CPIF: {name} debe ser numérico real, no bool/NaN")
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"CPIF: {name} debe ser finito")

    if target_cost <= 0:
        raise ValueError("CPIF: target_cost debe ser > 0")
    if actual_cost <= 0:
        raise ValueError("CPIF: actual_cost debe ser > 0")

    buyer = float(buyer_share_ratio_pct)
    seller = float(seller_share_ratio_pct)
    if buyer <= 0 or seller <= 0:
        raise ValueError("CPIF: los porcentajes de reparto deben ser > 0")
    if abs((buyer + seller) - 100.0) > 0.01:
        raise ValueError("CPIF: buyer_share_ratio_pct + seller_share_ratio_pct debe sumar 100.0")

    if not (0 <= float(minimum_fee) <= float(target_fee) <= float(maximum_fee)):
        raise ValueError(
            "CPIF: se requiere 0 <= minimum_fee <= target_fee <= maximum_fee"
        )

    tc = float(target_cost)
    tf = float(target_fee)
    ac = float(actual_cost)
    min_fee = float(minimum_fee)
    max_fee = float(maximum_fee)

    cost_variance = round(tc - ac, 2)
    raw_calculated_fee = round(tf + cost_variance * (seller / 100.0), 2)
    final_fee = round(min(max_fee, max(min_fee, raw_calculated_fee)), 2)
    total_reimbursed_price = round(ac + final_fee, 2)
    is_capped_at_max_fee = bool(raw_calculated_fee > max_fee)
    is_floored_at_min_fee = bool(raw_calculated_fee < min_fee)
    optimistic_range_cost = round(tc - ((max_fee - tf) / (seller / 100.0)), 2)
    pessimistic_range_cost = round(tc + ((tf - min_fee) / (seller / 100.0)), 2)

    is_within_incentive_range = bool(not is_capped_at_max_fee and not is_floored_at_min_fee)

    return {
        "cost_variance": cost_variance,
        "raw_calculated_fee": raw_calculated_fee,
        "final_fee": final_fee,
        "total_reimbursed_price": total_reimbursed_price,
        "is_capped_at_max_fee": is_capped_at_max_fee,
        "is_floored_at_min_fee": is_floored_at_min_fee,
        "optimistic_range_cost": optimistic_range_cost,
        "pessimistic_range_cost": pessimistic_range_cost,
        "is_within_incentive_range": is_within_incentive_range,
    }


__all__ = [
    "validate_schedule_compression_fast_tracking_and_crashing",
    "validate_cpm_float_and_critical_path",
    "validate_emv_decision_tree_exposure",
    "validate_pdm_dependency_leads_and_lags",
    "validate_schedule_compression_options",
    "validate_wbs_work_package_sizing_heuristic",
    "validate_monte_carlo_schedule_confidence_buffer",
    "validate_resource_leveling_overallocation",
    "validate_schedule_buffer_fever_chart_status",
    "validate_rolling_wave_planning_horizon",
    "validate_resource_smoothing_float_boundaries",
    "validate_sprint_velocity_commitment_stability",
    "validate_fpif_point_of_total_assumption",
    "validate_cpif_cost_sharing_and_fee_bounds",
    "validate_tm_contract_not_to_exceed_and_rate_card",
    "validate_fpif_share_ratio_and_point_of_total_assumption",
    "validate_schedule_network_lead_lag_and_float_feasibility",
    "validate_three_point_pert_skew_and_confidence_band",
    "validate_deliverable_acceptance_criteria_measurability",
    "validate_resource_calendar_overtime_and_blackout_bounds",
    "validate_ccpm_feeding_and_project_buffer_sizing",
    "validate_wbs_hundred_percent_rule_decomposition",
    "validate_emv_decision_tree_and_contingency_reserve",
    "validate_parametric_estimation_model_fit",
    "validate_funding_limit_reconciliation_and_cash_flow_cliff",
    "validate_business_case_npv_irr_and_payback_hurdle",
    "validate_monte_carlo_confidence_band_and_reserve_adequacy",
    "validate_resource_leveling_and_smoothing_constraints",
    "validate_wbs_100_percent_rollup_and_8_80_granularity",
    "validate_make_or_buy_breakeven_and_tco",
    "validate_risk_response_strategy_and_contingency_triggers",
    "validate_schedule_network_pdm_lead_lag_hygiene",
    "validate_requirements_traceability_bidirectional_coverage",
    "validate_three_point_pert_and_triangular_estimates",
    "validate_ccpm_critical_chain_buffer_fever_chart",
    "validate_raci_responsibility_assignment_matrix_hygiene",
    "validate_monte_carlo_confidence_percentiles_and_contingency",
    "validate_make_or_buy_tco_and_strategic_lock_in",
    "validate_resource_calendar_timezone_overlap_and_allocation",
    "validate_wbs_work_package_8_80_granularity_and_dictionary",
    "validate_risk_probability_impact_matrix_and_appetite_thresholds",
    "validate_ccpm_fever_chart_and_buffer_consumption",
    "validate_sprint_velocity_volatility_and_commitment_reliability",
    "validate_portfolio_efficient_frontier_and_budget_knapsack",
    "validate_pdm_network_dangling_activities_and_negative_float",
    "validate_risk_emv_decision_tree_and_contingency_adequacy",
    "validate_pert_three_point_estimation_and_delphi_convergence",
    "validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity",
    "validate_resource_leveling_overallocation_and_context_switching",
    "validate_wbs_rolling_wave_horizon_and_8_80_rule",
    "validate_rtm_bidirectional_traceability_and_gold_plating",
]


def validate_schedule_compression_options(
    activities: list[dict[str, Any]] | None = None,
    max_rework_risk_pct: float = 25.0,
) -> dict[str, Any]:
    """Valida opciones de compresión de cronograma crashing/fast-tracking (PMBOK §6.5.2.6).

    Cada opción declara `id`/`activity_id` (fallback 'ACT-{idx}'), flag de
    ruta crítica (`is_critical`/`on_critical_path`), duración normal y
    comprimida, costo normal y comprimido, técnica
    (`technique`/`compression_type`, default 'crashing') y riesgo de rework
    (`rework_risk_pct`/`overlap_risk_pct`):
    - `invalid_crash_slope_ids`: geometría inválida (duraciones <= 0,
      crash > normal, o en crashing costo comprimido < costo normal).
    - `non_critical_compression_ids`: compresión fuera de la ruta crítica.
    - `high_risk_fast_track_ids`: fast-tracking con rework > límite o
      compresión > 50% de la duración normal.
    - `total_days_saved`: días ganados solo en actividades críticas sin hallazgos (2 dec).
    - `is_compression_plan_sound`: las 3 listas vacías.
    - `compression_posture`: 'NO_COMPRESSION_OPTIONS' sin opciones;
      'INVALID_CRASH_COST_DURATION_SLOPE'; 'NON_CRITICAL_PATH_COMPRESSION_WASTE';
      'EXCESSIVE_FAST_TRACK_REWORK_RISK'; 'OPTIMAL_CRITICAL_PATH_COMPRESSION'.
    """
    records = [a for a in (activities or []) if isinstance(a, dict)]
    if not records:
        return {
            "total_options": 0,
            "total_days_saved": 0.0,
            "non_critical_compression_ids": [],
            "invalid_crash_slope_ids": [],
            "high_risk_fast_track_ids": [],
            "is_compression_plan_sound": True,
            "compression_posture": "NO_COMPRESSION_OPTIONS",
        }

    CRASHING_TECHNIQUES = {"crashing", "intensificacion"}
    FAST_TRACK_TECHNIQUES = {"fast_tracking", "fast-tracking", "ejecucion_rapida"}

    total_options = len(records)
    total_days_saved_raw = 0.0
    non_critical_compression_ids: list[str] = []
    invalid_crash_slope_ids: list[str] = []
    high_risk_fast_track_ids: list[str] = []

    for idx, item in enumerate(records, start=1):
        act_id = str(item.get("id") or item.get("activity_id") or f"ACT-{idx}").strip()
        is_critical = bool(item.get("is_critical") or item.get("on_critical_path"))
        try:
            normal_duration = float(item.get("normal_duration_days") or item.get("normal_duration") or 0.0)
        except (TypeError, ValueError):
            normal_duration = 0.0
        crash_raw = item.get("crash_duration_days")
        if crash_raw is None:
            crash_raw = item.get("crashed_duration")
        crash_duration = float(crash_raw) if crash_raw is not None else normal_duration
        try:
            normal_cost = float(item.get("normal_cost") or 0.0)
        except (TypeError, ValueError):
            normal_cost = 0.0
        cost_raw = item.get("crash_cost")
        if cost_raw is None:
            cost_raw = item.get("crashed_cost")
        crash_cost = float(cost_raw) if cost_raw is not None else normal_cost
        technique = str(item.get("technique") or item.get("compression_type") or "crashing").strip().lower()
        try:
            rework_risk_pct = float(item.get("rework_risk_pct") or item.get("overlap_risk_pct") or 0.0)
        except (TypeError, ValueError):
            rework_risk_pct = 0.0

        is_invalid_slope = bool(
            normal_duration <= 0.0
            or crash_duration <= 0.0
            or crash_duration > normal_duration + 1e-9
            or (technique in CRASHING_TECHNIQUES and crash_cost < normal_cost - 1e-9)
        )
        is_non_critical_compression = bool(
            crash_duration < normal_duration - 1e-9 and not is_critical
        )
        is_high_risk_fast_track = bool(
            technique in FAST_TRACK_TECHNIQUES
            and (
                rework_risk_pct > float(max_rework_risk_pct) + 1e-9
                or (
                    normal_duration > 0.0
                    and ((normal_duration - crash_duration) / normal_duration) * 100.0
                    > 50.0 + 1e-9
                )
            )
        )

        if is_invalid_slope:
            invalid_crash_slope_ids.append(act_id)
        if is_non_critical_compression:
            non_critical_compression_ids.append(act_id)
        if is_high_risk_fast_track:
            high_risk_fast_track_ids.append(act_id)
        if is_critical and not (is_invalid_slope or is_non_critical_compression or is_high_risk_fast_track):
            total_days_saved_raw += max(0.0, normal_duration - crash_duration)

    is_compression_plan_sound = bool(
        len(non_critical_compression_ids) == 0
        and len(invalid_crash_slope_ids) == 0
        and len(high_risk_fast_track_ids) == 0
    )

    if total_options == 0:
        compression_posture = "NO_COMPRESSION_OPTIONS"
    elif len(invalid_crash_slope_ids) > 0:
        compression_posture = "INVALID_CRASH_COST_DURATION_SLOPE"
    elif len(non_critical_compression_ids) > 0:
        compression_posture = "NON_CRITICAL_PATH_COMPRESSION_WASTE"
    elif len(high_risk_fast_track_ids) > 0:
        compression_posture = "EXCESSIVE_FAST_TRACK_REWORK_RISK"
    else:
        compression_posture = "OPTIMAL_CRITICAL_PATH_COMPRESSION"

    return {
        "total_options": total_options,
        "total_days_saved": round(total_days_saved_raw, 2),
        "non_critical_compression_ids": non_critical_compression_ids,
        "invalid_crash_slope_ids": invalid_crash_slope_ids,
        "high_risk_fast_track_ids": high_risk_fast_track_ids,
        "is_compression_plan_sound": is_compression_plan_sound,
        "compression_posture": compression_posture,
    }


def validate_wbs_work_package_sizing_heuristic(
    work_packages: list[dict[str, Any]] | None = None,
    min_effort_hours: float = 8.0,
    max_effort_hours: float = 80.0,
) -> dict[str, Any]:
    """Valida la heurística 8/80 horas y propietario único en paquetes de trabajo hoja de la EDT/WBS (PMBOK §5.4 / §6.2).

    Reglas:
    - Ignora paquetes sin `id`/`wp_id` o con `is_leaf` en `False` (nodos resumen).
    - `effort = float(item.get("estimated_hours") if item.get("estimated_hours") is not None else 0.0)`
    - Si `effort < float(min_effort_hours)` -> `undersized_package_ids`.
    - Si `effort > float(max_effort_hours)` -> `oversized_package_ids`.
    - Si `len(owners_list) != 1` -> `invalid_ownership_package_ids`.
    - `is_wbs_sizing_compliant = bool(total_leaf_packages > 0 and len(undersized_package_ids) == 0 and len(oversized_package_ids) == 0 and len(invalid_ownership_package_ids) == 0)`
    """
    total_leaf_packages = 0
    undersized_package_ids: list[str] = []
    oversized_package_ids: list[str] = []
    invalid_ownership_package_ids: list[str] = []

    for item in work_packages or []:
        if not isinstance(item, dict):
            continue
        wp_id = str(item.get("id") or item.get("wp_id") or "").strip()
        if not wp_id:
            continue
        is_leaf = bool(item.get("is_leaf", True))
        if not is_leaf:
            continue

        total_leaf_packages += 1
        raw_effort = item.get("estimated_hours")
        try:
            effort = float(raw_effort if raw_effort is not None else 0.0)
        except (TypeError, ValueError):
            effort = 0.0

        owner_id = str(item.get("owner_id") or "").strip()
        raw_owners = item.get("owners")
        if isinstance(raw_owners, list):
            owners_list = [str(o).strip() for o in raw_owners if str(o).strip()]
        else:
            owners_list = [owner_id] if owner_id else []

        if effort < float(min_effort_hours):
            undersized_package_ids.append(wp_id)
        if effort > float(max_effort_hours):
            oversized_package_ids.append(wp_id)
        if len(owners_list) != 1:
            invalid_ownership_package_ids.append(wp_id)

    is_wbs_sizing_compliant = bool(
        total_leaf_packages > 0
        and len(undersized_package_ids) == 0
        and len(oversized_package_ids) == 0
        and len(invalid_ownership_package_ids) == 0
    )

    if total_leaf_packages == 0:
        sizing_posture = "NO_LEAF_WORK_PACKAGES"
    elif len(oversized_package_ids) > 0:
        sizing_posture = "OVERSIZED_WORK_PACKAGES_NEED_DECOMPOSITION"
    elif len(invalid_ownership_package_ids) > 0:
        sizing_posture = "INVALID_WORK_PACKAGE_OWNERSHIP"
    elif len(undersized_package_ids) > 0:
        sizing_posture = "UNDERSIZED_MICRO_WORK_PACKAGES"
    else:
        sizing_posture = "BALANCED_8_80_WBS_DECOMPOSITION"

    return {
        "total_leaf_packages": total_leaf_packages,
        "undersized_package_ids": undersized_package_ids,
        "oversized_package_ids": oversized_package_ids,
        "invalid_ownership_package_ids": invalid_ownership_package_ids,
        "is_wbs_sizing_compliant": is_wbs_sizing_compliant,
        "sizing_posture": sizing_posture,
    }


def validate_monte_carlo_schedule_confidence_buffer(
    deterministic_duration_days: float = 0.0,
    p50_days: float = 0.0,
    p80_days: float = 0.0,
    p95_days: float = 0.0,
    allocated_buffer_days: float = 0.0,
) -> dict[str, Any]:
    """Valida percentiles de confianza Monte Carlo (P50/P80/P95) y suficiencia de buffer de cronograma (PMBOK §6.5.2.4 / §11.4.2.5)."""
    try:
        det = float(deterministic_duration_days or 0.0)
    except (TypeError, ValueError):
        det = 0.0
    try:
        p50 = float(p50_days or 0.0)
    except (TypeError, ValueError):
        p50 = 0.0
    try:
        p80 = float(p80_days or 0.0)
    except (TypeError, ValueError):
        p80 = 0.0
    try:
        p95 = float(p95_days or 0.0)
    except (TypeError, ValueError):
        p95 = 0.0
    try:
        buf = max(0.0, float(allocated_buffer_days or 0.0))
    except (TypeError, ValueError):
        buf = 0.0

    if det <= 0.0 or p50 <= 0.0 or p80 <= 0.0 or p95 <= 0.0:
        return {
            "committed_duration_days": 0.0,
            "required_p80_buffer_days": 0.0,
            "buffer_shortfall_days": 0.0,
            "tail_spread_p95_p50_days": 0.0,
            "is_monotonic_distribution": False,
            "meets_p80_confidence": False,
            "monte_carlo_posture": "INVALID_MONTE_CARLO_INPUTS",
        }

    is_monotonic = bool((p50 <= p80 + 1e-6) and (p80 <= p95 + 1e-6))
    committed = round(det + buf, 2)
    req_p80_buf = round(max(0.0, p80 - det), 2)
    shortfall = round(max(0.0, p80 - committed), 2)
    tail_spread = round(max(0.0, p95 - p50), 2)
    meets_p80 = bool(is_monotonic and (committed + 1e-6 >= p80))

    if not is_monotonic:
        monte_carlo_posture = "NON_MONOTONIC_PERCENTILE_CURVE"
    elif committed + 1e-6 < p50:
        monte_carlo_posture = "BELOW_P50_HIGH_OVERRUN_PROBABILITY"
    elif committed + 1e-6 < p80:
        monte_carlo_posture = "INSUFFICIENT_P80_CONFIDENCE_BUFFER"
    elif committed + 1e-6 >= p95:
        monte_carlo_posture = "HIGH_P95_CONFIDENCE_COVERAGE"
    else:
        monte_carlo_posture = "ADEQUATE_P80_SCHEDULE_CONFIDENCE"

    return {
        "committed_duration_days": committed,
        "required_p80_buffer_days": req_p80_buf,
        "buffer_shortfall_days": shortfall,
        "tail_spread_p95_p50_days": tail_spread,
        "is_monotonic_distribution": is_monotonic,
        "meets_p80_confidence": meets_p80,
        "monte_carlo_posture": monte_carlo_posture,
    }


def validate_resource_leveling_overallocation(
    resource_allocations: list[dict[str, Any]] | None = None,
    max_peak_to_average_ratio: float = 1.5,
) -> dict[str, Any]:
    """Valida nivelación de recursos (Resource Leveling & Smoothing), sobre-asignación y ratio pico-promedio según PMI PMBOK §6.5.2.3 y §9.6."""
    total_resources = 0
    overallocated_resource_ids: list[str] = []
    unsmoothed_peak_resource_ids: list[str] = []

    for item in resource_allocations or []:
        if not isinstance(item, dict):
            continue
        resource_id = str(item.get("resource_id") or item.get("id") or "").strip()
        if not resource_id:
            continue

        raw_cap = item.get("capacity_hours_per_period")
        if raw_cap is None:
            raw_cap = item.get("capacity_hours")
        try:
            capacity_hours = max(
                0.0, float(raw_cap if raw_cap is not None else 40.0)
            )
        except (TypeError, ValueError):
            capacity_hours = 40.0

        raw_loads = item.get("period_loads")
        period_loads: list[float] = []
        if isinstance(raw_loads, list):
            for h in raw_loads:
                try:
                    period_loads.append(max(0.0, float(h)))
                except (TypeError, ValueError):
                    continue

        if len(period_loads) == 0 or capacity_hours <= 0.0:
            continue

        total_resources += 1
        peak_load = max(period_loads)
        avg_load = sum(period_loads) / len(period_loads)
        pta_ratio = (peak_load / avg_load) if avg_load > 1e-6 else 1.0

        if peak_load > capacity_hours + 1e-6:
            overallocated_resource_ids.append(resource_id)
        if pta_ratio > float(max_peak_to_average_ratio) + 1e-6:
            unsmoothed_peak_resource_ids.append(resource_id)

    is_resource_schedule_leveled = bool(
        total_resources > 0
        and len(overallocated_resource_ids) == 0
        and len(unsmoothed_peak_resource_ids) == 0
    )

    if total_resources == 0:
        leveling_posture = "NO_RESOURCE_ALLOCATIONS"
    elif len(overallocated_resource_ids) > 0:
        leveling_posture = "RESOURCE_CAPACITY_OVERALLOCATED"
    elif len(unsmoothed_peak_resource_ids) > 0:
        leveling_posture = "UNSMOOTHED_RESOURCE_LOAD_PEAKS"
    else:
        leveling_posture = "LEVELED_AND_SMOOTHED_RESOURCES"

    return {
        "total_resources": total_resources,
        "overallocated_resource_ids": overallocated_resource_ids,
        "unsmoothed_peak_resource_ids": unsmoothed_peak_resource_ids,
        "is_resource_schedule_leveled": is_resource_schedule_leveled,
        "leveling_posture": leveling_posture,
    }


def validate_schedule_buffer_fever_chart_status(
    buffer_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evalúa consumo de buffers de cronograma frente al avance de la cadena crítica (Critical Chain Fever Chart, PMI PMBOK §6.4 / §6.5.2.6)."""
    evaluated_chain_count = 0
    green_zone_chain_ids: list[str] = []
    yellow_zone_chain_ids: list[str] = []
    red_zone_chain_ids: list[str] = []
    unmitigated_red_zone_ids: list[str] = []
    invalid_buffer_ids: list[str] = []
    max_burn_rate_index = 0.0

    for item in buffer_records or []:
        if not isinstance(item, dict):
            continue
        chain_id = str(item.get("chain_id") or "").strip()
        if not chain_id:
            continue

        evaluated_chain_count += 1
        try:
            raw_prog = float(item.get("chain_progress_pct") or 0.0)
        except (TypeError, ValueError):
            raw_prog = 0.0
        chain_progress_pct = max(0.0, min(100.0, raw_prog))

        try:
            buffer_total_days = float(item.get("buffer_total_days") or 0.0)
        except (TypeError, ValueError):
            buffer_total_days = 0.0

        try:
            buffer_consumed_days = float(item.get("buffer_consumed_days") or 0.0)
        except (TypeError, ValueError):
            buffer_consumed_days = 0.0

        recovery_plan_defined = bool(item.get("recovery_plan_defined", False))

        if buffer_total_days <= 0.0:
            invalid_buffer_ids.append(chain_id)

        buffer_consumption_pct = (
            round((buffer_consumed_days / buffer_total_days) * 100.0, 2)
            if buffer_total_days > 0.0
            else 100.0
        )
        if chain_progress_pct > 0.0:
            burn_rate_index = round(
                buffer_consumption_pct / max(chain_progress_pct, 1.0), 2
            )
        else:
            burn_rate_index = (
                round(buffer_consumption_pct, 2)
                if buffer_consumption_pct > 0.0
                else 0.0
            )
        if burn_rate_index > max_burn_rate_index:
            max_burn_rate_index = burn_rate_index

        red_threshold_pct = 33.33 + 0.6667 * chain_progress_pct
        yellow_threshold_pct = 16.67 + 0.5 * chain_progress_pct

        if (
            buffer_consumption_pct > red_threshold_pct
            or buffer_consumed_days > buffer_total_days
        ):
            red_zone_chain_ids.append(chain_id)
            if not recovery_plan_defined:
                unmitigated_red_zone_ids.append(chain_id)
        elif buffer_consumption_pct > yellow_threshold_pct:
            yellow_zone_chain_ids.append(chain_id)
        else:
            green_zone_chain_ids.append(chain_id)

    is_valid = bool(
        evaluated_chain_count > 0
        and len(unmitigated_red_zone_ids) == 0
        and len(invalid_buffer_ids) == 0
    )

    return {
        "evaluated_chain_count": evaluated_chain_count,
        "green_zone_chain_ids": green_zone_chain_ids,
        "yellow_zone_chain_ids": yellow_zone_chain_ids,
        "red_zone_chain_ids": red_zone_chain_ids,
        "unmitigated_red_zone_ids": unmitigated_red_zone_ids,
        "invalid_buffer_ids": invalid_buffer_ids,
        "max_burn_rate_index": max_burn_rate_index,
        "is_valid": is_valid,
    }




def validate_rolling_wave_planning_horizon(
    wbs_packages: Sequence[Mapping[str, Any]] | None,
    *,
    near_term_horizon_days: int = 30,
) -> dict[str, Any]:
    """Valida la gobernanza de Planificación Gradual (Rolling Wave, PMBOK §5.4.2.2 y §6.2.2.3).

    - Planning packages cerca del horizonte -> ``undecomposed_near_term_planning_ids``.
    - Planning packages lejos del horizonte (correctos) -> ``valid_far_term_planning_ids``.
    - Work packages cerca del horizonte sin actividades detalladas, dueño
      asignado o esfuerzo positivo -> ``unready_near_term_work_package_ids``.
    - ``package_type`` fuera de {'work_package', 'planning_package'} ->
      ``invalid_package_type_ids``.
    """
    if not isinstance(wbs_packages, (list, tuple)):
        wbs_packages = []

    evaluated_package_count = 0
    undecomposed_near_term_planning_ids: list[str] = []
    unready_near_term_work_package_ids: list[str] = []
    valid_far_term_planning_ids: list[str] = []
    invalid_package_type_ids: list[str] = []

    for item in wbs_packages:
        if not isinstance(item, Mapping):
            continue
        package_id = str(item.get("package_id") or "").strip()
        if not package_id:
            continue
        evaluated_package_count += 1

        package_type = str(item.get("package_type") or "").strip().lower()
        if package_type not in {"work_package", "planning_package"}:
            invalid_package_type_ids.append(package_id)
            continue

        try:
            days_until_start = float(item.get("days_until_start", 0))
        except (TypeError, ValueError):
            days_until_start = 0.0

        if package_type == "planning_package":
            if days_until_start <= float(near_term_horizon_days):
                undecomposed_near_term_planning_ids.append(package_id)
            else:
                valid_far_term_planning_ids.append(package_id)
        elif days_until_start <= float(near_term_horizon_days):
            try:
                estimated_effort_hours = float(item.get("estimated_effort_hours", 0.0))
            except (TypeError, ValueError):
                estimated_effort_hours = 0.0
            has_detailed_activities = bool(item.get("has_detailed_activities", False))
            has_assigned_owner = bool(item.get("has_assigned_owner", False))
            if (
                not has_detailed_activities
                or not has_assigned_owner
                or estimated_effort_hours <= 0.0
            ):
                unready_near_term_work_package_ids.append(package_id)

    is_valid = bool(
        evaluated_package_count > 0
        and len(undecomposed_near_term_planning_ids) == 0
        and len(unready_near_term_work_package_ids) == 0
        and len(invalid_package_type_ids) == 0
    )

    return {
        "evaluated_package_count": evaluated_package_count,
        "undecomposed_near_term_planning_ids": undecomposed_near_term_planning_ids,
        "unready_near_term_work_package_ids": unready_near_term_work_package_ids,
        "valid_far_term_planning_ids": valid_far_term_planning_ids,
        "invalid_package_type_ids": invalid_package_type_ids,
        "is_valid": is_valid,
    }


def validate_schedule_path_convergence_risk(
    merge_nodes: Sequence[Mapping[str, Any]] | None,
    *,
    max_safe_predecessors: int = 3,
    min_near_critical_float_days: float = 2.0,
) -> dict[str, Any]:
    """Evalúa puntos de convergencia de rutas y sesgo de fusión (Merge Bias) en el diagrama de red según PMI PMBOK §6.3.2.1, §6.5.2 y §11.4.2.2."""
    if not isinstance(merge_nodes, (list, tuple)):
        merge_nodes = []

    evaluated_node_count = 0
    high_convergence_node_ids: list[str] = []
    multi_near_critical_merge_ids: list[str] = []
    unbuffered_merge_hotspot_ids: list[str] = []
    invalid_node_ids: list[str] = []

    for item in merge_nodes:
        if not isinstance(item, Mapping):
            continue
        node_id = str(item.get("node_id") or "").strip()
        if not node_id:
            continue
        evaluated_node_count += 1

        raw_floats = item.get("predecessor_float_days")
        if not isinstance(raw_floats, (list, tuple)) or len(raw_floats) == 0:
            invalid_node_ids.append(node_id)
            continue

        parsed_floats: list[float] = []
        has_invalid_float = False
        for val in raw_floats:
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                has_invalid_float = True
                break
            f_val = float(val)
            if f_val < 0.0:
                has_invalid_float = True
                break
            parsed_floats.append(f_val)

        if has_invalid_float:
            invalid_node_ids.append(node_id)
            continue

        predecessor_count = len(parsed_floats)
        near_critical_predecessor_count = sum(
            1 for f in parsed_floats if f <= float(min_near_critical_float_days)
        )

        is_high_convergence = predecessor_count > int(max_safe_predecessors)
        is_multi_near_critical = near_critical_predecessor_count >= 2

        if is_high_convergence:
            high_convergence_node_ids.append(node_id)
        if is_multi_near_critical:
            multi_near_critical_merge_ids.append(node_id)

        risk_mitigation_buffered = bool(item.get("risk_mitigation_buffered", False))
        if (is_high_convergence or is_multi_near_critical) and not risk_mitigation_buffered:
            unbuffered_merge_hotspot_ids.append(node_id)

    is_valid = bool(
        evaluated_node_count > 0
        and len(unbuffered_merge_hotspot_ids) == 0
        and len(invalid_node_ids) == 0
    )

    return {
        "evaluated_node_count": evaluated_node_count,
        "high_convergence_node_ids": high_convergence_node_ids,
        "multi_near_critical_merge_ids": multi_near_critical_merge_ids,
        "unbuffered_merge_hotspot_ids": unbuffered_merge_hotspot_ids,
        "invalid_node_ids": invalid_node_ids,
        "is_valid": is_valid,
    }


def validate_schedule_risk_mitigation_residual_delay(
    risk_responses: Sequence[Mapping[str, Any]] | None,
    *,
    max_acceptable_residual_days: float = 5.0,
) -> dict[str, Any]:
    """Valida la efectividad de las respuestas a riesgos de cronograma y la exposición de demora residual según PMI PMBOK §11.5 y §6.5."""
    if (
        risk_responses is None
        or isinstance(risk_responses, (str, bytes, Mapping))
        or not isinstance(risk_responses, Sequence)
    ):
        items: Sequence[Any] = []
    else:
        items = risk_responses

    valid_strategies = {"avoid", "mitigate", "transfer", "accept", "escalate"}
    total_evaluated = 0
    total_pre_mitigation_days = 0.0
    total_post_mitigation_days = 0.0
    ineffective_response_risk_ids: list[str] = []
    excessive_residual_risk_ids: list[str] = []
    missing_fallback_risk_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        risk_id = str(item.get("risk_id") or "").strip()
        if not risk_id:
            continue

        try:
            pre_mitigation_delay_days = max(
                0.0, float(item.get("pre_mitigation_delay_days", 0.0) or 0.0)
            )
        except (TypeError, ValueError):
            pre_mitigation_delay_days = 0.0

        try:
            post_mitigation_delay_days = max(
                0.0, float(item.get("post_mitigation_delay_days", 0.0) or 0.0)
            )
        except (TypeError, ValueError):
            post_mitigation_delay_days = 0.0

        strategy = str(item.get("strategy") or "").strip().lower()
        fallback_plan = str(item.get("fallback_plan") or "").strip()

        total_evaluated += 1
        total_pre_mitigation_days += pre_mitigation_delay_days
        total_post_mitigation_days += post_mitigation_delay_days

        if strategy not in valid_strategies or (
            strategy in {"avoid", "mitigate"}
            and post_mitigation_delay_days >= pre_mitigation_delay_days > 0.0
        ):
            ineffective_response_risk_ids.append(risk_id)

        if post_mitigation_delay_days > float(max_acceptable_residual_days):
            excessive_residual_risk_ids.append(risk_id)
            if not fallback_plan:
                missing_fallback_risk_ids.append(risk_id)

    delay_reduction_pct = (
        round(
            (
                (total_pre_mitigation_days - total_post_mitigation_days)
                / total_pre_mitigation_days
            )
            * 100.0,
            2,
        )
        if total_pre_mitigation_days > 0.0
        else 0.0
    )

    is_schedule_risk_controlled = bool(
        total_evaluated > 0
        and not ineffective_response_risk_ids
        and not excessive_residual_risk_ids
        and not missing_fallback_risk_ids
    )

    return {
        "total_evaluated": total_evaluated,
        "total_pre_mitigation_days": round(total_pre_mitigation_days, 2),
        "total_post_mitigation_days": round(total_post_mitigation_days, 2),
        "delay_reduction_pct": delay_reduction_pct,
        "ineffective_response_risk_ids": ineffective_response_risk_ids,
        "excessive_residual_risk_ids": excessive_residual_risk_ids,
        "missing_fallback_risk_ids": missing_fallback_risk_ids,
        "is_schedule_risk_controlled": is_schedule_risk_controlled,
    }




def validate_resource_smoothing_float_boundaries(
    activities: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Valida suavizado de recursos (Resource Smoothing, PMBOK §6.5.2.3).

    - Desplazamiento sobre actividades de la ruta crítica -> ``critical_path_shifted_activity_ids``.
    - Desplazamiento que excede la holgura libre -> ``float_exceeded_activity_ids``.
    - Sobreasignación residual (pico > 100%) -> ``unresolved_overallocation_activity_ids``.
    """
    if not isinstance(activities, (list, tuple)):
        activities = []

    total_activities = 0
    critical_path_shifted_activity_ids: list[str] = []
    float_exceeded_activity_ids: list[str] = []
    unresolved_overallocation_activity_ids: list[str] = []

    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    for item in activities:
        if not isinstance(item, Mapping):
            continue
        activity_id = str(item.get("activity_id") or "").strip()
        if not activity_id:
            continue

        free_float_days = max(0.0, _safe_float(item.get("free_float_days", 0.0) or 0.0, 0.0))
        total_float_days = max(0.0, _safe_float(item.get("total_float_days", 0.0) or 0.0, 0.0))
        smoothing_shift_days = max(0.0, _safe_float(item.get("smoothing_shift_days", 0.0) or 0.0, 0.0))
        peak_utilization_pct = max(0.0, _safe_float(item.get("peak_utilization_pct", 0.0) or 0.0, 0.0))
        is_critical = bool(item.get("is_critical", False)) or (total_float_days == 0.0)

        total_activities += 1

        if is_critical and smoothing_shift_days > 0.0:
            critical_path_shifted_activity_ids.append(activity_id)

        if smoothing_shift_days > free_float_days:
            float_exceeded_activity_ids.append(activity_id)

        if peak_utilization_pct > 100.0:
            unresolved_overallocation_activity_ids.append(activity_id)

    is_smoothing_valid = bool(
        total_activities > 0
        and not critical_path_shifted_activity_ids
        and not float_exceeded_activity_ids
        and not unresolved_overallocation_activity_ids
    )

    return {
        "total_activities": total_activities,
        "critical_path_shifted_activity_ids": critical_path_shifted_activity_ids,
        "float_exceeded_activity_ids": float_exceeded_activity_ids,
        "unresolved_overallocation_activity_ids": unresolved_overallocation_activity_ids,
        "is_smoothing_valid": is_smoothing_valid,
    }


def validate_sprint_velocity_commitment_stability(
    historical_velocities: Sequence[float | int] | None,
    committed_points: float,
    *,
    max_overcommitment_ratio: float = 1.15,
) -> dict[str, Any]:
    """Evalúa la estabilidad de velocidad ágil y el sobrecompromiso de capacidad del sprint según PMI PMBOK §6.4 y §9.2."""
    valid_vels: list[float] = []
    if (
        historical_velocities is not None
        and isinstance(historical_velocities, Sequence)
        and not isinstance(historical_velocities, (str, bytes, Mapping))
    ):
        for v in historical_velocities:
            if isinstance(v, bool):
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if fv >= 0.0:
                valid_vels.append(fv)

    try:
        committed = round(max(0.0, float(committed_points or 0.0)), 2)
    except (TypeError, ValueError):
        committed = 0.0

    n = len(valid_vels)
    mean_vel = (sum(valid_vels) / n) if n > 0 else 0.0
    if n == 0 or mean_vel <= 0.0:
        return {
            "sprints_analyzed": n,
            "mean_velocity": 0.0,
            "velocity_cv_pct": 0.0,
            "committed_points": committed,
            "commitment_to_mean_ratio": 0.0,
            "stability_posture": "insufficient_history",
            "is_commitment_sustainable": False,
        }

    variance = sum((v - mean_vel) ** 2 for v in valid_vels) / n
    std_dev = variance ** 0.5
    velocity_cv_pct = round((std_dev / mean_vel) * 100.0, 2)
    mean_velocity = round(mean_vel, 2)
    commitment_to_mean_ratio = round(committed / mean_vel, 4)

    if commitment_to_mean_ratio > float(max_overcommitment_ratio):
        stability_posture = "overcommitted"
    elif velocity_cv_pct > 25.0:
        stability_posture = "volatile_velocity"
    elif commitment_to_mean_ratio < 0.70:
        stability_posture = "underutilized_capacity"
    else:
        stability_posture = "predictable_sustainable"

    is_commitment_sustainable = bool(stability_posture == "predictable_sustainable")

    return {
        "sprints_analyzed": n,
        "mean_velocity": mean_velocity,
        "velocity_cv_pct": velocity_cv_pct,
        "committed_points": committed,
        "commitment_to_mean_ratio": commitment_to_mean_ratio,
        "stability_posture": stability_posture,
        "is_commitment_sustainable": is_commitment_sustainable,
    }


def validate_fpif_point_of_total_assumption(
    contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """PMBOK §12.1.1.6 — Point of Total Assumption (PTA) para contratos FPIF.

    - Fórmula PTA: ``target_cost + (ceiling_price - target_price) / buyer_share_ratio``.
    - Posturas: ``ceiling_breached`` (EAC > techo), ``above_pta_seller_absorbs``
      (PTA < EAC <= techo), ``cost_overrun_shared`` (target < EAC <= PTA) y
      ``on_or_under_target`` (EAC <= target_cost).
    """
    if not isinstance(contract, Mapping):
        return {
            "target_price": 0.0,
            "pta": 0.0,
            "estimated_actual_cost": 0.0,
            "pta_buffer_remaining": 0.0,
            "contract_posture": "invalid_inputs",
            "is_within_pta": False,
        }

    def _float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    target_cost = _float(contract.get("target_cost", 0.0) or 0.0)
    target_fee = _float(contract.get("target_fee", 0.0) or 0.0)
    ceiling_price = _float(contract.get("ceiling_price", 0.0) or 0.0)
    buyer_share_ratio = _float(contract.get("buyer_share_ratio", 0.0) or 0.0)
    estimated_actual_cost = _float(contract.get("estimated_actual_cost", 0.0) or 0.0)

    if (
        target_cost <= 0
        or target_fee < 0
        or ceiling_price < (target_cost + target_fee)
        or not (0.0 < buyer_share_ratio < 1.0)
        or estimated_actual_cost <= 0
    ):
        return {
            "target_price": 0.0,
            "pta": 0.0,
            "estimated_actual_cost": 0.0,
            "pta_buffer_remaining": 0.0,
            "contract_posture": "invalid_inputs",
            "is_within_pta": False,
        }

    target_price = round(target_cost + target_fee, 2)
    pta = round(target_cost + ((ceiling_price - target_price) / buyer_share_ratio), 2)
    estimated_actual_cost = round(estimated_actual_cost, 2)
    pta_buffer_remaining = round(pta - estimated_actual_cost, 2)

    if estimated_actual_cost > ceiling_price:
        contract_posture = "ceiling_breached"
    elif estimated_actual_cost > pta:
        contract_posture = "above_pta_seller_absorbs"
    elif estimated_actual_cost > target_cost:
        contract_posture = "cost_overrun_shared"
    else:
        contract_posture = "on_or_under_target"

    is_within_pta = bool(contract_posture in {"cost_overrun_shared", "on_or_under_target"})

    return {
        "target_price": target_price,
        "pta": pta,
        "estimated_actual_cost": estimated_actual_cost,
        "pta_buffer_remaining": pta_buffer_remaining,
        "contract_posture": contract_posture,
        "is_within_pta": is_within_pta,
    }


def validate_schedule_network_lead_lag_and_float_feasibility(
    predecessor_duration_days: float,
    successor_duration_days: float,
    relationship_type: str = "FS",
    lag_days: float = 0.0,
    total_float_days: float = 0.0,
    max_lead_ratio_pct: float = 50.0,
) -> dict[str, Any]:
    """Valida la lógica de red PDM (Precedence Diagramming Method) y DCMA 14-Point Schedule Assessment según PMI PMBOK §6.3 y §6.5."""
    pred_dur = float(predecessor_duration_days)
    succ_dur = float(successor_duration_days)
    max_lead_ratio = float(max_lead_ratio_pct)

    if pred_dur <= 0.0:
        raise ValueError("predecessor_duration_days debe ser > 0.")
    if succ_dur <= 0.0:
        raise ValueError("successor_duration_days debe ser > 0.")
    if not (0.0 < max_lead_ratio <= 100.0):
        raise ValueError("max_lead_ratio_pct debe estar en (0.0, 100.0].")

    norm_rel = str(relationship_type or "").strip().upper()
    if norm_rel not in {"FS", "SS", "FF", "SF"}:
        raise ValueError(
            "relationship_type inválido; use 'FS', 'SS', 'FF' o 'SF'."
        )

    lag_val = round(float(lag_days), 2)
    float_val = round(float(total_float_days), 2)
    lead_days = round(max(0.0, -float(lag_days)), 2)
    lead_ratio_pct = (
        round((lead_days / pred_dur) * 100.0, 2) if lead_days > 0.0 else 0.0
    )

    excessive_lead_detected = bool(
        lead_ratio_pct > max_lead_ratio
        or (lead_days > 0.0 and lead_days >= succ_dur)
    )
    sf_relationship_warning = bool(norm_rel == "SF")
    negative_float_detected = bool(float(total_float_days) < 0.0)

    is_schedule_logic_healthy = bool(
        not excessive_lead_detected
        and not sf_relationship_warning
        and not negative_float_detected
    )

    recommendations: list[str] = []
    if negative_float_detected:
        recommendations.append(
            "Resolver la holgura total negativa mediante fast-tracking, crashing o ajuste formal de restricciones de fecha (DCMA 14-Point)."
        )
    if excessive_lead_detected:
        recommendations.append(
            "Descomponer la actividad predecesora y reemplazar el adelanto (lead) excesivo por relaciones Finish-to-Start o Start-to-Start explícitas."
        )
    if sf_relationship_warning:
        recommendations.append(
            "Evitar relaciones Start-to-Finish (SF) salvo justificación técnica documentada; preferir relaciones FS."
        )

    if negative_float_detected or excessive_lead_detected:
        status = "critical"
    elif sf_relationship_warning:
        status = "warning"
    else:
        status = "healthy"

    return {
        "relationship_type": norm_rel,
        "lag_days": lag_val,
        "lead_days": lead_days,
        "lead_ratio_pct": lead_ratio_pct,
        "total_float_days": float_val,
        "excessive_lead_detected": excessive_lead_detected,
        "sf_relationship_warning": sf_relationship_warning,
        "negative_float_detected": negative_float_detected,
        "is_schedule_logic_healthy": is_schedule_logic_healthy,
        "status": status,
        "recommendations": recommendations,
    }


def validate_three_point_pert_skew_and_confidence_band(
    optimistic: float,
    most_likely: float,
    pessimistic: float,
    max_cv_pct: float = 25.0,
) -> dict[str, Any]:
    """Valida estimaciones de Tres Valores (Beta PERT y Triangular), bandas de confianza y asimetría de cola según PMI PMBOK §6.4.2.4 y §7.2.2.4."""
    numeric_inputs = {
        "optimistic": optimistic,
        "most_likely": most_likely,
        "pessimistic": pessimistic,
        "max_cv_pct": max_cv_pct,
    }
    for name, value in numeric_inputs.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not (value == value)
            or abs(float(value)) == float("inf")
        ):
            raise ValueError(f"PERT 3-Point: {name} debe ser numérico real, no bool/NaN/Inf")

    opt = float(optimistic)
    ml = float(most_likely)
    pess = float(pessimistic)
    max_cv = float(max_cv_pct)

    if opt <= 0.0:
        raise ValueError("PERT 3-Point: optimistic debe ser > 0")
    if not (opt <= ml <= pess):
        raise ValueError("PERT 3-Point: debe cumplirse optimistic <= most_likely <= pessimistic")
    if max_cv <= 0.0:
        raise ValueError("PERT 3-Point: max_cv_pct debe ser > 0")

    pert_expected = round((opt + 4.0 * ml + pess) / 6.0, 2)
    triangular_expected = round((opt + ml + pess) / 3.0, 2)
    standard_deviation = round((pess - opt) / 6.0, 4)
    variance = round(standard_deviation ** 2, 4)
    coefficient_of_variation_pct = round((standard_deviation / pert_expected) * 100.0, 2)
    confidence_68_band = (
        round(pert_expected - standard_deviation, 2),
        round(pert_expected + standard_deviation, 2),
    )
    confidence_95_band = (
        round(pert_expected - 2.0 * standard_deviation, 2),
        round(pert_expected + 2.0 * standard_deviation, 2),
    )
    excessive_uncertainty_detected = bool(coefficient_of_variation_pct > max_cv)
    severe_right_skew_detected = bool(
        (pess - ml) > 2.5 * max(0.01, ml - opt) and pess > ml
    )
    is_estimate_reliable = bool(
        not excessive_uncertainty_detected and not severe_right_skew_detected
    )

    return {
        "pert_expected": pert_expected,
        "triangular_expected": triangular_expected,
        "standard_deviation": standard_deviation,
        "variance": variance,
        "coefficient_of_variation_pct": coefficient_of_variation_pct,
        "confidence_68_band": confidence_68_band,
        "confidence_95_band": confidence_95_band,
        "excessive_uncertainty_detected": excessive_uncertainty_detected,
        "severe_right_skew_detected": severe_right_skew_detected,
        "is_estimate_reliable": is_estimate_reliable,
    }


def validate_deliverable_acceptance_criteria_measurability(
    deliverables: object,
) -> dict[str, object]:
    """Valida que los criterios de aceptación de entregables del Enunciado del Alcance y Diccionario WBS sean medibles, verificables y libres de ambigüedad subjetiva según PMI PMBOK §5.3 y §5.4."""
    total_evaluated = 0
    missing_criteria_deliverable_ids: list[str] = []
    invalid_verification_method_deliverable_ids: list[str] = []
    ambiguous_subjective_deliverable_ids: list[str] = []

    valid_verification_methods = {
        "inspection",
        "test",
        "demonstration",
        "analysis",
        "audit",
    }
    subjective_terms = (
        "adecuado",
        "optimo",
        "óptimo",
        "rapido",
        "rápido",
        "intuitivo",
        "amigable",
        "buena calidad",
        "según corresponda",
        "tbd",
        "por definir",
    )

    if isinstance(deliverables, Sequence) and not isinstance(
        deliverables, (str, bytes, bytearray)
    ):
        for item in deliverables:
            if not isinstance(item, Mapping):
                continue
            deliv_id = str(
                item.get("deliverable_id") or item.get("id") or ""
            ).strip()
            if not deliv_id:
                continue

            total_evaluated += 1
            acceptance_criteria = str(
                item.get("acceptance_criteria") or ""
            ).strip()
            verification_method = (
                str(item.get("verification_method") or "").strip().lower()
            )
            designated_approver_role = str(
                item.get("designated_approver_role") or ""
            ).strip()
            has_quantitative_threshold = bool(
                item.get("has_quantitative_threshold", False)
            )

            if len(acceptance_criteria) < 15 or not designated_approver_role:
                missing_criteria_deliverable_ids.append(deliv_id)

            if verification_method not in valid_verification_methods:
                invalid_verification_method_deliverable_ids.append(deliv_id)

            criteria_lower = acceptance_criteria.lower()
            if not has_quantitative_threshold and any(
                term in criteria_lower for term in subjective_terms
            ):
                ambiguous_subjective_deliverable_ids.append(deliv_id)

    return {
        "total_evaluated": total_evaluated,
        "missing_criteria_deliverable_ids": missing_criteria_deliverable_ids,
        "invalid_verification_method_deliverable_ids": invalid_verification_method_deliverable_ids,
        "ambiguous_subjective_deliverable_ids": ambiguous_subjective_deliverable_ids,
        "is_acceptance_criteria_measurable": (
            len(missing_criteria_deliverable_ids) == 0
            and len(invalid_verification_method_deliverable_ids) == 0
            and len(ambiguous_subjective_deliverable_ids) == 0
        ),
    }


def validate_tm_contract_not_to_exceed_and_rate_card(
    tm_contracts: object,
    *,
    burn_warning_threshold_pct: float = 85.0,
) -> dict[str, object]:
    """Valida techo Not-To-Exceed (NTE) y gobernanza de rate card en contratos Time & Materials según PMI PMBOK §12.1 y §12.2."""
    total_evaluated = 0
    missing_nte_ceiling_contract_ids: list[str] = []
    uncontrolled_rate_or_timesheet_contract_ids: list[str] = []
    nte_threshold_breach_contract_ids: list[str] = []

    threshold_pct = float(burn_warning_threshold_pct)
    contracts: Sequence[Any] = (
        tm_contracts
        if isinstance(tm_contracts, Sequence)
        and not isinstance(tm_contracts, (str, bytes, bytearray))
        else []
    )

    for item in contracts:
        if not isinstance(item, Mapping):
            continue
        contract_id = str(item.get("contract_id") or item.get("id") or "").strip()
        if not contract_id:
            continue

        total_evaluated += 1

        try:
            not_to_exceed_ceiling = float(
                item.get("not_to_exceed_ceiling", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            not_to_exceed_ceiling = 0.0
        try:
            cumulative_billed_amount = float(
                item.get("cumulative_billed_amount", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            cumulative_billed_amount = 0.0
        has_approved_rate_card = bool(item.get("has_approved_rate_card", False))
        timesheet_supervisor_signoff_required = bool(
            item.get("timesheet_supervisor_signoff_required", False)
        )

        if not_to_exceed_ceiling <= 0.0:
            missing_nte_ceiling_contract_ids.append(contract_id)

        if (
            not has_approved_rate_card
            or not timesheet_supervisor_signoff_required
        ):
            uncontrolled_rate_or_timesheet_contract_ids.append(contract_id)

        if not_to_exceed_ceiling > 0.0:
            burn_pct = (
                cumulative_billed_amount / not_to_exceed_ceiling
            ) * 100.0
            if burn_pct >= threshold_pct:
                nte_threshold_breach_contract_ids.append(contract_id)

    is_tm_contract_governance_valid = bool(
        len(missing_nte_ceiling_contract_ids) == 0
        and len(uncontrolled_rate_or_timesheet_contract_ids) == 0
        and len(nte_threshold_breach_contract_ids) == 0
    )

    return {
        "total_evaluated": total_evaluated,
        "missing_nte_ceiling_contract_ids": missing_nte_ceiling_contract_ids,
        "uncontrolled_rate_or_timesheet_contract_ids": uncontrolled_rate_or_timesheet_contract_ids,
        "nte_threshold_breach_contract_ids": nte_threshold_breach_contract_ids,
        "is_tm_contract_governance_valid": is_tm_contract_governance_valid,
    }


def validate_resource_calendar_overtime_and_blackout_bounds(
    calendar_allocations: object,
    *,
    max_weekly_overtime_hours: float = 10.0,
) -> dict[str, object]:
    """Valida calendarios de recursos, autorización y tope de horas extra semanales, y restricciones de ventanas de congelamiento/festivos según PMI PMBOK §6.5 y §9.3."""
    total_evaluated = 0
    unauthorized_overtime_allocation_ids: list[str] = []
    excessive_overtime_cap_allocation_ids: list[str] = []
    blackout_violation_allocation_ids: list[str] = []

    if isinstance(calendar_allocations, Sequence) and not isinstance(
        calendar_allocations, (str, bytes, bytearray)
    ):
        for item in calendar_allocations:
            if not isinstance(item, Mapping):
                continue
            alloc_id = str(
                item.get("allocation_id") or item.get("id") or ""
            ).strip()
            if not alloc_id:
                continue

            total_evaluated += 1
            try:
                standard_weekly_hours = float(
                    item.get("standard_weekly_hours", 40.0) or 40.0
                )
            except (TypeError, ValueError):
                standard_weekly_hours = 40.0

            try:
                scheduled_weekly_hours = float(
                    item.get("scheduled_weekly_hours", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                scheduled_weekly_hours = 0.0

            overtime_authorized = bool(item.get("overtime_authorized", False))
            scheduled_during_blackout_or_holiday = bool(
                item.get("scheduled_during_blackout_or_holiday", False)
            )
            change_freeze_exception_approved = bool(
                item.get("change_freeze_exception_approved", False)
            )

            overtime_hours = max(
                0.0, scheduled_weekly_hours - standard_weekly_hours
            )

            if overtime_hours > 0.0 and not overtime_authorized:
                unauthorized_overtime_allocation_ids.append(alloc_id)

            if (
                overtime_hours > float(max_weekly_overtime_hours)
                or scheduled_weekly_hours <= 0.0
            ):
                excessive_overtime_cap_allocation_ids.append(alloc_id)

            if (
                scheduled_during_blackout_or_holiday is True
                and not change_freeze_exception_approved
            ):
                blackout_violation_allocation_ids.append(alloc_id)

    return {
        "total_evaluated": total_evaluated,
        "unauthorized_overtime_allocation_ids": unauthorized_overtime_allocation_ids,
        "excessive_overtime_cap_allocation_ids": excessive_overtime_cap_allocation_ids,
        "blackout_violation_allocation_ids": blackout_violation_allocation_ids,
        "is_resource_calendar_compliant": (
            len(unauthorized_overtime_allocation_ids) == 0
            and len(excessive_overtime_cap_allocation_ids) == 0
            and len(blackout_violation_allocation_ids) == 0
        ),
    }



def validate_fpif_share_ratio_and_point_of_total_assumption(
    fpif_contracts: list[dict[str, object]],
) -> dict[str, object]:
    """Valida share ratio y Point of Total Assumption (PTA) en contratos Fixed-Price Incentive Fee según PMI PMBOK §12.1."""
    total_contracts = 0
    invalid_share_ratio_contract_ids: list[str] = []
    invalid_ceiling_or_target_contract_ids: list[str] = []
    degenerate_pta_contract_ids: list[str] = []
    pta_breached_contract_ids: list[str] = []
    computed_pta_by_contract: dict[str, float] = {}

    contracts: Sequence[Any] = (
        fpif_contracts
        if isinstance(fpif_contracts, Sequence)
        and not isinstance(fpif_contracts, (str, bytes, bytearray))
        else []
    )

    def _coerce_amount(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    for item in contracts:
        if not isinstance(item, Mapping):
            continue
        contract_id = str(item.get("contract_id") or item.get("id") or "").strip()
        if not contract_id:
            continue

        total_contracts += 1

        buyer_share_pct = _coerce_amount(item.get("buyer_share_pct"))
        seller_share_pct = _coerce_amount(item.get("seller_share_pct"))
        target_cost = _coerce_amount(item.get("target_cost"))
        target_fee = _coerce_amount(item.get("target_fee"))
        ceiling_price = _coerce_amount(item.get("ceiling_price"))
        actual_or_forecast_cost = _coerce_amount(
            item.get("actual_or_forecast_cost", 0.0)
        )

        if (
            abs((buyer_share_pct + seller_share_pct) - 100.0) > 0.01
            or buyer_share_pct <= 0.0
            or seller_share_pct <= 0.0
        ):
            invalid_share_ratio_contract_ids.append(contract_id)

        target_price = round(target_cost + target_fee, 2)
        if target_cost <= 0.0 or target_fee < 0.0 or ceiling_price < target_price:
            invalid_ceiling_or_target_contract_ids.append(contract_id)

        if buyer_share_pct > 0.0 and ceiling_price >= target_price and target_cost > 0.0:
            pta = round(
                target_cost
                + ((ceiling_price - target_price) / (buyer_share_pct / 100.0)),
                2,
            )
            computed_pta_by_contract[contract_id] = pta
            if pta < target_cost or pta > ceiling_price:
                degenerate_pta_contract_ids.append(contract_id)
            if actual_or_forecast_cost > pta:
                pta_breached_contract_ids.append(contract_id)

    is_fpif_governance_valid = bool(
        len(invalid_share_ratio_contract_ids) == 0
        and len(invalid_ceiling_or_target_contract_ids) == 0
        and len(degenerate_pta_contract_ids) == 0
        and len(pta_breached_contract_ids) == 0
    )

    return {
        "total_contracts": total_contracts,
        "invalid_share_ratio_contract_ids": invalid_share_ratio_contract_ids,
        "invalid_ceiling_or_target_contract_ids": invalid_ceiling_or_target_contract_ids,
        "degenerate_pta_contract_ids": degenerate_pta_contract_ids,
        "pta_breached_contract_ids": pta_breached_contract_ids,
        "computed_pta_by_contract": computed_pta_by_contract,
        "is_fpif_governance_valid": is_fpif_governance_valid,
    }


def validate_ccpm_feeding_and_project_buffer_sizing(
    chain_buffers: list[dict[str, object]],
    *,
    min_buffer_to_chain_ratio: float = 0.20,
    max_buffer_to_chain_ratio: float = 0.60,
) -> dict[str, object]:
    """Valida el dimensionamiento de buffers de proyecto y de alimentación (Feeding & Project Buffers) y las incursiones en la Zona Roja del Fever Chart sin plan de recuperación según PMI PMBOK §6.3 y §6.5 (CCPM)."""
    valid_types = {"project", "feeding", "resource"}

    try:
        min_ratio = float(min_buffer_to_chain_ratio)
    except (TypeError, ValueError):
        min_ratio = 0.20

    try:
        max_ratio = float(max_buffer_to_chain_ratio)
    except (TypeError, ValueError):
        max_ratio = 0.60

    total_buffers = 0
    invalid_buffer_definition_ids: list[str] = []
    misaligned_buffer_sizing_ids: list[str] = []
    unmitigated_fever_chart_red_zone_ids: list[str] = []

    if isinstance(chain_buffers, Sequence) and not isinstance(
        chain_buffers, (str, bytes, bytearray)
    ):
        for item in chain_buffers:
            if not isinstance(item, Mapping):
                continue
            buffer_id = str(
                item.get("buffer_id") or item.get("id") or ""
            ).strip()
            if not buffer_id:
                continue

            total_buffers += 1
            buffer_type = (
                str(item.get("buffer_type") or "").strip().lower()
            )

            def _num(key: str, default: float = -1.0) -> float:
                raw = item.get(key)
                if raw is None or isinstance(raw, bool):
                    return default
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return default

            chain_duration = _num("feeding_chain_duration_days", -1.0)
            buffer_size = _num("buffer_size_days", -1.0)
            buffer_consumed = _num("buffer_consumed_days", 0.0)
            chain_progress_pct = _num("chain_progress_pct", 0.0)
            recovery_triggered = bool(item.get("recovery_plan_triggered", False))

            if (
                buffer_type not in valid_types
                or chain_duration <= 0.0
                or buffer_size <= 0.0
                or buffer_consumed < 0.0
            ):
                invalid_buffer_definition_ids.append(buffer_id)
                continue

            if buffer_type in {"project", "feeding"}:
                sizing_ratio = buffer_size / chain_duration
                if sizing_ratio < min_ratio or sizing_ratio > max_ratio:
                    misaligned_buffer_sizing_ids.append(buffer_id)

            consumption_pct = (buffer_consumed / buffer_size) * 100.0
            red_zone_limit_pct = 30.0 + (
                0.70 * max(0.0, min(100.0, chain_progress_pct))
            )
            if consumption_pct > red_zone_limit_pct and not recovery_triggered:
                unmitigated_fever_chart_red_zone_ids.append(buffer_id)

    return {
        "total_buffers": total_buffers,
        "invalid_buffer_definition_ids": invalid_buffer_definition_ids,
        "misaligned_buffer_sizing_ids": misaligned_buffer_sizing_ids,
        "unmitigated_fever_chart_red_zone_ids": unmitigated_fever_chart_red_zone_ids,
        "is_ccpm_buffer_governance_valid": (
            len(invalid_buffer_definition_ids) == 0
            and len(misaligned_buffer_sizing_ids) == 0
            and len(unmitigated_fever_chart_red_zone_ids) == 0
        ),
    }


def validate_wbs_hundred_percent_rule_decomposition(
    parent_wbs_nodes: list[dict[str, object]],
    *,
    tolerance_pct: float = 0.01,
) -> dict[str, object]:
    """Valida la Regla del 100% en la descomposición jerárquica de la EDT/WBS (esfuerzo y presupuesto de hijos igual al 100% del padre), ausencia de hijos únicos redundantes y exclusividad mutua de entregables según PMI PMBOK §5.4 y §6.2."""
    try:
        tol_pct = float(tolerance_pct)
    except (TypeError, ValueError):
        tol_pct = 0.01

    total_parent_nodes = 0
    invalid_or_undecomposed_parent_codes: list[str] = []
    single_child_redundant_decomposition_codes: list[str] = []
    hundred_percent_rule_violation_codes: list[str] = []
    overlapping_child_scope_codes: list[str] = []

    if isinstance(parent_wbs_nodes, Sequence) and not isinstance(
        parent_wbs_nodes, (str, bytes, bytearray)
    ):
        for item in parent_wbs_nodes:
            if not isinstance(item, Mapping):
                continue
            parent_code = str(
                item.get("parent_code") or item.get("code") or ""
            ).strip()
            if not parent_code:
                continue

            total_parent_nodes += 1

            def _num(mapping: Mapping[str, Any], key: str, default: float = -1.0) -> float:
                raw = mapping.get(key)
                if raw is None or isinstance(raw, bool):
                    return default
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return default

            parent_effort = _num(item, "parent_planned_effort_hours", -1.0)
            parent_budget = _num(item, "parent_planned_budget", -1.0)

            raw_children = item.get("children")
            children = (
                [c for c in raw_children if isinstance(c, Mapping)]
                if isinstance(raw_children, Sequence)
                and not isinstance(raw_children, (str, bytes, bytearray))
                else []
            )

            if parent_effort <= 0.0 or parent_budget <= 0.0 or not children:
                invalid_or_undecomposed_parent_codes.append(parent_code)
                continue

            if len(children) == 1:
                single_child_redundant_decomposition_codes.append(parent_code)

            children_effort = 0.0
            children_budget = 0.0
            has_invalid_child_value = False
            seen_keys: set[str] = set()
            has_overlapping_scope = False

            for child in children:
                c_effort = _num(child, "effort_hours", 0.0)
                c_budget = _num(child, "budget", 0.0)
                if c_effort <= 0.0 or c_budget < 0.0:
                    has_invalid_child_value = True
                children_effort += c_effort
                children_budget += c_budget

                scope_key = (
                    str(child.get("scope_deliverable_key") or "").strip().lower()
                )
                if scope_key:
                    if scope_key in seen_keys:
                        has_overlapping_scope = True
                    seen_keys.add(scope_key)

            effort_diff_pct = (
                abs(children_effort - parent_effort) / parent_effort * 100.0
            )
            budget_diff_pct = (
                abs(children_budget - parent_budget) / parent_budget * 100.0
            )

            if (
                effort_diff_pct > tol_pct
                or budget_diff_pct > tol_pct
                or has_invalid_child_value
            ):
                hundred_percent_rule_violation_codes.append(parent_code)

            if has_overlapping_scope:
                overlapping_child_scope_codes.append(parent_code)

    return {
        "total_parent_nodes": total_parent_nodes,
        "invalid_or_undecomposed_parent_codes": invalid_or_undecomposed_parent_codes,
        "single_child_redundant_decomposition_codes": single_child_redundant_decomposition_codes,
        "hundred_percent_rule_violation_codes": hundred_percent_rule_violation_codes,
        "overlapping_child_scope_codes": overlapping_child_scope_codes,
        "is_wbs_hundred_percent_rule_valid": (
            len(invalid_or_undecomposed_parent_codes) == 0
            and len(single_child_redundant_decomposition_codes) == 0
            and len(hundred_percent_rule_violation_codes) == 0
            and len(overlapping_child_scope_codes) == 0
        ),
    }


def validate_emv_decision_tree_and_contingency_reserve(
    decision_nodes: list[dict[str, object]],
    *,
    allocated_contingency_reserve: float = 0.0,
) -> dict[str, object]:
    """Valida árbol de decisión EMV y suficiencia de reserva de contingencia (PMBOK §11.4).

    Cada nodo declarado aporta `node_id` y `branches` (cada rama con
    `branch_id`, `probability` y `monetary_impact`):
    - `empty_branch_node_ids`: nodos sin lista de ramas vacía/inexistente.
    - `invalid_probability_range_node_ids`: ramas con probabilidad fuera de [0.0, 1.0].
    - `unnormalized_probability_sum_node_ids`: suma de probabilidades desviada
      de 1.0 por más de 0.001 en nodos con ramas.
    - Los nodos sin hallazgos (1-3) reciben `emv_by_node[node_id]` =
      round(Σ prob * impacto, 2); `total_positive_threat_emv` suma solo los
      EMV positivos (2 dec); `reserve_shortfall` = round(max(0, EMV
      positivo total - reserva asignada), 2) y
      `has_contingency_reserve_shortfall` cuando excede 0.01.
    - `is_emv_tree_valid`: las 3 listas vacías y sin shortfall.
    """
    empty_branch_node_ids: list[str] = []
    invalid_probability_range_node_ids: list[str] = []
    unnormalized_probability_sum_node_ids: list[str] = []
    emv_by_node: dict[str, float] = {}

    nodes = [n for n in (decision_nodes or []) if isinstance(n, dict)]
    total_nodes = len(nodes)

    for node in nodes:
        node_id = str(node.get("node_id", "")).strip()
        branches = node.get("branches")

        if not isinstance(branches, list) or len(branches) == 0:
            empty_branch_node_ids.append(node_id)
            continue

        has_invalid_probability = False
        prob_sum = 0.0
        for branch in branches:
            if not isinstance(branch, dict):
                has_invalid_probability = True
                continue
            try:
                probability = float(
                    branch.get("probability", 0.0) if branch.get("probability", 0.0) is not None else 0.0
                )
            except (TypeError, ValueError):
                has_invalid_probability = True
                probability = 0.0
            if probability < 0.0 or probability > 1.0:
                has_invalid_probability = True
            prob_sum += probability

        if has_invalid_probability:
            invalid_probability_range_node_ids.append(node_id)
        if abs(prob_sum - 1.0) > 0.001:
            unnormalized_probability_sum_node_ids.append(node_id)

        if has_invalid_probability or abs(prob_sum - 1.0) > 0.001:
            continue

        node_emv = round(
            sum(
                float(b.get("probability", 0.0) or 0.0)
                * float(b.get("monetary_impact", 0.0) or 0.0)
                for b in branches
                if isinstance(b, dict)
            ),
            2,
        )
        emv_by_node[node_id] = node_emv

    total_positive_threat_emv = round(sum(max(0.0, v) for v in emv_by_node.values()), 2)
    reserve_shortfall = round(
        max(0.0, total_positive_threat_emv - float(allocated_contingency_reserve)), 2
    )
    has_contingency_reserve_shortfall = reserve_shortfall > 0.01

    return {
        "total_nodes": total_nodes,
        "emv_by_node": emv_by_node,
        "total_positive_threat_emv": total_positive_threat_emv,
        "reserve_shortfall": reserve_shortfall,
        "has_contingency_reserve_shortfall": has_contingency_reserve_shortfall,
        "empty_branch_node_ids": empty_branch_node_ids,
        "invalid_probability_range_node_ids": invalid_probability_range_node_ids,
        "unnormalized_probability_sum_node_ids": unnormalized_probability_sum_node_ids,
        "is_emv_tree_valid": (
            len(empty_branch_node_ids) == 0
            and len(invalid_probability_range_node_ids) == 0
            and len(unnormalized_probability_sum_node_ids) == 0
            and not has_contingency_reserve_shortfall
        ),
    }


def validate_parametric_estimation_model_fit(
    r_squared: float,
    sample_size: int,
    independent_variables_count: int,
    mean_absolute_percentage_error_pct: float,
    *,
    extrapolation_beyond_historical_range: bool = False,
    scale_adjustment_documented: bool = False,
    min_r_squared: float = 0.70,
    max_mape_pct: float = 25.0,
) -> dict[str, Any]:
    """PMBOK §6.4 / §7.2 — valida ajuste estadístico de regresión paramétrica (R², grados de libertad y MAPE)."""
    r2 = float(r_squared)
    n = int(sample_size)
    k = int(independent_variables_count)
    mape = float(mean_absolute_percentage_error_pct)
    min_r2 = float(min_r_squared)
    max_mape = float(max_mape_pct)

    if (
        not (0.0 <= r2 <= 1.0)
        or n <= 0
        or k < 1
        or mape < 0.0
        or not (0.0 < min_r2 <= 1.0)
        or max_mape <= 0.0
    ):
        raise ValueError(
            "Parámetros de estimación paramétrica fuera de rango válido (R² en [0, 1], n > 0, k >= 1, MAPE >= 0)."
        )

    degrees_of_freedom = n - k - 1
    if degrees_of_freedom < 1:
        raise ValueError(
            f"Regresión paramétrica rechazada por muestra histórica insuficiente: grados de libertad ({degrees_of_freedom}) < 1."
        )

    if r2 < min_r2 or mape > max_mape:
        raise ValueError(
            f"Modelo rechazado por ajuste estadístico insuficiente: R²={r2:.4f} (mín {min_r2:.4f}) o MAPE={mape:.2f}% (máx {max_mape:.2f}%)."
        )

    if bool(extrapolation_beyond_historical_range) and not bool(
        scale_adjustment_documented
    ):
        raise ValueError(
            "La extrapolación fuera del rango histórico exige factor de ajuste de escala documentado."
        )

    adjusted_r_squared = round(
        1.0 - ((1.0 - r2) * (n - 1) / degrees_of_freedom), 4
    )

    return {
        "r_squared": round(r2, 4),
        "adjusted_r_squared": adjusted_r_squared,
        "degrees_of_freedom": int(degrees_of_freedom),
        "mean_absolute_percentage_error_pct": round(mape, 2),
        "extrapolation_beyond_historical_range": bool(
            extrapolation_beyond_historical_range
        ),
        "is_valid": True,
    }



def validate_schedule_compression_fast_tracking_and_crashing(
    original_duration_days: float,
    compressed_duration_days: float,
    fast_tracked_overlap_pct: float,
    crashing_added_cost: float,
    baseline_budget_bac: float,
    *,
    rework_risk_contingency_documented: bool = False,
    max_overlap_pct: float = 33.3,
    max_crashing_cost_ratio_pct: float = 15.0,
) -> dict[str, float | bool]:
    """Valida compresión de cronograma fast-tracking + crashing (PMBOK §6.5.2.6).

    ValueError en: original_duration_days <= 0; compressed fuera de
    (0, original]; fast_tracked_overlap_pct fuera de [0, 100] o por
    encima de max_overlap_pct (superposición excesiva); crashing_added_cost
    negativo; baseline_budget_bac <= 0; max_overlap_pct fuera de (0, 100];
    max_crashing_cost_ratio_pct <= 0; overlap > 0 sin contingencia de
    retrabajo documentada; crashing_cost_ratio_pct > max (sobrecosto
    desproporcionado); costo de crashing sin reducción efectiva de
    duración.
    """
    original = float(original_duration_days)
    compressed = float(compressed_duration_days)
    overlap_pct = float(fast_tracked_overlap_pct)
    crashing_cost = float(crashing_added_cost)
    bac = float(baseline_budget_bac)
    max_overlap = float(max_overlap_pct)
    max_crash_ratio = float(max_crashing_cost_ratio_pct)

    if original <= 0:
        raise ValueError("original_duration_days debe ser > 0")
    if compressed <= 0 or compressed > original:
        raise ValueError("compressed_duration_days debe estar en (0, original_duration_days]")
    if overlap_pct < 0.0 or overlap_pct > 100.0:
        raise ValueError("fast_tracked_overlap_pct debe estar en [0.0, 100.0]")
    if crashing_cost < 0.0:
        raise ValueError("crashing_added_cost debe ser >= 0.0")
    if bac <= 0:
        raise ValueError("baseline_budget_bac debe ser > 0")
    if max_overlap <= 0.0 or max_overlap > 100.0:
        raise ValueError("max_overlap_pct debe estar en (0.0, 100.0]")
    if max_crash_ratio <= 0.0:
        raise ValueError("max_crashing_cost_ratio_pct debe ser > 0.0")
    if overlap_pct > max_overlap:
        raise ValueError("fast_tracked_overlap_pct supera max_overlap_pct (superposicion excesiva de ruta critica)")
    if overlap_pct > 0.0 and not rework_risk_contingency_documented:
        raise ValueError("fast-tracking requiere contingencia de retrabajo documentada")
    crashing_cost_ratio_pct = round((crashing_cost / bac) * 100.0, 2)
    if crashing_cost_ratio_pct > max_crash_ratio:
        raise ValueError("crashing sobrepasa max_crashing_cost_ratio_pct (sobrecosto desproporcionado)")
    if compressed == original and crashing_cost > 0.0:
        raise ValueError("crashing_added_cost sin reduccion efectiva de duracion")

    duration_reduction_days = round(original - compressed, 2)
    compression_ratio_pct = round((duration_reduction_days / original) * 100.0, 2)
    crash_cost_per_day_saved = (
        round(crashing_cost / duration_reduction_days, 2) if duration_reduction_days > 0 else 0.0
    )

    return {
        "duration_reduction_days": duration_reduction_days,
        "compression_ratio_pct": compression_ratio_pct,
        "fast_tracked_overlap_pct": round(overlap_pct, 2),
        "crashing_cost_ratio_pct": crashing_cost_ratio_pct,
        "crash_cost_per_day_saved": crash_cost_per_day_saved,
        "is_valid": True,
    }


def validate_funding_limit_reconciliation_and_cash_flow_cliff(
    periodic_expenditures: list[float],
    periodic_funding_limits: list[float],
    *,
    min_liquidity_buffer_pct: float = 5.0,
    allow_fiscal_rescheduling_with_cr: bool = False,
    approved_rescheduling_cr_id: str | None = None,
) -> dict[str, Any]:
    """Valida conciliacion de limites de financiamiento y precipicio de flujo de caja (PMBOK §7.3, §7.4)."""
    if not isinstance(periodic_expenditures, list) or not isinstance(periodic_funding_limits, list):
        raise ValueError("periodic_expenditures y periodic_funding_limits deben ser listas")
    if len(periodic_expenditures) == 0:
        raise ValueError("periodic_expenditures no puede estar vacia")
    if len(periodic_expenditures) != len(periodic_funding_limits):
        raise ValueError(
            "periodic_expenditures y periodic_funding_limits deben tener la misma longitud"
        )

    exp_vals = [float(x) for x in periodic_expenditures]
    fund_vals = [float(x) for x in periodic_funding_limits]
    if any(x < 0.0 for x in exp_vals) or any(x < 0.0 for x in fund_vals):
        raise ValueError("Los gastos y limites de financiamiento por periodo deben ser >= 0.0")

    total_fund = sum(fund_vals)
    if total_fund <= 0.0:
        raise ValueError("La suma de periodic_funding_limits debe ser > 0.0")

    min_buf_threshold = float(min_liquidity_buffer_pct)
    if min_buf_threshold < 0.0 or min_buf_threshold >= 100.0:
        raise ValueError("min_liquidity_buffer_pct debe estar en [0.0, 100.0)")

    total_exp = sum(exp_vals)
    if total_exp > total_fund + 1e-6:
        raise ValueError(
            "El gasto planificado total excede el limite total de financiamiento disponible"
        )

    cum_exp = 0.0
    cum_fund = 0.0
    funding_breach_periods: list[int] = []
    min_period_buffer_pct: float | None = None

    for period_idx, (exp, fund) in enumerate(zip(exp_vals, fund_vals), start=1):
        cum_exp += exp
        cum_fund += fund
        if cum_exp > cum_fund + 1e-6:
            funding_breach_periods.append(period_idx)
        if cum_fund > 0.0:
            buffer_pct = ((cum_fund - cum_exp) / cum_fund) * 100.0
            if min_period_buffer_pct is None or buffer_pct < min_period_buffer_pct:
                min_period_buffer_pct = buffer_pct

    effective_min_buffer = min_period_buffer_pct if min_period_buffer_pct is not None else 0.0
    has_valid_rescheduling_cr = bool(allow_fiscal_rescheduling_with_cr) and bool(
        str(approved_rescheduling_cr_id or "").strip()
    )

    if (
        len(funding_breach_periods) > 0 or effective_min_buffer < min_buf_threshold
    ) and not has_valid_rescheduling_cr:
        raise ValueError(
            "Deficit de flujo de caja o colchon de liquidez insuficiente sin CR aprobado de reprogramacion fiscal (PMBOK §7.3.2.3)"
        )

    return {
        "periods_count": len(periodic_expenditures),
        "total_planned_expenditure": round(total_exp, 2),
        "total_funding_limit": round(total_fund, 2),
        "min_period_buffer_pct": round(effective_min_buffer, 2),
        "funding_breach_periods": funding_breach_periods,
        "is_valid": True,
    }


def validate_business_case_npv_irr_and_payback_hurdle(
    net_present_value_npv: float,
    internal_rate_of_return_irr_pct: float,
    discount_rate_wacc_pct: float,
    payback_period_months: float,
    max_allowed_payback_months: float,
    benefit_cost_ratio_bcr: float,
    *,
    is_mandatory_regulatory_compliance: bool = False,
) -> dict[str, Any]:
    """Valida indicadores financieros del Caso de Negocio (NPV, IRR vs WACC, BCR y Payback) segun PMI PMBOK §1.2 y §7.2."""
    npv = float(net_present_value_npv)
    irr = float(internal_rate_of_return_irr_pct)
    wacc = float(discount_rate_wacc_pct)
    payback = float(payback_period_months)
    max_payback = float(max_allowed_payback_months)
    bcr = float(benefit_cost_ratio_bcr)
    is_mandatory = bool(is_mandatory_regulatory_compliance)

    if wacc <= 0.0:
        raise ValueError("discount_rate_wacc_pct debe ser > 0.0")
    if payback <= 0.0:
        raise ValueError("payback_period_months debe ser > 0.0")
    if max_payback <= 0.0:
        raise ValueError("max_allowed_payback_months debe ser > 0.0")
    if bcr < 0.0:
        raise ValueError("benefit_cost_ratio_bcr debe ser >= 0.0")

    irr_spread_over_wacc_pct = round(irr - wacc, 2)

    if not is_mandatory:
        if npv < 0.0 or irr < wacc or bcr < 1.0 or payback > max_payback:
            raise ValueError(
                "El Caso de Negocio no supera la tasa de corte (hurdle rate) financiera PMI (NPV >= 0, IRR >= WACC, BCR >= 1.0 y payback <= max)"
            )

    return {
        "net_present_value_npv": round(npv, 2),
        "irr_spread_over_wacc_pct": irr_spread_over_wacc_pct,
        "benefit_cost_ratio_bcr": round(bcr, 4),
        "payback_period_months": round(payback, 2),
        "is_mandatory_regulatory_compliance": is_mandatory,
        "is_valid": True,
    }




def validate_monte_carlo_confidence_band_and_reserve_adequacy(
    simulations: list[dict],
    *,
    min_iterations: int = 1000,
    max_p90_to_p50_spread_ratio: float = 1.35,
) -> dict[str, object]:
    """Valida bandas de confianza Monte Carlo (P50/P80/P90) y reserva (PMBOK §11.4).

    Cada simulación aporta simulation_id, iterations, deterministic_base,
    p50_estimate, p80_estimate, p90_estimate y
    allocated_contingency_reserve:
    - non_monotonic_or_under_sampled: iterations < min_iterations o la
      banda no es monotónica 0 < base <= P50 <= P80 <= P90.
    - reserve_shortfall_at_p80: base determinista + reserva de
      contingencia no cubre el P80 oficial.
    - excessive_tail_uncertainty_spread: P90/P50 excede el ratio máximo
      (cuando P50 > 0).
    - simulation_governance_status: 'HEALTHY' sin hallazgos; 'CRITICAL'
      con muestreo/monotonicidad inválida o shortfall de reserva;
      'AT_RISK' en otro caso; violations con {simulation_id, reasons}.
    """
    if not isinstance(simulations, list):
        simulations = []
    rows = [s for s in simulations if isinstance(s, dict)]

    total_simulations = len(rows)
    compliant_simulations_count = 0
    non_monotonic_or_under_sampled_count = 0
    reserve_shortfall_at_p80_count = 0
    excessive_tail_uncertainty_spread_count = 0
    violations: list[dict] = []

    for idx, row in enumerate(rows, start=1):
        simulation_id = str(row.get("simulation_id", f"SIM-{idx}"))
        reasons: list[str] = []
        has_invalid_band = False
        has_shortfall = False
        has_wide_spread = False

        raw_iterations = row.get("iterations")
        try:
            iterations = int(raw_iterations if raw_iterations is not None else 0)
        except (TypeError, ValueError):
            iterations = 0
        raw_base = row.get("deterministic_base")
        try:
            base = float(raw_base if raw_base is not None else 0.0)
        except (TypeError, ValueError):
            base = 0.0

        def _safe_pct(key: str) -> float:
            raw = row.get(key)
            try:
                return float(raw if raw is not None else 0.0)
            except (TypeError, ValueError):
                return 0.0

        p50 = _safe_pct("p50_estimate")
        p80 = _safe_pct("p80_estimate")
        p90 = _safe_pct("p90_estimate")
        raw_reserve = row.get("allocated_contingency_reserve")
        try:
            reserve = float(raw_reserve if raw_reserve is not None else 0.0)
        except (TypeError, ValueError):
            reserve = 0.0

        is_monotonic = 0.0 < base <= p50 <= p80 <= p90
        if iterations < int(min_iterations) or not is_monotonic:
            has_invalid_band = True
            if iterations < int(min_iterations):
                reasons.append(
                    f"UNDER_SAMPLED ({iterations}<{min_iterations})",
                )
            if not is_monotonic:
                reasons.append(
                    "NON_MONOTONIC_BAND (debe cumplir 0 < base <= P50 <= P80 <= P90)",
                )

        if (base + reserve) < p80:
            has_shortfall = True
            reasons.append(
                f"RESERVE_SHORTFALL_AT_P80 ({base + reserve}<{p80})",
            )

        if p50 > 0 and (p90 / p50) > float(max_p90_to_p50_spread_ratio):
            has_wide_spread = True
            reasons.append(
                f"EXCESSIVE_TAIL_SPREAD (P90/P50={p90 / p50}>{max_p90_to_p50_spread_ratio})",
            )

        if has_invalid_band:
            non_monotonic_or_under_sampled_count += 1
        if has_shortfall:
            reserve_shortfall_at_p80_count += 1
        if has_wide_spread:
            excessive_tail_uncertainty_spread_count += 1
        if not (has_invalid_band or has_shortfall or has_wide_spread):
            compliant_simulations_count += 1
        if reasons:
            violations.append({"simulation_id": simulation_id, "reasons": reasons})

    simulation_governance_status = (
        "CRITICAL"
        if non_monotonic_or_under_sampled_count > 0 or reserve_shortfall_at_p80_count > 0
        else (
            "AT_RISK"
            if excessive_tail_uncertainty_spread_count > 0
            else "HEALTHY"
        )
    )

    return {
        "total_simulations": total_simulations,
        "compliant_simulations_count": compliant_simulations_count,
        "non_monotonic_or_under_sampled_count": non_monotonic_or_under_sampled_count,
        "reserve_shortfall_at_p80_count": reserve_shortfall_at_p80_count,
        "excessive_tail_uncertainty_spread_count": excessive_tail_uncertainty_spread_count,
        "simulation_governance_status": simulation_governance_status,
        "violations": violations,
    }


def validate_resource_leveling_and_smoothing_constraints(
    optimization_runs: Sequence[Mapping[str, Any]] | None,
    *,
    max_peak_to_average_ratio: float = 1.6,
    max_leveling_schedule_slip_pct: float = 15.0,
) -> dict[str, Any]:
    """Valida restricciones de suavizado (smoothing) frente a nivelación (leveling) de recursos y picos de utilización FTE (PMI PMBOK §6.5 y §9.6)."""
    if (
        optimization_runs is None
        or isinstance(optimization_runs, (str, bytes))
        or not isinstance(optimization_runs, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = optimization_runs

    try:
        max_pta_ratio = float(max_peak_to_average_ratio)
    except (TypeError, ValueError):
        max_pta_ratio = 1.6

    try:
        max_slip_pct = float(max_leveling_schedule_slip_pct)
    except (TypeError, ValueError):
        max_slip_pct = 15.0

    total_runs = 0
    compliant_runs = 0

    smoothing_violates_float_or_critical_path_ids: list[str] = []
    unapproved_or_excessive_leveling_slip_ids: list[str] = []
    unresolved_over_allocation_or_spike_ids: list[str] = []

    def _positive_float(val: Any) -> float:
        try:
            return max(0.0, float(val or 0.0))
        except (TypeError, ValueError):
            return 0.0

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_runs += 1

        run_id = (
            str(raw.get("id") or raw.get("run_id") or "").strip()
            or "OPT-UNKNOWN"
        )
        mode = str(raw.get("mode") or "").strip().lower()

        total_float_available_days = _positive_float(
            raw.get("total_float_available_days")
        )
        activity_delay_days = _positive_float(raw.get("activity_delay_days"))
        baseline_duration_days = _positive_float(
            raw.get("baseline_duration_days")
        )
        critical_path_extended_days = _positive_float(
            raw.get("critical_path_extended_days")
        )
        ccb_approved_slip = bool(raw.get("ccb_approved_slip"))
        peak_allocation_fte = _positive_float(raw.get("peak_allocation_fte"))
        average_allocation_fte = _positive_float(
            raw.get("average_allocation_fte")
        )
        capacity_ceiling_fte = _positive_float(raw.get("capacity_ceiling_fte"))

        smoothing_violation = mode == "smoothing" and (
            activity_delay_days > total_float_available_days
            or critical_path_extended_days > 0.0
        )
        leveling_slip_violation = (
            mode == "leveling"
            and critical_path_extended_days > 0.0
            and (
                (not ccb_approved_slip)
                or (
                    baseline_duration_days > 0.0
                    and (
                        critical_path_extended_days / baseline_duration_days
                    )
                    * 100.0
                    > max_slip_pct
                )
            )
        )
        over_allocation_or_spike = (
            capacity_ceiling_fte > 0.0
            and peak_allocation_fte > capacity_ceiling_fte
        ) or (
            average_allocation_fte > 0.0
            and (peak_allocation_fte / average_allocation_fte) > max_pta_ratio
        )

        if smoothing_violation:
            smoothing_violates_float_or_critical_path_ids.append(run_id)
        if leveling_slip_violation:
            unapproved_or_excessive_leveling_slip_ids.append(run_id)
        if over_allocation_or_spike:
            unresolved_over_allocation_or_spike_ids.append(run_id)

        if (
            not smoothing_violation
            and not leveling_slip_violation
            and not over_allocation_or_spike
        ):
            compliant_runs += 1

    is_valid = (
        len(smoothing_violates_float_or_critical_path_ids) == 0
        and len(unapproved_or_excessive_leveling_slip_ids) == 0
        and len(unresolved_over_allocation_or_spike_ids) == 0
    )

    if is_valid:
        optimization_governance_status = "HEALTHY"
    elif (
        len(smoothing_violates_float_or_critical_path_ids) > 0
        or len(unapproved_or_excessive_leveling_slip_ids) > 0
    ):
        optimization_governance_status = "CRITICAL"
    else:
        optimization_governance_status = "AT_RISK"

    recommendations: list[str] = []
    if smoothing_violates_float_or_critical_path_ids:
        recommendations.append(
            f"Restringir Resource Smoothing a la holgura disponible sin extender la ruta crítica en {smoothing_violates_float_or_critical_path_ids}."
        )
    if unapproved_or_excessive_leveling_slip_ids:
        recommendations.append(
            f"Tramitar aprobación CCB o acotar el deslizamiento de Resource Leveling (<= {max_slip_pct}%) en {unapproved_or_excessive_leveling_slip_ids}."
        )
    if unresolved_over_allocation_or_spike_ids:
        recommendations.append(
            f"Rebalancear sobreasignaciones FTE que exceden la capacidad o el ratio pico/promedio (> {max_pta_ratio}) en {unresolved_over_allocation_or_spike_ids}."
        )

    return {
        "total_runs": total_runs,
        "compliant_runs": compliant_runs,
        "smoothing_violates_float_or_critical_path_ids": smoothing_violates_float_or_critical_path_ids,
        "unapproved_or_excessive_leveling_slip_ids": unapproved_or_excessive_leveling_slip_ids,
        "unresolved_over_allocation_or_spike_ids": unresolved_over_allocation_or_spike_ids,
        "optimization_governance_status": optimization_governance_status,
        "is_valid": is_valid,
        "recommendations": recommendations,
    }


def validate_wbs_100_percent_rollup_and_8_80_granularity(
    wbs_nodes: Sequence[Mapping[str, Any]] | None,
    *,
    min_leaf_effort_hours: float = 8.0,
    max_leaf_effort_hours: float = 80.0,
    rollup_tolerance_pct: float = 0.5,
) -> dict[str, Any]:
    """Valida la Regla del 100% de descomposición en nodos padre de la EDT/WBS, la heurística de granularidad de 8/80 horas en paquetes de trabajo hoja y la asignación de responsable único (PMI PMBOK §5.4 y §6.2)."""
    if (
        wbs_nodes is None
        or isinstance(wbs_nodes, (str, bytes))
        or not isinstance(wbs_nodes, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = wbs_nodes

    try:
        min_leaf_hrs = float(min_leaf_effort_hours)
    except (TypeError, ValueError):
        min_leaf_hrs = 8.0

    try:
        max_leaf_hrs = float(max_leaf_effort_hours)
    except (TypeError, ValueError):
        max_leaf_hrs = 80.0

    try:
        tol_pct = float(rollup_tolerance_pct)
    except (TypeError, ValueError):
        tol_pct = 0.5

    def _pos_float(val: Any) -> float:
        try:
            return max(0.0, float(val or 0.0))
        except (TypeError, ValueError):
            return 0.0

    total_nodes = 0
    compliant_nodes = 0

    parent_100_pct_rollup_violation_ids: list[str] = []
    leaf_granularity_out_of_8_80_bounds_ids: list[str] = []
    unowned_work_package_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_nodes += 1

        node_id = (
            str(
                raw.get("id")
                or raw.get("node_id")
                or raw.get("wbs_code")
                or ""
            ).strip()
            or "WBS-UNKNOWN"
        )
        is_leaf = bool(raw.get("is_leaf"))
        planned_effort_hours = _pos_float(raw.get("planned_effort_hours"))
        children_effort_sum_hours = _pos_float(
            raw.get("children_effort_sum_hours")
        )

        raw_weight = raw.get("children_scope_weight_sum_pct")
        if raw_weight is None:
            children_scope_weight_sum_pct = 100.0
        else:
            try:
                children_scope_weight_sum_pct = float(raw_weight)
            except (TypeError, ValueError):
                children_scope_weight_sum_pct = 100.0

        single_owner_assigned = bool(raw.get("single_owner_assigned"))

        is_parent_violation = (not is_leaf) and (
            abs(children_scope_weight_sum_pct - 100.0) > tol_pct
            or (
                planned_effort_hours > 0.0
                and (
                    abs(planned_effort_hours - children_effort_sum_hours)
                    / planned_effort_hours
                )
                * 100.0
                > tol_pct
            )
        )
        is_granularity_violation = is_leaf and (
            planned_effort_hours < min_leaf_hrs
            or planned_effort_hours > max_leaf_hrs
        )
        is_unowned_violation = is_leaf and (not single_owner_assigned)

        if is_parent_violation:
            parent_100_pct_rollup_violation_ids.append(node_id)
        if is_granularity_violation:
            leaf_granularity_out_of_8_80_bounds_ids.append(node_id)
        if is_unowned_violation:
            unowned_work_package_ids.append(node_id)

        if (
            not is_parent_violation
            and not is_granularity_violation
            and not is_unowned_violation
        ):
            compliant_nodes += 1

    is_valid = (
        len(parent_100_pct_rollup_violation_ids) == 0
        and len(leaf_granularity_out_of_8_80_bounds_ids) == 0
        and len(unowned_work_package_ids) == 0
    )

    if is_valid:
        wbs_governance_status = "HEALTHY"
    elif (
        len(parent_100_pct_rollup_violation_ids) > 0
        or len(unowned_work_package_ids) > 0
    ):
        wbs_governance_status = "CRITICAL"
    else:
        wbs_governance_status = "AT_RISK"

    recommendations: list[str] = []
    if parent_100_pct_rollup_violation_ids:
        recommendations.append(
            f"Alinear el rollup de esfuerzo y pesos de los nodos hijos al 100% (tolerancia <= {tol_pct}%) en {parent_100_pct_rollup_violation_ids}."
        )
    if unowned_work_package_ids:
        recommendations.append(
            f"Asignar un único responsable (single_owner_assigned=True) a los paquetes de trabajo hoja en {unowned_work_package_ids}."
        )
    if leaf_granularity_out_of_8_80_bounds_ids:
        recommendations.append(
            f"Subdividir o consolidar paquetes de trabajo hoja para mantenerse dentro de la regla de [{min_leaf_hrs}, {max_leaf_hrs}] horas en {leaf_granularity_out_of_8_80_bounds_ids}."
        )

    return {
        "total_nodes": total_nodes,
        "compliant_nodes": compliant_nodes,
        "parent_100_pct_rollup_violation_ids": parent_100_pct_rollup_violation_ids,
        "leaf_granularity_out_of_8_80_bounds_ids": leaf_granularity_out_of_8_80_bounds_ids,
        "unowned_work_package_ids": unowned_work_package_ids,
        "wbs_governance_status": wbs_governance_status,
        "is_valid": is_valid,
        "recommendations": recommendations,
    }


def validate_make_or_buy_breakeven_and_tco(
    decisions: Sequence[Mapping[str, Any]] | None,
    *,
    max_unjustified_cost_premium_pct: float = 10.0,
) -> dict[str, Any]:
    """Valida análisis de decisiones Hacer vs Comprar (Make-or-Buy): Costo Total de Propiedad (TCO), protección de propiedad intelectual crítica con escrow y capacidad interna disponible (PMI PMBOK §12.1.2.3)."""
    if (
        decisions is None
        or isinstance(decisions, (str, bytes))
        or not isinstance(decisions, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = decisions

    try:
        max_prem_pct = float(max_unjustified_cost_premium_pct)
    except (TypeError, ValueError):
        max_prem_pct = 10.0

    def _pos_float(val: Any) -> float:
        try:
            return max(0.0, float(val or 0.0))
        except (TypeError, ValueError):
            return 0.0

    total_decisions = 0
    compliant_decisions = 0

    core_ip_outsourced_without_escrow_ids: list[str] = []
    make_selected_without_capacity_ids: list[str] = []
    unjustified_tco_premium_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_decisions += 1

        decision_id = (
            str(raw.get("id") or raw.get("decision_id") or "").strip()
            or "MOB-UNKNOWN"
        )
        selected_option = str(raw.get("selected_option") or "").strip().lower()

        make_initial_cost = _pos_float(raw.get("make_initial_cost"))
        make_recurring_cost = _pos_float(raw.get("make_recurring_cost"))
        buy_initial_cost = _pos_float(raw.get("buy_initial_cost"))
        buy_recurring_cost = _pos_float(raw.get("buy_recurring_cost"))

        try:
            horizon_periods = max(1, int(raw.get("horizon_periods") or 1))
        except (TypeError, ValueError):
            horizon_periods = 1

        is_core_proprietary_ip = bool(raw.get("is_core_proprietary_ip"))
        ip_protection_and_escrow_signed = bool(
            raw.get("ip_protection_and_escrow_signed")
        )
        internal_capacity_available = bool(
            raw.get("internal_capacity_available")
        )
        strategic_override_approved = bool(
            raw.get("strategic_override_approved")
        )

        make_tco = make_initial_cost + (make_recurring_cost * horizon_periods)
        buy_tco = buy_initial_cost + (buy_recurring_cost * horizon_periods)

        is_core_ip_violation = (
            selected_option == "buy"
            and is_core_proprietary_ip
            and not ip_protection_and_escrow_signed
        )
        is_capacity_violation = (
            selected_option == "make" and not internal_capacity_available
        )
        is_tco_premium_violation = (not strategic_override_approved) and (
            (
                selected_option == "make"
                and buy_tco > 0.0
                and ((make_tco - buy_tco) / buy_tco) * 100.0 > max_prem_pct
            )
            or (
                selected_option == "buy"
                and make_tco > 0.0
                and ((buy_tco - make_tco) / make_tco) * 100.0 > max_prem_pct
            )
        )

        if is_core_ip_violation:
            core_ip_outsourced_without_escrow_ids.append(decision_id)
        if is_capacity_violation:
            make_selected_without_capacity_ids.append(decision_id)
        if is_tco_premium_violation:
            unjustified_tco_premium_ids.append(decision_id)

        if (
            not is_core_ip_violation
            and not is_capacity_violation
            and not is_tco_premium_violation
        ):
            compliant_decisions += 1

    is_valid = (
        len(core_ip_outsourced_without_escrow_ids) == 0
        and len(make_selected_without_capacity_ids) == 0
        and len(unjustified_tco_premium_ids) == 0
    )

    if is_valid:
        mob_governance_status = "HEALTHY"
    elif (
        len(core_ip_outsourced_without_escrow_ids) > 0
        or len(make_selected_without_capacity_ids) > 0
    ):
        mob_governance_status = "CRITICAL"
    else:
        mob_governance_status = "AT_RISK"

    recommendations: list[str] = []
    if core_ip_outsourced_without_escrow_ids:
        recommendations.append(
            f"Exigir contrato de protección de propiedad intelectual y depósito de código en escrow antes de externalizar IP crítica en {core_ip_outsourced_without_escrow_ids}."
        )
    if make_selected_without_capacity_ids:
        recommendations.append(
            f"Verificar disponibilidad de capacidad interna o reevaluar alternativa de adquisición para decisiones 'make' en {make_selected_without_capacity_ids}."
        )
    if unjustified_tco_premium_ids:
        recommendations.append(
            f"Justificar estratégicamente (strategic_override_approved=True) o seleccionar la opción de menor TCO (sobrecosto > {max_prem_pct}%) en {unjustified_tco_premium_ids}."
        )

    return {
        "total_decisions": total_decisions,
        "compliant_decisions": compliant_decisions,
        "core_ip_outsourced_without_escrow_ids": core_ip_outsourced_without_escrow_ids,
        "make_selected_without_capacity_ids": make_selected_without_capacity_ids,
        "unjustified_tco_premium_ids": unjustified_tco_premium_ids,
        "mob_governance_status": mob_governance_status,
        "is_valid": is_valid,
        "recommendations": recommendations,
    }


def validate_risk_response_strategy_and_contingency_triggers(
    risk_responses: list[dict[str, Any]],
    *,
    require_fallback_for_high_residual: bool = True,
    high_residual_score_threshold: float = 12.0,
    require_early_warning_trigger: bool = True,
) -> dict[str, Any]:
    """Valida la alineación de estrategias de respuesta a riesgos (amenazas vs oportunidades), efectividad de reducción de riesgo residual y disparadores/planes de respaldo (PMI PMBOK §11.5)."""
    if (
        risk_responses is None
        or isinstance(risk_responses, (str, bytes))
        or not isinstance(risk_responses, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = risk_responses

    try:
        residual_threshold = float(high_residual_score_threshold)
    except (TypeError, ValueError):
        residual_threshold = 12.0

    threat_strategies = {"avoid", "transfer", "mitigate", "accept", "escalate"}
    opportunity_strategies = {
        "exploit",
        "share",
        "enhance",
        "accept",
        "escalate",
    }

    total_responses_evaluated = 0
    invalid_strategy_alignment_ids: list[str] = []
    ineffective_mitigation_ids: list[str] = []
    missing_trigger_ids: list[str] = []
    missing_fallback_ids: list[str] = []
    threat_reductions: list[float] = []
    issues: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_responses_evaluated += 1

        risk_id = (
            str(raw.get("risk_id") or raw.get("id") or "").strip()
            or f"RSK-{total_responses_evaluated}"
        )
        risk_type = str(raw.get("risk_type") or "threat").strip().lower()
        strategy = str(raw.get("strategy") or "").strip().lower()

        raw_pre = raw.get("pre_response_score")
        try:
            pre_response_score = float(raw_pre) if raw_pre is not None else 0.0
        except (TypeError, ValueError):
            pre_response_score = 0.0

        raw_res = raw.get("residual_score")
        try:
            residual_score = float(raw_res) if raw_res is not None else 0.0
        except (TypeError, ValueError):
            residual_score = 0.0

        early_warning_trigger = str(
            raw.get("early_warning_trigger") or ""
        ).strip()
        fallback_plan = str(raw.get("fallback_plan") or "").strip()
        action_owner_id = str(raw.get("action_owner_id") or "").strip()

        valid_for_type = (
            risk_type == "threat" and strategy in threat_strategies
        ) or (
            risk_type == "opportunity" and strategy in opportunity_strategies
        )

        if not valid_for_type or not action_owner_id:
            invalid_strategy_alignment_ids.append(risk_id)
            issues.append(
                f"Riesgo '{risk_id}' presenta estrategia inválida ('{strategy}' para '{risk_type}') o carece de action_owner_id."
            )

        if risk_type == "threat":
            if pre_response_score > 0.0:
                threat_reductions.append(
                    ((pre_response_score - residual_score) / pre_response_score)
                    * 100.0
                )
            if (
                strategy in {"avoid", "mitigate"}
                and residual_score >= pre_response_score
            ) or (strategy == "avoid" and residual_score > 0.0):
                ineffective_mitigation_ids.append(risk_id)
                issues.append(
                    f"Amenaza '{risk_id}' con estrategia '{strategy}' no reduce efectivamente el puntaje residual ({residual_score} vs {pre_response_score})."
                )

        if (
            bool(require_early_warning_trigger)
            and strategy != "accept"
            and not early_warning_trigger
        ):
            missing_trigger_ids.append(risk_id)
            issues.append(
                f"Riesgo '{risk_id}' con estrategia activa ('{strategy}') carece de disparador de alerta temprana (early_warning_trigger)."
            )

        if (
            bool(require_fallback_for_high_residual)
            and residual_score >= residual_threshold
            and not fallback_plan
        ):
            missing_fallback_ids.append(risk_id)
            issues.append(
                f"Riesgo '{risk_id}' con puntaje residual alto ({residual_score} >= {residual_threshold}) carece de plan de respaldo (fallback_plan)."
            )

    average_risk_reduction_pct = (
        round(sum(threat_reductions) / len(threat_reductions), 2)
        if threat_reductions
        else 0.0
    )

    if (
        len(invalid_strategy_alignment_ids) > 0
        or len(ineffective_mitigation_ids) > 0
    ):
        governance_status = "non_compliant"
    elif len(missing_trigger_ids) > 0 or len(missing_fallback_ids) > 0:
        governance_status = "needs_refinement"
    else:
        governance_status = "compliant"

    return {
        "is_valid": governance_status == "compliant",
        "total_responses_evaluated": total_responses_evaluated,
        "invalid_strategy_alignment_ids": invalid_strategy_alignment_ids,
        "ineffective_mitigation_ids": ineffective_mitigation_ids,
        "missing_trigger_ids": missing_trigger_ids,
        "missing_fallback_ids": missing_fallback_ids,
        "average_risk_reduction_pct": average_risk_reduction_pct,
        "governance_status": governance_status,
        "issues": issues,
    }


def validate_schedule_network_pdm_lead_lag_hygiene(
    dependencies: list[dict[str, Any]],
    *,
    max_lag_ratio_of_duration_pct: float = 50.0,
    allow_start_to_finish: bool = False,
    max_negative_lead_days: float = 5.0,
) -> dict[str, Any]:
    """Valida la higiene del Diagrama de Red por Precedencia (PDM): tipos de relación (FS/SS/FF/SF), límites de adelantos negativos (leads), retrasos positivos (lags) frente a la duración del sucesor y dominancia FS (PMI PMBOK §6.3)."""
    if (
        dependencies is None
        or isinstance(dependencies, (str, bytes))
        or not isinstance(dependencies, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = dependencies

    try:
        max_lag_ratio = float(max_lag_ratio_of_duration_pct)
    except (TypeError, ValueError):
        max_lag_ratio = 50.0

    try:
        max_neg_lead = float(max_negative_lead_days)
    except (TypeError, ValueError):
        max_neg_lead = 5.0

    valid_rel_types = {"FS", "SS", "FF", "SF"}

    total_dependencies = 0
    fs_count = 0
    invalid_relationship_ids: list[str] = []
    excessive_negative_lead_ids: list[str] = []
    excessive_positive_lag_ids: list[str] = []
    issues: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_dependencies += 1

        dep_id = (
            str(raw.get("dependency_id") or raw.get("id") or "").strip()
            or f"DEP-{total_dependencies}"
        )
        rel_type = str(raw.get("relationship_type") or "").strip().upper()

        raw_lag = raw.get("lag_days")
        try:
            lag_days = float(raw_lag) if raw_lag is not None else 0.0
        except (TypeError, ValueError):
            lag_days = 0.0

        raw_dur = raw.get("successor_duration_days")
        try:
            successor_duration_days = (
                float(raw_dur) if raw_dur is not None else 0.0
            )
        except (TypeError, ValueError):
            successor_duration_days = 0.0

        has_documented_justification = bool(
            raw.get("has_documented_justification")
        )

        if rel_type == "FS":
            fs_count += 1

        if rel_type not in valid_rel_types or (
            rel_type == "SF"
            and not bool(allow_start_to_finish)
            and not has_documented_justification
        ):
            invalid_relationship_ids.append(dep_id)
            issues.append(
                f"Dependencia '{dep_id}' utiliza relación inválida o SF no autorizada ('{rel_type}')."
            )

        if lag_days < 0.0 and (
            abs(lag_days) > max_neg_lead or not has_documented_justification
        ):
            excessive_negative_lead_ids.append(dep_id)
            issues.append(
                f"Dependencia '{dep_id}' presenta adelanto negativo (lead={lag_days}d) excesivo o sin justificación documentada."
            )

        if (
            lag_days > 0.0
            and successor_duration_days > 0.0
            and ((lag_days / successor_duration_days) * 100.0) > max_lag_ratio
        ):
            excessive_positive_lag_ids.append(dep_id)
            issues.append(
                f"Dependencia '{dep_id}' presenta espera positiva (lag={lag_days}d) que supera el {max_lag_ratio}% de la duración de la sucesora ({successor_duration_days}d)."
            )

    fs_dominant_ratio_pct = (
        round((fs_count / total_dependencies) * 100.0, 2)
        if total_dependencies > 0
        else 100.0
    )

    if total_dependencies > 0 and fs_dominant_ratio_pct < 80.0:
        issues.append(
            f"La proporción de relaciones Finish-to-Start ({fs_dominant_ratio_pct:.2f}%) es inferior al estándar recomendado (80.0%)."
        )

    if (
        len(invalid_relationship_ids) > 0
        or len(excessive_negative_lead_ids) > 0
    ):
        pdm_hygiene_status = "NON_COMPLIANT"
    elif len(excessive_positive_lag_ids) > 0 or (
        total_dependencies > 0 and fs_dominant_ratio_pct < 80.0
    ):
        pdm_hygiene_status = "NEEDS_REFINEMENT"
    else:
        pdm_hygiene_status = "COMPLIANT"

    return {
        "is_valid": pdm_hygiene_status == "COMPLIANT",
        "total_dependencies": total_dependencies,
        "invalid_relationship_ids": invalid_relationship_ids,
        "excessive_negative_lead_ids": excessive_negative_lead_ids,
        "excessive_positive_lag_ids": excessive_positive_lag_ids,
        "fs_dominant_ratio_pct": fs_dominant_ratio_pct,
        "pdm_hygiene_status": pdm_hygiene_status,
        "issues": issues,
    }






def validate_requirements_traceability_bidirectional_coverage(
    requirements: list[dict[str, Any]] | None,
    *,
    min_traceability_coverage_pct: float = 95.0,
    require_test_case_for_mandatory: bool = True,
) -> dict[str, Any]:
    """PMBOK 5.2 — Requirements Traceability Matrix (RTM) bidireccional.

    Validator puro sobre ``requirements``. Entradas no-lista/None se tratan
    como lista vacía y elementos no-dict se ignoran. Reglas evaluadas sobre
    requisitos ACTIVOS (``is_deferred_or_descoped`` falsy):

    1. ``backward_untraced_requirement_ids``: ``business_objective_id``
       vacío/None.
    2. ``forward_untraced_wbs_requirement_ids``: ``wbs_deliverable_id``
       vacío/None.
    3. ``unverified_test_requirement_ids``: ``verification_test_case_id``
       vacío/None AND ``require_test_case_for_mandatory`` AND
       ``str(priority_class).strip().lower() == 'mandatory'``.
    4. ``fully_traced_count``: activos con los 3 IDs presentes.
    5. ``traceability_coverage_pct``: round(fully_traced / active * 100, 2)
       (100.0 si no hay activos).
    6. ``rtm_governance_status``: TRACEABILITY_GAP si hay unverified o
       forward-untraced; PARTIAL_COVERAGE si hay backward-untraced o
       cobertura < mínima; FULLY_TRACED en otro caso.
    ``is_valid`` = status == 'FULLY_TRACED'.
    """
    def _text(value: Any) -> str:
        if value is None or isinstance(value, bool):
            return ""
        if isinstance(value, str):
            return value.strip()
        return ""

    raw_items = requirements if isinstance(requirements, list) else []
    items = [entry for entry in raw_items if isinstance(entry, Mapping)]

    active = [entry for entry in items if entry.get("is_deferred_or_descoped") is not True]
    active_count = len(active)

    backward_untraced_requirement_ids: list[str] = []
    forward_untraced_wbs_requirement_ids: list[str] = []
    unverified_test_requirement_ids: list[str] = []
    fully_traced_count = 0

    for entry in active:
        requirement_id = entry.get("requirement_id")
        objective_id = _text(entry.get("business_objective_id"))
        wbs_id = _text(entry.get("wbs_deliverable_id"))
        test_case_id = _text(entry.get("verification_test_case_id"))
        priority_class = _text(entry.get("priority_class")).lower()

        missing_objective = not objective_id
        missing_wbs = not wbs_id
        missing_test = not test_case_id

        if missing_objective:
            backward_untraced_requirement_ids.append(requirement_id)
        if missing_wbs:
            forward_untraced_wbs_requirement_ids.append(requirement_id)
        if missing_test and require_test_case_for_mandatory and priority_class == "mandatory":
            unverified_test_requirement_ids.append(requirement_id)

        if not missing_objective and not missing_wbs and not missing_test:
            fully_traced_count += 1

    traceability_coverage_pct = (
        round((fully_traced_count / active_count) * 100.0, 2) if active_count > 0 else 100.0
    )

    if unverified_test_requirement_ids or forward_untraced_wbs_requirement_ids:
        rtm_governance_status = "TRACEABILITY_GAP"
    elif backward_untraced_requirement_ids or traceability_coverage_pct < min_traceability_coverage_pct:
        rtm_governance_status = "PARTIAL_COVERAGE"
    else:
        rtm_governance_status = "FULLY_TRACED"

    return {
        "active_requirements_count": active_count,
        "fully_traced_count": fully_traced_count,
        "traceability_coverage_pct": traceability_coverage_pct,
        "backward_untraced_requirement_ids": backward_untraced_requirement_ids,
        "forward_untraced_wbs_requirement_ids": forward_untraced_wbs_requirement_ids,
        "unverified_test_requirement_ids": unverified_test_requirement_ids,
        "rtm_governance_status": rtm_governance_status,
        "is_valid": rtm_governance_status == "FULLY_TRACED",
    }


def validate_three_point_pert_and_triangular_estimates(
    estimates: list[dict[str, Any]],
    *,
    max_uncertainty_ratio: float = 3.0,
    max_cv_coefficient_of_variation_pct: float = 35.0,
) -> dict[str, Any]:
    """Valida estimaciones por tres valores PERT (Beta) y Triangular (PMI PMBOK §6.4 / §7.2)."""
    if not isinstance(estimates, list):
        return {
            "is_valid": True,
            "total_estimates": 0,
            "inverted_ordering_wp_ids": [],
            "excessive_spread_wp_ids": [],
            "total_pert_expected": 0.0,
            "portfolio_combined_std_dev": 0.0,
            "estimation_governance_status": "CALIBRATED",
            "issues": [],
        }

    max_ratio = float(
        max_uncertainty_ratio if max_uncertainty_ratio is not None else 3.0
    )
    max_cv_pct = float(
        max_cv_coefficient_of_variation_pct
        if max_cv_coefficient_of_variation_pct is not None
        else 35.0
    )

    total_estimates = 0
    inverted_ordering_wp_ids: list[str] = []
    excessive_spread_wp_ids: list[str] = []
    issues: list[str] = []

    expected_sum = 0.0
    variance_sum = 0.0

    for idx, item in enumerate(estimates):
        if not isinstance(item, dict):
            continue
        total_estimates += 1
        wp_id = str(item.get("work_package_id") or f"WP-{idx + 1}").strip()
        o_val = float(item.get("optimistic_o") or 0.0)
        m_val = float(item.get("most_likely_m") or 0.0)
        p_val = float(item.get("pessimistic_p") or 0.0)
        dist = str(item.get("distribution") or "beta").strip().lower()

        if not (0.0 < o_val <= m_val <= p_val):
            inverted_ordering_wp_ids.append(wp_id)
            issues.append(
                f"Paquete '{wp_id}' incumple el orden 0 < O <= M <= P (O={o_val}, M={m_val}, P={p_val})."
            )
            continue

        if dist == "triangular":
            expected = (o_val + m_val + p_val) / 3.0
            radicand = max(
                0.0,
                o_val**2
                + m_val**2
                + p_val**2
                - o_val * m_val
                - o_val * p_val
                - m_val * p_val,
            )
            std_dev = (radicand / 18.0) ** 0.5
        else:
            expected = (o_val + 4.0 * m_val + p_val) / 6.0
            std_dev = (p_val - o_val) / 6.0

        expected_sum += expected
        variance_sum += std_dev**2

        ratio_po = p_val / o_val
        cv_pct = (std_dev / expected) * 100.0 if expected > 0.0 else 0.0
        if ratio_po > max_ratio or cv_pct > max_cv_pct:
            excessive_spread_wp_ids.append(wp_id)
            issues.append(
                f"Paquete '{wp_id}' presenta dispersión excesiva (P/O={ratio_po:.2f}, CV={cv_pct:.2f}%)."
            )

    total_pert_expected = round(expected_sum, 2)
    portfolio_combined_std_dev = round(variance_sum**0.5, 2)

    if len(inverted_ordering_wp_ids) > 0:
        estimation_governance_status = "INVALID_BOUNDS"
    elif len(excessive_spread_wp_ids) > 0:
        estimation_governance_status = "HIGH_UNCERTAINTY_CONE"
    else:
        estimation_governance_status = "CALIBRATED"

    return {
        "is_valid": estimation_governance_status == "CALIBRATED",
        "total_estimates": total_estimates,
        "inverted_ordering_wp_ids": inverted_ordering_wp_ids,
        "excessive_spread_wp_ids": excessive_spread_wp_ids,
        "total_pert_expected": total_pert_expected,
        "portfolio_combined_std_dev": portfolio_combined_std_dev,
        "estimation_governance_status": estimation_governance_status,
        "issues": issues,
    }


def validate_ccpm_critical_chain_buffer_fever_chart(
    chains: list[dict[str, Any]],
    *,
    green_to_yellow_base_pct: float = 20.0,
    green_to_yellow_slope: float = 0.6,
    yellow_to_red_base_pct: float = 40.0,
    yellow_to_red_slope: float = 0.6,
) -> dict[str, Any]:
    """Valida consumo de buffers CCPM en Fever Chart (Project y Feeding Buffers — PMI PMBOK §6.5.2.3)."""
    if not isinstance(chains, list):
        return {
            "is_valid": True,
            "total_chains": 0,
            "red_zone_action_chain_ids": [],
            "yellow_zone_watch_chain_ids": [],
            "green_zone_healthy_chain_ids": [],
            "fever_chart_status": "GREEN_PROTECTED",
            "issues": [],
        }

    gy_base = float(
        green_to_yellow_base_pct if green_to_yellow_base_pct is not None else 20.0
    )
    gy_slope = float(
        green_to_yellow_slope if green_to_yellow_slope is not None else 0.6
    )
    yr_base = float(
        yellow_to_red_base_pct if yellow_to_red_base_pct is not None else 40.0
    )
    yr_slope = float(
        yellow_to_red_slope if yellow_to_red_slope is not None else 0.6
    )

    total_chains = 0
    red_zone_action_chain_ids: list[str] = []
    yellow_zone_watch_chain_ids: list[str] = []
    green_zone_healthy_chain_ids: list[str] = []
    issues: list[str] = []

    for idx, item in enumerate(chains):
        if not isinstance(item, dict):
            continue
        total_chains += 1
        chain_id = str(item.get("chain_id") or f"CHAIN-{idx + 1}").strip()
        completion_pct = float(item.get("chain_completion_pct") or 0.0)
        consumed_pct = float(item.get("buffer_consumed_pct") or 0.0)

        yellow_threshold = gy_base + (gy_slope * completion_pct)
        red_threshold = yr_base + (yr_slope * completion_pct)

        if consumed_pct > red_threshold or consumed_pct > 100.0:
            red_zone_action_chain_ids.append(chain_id)
            issues.append(
                f"Cadena '{chain_id}' en zona ROJA del Fever Chart (buffer consumido={consumed_pct:.2f}% > umbral rojo={red_threshold:.2f}%)."
            )
        elif yellow_threshold < consumed_pct <= red_threshold and consumed_pct <= 100.0:
            yellow_zone_watch_chain_ids.append(chain_id)
            issues.append(
                f"Cadena '{chain_id}' en zona AMARILLA del Fever Chart (buffer consumido={consumed_pct:.2f}% > umbral amarillo={yellow_threshold:.2f}%)."
            )
        else:
            green_zone_healthy_chain_ids.append(chain_id)

    if len(red_zone_action_chain_ids) > 0:
        fever_chart_status = "RED_RECOVERY_REQUIRED"
    elif len(yellow_zone_watch_chain_ids) > 0:
        fever_chart_status = "YELLOW_PLAN_RECOVERY"
    else:
        fever_chart_status = "GREEN_PROTECTED"

    return {
        "is_valid": fever_chart_status == "GREEN_PROTECTED",
        "total_chains": total_chains,
        "red_zone_action_chain_ids": red_zone_action_chain_ids,
        "yellow_zone_watch_chain_ids": yellow_zone_watch_chain_ids,
        "green_zone_healthy_chain_ids": green_zone_healthy_chain_ids,
        "fever_chart_status": fever_chart_status,
        "issues": issues,
    }




def validate_raci_responsibility_assignment_matrix_hygiene(
    deliverables_matrix: Any,
    *,
    max_responsible_per_deliverable: int = 3,
    max_consulted_per_deliverable: int = 4,
) -> Dict[str, object]:
    """Validador PMBOK 9.1.2.2 RACI / RAM para la matriz de asignación.

    Aplica la regla PMI de un único Accountable por entregable, cobertura
    de al menos un Responsible y límites de sobrecarga en R (responsible)
    y C (consulted). Determinista: entradas no-lista/no-dict se ignoran.
    """
    entries = deliverables_matrix if isinstance(deliverables_matrix, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    zero_accountable_deliverable_ids: List[str] = []
    multiple_accountable_deliverable_ids: List[str] = []
    zero_responsible_deliverable_ids: List[str] = []
    overloaded_responsible_deliverable_ids: List[str] = []
    consultation_bottleneck_deliverable_ids: List[str] = []

    for row in rows:
        deliverable_id = row.get("deliverable_id")
        accountable_ids = row.get("accountable_ids")
        responsible_ids = row.get("responsible_ids")
        consulted_ids = row.get("consulted_ids")

        accountable_count = len(accountable_ids) if isinstance(accountable_ids, list) else 0
        responsible_count = len(responsible_ids) if isinstance(responsible_ids, list) else 0
        consulted_count = len(consulted_ids) if isinstance(consulted_ids, list) else 0

        if accountable_count == 0:
            zero_accountable_deliverable_ids.append(deliverable_id)
        elif accountable_count > 1:
            multiple_accountable_deliverable_ids.append(deliverable_id)

        if responsible_count == 0:
            zero_responsible_deliverable_ids.append(deliverable_id)

        if responsible_count > max_responsible_per_deliverable:
            overloaded_responsible_deliverable_ids.append(deliverable_id)

        if consulted_count > max_consulted_per_deliverable:
            consultation_bottleneck_deliverable_ids.append(deliverable_id)

    total_deliverables = len(rows)

    if (
        zero_accountable_deliverable_ids
        or multiple_accountable_deliverable_ids
        or zero_responsible_deliverable_ids
    ):
        raci_governance_status = "NON_COMPLIANT"
    elif overloaded_responsible_deliverable_ids or consultation_bottleneck_deliverable_ids:
        raci_governance_status = "WARNING"
    else:
        raci_governance_status = "COMPLIANT"

    recommendations: List[str] = []
    if zero_accountable_deliverable_ids:
        recommendations.append(
            "Assign a single accountable owner to deliverables: "
            + ", ".join(zero_accountable_deliverable_ids)
        )
    if multiple_accountable_deliverable_ids:
        recommendations.append(
            "Keep exactly one accountable owner per deliverable (PMI single-A rule): "
            + ", ".join(multiple_accountable_deliverable_ids)
        )
    if zero_responsible_deliverable_ids:
        recommendations.append(
            "Assign at least one responsible role to deliverables: "
            + ", ".join(zero_responsible_deliverable_ids)
        )
    if overloaded_responsible_deliverable_ids:
        recommendations.append(
            f"Rebalance responsible assignments exceeding {max_responsible_per_deliverable} per deliverable: "
            + ", ".join(overloaded_responsible_deliverable_ids)
        )
    if consultation_bottleneck_deliverable_ids:
        recommendations.append(
            f"Trim consultation lists exceeding {max_consulted_per_deliverable} per deliverable: "
            + ", ".join(consultation_bottleneck_deliverable_ids)
        )

    return {
        "total_deliverables": total_deliverables,
        "zero_accountable_deliverable_ids": zero_accountable_deliverable_ids,
        "multiple_accountable_deliverable_ids": multiple_accountable_deliverable_ids,
        "zero_responsible_deliverable_ids": zero_responsible_deliverable_ids,
        "overloaded_responsible_deliverable_ids": overloaded_responsible_deliverable_ids,
        "consultation_bottleneck_deliverable_ids": consultation_bottleneck_deliverable_ids,
        "raci_governance_status": raci_governance_status,
        "is_raci_valid": raci_governance_status == "COMPLIANT",
        "recommendations": recommendations,
    }


def validate_monte_carlo_confidence_percentiles_and_contingency(
    simulations: Any,
    *,
    min_iterations: int = 1000,
    target_confidence_level: str = "P80",
    max_reserve_shortfall_pct: float = 5.0,
) -> Dict[str, object]:
    """PMBOK 11.4.2.2 — análisis cuantitativo Monte Carlo: percentiles P50/P80/P90 y contingencia."""
    entries = simulations if isinstance(simulations, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    min_iter = max(1, int(min_iterations or 1000))
    target_level = str(target_confidence_level or "P80").strip().upper()
    max_shortfall = max(0.0, float(max_reserve_shortfall_pct or 0.0))

    insufficient_iterations_ids: List[str] = []
    non_monotonic_percentile_ids: List[str] = []
    optimistic_bias_ids: List[str] = []
    underfunded_contingency_ids: List[str] = []
    recommendations: List[str] = []

    for idx, row in enumerate(rows, start=1):
        sim_id = (
            str(row.get("simulation_id") or row.get("id") or f"MC-{idx}").strip()
            or f"MC-{idx}"
        )
        iterations_count = int(row.get("iterations_count") or 0)
        baseline = float(row.get("deterministic_baseline") or 0.0)
        p50 = float(row.get("p50_estimate") or 0.0)
        p80 = float(row.get("p80_estimate") or 0.0)
        p90 = float(row.get("p90_estimate") or 0.0)
        allocated_reserve = max(
            0.0, float(row.get("allocated_contingency_reserve") or 0.0)
        )

        if iterations_count < min_iter:
            insufficient_iterations_ids.append(sim_id)
            recommendations.append(
                f"Incrementar iteraciones de simulación '{sim_id}' ({iterations_count} < {min_iter}) para estabilizar la convergencia de percentiles."
            )

        if not (0.0 < p50 <= p80 <= p90):
            non_monotonic_percentile_ids.append(sim_id)
            recommendations.append(
                f"Corregir percentiles no monótonos en simulación '{sim_id}' (P50={p50:.2f}, P80={p80:.2f}, P90={p90:.2f})."
            )

        if baseline < p50:
            optimistic_bias_ids.append(sim_id)
            recommendations.append(
                f"Revisar sesgo optimista en línea base determinista de '{sim_id}' ({baseline:.2f} < P50={p50:.2f})."
            )

        if target_level == "P90":
            target_p_estimate = p90
        elif target_level == "P50":
            target_p_estimate = p50
        else:
            target_p_estimate = p80

        required_contingency = max(0.0, target_p_estimate - baseline)
        if required_contingency > 0.0:
            shortfall_pct = (
                (required_contingency - allocated_reserve) / required_contingency
            ) * 100.0
            if shortfall_pct > max_shortfall:
                underfunded_contingency_ids.append(sim_id)
                recommendations.append(
                    f"Incrementar reserva de contingencia en '{sim_id}' para cubrir nivel {target_level} (déficit del {shortfall_pct:.2f}% > {max_shortfall:.2f}%)."
                )

    if non_monotonic_percentile_ids or underfunded_contingency_ids:
        monte_carlo_governance_status = "INVALID"
    elif insufficient_iterations_ids or optimistic_bias_ids:
        monte_carlo_governance_status = "WARNING"
    else:
        monte_carlo_governance_status = "VALID"

    return {
        "total_simulations": len(rows),
        "insufficient_iterations_ids": insufficient_iterations_ids,
        "non_monotonic_percentile_ids": non_monotonic_percentile_ids,
        "optimistic_bias_ids": optimistic_bias_ids,
        "underfunded_contingency_ids": underfunded_contingency_ids,
        "monte_carlo_governance_status": monte_carlo_governance_status,
        "is_monte_carlo_valid": monte_carlo_governance_status == "VALID",
        "recommendations": recommendations,
    }


def validate_make_or_buy_tco_and_strategic_lock_in(
    options: list[dict[str, Any]],
    *,
    evaluation_horizon_months: int = 36,
    max_switching_cost_ratio_pct: float = 35.0,
) -> dict[str, Any]:
    """Validate PMI PMBOK §12.1.2.3 Make-or-Buy Total Cost of Ownership (TCO), break-even horizon, and vendor lock-in."""
    core_ip_outsourced_component_ids: list[str] = []
    uneconomic_decision_component_ids: list[str] = []
    vendor_lock_in_risk_component_ids: list[str] = []
    recommendations: list[str] = []

    valid_options = (
        [
            o
            for o in options
            if isinstance(o, dict) and str(o.get("component_id", "")).strip()
        ]
        if isinstance(options, list)
        else []
    )

    total_selected_tco = 0.0

    for opt in valid_options:
        component_id = str(opt.get("component_id", "")).strip()
        selected_decision = str(opt.get("selected_decision", "MAKE")).strip().upper()
        make_upfront_cost = float(opt.get("make_upfront_cost", 0.0) or 0.0)
        make_monthly_opex = float(opt.get("make_monthly_opex", 0.0) or 0.0)
        buy_upfront_cost = float(opt.get("buy_upfront_cost", 0.0) or 0.0)
        buy_monthly_license_cost = float(
            opt.get("buy_monthly_license_cost", 0.0) or 0.0
        )
        buy_switching_exit_cost = float(
            opt.get("buy_switching_exit_cost", 0.0) or 0.0
        )
        is_core_ip = bool(opt.get("is_core_intellectual_property", False))

        make_tco = round(
            make_upfront_cost + make_monthly_opex * evaluation_horizon_months, 2
        )
        buy_tco = round(
            buy_upfront_cost + buy_monthly_license_cost * evaluation_horizon_months, 2
        )
        switching_cost_ratio_pct = (
            round((buy_switching_exit_cost / buy_tco) * 100.0, 2)
            if buy_tco > 0.0
            else 0.0
        )

        if selected_decision == "BUY":
            total_selected_tco += buy_tco
        else:
            total_selected_tco += make_tco

        if selected_decision == "BUY" and is_core_ip:
            core_ip_outsourced_component_ids.append(component_id)

        if (selected_decision == "BUY" and buy_tco > make_tco * 1.15) or (
            selected_decision == "MAKE"
            and make_tco > buy_tco * 1.15
            and not is_core_ip
        ):
            uneconomic_decision_component_ids.append(component_id)

        if (
            selected_decision == "BUY"
            and switching_cost_ratio_pct > max_switching_cost_ratio_pct
        ):
            vendor_lock_in_risk_component_ids.append(component_id)

    total_selected_tco = round(total_selected_tco, 2)

    if core_ip_outsourced_component_ids:
        recommendations.append(
            f"Retain in-house development (MAKE) for core intellectual property components: {', '.join(core_ip_outsourced_component_ids)}."
        )
    if uneconomic_decision_component_ids:
        recommendations.append(
            f"Re-evaluate Make-or-Buy decision exceeding >15% TCO parity over {evaluation_horizon_months}m horizon for: {', '.join(uneconomic_decision_component_ids)}."
        )
    if vendor_lock_in_risk_component_ids:
        recommendations.append(
            f"Mitigate vendor lock-in via open standards or exit escrow on components with switching cost >{max_switching_cost_ratio_pct:.1f}%: {', '.join(vendor_lock_in_risk_component_ids)}."
        )

    if (
        core_ip_outsourced_component_ids
        or len(uneconomic_decision_component_ids) >= 2
    ):
        make_or_buy_governance_status = "CRITICAL"
    elif uneconomic_decision_component_ids or vendor_lock_in_risk_component_ids:
        make_or_buy_governance_status = "WARNING"
    else:
        make_or_buy_governance_status = "SOUND"

    return {
        "total_components": len(valid_options),
        "total_selected_tco": total_selected_tco,
        "core_ip_outsourced_component_ids": core_ip_outsourced_component_ids,
        "uneconomic_decision_component_ids": uneconomic_decision_component_ids,
        "vendor_lock_in_risk_component_ids": vendor_lock_in_risk_component_ids,
        "make_or_buy_governance_status": make_or_buy_governance_status,
        "is_make_or_buy_valid": make_or_buy_governance_status == "SOUND",
        "recommendations": recommendations,
    }


def validate_resource_calendar_timezone_overlap_and_allocation(
    team_members: list[dict[str, Any]],
    *,
    min_core_overlap_hours: float = 3.0,
    max_concurrent_projects_per_member: int = 2,
) -> dict[str, Any]:
    """Validate PMI PMBOK §9.2 & §6.4 multi-timezone synchronous overlap, holiday conflicts, and context-switching allocation."""
    overallocated_member_ids: list[str] = []
    context_switching_fragmented_member_ids: list[str] = []
    holiday_conflict_member_ids: list[str] = []
    recommendations: list[str] = []

    valid_members = (
        [
            m
            for m in team_members
            if isinstance(m, dict) and str(m.get("member_id", "")).strip()
        ]
        if isinstance(team_members, list)
        else []
    )

    if not valid_members:
        return {
            "total_members": 0,
            "team_synchronous_overlap_hours": 8.0,
            "insufficient_timezone_overlap": False,
            "overallocated_member_ids": [],
            "context_switching_fragmented_member_ids": [],
            "holiday_conflict_member_ids": [],
            "calendar_governance_status": "ALIGNED",
            "is_calendar_valid": True,
            "recommendations": [],
        }

    start_hours: list[float] = []
    end_hours: list[float] = []

    for member in valid_members:
        member_id = str(member.get("member_id", "")).strip()
        utc_start = float(member.get("utc_work_start_hour", 9.0) or 0.0)
        utc_end = float(member.get("utc_work_end_hour", 17.0) or 0.0)
        total_allocation_pct = float(
            member.get("total_allocation_pct", 100.0) or 0.0
        )
        concurrent_projects_count = int(
            member.get("concurrent_projects_count", 1) or 1
        )
        unmitigated_holiday_conflict_days = int(
            member.get("unmitigated_holiday_conflict_days", 0) or 0
        )

        start_hours.append(utc_start)
        end_hours.append(utc_end)

        if total_allocation_pct > 100.0:
            overallocated_member_ids.append(member_id)

        if concurrent_projects_count > max_concurrent_projects_per_member:
            context_switching_fragmented_member_ids.append(member_id)

        if unmitigated_holiday_conflict_days > 0:
            holiday_conflict_member_ids.append(member_id)

    overlap_start = max(start_hours)
    overlap_end = min(end_hours)
    team_synchronous_overlap_hours = round(
        max(0.0, overlap_end - overlap_start), 2
    )
    insufficient_timezone_overlap = bool(
        len(valid_members) >= 2
        and team_synchronous_overlap_hours < min_core_overlap_hours
    )

    if overallocated_member_ids:
        recommendations.append(
            f"Level resource calendars to eliminate >100% overallocation on members: {', '.join(overallocated_member_ids)}."
        )
    if insufficient_timezone_overlap:
        recommendations.append(
            f"Establish a minimum {min_core_overlap_hours:.1f}h synchronous UTC collaboration window (currently {team_synchronous_overlap_hours:.2f}h)."
        )
    if context_switching_fragmented_member_ids:
        recommendations.append(
            f"Reduce concurrent project assignments (<={max_concurrent_projects_per_member}) to prevent context-switching loss for: {', '.join(context_switching_fragmented_member_ids)}."
        )
    if holiday_conflict_member_ids:
        recommendations.append(
            f"Adjust sprint capacity or coverage handoffs for unmitigated regional holiday conflicts: {', '.join(holiday_conflict_member_ids)}."
        )

    if overallocated_member_ids or (
        insufficient_timezone_overlap and team_synchronous_overlap_hours == 0.0
    ):
        calendar_governance_status = "CRITICAL"
    elif (
        insufficient_timezone_overlap
        or context_switching_fragmented_member_ids
        or holiday_conflict_member_ids
    ):
        calendar_governance_status = "WARNING"
    else:
        calendar_governance_status = "ALIGNED"

    return {
        "total_members": len(valid_members),
        "team_synchronous_overlap_hours": team_synchronous_overlap_hours,
        "insufficient_timezone_overlap": insufficient_timezone_overlap,
        "overallocated_member_ids": overallocated_member_ids,
        "context_switching_fragmented_member_ids": context_switching_fragmented_member_ids,
        "holiday_conflict_member_ids": holiday_conflict_member_ids,
        "calendar_governance_status": calendar_governance_status,
        "is_calendar_valid": calendar_governance_status == "ALIGNED",
        "recommendations": recommendations,
    }


def validate_wbs_work_package_8_80_granularity_and_dictionary(
    work_packages: list[dict[str, Any]],
    *,
    min_effort_hours: float = 8.0,
    max_effort_hours: float = 80.0,
    max_wbs_depth_level: int = 6,
) -> dict[str, Any]:
    """Validate PMI PMBOK §5.4 & §6.5 WBS work package 8/80-hour decomposition granularity and WBS dictionary completeness."""
    micromanaged_wp_ids: list[str] = []
    oversized_wp_ids: list[str] = []
    excessive_depth_wp_ids: list[str] = []
    incomplete_dictionary_wp_ids: list[str] = []
    recommendations: list[str] = []

    valid_wps = (
        [
            wp
            for wp in work_packages
            if isinstance(wp, dict) and str(wp.get("wp_id", "")).strip()
        ]
        if isinstance(work_packages, list)
        else []
    )

    for wp in valid_wps:
        wp_id = str(wp.get("wp_id", "")).strip()
        is_leaf_package = (
            bool(wp.get("is_leaf_package", True))
            if wp.get("is_leaf_package") is not None
            else True
        )
        estimated_effort_hours = float(
            wp.get("estimated_effort_hours", 0.0) or 0.0
        )
        wbs_level = int(wp.get("wbs_level", 1) or 1)
        has_acceptance_criteria = (
            bool(wp.get("has_acceptance_criteria", True))
            if wp.get("has_acceptance_criteria") is not None
            else True
        )
        has_assigned_control_account = (
            bool(wp.get("has_assigned_control_account", True))
            if wp.get("has_assigned_control_account") is not None
            else True
        )
        deliverable_noun_phrase_valid = (
            bool(wp.get("deliverable_noun_phrase_valid", True))
            if wp.get("deliverable_noun_phrase_valid") is not None
            else True
        )

        if wbs_level > max_wbs_depth_level:
            excessive_depth_wp_ids.append(wp_id)

        if is_leaf_package:
            if estimated_effort_hours < min_effort_hours:
                micromanaged_wp_ids.append(wp_id)
            elif estimated_effort_hours > max_effort_hours:
                oversized_wp_ids.append(wp_id)

            if (
                not has_acceptance_criteria
                or not has_assigned_control_account
                or not deliverable_noun_phrase_valid
            ):
                incomplete_dictionary_wp_ids.append(wp_id)

    if oversized_wp_ids:
        recommendations.append(
            f"Decompose oversized leaf work packages exceeding {max_effort_hours:.1f}h (8/80 rule) into smaller deliverable units: {', '.join(oversized_wp_ids)}."
        )
    if incomplete_dictionary_wp_ids:
        recommendations.append(
            f"Complete WBS Dictionary entries (acceptance criteria, control account, noun-phrase deliverable) for: {', '.join(incomplete_dictionary_wp_ids)}."
        )
    if micromanaged_wp_ids:
        recommendations.append(
            f"Consolidate micro-managed leaf work packages below {min_effort_hours:.1f}h into cohesive work packages: {', '.join(micromanaged_wp_ids)}."
        )
    if excessive_depth_wp_ids:
        recommendations.append(
            f"Flatten WBS hierarchy levels exceeding depth {max_wbs_depth_level} on: {', '.join(excessive_depth_wp_ids)}."
        )

    if oversized_wp_ids or incomplete_dictionary_wp_ids:
        wbs_governance_status = "INVALID_WBS"
    elif micromanaged_wp_ids or excessive_depth_wp_ids:
        wbs_governance_status = "WARNING"
    else:
        wbs_governance_status = "WELL_DECOMPOSED"

    return {
        "total_work_packages": len(valid_wps),
        "micromanaged_wp_ids": micromanaged_wp_ids,
        "oversized_wp_ids": oversized_wp_ids,
        "excessive_depth_wp_ids": excessive_depth_wp_ids,
        "incomplete_dictionary_wp_ids": incomplete_dictionary_wp_ids,
        "wbs_governance_status": wbs_governance_status,
        "is_wbs_valid": wbs_governance_status == "WELL_DECOMPOSED",
        "recommendations": recommendations,
    }


def validate_risk_probability_impact_matrix_and_appetite_thresholds(
    risks: list[dict[str, Any]],
    *,
    high_risk_score_threshold: float = 0.18,
    urgency_days_threshold: int = 14,
) -> dict[str, Any]:
    """PMI PMBOK §11.3.2.3 — Qualitative Risk Analysis Probability-Impact (P-I) Matrix Scoring, Risk Appetite Threshold & Watchlist Escalation Validator."""
    valid_risks: list[dict[str, Any]] = []
    if isinstance(risks, (list, tuple)):
        for item in risks:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("risk_id") or "").strip()
            if not rid:
                continue
            valid_risks.append({**item, "_rid": rid})

    if not valid_risks:
        return {
            "total_risks": 0,
            "invalid_scale_risk_ids": [],
            "undertiered_high_risk_ids": [],
            "unmitigated_high_or_urgent_risk_ids": [],
            "unmonitored_low_risk_ids": [],
            "pi_matrix_governance_status": "CALIBRATED",
            "is_pi_matrix_valid": True,
            "recommendations": [],
        }

    invalid_scale_risk_ids: list[str] = []
    undertiered_high_risk_ids: list[str] = []
    unmitigated_high_or_urgent_risk_ids: list[str] = []
    unmonitored_low_risk_ids: list[str] = []

    for rsk in valid_risks:
        rid = rsk["_rid"]
        prob = float(rsk.get("probability", 0.0) or 0.0)
        imp = float(rsk.get("impact_weight", 0.0) or 0.0)
        proximity = max(0, int(rsk.get("days_to_impact_proximity", 30) or 0))
        tier = str(rsk.get("assigned_tier") or "").strip().upper()
        has_mitigation = bool(rsk.get("has_active_mitigation_plan", True))
        on_watchlist = bool(rsk.get("on_watchlist", True))

        pi_score = round(prob * imp, 4)

        if not (0.0 < prob <= 1.0) or not (0.0 < imp <= 1.0):
            invalid_scale_risk_ids.append(rid)

        if pi_score >= high_risk_score_threshold and tier != "HIGH":
            undertiered_high_risk_ids.append(rid)

        is_high_or_urgent = pi_score >= high_risk_score_threshold or (
            tier == "MODERATE" and proximity <= urgency_days_threshold
        )
        if is_high_or_urgent and not has_mitigation:
            unmitigated_high_or_urgent_risk_ids.append(rid)

        if tier == "LOW" and not on_watchlist and not has_mitigation:
            unmonitored_low_risk_ids.append(rid)

    recommendations: list[str] = []
    if invalid_scale_risk_ids:
        recommendations.append(
            f"Normalize probability and impact weights within (0.0, 1.0] for risk(s): {', '.join(invalid_scale_risk_ids)}."
        )
    if undertiered_high_risk_ids:
        recommendations.append(
            f"Escalate assigned_tier to 'HIGH' for risk(s) meeting/exceeding P-I threshold ({high_risk_score_threshold}): {', '.join(undertiered_high_risk_ids)}."
        )
    if unmitigated_high_or_urgent_risk_ids:
        recommendations.append(
            f"Define active mitigation plan for high-score or urgent moderate risk(s): {', '.join(unmitigated_high_or_urgent_risk_ids)}."
        )
    if unmonitored_low_risk_ids:
        recommendations.append(
            f"Add low-tier risk(s) to the risk watchlist for periodic monitoring: {', '.join(unmonitored_low_risk_ids)}."
        )

    if (
        invalid_scale_risk_ids
        or undertiered_high_risk_ids
        or unmitigated_high_or_urgent_risk_ids
    ):
        pi_matrix_governance_status = "MISCALIBRATED"
    elif unmonitored_low_risk_ids:
        pi_matrix_governance_status = "WARNING"
    else:
        pi_matrix_governance_status = "CALIBRATED"

    return {
        "total_risks": len(valid_risks),
        "invalid_scale_risk_ids": invalid_scale_risk_ids,
        "undertiered_high_risk_ids": undertiered_high_risk_ids,
        "unmitigated_high_or_urgent_risk_ids": unmitigated_high_or_urgent_risk_ids,
        "unmonitored_low_risk_ids": unmonitored_low_risk_ids,
        "pi_matrix_governance_status": pi_matrix_governance_status,
        "is_pi_matrix_valid": pi_matrix_governance_status == "CALIBRATED",
        "recommendations": recommendations,
    }


def validate_ccpm_fever_chart_and_buffer_consumption(
    chains: list[dict[str, Any]],
    *,
    red_zone_slope_factor: float = 0.7,
    red_zone_intercept_pct: float = 30.0,
    yellow_zone_intercept_pct: float = 15.0,
) -> dict[str, Any]:
    """PMI PMBOK §6.3 & §6.5 — Critical Chain Project Management (CCPM) Project Buffer, Feeding Buffer & Fever Chart Consumption Validator."""
    valid_chains: list[dict[str, Any]] = []
    if isinstance(chains, (list, tuple)):
        for item in chains:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("chain_id") or "").strip()
            if not cid:
                continue
            valid_chains.append({**item, "_cid": cid})

    if not valid_chains:
        return {
            "total_chains_evaluated": 0,
            "green_zone_count": 0,
            "yellow_zone_count": 0,
            "red_zone_count": 0,
            "unmitigated_red_zone_chain_ids": [],
            "max_buffer_burn_index": 0.0,
            "fever_chart_status": "HEALTHY_GREEN",
            "is_ccpm_buffer_compliant": True,
            "recommendations": [],
        }

    green_zone_count = 0
    yellow_zone_count = 0
    red_zone_count = 0
    unmitigated_red_zone_chain_ids: list[str] = []
    max_buffer_burn_index = 0.0

    for ch in valid_chains:
        cid = ch["_cid"]
        completion_pct = max(
            0.0, min(100.0, float(ch.get("chain_completion_pct", 0.0) or 0.0))
        )
        total_days = float(ch.get("buffer_total_days", 0.0) or 0.0)
        consumed_days = max(0.0, float(ch.get("buffer_consumed_days", 0.0) or 0.0))
        has_recovery = bool(ch.get("has_recovery_plan", False))

        if total_days > 0:
            buffer_consumed_pct = round((consumed_days / total_days) * 100.0, 2)
        else:
            buffer_consumed_pct = 100.0 if consumed_days > 0 else 0.0

        red_threshold_pct = round(
            red_zone_intercept_pct + red_zone_slope_factor * completion_pct, 2
        )
        yellow_threshold_pct = round(
            yellow_zone_intercept_pct + red_zone_slope_factor * completion_pct, 2
        )

        if buffer_consumed_pct <= yellow_threshold_pct:
            green_zone_count += 1
        elif buffer_consumed_pct <= red_threshold_pct:
            yellow_zone_count += 1
        else:
            red_zone_count += 1
            if not has_recovery:
                unmitigated_red_zone_chain_ids.append(cid)

        if completion_pct > 0:
            burn_index = round(buffer_consumed_pct / completion_pct, 2)
        elif buffer_consumed_pct > 0:
            burn_index = round(buffer_consumed_pct, 2)
        else:
            burn_index = 0.0

        if burn_index > max_buffer_burn_index:
            max_buffer_burn_index = burn_index

    recommendations: list[str] = []
    if unmitigated_red_zone_chain_ids:
        recommendations.append(
            f"Activate immediate schedule recovery plan for RED-zone CCPM chain(s): {', '.join(unmitigated_red_zone_chain_ids)}."
        )
    elif red_zone_count > 0:
        recommendations.append(
            "Monitor active recovery execution on RED-zone CCPM chains until buffer burn stabilizes."
        )
    if yellow_zone_count > 0:
        recommendations.append(
            f"Prepare contingency recovery options for {yellow_zone_count} YELLOW-zone CCPM chain(s)."
        )

    if len(unmitigated_red_zone_chain_ids) > 0:
        fever_chart_status = "FEVER_BREACH_UNMITIGATED"
    elif red_zone_count > 0:
        fever_chart_status = "CRITICAL_RED_MITIGATED"
    elif yellow_zone_count > 0:
        fever_chart_status = "WATCH_YELLOW"
    else:
        fever_chart_status = "HEALTHY_GREEN"

    return {
        "total_chains_evaluated": len(valid_chains),
        "green_zone_count": green_zone_count,
        "yellow_zone_count": yellow_zone_count,
        "red_zone_count": red_zone_count,
        "unmitigated_red_zone_chain_ids": unmitigated_red_zone_chain_ids,
        "max_buffer_burn_index": max_buffer_burn_index,
        "fever_chart_status": fever_chart_status,
        "is_ccpm_buffer_compliant": len(unmitigated_red_zone_chain_ids) == 0,
        "recommendations": recommendations,
    }


def validate_sprint_velocity_volatility_and_commitment_reliability(
    sprints: list[dict[str, Any]],
    *,
    min_say_do_ratio_pct: float = 80.0,
    max_carryover_rate_pct: float = 20.0,
    max_velocity_cv_pct: float = 30.0,
) -> dict[str, Any]:
    """PMI PMBOK §6.4 & §9.2 — Agile Sprint Capacity Velocity Volatility, Commitment Reliability & Carryover Debt Validator."""
    valid_sprints: list[dict[str, Any]] = []
    if isinstance(sprints, (list, tuple)):
        for item in sprints:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("sprint_id") or "").strip()
            if not sid:
                continue
            valid_sprints.append({**item, "_sid": sid})

    if not valid_sprints:
        return {
            "total_sprints_evaluated": 0,
            "mean_velocity": 0.0,
            "velocity_cv_pct": 0.0,
            "unreliable_commitment_sprint_ids": [],
            "excessive_carryover_sprint_ids": [],
            "predictability_status": "PREDICTABLE_CADENCE",
            "is_sprint_cadence_compliant": True,
            "recommendations": [],
        }

    unreliable_commitment_sprint_ids: list[str] = []
    excessive_carryover_sprint_ids: list[str] = []
    completed_points_list: list[float] = []

    for sp in valid_sprints:
        sid = sp["_sid"]
        committed = max(0.0, float(sp.get("committed_story_points", 0.0) or 0.0))
        completed = max(0.0, float(sp.get("completed_story_points", 0.0) or 0.0))
        carryover = max(0.0, float(sp.get("carryover_story_points", 0.0) or 0.0))

        completed_points_list.append(completed)

        if committed > 0:
            say_do_ratio_pct = round((completed / committed) * 100.0, 2)
            carryover_rate_pct = round((carryover / committed) * 100.0, 2)
        else:
            say_do_ratio_pct = 100.0
            carryover_rate_pct = 100.0 if carryover > 0 else 0.0

        if say_do_ratio_pct < min_say_do_ratio_pct:
            unreliable_commitment_sprint_ids.append(sid)
        if carryover_rate_pct > max_carryover_rate_pct:
            excessive_carryover_sprint_ids.append(sid)

    n = len(valid_sprints)
    mean_velocity = round(sum(completed_points_list) / n, 2)
    if mean_velocity > 0 and n > 1:
        variance = sum((x - mean_velocity) ** 2 for x in completed_points_list) / n
        std_dev = variance ** 0.5
        velocity_cv_pct = round((std_dev / mean_velocity) * 100.0, 2)
    else:
        velocity_cv_pct = 0.0

    recommendations: list[str] = []
    if unreliable_commitment_sprint_ids:
        recommendations.append(
            f"Improve sprint backlog refinement and capacity planning to achieve >= {min_say_do_ratio_pct}% Say/Do ratio on sprint(s): {', '.join(unreliable_commitment_sprint_ids)}."
        )
    if excessive_carryover_sprint_ids:
        recommendations.append(
            f"Slice user stories smaller to cap carryover debt (<= {max_carryover_rate_pct}%) on sprint(s): {', '.join(excessive_carryover_sprint_ids)}."
        )
    if velocity_cv_pct > max_velocity_cv_pct:
        recommendations.append(
            f"Stabilize team allocation and reduce mid-sprint interruptions to bring velocity CV ({velocity_cv_pct:.2f}%) within {max_velocity_cv_pct:.2f}%."
        )

    if unreliable_commitment_sprint_ids or excessive_carryover_sprint_ids:
        predictability_status = "UNPREDICTABLE_CHURN"
    elif velocity_cv_pct > max_velocity_cv_pct:
        predictability_status = "VOLATILE_VELOCITY"
    else:
        predictability_status = "PREDICTABLE_CADENCE"

    return {
        "total_sprints_evaluated": n,
        "mean_velocity": mean_velocity,
        "velocity_cv_pct": velocity_cv_pct,
        "unreliable_commitment_sprint_ids": unreliable_commitment_sprint_ids,
        "excessive_carryover_sprint_ids": excessive_carryover_sprint_ids,
        "predictability_status": predictability_status,
        "is_sprint_cadence_compliant": predictability_status == "PREDICTABLE_CADENCE",
        "recommendations": recommendations,
    }


def validate_portfolio_efficient_frontier_and_budget_knapsack(
    candidates: Any,
    *,
    total_portfolio_budget_cap: float = 100000.0,
    min_risk_adjusted_return_ratio: float = 1.2,
    min_strategic_fit_score: float = 65.0,
) -> Dict[str, object]:
    """Validador PMBOK 1.2.3 y Standard for Portfolio Management.

    Evalúa los proyectos seleccionados del portafolio: ratio de retorno
    ajustado por riesgo (NPV / volatilidad), alineación estratégica y
    sumatoria de CAPEX frente al techo presupuestario (knapsack).
    """
    entries = candidates if isinstance(candidates, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    selected_rows = [item for item in rows if item.get("is_selected_in_portfolio", False) is True]

    selected_total_capex = 0.0
    dominated_suboptimal_selected_ids: List[str] = []
    strategically_misaligned_selected_ids: List[str] = []

    for item in selected_rows:
        project_id = item.get("project_id")
        expected_return = item.get("expected_npv_return", 0.0)
        volatility = item.get("risk_volatility_cost", 1.0)
        required_capex = item.get("required_capex_budget", 0.0)
        strategic_fit = item.get("strategic_fit_score", 0.0)

        expected_val = expected_return if isinstance(expected_return, (int, float)) else 0.0
        volatility_val = volatility if isinstance(volatility, (int, float)) else 0.0
        capex_val = required_capex if isinstance(required_capex, (int, float)) else 0.0
        strategic_val = strategic_fit if isinstance(strategic_fit, (int, float)) else 0.0

        if volatility_val > 0:
            ratio = round(expected_val / volatility_val, 2)
        else:
            ratio = 0.0

        selected_total_capex += max(0.0, capex_val)

        if ratio < min_risk_adjusted_return_ratio:
            dominated_suboptimal_selected_ids.append(project_id)

        if strategic_val < min_strategic_fit_score:
            strategically_misaligned_selected_ids.append(project_id)

    selected_total_capex = round(selected_total_capex, 2)
    is_budget_cap_exceeded = selected_total_capex > total_portfolio_budget_cap

    if is_budget_cap_exceeded or strategically_misaligned_selected_ids:
        portfolio_optimization_status = "PORTFOLIO_CONSTRAINT_BREACH"
    elif dominated_suboptimal_selected_ids:
        portfolio_optimization_status = "SUBOPTIMAL_FRONTIER_WARNING"
    else:
        portfolio_optimization_status = "EFFICIENT_FRONTIER_OPTIMAL"

    return {
        "total_candidates_evaluated": len(rows),
        "selected_projects_count": len(selected_rows),
        "selected_total_capex": selected_total_capex,
        "is_budget_cap_exceeded": is_budget_cap_exceeded,
        "dominated_suboptimal_selected_ids": dominated_suboptimal_selected_ids,
        "strategically_misaligned_selected_ids": strategically_misaligned_selected_ids,
        "portfolio_optimization_status": portfolio_optimization_status,
        "is_portfolio_frontier_compliant": portfolio_optimization_status == "EFFICIENT_FRONTIER_OPTIMAL",
    }


def validate_pdm_network_dangling_activities_and_negative_float(
    activities: list[dict[str, Any]],
    *,
    max_lag_to_duration_ratio: float = 0.5,
) -> dict[str, Any]:
    """PMI PMBOK §6.2 & §6.3 — Schedule Network PDM Lead/Lag Abuse, Open-Ended Activity & Negative Float Validator."""
    valid_activities: list[dict[str, Any]] = []
    if isinstance(activities, (list, tuple)):
        for item in activities:
            if not isinstance(item, dict):
                continue
            aid = str(item.get("activity_id") or "").strip()
            if not aid:
                continue
            valid_activities.append({**item, "_aid": aid})

    if not valid_activities:
        return {
            "total_activities_evaluated": 0,
            "dangling_logic_activity_ids": [],
            "negative_float_activity_ids": [],
            "excessive_lead_or_lag_activity_ids": [],
            "schedule_network_status": "NETWORK_INTEGRITY_SOUND",
            "is_pdm_network_compliant": True,
            "recommendations": [],
        }

    dangling_logic_activity_ids: list[str] = []
    negative_float_activity_ids: list[str] = []
    excessive_lead_or_lag_activity_ids: list[str] = []

    for act in valid_activities:
        aid = act["_aid"]
        is_start = bool(act.get("is_start_milestone", False))
        is_finish = bool(act.get("is_finish_milestone", False))
        pred_cnt = int(
            act.get("predecessor_count", 0)
            if act.get("predecessor_count") is not None
            else 0
        )
        succ_cnt = int(
            act.get("successor_count", 0)
            if act.get("successor_count") is not None
            else 0
        )
        total_float = float(
            act.get("total_float_days", 0.0)
            if act.get("total_float_days") is not None
            else 0.0
        )
        lead_days = float(
            act.get("max_incoming_lead_days", 0.0)
            if act.get("max_incoming_lead_days") is not None
            else 0.0
        )
        lag_days = float(
            act.get("max_incoming_lag_days", 0.0)
            if act.get("max_incoming_lag_days") is not None
            else 0.0
        )
        duration = float(
            act.get("duration_days", 1.0)
            if act.get("duration_days") is not None
            else 1.0
        )

        if (not is_start and pred_cnt <= 0) or (
            not is_finish and succ_cnt <= 0
        ):
            dangling_logic_activity_ids.append(aid)

        if total_float < 0.0:
            negative_float_activity_ids.append(aid)

        if lead_days > 0.0 or (
            duration > 0.0
            and (lag_days / duration) > max_lag_to_duration_ratio
        ):
            excessive_lead_or_lag_activity_ids.append(aid)

    recommendations: list[str] = []
    if dangling_logic_activity_ids:
        recommendations.append(
            f"Close open-ended PDM network logic by assigning both predecessors and successors to non-milestone activity(ies): {', '.join(dangling_logic_activity_ids)}."
        )
    if negative_float_activity_ids:
        recommendations.append(
            f"Resolve negative total float via critical path re-sequencing or constraint removal in activity(ies): {', '.join(negative_float_activity_ids)}."
        )
    if excessive_lead_or_lag_activity_ids:
        recommendations.append(
            f"Eliminate negative lags (leads) and convert excessive lags (> {max_lag_to_duration_ratio * 100:.0f}% of duration) into explicit work packages in activity(ies): {', '.join(excessive_lead_or_lag_activity_ids)}."
        )

    if dangling_logic_activity_ids or negative_float_activity_ids:
        schedule_network_status = "DCMA_LOGIC_OR_FLOAT_BREACH"
    elif excessive_lead_or_lag_activity_ids:
        schedule_network_status = "LEAD_LAG_DISTORTION_WARNING"
    else:
        schedule_network_status = "NETWORK_INTEGRITY_SOUND"

    return {
        "total_activities_evaluated": len(valid_activities),
        "dangling_logic_activity_ids": dangling_logic_activity_ids,
        "negative_float_activity_ids": negative_float_activity_ids,
        "excessive_lead_or_lag_activity_ids": excessive_lead_or_lag_activity_ids,
        "schedule_network_status": schedule_network_status,
        "is_pdm_network_compliant": schedule_network_status
        == "NETWORK_INTEGRITY_SOUND",
        "recommendations": recommendations,
    }


def validate_risk_emv_decision_tree_and_contingency_adequacy(
    risks: list[dict[str, Any]],
    *,
    allocated_contingency_reserve: float = 10000.0,
    max_underfunded_shortfall_pct: float = 5.0,
) -> dict[str, Any]:
    """PMI PMBOK §11.4 & §7.3 — Risk Expected Monetary Value (EMV) Decision Tree Contingency Reserve Adequacy Validator."""
    valid_risks: list[dict[str, Any]] = []
    if isinstance(risks, (list, tuple)):
        for item in risks:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("risk_id") or "").strip()
            if not rid:
                continue
            valid_risks.append({**item, "_rid": rid})

    alloc_reserve = round(float(allocated_contingency_reserve or 0.0), 2)

    if not valid_risks:
        return {
            "total_risks_evaluated": 0,
            "net_threat_emv": 0.0,
            "allocated_contingency_reserve": alloc_reserve,
            "reserve_shortfall": 0.0,
            "shortfall_pct": 0.0,
            "invalid_probability_risk_ids": [],
            "unmodeled_high_threat_risk_ids": [],
            "emv_adequacy_status": "EMV_RESERVE_ADEQUATE",
            "is_emv_adequate": True,
            "recommendations": [],
        }

    invalid_probability_risk_ids: list[str] = []
    unmodeled_high_threat_risk_ids: list[str] = []
    emv_sum = 0.0

    for rsk in valid_risks:
        rid = rsk["_rid"]
        prob = float(
            rsk.get("probability", 0.0)
            if rsk.get("probability") is not None
            else 0.0
        )
        impact = float(
            rsk.get("financial_impact", 0.0)
            if rsk.get("financial_impact") is not None
            else 0.0
        )
        has_fallback = bool(rsk.get("has_quantified_fallback_branch", True))

        if prob < 0.0 or prob > 1.0:
            invalid_probability_risk_ids.append(rid)
            continue

        emv = prob * impact
        emv_sum += emv

        if emv >= 2000.0 and not has_fallback:
            unmodeled_high_threat_risk_ids.append(rid)

    net_threat_emv = round(emv_sum, 2)
    reserve_shortfall = round(max(0.0, net_threat_emv - alloc_reserve), 2)
    shortfall_pct = (
        round((reserve_shortfall / net_threat_emv) * 100.0, 2)
        if net_threat_emv > 0.0
        else 0.0
    )

    recommendations: list[str] = []
    if invalid_probability_risk_ids:
        recommendations.append(
            f"Normalize risk probabilities into [0.0, 1.0] interval for risk(s): {', '.join(invalid_probability_risk_ids)}."
        )
    if shortfall_pct > max_underfunded_shortfall_pct:
        recommendations.append(
            f"Replenish contingency reserve by {reserve_shortfall} ({shortfall_pct}% shortfall > {max_underfunded_shortfall_pct}% threshold) to cover net EMV exposure."
        )
    if unmodeled_high_threat_risk_ids:
        recommendations.append(
            f"Model quantified decision-tree fallback branches for high-EMV threat risk(s): {', '.join(unmodeled_high_threat_risk_ids)}."
        )

    if (
        invalid_probability_risk_ids
        or shortfall_pct > max_underfunded_shortfall_pct
    ):
        emv_adequacy_status = "UNDERFUNDED_OR_INVALID_MODEL"
    elif (
        unmodeled_high_threat_risk_ids
        or 0.0 < shortfall_pct <= max_underfunded_shortfall_pct
    ):
        emv_adequacy_status = "DECISION_TREE_BRANCH_WARNING"
    else:
        emv_adequacy_status = "EMV_RESERVE_ADEQUATE"

    return {
        "total_risks_evaluated": len(valid_risks),
        "net_threat_emv": net_threat_emv,
        "allocated_contingency_reserve": alloc_reserve,
        "reserve_shortfall": reserve_shortfall,
        "shortfall_pct": shortfall_pct,
        "invalid_probability_risk_ids": invalid_probability_risk_ids,
        "unmodeled_high_threat_risk_ids": unmodeled_high_threat_risk_ids,
        "emv_adequacy_status": emv_adequacy_status,
        "is_emv_adequate": emv_adequacy_status == "EMV_RESERVE_ADEQUATE",
        "recommendations": recommendations,
    }


def validate_pert_three_point_estimation_and_delphi_convergence(
    estimates: list[dict[str, Any]],
    *,
    max_uncertainty_spread_ratio: float = 3.0,
    max_expert_divergence_pct: float = 25.0,
) -> dict[str, Any]:
    """PMI PMBOK §6.4 & §7.2 — Three-Point PERT Estimation Beta/Triangular Skewness, Wide-Band Delphi Convergence & Optimism Bias Validator."""
    valid_estimates: list[dict[str, Any]] = []
    if isinstance(estimates, (list, tuple)):
        for item in estimates:
            if not isinstance(item, dict):
                continue
            wpid = str(item.get("work_package_id") or "").strip()
            if not wpid:
                continue
            valid_estimates.append({**item, "_wpid": wpid})

    if not valid_estimates:
        return {
            "total_estimates_evaluated": 0,
            "total_pert_expected_effort": 0.0,
            "inverted_bounds_package_ids": [],
            "excessive_spread_package_ids": [],
            "unconverged_delphi_package_ids": [],
            "pert_estimation_status": "PERT_CONVERGED_SOUND",
            "is_pert_estimation_compliant": True,
            "recommendations": [],
        }

    inverted_bounds_package_ids: list[str] = []
    excessive_spread_package_ids: list[str] = []
    unconverged_delphi_package_ids: list[str] = []
    expected_sum = 0.0

    for est in valid_estimates:
        wpid = est["_wpid"]
        opt_o = float(
            est.get("optimistic_o", 0.0)
            if est.get("optimistic_o") is not None
            else 0.0
        )
        ml_m = float(
            est.get("most_likely_m", 0.0)
            if est.get("most_likely_m") is not None
            else 0.0
        )
        pess_p = float(
            est.get("pessimistic_p", 0.0)
            if est.get("pessimistic_p") is not None
            else 0.0
        )
        delphi_div = float(
            est.get("delphi_round_divergence_pct", 0.0)
            if est.get("delphi_round_divergence_pct") is not None
            else 0.0
        )

        if delphi_div > max_expert_divergence_pct:
            unconverged_delphi_package_ids.append(wpid)

        if opt_o <= 0.0 or not (opt_o <= ml_m <= pess_p):
            inverted_bounds_package_ids.append(wpid)
            continue

        pert_expected = (opt_o + 4.0 * ml_m + pess_p) / 6.0
        expected_sum += pert_expected
        spread_ratio = pess_p / opt_o

        if spread_ratio > max_uncertainty_spread_ratio:
            excessive_spread_package_ids.append(wpid)

    total_pert_expected_effort = round(expected_sum, 2)

    recommendations: list[str] = []
    if inverted_bounds_package_ids:
        recommendations.append(
            f"Enforce strictly positive monotonic three-point bounds (0 < O <= M <= P) for work package(s): {', '.join(inverted_bounds_package_ids)}."
        )
    if unconverged_delphi_package_ids:
        recommendations.append(
            f"Conduct additional Wide-Band Delphi consensus rounds until expert divergence <= {max_expert_divergence_pct}% for work package(s): {', '.join(unconverged_delphi_package_ids)}."
        )
    if excessive_spread_package_ids:
        recommendations.append(
            f"Decompose work packages with P/O uncertainty cone ratio > {max_uncertainty_spread_ratio} into smaller WBS tasks: {', '.join(excessive_spread_package_ids)}."
        )

    if inverted_bounds_package_ids or unconverged_delphi_package_ids:
        pert_estimation_status = "INVALID_BOUNDS_OR_UNCONVERGED"
    elif excessive_spread_package_ids:
        pert_estimation_status = "WIDE_UNCERTAINTY_CONE_WARNING"
    else:
        pert_estimation_status = "PERT_CONVERGED_SOUND"

    return {
        "total_estimates_evaluated": len(valid_estimates),
        "total_pert_expected_effort": total_pert_expected_effort,
        "inverted_bounds_package_ids": inverted_bounds_package_ids,
        "excessive_spread_package_ids": excessive_spread_package_ids,
        "unconverged_delphi_package_ids": unconverged_delphi_package_ids,
        "pert_estimation_status": pert_estimation_status,
        "is_pert_estimation_compliant": pert_estimation_status
        == "PERT_CONVERGED_SOUND",
        "recommendations": recommendations,
    }


def validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity(
    simulations: Any,
    *,
    min_iterations_required: int = 5000,
    max_p90_to_p50_tail_ratio: float = 1.35,
) -> dict[str, Any]:
    """PMI PMBOK §11.4 & §6.5 — Monte Carlo P50/P80/P90 Confidence Interval Convergence, Tail Risk & Tornado Sensitivity Validator."""
    valid_rows: list[dict[str, Any]] = []
    if isinstance(simulations, (list, tuple)):
        for item in simulations:
            if not isinstance(item, dict):
                continue
            model_id = item.get("model_id")
            if not isinstance(model_id, str) or not model_id.strip():
                continue
            valid_rows.append({**item, "_model_id": model_id.strip()})

    def _num(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    under_converged_or_inverted_model_ids: list[str] = []
    underfunded_or_fat_tail_model_ids: list[str] = []

    for row in valid_rows:
        model_id = row["_model_id"]
        iterations = _num(row.get("iterations_count"), 10000.0)
        p50 = _num(row.get("p50_estimate"), 100.0)
        p80 = _num(row.get("p80_estimate"), 115.0)
        p90 = _num(row.get("p90_estimate"), 125.0)
        baseline = _num(row.get("baseline_commitment"), 115.0)
        correlation_r = _num(row.get("top_driver_correlation_r"), 0.5)

        if iterations < min_iterations_required or not (
            0.0 < p50 <= p80 <= p90
        ):
            under_converged_or_inverted_model_ids.append(model_id)

        if (
            baseline < p80
            or (p50 > 0.0 and (p90 / p50) > max_p90_to_p50_tail_ratio)
            or abs(correlation_r) > 0.85
        ):
            underfunded_or_fat_tail_model_ids.append(model_id)

    if under_converged_or_inverted_model_ids:
        monte_carlo_validation_status = (
            "MONTE_CARLO_CONVERGENCE_OR_MONOTONICITY_BREACH"
        )
    elif underfunded_or_fat_tail_model_ids:
        monte_carlo_validation_status = (
            "MONTE_CARLO_P80_UNDERFUNDED_OR_TAIL_WARNING"
        )
    else:
        monte_carlo_validation_status = "MONTE_CARLO_CONFIDENCE_OPTIMAL"

    return {
        "evaluated_models_count": len(valid_rows),
        "under_converged_or_inverted_model_ids": (
            under_converged_or_inverted_model_ids
        ),
        "underfunded_or_fat_tail_model_ids": (
            underfunded_or_fat_tail_model_ids
        ),
        "monte_carlo_validation_status": monte_carlo_validation_status,
        "is_monte_carlo_valid": monte_carlo_validation_status
        == "MONTE_CARLO_CONFIDENCE_OPTIMAL",
    }


def validate_resource_leveling_overallocation_and_context_switching(
    resource_allocations: Sequence[Mapping[str, Any]] | None,
    *,
    max_allocation_utilization_pct: float = 100.0,
    max_concurrent_work_packages: int = 3,
) -> dict[str, Any]:
    """PMI PMBOK §9.2 & §6.4 — Resource Leveling Overallocation Peak, Context-Switching Fragmentation & Burnout Threshold Validator."""
    valid_resources = [
        res
        for res in (resource_allocations or [])
        if isinstance(res, Mapping) and str(res.get("resource_id") or "").strip()
    ]

    overallocated_or_burnout_resource_ids: list[str] = []
    fragmented_context_switching_resource_ids: list[str] = []

    for res in valid_resources:
        rid = str(res.get("resource_id")).strip()
        allocated_hours = float(
            res.get("allocated_hours_per_week", 36.0)
            if res.get("allocated_hours_per_week") is not None
            else 36.0
        )
        capacity_hours = float(
            res.get("available_capacity_hours_per_week", 40.0)
            if res.get("available_capacity_hours_per_week") is not None
            else 40.0
        )
        concurrent_tasks = int(
            res.get("concurrent_active_tasks_count", 2)
            if res.get("concurrent_active_tasks_count") is not None
            else 2
        )
        overtime_weeks = int(
            res.get("sustained_overtime_weeks_count", 0)
            if res.get("sustained_overtime_weeks_count") is not None
            else 0
        )

        if (
            capacity_hours <= 0
            or (
                (allocated_hours / capacity_hours) * 100.0
                > max_allocation_utilization_pct
            )
            or overtime_weeks > 2
        ):
            overallocated_or_burnout_resource_ids.append(rid)

        if concurrent_tasks > max_concurrent_work_packages:
            fragmented_context_switching_resource_ids.append(rid)

    if overallocated_or_burnout_resource_ids:
        resource_leveling_status = "RESOURCE_OVERALLOCATION_OR_BURNOUT_BREACH"
    elif fragmented_context_switching_resource_ids:
        resource_leveling_status = "RESOURCE_CONTEXT_SWITCHING_WARNING"
    else:
        resource_leveling_status = "RESOURCE_LEVELING_BALANCED"

    return {
        "evaluated_resources_count": len(valid_resources),
        "overallocated_or_burnout_resource_ids": overallocated_or_burnout_resource_ids,
        "fragmented_context_switching_resource_ids": fragmented_context_switching_resource_ids,
        "resource_leveling_status": resource_leveling_status,
        "is_resource_leveling_valid": resource_leveling_status
        == "RESOURCE_LEVELING_BALANCED",
    }


def validate_wbs_rolling_wave_horizon_and_8_80_rule(
    wbs_elements: Sequence[Mapping[str, Any]] | None,
    *,
    freeze_horizon_days: int | float = 30,
    min_work_package_hours: float = 8.0,
    max_work_package_hours: float = 80.0,
) -> dict[str, Any]:
    """PMI PMBOK §5.4 & §6.2 — WBS Rolling Wave Planning Horizon, Planning Package Decomposition Lead-Time & 8/80 Rule Validator."""
    valid_elements = [
        elem
        for elem in (wbs_elements or [])
        if isinstance(elem, Mapping)
        and str(elem.get("element_id") or "").strip()
    ]

    undecomposed_horizon_or_unowned_ids: list[str] = []
    sizing_rule_8_80_violation_ids: list[str] = []

    for elem in valid_elements:
        eid = str(elem.get("element_id")).strip()
        is_planning_pkg = bool(
            elem.get("is_unexpanded_planning_package", False)
            if elem.get("is_unexpanded_planning_package") is not None
            else False
        )
        raw_days = elem.get("days_until_scheduled_start")
        days_until_start = float(raw_days if raw_days is not None else 45.0)
        raw_hours = elem.get("estimated_effort_hours")
        effort_hours = float(raw_hours if raw_hours is not None else 40.0)
        has_owner = bool(
            elem.get("has_single_accountable_owner", True)
            if elem.get("has_single_accountable_owner") is not None
            else True
        )

        if (
            is_planning_pkg and days_until_start <= freeze_horizon_days
        ) or not has_owner:
            undecomposed_horizon_or_unowned_ids.append(eid)

        if not is_planning_pkg and (
            effort_hours < min_work_package_hours
            or effort_hours > max_work_package_hours
        ):
            sizing_rule_8_80_violation_ids.append(eid)

    if undecomposed_horizon_or_unowned_ids:
        rolling_wave_status = (
            "WBS_ROLLING_WAVE_DECOMPOSITION_OR_OWNERSHIP_BREACH"
        )
    elif sizing_rule_8_80_violation_ids:
        rolling_wave_status = "WBS_8_80_SIZING_RULE_WARNING"
    else:
        rolling_wave_status = "WBS_ROLLING_WAVE_OPTIMAL"

    return {
        "evaluated_elements_count": len(valid_elements),
        "undecomposed_horizon_or_unowned_ids": undecomposed_horizon_or_unowned_ids,
        "sizing_rule_8_80_violation_ids": sizing_rule_8_80_violation_ids,
        "rolling_wave_status": rolling_wave_status,
        "is_rolling_wave_valid": rolling_wave_status
        == "WBS_ROLLING_WAVE_OPTIMAL",
    }


def validate_rtm_bidirectional_traceability_and_gold_plating(
    requirements: Sequence[Mapping[str, Any]] | None,
    *,
    min_test_case_coverage_per_req: int = 1,
) -> dict[str, Any]:
    """PMI PMBOK §5.2 & §5.3 — Requirements Traceability Matrix (RTM) Bidirectional Coverage, Orphan Test Case & Gold-Plating Scope Creep Validator."""
    valid_requirements = [
        req
        for req in (requirements or [])
        if isinstance(req, Mapping) and str(req.get("req_id") or "").strip()
    ]

    untested_or_gold_plating_req_ids: list[str] = []
    untraced_objective_or_wbs_req_ids: list[str] = []

    for req in valid_requirements:
        rid = str(req.get("req_id")).strip()
        linked_obj = req.get("linked_business_objective_id", "OBJ-1")
        linked_wbs = req.get("linked_wbs_deliverable_id", "WBS-1.1")
        test_cases_count = int(
            req.get("linked_verification_test_cases_count", 2)
            if req.get("linked_verification_test_cases_count") is not None
            else 2
        )
        is_gold_plating = bool(
            req.get("is_unapproved_gold_plating_feature", False)
            if req.get("is_unapproved_gold_plating_feature") is not None
            else False
        )

        if (
            is_gold_plating
            or test_cases_count < min_test_case_coverage_per_req
        ):
            untested_or_gold_plating_req_ids.append(rid)

        if (
            not linked_obj
            or not str(linked_obj).strip()
            or not linked_wbs
            or not str(linked_wbs).strip()
        ):
            untraced_objective_or_wbs_req_ids.append(rid)

    if untested_or_gold_plating_req_ids:
        rtm_traceability_status = "RTM_GOLD_PLATING_OR_UNTESTED_BREACH"
    elif untraced_objective_or_wbs_req_ids:
        rtm_traceability_status = "RTM_ORPHAN_TRACEABILITY_LINK_WARNING"
    else:
        rtm_traceability_status = "RTM_BIDIRECTIONAL_TRACEABILITY_OPTIMAL"

    return {
        "evaluated_requirements_count": len(valid_requirements),
        "untested_or_gold_plating_req_ids": untested_or_gold_plating_req_ids,
        "untraced_objective_or_wbs_req_ids": untraced_objective_or_wbs_req_ids,
        "rtm_traceability_status": rtm_traceability_status,
        "is_rtm_traceability_valid": rtm_traceability_status
        == "RTM_BIDIRECTIONAL_TRACEABILITY_OPTIMAL",
    }


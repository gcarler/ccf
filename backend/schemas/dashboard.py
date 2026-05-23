from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config


# --- Common Dashboard Elements ---
class MetricCard(BaseModel):
    title: str
    value: str
    trend: Optional[str] = None
    color: Optional[str] = "blue"
    icon: Optional[str] = None


class ChartDataPoint(BaseModel):
    label: str
    value: float


# --- Module Specific Dashboards ---


class AcademyDashboard(BaseModel):
    cards: List[MetricCard]
    enrollment_trends: List[ChartDataPoint]
    top_courses: List[Dict[str, str | int]]
    grade_distribution: List[ChartDataPoint]
    at_risk_students_count: int
    model_config = orm_config


class CrmDashboard(BaseModel):
    cards: List[MetricCard]
    pipeline_distribution: List[ChartDataPoint]
    growth_chart: List[ChartDataPoint]
    recent_interactions: List[Dict]
    conversion_rate: float
    model_config = orm_config


class FinanceDashboard(BaseModel):
    cards: List[MetricCard]
    income_by_category: List[ChartDataPoint]
    monthly_comparison: List[ChartDataPoint]
    pending_pledges_total: float
    model_config = orm_config


class ProjectsDashboard(BaseModel):
    cards: List[MetricCard]
    workload_distribution: List[ChartDataPoint]
    milestone_timeline: List[Dict]
    delayed_tasks_count: int
    model_config = orm_config


class AssetsDashboard(BaseModel):
    cards: List[MetricCard]
    maintenance_cost_trends: List[ChartDataPoint]
    lifecycle_status: List[ChartDataPoint]
    critical_alerts_count: int
    model_config = orm_config


class AdminGlobalDashboard(BaseModel):
    cards: List[MetricCard]
    system_load_chart: List[ChartDataPoint]
    audit_activity: List[ChartDataPoint]
    db_health_score: float
    active_sessions_count: int
    model_config = orm_config

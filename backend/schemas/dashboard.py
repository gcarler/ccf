from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from backend.schemas._common import orm_config


# ═══════════════════════════════════════════════════════════════════
# COMMON DASHBOARD ELEMENTS
# ═══════════════════════════════════════════════════════════════════

class MetricCard(BaseModel):
    title: str
    value: str
    trend: Optional[str] = None
    tone: Optional[str] = "blue"
    icon: Optional[str] = None
    subtitle: Optional[str] = None


class ChartDataPoint(BaseModel):
    label: str
    value: float
    secondary_value: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class FunnelStage(BaseModel):
    stage: str
    count: int
    conversion_rate: Optional[float] = None


class GeoBucket(BaseModel):
    label: str
    value: float
    lat: Optional[float] = None
    lng: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class HeatmapItem(BaseModel):
    x: str
    y: str
    value: float


class TableRow(BaseModel):
    id: str
    columns: Dict[str, Any]
    link: Optional[str] = None


class DashboardFilter(BaseModel):
    key: str
    label: str
    type: str = "select"
    options: Optional[List[Dict[str, str]]] = None
    default: Optional[Any] = None


# --- Module Specific Dashboards ---


class AcademyDashboard(BaseModel):
    cards: List[MetricCard]
    enrollment_trends: List[ChartDataPoint]
    top_courses: List[Dict[str, str | int]]
    grade_distribution: List[ChartDataPoint]
    at_risk_students_count: int
    filters: Optional[List[DashboardFilter]] = None
    geo_data: Optional[List[GeoBucket]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class CrmDashboard(BaseModel):
    cards: List[MetricCard]
    pipeline_funnel: List[FunnelStage]
    growth_chart: List[ChartDataPoint]
    interaction_heatmap: List[HeatmapItem]
    conversion_rate: Optional[float] = None
    pending_followups: int = 0
    slas_vencidos: int = 0
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class FinanceDashboard(BaseModel):
    cards: List[MetricCard]
    income_by_category: List[ChartDataPoint]
    monthly_series: List[ChartDataPoint]
    pending_pledges_total: Optional[float] = 0
    latest_donations: Optional[List[Dict]] = None
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class ProjectsDashboard(BaseModel):
    cards: List[MetricCard]
    workload_distribution: List[ChartDataPoint]
    milestone_timeline: Optional[List[Dict]] = None
    delayed_tasks_count: int
    status_distribution: List[ChartDataPoint]
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class EvangelismDashboard(BaseModel):
    cards: List[MetricCard]
    attendance_rate: float
    grupos_por_ubicacion: List[GeoBucket]
    asistencia_por_sesion: List[ChartDataPoint]
    embudo: List[FunnelStage]
    seguimientos_pendientes: int
    ausentes_detalle: Optional[List[TableRow]] = None
    asistentes_detalle: Optional[List[TableRow]] = None
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class AgendaDashboard(BaseModel):
    cards: List[MetricCard]
    eventos_proximos: Optional[List[Dict]] = None
    recursos_ocupados: List[ChartDataPoint]
    participacion_por_evento: List[ChartDataPoint]
    colisiones_recurso: int = 0
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class CmsDashboard(BaseModel):
    cards: List[MetricCard]
    versiones_por_pagina: List[ChartDataPoint]
    publicaciones_por_mes: List[ChartDataPoint]
    contenido_por_tipo: List[ChartDataPoint]
    borradores_pendientes: int
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class AdminGlobalDashboard(BaseModel):
    cards: List[MetricCard]
    audit_activity: Optional[List[ChartDataPoint]] = None
    usuarios_por_rol: List[ChartDataPoint]
    sesiones_activas: int = 0
    errores_recientes: int = 0
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config

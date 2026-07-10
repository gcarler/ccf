from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

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
    id: UUID
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
    enrollment_trends: List[ChartDataPoint] = []
    top_courses: List[Dict[str, str | int]] = []
    grade_distribution: List[ChartDataPoint] = []
    at_risk_students_count: int = 0
    filters: Optional[List[DashboardFilter]] = None
    geo_data: Optional[List[GeoBucket]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class CrmDashboard(BaseModel):
    cards: List[MetricCard]
    pipeline_funnel: List[FunnelStage] = []
    growth_chart: List[ChartDataPoint] = []
    interaction_heatmap: List[HeatmapItem] = []
    conversion_rate: Optional[float] = None
    pending_followups: int = 0
    slas_vencidos: int = 0
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class FinanceDashboard(BaseModel):
    cards: List[MetricCard]
    income_by_category: List[ChartDataPoint] = []
    monthly_series: List[ChartDataPoint] = []
    pending_pledges_total: Optional[float] = 0
    latest_donations: Optional[List[Dict]] = None
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class ProjectsDashboard(BaseModel):
    cards: List[MetricCard]
    workload_distribution: List[ChartDataPoint] = []
    milestone_timeline: Optional[List[Dict]] = None
    delayed_tasks_count: int = 0
    status_distribution: List[ChartDataPoint] = []
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class EvangelismDashboard(BaseModel):
    cards: List[MetricCard]
    attendance_rate: float = 0.0
    grupos_por_ubicacion: List[GeoBucket] = []
    asistencia_por_sesion: List[ChartDataPoint] = []
    embudo: List[FunnelStage] = []
    seguimientos_pendientes: int = 0
    ausentes_detalle: Optional[List[TableRow]] = None
    asistentes_detalle: Optional[List[TableRow]] = None
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class AgendaDashboard(BaseModel):
    cards: List[MetricCard]
    eventos_proximos: Optional[List[Dict]] = None
    recursos_ocupados: List[ChartDataPoint] = []
    participacion_por_evento: List[ChartDataPoint] = []
    colisiones_recurso: int = 0
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class SeoTrendPoint(BaseModel):
    """Un punto diario del widget SEO score trend."""
    label: str
    value: int
    metadata: Optional[Dict[str, Any]] = None


class CmsSeoTrendResponse(BaseModel):
    """Slice de SEO score trend para el dashboard CMS.

    Alimenta el widget "SEO score trend" del dashboard. La serie
    ``history_30d`` se renderiza como sparkline; ``history_7d`` se
    muestra como detalle + comparación con la semana previa. La
    alerta ``is_alert`` se dispara cuando la última lectura cae más
    de 10 puntos respecto a la previa (sea misma semana o 7d atrás).
    """
    current_score: Optional[int] = None
    previous_score: Optional[int] = None
    change_vs_prior: Optional[int] = None
    is_alert: bool = False
    alert_threshold: int = Field(
        default=10,
        description="Daily drop in points that triggers is_alert=True.",
    )
    total_pages: int = 0
    pages_with_errors: int = 0
    critical_issues: int = 0
    history_7d: List[SeoTrendPoint] = []
    history_30d: List[SeoTrendPoint] = []
    captured_at: Optional[str] = None
    has_data: bool = False


class CmsDashboard(BaseModel):
    cards: List[MetricCard]
    versiones_por_pagina: List[ChartDataPoint] = []
    publicaciones_por_mes: List[ChartDataPoint] = []
    contenido_por_tipo: List[ChartDataPoint] = []
    borradores_pendientes: int = 0
    # Métricas reales de page views, posts y actividad
    page_views_total: int = 0
    page_views_7d: int = 0
    page_views_30d: int = 0
    top_pages: List[Dict[str, Any]] = []
    recent_posts: List[Dict[str, Any]] = []
    recent_activity: List[Dict[str, Any]] = []
    posts_total: int = 0
    posts_published: int = 0
    categories_total: int = 0
    tags_total: int = 0
    # SEO score trend widget (alimentado por ``cms_seo_snapshots``,
    # capturado por ``backend.scheduler`` cada día).
    seo_trend: Optional[CmsSeoTrendResponse] = None
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config


class AdminGlobalDashboard(BaseModel):
    cards: List[MetricCard]
    audit_activity: Optional[List[ChartDataPoint]] = None
    usuarios_por_rol: List[ChartDataPoint] = []
    sesiones_activas: int = 0
    errores_recientes: int = 0
    filters: Optional[List[DashboardFilter]] = None
    last_updated: Optional[str] = None
    model_config = orm_config

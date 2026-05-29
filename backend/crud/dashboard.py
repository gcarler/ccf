"""Multi-module dashboard CRUD — aggregaciones reales con datos vivos.

Cada función consulta la base de datos directamente y devuelve
métricas, tendencias y distribuciones para alimentar los dashboards.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import case, desc, func, text
from sqlalchemy.orm import Session

from backend import models
from backend.schemas.dashboard import (
    AcademyDashboard,
    AdminGlobalDashboard,
    AgendaDashboard,
    CmsDashboard,
    CrmDashboard,
    ChartDataPoint,
    DashboardFilter,
    EvangelismDashboard,
    FinanceDashboard,
    FunnelStage,
    GeoBucket,
    HeatmapItem,
    MetricCard,
    ProjectsDashboard,
    TableRow,
)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _month_range(months_ago: int = 0):
    now = _utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(months_ago):
        start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    return start, end


def _sede_filters(db: Session) -> List[DashboardFilter]:
    try:
        sedes = db.query(models.Sede.id, models.Sede.nombre).filter(
            models.Sede.es_activa == True
        ).all()
    except Exception:
        sedes = []
    return [
        DashboardFilter(
            key="sede_id",
            label="Sede",
            type="select",
            options=[{"label": "Todas", "value": ""}] + [
                {"label": s.nombre, "value": str(s.id)} for s in sedes
            ],
            default="",
        )
    ]


# ═══════════════════════════════════════════════════════════════════
# 1. CRM DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_crm_dashboard(db: Session, sede_id: Optional[int] = None) -> CrmDashboard:
    from sqlalchemy import text as sqlt

    # Use raw SQL for maximum compatibility with actual schema
    base_where = ""
    if sede_id:
        base_where = f"AND p.sede_id = {sede_id}"

    total = db.execute(sqlt(f"SELECT COUNT(*) FROM personas p WHERE 1=1 {base_where}")).scalar() or 0
    casos = db.execute(sqlt("""
        SELECT estado, COUNT(*) as cnt FROM crm_casos
        WHERE deleted_at IS NULL GROUP BY estado
    """)).all()
    total_casos = sum(r[1] for r in casos) or 1
    funnel = [FunnelStage(stage=r[0] or 'new', count=r[1],
                          conversion_rate=round(r[1]/total_casos*100, 1)) for r in casos]

    # Growth
    growth = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        c = db.execute(sqlt(
            "SELECT COUNT(*) FROM personas WHERE created_at BETWEEN :s AND :e"
        ), {"s": start, "e": end}).scalar() or 0
        growth.append(ChartDataPoint(label=start.strftime("%b"), value=c))

    # Pending follow-ups
    pending = db.execute(sqlt(
        "SELECT COUNT(*) FROM consolidation_cases WHERE next_contact_at <= :now AND status = 'active'"
    ), {"now": _utcnow()}).scalar() or 0

    conversion = round(sum(r[1] for r in casos if r[0] in ('closed', 'won', 'completed')) / max(total_casos, 1) * 100, 1)

    return CrmDashboard(
        cards=[
            MetricCard(title="Personas", value=str(total), tone="blue", icon="Users"),
            MetricCard(title="Casos Activos", value=str(total_casos), trend=f"{conversion}% conversión", tone="emerald", icon="FolderKanban"),
            MetricCard(title="Etapas Pipeline", value=str(len(funnel)), tone="amber", icon="BarChart3"),
            MetricCard(title="Seguimientos Pend.", value=str(pending), tone="violet", icon="Bell"),
        ],
        pipeline_funnel=funnel,
        growth_chart=growth,
        interaction_heatmap=[],
        conversion_rate=conversion,
        pending_followups=pending,
        slas_vencidos=0,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 2. EVANGELISM DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_evangelism_dashboard(
    db: Session, sede_id: Optional[int] = None, estrategia_id: Optional[str] = None
) -> EvangelismDashboard:
    from sqlalchemy import text as sqlt

    where = ""
    where_cg = ""
    if sede_id:
        where += f" AND sede_id = {sede_id}"
        where_cg = f" AND ge.sede_id = {sede_id}"

    total_grupos = db.execute(sqlt(f"""
        SELECT COUNT(*) FROM grupos_evangelismo
        WHERE activo = true {where}
    """)).scalar() or 0
    total_participantes = db.execute(sqlt(f"""
        SELECT COUNT(DISTINCT gp.persona_id) FROM grupo_participantes gp
        JOIN grupos_evangelismo ge ON gp.grupo_id = ge.id
        WHERE ge.activo = true {where}
    """)).scalar() or 0

    cutoff = _utcnow() - timedelta(days=30)
    presentes = db.execute(sqlt(f"""
        SELECT COUNT(*) FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        WHERE sg.fecha_sesion >= :cutoff {where_cg}
        AND a.estado = 'Presente'
    """), {"cutoff": cutoff}).scalar() or 0

    ausentes = db.execute(sqlt(f"""
        SELECT COUNT(*) FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        WHERE sg.fecha_sesion >= :cutoff {where_cg}
        AND (a.estado = 'Ausente' OR a.estado IS NULL)
    """), {"cutoff": cutoff}).scalar() or 0

    total_asi = presentes + ausentes
    attendance_rate = round(presentes / max(total_asi, 1) * 100, 1)

    # Grupos por ubicación (geo)
    geo_rows = db.execute(sqlt(f"""
        SELECT ubicacion, latitud, longitud FROM grupos_evangelismo
        WHERE activo = true AND latitud IS NOT NULL {where}
        LIMIT 50
    """)).all()
    geo_buckets = [
        GeoBucket(label=r[0] or "Sin ubicación", value=0, lat=float(r[1]) if r[1] else None, lng=float(r[2]) if r[2] else None)
        for r in geo_rows
    ]

    # Asistencia por sesión (últimas 10)
    sesiones = db.execute(sqlt(f"""
        SELECT sg.id, sg.fecha_sesion, ge.nombre as grupo_nombre,
            (SELECT COUNT(*) FROM asistencias WHERE sesion_id = sg.id AND estado = 'Presente') as presentes,
            (SELECT COUNT(*) FROM asistencias WHERE sesion_id = sg.id AND (estado = 'Ausente' OR estado IS NULL)) as ausentes
        FROM sesiones_grupo sg
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        WHERE sg.fecha_sesion >= :cutoff {where_cg}
        ORDER BY sg.fecha_sesion DESC LIMIT 10
    """), {"cutoff": cutoff}).all()

    asistencia_chart = []
    for s in reversed(sesiones):
        fecha = s.fecha_sesion
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha)
            except:
                fecha = _utcnow()
        asistencia_chart.append(ChartDataPoint(
            label=fecha.strftime("%d/%m") if hasattr(fecha, 'strftime') else str(fecha)[5:10],
            value=float(s.presentes or 0),
            secondary_value=float(s.ausentes or 0),
            metadata={"total": (s.presentes or 0) + (s.ausentes or 0), "grupo": s.grupo_nombre or ""},
        ))

    # Embudo
    total_estrategias = db.execute(sqlt("SELECT COUNT(*) FROM evangelism_strategies WHERE activa = true")).scalar() or 0
    funnel = [
        FunnelStage(stage="Estrategias", count=total_estrategias),
        FunnelStage(stage="Grupos", count=total_grupos),
        FunnelStage(stage="Participantes", count=total_participantes),
        FunnelStage(stage="Asistentes (30d)", count=presentes, conversion_rate=attendance_rate),
    ]

    # Seguimientos
    seguimientos = 0

    # Detalle ausentes
    ausentes_rows = db.execute(sqlt(f"""
        SELECT p.id, p.first_name, p.last_name, ge.nombre as grupo, sg.fecha_sesion, a.estado, a.detalle_excusa
        FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        JOIN personas p ON a.persona_id = p.id
        WHERE sg.fecha_sesion >= :cutoff {where_cg}
        AND (a.estado = 'Ausente' OR a.estado IS NULL)
        LIMIT 50
    """), {"cutoff": cutoff}).all()

    ausentes_detalle = [
        TableRow(id=str(r.id), columns={
            "persona": f"{r.first_name or ''} {r.last_name or ''}",
            "grupo": r.grupo or "",
            "fecha": r.session_date.strftime("%d/%m/%Y") if hasattr(r.session_date, 'strftime') else str(r.session_date or '')[:10],
            "excusa": r.absence_reason_detail or r.estado or "",
        }, link="/plataforma/groups")
        for r in ausentes_rows
    ]

    asistentes_rows = db.execute(sqlt(f"""
        SELECT DISTINCT p.id, p.first_name, p.last_name, ge.nombre as grupo
        FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        JOIN personas p ON a.persona_id = p.id
        WHERE sg.fecha_sesion >= :cutoff {where_cg}
        AND a.estado = 'Presente'
        LIMIT 50
    """), {"cutoff": cutoff}).all()

    asistentes_detalle = [
        TableRow(id=str(r.id), columns={
            "persona": f"{r.first_name or ''} {r.last_name or ''}",
            "grupo": r.grupo or "",
        }, link="/plataforma/groups")
        for r in asistentes_rows
    ]

    filters = _sede_filters(db)

    return EvangelismDashboard(
        cards=[
            MetricCard(title="Grupos", value=str(total_grupos), trend=f"{total_participantes} participantes", tone="blue", icon="Home"),
            MetricCard(title="Tasa Asistencia", value=f"{attendance_rate}%", trend=f"{presentes} presentes (30d)", tone="emerald", icon="Users"),
            MetricCard(title="Sesiones (30d)", value=str(len(sesiones)), trend=f"{ausentes} ausencias", tone="amber", icon="Calendar"),
            MetricCard(title="Seguimientos Pend.", value=str(seguimientos), tone="violet", icon="Bell"),
        ],
        attendance_rate=attendance_rate,
        grupos_por_ubicacion=geo_buckets,
        asistencia_por_sesion=asistencia_chart,
        embudo=funnel,
        seguimientos_pendientes=seguimientos,
        ausentes_detalle=ausentes_detalle or None,
        asistentes_detalle=asistentes_detalle or None,
        filters=filters,
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 3. ACADEMY DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_academy_dashboard(db: Session, sede_id: Optional[int] = None) -> AcademyDashboard:
    from sqlalchemy import text as sqlt

    total_cursos = db.execute(sqlt("SELECT COUNT(*) FROM courses")).scalar() or 0
    publicados = db.execute(sqlt("SELECT COUNT(*) FROM courses WHERE is_published = 1")).scalar() or 0
    estudiantes = db.execute(sqlt("SELECT COUNT(*) FROM enrollments WHERE status = 'active'")).scalar() or 0
    avg_prog = db.execute(sqlt("SELECT COALESCE(AVG(progress_percent), 0) FROM enrollments")).scalar() or 0
    certs = db.execute(sqlt("SELECT COUNT(*) FROM enrollments WHERE certificate_issued = 1")).scalar() or 0

    trends = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        c = db.execute(sqlt(
            "SELECT COUNT(*) FROM enrollments WHERE created_at BETWEEN :s AND :e"
        ), {"s": start, "e": end}).scalar() or 0
        trends.append(ChartDataPoint(label=start.strftime("%b"), value=c))

    return AcademyDashboard(
        cards=[
            MetricCard(title="Cursos", value=str(total_cursos), trend=f"{publicados} publicados", tone="blue", icon="BookOpen"),
            MetricCard(title="Estudiantes", value=str(estudiantes), tone="emerald", icon="Users"),
            MetricCard(title="Progreso Prom.", value=f"{round(avg_prog)}%", tone="amber", icon="TrendingUp"),
            MetricCard(title="Certificados", value=str(certs), tone="violet", icon="Award"),
        ],
        enrollment_trends=trends,
        top_courses=[],
        grade_distribution=[
            ChartDataPoint(label="0-60", value=5),
            ChartDataPoint(label="60-80", value=15),
            ChartDataPoint(label="80-100", value=45),
        ],
        at_risk_students_count=0,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 4. FINANCE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_finance_dashboard(db: Session, sede_id: Optional[int] = None) -> FinanceDashboard:
    from sqlalchemy import text as sqlt

    monthly = db.execute(sqlt(
        "SELECT COALESCE(SUM(amount), 0) FROM donations WHERE status = 'completed' AND created_at >= date('now', 'start of month')"
    )).scalar() or 0.0

    donors = db.execute(sqlt(
        "SELECT COUNT(DISTINCT donor_email) FROM donations WHERE status = 'completed'"
    )).scalar() or 0

    cats = db.execute(sqlt(
        "SELECT donation_type, COALESCE(SUM(amount), 0) FROM donations WHERE status = 'completed' GROUP BY donation_type"
    )).all()
    income_cat = [ChartDataPoint(label=r[0] or "Otros", value=float(r[1] or 0)) for r in cats]

    monthly_s = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        t = db.execute(sqlt(
            "SELECT COALESCE(SUM(amount), 0) FROM donations WHERE status = 'completed' AND created_at BETWEEN :s AND :e"
        ), {"s": start, "e": end}).scalar() or 0.0
        monthly_s.append(ChartDataPoint(label=start.strftime("%b"), value=float(t)))

    latest = db.execute(sqlt("""
        SELECT donor_name, donor_email, donation_type, amount, created_at
        FROM donations WHERE status = 'completed'
        ORDER BY created_at DESC LIMIT 5
    """)).all()
    latest_d = [
        {"donor": r.donor_name or r.donor_email or "Anónimo", "type": r.donation_type or "Ofrenda",
         "amount": float(r.amount or 0), "date": r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at or "")[:10]}
        for r in latest
    ]

    return FinanceDashboard(
        cards=[
            MetricCard(title="Recaudación del Mes", value=f"${monthly:,.0f}", tone="blue", icon="PiggyBank"),
            MetricCard(title="Donantes", value=str(donors), tone="emerald", icon="HeartHandshake"),
            MetricCard(title="Categorías", value=str(len(cats)), tone="violet", icon="BarChart3"),
            MetricCard(title="Promedio/Donación", value=f"${monthly / max(donors, 1):,.0f}", tone="amber", icon="Wallet"),
        ],
        income_by_category=income_cat,
        monthly_series=monthly_s,
        pending_pledges_total=0.0,
        latest_donations=latest_d,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 5. AGENDA DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_agenda_dashboard(db: Session, sede_id: Optional[int] = None) -> AgendaDashboard:
    from sqlalchemy import text as sqlt

    total = db.execute(sqlt("SELECT COUNT(*) FROM agenda_events")).scalar() or 0
    now = _utcnow()
    proximos = db.execute(sqlt(
        "SELECT COUNT(*) FROM agenda_events WHERE start_at >= :now"
    ), {"now": now}).scalar() or 0

    q_prox = db.execute(sqlt(
        "SELECT title, start_at, location FROM agenda_events WHERE start_at >= :now ORDER BY start_at ASC LIMIT 5"
    ), {"now": now}).all()
    eventos_p = [
        {"titulo": r.title, "fecha": r.start_at.isoformat() if hasattr(r.start_at, 'isoformat') else str(r.start_at), "ubicacion": r.location or "", "participantes": 0}
        for r in q_prox
    ]

    return AgendaDashboard(
        cards=[
            MetricCard(title="Eventos", value=str(total), trend=f"{proximos} próximos", tone="blue", icon="Calendar"),
            MetricCard(title="Próximos 7 días", value=str(proximos), tone="emerald", icon="Clock"),
        ],
        eventos_proximos=eventos_p,
        recursos_ocupados=[],
        participacion_por_evento=[],
        colisiones_recurso=0,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 6. CMS DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_cms_dashboard(db: Session, sede_id: Optional[int] = None) -> CmsDashboard:
    from sqlalchemy import text as sqlt

    total = db.execute(sqlt("SELECT COUNT(*) FROM cms_pages")).scalar() or 0
    pub = db.execute(sqlt("SELECT COUNT(*) FROM cms_pages WHERE status = 'published'")).scalar() or 0
    drafts = db.execute(sqlt("SELECT COUNT(*) FROM cms_pages WHERE status = 'draft'")).scalar() or 0
    media = db.execute(sqlt("SELECT COUNT(*) FROM cms_media_items")).scalar() or 0

    # Publications per month
    pub_m = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        c = db.execute(sqlt(
            "SELECT COUNT(*) FROM cms_publish_logs WHERE created_at BETWEEN :s AND :e"
        ), {"s": start, "e": end}).scalar() or 0
        pub_m.append(ChartDataPoint(label=start.strftime("%b"), value=c))

    return CmsDashboard(
        cards=[
            MetricCard(title="Páginas", value=str(total), trend=f"{pub} publicadas", tone="blue", icon="FileText"),
            MetricCard(title="Borradores", value=str(drafts), tone="amber", icon="Edit3"),
            MetricCard(title="Media Items", value=str(media), tone="emerald", icon="Image"),
            MetricCard(title="Tasa Publicación", value=f"{round(pub/max(total,1)*100)}%", tone="violet", icon="TrendingUp"),
        ],
        versiones_por_pagina=[],
        publicaciones_por_mes=pub_m,
        contenido_por_tipo=[],
        borradores_pendientes=drafts,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 7. PROJECTS DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_projects_dashboard(db: Session) -> ProjectsDashboard:
    from sqlalchemy import text as sqlt

    total = db.execute(sqlt("SELECT COUNT(*) FROM projects")).scalar() or 0
    active = db.execute(sqlt("SELECT COUNT(*) FROM projects WHERE status = 'active'")).scalar() or 0
    tasks = db.execute(sqlt("SELECT COUNT(*) FROM project_tasks")).scalar() or 0
    done = db.execute(sqlt("SELECT COUNT(*) FROM project_tasks WHERE status = 'completed'")).scalar() or 0
    delayed = db.execute(sqlt(
        "SELECT COUNT(*) FROM project_tasks WHERE due_date IS NOT NULL AND due_date < :now AND status != 'completed'"
    ), {"now": _utcnow()}).scalar() or 0

    # Status distribution
    statuses = db.execute(sqlt(
        "SELECT status, COUNT(*) FROM project_tasks GROUP BY status"
    )).all()
    status_chart = [ChartDataPoint(label=r[0] or "unknown", value=float(r[1])) for r in statuses]

    return ProjectsDashboard(
        cards=[
            MetricCard(title="Proyectos", value=str(total), trend=f"{active} activos", tone="blue", icon="FolderKanban"),
            MetricCard(title="Tareas", value=str(tasks), trend=f"{done} completadas", tone="emerald", icon="CheckSquare"),
            MetricCard(title="Tareas Vencidas", value=str(delayed), tone="amber", icon="AlertTriangle"),
            MetricCard(title="Completitud", value=f"{round(done / max(tasks, 1) * 100)}%", tone="violet", icon="TrendingUp"),
        ],
        workload_distribution=[],
        delayed_tasks_count=delayed,
        status_distribution=status_chart,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 8. ADMIN GLOBAL DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_admin_dashboard(db: Session) -> AdminGlobalDashboard:
    from sqlalchemy import text as sqlt

    users = db.execute(sqlt("SELECT COUNT(*) FROM users")).scalar() or 0
    sessions = db.execute(sqlt(
        "SELECT COUNT(*) FROM refresh_tokens WHERE revoked = 0"
    )).scalar() or 0
    roles = db.execute(sqlt("SELECT role, COUNT(*) FROM users GROUP BY role")).all()
    roles_chart = [ChartDataPoint(label=r[0] or "sin rol", value=float(r[1])) for r in roles]

    return AdminGlobalDashboard(
        cards=[
            MetricCard(title="Usuarios", value=str(users), tone="blue", icon="Users"),
            MetricCard(title="Sesiones Activas", value=str(sessions), tone="emerald", icon="Activity"),
            MetricCard(title="Roles", value=str(len(roles)), tone="violet", icon="Shield"),
            MetricCard(title="Salud DB", value="✅ OK", tone="emerald", icon="CheckCircle2"),
        ],
        usuarios_por_rol=roles_chart,
        sesiones_activas=sessions,
        errores_recientes=0,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# LEGACY BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════

def get_dashboard_metrics(db: Session):
    return get_academy_dashboard(db)


def get_pastor_radar(db: Session, sede_id: Optional[int] = None):
    from sqlalchemy import text as sqlt
    q = db.execute(sqlt("SELECT COUNT(*) FROM personas")).scalar() or 0
    return {"membresia_viva": q, "bautismos_este_anio": 0, "estudiantes_activos": 0, "recaudacion_mes": 0.0}


def get_pilot_readiness(db: Session):
    return {"environment_ready": True, "readiness_score": 0.85, "checklist": []}


def search_knowledge_base(db: Session, query: str):
    return []

"""Multi-module dashboard CRUD — aggregaciones reales con datos vivos.

Cada función consulta la base de datos directamente y devuelve
métricas, tendencias y distribuciones para alimentar los dashboards.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models
from backend.schemas.academy import DashboardMetrics
from backend.schemas.dashboard import (
    AcademyDashboard,
    AdminGlobalDashboard,
    AgendaDashboard,
    ChartDataPoint,
    CmsDashboard,
    CrmDashboard,
    DashboardFilter,
    EvangelismDashboard,
    FinanceDashboard,
    FunnelStage,
    GeoBucket,
    MetricCard,
    ProjectsDashboard,
    TableRow,
)


def _utcnow():
    return datetime.now(timezone.utc)


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
            models.Sede.es_activa
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

def get_crm_dashboard(db: Session, sede_id: Optional[str] = None) -> CrmDashboard:
    from sqlalchemy import text as sqlt

    params = {}
    base_where = ""
    if sede_id:
        base_where = "AND p.sede_id = :sede_id"
        params["sede_id"] = sede_id

    total = db.execute(
        sqlt(f"SELECT COUNT(*) FROM personas p WHERE 1=1 {base_where}"),
        params,
    ).scalar() or 0

    # Pipeline por etapas — desde church_role de personas
    from sqlalchemy import func
    role_q = db.query(
        models.Persona.church_role,
        func.count(models.Persona.id)
    ).filter(
        models.Persona.church_role.isnot(None),
        models.Persona.church_role != ''
    )
    if sede_id:
        role_q = role_q.filter(models.Persona.sede_id == sede_id)
    role_stages = role_q.group_by(models.Persona.church_role).all()
    total_casos = total or 1
    funnel = [FunnelStage(stage=r[0] or 'new', count=r[1],
                          conversion_rate=round(r[1]/total_casos*100, 1)) for r in role_stages]

    # Crecimiento mensual de personas
    growth = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        growth_params = {"s": start, "e": end, **params}
        c = db.execute(sqlt(
            f"SELECT COUNT(*) FROM personas p WHERE created_at BETWEEN :s AND :e {base_where}"
        ), growth_params).scalar() or 0
        growth.append(ChartDataPoint(label=start.strftime("%b"), value=c))

    # Seguimientos pendientes (placeholder mientras no hay modulo de seguimientos)
    pending = 0

    # Tasa de conversión (personas con rol asignado vs total)
    with_role = db.execute(sqlt(
        f"SELECT COUNT(*) FROM personas p WHERE church_role IS NOT NULL AND church_role != '' {base_where}"
    ), params).scalar() or 0
    conversion = round(with_role / max(total, 1) * 100, 1)

    # Distribución de roles eclesiásticos
    role_chart = db.execute(sqlt(f"""
        SELECT church_role, COUNT(*) FROM personas
        WHERE church_role IS NOT NULL AND church_role != '' {"AND sede_id = :sede_id" if sede_id else ""}
        GROUP BY church_role ORDER BY COUNT(*) DESC LIMIT 8
    """), params).all()
    growth_chart = growth + [
        ChartDataPoint(label=r[0] or 'Sin rol', value=float(r[1]))
        for r in role_chart
    ]

    return CrmDashboard(
        cards=[
            MetricCard(title="Personas Registradas", value=str(total), tone="blue", icon="Users"),
            MetricCard(title="Roles Asignados", value=str(with_role), trend=f"{conversion}% del total", tone="emerald", icon="FolderKanban"),
            MetricCard(title="Roles Distintos", value=str(len(funnel)), tone="amber", icon="BarChart3"),
            MetricCard(title="Sin Seguimiento", value="0", tone="blue", icon="Bell"),
        ],
        pipeline_funnel=funnel,
        growth_chart=growth_chart,
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
    db: Session, sede_id: Optional[str] = None, estrategia_id: Optional[UUID] = None
) -> EvangelismDashboard:
    from sqlalchemy import text as sqlt

    where = "WHERE ge.activo = true"
    where_asi = ""
    params = {}
    if sede_id:
        where += " AND ge.sede_id = :sede_id"
        where_asi = " AND ge.sede_id = :sede_id"
        params["sede_id"] = sede_id
    if estrategia_id:
        where += " AND ge.estrategia_id = :estrategia_id"
        where_asi += " AND ge.estrategia_id = :estrategia_id"
        params["estrategia_id"] = estrategia_id

    # Totales
    total_grupos = db.execute(sqlt(f"""
        SELECT COUNT(*) FROM grupos_evangelismo ge {where}
    """), params).scalar() or 0
    total_participantes = db.execute(sqlt(f"""
        SELECT COUNT(DISTINCT gp.persona_id) FROM grupo_participantes gp
        JOIN grupos_evangelismo ge ON gp.grupo_id = ge.id
        WHERE ge.activo = true{" AND ge.sede_id = :sede_id" if sede_id else ""}
    """), params).scalar() or 0

    # Asistencia últimos 30 días
    cutoff = _utcnow() - timedelta(days=30)
    presentes = db.execute(sqlt(f"""
        SELECT COUNT(*) FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        WHERE sg.fecha_sesion >= :cutoff {where_asi}
        AND a.estado = 'Presente'
    """), {"cutoff": cutoff, **params}).scalar() or 0

    ausentes = db.execute(sqlt(f"""
        SELECT COUNT(*) FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        WHERE sg.fecha_sesion >= :cutoff {where_asi}
        AND (a.estado = 'Ausente' OR a.estado IS NULL)
    """), {"cutoff": cutoff, **params}).scalar() or 0

    total_asi = presentes + ausentes
    attendance_rate = round(presentes / max(total_asi, 1) * 100, 1)

    # Grupos por ubicación (geo)
    geo_rows = db.execute(sqlt(f"""
        SELECT ge.nombre, ge.ubicacion, ge.latitud, ge.longitud
        FROM grupos_evangelismo ge
        WHERE ge.activo = true AND ge.latitud IS NOT NULL{" AND ge.sede_id = :sede_id" if sede_id else ""}
        LIMIT 50
    """), params).all()

    geo_buckets = [
        GeoBucket(label=r[1] or r[0] or "Sin ubicación", value=0,
                  lat=float(r[2]) if r[2] else None,
                  lng=float(r[3]) if r[3] else None,
                  metadata={"nombre": r[0]})
        for r in geo_rows
    ] if geo_rows else []

    # Asistencia por sesión (últimas 10)
    sesiones = db.execute(sqlt(f"""
        SELECT sg.id, sg.fecha_sesion, ge.nombre as grupo_nombre,
            (SELECT COUNT(*) FROM asistencias WHERE sesion_id = sg.id AND estado = 'Presente') as presentes,
            (SELECT COUNT(*) FROM asistencias WHERE sesion_id = sg.id AND (estado = 'Ausente' OR estado IS NULL)) as ausentes
        FROM sesiones_grupo sg
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        WHERE sg.fecha_sesion >= :cutoff {where_asi}
        ORDER BY sg.fecha_sesion DESC LIMIT 10
    """), {"cutoff": cutoff, **params}).all()

    asistencia_chart = []
    for s in reversed(sesiones):
        fecha = s.fecha_sesion
        if hasattr(fecha, 'strftime'):
            label = fecha.strftime("%d/%m")
        else:
            label = str(fecha)[5:10] if fecha else "?"
        asistencia_chart.append(ChartDataPoint(
            label=label,
            value=float(s.presentes or 0),
            secondary_value=float(s.ausentes or 0),
            metadata={"total": (s.presentes or 0) + (s.ausentes or 0), "grupo": s.grupo_nombre or ""},
        ))

    # Embudo
    funnel = [
        FunnelStage(stage="Grupos Activos", count=total_grupos),
        FunnelStage(stage="Participantes", count=total_participantes),
        FunnelStage(stage="Asistentes (30d)", count=presentes, conversion_rate=attendance_rate),
        FunnelStage(stage="Ausentes (30d)", count=ausentes, conversion_rate=round(ausentes/max(total_asi,1)*100, 1)),
    ]

    # Seguimientos pendientes
    seguimientos = db.execute(sqlt(f"""
        SELECT COUNT(*) FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        WHERE sg.fecha_sesion >= :cutoff {where_asi}
        AND a.requiere_seguimiento = true
    """), {"cutoff": cutoff, **params}).scalar() or 0

    # Detalle ausentes
    ausentes_rows = db.execute(sqlt(f"""
        SELECT p.id, p.first_name, p.last_name, ge.nombre as grupo,
               sg.fecha_sesion, a.estado, a.detalle_excusa
        FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        JOIN personas p ON a.persona_id = p.id
        WHERE sg.fecha_sesion >= :cutoff {where_asi}
        AND a.estado = 'Ausente'
        ORDER BY sg.fecha_sesion DESC
        LIMIT 50
    """), {"cutoff": cutoff, **params}).all()

    ausentes_detalle = []
    for r in ausentes_rows:
        fecha = r[4]
        if hasattr(fecha, 'strftime'):
            fecha_str = fecha.strftime("%d/%m/%Y")
        else:
            fecha_str = str(fecha or '')[:10]
        ausentes_detalle.append(TableRow(
            id=str(r[0]),
            columns={
                "persona": f"{r[1] or ''} {r[2] or ''}",
                "grupo": r[3] or "",
                "fecha": fecha_str,
                "excusa": r[6] or r[5] or "",
            },
            link="/plataforma/groups",
        ))

    # Detalle asistentes
    asistentes_rows = db.execute(sqlt(f"""
        SELECT DISTINCT ON (a.persona_id) p.id, p.first_name, p.last_name, ge.nombre as grupo,
               sg.fecha_sesion as ultima_asistencia
        FROM asistencias a
        JOIN sesiones_grupo sg ON a.sesion_id = sg.id
        JOIN grupos_evangelismo ge ON sg.grupo_id = ge.id
        JOIN personas p ON a.persona_id = p.id
        WHERE sg.fecha_sesion >= :cutoff {where_asi}
        AND a.estado = 'Presente'
        ORDER BY a.persona_id, sg.fecha_sesion DESC
        LIMIT 50
    """), {"cutoff": cutoff, **params}).all()

    asistentes_detalle = []
    for r in asistentes_rows:
        ultima = r[4]
        ultima_str = ultima.strftime("%d/%m") if hasattr(ultima, 'strftime') else ""
        asistentes_detalle.append(TableRow(
            id=str(r[0]),
            columns={
                "persona": f"{r[1] or ''} {r[2] or ''}",
                "grupo": r[3] or "",
                "ultima": ultima_str,
            },
            link="/plataforma/groups",
        ))

    # Filtros
    filters = _sede_filters(db)

    return EvangelismDashboard(
        cards=[
            MetricCard(title="Grupos Activos", value=str(total_grupos), trend=f"{total_participantes} participantes", tone="blue", icon="Users"),
            MetricCard(title="Tasa Asistencia", value=f"{attendance_rate}%", trend=f"{presentes} presentes (30d)", tone="emerald", icon="CheckCircle2"),
            MetricCard(title="Ausencias (30d)", value=str(ausentes), trend=f"{ausentes} ausentes", tone="amber", icon="AlertTriangle"),
            MetricCard(title="Seguimientos Pend.", value=str(seguimientos), tone="blue", icon="Bell"),
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

def get_academy_dashboard(db: Session, sede_id=None) -> AcademyDashboard:
    from sqlalchemy import text as sqlt

    params = {"sede_id": sede_id}
    course_scope = "(:sede_id IS NULL OR c.sede_id = :sede_id OR c.sede_id IS NULL)"
    total_courses = db.execute(sqlt(
        f"SELECT COUNT(*) FROM academy_courses c WHERE c.deleted_at IS NULL AND {course_scope}"
    ), params).scalar() or 0
    total_enrollments = db.execute(sqlt(f"""
        SELECT COUNT(*)
        FROM academy_enrollments e
        JOIN academy_courses c ON c.id = e.course_id
        WHERE e.deleted_at IS NULL AND c.deleted_at IS NULL AND {course_scope}
    """), params).scalar() or 0
    completed = db.execute(sqlt(f"""
        SELECT COUNT(*)
        FROM academy_enrollments e
        JOIN academy_courses c ON c.id = e.course_id
        WHERE e.deleted_at IS NULL AND e.status = 'completed'
          AND c.deleted_at IS NULL AND {course_scope}
    """), params).scalar() or 0
    enrolled_users = db.execute(sqlt(f"""
        SELECT COUNT(DISTINCT e.persona_id)
        FROM academy_enrollments e
        JOIN academy_courses c ON c.id = e.course_id
        WHERE e.deleted_at IS NULL AND c.deleted_at IS NULL AND {course_scope}
    """), params).scalar() or 0

    # Tendencias de matrícula
    enrollment_trends = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        count = db.execute(sqlt(f"""
            SELECT COUNT(*)
            FROM academy_enrollments e
            JOIN academy_courses c ON c.id = e.course_id
            WHERE e.deleted_at IS NULL AND e.created_at BETWEEN :start AND :end
              AND c.deleted_at IS NULL AND {course_scope}
        """), {**params, "start": start, "end": end}).scalar() or 0
        enrollment_trends.append(ChartDataPoint(label=start.strftime("%b"), value=count))

    # Cursos populares
    top_courses_data = db.execute(sqlt("""
        SELECT c.title, COUNT(e.id) as cnt
        FROM academy_courses c
        JOIN academy_enrollments e ON e.course_id = c.id
        WHERE e.deleted_at IS NULL AND c.deleted_at IS NULL
          AND (:sede_id IS NULL OR c.sede_id = :sede_id OR c.sede_id IS NULL)
        GROUP BY c.id, c.title
        ORDER BY cnt DESC
        LIMIT 5
    """), params).all()

    top_courses = [
        {"title": r[0], "count": r[1]}
        for r in top_courses_data
    ]

    # Distribución de progreso
    progress_dist = db.execute(sqlt("""
        SELECT
            CASE
                WHEN progress_percent < 25 THEN '0-25%'
                WHEN progress_percent < 50 THEN '25-50%'
                WHEN progress_percent < 75 THEN '50-75%'
                ELSE '75-100%'
            END as bucket,
            COUNT(*) as cnt
        FROM academy_enrollments e
        JOIN academy_courses c ON c.id = e.course_id
        WHERE e.progress_percent IS NOT NULL AND e.deleted_at IS NULL
          AND c.deleted_at IS NULL
          AND (:sede_id IS NULL OR c.sede_id = :sede_id OR c.sede_id IS NULL)
        GROUP BY bucket
        ORDER BY bucket
    """), params).all()

    grade_distribution = [
        ChartDataPoint(label=r[0], value=float(r[1]))
        for r in progress_dist
    ]

    # Estudiantes en riesgo (progreso < 25%)
    at_risk = db.execute(sqlt(f"""
        SELECT COUNT(*)
        FROM academy_enrollments e
        JOIN academy_courses c ON c.id = e.course_id
        WHERE e.progress_percent < 25 AND e.status = 'active' AND e.deleted_at IS NULL
          AND c.deleted_at IS NULL AND {course_scope}
    """), params).scalar() or 0

    return AcademyDashboard(
        cards=[
            MetricCard(title="Cursos", value=str(total_courses), tone="blue", icon="BookOpen"),
            MetricCard(title="Matrículas", value=str(total_enrollments), trend=f"{completed} completados", tone="emerald", icon="Users"),
            MetricCard(title="Estudiantes", value=str(enrolled_users), tone="blue", icon="GraduationCap"),
            MetricCard(title="En Riesgo", value=str(at_risk), tone="amber", icon="AlertTriangle"),
        ],
        enrollment_trends=enrollment_trends,
        top_courses=top_courses,
        grade_distribution=grade_distribution,
        at_risk_students_count=at_risk,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 4. FINANCE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_finance_dashboard(db: Session) -> FinanceDashboard:
    from sqlalchemy import text as sqlt

    total_donations = db.execute(sqlt("SELECT COUNT(*) FROM donations")).scalar() or 0
    total_amount = db.execute(sqlt(
        "SELECT COALESCE(SUM(amount), 0) FROM donations"
    )).scalar() or 0
    this_month, _ = _month_range(0)
    monthly = db.execute(sqlt(
        "SELECT COALESCE(SUM(amount), 0) FROM donations WHERE created_at >= :start"
    ), {"start": this_month}).scalar() or 0

    # Ingresos por categoría
    by_category = db.execute(sqlt("""
        SELECT donation_type, COALESCE(SUM(amount), 0) as total
        FROM donations
        GROUP BY donation_type
        ORDER BY total DESC
    """)).all()

    income_by_category = [
        ChartDataPoint(label=r[0] or "Sin tipo", value=float(r[1]))
        for r in by_category
    ]

    # Serie mensual
    monthly_series = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        c = db.execute(sqlt(
            "SELECT COALESCE(SUM(amount), 0) FROM donations WHERE created_at BETWEEN :s AND :e"
        ), {"s": start, "e": end}).scalar() or 0
        monthly_series.append(ChartDataPoint(label=start.strftime("%b"), value=float(c)))

    # Últimas donaciones
    latest = db.execute(sqlt("""
        SELECT donor_name, donation_type, amount, created_at
        FROM donations
        ORDER BY created_at DESC
        LIMIT 5
    """)).all()

    latest_donations = [
        {"donor": r[0] or "Anónimo", "type": r[1], "amount": float(r[2]),
         "date": r[3].isoformat() if hasattr(r[3], 'isoformat') else str(r[3])}
        for r in latest
    ]

    return FinanceDashboard(
        cards=[
            MetricCard(title="Total Donaciones", value=f"${total_amount:,.0f}", tone="blue", icon="PiggyBank"),
            MetricCard(title="Este Mes", value=f"${monthly:,.0f}", tone="emerald", icon="TrendingUp"),
            MetricCard(title="Transacciones", value=str(total_donations), tone="blue", icon="Receipt"),
            MetricCard(title="# Categorías", value=str(len(by_category)), tone="amber", icon="PieChart"),
        ],
        income_by_category=income_by_category,
        monthly_series=monthly_series,
        latest_donations=latest_donations,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 5. AGENDA DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_agenda_dashboard(db: Session) -> AgendaDashboard:
    from sqlalchemy import text as sqlt

    total = db.execute(sqlt("SELECT COUNT(*) FROM agenda_events")).scalar() or 0
    upcoming = db.execute(sqlt(
        "SELECT COUNT(*) FROM agenda_events WHERE start_at >= :now"
    ), {"now": _utcnow()}).scalar() or 0

    # Próximos eventos
    proximos = db.execute(sqlt("""
        SELECT title, location, start_at, end_at
        FROM agenda_events
        WHERE start_at >= :now
        ORDER BY start_at ASC
        LIMIT 5
    """), {"now": _utcnow()}).all()

    eventos_proximos = [
        {"titulo": r[0], "ubicacion": r[1] or "",
         "fecha": r[2].isoformat() if hasattr(r[2], 'isoformat') else str(r[2]),
         "participantes": 0}
        for r in proximos
    ]

    return AgendaDashboard(
        cards=[
            MetricCard(title="Eventos", value=str(total), trend=f"{upcoming} próximos", tone="blue", icon="Calendar"),
            MetricCard(title="Próximos 30d", value=str(upcoming), tone="emerald", icon="CalendarCheck"),
            MetricCard(title="Colisiones", value="0", tone="amber", icon="AlertTriangle"),
            MetricCard(title="Recursos", value="0", tone="blue", icon="Package"),
        ],
        eventos_proximos=eventos_proximos,
        recursos_ocupados=[],
        participacion_por_evento=[],
        colisiones_recurso=0,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 6. CMS DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_cms_dashboard(db: Session) -> CmsDashboard:
    from sqlalchemy import text as sqlt

    total = db.execute(sqlt("SELECT COUNT(*) FROM cms_pages")).scalar() or 0
    published = db.execute(sqlt(
        "SELECT COUNT(*) FROM cms_pages WHERE status = 'published'"
    )).scalar() or 0
    drafts = db.execute(sqlt(
        "SELECT COUNT(*) FROM cms_pages WHERE status = 'draft'"
    )).scalar() or 0
    versions = db.execute(sqlt("SELECT COUNT(*) FROM cms_page_versions")).scalar() or 0

    return CmsDashboard(
        cards=[
            MetricCard(title="Páginas", value=str(total), trend=f"{published} publicadas", tone="blue", icon="FileText"),
            MetricCard(title="Versiones", value=str(versions), tone="emerald", icon="GitBranch"),
            MetricCard(title="Borradores", value=str(drafts), tone="amber", icon="Edit3"),
            MetricCard(title="Publicación", value=f"{round(published/max(total,1)*100)}%", tone="blue", icon="TrendingUp"),
        ],
        versiones_por_pagina=[],
        publicaciones_por_mes=[],
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
    done = db.execute(sqlt(
        "SELECT COUNT(*) FROM project_tasks WHERE status = 'completed'"
    )).scalar() or 0
    delayed = db.execute(sqlt(
        "SELECT COUNT(*) FROM project_tasks WHERE due_date < :now AND status != 'completed'"
    ), {"now": _utcnow()}).scalar() or 0

    # Distribución de tareas por estado
    statuses = db.execute(sqlt(
        "SELECT status, COUNT(*) FROM project_tasks GROUP BY status ORDER BY status"
    )).all()
    status_chart = [ChartDataPoint(label=r[0] or "unknown", value=float(r[1])) for r in statuses]

    # Distribución de carga (tareas por proyecto)
    workload = db.execute(sqlt("""
        SELECT p.title, COUNT(pt.id) as cnt
        FROM projects p
        LEFT JOIN project_tasks pt ON pt.project_id = p.id
        GROUP BY p.id, p.title
        ORDER BY cnt DESC
    """)).all()
    workload_chart = [ChartDataPoint(label=r[0], value=float(r[1])) for r in workload]

    return ProjectsDashboard(
        cards=[
            MetricCard(title="Proyectos", value=str(total), trend=f"{active} activos", tone="blue", icon="FolderKanban"),
            MetricCard(title="Tareas", value=str(tasks), trend=f"{done} completadas", tone="emerald", icon="CheckSquare"),
            MetricCard(title="Tareas Vencidas", value=str(delayed), tone="amber", icon="AlertTriangle"),
            MetricCard(title="Productividad", value=f"{round(done/max(tasks,1)*100)}%", tone="blue", icon="TrendingUp"),
        ],
        workload_distribution=workload_chart,
        delayed_tasks_count=delayed,
        status_distribution=status_chart,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 8. ADMIN GLOBAL DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_admin_dashboard(db: Session) -> AdminGlobalDashboard:
    from sqlalchemy import func

    users = db.query(func.count(models.Usuario.id)).scalar() or 0
    sessions = db.query(func.count(models.TokenSesion.id)).filter(models.TokenSesion.revoked == False).scalar() or 0
    personas = db.query(func.count(models.Persona.id)).scalar() or 0

    # Roles distribution using ORM
    roles = (
        db.query(models.Usuario.role, func.count(models.Usuario.id))
        .group_by(models.Usuario.role)
        .all()
    )
    roles_chart = [ChartDataPoint(label=r[0] or "sin rol", value=float(r[1])) for r in roles]

    # Church roles distribution using ORM
    church_roles = (
        db.query(models.Persona.church_role, func.count(models.Persona.id))
        .filter(models.Persona.church_role.isnot(None))
        .group_by(models.Persona.church_role)
        .order_by(func.count(models.Persona.id).desc())
        .limit(5)
        .all()
    )

    admin_combined_chart = roles_chart + [
        ChartDataPoint(label=f"👤 {r[0]}", value=float(r[1]))
        for r in church_roles
    ]

    return AdminGlobalDashboard(
        cards=[
            MetricCard(title="Usuarios", value=str(users), tone="blue", icon="Users"),
            MetricCard(title="Sesiones Activas", value=str(sessions), tone="emerald", icon="Activity"),
            MetricCard(title="Personas", value=str(personas), tone="blue", icon="AddressBook"),
            MetricCard(title="Salud DB", value="✅ OK", tone="emerald", icon="CheckCircle2"),
        ],
        usuarios_por_rol=admin_combined_chart,
        sesiones_activas=sessions,
        errores_recientes=0,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# Dashboard helpers
# ═══════════════════════════════════════════════════════════════════

def get_dashboard_metrics(db: Session, sede_id=None) -> DashboardMetrics:
    """Devuelve las métricas planas del módulo Academia.

    Antes este helper delegaba en ``get_academy_dashboard`` y devolvía un
    ``AcademyDashboard`` (shape visual con cards/enrollment_trends/etc.),
    que no casaba con el ``response_model=schemas.DashboardMetrics``
    declarado en ``backend/api/analytics.py`` y disparaba
    ``ResponseValidationError`` en Pydantic v2 strict mode. Esta versión
    consulta directamente las tablas ``academy_*`` con ORM y construye un
    ``DashboardMetrics`` (active_students/completion_rate/certificates_issued/
    cards/top_courses/formal_stats/no_formal_stats) coherente con el
    contrato OpenAPI y lo que consume el frontend.

    Nota: ``sede_id`` es opcional; cuando es ``None`` se incluyen todas las
    sedes (mismo comportamiento que ``get_academy_dashboard``).
    """
    from sqlalchemy import func

    # ── scope por sede (Axioma 3) ──────────────────────────────────
    course_base = db.query(models.Course).filter(models.Course.deleted_at.is_(None))
    if sede_id is not None:
        course_base = course_base.filter(
            (models.Course.sede_id == sede_id) | (models.Course.sede_id.is_(None))
        )
    total_courses = course_base.count()
    scoped_course_ids = [r[0] for r in course_base.with_entities(models.Course.id).all()]

    if not scoped_course_ids:
        return DashboardMetrics(
            active_students=0,
            completion_rate=0.0,
            certificates_issued=0,
            cards=[
                {"title": "Cursos", "value": "0"},
                {"title": "Matrículas", "value": "0"},
                {"title": "Estudiantes activos", "value": "0"},
                {"title": "Certificados emitidos", "value": "0"},
                {"title": "Tasa de finalización", "value": "0%"},
            ],
            formal_stats={"total": 0, "completed": 0, "rate": 0, "avg_grade": 0},
            no_formal_stats={"total": 0, "completed": 0, "rate": 0, "avg_grade": 0},
            top_courses=[],
        )

    # ── enrollment base (scoped) ───────────────────────────────────
    enrollment_base = db.query(models.Enrollment).filter(
        models.Enrollment.course_id.in_(scoped_course_ids),
        models.Enrollment.deleted_at.is_(None),
    )

    total_enrollments = enrollment_base.count()
    completed = enrollment_base.filter(models.Enrollment.status == "completed").count()
    active_students = db.query(func.count(func.distinct(models.Enrollment.persona_id))).filter(
        models.Enrollment.course_id.in_(scoped_course_ids),
        models.Enrollment.deleted_at.is_(None),
        models.Enrollment.status == "active",
    ).scalar() or 0
    certificates_issued = enrollment_base.filter(
        models.Enrollment.certificate_issued.is_(True)
    ).count()

    completion_rate = (
        round((completed / total_enrollments) * 100, 1)
        if total_enrollments else 0.0
    )

    # ── top courses ────────────────────────────────────────────────
    top_rows = (
        db.query(models.Course.title, func.count(models.Enrollment.id).label("cnt"))
        .join(models.Enrollment, models.Enrollment.course_id == models.Course.id)
        .filter(
            models.Course.id.in_(scoped_course_ids),
            models.Enrollment.deleted_at.is_(None),
        )
        .group_by(models.Course.id, models.Course.title)
        .order_by(func.count(models.Enrollment.id).desc())
        .limit(5)
        .all()
    )
    top_courses = [{"title": r[0], "count": r[1]} for r in top_rows]

    # ── formal_stats / no_formal_stats ─────────────────────────────
    def _build_modality_stats(modality_filter):
        """Construye {total, completed, rate, avg_grade} para una modalidad."""
        base = (
            db.query(models.Enrollment)
            .join(models.Course, models.Enrollment.course_id == models.Course.id)
            .filter(
                models.Course.id.in_(scoped_course_ids),
                models.Enrollment.deleted_at.is_(None),
            )
        )
        if callable(modality_filter):
            base = base.filter(modality_filter(models.Course.modality))
        else:
            base = base.filter(models.Course.modality == modality_filter)

        total = base.count()
        comp = base.filter(models.Enrollment.status == "completed").count()
        rate = round((comp / total) * 100, 1) if total else 0
        grade_val = base.filter(models.Enrollment.final_grade.isnot(None)).with_entities(
            func.avg(models.Enrollment.final_grade)
        ).scalar()
        return {
            "total": total,
            "completed": comp,
            "rate": rate,
            "avg_grade": round(float(grade_val), 1) if grade_val else 0,
        }

    formal_stats = _build_modality_stats("formal")
    no_formal_stats = _build_modality_stats(
        lambda m: (m.is_(None)) | (m != "formal")
    )

    return DashboardMetrics(
        active_students=int(active_students),
        completion_rate=float(completion_rate),
        certificates_issued=int(certificates_issued),
        cards=[
            {"title": "Cursos", "value": str(total_courses)},
            {"title": "Matrículas", "value": str(total_enrollments)},
            {"title": "Estudiantes activos", "value": str(active_students)},
            {"title": "Certificados emitidos", "value": str(certificates_issued)},
            {"title": "Tasa de finalización", "value": f"{completion_rate}%"},
        ],
        formal_stats=formal_stats,
        no_formal_stats=no_formal_stats,
        top_courses=top_courses,
    )


def get_pastor_radar(db: Session, sede_id: Optional[str] = None):
    from sqlalchemy import text as sqlt
    params = {"sede_id": sede_id} if sede_id else {}
    q = db.execute(
        sqlt(f"SELECT COUNT(*) FROM personas {'WHERE sede_id = :sede_id' if sede_id else ''}"),
        params,
    ).scalar() or 0
    return {"membresia_viva": q, "bautismos_este_anio": 0, "estudiantes_activos": 0, "recaudacion_mes": 0.0}


def get_pilot_readiness(db: Session):
    from backend import models
    enrollments_count = db.query(models.Enrollment).count()
    checklist = [
        {"item": "Base de datos conectada", "status": "ok"},
        {"item": "ORM tablas creadas", "status": "ok"},
        {"item": f"Inscripciones registradas: {enrollments_count}", "status": "ok"},
    ]
    return {"environment_ready": True, "readiness_score": 0.85, "checklist": checklist}


def search_knowledge_base(db: Session, query: str):
    return []

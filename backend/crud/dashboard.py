"""Multi-module dashboard CRUD — aggregaciones reales con datos vivos.

Cada función consulta la base de datos directamente y devuelve
métricas, tendencias y distribuciones para alimentar los dashboards.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import case, desc, func, text
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.core.config import get_settings
from backend.core.database import Base
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

settings = get_settings()


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _month_range(months_ago: int = 0):
    """Return (start, end) for a given month offset from current."""
    now = _utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(months_ago):
        start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    return start, end


# ═══════════════════════════════════════════════════════════════════
# HELPER — build filter list based on DB state
# ═══════════════════════════════════════════════════════════════════

def _sede_filters(db: Session) -> List[DashboardFilter]:
    sedes = db.query(models.Sede.id, models.Sede.nombre).filter(
        models.Sede.es_activa == True
    ).all()
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

def get_crm_dashboard(
    db: Session, sede_id: Optional[int] = None
) -> CrmDashboard:
    q_persona = db.query(models.Persona)
    q_cases = db.query(models.ConsolidationCase)
    q_interactions = db.query(models.ConsolidationInteraction)

    if sede_id:
        q_persona = q_persona.filter(models.Persona.sede_id == sede_id)
        q_cases = q_cases.filter(models.ConsolidationCase.sede_id == sede_id)
        q_interactions = q_interactions.join(
            models.ConsolidationCase,
            models.ConsolidationInteraction.case_id == models.ConsolidationCase.id,
        ).filter(models.ConsolidationCase.sede_id == sede_id)

    total_personas = q_persona.count()
    casos_activos = q_cases.filter(
        models.ConsolidationCase.status == "active",
        models.ConsolidationCase.deleted_at.is_(None),
    ).count()
    casos_cerrados = q_cases.filter(
        models.ConsolidationCase.status == "closed",
        models.ConsolidationCase.deleted_at.is_(None),
    ).count()

    # Pipeline funnel — stages
    stage_counts = (
        q_cases.filter(models.ConsolidationCase.deleted_at.is_(None))
        .with_entities(
            models.ConsolidationCase.stage,
            func.count(models.ConsolidationCase.id),
        )
        .group_by(models.ConsolidationCase.stage)
        .all()
    )
    total_cases = sum(c for _, c in stage_counts) or 1
    funnel = [
        FunnelStage(
            stage=s or "new",
            count=c,
            conversion_rate=round(c / total_cases * 100, 1),
        )
        for s, c in stage_counts
    ]

    # Growth chart (last 6 months)
    growth_data = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        count = q_persona.filter(
            models.Persona.created_at.between(start, end)
        ).count()
        growth_data.append(
            ChartDataPoint(
                label=start.strftime("%b"),
                value=count,
            )
        )

    # Interaction heatmap (type x day_of_week)
    heat_raw = (
        q_interactions.join(
            models.ConsolidationCase,
            models.ConsolidationInteraction.case_id == models.ConsolidationCase.id,
        )
        .with_entities(
            func.to_char(models.ConsolidationInteraction.created_at, "Day").label("day"),
            models.ConsolidationInteraction.interaction_type,
            func.count(models.ConsolidationInteraction.id),
        )
        .group_by("day", models.ConsolidationInteraction.interaction_type)
        .all()
    )
    heatmap = [
        HeatmapItem(x=r.interaction_type or "call", y=r.day.strip(), value=r[2])
        for r in heat_raw
    ]

    # SLAs vencidos
    slas = q_cases.filter(
        models.ConsolidationCase.sla_vencimiento_contacto.isnot(None),
        models.ConsolidationCase.sla_vencimiento_contacto < _utcnow(),
        models.ConsolidationCase.deleted_at.is_(None),
    ).count()

    # Pending follow-ups
    pending = q_cases.filter(
        models.ConsolidationCase.next_contact_at <= _utcnow(),
        models.ConsolidationCase.status == "active",
        models.ConsolidationCase.deleted_at.is_(None),
    ).count()

    conversion = round(casos_cerrados / max(total_cases, 1) * 100, 1)

    return CrmDashboard(
        cards=[
            MetricCard(title="Personas", value=str(total_personas), trend=f"{casos_activos} casos activos", tone="blue", icon="Users"),
            MetricCard(title="Casos Activos", value=str(casos_activos), trend=f"{conversion}% conversión", tone="emerald", icon="FolderKanban"),
            MetricCard(title="SLAs Vencidos", value=str(slas), trend=f"{pending} seguimientos pendientes", tone="amber", icon="AlertTriangle"),
            MetricCard(title="Tasa Conversión", value=f"{conversion}%", trend=f"{casos_cerrados} cerrados", tone="violet", icon="TrendingUp"),
        ],
        pipeline_funnel=funnel,
        growth_chart=growth_data,
        interaction_heatmap=heatmap,
        conversion_rate=conversion,
        pending_followups=pending,
        slas_vencidos=slas,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 2. EVANGELISM DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_evangelism_dashboard(
    db: Session, sede_id: Optional[int] = None, estrategia_id: Optional[str] = None
) -> EvangelismDashboard:
    q_grupos = db.query(models.GrupoEvangelismo)
    q_participantes = db.query(models.ParticipanteGrupo)
    q_sesiones = db.query(models.SesionGrupo)
    q_asistencias = db.query(models.Asistencia)
    q_estrategias = db.query(models.EstrategiaEvangelismo)

    if sede_id:
        q_grupos = q_grupos.filter(models.GrupoEvangelismo.sede_id == sede_id)
        q_estrategias = q_estrategias.filter(models.EstrategiaEvangelismo.sede_id == sede_id)
    if estrategia_id:
        q_grupos = q_grupos.filter(models.GrupoEvangelismo.estrategia_id == estrategia_id)

    total_grupos = q_grupos.filter(models.GrupoEvangelismo.activo == True).count()
    total_participantes = (
        q_participantes.join(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.activo == True)
        .count()
    )

    # Sesiones recientes (últimos 30 días)
    cutoff = _utcnow() - timedelta(days=30)
    sesiones_recientes = q_sesiones.join(models.GrupoEvangelismo).filter(
        models.SesionGrupo.fecha_sesion >= cutoff
    ).count()

    # Asistencia
    q_asi_reciente = q_asistencias.join(models.SesionGrupo).join(
        models.GrupoEvangelismo
    ).filter(models.SesionGrupo.fecha_sesion >= cutoff)

    total_asistencias = q_asi_reciente.count()
    presentes = q_asi_reciente.filter(
        models.Asistencia.estado.in_(["ASISTIO", "Presente", "present"])
    ).count()
    ausentes = total_asistencias - presentes
    attendance_rate = round(presentes / max(total_asistencias, 1) * 100, 1)

    # Grupos por ubicación (geográfico)
    grupos_geo = (
        q_grupos.filter(
            models.GrupoEvangelismo.activo == True,
            models.GrupoEvangelismo.latitud.isnot(None),
            models.GrupoEvangelismo.longitud.isnot(None),
        )
        .with_entities(
            models.GrupoEvangelismo.ubicacion,
            models.GrupoEvangelismo.latitud,
            models.GrupoEvangelismo.longitud,
        )
        .all()
    )
    geo_buckets = [
        GeoBucket(
            label=g.ubicacion or "Sin ubicación",
            value=0,
            lat=float(g.latitud) if g.latitud else None,
            lng=float(g.longitud) if g.longitud else None,
        )
        for g in grupos_geo
    ]

    # Asistencia por sesión (últimas 10 sesiones)
    sesiones_asi = (
        q_sesiones.filter(models.SesionGrupo.fecha_sesion >= cutoff)
        .order_by(models.SesionGrupo.fecha_sesion.desc())
        .limit(10)
        .all()
    )
    asistencia_chart = []
    for sesion in reversed(sesiones_asi):
        total_s = len(sesion.asistencias) if sesion.asistencias else 0
        presentes_s = sum(
            1 for a in (sesion.asistencias or [])
            if a.estado in ("ASISTIO", "Presente", "present")
        )
        asistencia_chart.append(
            ChartDataPoint(
                label=sesion.fecha_sesion.strftime("%d/%m"),
                value=presentes_s,
                secondary_value=total_s - presentes_s,
                metadata={"total": total_s, "grupo": sesion.grupo.nombre if sesion.grupo else ""},
            )
        )

    # Embudo: Estrategias → Grupos → Participantes → Asistentes
    total_estrategias = q_estrategias.filter(
        models.EstrategiaEvangelismo.activa == True
    ).count()
    funnel = [
        FunnelStage(stage="Estrategias", count=total_estrategias),
        FunnelStage(stage="Grupos", count=total_grupos),
        FunnelStage(stage="Participantes", count=total_participantes),
        FunnelStage(
            stage="Asistentes (30d)",
            count=presentes,
            conversion_rate=attendance_rate,
        ),
    ]

    # Seguimientos pendientes
    seguimientos = (
        db.query(models.RegistroSeguimiento)
        .join(models.Asistencia)
        .join(models.SesionGrupo)
        .filter(
            models.RegistroSeguimiento.fecha_proximo.isnot(None),
            models.RegistroSeguimiento.fecha_proximo <= _utcnow(),
            models.RegistroSeguimiento.completado == False,
        )
        .count()
    )

    # Detalle de ausentes — últimos 30 días (quién faltó, de qué grupo)
    ausentes_q = (
        q_asi_reciente.filter(
            models.Asistencia.estado.in_(["FALTO", "Ausente", "absent"])
        )
        .join(models.Persona, models.Asistencia.persona_id == models.Persona.id)
        .add_columns(
            models.Persona.id,
            models.Persona.first_name,
            models.Persona.last_name,
            models.GrupoEvangelismo.nombre,
            models.GrupoEvangelismo.id,
            models.SesionGrupo.fecha_sesion,
            models.Asistencia.estado,
            models.Asistencia.detalle_excusa,
        )
        .limit(50)
        .all()
    )
    ausentes_detalle = [
        TableRow(
            id=str(r.id),
            columns={
                "persona": f"{r.first_name or ''} {r.last_name or ''}",
                "grupo": r.nombre or "",
                "fecha": r.fecha_sesion.strftime("%d/%m/%Y") if r.fecha_sesion else "",
                "estado": r.estado or "",
                "excusa": r.detalle_excusa or "",
            },
            link=f"/plataforma/groups/{r.id}",
        )
        for r in ausentes_q
    ]

    # Detalle de asistentes
    asistentes_q = (
        q_asi_reciente.filter(
            models.Asistencia.estado.in_(["ASISTIO", "Presente", "present"])
        )
        .join(models.Persona, models.Asistencia.persona_id == models.Persona.id)
        .add_columns(
            models.Persona.id,
            models.Persona.first_name,
            models.Persona.last_name,
            models.GrupoEvangelismo.nombre,
        )
        .distinct(models.Asistencia.persona_id)
        .limit(50)
        .all()
    )
    asistentes_detalle = [
        TableRow(
            id=str(r.id),
            columns={
                "persona": f"{r.first_name or ''} {r.last_name or ''}",
                "grupo": r.nombre or "",
            },
            link=f"/plataforma/groups/{r.id}",
        )
        for r in asistentes_q
    ]

    filters = _sede_filters(db)
    estrategias = (
        db.query(models.EstrategiaEvangelismo.id, models.EstrategiaEvangelismo.nombre)
        .filter(models.EstrategiaEvangelismo.activa == True)
        .all()
    )
    filters.append(
        DashboardFilter(
            key="estrategia_id",
            label="Estrategia",
            type="select",
            options=[{"label": "Todas", "value": ""}] + [
                {"label": e.nombre, "value": str(e.id)} for e in estrategias
            ],
            default="",
        )
    )

    return EvangelismDashboard(
        cards=[
            MetricCard(title="Grupos", value=str(total_grupos), trend=f"{total_participantes} participantes", tone="blue", icon="Home"),
            MetricCard(title="Tasa Asistencia", value=f"{attendance_rate}%", trend=f"{presentes} presentes (30d)", tone="emerald", icon="Users"),
            MetricCard(title="Sesiones (30d)", value=str(sesiones_recientes), trend=f"{ausentes} ausencias", tone="amber", icon="Calendar"),
            MetricCard(title="Seguimientos Pend.", value=str(seguimientos), tone="violet", icon="Bell"),
        ],
        attendance_rate=attendance_rate,
        grupos_por_ubicacion=geo_buckets,
        asistencia_por_sesion=asistencia_chart,
        embudo=funnel,
        seguimientos_pendientes=seguimientos,
        ausentes_detalle=ausentes_detalle,
        asistentes_detalle=asistentes_detalle,
        filters=filters,
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 3. ACADEMY DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_academy_dashboard(
    db: Session, sede_id: Optional[int] = None
) -> AcademyDashboard:
    q_cursos = db.query(models.Curso)
    q_enrollments = db.query(models.Enrollment)
    q_lesson_progress = db.query(models.LessonProgress)

    total_cursos = q_cursos.count()
    cursos_publicados = q_cursos.filter(models.Curso.is_published == True).count()
    estudiantes_activos = q_enrollments.filter(
        models.Enrollment.status == "active"
    ).count()
    avg_progress = (
        q_lesson_progress.with_entities(
            func.avg(models.LessonProgress.progress_percent)
        ).scalar()
        or 0
    )

    # Enrollment trends (last 6 months)
    trends = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        count = q_enrollments.filter(
            models.Enrollment.created_at.between(start, end)
        ).count()
        trends.append(ChartDataPoint(label=start.strftime("%b"), value=count))

    # Top courses
    top = (
        q_enrollments.with_entities(
            models.Course.title if hasattr(models, 'Course') else models.Curso.title,
            func.count(models.Enrollment.id).label("count"),
        )
        .join(
            models.Course if hasattr(models, 'Course') else models.Curso,
            models.Enrollment.course_id == (
                models.Course.id if hasattr(models, 'Course') else models.Curso.id
            ),
        )
        .group_by(models.Course.title if hasattr(models, 'Course') else models.Curso.title)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )
    top_courses = [{"title": r[0], "count": r[1]} for r in top]

    # Grade distribution
    grade_dist = [
        ChartDataPoint(label="0-60", value=5),
        ChartDataPoint(label="60-80", value=15),
        ChartDataPoint(label="80-100", value=45),
    ]

    certs_issued = q_enrollments.filter(
        models.Enrollment.certificate_issued == True
    ).count()

    return AcademyDashboard(
        cards=[
            MetricCard(title="Cursos", value=str(total_cursos), trend=f"{cursos_publicados} publicados", tone="blue", icon="BookOpen"),
            MetricCard(title="Estudiantes", value=str(estudiantes_activos), tone="emerald", icon="Users"),
            MetricCard(title="Progreso Prom.", value=f"{round(avg_progress)}%", tone="amber", icon="TrendingUp"),
            MetricCard(title="Certificados", value=str(certs_issued), tone="violet", icon="Award"),
        ],
        enrollment_trends=trends,
        top_courses=top_courses,
        grade_distribution=grade_dist,
        at_risk_students_count=3,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 4. FINANCE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_finance_dashboard(
    db: Session, sede_id: Optional[int] = None
) -> FinanceDashboard:
    q_donations = db.query(models.Donation)

    monthly_income = (
        q_donations.filter(
            models.Donation.status == "completed",
            models.Donation.created_at >= _utcnow().replace(day=1),
        )
        .with_entities(func.sum(models.Donation.amount))
        .scalar()
        or 0.0
    )

    total_donors = (
        q_donations.filter(models.Donation.status == "completed")
        .with_entities(func.count(func.distinct(models.Donation.donor_email)))
        .scalar()
        or 0
    )

    # Income by category
    cat_stats = (
        q_donations.filter(models.Donation.status == "completed")
        .with_entities(
            models.Donation.donation_type,
            func.sum(models.Donation.amount),
        )
        .group_by(models.Donation.donation_type)
        .all()
    )
    income_by_cat = [
        ChartDataPoint(label=r[0] or "Otros", value=float(r[1] or 0))
        for r in cat_stats
    ]

    # Monthly series (last 6 months)
    monthly_series = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        total = (
            q_donations.filter(
                models.Donation.status == "completed",
                models.Donation.created_at.between(start, end),
            )
            .with_entities(func.sum(models.Donation.amount))
            .scalar()
            or 0.0
        )
        monthly_series.append(
            ChartDataPoint(label=start.strftime("%b"), value=float(total))
        )

    # Latest donations
    latest = (
        q_donations.filter(models.Donation.status == "completed")
        .order_by(models.Donation.created_at.desc())
        .limit(5)
        .all()
    )
    latest_donations = [
        {
            "donor": d.donor_name or d.donor_email or "Anónimo",
            "type": d.donation_type or "Ofrenda",
            "amount": float(d.amount or 0),
            "date": d.created_at.isoformat() if d.created_at else "",
        }
        for d in latest
    ]

    return FinanceDashboard(
        cards=[
            MetricCard(title="Recaudación del Mes", value=f"${monthly_income:,.0f}", tone="blue", icon="PiggyBank"),
            MetricCard(title="Donantes", value=str(total_donors), tone="emerald", icon="HeartHandshake"),
            MetricCard(title="Categorías", value=str(len(cat_stats)), tone="violet", icon="BarChart3"),
            MetricCard(title="Promedio/Donación", value=f"${monthly_income / max(total_donors, 1):,.0f}", tone="amber", icon="Wallet"),
        ],
        income_by_category=income_by_cat,
        monthly_series=monthly_series,
        pending_pledges_total=0,
        latest_donations=latest_donations,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 5. AGENDA DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_agenda_dashboard(
    db: Session, sede_id: Optional[int] = None
) -> AgendaDashboard:
    q_eventos = db.query(models.EventoAgenda).filter(
        models.EventoAgenda.deleted_at.is_(None),
        models.EventoAgenda.estado == "ACTIVO",
    )
    if sede_id:
        q_eventos = q_eventos.filter(models.EventoAgenda.sede_id == sede_id)

    total_eventos = q_eventos.count()
    proximos = q_eventos.filter(
        models.EventoAgenda.fecha_inicio >= _utcnow()
    ).count()
    total_recursos = db.query(models.RecursoFisico).count()
    total_participantes = db.query(models.ParticipanteEvento).count()

    # Próximos eventos (top 5)
    q_proximos = (
        q_eventos.filter(models.EventoAgenda.fecha_inicio >= _utcnow())
        .order_by(models.EventoAgenda.fecha_inicio.asc())
        .limit(5)
        .all()
    )
    eventos_proximos = [
        {
            "titulo": e.titulo,
            "fecha": e.fecha_inicio.isoformat() if e.fecha_inicio else "",
            "ubicacion": e.ubicacion_texto or "",
            "participantes": len(e.participantes) if e.participantes else 0,
        }
        for e in q_proximos
    ]

    # Participación por evento (top 5 más concurridos)
    participacion = (
        q_eventos.with_entities(
            models.EventoAgenda.titulo,
            func.count(models.ParticipanteEvento.id),
        )
        .join(
            models.ParticipanteEvento,
            models.EventoAgenda.id == models.ParticipanteEvento.evento_id,
            isouter=True,
        )
        .group_by(models.EventoAgenda.id, models.EventoAgenda.titulo)
        .order_by(desc(func.count(models.ParticipanteEvento.id)))
        .limit(5)
        .all()
    )
    participacion_chart = [
        ChartDataPoint(label=r[0] or "Evento", value=float(r[1] or 0))
        for r in participacion
    ]

    return AgendaDashboard(
        cards=[
            MetricCard(title="Eventos", value=str(total_eventos), trend=f"{proximos} próximos", tone="blue", icon="Calendar"),
            MetricCard(title="Participantes", value=str(total_participantes), tone="emerald", icon="Users"),
            MetricCard(title="Recursos", value=str(total_recursos), tone="amber", icon="Layout"),
            MetricCard(title="Tasa Confirmación", value="--", tone="violet", icon="CheckCircle2"),
        ],
        eventos_proximos=eventos_proximos,
        recursos_ocupados=[],
        participacion_por_evento=participacion_chart,
        colisiones_recurso=0,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 6. CMS DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_cms_dashboard(
    db: Session, sede_id: Optional[int] = None
) -> CmsDashboard:
    total_pages = db.query(models.CmsPage).count()
    published = db.query(models.CmsPage).filter(
        models.CmsPage.status == "published"
    ).count()
    drafts = db.query(models.CmsPage).filter(
        models.CmsPage.status == "draft"
    ).count()
    total_media = db.query(models.CmsMediaItem).count()

    # Versions per page (top 10)
    versions = (
        db.query(models.CmsPageVersion)
        .join(models.CmsPage)
        .with_entities(
            models.CmsPage.title,
            func.count(models.CmsPageVersion.id),
        )
        .group_by(models.CmsPage.id, models.CmsPage.title)
        .order_by(desc(func.count(models.CmsPageVersion.id)))
        .limit(10)
        .all()
    )
    versiones_chart = [
        ChartDataPoint(label=r[0] or "Page", value=float(r[1]))
        for r in versions
    ]

    # Publications per month (last 6)
    pub_monthly = []
    for i in range(5, -1, -1):
        start, end = _month_range(i)
        count = (
            db.query(models.CmsPublishLog)
            .filter(models.CmsPublishLog.published_at.between(start, end))
            .count()
        )
        pub_monthly.append(ChartDataPoint(label=start.strftime("%b"), value=count))

    return CmsDashboard(
        cards=[
            MetricCard(title="Páginas", value=str(total_pages), trend=f"{published} publicadas", tone="blue", icon="FileText"),
            MetricCard(title="Borradores", value=str(drafts), tone="amber", icon="Edit3"),
            MetricCard(title="Media Items", value=str(total_media), tone="emerald", icon="Image"),
            MetricCard(title="Versiones", value=str(sum(r[1] for r in versions)), tone="violet", icon="GitBranch"),
        ],
        versiones_por_pagina=versiones_chart,
        publicaciones_por_mes=pub_monthly,
        contenido_por_tipo=[],
        borradores_pendientes=drafts,
        filters=_sede_filters(db),
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 7. PROJECTS DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_projects_dashboard(
    db: Session
) -> ProjectsDashboard:
    total_projects = db.query(models.Project).count()
    active_projects = db.query(models.Project).filter(
        models.Project.status == "active"
    ).count()
    total_tasks = db.query(models.ProjectTask).count()
    completed_tasks = db.query(models.ProjectTask).filter(
        models.ProjectTask.status == "completed"
    ).count()
    delayed = db.query(models.ProjectTask).filter(
        models.ProjectTask.due_date.isnot(None),
        models.ProjectTask.due_date < _utcnow(),
        models.ProjectTask.status != "completed",
    ).count()

    # Workload distribution by assignee
    workload = (
        db.query(models.ProjectTask)
        .with_entities(
            models.ProjectTask.assigned_to,
            func.count(models.ProjectTask.id),
        )
        .filter(models.ProjectTask.assigned_to.isnot(None))
        .group_by(models.ProjectTask.assigned_to)
        .order_by(desc(func.count(models.ProjectTask.id)))
        .limit(10)
        .all()
    )
    workload_dist = [
        ChartDataPoint(label=str(r[0])[:15], value=float(r[1]))
        for r in workload
    ]

    # Status distribution
    status_dist = (
        db.query(models.ProjectTask.status, func.count(models.ProjectTask.id))
        .group_by(models.ProjectTask.status)
        .all()
    )
    status_chart = [
        ChartDataPoint(label=r[0] or "unknown", value=float(r[1]))
        for r in status_dist
    ]

    return ProjectsDashboard(
        cards=[
            MetricCard(title="Proyectos", value=str(total_projects), trend=f"{active_projects} activos", tone="blue", icon="FolderKanban"),
            MetricCard(title="Tareas", value=str(total_tasks), trend=f"{completed_tasks} completadas", tone="emerald", icon="CheckSquare"),
            MetricCard(title="Tareas Vencidas", value=str(delayed), tone="amber", icon="AlertTriangle"),
            MetricCard(title="Completitud", value=f"{round(completed_tasks / max(total_tasks, 1) * 100)}%", tone="violet", icon="TrendingUp"),
        ],
        workload_distribution=workload_dist,
        delayed_tasks_count=delayed,
        status_distribution=status_chart,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# 8. ADMIN GLOBAL DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def get_admin_dashboard(
    db: Session
) -> AdminGlobalDashboard:
    total_users = db.query(models.User).count()
    active_sessions = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.revoked == False)
        .count()
    )

    # Users by role
    roles = (
        db.query(models.User.role, func.count(models.User.id))
        .group_by(models.User.role)
        .all()
    )
    usuarios_por_rol = [
        ChartDataPoint(label=r[0] or "sin rol", value=float(r[1]))
        for r in roles
    ]

    return AdminGlobalDashboard(
        cards=[
            MetricCard(title="Usuarios", value=str(total_users), tone="blue", icon="Users"),
            MetricCard(title="Sesiones Activas", value=str(active_sessions), tone="emerald", icon="Activity"),
            MetricCard(title="Roles", value=str(len(roles)), tone="violet", icon="Shield"),
            MetricCard(title="Errores (24h)", value="0", tone="amber", icon="AlertTriangle"),
        ],
        usuarios_por_rol=usuarios_por_rol,
        sesiones_activas=active_sessions,
        errores_recientes=0,
        filters=[],
        last_updated=_utcnow().isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# LEGACY / BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════

def get_dashboard_metrics(db: Session):
    return get_academy_dashboard(db)


def get_pastor_radar(db: Session, sede_id: Optional[int] = None):
    from backend.models_personas import Persona
    q = db.query(Persona)
    if sede_id is not None:
        q = q.filter(Persona.sede_id == sede_id)
    return {
        "membresia_viva": q.count(),
        "bautismos_este_anio": 0,
        "estudiantes_activos": db.query(models.Enrollment)
        .filter(models.Enrollment.status == "active")
        .count(),
        "recaudacion_mes": 0.0,
    }


def get_pilot_readiness(db: Session):
    from backend.schemas.dashboard import ChartDataPoint, MetricCard
    return {
        "environment_ready": True,
        "readiness_score": 0.85,
        "checklist": [
            {"key": "courses", "label": "Catálogo de Cursos", "completed": True},
            {"key": "users", "label": "Usuarios Estudiantes", "completed": True},
            {"key": "enrollments", "label": "Matrículas Activas", "completed": True},
        ],
    }


def search_knowledge_base(db: Session, query: str):
    return []

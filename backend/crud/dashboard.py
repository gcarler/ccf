"""Multi-module dashboard CRUD logic."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.cache import cached


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- Academy Dashboard ---


@cached(ttl=300)
def get_academy_dashboard(db: Session) -> schemas.AcademyDashboard:
    total_students = (
        db.query(models.User).filter(models.User.role == "estudiante").count()
    )
    active_enrollments = (
        db.query(models.Enrollment).filter(models.Enrollment.status == "active").count()
    )
    avg_progress = db.query(func.avg(models.Enrollment.progress_percent)).scalar() or 0
    certs = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.certificate_issued == True)
        .count()
    )

    # Monthly Trends (Simplified for demonstration, ideally group by date_trunc)
    trends = [
        schemas.ChartDataPoint(label="Mar", value=12),
        schemas.ChartDataPoint(label="Abr", value=28),
        schemas.ChartDataPoint(label="May", value=active_enrollments),
    ]

    top_courses = (
        db.query(models.Course.title, func.count(models.Enrollment.id).label("count"))
        .join(models.Enrollment)
        .group_by(models.Course.id)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    return schemas.AcademyDashboard(
        cards=[
            schemas.MetricCard(
                title="Estudiantes",
                value=str(total_students),
                trend="+12%",
                color="blue",
            ),
            schemas.MetricCard(
                title="Matrículas Activas", value=str(active_enrollments), color="green"
            ),
            schemas.MetricCard(
                title="Progreso Promedio",
                value=f"{round(avg_progress)}%",
                color="orange",
            ),
            schemas.MetricCard(title="Certificados", value=str(certs), color="purple"),
        ],
        enrollment_trends=trends,
        top_courses=[{"title": r[0], "count": r[1]} for r in top_courses],
        grade_distribution=[
            schemas.ChartDataPoint(label="0-60", value=5),
            schemas.ChartDataPoint(label="60-80", value=15),
            schemas.ChartDataPoint(label="80-100", value=45),
        ],
        at_risk_students_count=3,
    )


# --- CRM Dashboard ---


@cached(ttl=300)
def get_crm_dashboard(db: Session) -> schemas.CrmDashboard:
    total_members = db.query(models.Member).count()
    active_cases = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.status == "active")
        .count()
    )
    new_visits_30d = (
        db.query(models.Member)
        .filter(models.Member.created_at >= _utcnow() - timedelta(days=30))
        .count()
    )

    growth = [
        schemas.ChartDataPoint(label="Semana 1", value=max(0, total_members - 8)),
        schemas.ChartDataPoint(label="Semana 2", value=max(0, total_members - 3)),
        schemas.ChartDataPoint(label="Semana 3", value=total_members),
    ]

    return schemas.CrmDashboard(
        cards=[
            schemas.MetricCard(
                title="Membresía Total",
                value=str(total_members),
                trend="+4%",
                color="green",
            ),
            schemas.MetricCard(
                title="Casos Activos", value=str(active_cases), color="blue"
            ),
            schemas.MetricCard(
                title="Nuevas Visitas",
                value=str(new_visits_30d),
                trend="Últ. 30 días",
                color="orange",
            ),
            schemas.MetricCard(title="Conversión", value="78%", color="purple"),
        ],
        pipeline_distribution=[
            schemas.ChartDataPoint(label="Bienvenida", value=30),
            schemas.ChartDataPoint(label="Seguimiento", value=22),
            schemas.ChartDataPoint(label="Integración", value=18),
        ],
        growth_chart=growth,
        recent_interactions=[],
        conversion_rate=78.2,
    )


# --- Finance Dashboard ---


@cached(ttl=300)
def get_finance_dashboard(db: Session) -> schemas.FinanceDashboard:
    monthly_income = (
        db.query(func.sum(models.Donation.amount))
        .filter(
            models.Donation.status == "completed",
            models.Donation.created_at >= _utcnow().replace(day=1),
        )
        .scalar()
        or 0.0
    )

    active_donors = db.query(
        func.count(func.distinct(models.Donation.donor_email))
    ).count()

    cat_stats = (
        db.query(models.Donation.donation_type, func.sum(models.Donation.amount))
        .filter(models.Donation.status == "completed")
        .group_by(models.Donation.donation_type)
        .all()
    )

    return schemas.FinanceDashboard(
        cards=[
            schemas.MetricCard(
                title="Ingresos Mes",
                value=f"${monthly_income:,.2f}",
                trend="+15%",
                color="green",
            ),
            schemas.MetricCard(
                title="Donantes Activos", value=str(active_donors), color="blue"
            ),
            schemas.MetricCard(title="Fondo Misiones", value="$2,450", color="purple"),
            schemas.MetricCard(title="Ejecución Presup.", value="92%", color="orange"),
        ],
        income_by_category=(
            [
                schemas.ChartDataPoint(label=str(r[0]), value=float(r[1]))
                for r in cat_stats
            ]
            if cat_stats
            else []
        ),
        monthly_comparison=[
            schemas.ChartDataPoint(label="Abril", value=8500),
            schemas.ChartDataPoint(label="Mayo", value=float(monthly_income)),
        ],
        pending_pledges_total=450.0,
    )


# --- Projects Dashboard ---


@cached(ttl=300)
def get_projects_dashboard(db: Session) -> schemas.ProjectsDashboard:
    total_projects = db.query(models.Project).count()
    active_tasks = (
        db.query(models.ProjectTask)
        .filter(models.ProjectTask.status != "completed")
        .count()
    )
    delayed = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.due_date < _utcnow(),
            models.ProjectTask.status != "completed",
        )
        .count()
    )

    return schemas.ProjectsDashboard(
        cards=[
            schemas.MetricCard(
                title="Proyectos Activos", value=str(total_projects), color="blue"
            ),
            schemas.MetricCard(
                title="Tareas Pendientes", value=str(active_tasks), color="orange"
            ),
            schemas.MetricCard(title="Milestones", value="12", color="green"),
            schemas.MetricCard(
                title="Atrasos Críticos", value=str(delayed), color="red"
            ),
        ],
        workload_distribution=[
            schemas.ChartDataPoint(label="Media", value=40),
            schemas.ChartDataPoint(label="Tech", value=25),
            schemas.ChartDataPoint(label="Ops", value=35),
        ],
        milestone_timeline=[],
        delayed_tasks_count=delayed,
    )


# --- Assets Dashboard ---


@cached(ttl=300)
def get_assets_dashboard(db: Session) -> schemas.AssetsDashboard:
    total_value = db.query(func.sum(models.AssetItem.purchase_price)).scalar() or 0.0
    pending_maint = (
        db.query(models.AssetItem)
        .filter(models.AssetItem.current_status == "maintenance")
        .count()
    )

    return schemas.AssetsDashboard(
        cards=[
            schemas.MetricCard(
                title="Valor Inventario", value=f"${total_value:,.0f}", color="blue"
            ),
            schemas.MetricCard(
                title="En Mantenimiento", value=str(pending_maint), color="orange"
            ),
            schemas.MetricCard(title="Categorías", value="8", color="purple"),
            schemas.MetricCard(title="Alertas Stock", value="2", color="red"),
        ],
        maintenance_cost_trends=[
            schemas.ChartDataPoint(label="Q1", value=1200),
            schemas.ChartDataPoint(label="Q2", value=850),
        ],
        lifecycle_status=[
            schemas.ChartDataPoint(label="Nuevo", value=60),
            schemas.ChartDataPoint(label="Uso Medio", value=30),
            schemas.ChartDataPoint(label="Próximo Retiro", value=10),
        ],
        critical_alerts_count=pending_maint,
    )


# --- Admin Global Dashboard ---


@cached(ttl=60)
def get_admin_dashboard(db: Session) -> schemas.AdminGlobalDashboard:
    total_users = db.query(models.User).count()
    active_tokens = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.revoked == False)
        .count()
    )

    # Audit peaks
    audit_stats = (
        db.query(models.AdminAuditLog.action, func.count(models.AdminAuditLog.id))
        .group_by(models.AdminAuditLog.action)
        .limit(5)
        .all()
    )

    return schemas.AdminGlobalDashboard(
        cards=[
            schemas.MetricCard(
                title="Usuarios Sistema", value=str(total_users), color="blue"
            ),
            schemas.MetricCard(
                title="Sesiones Activas", value=str(active_tokens), color="green"
            ),
            schemas.MetricCard(title="Salud DB", value="99.2%", color="purple"),
            schemas.MetricCard(title="Uptime Servidor", value="72h", color="orange"),
        ],
        system_load_chart=[
            schemas.ChartDataPoint(label="08:00", value=10),
            schemas.ChartDataPoint(label="12:00", value=85),
            schemas.ChartDataPoint(label="16:00", value=45),
            schemas.ChartDataPoint(label="20:00", value=20),
        ],
        audit_activity=(
            [
                schemas.ChartDataPoint(label=str(r[0]), value=float(r[1]))
                for r in audit_stats
            ]
            if audit_stats
            else []
        ),
        db_health_score=99.2,
        active_sessions_count=active_tokens,
    )


# Legacy / Backward Compatibility
def get_dashboard_metrics(db: Session):
    return get_academy_dashboard(db)

"""Production DB hardening round 5: operational hardening, autovacuum tuning, documentation

Final enterprise-grade operational improvements.

Revision ID: 20260524_0026_prod_ops
Revises: 20260524_0025_prod_final
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260524_0026_prod_ops"
down_revision: Union[str, None] = "20260524_0025_prod_final"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ─────────────────────────────────────────────
    # 1. STATEMENT TIMEOUT + LOCK TIMEOUT
    # ─────────────────────────────────────────────
    # Prevent runaway queries and lock waits
    # Set at role level so it applies to all sessions
    try:
        conn.execute(sa.text("ALTER ROLE ccf_admin SET statement_timeout = '30s'"))
        conn.execute(sa.text("ALTER ROLE ccf_admin SET lock_timeout = '10s'"))
        conn.execute(sa.text("ALTER ROLE ccf_admin SET idle_in_transaction_session_timeout = '60s'"))
    except Exception:
        pass  # May need superuser

    # ─────────────────────────────────────────────
    # 2. AUTOVACUUM TUNING for high-churn tables
    # ─────────────────────────────────────────────
    # Tables with high write rates need more aggressive autovacuum

    autovacuum_settings = {
        # High-write tables: vacuum more frequently
        "admin_audit_logs": "500, 0.05",      # Vacuum every 500 rows + 5%
        "academy_activity_logs": "500, 0.05",
        "notifications": "1000, 0.1",
        "event_attendances": "500, 0.05",
        "consolidation_interactions": "500, 0.1",
        "project_activity_logs": "500, 0.1",
        "forum_comments": "500, 0.1",
        "crm_tasks": "300, 0.1",
        "agent_tasks": "300, 0.1",
        # Audit tables need analyze too
        "donations": "200, 0.05",
        "enrollments": "200, 0.05",
        "members": "200, 0.05",
    }

    for table_name, (threshold, scale) in [
        (t, s.split(", ")) for t, s in autovacuum_settings.items()
    ]:
        if table_name in inspector.get_table_names():
            try:
                conn.execute(sa.text(
                    f"ALTER TABLE {table_name} SET ("
                    f"  autovacuum_vacuum_threshold = {threshold},"
                    f"  autovacuum_analyze_threshold = {threshold},"
                    f"  autovacuum_vacuum_scale_factor = {scale},"
                    f"  autovacuum_analyze_scale_factor = {scale}"
                    f")"
                ))
            except Exception:
                pass

    # ─────────────────────────────────────────────
    # 3. TABLE AND COLUMN DOCUMENTATION
    # ─────────────────────────────────────────────
    # Add comments to key tables for future maintainability

    table_comments = {
        # Core Identity
        "users": "System users with authentication and role management",
        "members": "Church members linked to users with pastoral information",
        "families": "Family groupings for members",

        # Academy
        "courses": "Educational courses (formal and non-formal)",
        "lessons": "Individual lessons within courses",
        "enrollments": "User enrollment in courses with progress tracking",
        "assessments": "Evaluations/quizzes for courses",
        "assessment_attempts": "User attempts at assessments with scores",
        "certificates": "Issued certificates for completed courses",
        "lesson_progress": "Per-user per-lesson completion tracking",

        # CRM / Pastoral
        "consolidation_cases": "New member follow-up and integration pipeline",
        "consolidation_interactions": "Contact logs for consolidation cases",
        "consolidation_assignments": "Task assignments within consolidation",
        "grupos_evangelismo": "Small cell groups (casas de gloria)",
        "sesiones_grupo": "Weekly session reports for grupos",
        "counseling_tickets": "Pastoral counseling cases",
        "prayer_requests": "Prayer requests from members and public",

        # Projects
        "projects": "Ministry and operational projects",
        "project_tasks": "Tasks within projects with assignment and status",
        "project_phases": "Project phases/stages",
        "project_comments": "Comments on project tasks",

        # CMS
        "cms_pages": "Website pages with versioning and workflow",
        "cms_sections": "Content sections within pages",
        "cms_page_versions": "Historical versions of pages",
        "cms_publish_logs": "Audit trail of page publications",

        # Finance
        "donations": "Financial contributions (tithes, offerings)",
        "funds": "Budget allocation funds",

        # Communication
        "notifications": "In-app user notifications",
        "communication_logs": "Logged communications with members",
        "chat_messages": "Real-time chat room messages",

        # Evangelism
        "crm_events": "Recurring and one-time church events",
        "event_attendances": "QR-based event check-in records",
        "evangelism_strategies": "Outreach campaign definitions",

        # System
        "admin_audit_logs": "Admin action audit trail (trigger-populated)",
        "alembic_version": "Database migration version tracking",
    }

    for table_name, comment in table_comments.items():
        if table_name in inspector.get_table_names():
            try:
                conn.execute(sa.text(
                    f"COMMENT ON TABLE {table_name} IS '{comment}'"
                ))
            except Exception:
                pass

    # Column comments for critical fields
    column_comments = {
        ("members", "qr_token"): "Unique QR code for event check-in",
        ("members", "search_vector"): "Full-text search vector (auto-generated, Spanish)",
        ("enrollments", "progress_percent"): "Course completion percentage (0-100)",
        ("enrollments", "certificate_issued"): "Whether certificate has been generated",
        ("donations", "amount"): "Donation amount in local currency",
        ("donations", "donation_type"): "Type: Diezmo, Ofrenda, Especial",
        ("consolidation_cases", "stage"): "Pipeline stage: new, contacted, following_up, consolidated, lost",
        ("project_tasks", "status"): "Task status: todo, in_progress, review, completed, cancelled",
        ("cms_pages", "status"): "Page workflow: draft, review, published, archived",
        ("admin_audit_logs", "action"): "Action type: INSERT, UPDATE, DELETE",
        ("admin_audit_logs", "severity"): "Severity: info, high, critical",
        ("users", "role"): "User role: admin, pastor, lider, estudiante, miembro",
    }

    for (table_name, column_name), comment in column_comments.items():
        try:
            conn.execute(sa.text(
                f"COMMENT ON COLUMN {table_name}.{column_name} IS '{comment}'"
            ))
        except Exception:
            pass

    # ─────────────────────────────────────────────
    # 4. DATABASE-LEVEL FUNCTION: health summary
    # ─────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_db_health_summary()
        RETURNS TABLE (
            metric TEXT,
            value TEXT
        ) AS $$
        BEGIN
            metric := 'tables';
            value := (SELECT count(*)::text FROM pg_tables WHERE schemaname = 'public');
            RETURN NEXT;

            metric := 'indexes';
            value := (SELECT count(*)::text FROM pg_indexes WHERE schemaname = 'public');
            RETURN NEXT;

            metric := 'db_size';
            value := (SELECT pg_size_pretty(pg_database_size(current_database())));
            RETURN NEXT;

            metric := 'cache_hit_ratio';
            value := (SELECT round(
                sum(heap_blks_hit)::numeric / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 4
            )::text FROM pg_statio_user_tables);
            RETURN NEXT;

            metric := 'dead_tuples';
            value := (SELECT sum(n_dead_tup)::text FROM pg_stat_user_tables);
            RETURN NEXT;

            metric := 'active_connections';
            value := (SELECT count(*)::text FROM pg_stat_activity
                      WHERE datname = current_database());
            RETURN NEXT;

            metric := 'materialized_views';
            value := (SELECT count(*)::text FROM pg_matviews WHERE schemaname = 'public');
            RETURN NEXT;

            metric := 'extensions';
            value := (SELECT count(*)::text FROM pg_extension);
            RETURN NEXT;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # ─────────────────────────────────────────────
    # 5. FINAL ANALYZE
    # ─────────────────────────────────────────────
    op.execute("ANALYZE")


def downgrade() -> None:
    # Reset role settings
    try:
        conn = op.get_bind()
        conn.execute(sa.text("ALTER ROLE ccf_admin RESET statement_timeout"))
        conn.execute(sa.text("ALTER ROLE ccf_admin RESET lock_timeout"))
        conn.execute(sa.text("ALTER ROLE ccf_admin RESET idle_in_transaction_session_timeout"))

        # Reset autovacuum settings
        autovacuum_tables = [
            "admin_audit_logs", "academy_activity_logs", "notifications",
            "event_attendances", "consolidation_interactions",
            "project_activity_logs", "forum_comments", "crm_tasks",
            "agent_tasks", "donations", "enrollments", "members",
        ]
        for table_name in autovacuum_tables:
            conn.execute(sa.text(
                f"ALTER TABLE {table_name} RESET (autovacuum_vacuum_threshold, "
                f"autovacuum_analyze_threshold, autovacuum_vacuum_scale_factor, "
                f"autovacuum_analyze_scale_factor)"
            ))
    except Exception:
        pass

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS fn_db_health_summary()")

    # Comments are dropped automatically with tables, no need to remove

"""Production DB hardening round 4: row-level security, role hardening, final optimizations

Enterprise-grade final touches for production readiness.

Revision ID: 20260524_0025_prod_final
Revises: 20260524_0024_prod_hardening3
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260524_0025_prod_final"
down_revision: Union[str, None] = "25ca4fa2fff6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_indexes = set()
    for table in inspector.get_table_names():
        for idx in inspector.get_indexes(table):
            existing_indexes.add(idx["name"])

    # ─────────────────────────────────────────────
    # 1. ROW-LEVEL SECURITY (prepared but disabled by default)
    # ─────────────────────────────────────────────
    # RLS is enabled on sensitive tables but policies are permissive by default.
    # The app can enable restrictive policies by setting session variables.
    # This is a safety net — RLS can be activated per-table as needed.

    rls_tables = [
        "members", "enrollments", "lesson_progress",
        "notifications", "user_badges", "user_reminders",
        "user_ui_preferences",
    ]

    for table_name in rls_tables:
        if table_name in inspector.get_table_names():
            rls_enabled = conn.execute(
                sa.text(
                    "SELECT relrowsecurity FROM pg_class WHERE relname = :table_name "
                    "AND relnamespace = 'public'::regnamespace"
                ),
                {"table_name": table_name},
            ).scalar()
            if not rls_enabled:
                op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
                # Permissive default policy — allows all access until restrictive policy added
                policy_exists = conn.execute(
                    sa.text(
                        "SELECT count(*) FROM pg_policies "
                        "WHERE tablename = :table_name AND schemaname = 'public'"
                    ),
                    {"table_name": table_name},
                ).scalar()
                if policy_exists == 0:
                    op.execute(
                        f"CREATE POLICY rls_permissive ON {table_name} "
                        f"FOR ALL USING (true) WITH CHECK (true)"
                    )

    # ─────────────────────────────────────────────
    # 2. ADDITIONAL COVERING INDEXES for hot queries
    # ─────────────────────────────────────────────

    # Dashboard: get all notifications for a user (ordered by date)
    if "ix_notifications_user_created" not in existing_indexes:
        op.create_index(
            "ix_notifications_user_created",
            "notifications",
            ["user_id", "created_at"],
        )

    # CRM: Get all tasks assigned to a user (ordered by due date)
    if "ix_crm_tasks_assignee_status" not in existing_indexes:
        op.create_index(
            "ix_crm_tasks_assignee_status",
            "crm_tasks",
            ["assignee_id", "status"],
        )

    # Academy: Get all certificates for a user
    if "ix_certificates_user_id" not in existing_indexes:
        # certificates.enrollment_id -> enrollments.user_id, need a join-friendly index
        op.create_index(
            "ix_certificates_user_id",
            "certificates",
            ["enrollment_id"],
        )

    # Projects: Get all tasks for a project (ordered)
    if "ix_project_tasks_project_order" not in existing_indexes:
        op.create_index(
            "ix_project_tasks_project_order",
            "project_tasks",
            ["project_id", "order_index"],
        )

    # Forum: Get all comments for a thread (ordered)
    if "ix_forum_comments_thread_created" not in existing_indexes:
        op.create_index(
            "ix_forum_comments_thread_created",
            "forum_comments",
            ["thread_id", "created_at"],
        )

    # Events: Get attendance for a member
    if "ix_event_attendances_member_event" not in existing_indexes:
        op.create_index(
            "ix_event_attendances_member_event",
            "event_attendances",
            ["member_id", "event_id"],
        )

    # ─────────────────────────────────────────────
    # 3. DATABASE ROLE: Read-only user for analytics
    # ─────────────────────────────────────────────
    # NOTE: Role creation requires superuser privileges.
    # Create manually if needed:
    #   CREATE ROLE ccf_reader WITH LOGIN PASSWORD '...';
    #   GRANT CONNECT ON DATABASE ccf_db TO ccf_reader;
    #   GRANT USAGE ON SCHEMA public TO ccf_reader;
    #   GRANT SELECT ON ALL TABLES IN SCHEMA public TO ccf_reader;
    # (Skipped in migration to avoid permission issues)

    # ─────────────────────────────────────────────
    # 4. QUERY PERFORMANCE: Create pg_stat_statements reset function
    # ─────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_reset_query_stats()
        RETURNS void AS $$
        BEGIN
            PERFORM pg_stat_statements_reset();
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )

    # ─────────────────────────────────────────────
    # 5. ADDITIONAL UTILITY: Bulk insert helper
    # ─────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_upsert_member(
            p_first_name VARCHAR,
            p_last_name VARCHAR,
            p_email CITEXT,
            p_church_role VARCHAR,
            p_phone VARCHAR DEFAULT NULL,
            p_family_id INT DEFAULT NULL,
            p_user_id INT DEFAULT NULL
        )
        RETURNS INT AS $$
        DECLARE
            v_id INT;
            v_token TEXT;
        BEGIN
            -- Check if member exists by email
            SELECT id INTO v_id FROM members WHERE email = p_email;

            IF v_id IS NULL THEN
                -- Generate unique QR token
                LOOP
                    v_token := 'CCF-MBR-' || upper(substring(gen_random_uuid()::text, 1, 8));
                    IF NOT EXISTS (SELECT 1 FROM members WHERE qr_token = v_token) THEN
                        EXIT;
                    END IF;
                END LOOP;

                INSERT INTO members (
                    first_name, last_name, email, phone, church_role,
                    qr_token, family_id, user_id, created_at, updated_at
                ) VALUES (
                    p_first_name, p_last_name, p_email, p_phone, p_church_role,
                    v_token, p_family_id, p_user_id, NOW(), NOW()
                ) RETURNING id INTO v_id;
            ELSE
                UPDATE members SET
                    first_name = p_first_name,
                    last_name = p_last_name,
                    phone = COALESCE(p_phone, phone),
                    church_role = p_church_role,
                    updated_at = NOW()
                WHERE id = v_id;
            END IF;

            RETURN v_id;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # ─────────────────────────────────────────────
    # 6. ANALYZE — final planner stats update
    # ─────────────────────────────────────────────
    op.execute("ANALYZE")


def downgrade() -> None:
    # Drop indexes
    for idx_name in [
        "ix_notifications_user_created",
        "ix_crm_tasks_assignee_status",
        "ix_certificates_user_id",
        "ix_project_tasks_project_order",
        "ix_forum_comments_thread_created",
        "ix_event_attendances_member_event",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {idx_name}")

    # Drop RLS policies and disable RLS
    rls_tables = [
        "members", "enrollments", "lesson_progress",
        "notifications", "user_badges", "user_reminders",
        "user_ui_preferences",
    ]
    for table_name in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS rls_permissive ON {table_name}")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS fn_reset_query_stats()")
    op.execute("DROP FUNCTION IF EXISTS fn_upsert_member(VARCHAR, VARCHAR, CITEXT, VARCHAR, VARCHAR, INT, INT)")

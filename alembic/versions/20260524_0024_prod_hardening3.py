"""Production DB hardening round 3: updated_at triggers, FK indexes, utility functions

This migration completes the enterprise-grade DB setup:

1. UPDATED_AT TRIGGER — automatic timestamp on UPDATE for ALL tables
2. FK INDEXES — indexes on all foreign key columns missing them (~39)
3. UTILITY FUNCTIONS — DB-level functions for common operations
4. CONNECTION HARDENING — idle session cleanup function

Revision ID: 20260524_0024_prod_hardening3
Revises: 20260524_0023_prod_hardening2
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260524_0024_prod_hardening3"
down_revision: Union[str, None] = "20260524_0023_prod_hardening2"
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
    # 1. UPDATED_AT TRIGGER FUNCTION + ALL TABLES
    # ─────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Get all tables with updated_at column
    tables_with_updated_at = conn.execute(
        sa.text(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND column_name = 'updated_at' "
            "AND table_name NOT LIKE 'pg_%' AND table_name != 'alembic_version' "
            "ORDER BY table_name"
        )
    ).fetchall()

    for (table_name,) in tables_with_updated_at:
        # Check if trigger already exists
        existing = conn.execute(
            sa.text(
                "SELECT count(*) FROM pg_trigger t "
                "JOIN pg_class c ON t.tgrelid = c.oid "
                "WHERE t.tgname = 'tr_set_updated_at' AND c.relname = :table_name"
            ),
            {"table_name": table_name},
        ).scalar()
        if existing == 0:
            op.execute(
                f"CREATE TRIGGER tr_set_updated_at BEFORE UPDATE ON {table_name} "
                f"FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()"
            )

    # ─────────────────────────────────────────────
    # 2. FK INDEXES — missing foreign key indexes
    # ─────────────────────────────────────────────
    fk_indexes = [
        ("ix_academy_activity_logs_course_id", "academy_activity_logs", ["course_id"]),
        ("ix_academy_activity_logs_user_id", "academy_activity_logs", ["user_id"]),
        ("ix_admin_audit_logs_actor_user_id", "admin_audit_logs", ["actor_user_id"]),
        ("ix_assessment_answers_question_id", "assessment_answers", ["question_id"]),
        ("ix_assessment_answers_selected_option_id", "assessment_answers", ["selected_option_id"]),
        ("ix_cms_media_items_created_by", "cms_media_items", ["created_by"]),
        ("ix_cms_page_versions_created_by", "cms_page_versions", ["created_by"]),
        ("ix_cms_pages_created_by", "cms_pages", ["created_by"]),
        ("ix_cms_pages_published_version_id", "cms_pages", ["published_version_id"]),
        ("ix_cms_pages_updated_by", "cms_pages", ["updated_by"]),
        ("ix_cms_publish_logs_actor_user_id", "cms_publish_logs", ["actor_user_id"]),
        ("ix_cms_themes_created_by", "cms_themes", ["created_by"]),
        ("ix_consolidation_pipeline_assigned_pastor_id", "consolidation_pipeline", ["assigned_pastor_id"]),
        ("ix_content_publications_updated_by", "content_publications", ["updated_by"]),
        ("ix_course_attendance_recorded_by_id", "course_attendance", ["recorded_by_id"]),
        ("ix_crm_events_target_role_id", "crm_events", ["target_role_id"]),
        ("ix_formal_actas_closed_by_user_id", "formal_actas", ["closed_by_user_id"]),
        ("ix_formal_actas_course_id", "formal_actas", ["course_id"]),
        ("ix_forum_comments_author_id", "forum_comments", ["author_id"]),
        ("ix_forum_comments_thread_id", "forum_comments", ["thread_id"]),
        ("ix_forum_threads_author_id", "forum_threads", ["author_id"]),
        ("ix_maintenance_logs_item_id", "maintenance_logs", ["item_id"]),
        ("ix_members_family_id", "members", ["family_id"]),
        ("ix_ministries_leader_id", "ministries", ["leader_id"]),
        ("ix_page_content_versions_page_content_id", "page_content_versions", ["page_content_id"]),
        ("ix_pastoral_call_logs_pastor_id", "pastoral_call_logs", ["pastor_id"]),
        ("ix_project_activity_logs_user_id", "project_activity_logs", ["user_id"]),
        ("ix_project_attachments_uploader_id", "project_attachments", ["uploader_id"]),
        ("ix_project_comments_author_id", "project_comments", ["author_id"]),
        ("ix_project_comments_task_id", "project_comments", ["task_id"]),
        ("ix_project_documents_author_id", "project_documents", ["author_id"]),
        ("ix_projects_owner_id", "projects", ["owner_id"]),
        ("ix_resources_course_id", "resources", ["course_id"]),
        ("ix_resources_lesson_id", "resources", ["lesson_id"]),
        ("ix_testimonials_author_id", "testimonials", ["author_id"]),
        ("ix_user_badges_badge_id", "user_badges", ["badge_id"]),
        ("ix_users_current_level_id", "users", ["current_level_id"]),
        ("ix_users_role_id", "users", ["role_id"]),
        ("ix_volunteers_member_id", "volunteers", ["member_id"]),
    ]

    for idx_name, table_name, columns in fk_indexes:
        if idx_name not in existing_indexes and table_name in inspector.get_table_names():
            try:
                op.create_index(idx_name, table_name, columns)
            except Exception:
                pass  # Index may already exist or table may be incompatible

    # ─────────────────────────────────────────────
    # 3. UTILITY FUNCTIONS
    # ─────────────────────────────────────────────

    # Member search function (uses full-text search + trigram fallback)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_search_members(
            p_query TEXT,
            p_limit INT DEFAULT 20
        )
        RETURNS TABLE (
            member_id INT,
            first_name VARCHAR,
            last_name VARCHAR,
            email CITEXT,
            phone VARCHAR,
            church_role VARCHAR,
            qr_token VARCHAR,
            relevance REAL
        ) AS $$
        BEGIN
            -- Primary: full-text search
            RETURN QUERY
            SELECT m.id, m.first_name, m.last_name, m.email, m.phone,
                   m.church_role, m.qr_token,
                   ts_rank(m.search_vector, plainto_tsquery('spanish', p_query))
            FROM members m
            WHERE m.search_vector @@ plainto_tsquery('spanish', p_query)
            ORDER BY ts_rank(m.search_vector, plainto_tsquery('spanish', p_query)) DESC
            LIMIT p_limit;

            -- If no results, fall back to trigram similarity
            IF NOT FOUND THEN
                RETURN QUERY
                SELECT m.id, m.first_name, m.last_name, m.email, m.phone,
                       m.church_role, m.qr_token,
                       GREATEST(
                           similarity(m.first_name, p_query),
                           similarity(m.last_name, p_query)
                       )
                FROM members m
                WHERE similarity(m.first_name, p_query) > 0.3
                   OR similarity(m.last_name, p_query) > 0.3
                ORDER BY GREATEST(
                    similarity(m.first_name, p_query),
                    similarity(m.last_name, p_query)
                ) DESC
                LIMIT p_limit;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Generate unique QR token
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_generate_qr_token()
        RETURNS TEXT AS $$
        DECLARE
            new_token TEXT;
        BEGIN
            LOOP
                new_token := 'CCF-MBR-' || upper(substring(gen_random_uuid()::text, 1, 8));
                IF NOT EXISTS (SELECT 1 FROM members WHERE qr_token = new_token) THEN
                    RETURN new_token;
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Calculate member engagement score
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_member_engagement_score(
            p_member_id INT
        )
        RETURNS TABLE (
            score FLOAT,
            events_90d BIGINT,
            enrollments_active BIGINT,
            communications_30d BIGINT,
            donations_90d BIGINT
        ) AS $$
        DECLARE
            m RECORD;
        BEGIN
            SELECT * FROM mv_member_engagement WHERE member_id = p_member_id INTO m;
            IF FOUND THEN
                score := LEAST(100,
                    LEAST(m.events_90d, 10) * 3 +
                    LEAST(m.active_enrollments, 5) * 8 +
                    LEAST(m.communications_30d, 10) * 2 +
                    LEAST(m.donations_90d, 5) * 4
                );
                events_90d := m.events_90d;
                enrollments_active := m.active_enrollments;
                communications_30d := m.communications_30d;
                donations_90d := m.donations_90d;
                RETURN NEXT;
            ELSE
                score := 0;
                events_90d := 0;
                enrollments_active := 0;
                communications_30d := 0;
                donations_90d := 0;
                RETURN NEXT;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Kill idle connections older than N minutes
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_cleanup_idle_connections(
            p_idle_minutes INT DEFAULT 30
        )
        RETURNS INT AS $$
        DECLARE
            killed INT := 0;
            r RECORD;
        BEGIN
            FOR r IN
                SELECT pid, now() - state_change AS idle_duration
                FROM pg_stat_activity
                WHERE state = 'idle'
                    AND state_change < NOW() - (p_idle_minutes || ' minutes')::INTERVAL
                    AND pid != pg_backend_pid()
                    AND usename != 'ccf_admin'  -- Don't kill admin connections
            LOOP
                PERFORM pg_terminate_backend(r.pid);
                killed := killed + 1;
            END LOOP;
            RETURN killed;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # ─────────────────────────────────────────────
    # 4. ANALYZE — update planner stats
    # ─────────────────────────────────────────────
    op.execute("ANALYZE")


def downgrade() -> None:
    # Drop indexes created in this migration
    fk_indexes = [
        "ix_academy_activity_logs_course_id",
        "ix_academy_activity_logs_user_id",
        "ix_admin_audit_logs_actor_user_id",
        "ix_assessment_answers_question_id",
        "ix_assessment_answers_selected_option_id",
        "ix_cms_media_items_created_by",
        "ix_cms_page_versions_created_by",
        "ix_cms_pages_created_by",
        "ix_cms_pages_published_version_id",
        "ix_cms_pages_updated_by",
        "ix_cms_publish_logs_actor_user_id",
        "ix_cms_themes_created_by",
        "ix_consolidation_pipeline_assigned_pastor_id",
        "ix_content_publications_updated_by",
        "ix_course_attendance_recorded_by_id",
        "ix_crm_events_target_role_id",
        "ix_formal_actas_closed_by_user_id",
        "ix_formal_actas_course_id",
        "ix_forum_comments_author_id",
        "ix_forum_comments_thread_id",
        "ix_forum_threads_author_id",
        "ix_maintenance_logs_item_id",
        "ix_members_family_id",
        "ix_ministries_leader_id",
        "ix_page_content_versions_page_content_id",
        "ix_pastoral_call_logs_pastor_id",
        "ix_project_activity_logs_user_id",
        "ix_project_attachments_uploader_id",
        "ix_project_comments_author_id",
        "ix_project_comments_task_id",
        "ix_project_documents_author_id",
        "ix_projects_owner_id",
        "ix_resources_course_id",
        "ix_resources_lesson_id",
        "ix_testimonials_author_id",
        "ix_user_badges_badge_id",
        "ix_users_current_level_id",
        "ix_users_role_id",
        "ix_volunteers_member_id",
    ]
    for idx_name in fk_indexes:
        op.execute(f"DROP INDEX IF EXISTS {idx_name}")

    # Drop triggers
    conn = op.get_bind()
    tables_with_updated_at = conn.execute(
        sa.text(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND column_name = 'updated_at' "
            "AND table_name NOT LIKE 'pg_%' AND table_name != 'alembic_version' "
            "ORDER BY table_name"
        )
    ).fetchall()
    for (table_name,) in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS tr_set_updated_at ON {table_name}")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS fn_cleanup_idle_connections(INT)")
    op.execute("DROP FUNCTION IF EXISTS fn_member_engagement_score(INT)")
    op.execute("DROP FUNCTION IF EXISTS fn_generate_qr_token()")
    op.execute("DROP FUNCTION IF EXISTS fn_search_members(TEXT, INT) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS fn_set_updated_at()")

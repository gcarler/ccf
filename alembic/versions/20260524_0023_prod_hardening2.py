"""Production DB hardening round 2: audit triggers, full-text search, constraints, sequences

This migration adds enterprise-grade features:

1. AUDIT TRIGGERS — automatic audit logging on sensitive tables
2. FULL-TEXT SEARCH — tsvector columns + GIN indexes for member search
3. CHECK CONSTRAINTS — data integrity at the database level
4. SEQUENCE OPTIMIZATION — CACHE for high-throughput tables
5. ADDITIONAL INDEXES — covering indexes for common query patterns

Revision ID: 20260524_0023_prod_hardening2
Revises: 20260524_0022_prod_hardening
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260524_0023_prod_hardening2"
down_revision: Union[str, None] = "b3d39dd6263e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = set()
    for table in inspector.get_table_names():
        for idx in inspector.get_indexes(table):
            existing_indexes.add(idx["name"])

    existing_constraints = set()
    for table in inspector.get_table_names():
        for c in inspector.get_check_constraints(table):
            existing_constraints.add(c["name"])

    # ─────────────────────────────────────────────
    # 1. AUDIT TRIGGER FUNCTION
    # ─────────────────────────────────────────────
    # Generic trigger that logs all changes to admin_audit_logs
    # Automatically captures old/new values as JSONB

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_audit_trigger()
        RETURNS TRIGGER AS $$
        DECLARE
            actor_id INTEGER;
            action_data JSONB;
            severity TEXT := 'info';
        BEGIN
            -- Try to get actor from NEW/OLD (for FK relationships)
            actor_id := COALESCE(
                (SELECT id FROM users WHERE id = COALESCE(NEW.actor_user_id, OLD.actor_user_id) LIMIT 1),
                1  -- Default to system user if no actor found
            );

            IF (TG_OP = 'INSERT') THEN
                action_data := to_jsonb(NEW);
                -- Determine severity based on table
                IF TG_TABLE_NAME IN ('users', 'donations', 'certificates') THEN
                    severity := 'high';
                END IF;
                INSERT INTO admin_audit_logs (
                    actor_user_id, action, resource_type, resource_id,
                    action_data, severity, created_at, updated_at
                ) VALUES (
                    actor_id, 'INSERT', TG_TABLE_NAME,
                    COALESCE(NEW.id::text, '0'),
                    action_data,
                    severity,
                    NOW(), NOW()
                );
                RETURN NEW;
            ELSIF (TG_OP = 'UPDATE') THEN
                -- Only log if there are actual changes
                IF to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
                    action_data := jsonb_build_object(
                        'old', to_jsonb(OLD),
                        'new', to_jsonb(NEW),
                        'changed_fields', (
                            SELECT jsonb_object_agg(key, jsonb_build_object('old', old_val, 'new', new_val))
                            FROM jsonb_each(to_jsonb(OLD)) AS old_row(key, old_val)
                            JOIN jsonb_each(to_jsonb(NEW)) AS new_row(key, new_val) USING (key)
                            WHERE old_val IS DISTINCT FROM new_val
                        )
                    );
                    IF TG_TABLE_NAME IN ('users', 'donations', 'certificates') THEN
                        severity := 'high';
                    END IF;
                    INSERT INTO admin_audit_logs (
                        actor_user_id, action, resource_type, resource_id,
                        action_data, severity, created_at, updated_at
                    ) VALUES (
                        actor_id, 'UPDATE', TG_TABLE_NAME,
                        COALESCE(NEW.id::text, OLD.id::text),
                        action_data,
                        severity,
                        NOW(), NOW()
                    );
                END IF;
                RETURN NEW;
            ELSIF (TG_OP = 'DELETE') THEN
                action_data := to_jsonb(OLD);
                IF TG_TABLE_NAME IN ('users', 'donations', 'certificates') THEN
                    severity := 'critical';
                END IF;
                INSERT INTO admin_audit_logs (
                    actor_user_id, action, resource_type, resource_id,
                    action_data, severity, created_at, updated_at
                ) VALUES (
                    actor_id, 'DELETE', TG_TABLE_NAME,
                    COALESCE(OLD.id::text, '0'),
                    action_data,
                    severity,
                    NOW(), NOW()
                );
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # ─────────────────────────────────────────────
    # 2. ATTACH AUDIT TRIGGERS TO SENSITIVE TABLES
    # ─────────────────────────────────────────────
    audit_tables = [
        "members", "users", "donations", "enrollments",
        "courses", "certificates", "consolidation_cases",
        "projects", "project_tasks", "crm_events",
        "grupos_evangelismo", "families",
    ]

    for table_name in audit_tables:
        if table_name in inspector.get_table_names():
            # Check if trigger already exists using a simple query
            existing = conn.execute(
                sa.text(
                    "SELECT count(*) FROM pg_trigger t "
                    "JOIN pg_class c ON t.tgrelid = c.oid "
                    "WHERE t.tgname = :name AND c.relname = :table_name"
                ),
                {"name": f"tr_audit_{table_name}", "table_name": table_name},
            ).scalar()
            if existing == 0:
                op.execute(
                    f"""
                    CREATE TRIGGER tr_audit_{table_name}
                    AFTER INSERT OR UPDATE OR DELETE ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger()
                    """
                )

    # ─────────────────────────────────────────────
    # 3. FULL-TEXT SEARCH: tsvector on members
    # ─────────────────────────────────────────────

    # Add tsvector column to members for fast full-text search
    op.execute(
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS search_vector tsvector "
        "GENERATED ALWAYS AS ("
        "  setweight(to_tsvector('spanish', coalesce(first_name, '')), 'A') || "
        "  setweight(to_tsvector('spanish', coalesce(last_name, '')), 'A') || "
        "  setweight(to_tsvector('spanish', coalesce(email, '')), 'B') || "
        "  setweight(to_tsvector('spanish', coalesce(phone, '')), 'C') || "
        "  setweight(to_tsvector('spanish', coalesce(church_role, '')), 'D')"
        ") STORED"
    )

    # GIN index on tsvector for fast full-text search
    if "idx_members_search_vector" not in existing_indexes:
        op.execute(
            "CREATE INDEX idx_members_search_vector ON members "
            "USING GIN (search_vector)"
        )

    # ─────────────────────────────────────────────
    # 4. CHECK CONSTRAINTS — data integrity at DB level
    # ─────────────────────────────────────────────

    # Enrollments: progress must be 0-100
    if "chk_enrollments_progress_range" not in existing_constraints:
        op.execute(
            "ALTER TABLE enrollments ADD CONSTRAINT chk_enrollments_progress_range "
            "CHECK (progress_percent >= 0 AND progress_percent <= 100)"
        )

    # Donations: amount must be positive
    if "chk_donations_amount_positive" not in existing_constraints:
        op.execute(
            "ALTER TABLE donations ADD CONSTRAINT chk_donations_amount_positive "
            "CHECK (amount >= 0)"
        )

    # Assessments: passing_score must be <= max_score
    if "chk_assessments_score_valid" not in existing_constraints:
        op.execute(
            "ALTER TABLE assessments ADD CONSTRAINT chk_assessments_score_valid "
            "CHECK (passing_score <= max_score AND max_score > 0)"
        )

    # CRM Events: status must be one of known values
    if "chk_crm_events_status" not in existing_constraints:
        op.execute(
            "ALTER TABLE crm_events ADD CONSTRAINT chk_crm_events_status "
            "CHECK (status IN ('active', 'cancelled', 'completed', 'draft'))"
        )

    # Consolidation cases: stage must be valid
    if "chk_consolidation_cases_stage" not in existing_constraints:
        op.execute(
            "ALTER TABLE consolidation_cases ADD CONSTRAINT chk_consolidation_cases_stage "
            "CHECK (stage IN ('new', 'contacted', 'following_up', 'consolidated', 'lost'))"
        )

    # Project tasks: priority must be valid
    if "chk_project_tasks_priority" not in existing_constraints:
        op.execute(
            "ALTER TABLE project_tasks ADD CONSTRAINT chk_project_tasks_priority "
            "CHECK (priority IN ('low', 'medium', 'high', 'urgent'))"
        )

    # Project tasks: status must be valid
    if "chk_project_tasks_status" not in existing_constraints:
        op.execute(
            "ALTER TABLE project_tasks ADD CONSTRAINT chk_project_tasks_status "
            "CHECK (status IN ('todo', 'in_progress', 'review', 'completed', 'cancelled'))"
        )

    # ─────────────────────────────────────────────
    # 5. SEQUENCE OPTIMIZATION — CACHE for performance
    # ─────────────────────────────────────────────
    # High-throughput tables benefit from sequence caching

    sequences = [
        ("members_id_seq", 10),
        ("enrollments_id_seq", 10),
        ("crm_events_id_seq", 10),
        ("project_tasks_id_seq", 20),
        ("assessment_attempts_id_seq", 20),
        ("attendance_id_seq", 20),
        ("admin_audit_logs_id_seq", 20),
        ("notifications_id_seq", 20),
        ("event_attendances_id_seq", 20),
    ]

    for seq_name, cache_value in sequences:
        try:
            conn.execute(sa.text(f"ALTER SEQUENCE {seq_name} CACHE {cache_value}"))
        except Exception:
            pass  # Sequence might not exist or already set

    # ─────────────────────────────────────────────
    # 6. ADDITIONAL STRATEGIC INDEXES
    # ─────────────────────────────────────────────

    # CRM: Pastoral call logs by date (timeline queries)
    if "ix_pastoral_call_logs_date" not in existing_indexes:
        op.create_index(
            "ix_pastoral_call_logs_date",
            "pastoral_call_logs",
            ["created_at"],
        )

    # Academy: Lesson progress by user + course (learning dashboard)
    if "ix_lesson_progress_user_course" not in existing_indexes:
        op.create_index(
            "ix_lesson_progress_user_course",
            "lesson_progress",
            ["user_id", "lesson_id"],
        )

    # Assessment attempts by enrollment (grading workflow)
    if "ix_assessment_attempts_enrollment" not in existing_indexes:
        op.create_index(
            "ix_assessment_attempts_enrollment",
            "assessment_attempts",
            ["enrollment_id", "created_at"],
        )

    # Forum threads by category + resolved (community queries)
    if "ix_forum_threads_category_resolved" not in existing_indexes:
        op.create_index(
            "ix_forum_threads_category_resolved",
            "forum_threads",
            ["category", "is_resolved"],
        )

    # Course attendance by date + enrollment (attendance reports)
    if "ix_course_attendance_enrollment_date" not in existing_indexes:
        op.create_index(
            "ix_course_attendance_enrollment_date",
            "course_attendance",
            ["enrollment_id", "session_date"],
        )

    # ─────────────────────────────────────────────
    # 7. ANALYZE — update query planner statistics
    # ─────────────────────────────────────────────
    op.execute("ANALYZE")


def downgrade() -> None:
    # Drop additional indexes
    indexes_to_drop = [
        "idx_members_search_vector",
        "ix_pastoral_call_logs_date",
        "ix_lesson_progress_user_course",
        "ix_assessment_attempts_enrollment",
        "ix_forum_threads_category_resolved",
        "ix_course_attendance_enrollment_date",
    ]
    for idx_name in indexes_to_drop:
        op.execute(f"DROP INDEX IF EXISTS {idx_name}")

    # Drop check constraints
    op.execute("ALTER TABLE enrollments DROP CONSTRAINT IF EXISTS chk_enrollments_progress_range")
    op.execute("ALTER TABLE donations DROP CONSTRAINT IF EXISTS chk_donations_amount_positive")
    op.execute("ALTER TABLE assessments DROP CONSTRAINT IF EXISTS chk_assessments_score_valid")
    op.execute("ALTER TABLE crm_events DROP CONSTRAINT IF EXISTS chk_crm_events_status")
    op.execute("ALTER TABLE consolidation_cases DROP CONSTRAINT IF EXISTS chk_consolidation_cases_stage")
    op.execute("ALTER TABLE project_tasks DROP CONSTRAINT IF EXISTS chk_project_tasks_priority")
    op.execute("ALTER TABLE project_tasks DROP CONSTRAINT IF EXISTS chk_project_tasks_status")

    # Drop search_vector column
    op.execute("ALTER TABLE members DROP COLUMN IF EXISTS search_vector")

    # Drop audit triggers
    audit_tables = [
        "members", "users", "donations", "enrollments",
        "courses", "certificates", "consolidation_cases",
        "projects", "project_tasks", "crm_events",
        "grupos_evangelismo", "families",
    ]
    for table_name in audit_tables:
        op.execute(f"DROP TRIGGER IF EXISTS tr_audit_{table_name} ON {table_name}")

    # Drop audit trigger function
    op.execute("DROP FUNCTION IF EXISTS fn_audit_trigger()")

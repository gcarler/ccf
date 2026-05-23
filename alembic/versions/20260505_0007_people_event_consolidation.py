"""create people-event and consolidation tables

Revision ID: 20260505_0007
Revises: 20260504_0006
Create Date: 2026-05-05 09:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260505_0007"
down_revision = "20260504_0006"
branch_labels = None
depends_on = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "positions"):
        op.create_table(
            "positions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index("ix_positions_name", "positions", ["name"], unique=False)
        op.create_index(
            "ix_positions_category", "positions", ["category"], unique=False
        )
        op.create_index(
            "ix_positions_is_active", "positions", ["is_active"], unique=False
        )
        op.create_index(
            "ix_positions_created_at", "positions", ["created_at"], unique=False
        )

    if not _has_table(inspector, "member_positions"):
        op.create_table(
            "member_positions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("position_id", sa.Integer(), nullable=False),
            sa.Column("start_date", sa.DateTime(), nullable=True),
            sa.Column("end_date", sa.DateTime(), nullable=True),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["position_id"], ["positions.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "member_id",
                "position_id",
                "start_date",
                name="uq_member_position_history",
            ),
        )
        op.create_index(
            "ix_member_positions_member_id",
            "member_positions",
            ["member_id"],
            unique=False,
        )
        op.create_index(
            "ix_member_positions_position_id",
            "member_positions",
            ["position_id"],
            unique=False,
        )
        op.create_index(
            "ix_member_positions_start_date",
            "member_positions",
            ["start_date"],
            unique=False,
        )
        op.create_index(
            "ix_member_positions_end_date",
            "member_positions",
            ["end_date"],
            unique=False,
        )
        op.create_index(
            "ix_member_positions_is_active",
            "member_positions",
            ["is_active"],
            unique=False,
        )
        op.create_index(
            "ix_member_positions_created_at",
            "member_positions",
            ["created_at"],
            unique=False,
        )

    if not _has_table(inspector, "event_attendances"):
        op.create_table(
            "event_attendances",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'present'"),
            ),
            sa.Column(
                "role_at_event",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'attendee'"),
            ),
            sa.Column(
                "source",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'manual'"),
            ),
            sa.Column("check_in_at", sa.DateTime(), nullable=True),
            sa.Column("check_out_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "scanned_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "attended", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.ForeignKeyConstraint(
                ["event_id"], ["crm_events.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "event_id", "session_date", "member_id", name="uq_event_attendance"
            ),
        )
        op.create_index(
            "ix_event_attendances_event_id",
            "event_attendances",
            ["event_id"],
            unique=False,
        )
        op.create_index(
            "ix_event_attendances_session_date",
            "event_attendances",
            ["session_date"],
            unique=False,
        )
        op.create_index(
            "ix_event_attendances_member_id",
            "event_attendances",
            ["member_id"],
            unique=False,
        )
        op.create_index(
            "ix_event_attendances_status", "event_attendances", ["status"], unique=False
        )
        op.create_index(
            "ix_event_attendances_role_at_event",
            "event_attendances",
            ["role_at_event"],
            unique=False,
        )
        op.create_index(
            "ix_event_attendances_source", "event_attendances", ["source"], unique=False
        )
        op.create_index(
            "ix_event_attendances_check_in_at",
            "event_attendances",
            ["check_in_at"],
            unique=False,
        )
        op.create_index(
            "ix_event_attendances_check_out_at",
            "event_attendances",
            ["check_out_at"],
            unique=False,
        )
        op.create_index(
            "ix_event_attendances_scanned_at",
            "event_attendances",
            ["scanned_at"],
            unique=False,
        )
        op.create_index(
            "ix_event_attendances_attended",
            "event_attendances",
            ["attended"],
            unique=False,
        )

    if not _has_table(inspector, "consolidation_cases"):
        op.create_table(
            "consolidation_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column(
                "stage",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'new'"),
            ),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("last_contact_at", sa.DateTime(), nullable=True),
            sa.Column("next_contact_at", sa.DateTime(), nullable=True),
            sa.Column("assigned_pastor_id", sa.Integer(), nullable=True),
            sa.Column("assigned_leader_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["assigned_pastor_id"], ["members.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["assigned_leader_id"], ["members.id"], ondelete="SET NULL"
            ),
        )
        op.create_index(
            "ix_consolidation_cases_member_id",
            "consolidation_cases",
            ["member_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_stage",
            "consolidation_cases",
            ["stage"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_status",
            "consolidation_cases",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_source",
            "consolidation_cases",
            ["source"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_last_contact_at",
            "consolidation_cases",
            ["last_contact_at"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_next_contact_at",
            "consolidation_cases",
            ["next_contact_at"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_assigned_pastor_id",
            "consolidation_cases",
            ["assigned_pastor_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_assigned_leader_id",
            "consolidation_cases",
            ["assigned_leader_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_created_at",
            "consolidation_cases",
            ["created_at"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_cases_updated_at",
            "consolidation_cases",
            ["updated_at"],
            unique=False,
        )

    if not _has_table(inspector, "consolidation_assignments"):
        op.create_table(
            "consolidation_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), nullable=False),
            sa.Column("assigned_by_member_id", sa.Integer(), nullable=False),
            sa.Column("assigned_to_member_id", sa.Integer(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column(
                "priority",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'normal'"),
            ),
            sa.Column(
                "start_date",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("end_date", sa.DateTime(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["case_id"], ["consolidation_cases.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["assigned_by_member_id"], ["members.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["assigned_to_member_id"], ["members.id"], ondelete="CASCADE"
            ),
        )
        op.create_index(
            "ix_consolidation_assignments_case_id",
            "consolidation_assignments",
            ["case_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_assignments_assigned_by_member_id",
            "consolidation_assignments",
            ["assigned_by_member_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_assignments_assigned_to_member_id",
            "consolidation_assignments",
            ["assigned_to_member_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_assignments_priority",
            "consolidation_assignments",
            ["priority"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_assignments_start_date",
            "consolidation_assignments",
            ["start_date"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_assignments_end_date",
            "consolidation_assignments",
            ["end_date"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_assignments_status",
            "consolidation_assignments",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_assignments_created_at",
            "consolidation_assignments",
            ["created_at"],
            unique=False,
        )

    if not _has_table(inspector, "consolidation_interactions"):
        op.create_table(
            "consolidation_interactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), nullable=False),
            sa.Column("performed_by_member_id", sa.Integer(), nullable=False),
            sa.Column("interaction_type", sa.String(length=50), nullable=False),
            sa.Column(
                "interaction_date",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("result", sa.String(length=100), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("next_action_date", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["case_id"], ["consolidation_cases.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["performed_by_member_id"], ["members.id"], ondelete="CASCADE"
            ),
        )
        op.create_index(
            "ix_consolidation_interactions_case_id",
            "consolidation_interactions",
            ["case_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_interactions_performed_by_member_id",
            "consolidation_interactions",
            ["performed_by_member_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_interactions_interaction_type",
            "consolidation_interactions",
            ["interaction_type"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_interactions_interaction_date",
            "consolidation_interactions",
            ["interaction_date"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_interactions_next_action_date",
            "consolidation_interactions",
            ["next_action_date"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_interactions_created_at",
            "consolidation_interactions",
            ["created_at"],
            unique=False,
        )

    if not _has_table(inspector, "consolidation_follow_up_tasks"):
        op.create_table(
            "consolidation_follow_up_tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), nullable=False),
            sa.Column("assignment_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("due_date", sa.DateTime(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["case_id"], ["consolidation_cases.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["assignment_id"], ["consolidation_assignments.id"], ondelete="SET NULL"
            ),
        )
        op.create_index(
            "ix_consolidation_follow_up_tasks_case_id",
            "consolidation_follow_up_tasks",
            ["case_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_follow_up_tasks_assignment_id",
            "consolidation_follow_up_tasks",
            ["assignment_id"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_follow_up_tasks_due_date",
            "consolidation_follow_up_tasks",
            ["due_date"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_follow_up_tasks_status",
            "consolidation_follow_up_tasks",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_follow_up_tasks_completed_at",
            "consolidation_follow_up_tasks",
            ["completed_at"],
            unique=False,
        )
        op.create_index(
            "ix_consolidation_follow_up_tasks_created_at",
            "consolidation_follow_up_tasks",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "consolidation_follow_up_tasks"):
        op.drop_index(
            "ix_consolidation_follow_up_tasks_created_at",
            table_name="consolidation_follow_up_tasks",
        )
        op.drop_index(
            "ix_consolidation_follow_up_tasks_completed_at",
            table_name="consolidation_follow_up_tasks",
        )
        op.drop_index(
            "ix_consolidation_follow_up_tasks_status",
            table_name="consolidation_follow_up_tasks",
        )
        op.drop_index(
            "ix_consolidation_follow_up_tasks_due_date",
            table_name="consolidation_follow_up_tasks",
        )
        op.drop_index(
            "ix_consolidation_follow_up_tasks_assignment_id",
            table_name="consolidation_follow_up_tasks",
        )
        op.drop_index(
            "ix_consolidation_follow_up_tasks_case_id",
            table_name="consolidation_follow_up_tasks",
        )
        op.drop_table("consolidation_follow_up_tasks")

    if _has_table(inspector, "consolidation_interactions"):
        op.drop_index(
            "ix_consolidation_interactions_created_at",
            table_name="consolidation_interactions",
        )
        op.drop_index(
            "ix_consolidation_interactions_next_action_date",
            table_name="consolidation_interactions",
        )
        op.drop_index(
            "ix_consolidation_interactions_interaction_date",
            table_name="consolidation_interactions",
        )
        op.drop_index(
            "ix_consolidation_interactions_interaction_type",
            table_name="consolidation_interactions",
        )
        op.drop_index(
            "ix_consolidation_interactions_performed_by_member_id",
            table_name="consolidation_interactions",
        )
        op.drop_index(
            "ix_consolidation_interactions_case_id",
            table_name="consolidation_interactions",
        )
        op.drop_table("consolidation_interactions")

    if _has_table(inspector, "consolidation_assignments"):
        op.drop_index(
            "ix_consolidation_assignments_created_at",
            table_name="consolidation_assignments",
        )
        op.drop_index(
            "ix_consolidation_assignments_status",
            table_name="consolidation_assignments",
        )
        op.drop_index(
            "ix_consolidation_assignments_end_date",
            table_name="consolidation_assignments",
        )
        op.drop_index(
            "ix_consolidation_assignments_start_date",
            table_name="consolidation_assignments",
        )
        op.drop_index(
            "ix_consolidation_assignments_priority",
            table_name="consolidation_assignments",
        )
        op.drop_index(
            "ix_consolidation_assignments_assigned_to_member_id",
            table_name="consolidation_assignments",
        )
        op.drop_index(
            "ix_consolidation_assignments_assigned_by_member_id",
            table_name="consolidation_assignments",
        )
        op.drop_index(
            "ix_consolidation_assignments_case_id",
            table_name="consolidation_assignments",
        )
        op.drop_table("consolidation_assignments")

    if _has_table(inspector, "consolidation_cases"):
        op.drop_index(
            "ix_consolidation_cases_updated_at", table_name="consolidation_cases"
        )
        op.drop_index(
            "ix_consolidation_cases_created_at", table_name="consolidation_cases"
        )
        op.drop_index(
            "ix_consolidation_cases_assigned_leader_id",
            table_name="consolidation_cases",
        )
        op.drop_index(
            "ix_consolidation_cases_assigned_pastor_id",
            table_name="consolidation_cases",
        )
        op.drop_index(
            "ix_consolidation_cases_next_contact_at", table_name="consolidation_cases"
        )
        op.drop_index(
            "ix_consolidation_cases_last_contact_at", table_name="consolidation_cases"
        )
        op.drop_index("ix_consolidation_cases_source", table_name="consolidation_cases")
        op.drop_index("ix_consolidation_cases_status", table_name="consolidation_cases")
        op.drop_index("ix_consolidation_cases_stage", table_name="consolidation_cases")
        op.drop_index(
            "ix_consolidation_cases_member_id", table_name="consolidation_cases"
        )
        op.drop_table("consolidation_cases")

    if _has_table(inspector, "event_attendances"):
        op.drop_index("ix_event_attendances_attended", table_name="event_attendances")
        op.drop_index("ix_event_attendances_scanned_at", table_name="event_attendances")
        op.drop_index(
            "ix_event_attendances_check_out_at", table_name="event_attendances"
        )
        op.drop_index(
            "ix_event_attendances_check_in_at", table_name="event_attendances"
        )
        op.drop_index("ix_event_attendances_source", table_name="event_attendances")
        op.drop_index(
            "ix_event_attendances_role_at_event", table_name="event_attendances"
        )
        op.drop_index("ix_event_attendances_status", table_name="event_attendances")
        op.drop_index("ix_event_attendances_member_id", table_name="event_attendances")
        op.drop_index(
            "ix_event_attendances_session_date", table_name="event_attendances"
        )
        op.drop_index("ix_event_attendances_event_id", table_name="event_attendances")
        op.drop_table("event_attendances")

    if _has_table(inspector, "member_positions"):
        op.drop_index("ix_member_positions_created_at", table_name="member_positions")
        op.drop_index("ix_member_positions_is_active", table_name="member_positions")
        op.drop_index("ix_member_positions_end_date", table_name="member_positions")
        op.drop_index("ix_member_positions_start_date", table_name="member_positions")
        op.drop_index("ix_member_positions_position_id", table_name="member_positions")
        op.drop_index("ix_member_positions_member_id", table_name="member_positions")
        op.drop_table("member_positions")

    if _has_table(inspector, "positions"):
        op.drop_index("ix_positions_created_at", table_name="positions")
        op.drop_index("ix_positions_is_active", table_name="positions")
        op.drop_index("ix_positions_category", table_name="positions")
        op.drop_index("ix_positions_name", table_name="positions")
        op.drop_table("positions")

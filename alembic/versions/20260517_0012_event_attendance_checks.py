"""add check constraints for event attendance consistency

Revision ID: 20260517_0012
Revises: 20260516_0011
Create Date: 2026-05-17 09:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_0012"
down_revision = "20260516_0011"
branch_labels = None
depends_on = None


def _has_check_constraint(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    for constraint in inspector.get_check_constraints(table_name):
        if constraint.get("name") == constraint_name:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("event_attendances"):
        return

    if not _has_check_constraint(inspector, "event_attendances", "ck_event_attendances_status_allowed"):
        with op.batch_alter_table("event_attendances") as batch_op:
            batch_op.create_check_constraint(
                "ck_event_attendances_status_allowed",
                "status IN ('present', 'absent')",
            )
        inspector = sa.inspect(bind)

    if not _has_check_constraint(inspector, "event_attendances", "ck_event_attendances_attended_matches_status"):
        with op.batch_alter_table("event_attendances") as batch_op:
            batch_op.create_check_constraint(
                "ck_event_attendances_attended_matches_status",
                "(attended = 1 AND status = 'present') OR (attended = 0 AND status = 'absent')",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("event_attendances"):
        return

    if _has_check_constraint(inspector, "event_attendances", "ck_event_attendances_attended_matches_status"):
        with op.batch_alter_table("event_attendances") as batch_op:
            batch_op.drop_constraint("ck_event_attendances_attended_matches_status", type_="check")
        inspector = sa.inspect(bind)

    if _has_check_constraint(inspector, "event_attendances", "ck_event_attendances_status_allowed"):
        with op.batch_alter_table("event_attendances") as batch_op:
            batch_op.drop_constraint("ck_event_attendances_status_allowed", type_="check")

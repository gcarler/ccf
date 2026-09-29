"""Evangelism: Add registration_number to event_registrations.

Revision ID: 20260926_0011_event_registrations_registration_number
Revises: 20260926_0010_projects_boveda_documental_files
Create Date: 2026-09-26 19:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0011_event_registrations_registration_number"
down_revision: Union[str, None] = "20260926_0010_projects_boveda_documental_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column("registration_number", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_event_registrations_event_reg_num",
        "event_registrations",
        ["event_id", "registration_number"],
    )

    # Backfill existing rows with consecutive numbers per event
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        conn.execute(sa.text("""
            UPDATE event_registrations er
            SET registration_number = sub.rn
            FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY created_at ASC) as rn
                FROM event_registrations
            ) sub
            WHERE er.id = sub.id AND er.registration_number IS NULL;
        """))
    else:
        # Generic fallback for SQLite / other dialects
        try:
            conn.execute(sa.text("""
                UPDATE event_registrations
                SET registration_number = (
                    SELECT COUNT(*)
                    FROM event_registrations AS r2
                    WHERE r2.event_id = event_registrations.event_id
                      AND (r2.created_at < event_registrations.created_at
                           OR (r2.created_at = event_registrations.created_at AND r2.id <= event_registrations.id))
                )
                WHERE registration_number IS NULL;
            """))
        except Exception:
            pass


def downgrade() -> None:
    op.drop_index("ix_event_registrations_event_reg_num", table_name="event_registrations")
    op.drop_column("event_registrations", "registration_number")

"""Add missing columns to match SQLAlchemy models — critical path tables

Adds columns that exist in models but are missing from the production PostgreSQL
schema. These are actively referenced by API code (messaging, grupos,
pastoral calls, etc.) and would cause UndefinedColumn errors at runtime.

Revision ID: 20260524_0029
Revises: 20260524_0028
Create Date: 2026-05-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "20260524_0029"
down_revision = "20260524_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- communication_logs (used by MessagingGateway) ---
    op.add_column(
        "communication_logs",
        sa.Column("campaign_name", sa.String(120), nullable=True, index=True),
    )
    op.add_column(
        "communication_logs",
        sa.Column("external_id", sa.String(120), nullable=True, index=True),
    )
    op.add_column(
        "communication_logs",
        sa.Column("is_read", sa.Boolean(), default=False, index=True),
    )
    op.add_column(
        "communication_logs",
        sa.Column(
            "leader_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True
        ),
    )
    op.add_column(
        "communication_logs",
        sa.Column("outcome", sa.String(50), default="sent", index=True),
    )
    op.add_column(
        "communication_logs",
        sa.Column("recipient_phone", sa.String(30), nullable=True),
    )

    # --- grupos_evangelismo (used by CRM grupo endpoints) ---
    op.add_column(
        "grupos_evangelismo",
        sa.Column("code", sa.String(30), nullable=True, unique=True, index=True),
    )
    op.add_column(
        "grupos_evangelismo",
        sa.Column("address", sa.String(255), nullable=True),
    )
    op.add_column(
        "grupos_evangelismo",
        sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
    )
    op.add_column(
        "grupos_evangelismo",
        sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
    )
    op.add_column(
        "grupos_evangelismo",
        sa.Column("day_of_week", sa.String(20), nullable=True),
    )
    op.add_column(
        "grupos_evangelismo",
        sa.Column("start_time", sa.String(50), nullable=True),
    )
    op.add_column(
        "grupos_evangelismo",
        sa.Column("end_time", sa.String(50), nullable=True),
    )

    # --- pastoral_call_logs (used by pipeline call creation endpoint) ---
    op.add_column(
        "pastoral_call_logs",
        sa.Column("duration_seconds", sa.Integer(), default=0),
    )

    # --- donations (used by Donation model) ---
    op.add_column(
        "donations",
        sa.Column("fund_id", sa.Integer(), nullable=True, index=True),
    )
    op.add_column(
        "donations",
        sa.Column(
            "member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=True, index=True
        ),
    )
    op.add_column(
        "donations",
        sa.Column("payment_method", sa.String(50), nullable=True),
    )
    op.add_column(
        "donations",
        sa.Column("person_id", sa.Integer(), nullable=True, index=True),
    )
    op.add_column(
        "donations",
        sa.Column("reference_code", sa.String(100), nullable=True),
    )

    # --- announcements (used by Announcement model) ---
    op.add_column(
        "announcements",
        sa.Column("is_featured", sa.Boolean(), default=False),
    )
    op.add_column(
        "announcements",
        sa.Column("published_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "announcements",
        sa.Column("status", sa.String(20), default="draft"),
    )

    # --- formal_actas (used by FormalActa model) ---
    op.add_column(
        "formal_actas",
        sa.Column("min_attendance_required", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "formal_actas",
        sa.Column("min_grade_required", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "formal_actas",
        sa.Column("status", sa.String(20), default="draft"),
    )

    # --- page_content_versions ---
    op.add_column(
        "page_content_versions",
        sa.Column("page_key", sa.String(120), nullable=True, index=True),
    )

    # --- content_metrics ---
    op.add_column(
        "content_metrics",
        sa.Column("metric_key", sa.String(120), nullable=True, index=True),
    )
    op.add_column(
        "content_metrics",
        sa.Column("ref_id", sa.Integer(), nullable=True, index=True),
    )

    # --- families ---
    op.add_column(
        "families",
        sa.Column("address", sa.Text(), nullable=True),
    )

    # --- assessment_attempts ---
    op.add_column(
        "assessment_attempts",
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    # assessment_attempts
    op.drop_column("assessment_attempts", "score")

    # families
    op.drop_column("families", "address")

    # content_metrics
    op.drop_column("content_metrics", "ref_id")
    op.drop_column("content_metrics", "metric_key")

    # page_content_versions
    op.drop_column("page_content_versions", "page_key")

    # formal_actas
    op.drop_column("formal_actas", "status")
    op.drop_column("formal_actas", "min_grade_required")
    op.drop_column("formal_actas", "min_attendance_required")

    # announcements
    op.drop_column("announcements", "status")
    op.drop_column("announcements", "published_at")
    op.drop_column("announcements", "is_featured")

    # donations
    op.drop_column("donations", "reference_code")
    op.drop_column("donations", "person_id")
    op.drop_column("donations", "payment_method")
    op.drop_column("donations", "member_id")
    op.drop_column("donations", "fund_id")

    # pastoral_call_logs
    op.drop_column("pastoral_call_logs", "duration_seconds")

    # grupos_evangelismo
    op.drop_column("grupos_evangelismo", "end_time")
    op.drop_column("grupos_evangelismo", "start_time")
    op.drop_column("grupos_evangelismo", "day_of_week")
    op.drop_column("grupos_evangelismo", "longitude")
    op.drop_column("grupos_evangelismo", "latitude")
    op.drop_column("grupos_evangelismo", "address")
    op.drop_column("grupos_evangelismo", "code")

    # communication_logs
    op.drop_column("communication_logs", "recipient_phone")
    op.drop_column("communication_logs", "outcome")
    op.drop_column("communication_logs", "leader_id")
    op.drop_column("communication_logs", "is_read")
    op.drop_column("communication_logs", "external_id")
    op.drop_column("communication_logs", "campaign_name")

"""Projects MGA/CREMA: Indicators and SPI Records."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "20260925_0008_projects_mga_crema_indicators"
down_revision: Union[str, None] = "20260924_0007_projects_super_pro_automations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_indicators",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("level", sa.String(50), server_default="PRODUCTO_PRINCIPAL", nullable=False),
        sa.Column("calculation_type", sa.String(50), server_default="ABSOLUTO_ACUMULADO", nullable=False),
        sa.Column("unit_of_measure", sa.String(50), nullable=True),
        sa.Column("baseline_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("target_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("current_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("frequency", sa.String(50), server_default="mensual", nullable=False),
        sa.Column("period_targets", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("crema_score", sa.Float(), nullable=True),
        sa.Column("crema_evaluation", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sede_id", UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_indicators_project_id", "project_indicators", ["project_id"])
    op.create_index("ix_project_indicators_code", "project_indicators", ["code"])
    op.create_index("ix_project_indicators_level", "project_indicators", ["level"])
    op.create_index("ix_project_indicators_calculation_type", "project_indicators", ["calculation_type"])
    op.create_index("ix_project_indicators_sede_id", "project_indicators", ["sede_id"])
    op.create_index("ix_project_indicators_created_by", "project_indicators", ["created_by"])
    op.create_index("ix_project_indicators_deleted_at", "project_indicators", ["deleted_at"])

    op.create_table(
        "project_indicator_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("indicator_id", UUID(as_uuid=True), sa.ForeignKey("project_indicators.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(50), nullable=False),
        sa.Column("target_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("actual_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("spi", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evidence_url", sa.String(500), nullable=True),
        sa.Column("reported_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_indicator_records_indicator_id", "project_indicator_records", ["indicator_id"])
    op.create_index("ix_project_indicator_records_period", "project_indicator_records", ["period"])
    op.create_index("ix_project_indicator_records_reported_by", "project_indicator_records", ["reported_by"])
    op.create_index("ix_project_indicator_records_deleted_at", "project_indicator_records", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("project_indicator_records")
    op.drop_table("project_indicators")

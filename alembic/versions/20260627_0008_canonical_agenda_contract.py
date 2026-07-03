"""Remove the parallel Agenda event table.

Revision ID: 20260627_0008_agenda_contract
Revises: 20260627_0007_cms_site_base_path
"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260627_0008_agenda_contract"
down_revision: str | None = "20260627_0007_cms_site_base_path"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    count = connection.execute(sa.text("SELECT COUNT(*) FROM agenda_events")).scalar_one()
    if count:
        raise RuntimeError(
            f"Cannot remove parallel Agenda table agenda_events: it contains {count} rows"
        )

    op.add_column(
        "agenda_recursos",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agenda_participantes",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agenda_reserva_recursos",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_table("agenda_events")


def downgrade() -> None:
    uuid_type = sa.Uuid()
    timestamp = sa.DateTime(timezone=True)
    op.create_table(
        "agenda_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_at", timestamp, nullable=False),
        sa.Column("end_at", timestamp, nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("is_all_day", sa.Boolean(), nullable=True),
        sa.Column(
            "created_by_persona_id",
            uuid_type,
            sa.ForeignKey("personas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", timestamp, nullable=True),
        sa.Column("updated_at", timestamp, nullable=True),
        sa.Column("deleted_at", timestamp, nullable=True),
    )
    op.drop_column("agenda_reserva_recursos", "deleted_at")
    op.drop_column("agenda_participantes", "deleted_at")
    op.drop_column("agenda_recursos", "deleted_at")

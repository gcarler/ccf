"""0041_consolidation_cleanup_pipeline_rename_tasks

Revision ID: 20260527_0041
Revises: 20260527_0040
Create Date: 2026-05-27

Elimina consolidation_pipeline, renombra consolidation_follow_up_tasks
a consolidation_tasks, y elimina columnas FK antiguas de tipo integer
en tablas de consolidacion reemplazándolas con UUID a personas.id.

Segura para ejecutar porque todas las tablas de consolidación tienen 0 filas.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0041"
down_revision: Union[str, None] = "20260527_0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()

    # ── 1. Drop consolidation_pipeline (replaced by Personas + ConsolidationCase) ──
    if "consolidation_pipeline" in tables:
        conn.execute(sa.text("DROP TABLE consolidation_pipeline CASCADE"))
        print("    ✓ Dropped consolidation_pipeline")

    # ── 2. Rename consolidation_follow_up_tasks → consolidation_tasks ──
    if "consolidation_follow_up_tasks" in tables and "consolidation_tasks" not in tables:
        op.rename_table("consolidation_follow_up_tasks", "consolidation_tasks")
        print("    ✓ Renamed consolidation_follow_up_tasks → consolidation_tasks")

    # ── 3. Drop old integer FK columns from consolidation tables ──
    # These columns no longer exist in the models; they were replaced by UUID columns
    # that are created by the standalone migration script.
    columns_to_drop = [
        ("consolidation_cases", "member_id"),
        ("consolidation_assignments", "assigned_by_member_id"),
        ("consolidation_assignments", "assigned_to_member_id"),
        ("consolidation_interactions", "performed_by_member_id"),
    ]
    for table, column in columns_to_drop:
        if table in tables:
            _drop_column_if_exists(table, column)

    # ── 4. Source_campaign column (if not already present) ──
    if "consolidation_cases" in tables:
        cols = [c["name"] for c in sa.inspect(conn).get_columns("consolidation_cases")]
        if "source_campaign" not in cols:
            op.add_column(
                "consolidation_cases",
                sa.Column("source_campaign", sa.String(200), nullable=True),
            )
            print("    ✓ Added consolidation_cases.source_campaign")


def downgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()

    # Reverse: recreate consolidation_pipeline
    if "consolidation_pipeline" not in tables:
        op.create_table(
            "consolidation_pipeline",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("first_name", sa.String(100), nullable=False),
            sa.Column("last_name", sa.String(100), nullable=False),
            sa.Column("phone", sa.String(20), nullable=False),
            sa.Column("source", sa.String(100), nullable=True),
            sa.Column("landing_page", sa.String(500), nullable=True),
            sa.Column("campaign", sa.String(200), nullable=True, index=True),
            sa.Column("stage", sa.String(20), default="new", index=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "assigned_pastor_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), default=sa.func.now()),
        )

    # Rename back
    if "consolidation_tasks" in tables:
        op.rename_table("consolidation_tasks", "consolidation_follow_up_tasks")

    # Drop source_campaign if present
    if "consolidation_cases" in tables:
        cols = [c["name"] for c in sa.inspect(conn).get_columns("consolidation_cases")]
        if "source_campaign" in cols:
            op.drop_column("consolidation_cases", "source_campaign")


def _drop_column_if_exists(table: str, column: str) -> None:
    """Drop a column if it exists, ignoring errors."""
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns(table)]
    if column in cols:
        op.drop_column(table, column)
        print(f"    ✓ Dropped {table}.{column}")

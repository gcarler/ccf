"""Use UUID for the canonical evangelism strategy and remove orphan cell groups.

Revision ID: 20260627_0010_strategy_uuid
Revises: 20260627_0009_auth_roles
"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260627_0010_strategy_uuid"
down_revision: str | None = "20260627_0009_auth_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UUID_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def _assert_uuid_values(connection, table: str, column: str) -> None:
    invalid = connection.execute(
        sa.text(
            f'SELECT COUNT(*) FROM "{table}" '
            f'WHERE "{column}" IS NOT NULL AND "{column}" !~ :pattern'
        ),
        {"pattern": UUID_PATTERN},
    ).scalar_one()
    if invalid:
        raise RuntimeError(
            f"Cannot convert {table}.{column} to UUID: {invalid} invalid value(s)"
        )


def upgrade() -> None:
    connection = op.get_bind()
    orphan_rows = connection.execute(sa.text("SELECT COUNT(*) FROM cell_groups")).scalar_one()
    if orphan_rows:
        raise RuntimeError(
            f"Cannot remove orphan cell_groups table: it contains {orphan_rows} row(s)"
        )

    columns = (
        ("estrategias_evangelismo", "id"),
        ("estrategia_roles_personalizados", "estrategia_id"),
        ("grupos_evangelismo", "estrategia_id"),
        ("personas", "origen_estrategia_id"),
        ("crm_casos", "origen_estrategia_id"),
    )
    for table, column in columns:
        _assert_uuid_values(connection, table, column)

    op.drop_table("cell_groups")
    op.drop_constraint(
        "estrategia_roles_personalizados_estrategia_id_fkey",
        "estrategia_roles_personalizados",
        type_="foreignkey",
    )
    op.drop_constraint(
        "grupos_evangelismo_estrategia_id_fkey",
        "grupos_evangelismo",
        type_="foreignkey",
    )
    op.drop_constraint(
        "crm_casos_origen_estrategia_id_fkey",
        "crm_casos",
        type_="foreignkey",
    )

    uuid_type = postgresql.UUID(as_uuid=True)
    for table, column in columns:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(),
            type_=uuid_type,
            postgresql_using=f'"{column}"::uuid',
            existing_nullable=column != "id",
        )

    op.create_foreign_key(
        "estrategia_roles_personalizados_estrategia_id_fkey",
        "estrategia_roles_personalizados",
        "estrategias_evangelismo",
        ["estrategia_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "grupos_evangelismo_estrategia_id_fkey",
        "grupos_evangelismo",
        "estrategias_evangelismo",
        ["estrategia_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_personas_origen_estrategia_id",
        "personas",
        "estrategias_evangelismo",
        ["origen_estrategia_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "crm_casos_origen_estrategia_id_fkey",
        "crm_casos",
        "estrategias_evangelismo",
        ["origen_estrategia_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "crm_casos_origen_estrategia_id_fkey", "crm_casos", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_personas_origen_estrategia_id", "personas", type_="foreignkey"
    )
    op.drop_constraint(
        "grupos_evangelismo_estrategia_id_fkey",
        "grupos_evangelismo",
        type_="foreignkey",
    )
    op.drop_constraint(
        "estrategia_roles_personalizados_estrategia_id_fkey",
        "estrategia_roles_personalizados",
        type_="foreignkey",
    )

    lengths = {
        ("estrategias_evangelismo", "id"): 36,
        ("estrategia_roles_personalizados", "estrategia_id"): 36,
        ("grupos_evangelismo", "estrategia_id"): 36,
        ("personas", "origen_estrategia_id"): 50,
        ("crm_casos", "origen_estrategia_id"): 36,
    }
    for (table, column), length in lengths.items():
        op.alter_column(
            table,
            column,
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.String(length=length),
            postgresql_using=f'"{column}"::text',
            existing_nullable=column != "id",
        )

    op.create_foreign_key(
        "estrategia_roles_personalizados_estrategia_id_fkey",
        "estrategia_roles_personalizados",
        "estrategias_evangelismo",
        ["estrategia_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "grupos_evangelismo_estrategia_id_fkey",
        "grupos_evangelismo",
        "estrategias_evangelismo",
        ["estrategia_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "crm_casos_origen_estrategia_id_fkey",
        "crm_casos",
        "estrategias_evangelismo",
        ["origen_estrategia_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "cell_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("zone", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
        sa.Column("leader_name", sa.String(length=100), nullable=True),
        sa.Column("members_count", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.String(length=20), nullable=True),
        sa.Column("start_time", sa.String(length=50), nullable=True),
        sa.Column("end_time", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("sede_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evangelism_strategy_id", sa.String(length=36), nullable=True),
        sa.Column("leader_persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assistant_persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("host_persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("schedule", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sede_id"], ["sedes.id"]),
        sa.ForeignKeyConstraint(
            ["evangelism_strategy_id"],
            ["estrategias_evangelismo.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["leader_persona_id"], ["personas.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["assistant_persona_id"], ["personas.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["host_persona_id"], ["personas.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_cell_groups_code", "cell_groups", ["code"], unique=True)
    op.create_index(
        "ix_cell_groups_evangelism_strategy_id",
        "cell_groups",
        ["evangelism_strategy_id"],
    )
    op.create_index("ix_cell_groups_sede_id", "cell_groups", ["sede_id"])
    op.create_index("ix_cell_groups_status", "cell_groups", ["status"])

"""add deleted_at to auth_user_module_roles

Revision ID: add_deleted_at_mod
Revises: 20260604_habilitacion_sesiones
Create Date: 2026-06-04

Adds soft-delete column deleted_at to auth_user_module_roles
to replace hard DELETE operations with logical deletion.
"""

from alembic import op
import sqlalchemy as sa

revision = "add_deleted_at_mod"
down_revision = "20260604_habilitacion_sesiones"
branch_labels = None
depends_on = None


def _col_exists(table, column):
    """Check if a column already exists in the table (idempotency helper)."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        result = conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
        return result.fetchone() is not None
    # SQLite fallback: PRAGMA table_info
    pragma = conn.execute(sa.text(f"PRAGMA table_info('{table}')"))
    for row in pragma:
        if row[1] == column:
            return True
    return False


def upgrade():
    if not _col_exists("auth_user_module_roles", "deleted_at"):
        op.add_column(
            "auth_user_module_roles",
            sa.Column(
                "deleted_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Soft-delete timestamp; NULL means active record",
            ),
        )


def downgrade():
    if _col_exists("auth_user_module_roles", "deleted_at"):
        op.drop_column("auth_user_module_roles", "deleted_at")

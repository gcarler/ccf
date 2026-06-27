"""Grant imported platform users the Academy student capability.

Revision ID: 20260627_0003_academy_access
Revises: 20260627_0002_drop_academy
"""

from typing import Sequence

from alembic import op


revision: str = "20260627_0003_academy_access"
down_revision: str | None = "20260627_0002_drop_academy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE auth_roles
        SET permisos = COALESCE(permisos, '{}'::jsonb)
            || '{"academy:study": "allow"}'::jsonb
        WHERE upper(nombre) = 'LECTOR'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE auth_roles
        SET permisos = COALESCE(permisos, '{}'::jsonb) - 'academy:study'
        WHERE upper(nombre) = 'LECTOR'
        """
    )

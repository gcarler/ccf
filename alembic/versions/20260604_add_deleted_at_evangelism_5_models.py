"""Add deleted_at to 5 evangelism models without soft delete

Revision ID: 20260604_evangelism_deleted_at
Revises: 3543395b085b
Create Date: 2026-06-04 18:45:00.000000

Models updated:
- sedes
- logs_auditoria
- categorias_estrategia
- registros_seguimiento
- historial_embudo
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260604_evangelism_deleted_at"
down_revision: Union[str, None] = "3543395b085b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sedes", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("logs_auditoria", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("categorias_estrategia", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("registros_seguimiento", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("historial_embudo", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sedes", "deleted_at")
    op.drop_column("logs_auditoria", "deleted_at")
    op.drop_column("categorias_estrategia", "deleted_at")
    op.drop_column("registros_seguimiento", "deleted_at")
    op.drop_column("historial_embudo", "deleted_at")

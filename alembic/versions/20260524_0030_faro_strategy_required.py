"""Make evangelism_strategy_id NOT NULL on grupos_evangelismo

Faro groups must belong to a Relacional strategy. No standalone groups allowed.
"""
import sqlalchemy as sa

from alembic import op

revision = "20260524_0030"
down_revision = "20260524_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure no NULL values exist before adding constraint
    op.execute("""
        DELETE FROM grupos_evangelismo WHERE evangelism_strategy_id IS NULL
    """)
    # Make column NOT NULL with a default for new records
    op.alter_column(
        'grupos_evangelismo',
        'evangelism_strategy_id',
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'grupos_evangelismo',
        'evangelism_strategy_id',
        existing_type=sa.Integer(),
        nullable=True,
    )

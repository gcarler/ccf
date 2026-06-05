"""Add scanner_token_hash and scanner_token_expires_at to personas

Revision ID: 20260604_personas_scanner_token
Revises: 20260604_evangelism_deleted_at
Create Date: 2026-06-04 22:00:00.000000

Adds scanner token validation columns to the Persona model
for production-ready QR code authentication.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260604_personas_scanner_token"
down_revision: Union[str, None] = "20260604_evangelism_deleted_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "personas",
        sa.Column(
            "scanner_token_hash",
            sa.String(128),
            nullable=True,
            index=True,
            comment="SHA-256 hash del scanner token",
        ),
    )
    op.add_column(
        "personas",
        sa.Column(
            "scanner_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Fecha de expiración del scanner token",
        ),
    )


def downgrade() -> None:
    op.drop_column("personas", "scanner_token_expires_at")
    op.drop_column("personas", "scanner_token_hash")

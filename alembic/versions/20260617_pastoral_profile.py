"""Add pastoral profile fields to Persona table

Revision ID: 20260617_pastoral_profile
Revises: 20260616_0001
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260617_pastoral_profile"
down_revision: Union[str, None] = "20260616_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("personas", sa.Column("photo_url", sa.String(500), nullable=True))
    op.add_column("personas", sa.Column("bio_short", sa.Text(), nullable=True))
    op.add_column("personas", sa.Column("bio_full", sa.Text(), nullable=True))
    op.add_column("personas", sa.Column("social_instagram", sa.String(200), nullable=True))
    op.add_column("personas", sa.Column("social_facebook", sa.String(200), nullable=True))
    op.add_column("personas", sa.Column("social_twitter", sa.String(200), nullable=True))
    op.add_column("personas", sa.Column("is_pastoral_leader", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("personas", sa.Column("is_main_pastor", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_index("ix_personas_is_pastoral_leader", "personas", ["is_pastoral_leader"])


def downgrade() -> None:
    op.drop_index("ix_personas_is_pastoral_leader", table_name="personas")
    op.drop_column("personas", "is_main_pastor")
    op.drop_column("personas", "is_pastoral_leader")
    op.drop_column("personas", "social_twitter")
    op.drop_column("personas", "social_facebook")
    op.drop_column("personas", "social_instagram")
    op.drop_column("personas", "bio_full")
    op.drop_column("personas", "bio_short")
    op.drop_column("personas", "photo_url")

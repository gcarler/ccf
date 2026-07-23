"""add_deleted_at_to_admin_entities

Revision ID: 20260723_0001
Revises: 20260719_0001_crm_events_deleted_at
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260723_0001"
down_revision: Union[str, None] = "20260721_0001_prayer_requests_deleted_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deleted_at to auth_roles
    op.add_column(
        "auth_roles",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_auth_roles_deleted_at",
        "auth_roles",
        ["deleted_at"],
        unique=False,
    )

    # Add deleted_at to church_locations
    op.add_column(
        "church_locations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_church_locations_deleted_at",
        "church_locations",
        ["deleted_at"],
        unique=False,
    )

    # Add deleted_at to social_channels
    op.add_column(
        "social_channels",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_social_channels_deleted_at",
        "social_channels",
        ["deleted_at"],
        unique=False,
    )

    # Add deleted_at to system_variables
    op.add_column(
        "system_variables",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_system_variables_deleted_at",
        "system_variables",
        ["deleted_at"],
        unique=False,
    )

    # Add deleted_at to donation_categories
    op.add_column(
        "donation_categories",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_donation_categories_deleted_at",
        "donation_categories",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_donation_categories_deleted_at", table_name="donation_categories")
    op.drop_column("donation_categories", "deleted_at")

    op.drop_index("ix_system_variables_deleted_at", table_name="system_variables")
    op.drop_column("system_variables", "deleted_at")

    op.drop_index("ix_social_channels_deleted_at", table_name="social_channels")
    op.drop_column("social_channels", "deleted_at")

    op.drop_index("ix_church_locations_deleted_at", table_name="church_locations")
    op.drop_column("church_locations", "deleted_at")

    op.drop_index("ix_auth_roles_deleted_at", table_name="auth_roles")
    op.drop_column("auth_roles", "deleted_at")

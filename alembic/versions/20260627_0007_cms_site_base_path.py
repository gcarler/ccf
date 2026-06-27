"""Add ``server_default='/'`` to ``cms_sites.base_path``

Companion to the ORM-level ``default='/'`` on
``backend.models_cms.CmsSite.base_path``. Without ``server_default``, raw SQL
inserts or any data-migration path that bypasses SQLAlchemy ``__init__``
would fail on the NOT NULL constraint. The ORM default only fires for the
SQLAlchemy instantiation path; this companion makes the default visible to
the database engine itself.

Revision ID: 20260627_0007_cms_site_base_path
Revises: 20260627_0006_crm_contract
Create Date: 2026-06-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260627_0007_cms_site_base_path"
down_revision: Union[str, None] = "20260627_0006_crm_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply ``server_default='/'`` to ``cms_sites.base_path``.

    The column stays NOT NULL (``existing_nullable=False``); only the default
    is added so the engine fills the value when an INSERT statement omits it.
    """
    op.alter_column(
        "cms_sites",
        "base_path",
        existing_type=sa.String(length=120),
        server_default="/",
        existing_nullable=False,
    )


def downgrade() -> None:
    """Remove the server default on ``cms_sites.base_path``."""
    op.alter_column(
        "cms_sites",
        "base_path",
        existing_type=sa.String(length=120),
        server_default=None,
        existing_nullable=False,
    )

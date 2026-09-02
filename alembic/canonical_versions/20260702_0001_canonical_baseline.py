"""Canonical baseline for the current CCF schema.

Revision ID: 20260702_0001_canonical_baseline
Revises: None
Create Date: 2026-07-02 00:00:00

This is the new active baseline after archiving the historical migration
chain as legacy. It materializes the current ORM metadata in one shot so
fresh databases can be brought to head without replaying the old chain.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

revision: str = "20260702_0001_canonical_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import backend.models  # noqa: F401
    from backend.core.database import Base

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # The canonical metadata contains CITEXT columns. Extensions belong
        # to the migration contract so CI, fresh installs and quality
        # provisioners all share the same prerequisite behavior.
        bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS citext")
        bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import backend.models  # noqa: F401
    from backend.core.database import Base

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # The ORM graph contains intentional cycles (for example the
        # evangelism strategy/group/persona relationships), and several
        # historical FKs are unnamed. SQLAlchemy cannot topologically sort
        # that graph for DROP. The canonical baseline owns the public schema
        # on a fresh install, so drop its tables with PostgreSQL CASCADE while
        # preserving Alembic's own revision table for the version update.
        bind.exec_driver_sql(
            """
            DO $$
            DECLARE table_record RECORD;
            BEGIN
                FOR table_record IN
                    SELECT tablename
                    FROM pg_catalog.pg_tables
                    WHERE schemaname = 'public'
                      AND tablename <> 'alembic_version'
                LOOP
                    EXECUTE format('DROP TABLE IF EXISTS public.%%I CASCADE', table_record.tablename);
                END LOOP;
            END $$;
            """
        )
    else:
        Base.metadata.drop_all(bind=bind)

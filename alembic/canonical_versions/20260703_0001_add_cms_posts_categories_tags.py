"""add_cms_posts_categories_tags — no-op in canonical chain

Revision ID: 20260703_0001_add_cms_posts_categories_tags
Revises: 20260702_0002_reported_at_tz
Create Date: 2026-07-03 00:00:00.000000

This revision is intentionally a NO-OP in the canonical chain because the
immediately prior revision ``20260702_0001_canonical_baseline`` already
creates every CMS table — including ``cms_categories``, ``cms_posts``,
``cms_tags``, ``cms_post_categories`` and ``cms_post_tags`` — via
``Base.metadata.create_all()`` against the current ORM metadata.

Forcing ``op.create_table`` calls here would fail with
``(sqlite3.OperationalError) table cms_categories already exists`` on any
fresh database bootstrapped via this canonical chain (production-grade
``alembic upgrade head`` scenario). The structure of the upgrade/downgrade
is preserved (revision + down_revision chain intact) so that the
historical migration graph between ``20260702_0002_reported_at_tz`` and
subsequent canonical revisions remains valid.

The duplicate (identically-structured) migration that lives in
``alembic/versions/`` is the CLOSED legacy chain record — per
``REGLAS.md §9.1`` it is not modified. ``alembic.ini`` points
``version_locations`` only at ``alembic/canonical_versions``, so the
duplicate is not discovered at upgrade time and this no-op is the single
source of truth forward.

If/when the legacy chain in ``alembic/versions/`` is fully retired and
this canonical chain becomes the only chain, this no-op can be retired
in a future revision that simply chains forward with the same identifiers
but does nothing.
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '20260703_0001_add_cms_posts_categories_tags'
down_revision: Union[str, None] = '20260702_0002_reported_at_tz'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intentionally a no-op. See module docstring.
    # Prior revision 20260702_0001_canonical_baseline has already created
    # all CMS tables via Base.metadata.create_all() on the canonical chain,
    # so re-issuing ``op.create_table`` for cms_* here would crash with a
    # ``table X already exists`` runtime error on every fresh database.
    pass


def downgrade() -> None:
    # Intentionally a no-op (matches upgrade()).
    # The cms_* table lifecycle is owned by ``20260702_0001_canonical_baseline``
    # (which uses ``Base.metadata.create_all`` upward and ``drop_all`` downward).
    # This revision neither creates nor drops those tables, so a downgrade past
    # this point in the canonical chain leaves them in place; whatever owns the
    # lifecycle (the baseline) re-creates them on the matching upgrade. Do not
    # move create/drop statements for cms_* into this file — they belong to the
    # baseline.
    pass

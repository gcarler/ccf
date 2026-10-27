"""Reversibility and data preservation for the deployed CoQ revision."""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_coq_column_upgrade_downgrade_preserves_acceptance_rows():
    path = Path(__file__).resolve().parents[1] / "alembic/canonical_versions/20261024_0001_add_coq_amount_to_project_dod_acceptances.py"
    spec = importlib.util.spec_from_file_location("project_coq_revision", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE project_dod_acceptances (id VARCHAR(36) PRIMARY KEY, notes TEXT)"))
        connection.execute(sa.text("INSERT INTO project_dod_acceptances VALUES ('acceptance-1', 'accepted evidence')"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        columns = {c["name"]: c for c in sa.inspect(connection).get_columns("project_dod_acceptances")}
        assert columns["coq_amount"]["nullable"]
        assert connection.execute(sa.text("SELECT coq_amount FROM project_dod_acceptances")).scalar_one() is None
        connection.execute(sa.text("UPDATE project_dod_acceptances SET coq_amount = 12.5"))
        migration.downgrade()
        assert "coq_amount" not in {c["name"] for c in sa.inspect(connection).get_columns("project_dod_acceptances")}
        assert connection.execute(sa.text("SELECT id, notes FROM project_dod_acceptances")).one() == ("acceptance-1", "accepted evidence")
        migration.upgrade()
        assert connection.execute(sa.text("SELECT COUNT(*) FROM project_dod_acceptances")).scalar_one() == 1

"""The baseline must support PostgreSQL teardown without changing its history."""

from sqlalchemy import create_mock_engine

import backend.models  # noqa: F401
from backend.core.database import Base


def test_postgresql_baseline_can_plan_a_complete_downgrade():
    statements = []

    def execute(sql, *multiparams, **params):
        statements.append(str(sql.compile(dialect=engine.dialect)))

    engine = create_mock_engine("postgresql+psycopg2://", execute)
    Base.metadata.drop_all(engine, checkfirst=False)
    assert sum(sql.lstrip().startswith("DROP TABLE") for sql in statements) == len(Base.metadata.tables)
    # Each PostgreSQL default constraint name belongs to its actual table.
    for table in Base.metadata.tables.values():
        for constraint in table.foreign_key_constraints:
            if constraint.use_alter and constraint.name.endswith("_fkey"):
                assert constraint.name.startswith(f"{table.name}_")

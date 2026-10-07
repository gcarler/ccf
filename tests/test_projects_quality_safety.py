from __future__ import annotations

import pytest

from scripts.projects_quality_safety import (
    ProjectsQualityTargetError,
    validate_projects_quality_target,
)


def _validate(database: str = "ccf_projects_quality_20261004", **overrides: str) -> str:
    values = {
        "database_url": f"postgresql://user:pass@localhost/{database}",
        "quality_database_url": f"postgresql://user:pass@localhost/{database}",
        "confirmed_database": database,
        "run_id": "projects-20261004-01",
    }
    values.update(overrides)
    return validate_projects_quality_target(**values)


def test_projects_quality_accepts_explicit_isolated_database():
    assert _validate() == "ccf_projects_quality_20261004"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"quality_database_url": ""}, "QUALITY_DATABASE_URL es obligatorio"),
        ({"confirmed_database": ""}, "debe confirmar explícitamente"),
        ({"confirmed_database": "ccf_shared"}, "debe coincidir exactamente"),
        ({"database_url": "sqlite:///projects.db", "confirmed_database": "projects.db"}, "requiere PostgreSQL"),
        ({"database_url": "postgresql://user:pass@localhost/development", "confirmed_database": "development"}, "_e2e, _test o _quality"),
        ({"quality_database_url": "postgresql://user:pass@localhost/other_quality"}, "misma base PostgreSQL"),
        ({"quality_database_url": "postgresql://user:pass@other-host/ccf_projects_quality_20261004"}, "mismo host y puerto"),
        ({"quality_database_url": "postgresql://user:pass@localhost:5433/ccf_projects_quality_20261004"}, "mismo host y puerto"),
        ({"run_id": "   "}, "QUALITY_RUN_ID es obligatorio"),
    ],
)
def test_projects_quality_rejects_unisolated_or_ambiguous_target(kwargs, message):
    with pytest.raises(ProjectsQualityTargetError, match=message):
        _validate(**kwargs)

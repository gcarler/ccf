from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["ENVIRONMENT"] = "test"
    env["DATABASE_URL"] = database_url
    return subprocess.run(
        ["alembic", *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_canonical_baseline_is_the_only_active_head(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'canonical_baseline.db'}"

    heads = _run_alembic("heads", database_url=db_url)
    assert heads.returncode == 0, heads.stderr
    assert "20260702_0001_canonical_baseline" in heads.stdout

    upgrade = _run_alembic("upgrade", "head", database_url=db_url)
    assert upgrade.returncode == 0, upgrade.stderr

    downgrade = _run_alembic("downgrade", "base", database_url=db_url)
    assert downgrade.returncode == 0, downgrade.stderr

    second_upgrade = _run_alembic("upgrade", "head", database_url=db_url)
    assert second_upgrade.returncode == 0, second_upgrade.stderr

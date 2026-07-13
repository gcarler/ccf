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
    assert "20260713_0001" in heads.stdout

    assert heads.stdout.count("(head)") == 1

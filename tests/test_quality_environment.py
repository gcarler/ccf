from __future__ import annotations

import pytest

from scripts.quality_environment import QualityEnvironment, QualityEnvironmentError


def _set_valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUALITY_DATABASE_URL", "postgresql://quality:secret@localhost/quality")
    monkeypatch.setenv("QUALITY_API_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("QUALITY_RUN_ID", "test-run")


def test_quality_environment_requires_explicit_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUALITY_DATABASE_URL", raising=False)
    monkeypatch.delenv("QUALITY_API_URL", raising=False)
    monkeypatch.delenv("QUALITY_RUN_ID", raising=False)

    with pytest.raises(QualityEnvironmentError, match="QUALITY_DATABASE_URL"):
        QualityEnvironment.from_process()


def test_quality_environment_rejects_sqlite_for_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUALITY_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("QUALITY_API_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("QUALITY_RUN_ID", "test-run")

    with pytest.raises(QualityEnvironmentError, match="PostgreSQL"):
        QualityEnvironment.from_process()


def test_quality_environment_propagates_one_database_and_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_valid_environment(monkeypatch)

    environment = QualityEnvironment.from_process()
    child_env = environment.child_environment()

    assert child_env["DATABASE_URL"] == child_env["QUALITY_DATABASE_URL"]
    assert child_env["database_url"] == child_env["QUALITY_DATABASE_URL"]
    assert child_env["QUALITY_API_URL"] == "http://127.0.0.1:8000"
    assert child_env["QUALITY_RUN_ID"] == "test-run"

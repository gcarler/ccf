"""Alembic environment — cwd-independent thanks to backend.core.bootstrap.

The walk-up that puts `backend/` on `sys.path` is the one operation this
file MUST do inline because Python evaluates imports during module load
and we cannot `from backend.core.bootstrap import …` until `sys.path` is
rooted. After that one-line setup, `load_settings()` re-applies the same
walk-up idempotently (defense-in-depth).
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

# One-line walk-up so the imports below can find `backend.*`.
sys.path.insert(
    0,
    str(next(
        p for p in Path(__file__).resolve().parents
        if (p / "backend" / "__init__.py").is_file()
    )),
)

from sqlalchemy import engine_from_config, pool  # noqa: E402

import backend.models as models  # noqa: E402,F401
from alembic import context  # noqa: E402
from backend.core.bootstrap import load_settings  # noqa: E402
from backend.core.database import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# load_settings self-bootstraps via ensure_project_root(start=__file__).
# Raises an actionable RuntimeError if .env is missing or the security
# validator rejects the env values.
settings = load_settings(start=__file__)
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

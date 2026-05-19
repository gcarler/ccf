# Migration Normalization

## Current State

- Alembic history is incomplete relative to `backend/models.py`.
- Some operational scripts still relied on `Base.metadata.create_all(...)`.
- Runtime schema mutation in the API has been disabled by default and is now opt-in through `RUN_STARTUP_SCHEMA_FIXES`.

## New Rules

- Production and CI must use Alembic as the primary schema path.
- Compatibility bootstrapping with `create_all(...)` is allowed only when explicitly enabled with `CCF_ALLOW_CREATE_ALL_BOOTSTRAP=true`.
- Local destructive resets are restricted to `ENVIRONMENT=local|test`.

## Scripts

- `python -m backend.init_db`
  - Runs `alembic upgrade head`
  - Optionally bootstraps unmanaged tables if `CCF_ALLOW_CREATE_ALL_BOOTSTRAP=true`
  - Prints a drift report

- `python scripts/schema_drift_report.py`
  - Prints current Alembic revision
  - Lists tables missing in DB and extra tables present in DB

- `python scripts/reset_db.py`
  - Local/test only
  - Drops and recreates schema from metadata for preview/bootstrap workflows

## Next Work

1. Snapshot a production-like database and run `scripts/schema_drift_report.py`.
2. Group unmanaged tables into migration batches by domain.
3. Create baseline Alembic revisions for unmanaged domains before removing bootstrap mode from scripts.
4. Remove remaining `create_all(...)` usages from seed/verification utilities once each domain is migration-backed.

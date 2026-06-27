"""Project-bootstrap helpers shared by alembic/env.py and any future
entrypoint (`celery`, `scheduler`, scripts/... entrypoints that can
pre-import `backend.*`).

Public surface:
- `ensure_project_root(start=None)` — walk up to find project root and
  preprint it to `sys.path` so `import backend.*` works.
- `load_settings(start=None)` — instantiate `Settings(_env_file=…)` rooted
  at the project root, with `.env` existence check and security-validator
  wrap. Self-bootstraps before importing `backend.core.config.Settings`.

The walk-up logic that powers both helpers lives in the private
`_resolve_project_root(start)` function below. `alembic/env.py` and the
34 entrypoint scripts under `scripts/` mirror the same algorithm inline
because they cannot import this module until `sys.path` is rooted. If
you change `_resolve_project_root`, mirror the change in those inline
blocks (or migrate them to a sibling `scripts/_scripts_walkup.py` shim
that exec's this file).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.config import Settings


def _resolve_project_root(start: Path | str | None = None) -> Path:
    """Single source of truth for the walk-up algorithm.

    Walks up `start` (defaults to this module's file path) until a parent
    contains `backend/__init__.py`. That parent is the project root.
    Raises RuntimeError if `backend/` cannot be located.

    The same algorithm is mirrored inline in `alembic/env.py` and the
    entrypoint scripts under `scripts/`. Keep them in sync.
    """
    here = Path(start).resolve() if start else Path(__file__).resolve()
    root = next(
        (p for p in here.parents if (p / "backend" / "__init__.py").is_file()),
        None,
    )
    if root is None:
        raise RuntimeError(f"backend package not found above {here}")
    return root


def ensure_project_root(start: Path | str | None = None) -> Path:
    """Walk up to the project root and prepend it to `sys.path` so that
    `import backend.*` works. Idempotent — no-op when already set.

    Returns the resolved project root.
    """
    root = _resolve_project_root(start)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def load_settings(start: Path | str | None = None) -> "Settings":
    """Instantiate `Settings` rooted at the project root.

    Auto-bootstraps: calls `ensure_project_root(start)` first so callers
    that have not yet rooted `sys.path` still get a working bootstrap.
    This is a defense-in-depth layer on top of the inline walk-up in
    `alembic/env.py` and the entrypoint scripts.

    Bypasses `get_settings()`'s `lru_cache` to avoid cwd-relative `.env`
    capture across runs.

    Raises an actionable RuntimeError in two scenarios:
    * `.env` is missing at the project root.
    * `Settings.validate_security_defaults` rejects the env values
      (weak secrets in production-like env). The original `ValueError`
      is preserved as `__cause__`.
    """
    # Self-bootstrap: idempotent, no-op if sys.path already has backend/.
    root = ensure_project_root(start)

    # Lazy import keeps the dependency surface small for callers that only
    # need `ensure_project_root`.
    from backend.core.config import Settings

    env_path = root / ".env"
    if not env_path.is_file():
        raise RuntimeError(
            f".env not found at {env_path}. Create it, or export the required "
            f"settings (DATABASE_URL, SECRET_KEY, etc.) before running this "
            f"entrypoint."
        )
    try:
        return Settings(_env_file=str(env_path))
    except ValueError as exc:
        # Settings.validate_security_defaults raises ValueError for weak
        # production secrets — surface it with the .env path so the user
        # knows which file to fix.
        raise RuntimeError(
            f"Settings rejected env values from {env_path}. "
            f"Check SECRET_KEY / ENCRYPTION_KEY / SMTP / DATABASE_URL per "
            f"validate_security_defaults: {exc}"
        ) from exc

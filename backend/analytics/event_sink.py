from __future__ import annotations

import datetime as dt
import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

# pyright: reportMissingImports=false


try:  # pragma: no cover - import guard for optional dep
    import duckdb  # type: ignore[import]
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    pass

from backend.core.config import get_settings

settings = get_settings()
WAREHOUSE_PATH = Path(settings.analytics_db_path)
WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
_RESOLVED_WAREHOUSE_PATH: Path | None = None

CREATE_EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS domain_events (
    event_time TIMESTAMP,
    event_name TEXT,
    payload JSON
)
"""


def _connect():
    if duckdb is None:  # pragma: no cover
        raise RuntimeError("duckdb dependency is required for analytics")
    global _RESOLVED_WAREHOUSE_PATH
    target = _RESOLVED_WAREHOUSE_PATH or WAREHOUSE_PATH
    try:
        conn = duckdb.connect(str(target))
    except Exception:
        fallback_dir = Path(tempfile.gettempdir()) / "ccf_analytics"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        target = fallback_dir / WAREHOUSE_PATH.name
        _RESOLVED_WAREHOUSE_PATH = target
        conn = duckdb.connect(str(target))
    else:
        _RESOLVED_WAREHOUSE_PATH = target
    conn.execute(CREATE_EVENTS_SQL)
    return conn


def persist_event(name: str, payload: Dict[str, Any]) -> None:
    """Append event data to DuckDB warehouse."""

    timestamp = dt.datetime.now(dt.timezone.utc)
    serialized = json.dumps(payload or {})
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO domain_events (event_time, event_name, payload) VALUES (?, ?, ?)",
            [timestamp, name, serialized],
        )
    finally:
        conn.close()

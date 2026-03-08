from __future__ import annotations

# pyright: reportMissingImports=false

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

try:  # pragma: no cover - import guard for optional dep
    import duckdb  # type: ignore[import]
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from duckdb import DuckDBPyConnection

from backend.core.config import get_settings


settings = get_settings()
WAREHOUSE_PATH = Path(settings.analytics_db_path)
WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)

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
    conn = duckdb.connect(str(WAREHOUSE_PATH))
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

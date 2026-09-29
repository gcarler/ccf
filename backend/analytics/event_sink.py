from __future__ import annotations

import datetime as dt
import json
import logging
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


try:  # pragma: no cover - import guard for optional dep
    import duckdb  # type: ignore[import]
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore

from backend.core.config import get_settings

settings = get_settings()
WAREHOUSE_PATH = Path(settings.analytics_db_path)
try:
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
except OSError:  # pragma: no cover - read-only FS edge case
    logger.warning("analytics warehouse dir not creatable: %s", WAREHOUSE_PATH.parent)
_RESOLVED_WAREHOUSE_PATH: Optional[Path] = None

CREATE_EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS domain_events (
    event_time TIMESTAMP,
    event_name TEXT,
    payload JSON
)
"""

# ── Safe in-memory fallback (Axioma: analytics nunca tumba peticiones) ──
# Cuando duckdb no está instalado o la DB falla, los eventos viven aquí
# para que persist_event()/queries() sigan operando sin excepciones.
_MEMORY_EVENTS: List[Tuple[dt.datetime, str, str]] = []
_MEMORY_LOCK = Lock()
_MEMORY_MAX_EVENTS = 10_000


def is_available() -> bool:
    """True si el warehouse persistente (duckdb) está operativo."""
    return duckdb is not None


def _connect():
    """Conexión duckdb o ``None`` cuando la dependencia no está presente.

    Nunca lanza por dependencia ausente: los callers tratan ``None``
    como señal de usar el fallback en memoria.
    """
    if duckdb is None:
        return None
    global _RESOLVED_WAREHOUSE_PATH
    target = _RESOLVED_WAREHOUSE_PATH or WAREHOUSE_PATH
    try:
        conn = duckdb.connect(str(target))
    except Exception as exc:
        # Fallback to a throwaway DB so analytics keep working, but log it:
        # silently degrading to empty data hides real storage problems (C3).
        logger.warning("duckdb connect failed for %s, using temp fallback: %s", target, exc)
        fallback_dir = Path(tempfile.gettempdir()) / "ccf_analytics"
        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)
            target = fallback_dir / WAREHOUSE_PATH.name
            conn = duckdb.connect(str(target))
            _RESOLVED_WAREHOUSE_PATH = target
        except Exception as exc2:  # ni el fallback temporal es viable
            logger.warning("duckdb temp fallback failed, using in-memory sink: %s", exc2)
            return None
    else:
        _RESOLVED_WAREHOUSE_PATH = target
    try:
        conn.execute(CREATE_EVENTS_SQL)
    except Exception as exc:
        logger.warning("duckdb schema init failed, using in-memory sink: %s", exc)
        try:
            conn.close()
        except Exception:  # pragma: no cover
            pass
        return None
    return conn


def _memory_append(timestamp: dt.datetime, name: str, serialized: str) -> None:
    with _MEMORY_LOCK:
        _MEMORY_EVENTS.append((timestamp, name, serialized))
        # Cap duro para que el fallback en memoria no crezca sin límite.
        if len(_MEMORY_EVENTS) > _MEMORY_MAX_EVENTS:
            del _MEMORY_EVENTS[: len(_MEMORY_EVENTS) - _MEMORY_MAX_EVENTS]


def persist_event(name: str, payload: Dict[str, Any]) -> None:
    """Append event data to the DuckDB warehouse.

    Resiliencia total (nunca lanza): si duckdb no está instalado, la DB
    falla o el INSERT falla, se registra warning y el evento se retiene
    en el fallback en memoria para que la petición del caller nunca se
    tumbe por telemetría.
    """
    timestamp = dt.datetime.now(dt.timezone.utc)
    serialized = json.dumps(payload or {})
    try:
        conn = _connect()
        if conn is None:
            _memory_append(timestamp, name, serialized)
            return
        try:
            conn.execute(
                "INSERT INTO domain_events (event_time, event_name, payload) VALUES (?, ?, ?)",
                [timestamp, name, serialized],
            )
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 — telemetría jamás rompe el flujo
        logger.warning("persist_event degraded to in-memory sink for %r: %s", name, exc)
        _memory_append(timestamp, name, serialized)


def fetch_recent_events() -> List[Tuple[dt.datetime, str, str]]:
    """Eventos del fallback en memoria (más recientes primero)."""
    with _MEMORY_LOCK:
        return list(reversed(_MEMORY_EVENTS))

from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, List

from backend.analytics import event_sink


def _connect():
    """Conexión duckdb o ``None`` si la dependencia/DB no está disponible.

    Nunca lanza: el caller degrada a los payloads vacíos/en memoria.
    La disponibilidad se consulta en ``event_sink`` (fuente única de
    verdad) para que parches de runtime (tests, entornos degradados)
    se reflejen en ambos módulos a la vez.
    """
    if event_sink.duckdb is None:
        return None
    try:
        return event_sink._connect()
    except Exception as exc:  # noqa: BLE001 — lecturas nunca rompen peticiones
        import logging

        logging.getLogger(__name__).warning("analytics queries connect failed: %s", exc)
        return None


def _memory_summary(days: int) -> Dict[str, Any]:
    """Resumen desde el fallback en memoria de ``event_sink``."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    counts: Dict[str, int] = {}
    total = 0
    for ts, name, _payload in event_sink.fetch_recent_events():
        if ts >= cutoff:
            counts[name] = counts.get(name, 0) + 1
            total += 1
    by_event = [
        {"event_name": name, "count": count}
        for name, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return {"total_events": total, "by_event": by_event}


def get_event_summary(days: int = 7) -> Dict[str, Any]:
    """Resumen de eventos del warehouse (o del fallback en memoria)."""
    conn = _connect()
    if conn is None:
        return _memory_summary(days)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    try:
        result = conn.execute(
            """
            WITH recent AS (
                SELECT * FROM domain_events
                WHERE event_time >= ?
            )
            SELECT event_name, COUNT(*) as count
            FROM recent
            GROUP BY event_name
            ORDER BY count DESC
            """,
            [cutoff],
        ).fetchall()
        total = sum(row[1] for row in result)
        return {
            "total_events": total,
            "by_event": [{"event_name": row[0], "count": row[1]} for row in result],
        }
    except Exception as exc:  # noqa: BLE001 — warehouse dañado ⇒ fallback memoria
        import logging

        logging.getLogger(__name__).warning("get_event_summary degraded to in-memory: %s", exc)
        return _memory_summary(days)
    finally:
        try:
            conn.close()
        except Exception:  # pragma: no cover
            pass


def _memory_course_performance(limit: int) -> List[Dict[str, Any]]:
    """Performance por curso desde el fallback en memoria.

    Replica la semántica de la query duckdb: agrupa por
    ``payload->>'course_id'`` casteable a entero y cuenta
    EnrollmentCreated / CertificateIssued / AssessmentSubmitted(passed).
    """
    stats: Dict[int, Dict[str, Any]] = {}
    for _ts, name, payload_raw in event_sink.fetch_recent_events():
        try:
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else (payload_raw or {})
        except (TypeError, ValueError):
            continue
        try:
            course_id = int(payload.get("course_id"))  # TRY_CAST semantics
        except (TypeError, ValueError):
            continue
        row = stats.setdefault(
            course_id, {"course_id": course_id, "enrollments": 0, "certificates": 0, "approvals": 0}
        )
        if name == "EnrollmentCreated":
            row["enrollments"] += 1
        elif name == "CertificateIssued":
            row["certificates"] += 1
        elif name == "AssessmentSubmitted" and payload.get("passed"):
            row["approvals"] += 1
    rows = sorted(stats.values(), key=lambda r: (r["enrollments"], r["certificates"]), reverse=True)
    return rows[:max(limit, 0)]


def get_course_performance(limit: int = 10) -> List[Dict[str, Any]]:
    """Performance por curso; fallback en memoria sin warehouse."""
    conn = _connect()
    if conn is None:
        return _memory_course_performance(limit)
    try:
        rows = conn.execute(
            """
            SELECT
                TRY_CAST(payload->>'course_id' AS INTEGER) as course_id,
                SUM(CASE WHEN event_name = 'EnrollmentCreated' THEN 1 ELSE 0 END) AS enrollments,
                SUM(CASE WHEN event_name = 'CertificateIssued' THEN 1 ELSE 0 END) AS certificates,
                SUM(CASE WHEN event_name = 'AssessmentSubmitted' AND (payload->>'passed')::BOOL THEN 1 ELSE 0 END) AS approvals
            FROM domain_events
            WHERE payload->>'course_id' IS NOT NULL
              AND TRY_CAST(payload->>'course_id' AS INTEGER) IS NOT NULL
            GROUP BY course_id
            ORDER BY enrollments DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        return [
            {
                "course_id": row[0],
                "enrollments": row[1],
                "certificates": row[2],
                "approvals": row[3],
            }
            for row in rows
        ]
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("get_course_performance degraded to in-memory: %s", exc)
        return _memory_course_performance(limit)
    finally:
        try:
            conn.close()
        except Exception:  # pragma: no cover
            pass


def list_raw_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Eventos crudos recientes; fallback en memoria sin warehouse."""
    conn = _connect()
    if conn is None:
        return [
            {
                "event_time": ts.isoformat() if hasattr(ts, "isoformat") else ts,
                "event_name": name,
                "payload": json.loads(payload) if isinstance(payload, str) else payload,
            }
            for ts, name, payload in event_sink.fetch_recent_events()[:limit]
        ]
    try:
        rows = conn.execute(
            """
            SELECT event_time, event_name, payload
            FROM domain_events
            ORDER BY event_time DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        return [
            {
                "event_time": (row[0].isoformat() if hasattr(row[0], "isoformat") else row[0]),
                "event_name": row[1],
                "payload": json.loads(row[2]) if isinstance(row[2], str) else row[2],
            }
            for row in rows
        ]
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("list_raw_events degraded to in-memory: %s", exc)
        return [
            {
                "event_time": ts.isoformat() if hasattr(ts, "isoformat") else ts,
                "event_name": name,
                "payload": json.loads(payload) if isinstance(payload, str) else payload,
            }
            for ts, name, payload in event_sink.fetch_recent_events()[:limit]
        ]
    finally:
        try:
            conn.close()
        except Exception:  # pragma: no cover
            pass

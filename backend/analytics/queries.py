from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, List

try:
    import duckdb  # type: ignore[import]
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore

from backend.analytics import event_sink

WAREHOUSE_PATH = event_sink.WAREHOUSE_PATH


def _connect():
    if duckdb is None:  # pragma: no cover
        raise RuntimeError("duckdb dependency is required for analytics")
    return event_sink._connect()


def get_event_summary(days: int = 7) -> Dict[str, Any]:
    conn = _connect()
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
    finally:
        conn.close()


def get_course_performance(limit: int = 10) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT
                CAST(payload->>'course_id' AS INTEGER) as course_id,
                SUM(CASE WHEN event_name = 'EnrollmentCreated' THEN 1 ELSE 0 END) AS enrollments,
                SUM(CASE WHEN event_name = 'CertificateIssued' THEN 1 ELSE 0 END) AS certificates,
                SUM(CASE WHEN event_name = 'AssessmentSubmitted' AND (payload->>'passed')::BOOL THEN 1 ELSE 0 END) AS approvals
            FROM domain_events
            WHERE payload->>'course_id' IS NOT NULL
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
    finally:
        conn.close()


def list_raw_events(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _connect()
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
                "event_time": (
                    row[0].isoformat() if hasattr(row[0], "isoformat") else row[0]
                ),
                "event_name": row[1],
                "payload": json.loads(row[2]) if isinstance(row[2], str) else row[2],
            }
            for row in rows
        ]
    finally:
        conn.close()

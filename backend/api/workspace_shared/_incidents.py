from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException

from backend.api.workspace_shared import SEVERITY_ORDER
from backend.api.workspace_shared._audit import _parse_timestamp
from backend.api.workspace_shared._storage import _append_incident_history, _append_notification, _now_iso


def _incident_fingerprint(kind: str, key: str) -> str:
    return hashlib.md5(f"{kind}:{key}".encode("utf-8")).hexdigest()


def _is_silenced_active(incident: Dict[str, Any]) -> bool:
    silenced_until = incident.get("silenced_until")
    if not silenced_until:
        return False
    parsed = _parse_timestamp(silenced_until)
    if not parsed:
        return False
    return parsed.timestamp() > datetime.now(tz=timezone.utc).timestamp()


def _seconds_between(start: Any, end: Any) -> float | None:
    start_dt = _parse_timestamp(start)
    end_dt = _parse_timestamp(end)
    if not start_dt or not end_dt:
        return None
    delta = end_dt.timestamp() - start_dt.timestamp()
    if delta < 0:
        return None
    return delta


def _compute_incident_severity(incident: Dict[str, Any]) -> str:
    status_value = str(incident.get("status") or "open")
    if status_value == "closed":
        return "low"

    count = max(0, int(incident.get("count") or 0))
    threshold = max(1, int(incident.get("threshold") or 1))
    ratio = count / threshold
    age_seconds = _seconds_between(incident.get("created_at"), _now_iso()) or 0.0
    age_minutes = age_seconds / 60.0

    if ratio >= 3.0 or age_minutes >= 24 * 60:
        return "critical"
    if ratio >= 2.0 or age_minutes >= 6 * 60:
        return "high"
    if ratio >= 1.2 or age_minutes >= 2 * 60:
        return "medium"
    return "low"


def _set_incident_severity(
    incident: Dict[str, Any],
    *,
    actor_id: str,
    reason: str,
) -> bool:
    previous = str(incident.get("severity") or "low")
    current = _compute_incident_severity(incident)
    incident["severity"] = current

    if previous == current:
        return False

    _append_incident_history(
        incident,
        event="severity_changed",
        actor_id=actor_id,
        metadata={"from": previous, "to": current, "reason": reason},
    )

    if SEVERITY_ORDER.get(current, 0) > SEVERITY_ORDER.get(previous, 0):
        _append_notification(
            {
                "type": "incident_severity_escalated",
                "incident_id": incident.get("id"),
                "incident_key": incident.get("key"),
                "severity": current,
                "previous_severity": previous,
                "reason": reason,
            }
        )

    return True


def _summarize_incidents(
    incidents: list[Dict[str, Any]],
    *,
    mtta_target_minutes: int = 60,
    mttr_target_minutes: int = 240,
) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {}
    ack_durations: list[float] = []
    close_durations: list[float] = []
    open_ages: list[float] = []
    now_iso = _now_iso()

    for item in incidents:
        status_value = str(item.get("status") or "open")
        counts[status_value] = counts.get(status_value, 0) + 1
        severity_value = str(item.get("severity") or "low")
        severity_counts[severity_value] = severity_counts.get(severity_value, 0) + 1

        ack_seconds = _seconds_between(item.get("created_at"), item.get("ack_at"))
        if ack_seconds is not None:
            ack_durations.append(ack_seconds)

        close_seconds = _seconds_between(item.get("created_at"), item.get("closed_at"))
        if close_seconds is not None:
            close_durations.append(close_seconds)

        if status_value in {"open", "acknowledged", "silenced"}:
            age_seconds = _seconds_between(item.get("created_at"), now_iso)
            if age_seconds is not None:
                open_ages.append(age_seconds)

    def _avg_minutes(values: list[float]) -> float | None:
        if not values:
            return None
        return round((sum(values) / len(values)) / 60.0, 2)

    def _p95_minutes(values: list[float]) -> float | None:
        if not values:
            return None
        sorted_values = sorted(values)
        idx = int((len(sorted_values) - 1) * 0.95)
        return round(sorted_values[idx] / 60.0, 2)

    mtta_minutes = _avg_minutes(ack_durations)
    mttr_minutes = _avg_minutes(close_durations)
    open_age_p95 = _p95_minutes(open_ages)
    safe_mtta_target = max(1, min(mtta_target_minutes, 60 * 24 * 30))
    safe_mttr_target = max(1, min(mttr_target_minutes, 60 * 24 * 30))

    return {
        "counts": counts,
        "severity_counts": severity_counts,
        "total": len(incidents),
        "mtta_minutes": mtta_minutes,
        "mttr_minutes": mttr_minutes,
        "open_age_p95_minutes": open_age_p95,
        "targets": {
            "mtta_minutes": safe_mtta_target,
            "mttr_minutes": safe_mttr_target,
        },
        "breaches": {
            "mtta": bool(mtta_minutes is not None and mtta_minutes > safe_mtta_target),
            "mttr": bool(mttr_minutes is not None and mttr_minutes > safe_mttr_target),
        },
    }


def _cleanup_incidents(
    incidents: list[Dict[str, Any]],
    *,
    retain_closed_days: int,
    retain_resolved_days: int,
) -> Dict[str, int]:
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    closed_boundary = now_ts - (max(1, min(retain_closed_days, 3650)) * 86400)
    resolved_boundary = now_ts - (max(1, min(retain_resolved_days, 3650)) * 86400)

    removed_closed = 0
    removed_resolved = 0
    reopened_silenced = 0
    kept: list[Dict[str, Any]] = []

    for incident in incidents:
        status_value = str(incident.get("status") or "open")

        if status_value == "silenced" and not _is_silenced_active(incident):
            incident["status"] = "open"
            incident["silenced_until"] = None
            incident["updated_at"] = _now_iso()
            _append_incident_history(
                incident,
                event="silence_expired",
                actor_id="system",
                metadata={"reason": "cleanup"},
            )
            reopened_silenced += 1
            status_value = "open"

        if status_value == "closed":
            closed_at = _parse_timestamp(incident.get("closed_at"))
            if closed_at and closed_at.timestamp() < closed_boundary:
                removed_closed += 1
                continue

        if status_value in {"acknowledged", "silenced"}:
            updated_at = _parse_timestamp(incident.get("updated_at"))
            if updated_at and updated_at.timestamp() < resolved_boundary:
                removed_resolved += 1
                continue

        kept.append(incident)

    incidents[:] = kept
    return {
        "removed_closed": removed_closed,
        "removed_resolved": removed_resolved,
        "reopened_silenced": reopened_silenced,
    }


def _incident_daily_trends(
    incidents: list[Dict[str, Any]], days: int = 14
) -> list[Dict[str, Any]]:
    safe_days = max(1, min(days, 180))
    now = datetime.now(tz=timezone.utc)

    buckets: Dict[str, Dict[str, Any]] = {}
    for offset in range(safe_days):
        day = (now - timedelta(days=(safe_days - 1 - offset))).date().isoformat()
        buckets[day] = {
            "date": day,
            "created": 0,
            "closed": 0,
            "acknowledged": 0,
            "mtta_values": [],
            "mttr_values": [],
        }

    def _day_key(value: Any) -> str | None:
        parsed = _parse_timestamp(value)
        if not parsed:
            return None
        return parsed.date().isoformat()

    for incident in incidents:
        created_key = _day_key(incident.get("created_at"))
        if created_key in buckets:
            buckets[created_key]["created"] += 1

        closed_key = _day_key(incident.get("closed_at"))
        if closed_key in buckets:
            buckets[closed_key]["closed"] += 1
            mttr_seconds = _seconds_between(
                incident.get("created_at"), incident.get("closed_at")
            )
            if mttr_seconds is not None:
                buckets[closed_key]["mttr_values"].append(mttr_seconds / 60.0)

        ack_key = _day_key(incident.get("ack_at"))
        if ack_key in buckets:
            buckets[ack_key]["acknowledged"] += 1
            mtta_seconds = _seconds_between(
                incident.get("created_at"), incident.get("ack_at")
            )
            if mtta_seconds is not None:
                buckets[ack_key]["mtta_values"].append(mtta_seconds / 60.0)

    rows: list[Dict[str, Any]] = []
    for day in sorted(buckets.keys()):
        row = buckets[day]
        mtta_values = row.pop("mtta_values")
        mttr_values = row.pop("mttr_values")
        row["mtta_avg_minutes"] = (
            round(sum(mtta_values) / len(mtta_values), 2) if mtta_values else None
        )
        row["mttr_avg_minutes"] = (
            round(sum(mttr_values) / len(mttr_values), 2) if mttr_values else None
        )
        rows.append(row)

    return rows


def _period_bounds(
    window: str = "weekly",
) -> tuple[datetime, datetime, datetime, datetime, int]:
    normalized = (window or "weekly").strip().lower()
    if normalized == "monthly":
        days = 30
    elif normalized == "weekly":
        days = 7
    else:
        raise HTTPException(status_code=400, detail="window must be weekly or monthly")

    now = datetime.now(tz=timezone.utc)
    current_end = now
    current_start = now - timedelta(days=days)
    previous_end = current_start
    previous_start = current_start - timedelta(days=days)
    return current_start, current_end, previous_start, previous_end, days


def _in_range(ts: datetime | None, start: datetime, end: datetime) -> bool:
    if not ts:
        return False
    return start <= ts < end


def _period_incident_stats(
    incidents: list[Dict[str, Any]], start: datetime, end: datetime
) -> Dict[str, Any]:
    created = 0
    acknowledged = 0
    closed = 0
    active_end = 0
    mtta_values: list[float] = []
    mttr_values: list[float] = []
    severity_counts: Dict[str, int] = {}

    for item in incidents:
        created_at = _parse_timestamp(item.get("created_at"))
        ack_at = _parse_timestamp(item.get("ack_at"))
        closed_at = _parse_timestamp(item.get("closed_at"))

        if _in_range(created_at, start, end):
            created += 1
            sev = str(item.get("severity") or "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if _in_range(ack_at, start, end):
            acknowledged += 1
            ack_seconds = _seconds_between(item.get("created_at"), item.get("ack_at"))
            if ack_seconds is not None:
                mtta_values.append(ack_seconds / 60.0)

        if _in_range(closed_at, start, end):
            closed += 1
            close_seconds = _seconds_between(
                item.get("created_at"), item.get("closed_at")
            )
            if close_seconds is not None:
                mttr_values.append(close_seconds / 60.0)

        is_active_at_end = (
            created_at is not None
            and created_at < end
            and (closed_at is None or closed_at >= end)
        )
        if is_active_at_end:
            active_end += 1

    def _avg(values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    return {
        "created": created,
        "acknowledged": acknowledged,
        "closed": closed,
        "active_end": active_end,
        "closure_rate": round((closed / created) * 100.0, 2) if created > 0 else None,
        "mtta_minutes": _avg(mtta_values),
        "mttr_minutes": _avg(mttr_values),
        "severity_counts": severity_counts,
    }


def _pct_delta(
    current: float | int | None, previous: float | int | None
) -> float | None:
    if current is None or previous is None:
        return None
    if previous == 0:
        return None
    return round(((float(current) - float(previous)) / float(previous)) * 100.0, 2)


def _scan_incidents_from_anomalies(
    anomalies: Dict[str, Any],
    incidents: list[Dict[str, Any]],
    *,
    actor_threshold: int,
    action_threshold: int,
) -> Dict[str, Any]:
    now = _now_iso()
    candidates: list[Dict[str, Any]] = []
    for item in anomalies.get("actor_spikes", []):
        actor = str(item.get("actor") or "unknown")
        candidates.append(
            {
                "kind": "actor_spike",
                "key": actor,
                "count": int(item.get("count") or 0),
                "threshold": actor_threshold,
            }
        )
    for item in anomalies.get("action_spikes", []):
        action_name = str(item.get("action") or "unknown")
        candidates.append(
            {
                "kind": "action_spike",
                "key": action_name,
                "count": int(item.get("count") or 0),
                "threshold": action_threshold,
            }
        )

    created = 0
    updated = 0
    for candidate in candidates:
        fingerprint = _incident_fingerprint(candidate["kind"], candidate["key"])
        existing = next(
            (
                item
                for item in incidents
                if item.get("fingerprint") == fingerprint
                and item.get("status") != "closed"
            ),
            None,
        )

        if existing:
            previous_count = int(existing.get("count") or 0)
            existing["count"] = candidate["count"]
            existing["threshold"] = candidate["threshold"]
            existing["updated_at"] = now
            existing["last_seen_at"] = now
            if existing.get("status") == "silenced" and not _is_silenced_active(
                existing
            ):
                existing["status"] = "open"
                existing["silenced_until"] = None
                _append_incident_history(
                    existing,
                    event="silence_expired",
                    actor_id="system",
                    metadata={"reason": "silence window expired during scan"},
                )
            if previous_count != candidate["count"]:
                _append_incident_history(
                    existing,
                    event="scan_update",
                    actor_id="system",
                    metadata={
                        "previous_count": previous_count,
                        "count": candidate["count"],
                        "threshold": candidate["threshold"],
                    },
                )
            _set_incident_severity(existing, actor_id="system", reason="scan")
            updated += 1
            continue

        incidents.append(
            {
                "id": hashlib.md5(f"{fingerprint}:{now}".encode("utf-8")).hexdigest()[
                    :12
                ],
                "fingerprint": fingerprint,
                "kind": candidate["kind"],
                "key": candidate["key"],
                "count": candidate["count"],
                "threshold": candidate["threshold"],
                "status": "open",
                "severity": "low",
                "created_at": now,
                "updated_at": now,
                "last_seen_at": now,
                "ack_by": None,
                "ack_at": None,
                "closed_by": None,
                "closed_at": None,
                "silenced_until": None,
                "note": "",
                "history": [
                    {
                        "at": now,
                        "event": "created_by_scan",
                        "by": "system",
                        "metadata": {
                            "count": candidate["count"],
                            "threshold": candidate["threshold"],
                        },
                    }
                ],
            }
        )
        _set_incident_severity(
            incidents[-1], actor_id="system", reason="created_by_scan"
        )
        created += 1

    return {
        "created": created,
        "updated": updated,
        "total_candidates": len(candidates),
    }


def _detect_anomalies(
    rows: list[Dict[str, Any]],
    *,
    lookback_hours: int = 24,
    actor_threshold: int = 10,
    action_threshold: int = 20,
) -> Dict[str, Any]:
    now = datetime.now(tz=timezone.utc)
    safe_hours = max(1, min(lookback_hours, 720))
    safe_actor_threshold = max(2, min(actor_threshold, 1000))
    safe_action_threshold = max(2, min(action_threshold, 5000))
    boundary = now.timestamp() - (safe_hours * 3600)

    recent: list[Dict[str, Any]] = []
    for row in rows:
        ts = _parse_timestamp(row.get("timestamp"))
        if ts and ts.timestamp() >= boundary:
            recent.append(row)

    by_actor: Dict[str, int] = {}
    by_action: Dict[str, int] = {}
    for row in recent:
        actor = str(row.get("updated_by", "unknown") or "unknown")
        action = str(row.get("action", "unknown") or "unknown")
        by_actor[actor] = by_actor.get(actor, 0) + 1
        by_action[action] = by_action.get(action, 0) + 1

    actor_spikes = [
        {"actor": actor, "count": count, "threshold": safe_actor_threshold}
        for actor, count in sorted(
            by_actor.items(), key=lambda item: item[1], reverse=True
        )
        if count >= safe_actor_threshold
    ]
    action_spikes = [
        {"action": action, "count": count, "threshold": safe_action_threshold}
        for action, count in sorted(
            by_action.items(), key=lambda item: item[1], reverse=True
        )
        if count >= safe_action_threshold
    ]

    return {
        "lookback_hours": safe_hours,
        "recent_events": len(recent),
        "has_anomaly": bool(actor_spikes or action_spikes),
        "actor_spikes": actor_spikes,
        "action_spikes": action_spikes,
    }

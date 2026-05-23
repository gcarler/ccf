from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _filter_audit_rows(
    rows: list[Dict[str, Any]],
    *,
    action: str | None = None,
    feature_id: str | None = None,
    actor: str | None = None,
    limit: int = 100,
) -> list[Dict[str, Any]]:
    filtered = rows
    if action:
        action_norm = action.strip().lower()
        filtered = [
            row for row in filtered if str(row.get("action", "")).lower() == action_norm
        ]
    if feature_id:
        filtered = [
            row for row in filtered if str(row.get("feature_id", "")) == feature_id
        ]
    if actor:
        actor_norm = actor.strip()
        filtered = [
            row for row in filtered if str(row.get("updated_by", "")) == actor_norm
        ]
    return filtered[-max(1, min(limit, 1000)) :]


def _build_event_diff(row: Dict[str, Any]) -> Dict[str, Any]:
    before = row.get("before")
    after = row.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {"count": 0, "changes": []}

    keys = sorted(set(before.keys()) | set(after.keys()))
    changes: list[Dict[str, Any]] = []
    for key in keys:
        old_value = before.get(key)
        new_value = after.get(key)
        if old_value == new_value:
            continue
        changes.append({"key": key, "before": old_value, "after": new_value})

    return {
        "count": len(changes),
        "changes": changes,
        "summary": f"{len(changes)} key(s) changed",
    }


def _enrich_audit_rows(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    enriched: list[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["diff"] = _build_event_diff(item)
        enriched.append(item)
    return enriched


def _summarize_audit(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    by_action: Dict[str, int] = {}
    by_actor: Dict[str, int] = {}
    by_feature: Dict[str, int] = {}

    for row in rows:
        action_value = str(row.get("action", "unknown") or "unknown")
        actor_value = str(row.get("updated_by", "unknown") or "unknown")
        feature_value = str(row.get("feature_id", "global") or "global")

        by_action[action_value] = by_action.get(action_value, 0) + 1
        by_actor[actor_value] = by_actor.get(actor_value, 0) + 1
        by_feature[feature_value] = by_feature.get(feature_value, 0) + 1

    top_actors = sorted(by_actor.items(), key=lambda item: item[1], reverse=True)[:5]
    top_features = sorted(by_feature.items(), key=lambda item: item[1], reverse=True)[
        :5
    ]

    return {
        "total_events": len(rows),
        "by_action": by_action,
        "top_actors": [{"actor": actor, "count": count} for actor, count in top_actors],
        "top_features": [
            {"feature": feature, "count": count} for feature, count in top_features
        ],
    }

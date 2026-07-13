from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from backend.api.workspace_shared import (
    AUDIT_FILE,
    DATA_DIR,
    DEFAULT_COMPLIANCE_POLICY,
    DEFAULT_WORKSPACE_CONFIG,
    FLAGS_FILE,
    INCIDENTS_FILE,
    NOTIFICATIONS_FILE,
    SNAPSHOT_HISTORY_FILE,
)
from backend.core.file_lock import file_lock

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _json_canonical(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Workspace config
# ---------------------------------------------------------------------------


def _load_workspace_config() -> Dict[str, Any]:
    if not FLAGS_FILE.exists():
        return DEFAULT_WORKSPACE_CONFIG
    try:
        data = json.loads(FLAGS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            default_rules = DEFAULT_WORKSPACE_CONFIG.get("feature_rules", {}) or {}
            data_rules = data.get("feature_rules") or {}
            merged_rules = {**default_rules}
            for key, value in data_rules.items():
                base_rule = dict(default_rules.get(key) or {})
                if isinstance(value, dict):
                    merged_rules[key] = {**base_rule, **value}
                else:
                    merged_rules[key] = base_rule

            default_policy = DEFAULT_COMPLIANCE_POLICY
            data_policy = data.get("compliance_policy") or {}
            default_envs = default_policy.get("environments", {}) or {}
            data_envs = (
                data_policy.get("environments", {})
                if isinstance(data_policy, dict)
                else {}
            )
            merged_envs: Dict[str, Any] = {**default_envs}
            for env_name, env_value in data_envs.items():
                base_env = dict(default_envs.get(env_name) or {})
                if isinstance(env_value, dict):
                    merged_envs[env_name] = {**base_env, **env_value}

            merged_policy = {
                **default_policy,
                **(data_policy if isinstance(data_policy, dict) else {}),
                "environments": merged_envs,
                "critical_feature_flags": sorted(
                    {
                        *list(default_policy.get("critical_feature_flags", [])),
                        *list(
                            (
                                data_policy.get("critical_feature_flags")
                                if isinstance(data_policy, dict)
                                else []
                            )
                            or []
                        ),
                    }
                ),
                "suppressions": list(
                    (
                        data_policy.get("suppressions")
                        if isinstance(data_policy, dict)
                        else []
                    )
                    or []
                ),
            }

            merged = {
                **DEFAULT_WORKSPACE_CONFIG,
                **data,
                "features_enabled": {
                    **DEFAULT_WORKSPACE_CONFIG.get("features_enabled", {}),
                    **(data.get("features_enabled") or {}),
                },
                "feature_rules": merged_rules,
                "compliance_policy": merged_policy,
            }
            return merged
    except MemoryError:
        raise
    except Exception as exc:
        logger.exception("Failed to load workspace config from %s", FLAGS_FILE)
        return DEFAULT_WORKSPACE_CONFIG
    return DEFAULT_WORKSPACE_CONFIG


def _save_workspace_config(config: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with file_lock(FLAGS_FILE):
        FLAGS_FILE.write_text(
            json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Incidents persistence
# ---------------------------------------------------------------------------


def _load_incidents() -> list[Dict[str, Any]]:
    if not INCIDENTS_FILE.exists():
        return []
    try:
        payload = json.loads(INCIDENTS_FILE.read_text(encoding="utf-8"))
    except MemoryError:
        raise
    except Exception as exc:
        logger.exception("Failed to load incidents from %s", INCIDENTS_FILE)
        return []
    if not isinstance(payload, list):
        return []

    normalized: list[Dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": str(item.get("id") or ""),
                "fingerprint": str(item.get("fingerprint") or ""),
                "kind": str(item.get("kind") or "unknown"),
                "key": str(item.get("key") or "unknown"),
                "count": int(item.get("count") or 0),
                "threshold": int(item.get("threshold") or 0),
                "status": str(item.get("status") or "open"),
                "severity": str(item.get("severity") or "low"),
                "created_at": str(item.get("created_at") or _now_iso()),
                "updated_at": str(item.get("updated_at") or _now_iso()),
                "last_seen_at": str(item.get("last_seen_at") or _now_iso()),
                "ack_by": item.get("ack_by"),
                "ack_at": item.get("ack_at"),
                "closed_by": item.get("closed_by"),
                "closed_at": item.get("closed_at"),
                "silenced_until": item.get("silenced_until"),
                "note": item.get("note") or "",
                "history": (
                    item.get("history") if isinstance(item.get("history"), list) else []
                ),
            }
        )
    return normalized


def _save_incidents(incidents: list[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with file_lock(INCIDENTS_FILE):
        INCIDENTS_FILE.write_text(
            json.dumps(incidents, ensure_ascii=True, indent=2), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def _read_audit_events(limit: int = 100) -> list[Dict[str, Any]]:
    clamped = max(1, min(limit, 1000))
    if not AUDIT_FILE.exists():
        return []
    rows: list[Dict[str, Any]] = []
    for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows[-clamped:]


def _append_audit_event(event: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        **event,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def _append_notification(event: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": _now_iso(),
        **event,
    }
    with NOTIFICATIONS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _read_notifications(limit: int = 100) -> list[Dict[str, Any]]:
    clamped = max(1, min(limit, 1000))
    if not NOTIFICATIONS_FILE.exists():
        return []
    rows: list[Dict[str, Any]] = []
    for line in NOTIFICATIONS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows[-clamped:]


# ---------------------------------------------------------------------------
# Snapshot history persistence
# ---------------------------------------------------------------------------


def _append_snapshot_history(entry: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_HISTORY_FILE.open("a", encoding="utf-8") as fh:
        fh.write(_json_canonical(entry) + "\n")


def _read_snapshot_history(limit: int = 1000) -> list[Dict[str, Any]]:
    clamped = max(1, min(limit, 5000))
    if not SNAPSHOT_HISTORY_FILE.exists():
        return []
    rows: list[Dict[str, Any]] = []
    for line in SNAPSHOT_HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows[-clamped:]


def _save_snapshot_history(rows: list[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with file_lock(SNAPSHOT_HISTORY_FILE):
        with SNAPSHOT_HISTORY_FILE.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(_json_canonical(row) + "\n")


# ---------------------------------------------------------------------------
# Incident history helper
# ---------------------------------------------------------------------------


def _append_incident_history(
    incident: Dict[str, Any],
    *,
    event: str,
    actor_id: str,
    note: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    history = incident.get("history")
    if not isinstance(history, list):
        history = []
    entry: Dict[str, Any] = {
        "at": _now_iso(),
        "event": event,
        "by": actor_id,
    }
    if note:
        entry["note"] = note
    if metadata:
        entry["metadata"] = metadata
    history.append(entry)
    incident["history"] = history[-50:]

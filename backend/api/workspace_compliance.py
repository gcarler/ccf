import json
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import models
from backend.auth import require_admin
from backend.core.rate_limit import rate_limiter
from backend.api.workspace_shared import (
    DEFAULT_COMPLIANCE_POLICY,
    _append_audit_event,
    _append_snapshot_history,
    _build_compliance_snapshot,
    _cleanup_snapshot_history,
    _compare_snapshot_payloads,
    _find_snapshot_history_item,
    _load_workspace_config,
    _maybe_emit_snapshot_drift_alert,
    _normalize_compliance_policy_update,
    _normalize_suppression_payload,
    _now_iso,
    _parse_timestamp,
    _read_snapshot_history,
    _resolve_compliance_policy,
    _resolve_compare_pair,
    _save_snapshot_history,
    _verify_snapshot_history_item,
    _weekly_snapshot_summary,
    _save_workspace_config,
)


router = APIRouter(tags=["workspace"])


@router.get("/flags/compliance/snapshot", dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))])
def get_flags_compliance_snapshot(
    download: bool = False,
    record: bool = True,
    environment: str | None = None,
    audit_limit: int = 200,
    incident_limit: int = 200,
    lookback_hours: int = 24,
    actor_threshold: int = 10,
    action_threshold: int = 20,
    current_user: models.User = Depends(require_admin),
):
    actor_id = str(getattr(current_user, "id", ""))
    snapshot = _build_compliance_snapshot(
        actor_id=actor_id,
        environment=environment,
        audit_limit=audit_limit,
        incident_limit=incident_limit,
        lookback_hours=lookback_hours,
        actor_threshold=actor_threshold,
        action_threshold=action_threshold,
    )

    if record:
        previous_rows = _read_snapshot_history(limit=5000)
        previous_entry = previous_rows[-1] if previous_rows else None
        history_entry = {
            "recorded_at": _now_iso(),
            "snapshot_id": snapshot.get("signature", {}).get("snapshot_id"),
            "schema_version": snapshot.get("schema_version"),
            "generated_at": snapshot.get("generated_at"),
            "requested_by": snapshot.get("requested_by"),
            "signature": snapshot.get("signature"),
            "summary": {
                "features_enabled": len((snapshot.get("config", {}).get("features_enabled") or {})),
                "audit_events": snapshot.get("audit", {}).get("count"),
                "incidents": snapshot.get("incidents", {}).get("count"),
                "has_anomaly": snapshot.get("audit", {}).get("anomalies", {}).get("has_anomaly"),
                "critical_incidents": snapshot.get("incidents", {}).get("summary", {}).get("severity_counts", {}).get("critical", 0),
            },
            "snapshot": snapshot,
        }
        drift_from_previous = _maybe_emit_snapshot_drift_alert(previous_entry=previous_entry, current_entry=history_entry)
        if drift_from_previous is not None:
            history_entry["drift_from_previous"] = drift_from_previous
        _append_snapshot_history(history_entry)

    if download:
        return Response(
            content=json.dumps(snapshot, ensure_ascii=True, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=flags_compliance_snapshot.json"},
        )

    return {
        "status": "ok",
        **snapshot,
    }


@router.get("/flags/compliance/policy", dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))])
def get_flags_compliance_policy(
    environment: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    config = _load_workspace_config()
    raw_policy = config.get("compliance_policy") if isinstance(config.get("compliance_policy"), dict) else DEFAULT_COMPLIANCE_POLICY
    resolved = _resolve_compliance_policy(raw_policy, environment=environment)
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "policy": raw_policy,
        "resolved": resolved,
    }


@router.put("/flags/compliance/policy", dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))])
def update_flags_compliance_policy(
    payload: Dict[str, Any],
    current_user: models.User = Depends(require_admin),
):
    config = _load_workspace_config()
    current_policy = config.get("compliance_policy") if isinstance(config.get("compliance_policy"), dict) else DEFAULT_COMPLIANCE_POLICY
    next_policy = _normalize_compliance_policy_update(payload, current_policy)
    config["compliance_policy"] = next_policy
    _save_workspace_config(config)
    _append_audit_event(
        {
            "action": "update_compliance_policy",
            "updated_by": str(getattr(current_user, "id", "")),
            "before": current_policy,
            "after": next_policy,
        }
    )
    return {
        "status": "ok",
        "updated_by": str(getattr(current_user, "id", "")),
        "policy": next_policy,
        "resolved": _resolve_compliance_policy(next_policy),
    }


@router.post("/flags/compliance/suppressions", dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))])
def create_flags_compliance_suppression(
    payload: Dict[str, Any],
    current_user: models.User = Depends(require_admin),
):
    config = _load_workspace_config()
    policy = config.get("compliance_policy") if isinstance(config.get("compliance_policy"), dict) else DEFAULT_COMPLIANCE_POLICY
    suppressions = list(policy.get("suppressions") or [])
    actor_id = str(getattr(current_user, "id", ""))
    entry = _normalize_suppression_payload(payload, actor_id=actor_id)
    suppressions.append(entry)
    policy["suppressions"] = suppressions
    config["compliance_policy"] = policy
    _save_workspace_config(config)
    _append_audit_event(
        {
            "action": "create_compliance_suppression",
            "updated_by": actor_id,
            "changes": entry,
        }
    )
    return {
        "status": "ok",
        "suppression": entry,
        "resolved": _resolve_compliance_policy(policy),
    }


@router.delete("/flags/compliance/suppressions/{suppression_id}", dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))])
def delete_flags_compliance_suppression(
    suppression_id: str,
    current_user: models.User = Depends(require_admin),
):
    config = _load_workspace_config()
    policy = config.get("compliance_policy") if isinstance(config.get("compliance_policy"), dict) else DEFAULT_COMPLIANCE_POLICY
    suppressions = list(policy.get("suppressions") or [])
    previous_len = len(suppressions)
    suppressions = [item for item in suppressions if str(item.get("id", "")) != suppression_id]
    if len(suppressions) == previous_len:
        raise HTTPException(status_code=404, detail="suppression not found")

    policy["suppressions"] = suppressions
    config["compliance_policy"] = policy
    _save_workspace_config(config)
    actor_id = str(getattr(current_user, "id", ""))
    _append_audit_event(
        {
            "action": "delete_compliance_suppression",
            "updated_by": actor_id,
            "changes": {"suppression_id": suppression_id},
        }
    )
    return {
        "status": "ok",
        "deleted": suppression_id,
        "resolved": _resolve_compliance_policy(policy),
    }


@router.get("/flags/compliance/history", dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))])
def get_flags_compliance_history(
    limit: int = 50,
    since: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _read_snapshot_history(limit=1000)
    if since:
        since_dt = _parse_timestamp(since)
        if since_dt is None:
            raise HTTPException(status_code=422, detail="Invalid since datetime")
        rows = [row for row in rows if (_parse_timestamp(row.get("recorded_at")) or datetime.fromtimestamp(0, tz=timezone.utc)) >= since_dt]

    capped_limit = max(1, min(limit, 500))
    rows = rows[-capped_limit:]
    compact = [
        {
            "recorded_at": row.get("recorded_at"),
            "snapshot_id": row.get("snapshot_id"),
            "schema_version": row.get("schema_version"),
            "requested_by": row.get("requested_by"),
            "signature": row.get("signature"),
            "summary": row.get("summary", {}),
            "drift_from_previous": row.get("drift_from_previous"),
        }
        for row in rows
    ]
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "count": len(compact),
        "history": compact,
    }


@router.get("/flags/compliance/history/weekly-summary", dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))])
def get_flags_compliance_history_weekly_summary(
    weeks: int = 8,
    current_user: models.User = Depends(require_admin),
):
    rows = _read_snapshot_history(limit=5000)
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "weeks": max(1, min(weeks, 104)),
        "rows": _weekly_snapshot_summary(rows, weeks=weeks),
    }


@router.get("/flags/compliance/history/{snapshot_id}", dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))])
def get_flags_compliance_history_item(
    snapshot_id: str,
    download: bool = False,
    current_user: models.User = Depends(require_admin),
):
    rows = _read_snapshot_history(limit=5000)
    item = _find_snapshot_history_item(rows, snapshot_id)
    if not item:
        raise HTTPException(status_code=404, detail="snapshot not found")

    verification = _verify_snapshot_history_item(item)
    if download:
        return Response(
            content=json.dumps(item, ensure_ascii=True, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=flags_compliance_snapshot_{snapshot_id}.json"},
        )

    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "item": item,
        "verification": verification,
    }


@router.get("/flags/compliance/compare", dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))])
def compare_flags_compliance_snapshots(
    from_snapshot_id: str | None = None,
    to_snapshot_id: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _read_snapshot_history(limit=5000)
    first, second = _resolve_compare_pair(rows, from_snapshot_id, to_snapshot_id)
    first_snapshot_id = str(first.get("snapshot_id") or "")
    second_snapshot_id = str(second.get("snapshot_id") or "")
    first_payload = first.get("snapshot") or {}
    second_payload = second.get("snapshot") or {}
    if not isinstance(first_payload, dict) or not isinstance(second_payload, dict):
        raise HTTPException(status_code=422, detail="Invalid snapshot payload in history")

    second_config = second_payload.get("config") if isinstance(second_payload.get("config"), dict) else {}
    second_policy = second_config.get("compliance_policy") if isinstance(second_config.get("compliance_policy"), dict) else None
    second_inputs = second_payload.get("inputs") if isinstance(second_payload.get("inputs"), dict) else {}
    diff = _compare_snapshot_payloads(
        first_payload,
        second_payload,
        policy=second_policy,
        environment=(str(second_inputs.get("environment")) if second_inputs.get("environment") else None),
    )
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "from": {
            "snapshot_id": first_snapshot_id,
            "recorded_at": first.get("recorded_at"),
        },
        "to": {
            "snapshot_id": second_snapshot_id,
            "recorded_at": second.get("recorded_at"),
        },
        "diff": diff,
        "verification": {
            "from": _verify_snapshot_history_item(first),
            "to": _verify_snapshot_history_item(second),
        },
    }


@router.get("/flags/compliance/drift", dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))])
def get_flags_compliance_drift(
    from_snapshot_id: str | None = None,
    to_snapshot_id: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _read_snapshot_history(limit=5000)
    first, second = _resolve_compare_pair(rows, from_snapshot_id, to_snapshot_id)
    first_payload = first.get("snapshot") or {}
    second_payload = second.get("snapshot") or {}
    if not isinstance(first_payload, dict) or not isinstance(second_payload, dict):
        raise HTTPException(status_code=422, detail="Invalid snapshot payload in history")

    second_config = second_payload.get("config") if isinstance(second_payload.get("config"), dict) else {}
    second_policy = second_config.get("compliance_policy") if isinstance(second_config.get("compliance_policy"), dict) else None
    second_inputs = second_payload.get("inputs") if isinstance(second_payload.get("inputs"), dict) else {}
    diff = _compare_snapshot_payloads(
        first_payload,
        second_payload,
        policy=second_policy,
        environment=(str(second_inputs.get("environment")) if second_inputs.get("environment") else None),
    )
    drift = diff.get("drift") or {}
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "from": {
            "snapshot_id": str(first.get("snapshot_id") or ""),
            "recorded_at": first.get("recorded_at"),
        },
        "to": {
            "snapshot_id": str(second.get("snapshot_id") or ""),
            "recorded_at": second.get("recorded_at"),
        },
        "drift": drift,
        "verification": {
            "from": _verify_snapshot_history_item(first),
            "to": _verify_snapshot_history_item(second),
        },
    }


@router.post("/flags/compliance/history/cleanup", dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))])
def cleanup_flags_compliance_history(
    retain_days: int = 90,
    current_user: models.User = Depends(require_admin),
):
    rows = _read_snapshot_history(limit=5000)
    result = _cleanup_snapshot_history(rows, retain_days=retain_days)
    _save_snapshot_history(rows)
    _append_audit_event(
        {
            "action": "cleanup_compliance_history",
            "updated_by": str(getattr(current_user, "id", "")),
            "changes": result,
        }
    )
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "cleanup": result,
    }

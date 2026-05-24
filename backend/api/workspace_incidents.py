import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import models
from backend.api.workspace_shared import (_append_audit_event,
                                          _append_incident_history,
                                          _cleanup_incidents,
                                          _detect_anomalies,
                                          _filter_audit_rows,
                                          _incident_daily_trends,
                                          _load_incidents, _now_iso,
                                          _pct_delta, _period_bounds,
                                          _period_incident_stats,
                                          _read_audit_events,
                                          _read_notifications, _save_incidents,
                                          _scan_incidents_from_anomalies,
                                          _set_incident_severity,
                                          _summarize_incidents)
from backend.auth import require_admin
from backend.core.rate_limit import rate_limiter

router = APIRouter(tags=["workspace"])


@router.get(
    "/flags/incidents",
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_flags_incidents(
    status: str | None = None,
    limit: int = 200,
    mtta_target_minutes: int = 60,
    mttr_target_minutes: int = 240,
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    if status:
        status_norm = status.strip().lower()
        incidents = [
            item
            for item in incidents
            if str(item.get("status", "")).lower() == status_norm
        ]

    capped_limit = max(1, min(limit, 1000))
    incidents = incidents[-capped_limit:]
    return {
        "status": "ok",
        "count": len(incidents),
        "requested_by": str(getattr(current_user, "id", "")),
        "summary": _summarize_incidents(
            incidents,
            mtta_target_minutes=mtta_target_minutes,
            mttr_target_minutes=mttr_target_minutes,
        ),
        "incidents": incidents,
    }


@router.get(
    "/flags/incidents/summary",
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_flags_incidents_summary(
    status: str | None = None,
    mtta_target_minutes: int = 60,
    mttr_target_minutes: int = 240,
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    if status:
        status_norm = status.strip().lower()
        incidents = [
            item
            for item in incidents
            if str(item.get("status", "")).lower() == status_norm
        ]
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "summary": _summarize_incidents(
            incidents,
            mtta_target_minutes=mtta_target_minutes,
            mttr_target_minutes=mttr_target_minutes,
        ),
    }


@router.get(
    "/flags/incidents/trends",
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_flags_incidents_trends(
    days: int = 14,
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "days": max(1, min(days, 180)),
        "rows": _incident_daily_trends(incidents, days=days),
    }


@router.get(
    "/flags/incidents/notifications",
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_flags_incident_notifications(
    limit: int = 100,
    current_user: models.User = Depends(require_admin),
):
    rows = _read_notifications(limit=limit)
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "count": len(rows),
        "notifications": rows,
    }


@router.get(
    "/flags/incidents/stats",
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_flags_incidents_stats(
    window: str = "weekly",
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    current_start, current_end, previous_start, previous_end, days = _period_bounds(
        window
    )
    current_stats = _period_incident_stats(incidents, current_start, current_end)
    previous_stats = _period_incident_stats(incidents, previous_start, previous_end)
    deltas = {
        "created_pct": _pct_delta(
            current_stats.get("created"), previous_stats.get("created")
        ),
        "closed_pct": _pct_delta(
            current_stats.get("closed"), previous_stats.get("closed")
        ),
        "closure_rate_pct": _pct_delta(
            current_stats.get("closure_rate"), previous_stats.get("closure_rate")
        ),
        "mtta_pct": _pct_delta(
            current_stats.get("mtta_minutes"), previous_stats.get("mtta_minutes")
        ),
        "mttr_pct": _pct_delta(
            current_stats.get("mttr_minutes"), previous_stats.get("mttr_minutes")
        ),
        "active_end_pct": _pct_delta(
            current_stats.get("active_end"), previous_stats.get("active_end")
        ),
    }
    trends = _incident_daily_trends(incidents, days=days)
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "window": window,
        "days": days,
        "current": current_stats,
        "previous": previous_stats,
        "deltas": deltas,
        "trends": trends,
    }


@router.get(
    "/flags/incidents/export",
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
def export_flags_incidents(
    format: str = "json",
    status: str | None = None,
    severity: str | None = None,
    limit: int = 500,
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    if status:
        status_norm = status.strip().lower()
        incidents = [
            item
            for item in incidents
            if str(item.get("status", "")).lower() == status_norm
        ]
    if severity:
        severity_norm = severity.strip().lower()
        incidents = [
            item
            for item in incidents
            if str(item.get("severity", "")).lower() == severity_norm
        ]

    capped_limit = max(1, min(limit, 1000))
    incidents = incidents[-capped_limit:]
    normalized_format = format.strip().lower()
    if normalized_format == "json":
        payload = {
            "status": "ok",
            "count": len(incidents),
            "requested_by": str(getattr(current_user, "id", "")),
            "incidents": incidents,
        }
        return Response(
            content=json.dumps(payload, ensure_ascii=True, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=feature_flags_incidents.json"
            },
        )

    if normalized_format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "id",
                "kind",
                "key",
                "status",
                "severity",
                "count",
                "threshold",
                "created_at",
                "updated_at",
                "ack_at",
                "closed_at",
                "silenced_until",
                "note",
                "history",
            ],
        )
        writer.writeheader()
        for item in incidents:
            writer.writerow(
                {
                    "id": item.get("id", ""),
                    "kind": item.get("kind", ""),
                    "key": item.get("key", ""),
                    "status": item.get("status", ""),
                    "severity": item.get("severity", ""),
                    "count": item.get("count", ""),
                    "threshold": item.get("threshold", ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                    "ack_at": item.get("ack_at", ""),
                    "closed_at": item.get("closed_at", ""),
                    "silenced_until": item.get("silenced_until", ""),
                    "note": item.get("note", ""),
                    "history": json.dumps(item.get("history", []), ensure_ascii=True),
                }
            )
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=feature_flags_incidents.csv"
            },
        )

    raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")


@router.post(
    "/flags/incidents/scan",
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
def scan_flags_incidents(
    lookback_hours: int = 24,
    actor_threshold: int = 10,
    action_threshold: int = 20,
    action: str | None = None,
    feature_id: str | None = None,
    actor: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _filter_audit_rows(
        _read_audit_events(limit=1000),
        action=action,
        feature_id=feature_id,
        actor=actor,
        limit=1000,
    )
    anomalies = _detect_anomalies(
        rows,
        lookback_hours=lookback_hours,
        actor_threshold=actor_threshold,
        action_threshold=action_threshold,
    )
    incidents = _load_incidents()
    scan_result = _scan_incidents_from_anomalies(
        anomalies,
        incidents,
        actor_threshold=max(2, min(actor_threshold, 1000)),
        action_threshold=max(2, min(action_threshold, 5000)),
    )
    _save_incidents(incidents)
    _append_audit_event(
        {
            "action": "scan_incidents",
            "updated_by": str(getattr(current_user, "id", "")),
            "changes": {
                "created": scan_result["created"],
                "updated": scan_result["updated"],
                "candidates": scan_result["total_candidates"],
                "lookback_hours": lookback_hours,
            },
        }
    )
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "scan": scan_result,
        "anomalies": anomalies,
    }


@router.patch(
    "/flags/incidents/{incident_id}",
    dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))],
)
def update_flags_incident(
    incident_id: str,
    payload: Dict[str, Any],
    current_user: models.User = Depends(require_admin),
):
    action = str(payload.get("action") or "").strip().lower()
    note = str(payload.get("note") or "").strip()
    silence_minutes = payload.get("silence_minutes", 60)
    if action not in {"acknowledge", "close", "reopen", "silence", "note"}:
        raise HTTPException(
            status_code=400,
            detail="action must be acknowledge|close|reopen|silence|note",
        )

    incidents = _load_incidents()
    incident = next(
        (item for item in incidents if str(item.get("id", "")) == incident_id), None
    )
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")

    now = _now_iso()
    actor_id = str(getattr(current_user, "id", ""))

    if action == "acknowledge":
        incident["status"] = "acknowledged"
        incident["ack_by"] = actor_id
        incident["ack_at"] = now
        _append_incident_history(
            incident, event="acknowledged", actor_id=actor_id, note=note
        )
    elif action == "close":
        incident["status"] = "closed"
        incident["closed_by"] = actor_id
        incident["closed_at"] = now
        _append_incident_history(incident, event="closed", actor_id=actor_id, note=note)
    elif action == "reopen":
        incident["status"] = "open"
        incident["silenced_until"] = None
        _append_incident_history(
            incident, event="reopened", actor_id=actor_id, note=note
        )
    elif action == "silence":
        try:
            minutes = max(1, min(int(silence_minutes), 60 * 24 * 7))
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=422, detail="silence_minutes must be an integer"
            )
        until_dt = datetime.now(tz=timezone.utc).timestamp() + (minutes * 60)
        incident["status"] = "silenced"
        incident["silenced_until"] = datetime.fromtimestamp(
            until_dt, tz=timezone.utc
        ).isoformat()
        _append_incident_history(
            incident,
            event="silenced",
            actor_id=actor_id,
            note=note,
            metadata={"silence_minutes": minutes},
        )
    elif action == "note":
        if not note:
            raise HTTPException(
                status_code=422, detail="note is required when action=note"
            )
        _append_incident_history(incident, event="note", actor_id=actor_id, note=note)

    if note:
        incident["note"] = note
    _set_incident_severity(
        incident, actor_id=actor_id, reason=f"incident_action:{action}"
    )
    incident["updated_at"] = now
    _save_incidents(incidents)
    _append_audit_event(
        {
            "action": "update_incident",
            "feature_id": str(incident.get("key") or ""),
            "updated_by": actor_id,
            "changes": {
                "incident_id": incident_id,
                "incident_action": action,
                "status": incident.get("status"),
            },
        }
    )
    return {
        "status": "ok",
        "requested_by": actor_id,
        "incident": incident,
    }


@router.post(
    "/flags/incidents/cleanup",
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
def cleanup_flags_incidents(
    retain_closed_days: int = 30,
    retain_resolved_days: int = 14,
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    result = _cleanup_incidents(
        incidents,
        retain_closed_days=retain_closed_days,
        retain_resolved_days=retain_resolved_days,
    )
    _save_incidents(incidents)
    _append_audit_event(
        {
            "action": "cleanup_incidents",
            "updated_by": str(getattr(current_user, "id", "")),
            "changes": {
                **result,
                "retain_closed_days": max(1, min(retain_closed_days, 3650)),
                "retain_resolved_days": max(1, min(retain_resolved_days, 3650)),
            },
        }
    )
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "cleanup": result,
        "summary": _summarize_incidents(incidents),
    }

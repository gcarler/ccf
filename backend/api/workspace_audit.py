import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import models
from backend.auth import require_admin
from backend.core.rate_limit import rate_limiter
from backend.api.workspace_shared import (
    _detect_anomalies,
    _enrich_audit_rows,
    _filter_audit_rows,
    _read_audit_events,
    _summarize_audit,
)


router = APIRouter(tags=["workspace"])


@router.get("/flags/audit", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
def get_flags_audit(
    limit: int = 100,
    action: str | None = None,
    feature_id: str | None = None,
    actor: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _filter_audit_rows(_read_audit_events(limit=1000), action=action, feature_id=feature_id, actor=actor, limit=limit)
    rows = _enrich_audit_rows(rows)
    return {
        "status": "ok",
        "count": len(rows),
        "requested_by": str(getattr(current_user, "id", "")),
        "events": rows,
    }


@router.get("/flags/audit/export", dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))])
def export_flags_audit(
    format: str = "json",
    limit: int = 500,
    action: str | None = None,
    feature_id: str | None = None,
    actor: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _filter_audit_rows(_read_audit_events(limit=1000), action=action, feature_id=feature_id, actor=actor, limit=limit)
    rows = _enrich_audit_rows(rows)

    normalized_format = format.strip().lower()
    if normalized_format == "json":
        payload = {
            "status": "ok",
            "count": len(rows),
            "requested_by": str(getattr(current_user, "id", "")),
            "events": rows,
        }
        return Response(
            content=json.dumps(payload, ensure_ascii=True, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=feature_flags_audit.json"},
        )

    if normalized_format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=["timestamp", "action", "feature_id", "updated_by", "changes", "before", "after", "diff"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "timestamp": row.get("timestamp", ""),
                    "action": row.get("action", ""),
                    "feature_id": row.get("feature_id", ""),
                    "updated_by": row.get("updated_by", ""),
                    "changes": json.dumps(row.get("changes", {}), ensure_ascii=True),
                    "before": json.dumps(row.get("before", {}), ensure_ascii=True),
                    "after": json.dumps(row.get("after", {}), ensure_ascii=True),
                    "diff": json.dumps(row.get("diff", {}), ensure_ascii=True),
                }
            )
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=feature_flags_audit.csv"},
        )

    raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")


@router.get("/flags/audit/summary", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
def get_flags_audit_summary(
    action: str | None = None,
    feature_id: str | None = None,
    actor: str | None = None,
    limit: int = 1000,
    current_user: models.User = Depends(require_admin),
):
    rows = _filter_audit_rows(_read_audit_events(limit=1000), action=action, feature_id=feature_id, actor=actor, limit=limit)
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "summary": _summarize_audit(rows),
    }


@router.get("/flags/audit/anomalies", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
def get_flags_audit_anomalies(
    lookback_hours: int = 24,
    actor_threshold: int = 10,
    action_threshold: int = 20,
    action: str | None = None,
    feature_id: str | None = None,
    actor: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _filter_audit_rows(_read_audit_events(limit=1000), action=action, feature_id=feature_id, actor=actor, limit=1000)
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "anomalies": _detect_anomalies(
            rows,
            lookback_hours=lookback_hours,
            actor_threshold=actor_threshold,
            action_threshold=action_threshold,
        ),
    }

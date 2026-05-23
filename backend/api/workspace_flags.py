from typing import Any, Dict

from fastapi import APIRouter, Depends

from backend import models
from backend.api.workspace_shared import (DEFAULT_WORKSPACE_CONFIG,
                                          _append_audit_event,
                                          _load_workspace_config,
                                          _normalize_rule_payload,
                                          _sanitize_feature_payload,
                                          _save_workspace_config)
from backend.auth import require_admin
from backend.core.rate_limit import rate_limiter

router = APIRouter(tags=["workspace"])


@router.put("/flags", dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))])
def update_feature_flags(
    payload: Dict[str, bool],
    current_user: models.User = Depends(require_admin),
):
    config = _load_workspace_config()
    current = config.get("features_enabled", {})
    known_features = set((config.get("features_enabled") or {}).keys()) | set(
        (DEFAULT_WORKSPACE_CONFIG.get("features_enabled") or {}).keys()
    )
    changes = _sanitize_feature_payload(payload, known_features=known_features)
    merged = {**current, **changes}
    previous = current.copy()
    config["features_enabled"] = merged
    _save_workspace_config(config)
    _append_audit_event(
        {
            "action": "update_flags",
            "updated_by": str(getattr(current_user, "id", "")),
            "changes": changes,
            "before": previous,
            "after": merged,
        }
    )
    return {
        "status": "ok",
        "updated_by": str(getattr(current_user, "id", "")),
        "features_enabled": merged,
    }


@router.put(
    "/flags/rules/{feature_id}",
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
def update_feature_rule(
    feature_id: str,
    payload: Dict[str, Any],
    current_user: models.User = Depends(require_admin),
):
    config = _load_workspace_config()
    rules = dict(config.get("feature_rules") or {})
    current = dict(rules.get(feature_id) or {})
    normalized = _normalize_rule_payload(payload, fallback=current)
    merged = {**current, **normalized}
    rules[feature_id] = merged
    config["feature_rules"] = rules
    _save_workspace_config(config)
    _append_audit_event(
        {
            "action": "update_rule",
            "feature_id": feature_id,
            "updated_by": str(getattr(current_user, "id", "")),
            "before": current,
            "after": merged,
        }
    )
    return {
        "status": "ok",
        "feature_id": feature_id,
        "updated_by": str(getattr(current_user, "id", "")),
        "rule": merged,
    }

from fastapi import APIRouter, Depends

from backend import models
from backend.api.workspace_shared import (
    _append_audit_event,
    _load_workspace_config,
    _now_iso,
    _resolve_features,
    _save_workspace_config,
)
from backend.core.permissions import require_active_user, require_admin

router = APIRouter(tags=["workspace"])


@router.get("/config")
def get_workspace_config(current_user: models.User = Depends(require_active_user)):
    config = _load_workspace_config()
    config["features_raw"] = config.get("features_enabled", {}).copy()
    config["features_enabled"] = _resolve_features(config, current_user)
    config["requested_by"] = str(getattr(current_user, "id", ""))
    return config


@router.patch("/config")
def update_workspace_config(
    config: dict,
    current_user: models.User = Depends(require_admin),
):
    """Update workspace configuration."""
    _prev_config = _load_workspace_config()
    _save_workspace_config(config)
    user_id = str(getattr(current_user, "id", "admin"))
    _append_audit_event({
        "action": "update_workspace_config",
        "actor_user_id": user_id,
        "timestamp": _now_iso(),
        "changed_keys": list(config.keys()),
    })
    return {"status": "success"}

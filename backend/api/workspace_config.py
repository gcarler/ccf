from fastapi import APIRouter, Depends, HTTPException

from backend import models
from backend.api.workspace_shared import (_load_workspace_config,
                                          _resolve_features,
                                          _save_workspace_config)
from backend.auth import require_active_user, require_admin

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
    _save_workspace_config(config)
    return {"status": "success"}

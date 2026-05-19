from __future__ import annotations

import hashlib
from typing import Any, Dict

from fastapi import HTTPException

from backend import models
from backend.auth import VALID_ROLES

from backend.api.workspace_shared import MAX_LIST_ITEMS, MAX_USER_REF_LENGTH, ALLOWED_RULE_KEYS


def _sanitize_feature_payload(payload: Dict[str, Any], known_features: set[str]) -> Dict[str, bool]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Feature payload must be an object")

    unknown = [key for key in payload.keys() if key not in known_features]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown feature ids: {', '.join(unknown)}")

    normalized: Dict[str, bool] = {}
    for key, value in payload.items():
        if not isinstance(value, bool):
            raise HTTPException(status_code=422, detail=f"Feature '{key}' must be boolean")
        normalized[key] = value
    return normalized


def _normalize_role_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a list")
    if len(value) > MAX_LIST_ITEMS:
        raise HTTPException(status_code=422, detail=f"{field_name} exceeds {MAX_LIST_ITEMS} items")

    normalized: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            raise HTTPException(status_code=422, detail=f"{field_name} must contain only strings")
        role = raw.strip().lower()
        if not role:
            continue
        if role not in VALID_ROLES:
            raise HTTPException(status_code=422, detail=f"Invalid role in {field_name}: {role}")
        if role not in normalized:
            normalized.append(role)
    return normalized


def _normalize_user_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a list")
    if len(value) > MAX_LIST_ITEMS:
        raise HTTPException(status_code=422, detail=f"{field_name} exceeds {MAX_LIST_ITEMS} items")

    normalized: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            raise HTTPException(status_code=422, detail=f"{field_name} must contain only strings")
        item = raw.strip()
        if not item:
            continue
        if len(item) > MAX_USER_REF_LENGTH:
            raise HTTPException(status_code=422, detail=f"{field_name} contains overlong user reference")
        if item not in normalized:
            normalized.append(item)
    return normalized


def _normalize_rollout(value: Any, fallback: int = 100) -> int:
    if value is None:
        return max(0, min(int(fallback), 100))
    if isinstance(value, bool):
        raise HTTPException(status_code=422, detail="rollout_percent must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="rollout_percent must be an integer")
    return max(0, min(parsed, 100))


def _normalize_rule_payload(payload: Dict[str, Any], fallback: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Rule payload must be an object")

    unknown = [key for key in payload.keys() if key not in ALLOWED_RULE_KEYS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown rule fields: {', '.join(unknown)}")

    current = fallback or {}
    return {
        "roles_allow": _normalize_role_list(payload.get("roles_allow"), "roles_allow")
        if "roles_allow" in payload
        else _normalize_role_list(current.get("roles_allow", []), "roles_allow"),
        "roles_deny": _normalize_role_list(payload.get("roles_deny"), "roles_deny")
        if "roles_deny" in payload
        else _normalize_role_list(current.get("roles_deny", []), "roles_deny"),
        "users_allow": _normalize_user_list(payload.get("users_allow"), "users_allow")
        if "users_allow" in payload
        else _normalize_user_list(current.get("users_allow", []), "users_allow"),
        "users_deny": _normalize_user_list(payload.get("users_deny"), "users_deny")
        if "users_deny" in payload
        else _normalize_user_list(current.get("users_deny", []), "users_deny"),
        "rollout_percent": _normalize_rollout(payload.get("rollout_percent"), current.get("rollout_percent", 100)),
    }


def _stable_rollout_hit(user_ref: str, feature_id: str, rollout_percent: int) -> bool:
    clamped = max(0, min(rollout_percent, 100))
    if clamped >= 100:
        return True
    if clamped <= 0:
        return False
    digest = hashlib.md5(f"{feature_id}:{user_ref}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < clamped


def _resolve_features(config: Dict[str, Any], current_user: models.User) -> Dict[str, bool]:
    raw = config.get("features_enabled") or {}
    rules = config.get("feature_rules") or {}

    role = str(getattr(current_user, "role", "") or "").strip().lower()
    user_ref = str(getattr(current_user, "id", "") or getattr(current_user, "user_id", ""))

    resolved: Dict[str, bool] = {}
    all_features = set(raw.keys()) | set(rules.keys())

    for feature in all_features:
        base_enabled = bool(raw.get(feature, False))
        if not base_enabled:
            resolved[feature] = False
            continue

        rule = rules.get(feature) or {}
        roles_allow = {str(item).strip().lower() for item in rule.get("roles_allow", []) if str(item).strip()}
        roles_deny = {str(item).strip().lower() for item in rule.get("roles_deny", []) if str(item).strip()}
        users_allow = {str(item).strip() for item in rule.get("users_allow", []) if str(item).strip()}
        users_deny = {str(item).strip() for item in rule.get("users_deny", []) if str(item).strip()}
        rollout_percent = int(rule.get("rollout_percent", 100))

        if role in roles_deny or user_ref in users_deny:
            resolved[feature] = False
            continue

        if users_allow and user_ref not in users_allow:
            resolved[feature] = False
            continue

        if roles_allow and role not in roles_allow:
            resolved[feature] = False
            continue

        resolved[feature] = _stable_rollout_hit(user_ref=user_ref, feature_id=feature, rollout_percent=rollout_percent)

    return resolved
